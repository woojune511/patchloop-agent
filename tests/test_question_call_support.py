from __future__ import annotations

import pytest
from test_evidence_focus import select, span

from patchloop.dev.question_support import question_support

CODE = '''def read_item(path, label=None):
    try:
        data = open_item(path)
    except OSError:
        raise LoadFailure(path)
    if label is None:
        label = derive_label(path)
    return data, label

def from_name(label):
    spec = locate(label)
    if spec.kind == "virtual":
        return build_virtual(spec.parts)
    if spec.path is None:
        raise Missing(label)
    return dispatch(spec.path, label, fallback=False)

def dispatch(path, label=None, fallback=True, source=False):
    try:
        path = normalize(path)
        source = True
    except Missing:
        pass
    if label is None:
        label = guess_label(path)
    if path in cache:
        return cache[path]
    if source:
        return read_item(path, label)
    if fallback and label:
        return from_name(label)
    raise Missing(path)

def distant(path):
    return dispatch(path)

def irrelevant(path):
    return unrelated(path)

END = True
'''.rstrip()


def line(text, snippet):
    return next(n for n, value in enumerate(text.splitlines(), 1) if snippet in value)


def refs(text=CODE, path="x.py", digest="hash"):
    return [{"kind": "source", "path": path, "file_hash": digest,
             "role": role, "start_line": line(text, start), "end_line": line(text, end)}
            for role, start, end in (
                ("primary", "data =", "raise LoadFailure"),
                ("countercheck", 'if spec.kind', "fallback=False"),
            )]


def observed(text=CODE, path="x.py", digest="hash"):
    return {(path, digest, n): (value, 2, 1)
            for n, value in enumerate(text.splitlines(), 1)}


@pytest.mark.parametrize("rename,offset", [(False, 0), (True, 17)])
def test_calls_keep_argument_guards_and_local_counterevidence_without_case_names(rename, offset):
    text = CODE
    if rename:
        for before, after in [("read_item", "unpack"), ("from_name", "lookup"),
                              ("dispatch", "choose"), ("path", "target"),
                              ("label", "key"), ("source", "concrete")]:
            text = text.replace(before, after)
    text = "\n" * offset + text
    support = question_support(observed(text), refs(text))
    numbers = {n for _, _, n in support}
    required = ["normalize(", "= True", "except Missing:", "pass", "if ",
                "guess_", "in cache:", "return cache[", "derive_", "spec = locate"]
    for snippet in required:
        assert line(text, snippet) in numbers
    # These separate preconditions and bypasses are not an isolated call line.
    caller_start = line(text, "fallback=True")
    assert set(range(caller_start, line(text, "raise Missing(path)" if not rename
                                       else "raise Missing(target)"))) <= numbers
    assert line(text, "def distant") not in numbers  # No transitive caller expansion.
    assert line(text, "def irrelevant") not in numbers
    assert support == question_support(dict(reversed(list(observed(text).items()))),
                                       list(reversed(refs(text))))


def test_ambiguous_observed_function_names_do_not_expand_callers():
    other = "def read_item(path):\n    return other(path)\n\nEND = True"
    data = observed() | observed(other, path="other.py", digest="other")
    primary = [refs()[0]]
    support = question_support(data, primary)
    assert ("x.py", "hash", line(CODE, "derive_label")) in support
    assert ("x.py", "hash", line(CODE, "normalize(")) not in support
    assert not any(p == "other.py" for p, _, _ in support)


@pytest.mark.parametrize("variant", ["gap", "tail", "syntax", "literal", "fstring", "language",
                                     "stale", "unavailable", "legacy"])
def test_unknown_or_ineligible_source_adds_no_support(variant):
    text = "def leaf(value):\n    return value\n\nEND = True"
    path, digest = "x.py", "hash"
    focus = [{"kind": "source", "role": "primary", "path": path, "file_hash": digest,
              "start_line": 2, "end_line": 2}]
    if variant == "tail":
        text = text.split("\n\n")[0]  # No observed closing/dedent witness.
    elif variant == "syntax":
        text = text.replace("def leaf(value):", "def leaf(value): (")
    elif variant in {"literal", "fstring"}:
        text = ('f' if variant == "fstring" else '') + '"""\n' + text + '\n"""\nEND = True'
        focus[0].update(start_line=3, end_line=3)
    elif variant == "language":
        path = focus[0]["path"] = "x.js"
    elif variant == "stale":
        focus[0]["file_hash"] = "old"
    elif variant == "unavailable":
        focus[0]["unavailable_reason"] = "expired"
    elif variant == "legacy":
        focus[0].pop("role")
    data = observed(text, path, digest)
    if variant == "gap":
        del data[path, digest, 1]
    assert not question_support(data, focus)


@pytest.mark.parametrize("commented", [False, True])
def test_support_keeps_try_alternatives_and_finally_with_source_order(commented):
    text = '''def leaf(value):
    return value

def caller(value):
    try:
        if value:
            value = prepare(value)
        else:
            value = default()
        return leaf(value)
    except Missing:
        return fallback(value)
    finally:
        release(value)

END = True'''
    if commented:
        text = text.replace("else:", "else :  # alternate input")
        text = text.replace("finally:", "finally :  # cleanup after either arm")
    focus = [{"kind": "source", "role": "countercheck", "path": "x.py", "file_hash": "hash",
              "start_line": 2, "end_line": 2}]
    support = question_support(observed(text), focus)
    assert set(range(4, 15)) <= {n for _, _, n in support}


def test_call_connection_includes_import_effects_failure_and_immediate_return_conditions():
    text = '''def leaf(value):
    return helper(value)

def helper(value: "Input" = "default") -> "Output":
    from parser import decode as parse_value
    if value is None:
        return empty()
    return parse_value(value)

def caller(value, cwd, enabled=False):
    from api import Engine
    if cwd:
        before = current_directory()
        enter_directory(cwd)
    try:
        if enabled:
            return Engine().leaf(value)
        raise Missing(value)
    finally:
        if cwd:
            enter_directory(before)

def unrelated_helper():
    return parse_value("unrelated")

END = True'''
    focus = [{"kind": "source", "role": "primary", "path": "x.py", "file_hash": "hash",
              "start_line": 2, "end_line": 2}]
    support = question_support(observed(text), focus)
    for snippet in ("from parser", "if value is None", "return empty", "return parse_value",
                    "from api", "enter_directory(cwd)", "raise Missing", "enter_directory(before)"):
        assert ("x.py", "hash", line(text, snippet)) in support
    assert ("x.py", "hash", line(text, "def unrelated_helper")) not in support


def test_native_overlap_and_pair_support_fit_exactly_but_never_evict_explicit_refs():
    text = '''def leaf(value):
    return value

def caller(value, enabled=False):
    if enabled:
        return leaf(value)

END = True'''
    focus = [{"kind": "source", "role": "primary", "path": "x.py", "file_hash": "hash",
              "start_line": 2, "end_line": 2},
             {"kind": "source", "role": "countercheck", "path": "x.py", "file_hash": "hash",
              "start_line": 8, "end_line": 8}]
    data = [span(1, text), span(50, "newer filler" * 20, 10)]
    # Expected bundle is the two function blocks, with the blank separator omitted.
    cost = sum(len(s) for s in ("\n".join(text.splitlines()[:2]),
                               "\n".join(text.splitlines()[3:6]), "END = True"))
    got = select(data, focus, limit=cost)
    delivered = {s["start_line"] + i for s in got.source_spans
                 for i, _ in enumerate(s["content"].split("\n"))}
    assert {1, 2, 4, 5, 6, 8} <= delivered and 50 not in delivered
    assert got.retained_content_chars == cost
    small = select(data, focus, limit=cost - 1)
    assert small.retained_content_chars <= cost - 1
    assert {2, 8} <= {s["start_line"] + i for s in small.source_spans
                      for i, _ in enumerate(s["content"].split("\n"))}
    native = [span(1, "\n".join(text.splitlines()[:2]))]
    overlap = select(data, focus, limit=cost - len(native[0]["content"]), native=native)
    assert overlap.retained_content_chars == cost - len(native[0]["content"])
    assert not any(s["start_line"] <= 2 for s in overlap.source_spans)
    anchor = select(data, focus, limit=len("newer filler" * 20),
                    priorities=[("x.py", 50, 50, 0)])
    assert anchor.source_spans[0]["start_line"] == 50
