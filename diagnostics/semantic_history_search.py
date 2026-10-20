"""Local-only embedding ranker for a diagnostic; not an agent runtime dependency."""
from __future__ import annotations

import time
from pathlib import Path

from diagnostics.decision_sampler import require
from patchloop.util import canonical_json, sha256_json

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
WINDOW_TOKENS = 512
OVERLAP_TOKENS = 64
RRF_K = 60


def windows(tokenizer, text):
    """Keep every overflow window and its exact range in the original JSON string."""
    encoded = tokenizer.encode(text)
    parts = [encoded, *encoded.overflowing]
    spans = []
    for part in parts:
        offsets = [(a, b) for a, b in part.offsets if b > a]
        require(offsets and len(part.ids) <= WINDOW_TOKENS, "invalid token window")
        spans.append((min(a for a, _ in offsets), max(b for _, b in offsets)))
    require(spans[-1][1] == len(text.rstrip()), "record tail was truncated")
    return parts, spans


def ranked(records, scores):
    # A cached vector from another run/future record is never a retrieval candidate.
    values = [(scores[key], record) for key, record in records.items() if key in scores]
    return sorted(values, key=lambda p: (
        -p[0], p[1]["origin"]["first_delivered_sequence"], p[1]["record_id"]))


def fuse(records, lexical, dense):
    scores = {}
    for order in (lexical, dense):
        for rank, (_, record) in enumerate(order, 1):
            key = record["record_id"]
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
    return ranked(records, scores)


class LocalEncoder:
    """Official ONNX, CLS pooling, normalized float32 vectors, CPU only, no network."""

    def __init__(self, model: Path):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.np = np
        self.tokenizer = Tokenizer.from_file(str(model / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=WINDOW_TOKENS, stride=OVERLAP_TOKENS)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model / "onnx/model.onnx"),
            sess_options=options, providers=["CPUExecutionProvider"])
        self.cache, self.entries = {}, {}
        self.inference_seconds = 0.0
        self.scoring_seconds = 0.0
        self.encoded_windows = 0

    def prepare(self, texts, *, query=False):
        pending = {}
        for raw in texts:
            key = sha256_json([query, raw])
            if key in self.entries:
                continue
            text = QUERY_PREFIX + raw if query else raw
            parts, spans = windows(self.tokenizer, text)
            require(not query or len(parts) == 1, "query prefix exceeds model window")
            keys = []
            for part in parts:
                ids, types = part.ids, part.type_ids
                digest = sha256_json([ids, types])
                keys.append(digest)
                if digest not in self.cache:
                    pending[digest] = (ids, types)
            self.entries[key] = {"windows": keys, "spans": spans, "query": query}
        todo = list(pending.items())
        started = time.perf_counter()
        for start in range(0, len(todo), 8):
            batch = todo[start:start + 8]
            width = max(len(v[0]) for _, v in batch)
            ids = self.np.zeros((len(batch), width), dtype=self.np.int64)
            types = self.np.zeros_like(ids)
            mask = self.np.zeros_like(ids)
            for index, (_, (tokens, token_types)) in enumerate(batch):
                ids[index, :len(tokens)] = tokens
                types[index, :len(tokens)] = token_types
                mask[index, :len(tokens)] = 1
            feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
            output = self.session.run(None, {i.name: feed[i.name]
                                            for i in self.session.get_inputs()})[0]
            require(output.ndim == 3 and output.shape[2] == 768, "unexpected ONNX output")
            vectors = output[:, 0, :].astype(self.np.float32)
            norm = self.np.linalg.norm(vectors, axis=1, keepdims=True)
            require(self.np.isfinite(vectors).all() and (norm > 0).all(), "invalid embedding")
            vectors /= norm
            for (key, _), vector in zip(batch, vectors, strict=True):
                self.cache[key] = vector
            self.encoded_windows += len(batch)
            if start % 128 == 0:
                print(canonical_json({"embedding_windows_done": start + len(batch),
                    "batch_windows": len(todo), "total_unique_windows": self.encoded_windows}),
                    flush=True)
        self.inference_seconds += time.perf_counter() - started

    def score(self, query, records, *, body_for=None):
        bodies = {key: canonical_json(body_for(r) if body_for else r["body"])
                  for key, r in records.items()}
        self.prepare(list(bodies.values()))
        self.prepare([query], query=True)
        started = time.perf_counter()
        q = self.cache[self.entries[sha256_json([True, query])]["windows"][0]]
        scores, matches = {}, {}
        for key, text in bodies.items():
            entry = self.entries[sha256_json([False, text])]
            vectors = self.np.stack([self.cache[k] for k in entry["windows"]])
            similarities = vectors @ q
            index = int(similarities.argmax())
            scores[key] = float(similarities[index])
            start, end = entry["spans"][index]
            matches[key] = {"window": index, "windows": len(entry["windows"]),
                           "start": start, "end": end, "text": text[start:end]}
        self.scoring_seconds += time.perf_counter() - started
        return scores, matches

    def save(self, output, store):
        keys = sorted(self.cache)
        path = output / "embeddings.npz"
        self.np.savez_compressed(path, keys=self.np.array(keys),
                                vectors=self.np.stack([self.cache[k] for k in keys]))
        return {"vectors": store.put_bytes(path.read_bytes(), "application/zip").model_dump(
                    mode="json"),
                "entries": store.put_json(self.entries).model_dump(mode="json"),
                "unique_windows": len(keys), "text_entries": len(self.entries),
                "inference_seconds": self.inference_seconds,
                "scoring_seconds": self.scoring_seconds}
