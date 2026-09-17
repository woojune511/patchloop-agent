"""Independent relational oracle for PC conditioning rounds; evaluator-only."""

from itertools import combinations, permutations

import pandas as pd
import pgmpy.causal_discovery._base as module
from pgmpy.causal_discovery import ExpertKnowledge, PC


def edge(*nodes):
    return frozenset(nodes)


def expected_rounds(nodes, rules, depth, required, forbidden, temporal):
    """Enumerate valid CI witnesses against immutable edge sets at each depth."""
    edges = {edge(*pair) for pair in combinations(nodes, 2)} - forbidden
    witnesses = {}
    for size in range(depth + 1):
        available = {}
        for pair in edges - required:
            u, v = tuple(pair)
            candidates = {frozenset(given) for given in combinations(set(nodes) - pair, size)}
            admissible = {
                given for given in candidates
                if (all(edge(u, member) in edges for member in given)
                    or all(edge(v, member) in edges for member in given))
                and all(temporal.get(member, 0) <= min(temporal.get(u, 0), temporal.get(v, 0))
                        for member in given)
                and (pair, given) in rules
            }
            if admissible:
                available[pair] = admissible
        witnesses.update(available)
        edges = edges - available.keys()
    return edges, witnesses


def check(order, rules, depth, *, variant="stable", required=(), forbidden=(), tiers=(), enforce=True):
    required, forbidden = set(required), set(forbidden)
    temporal = {node: rank for rank, tier in enumerate(tiers) for node in tier}
    expected, witnesses = expected_rounds(
        order, rules, depth, required if enforce else set(), forbidden if enforce else set(), temporal)
    if variant == "orig":
        # This preserved three-node control is intentionally order-sensitive.
        hub, *spokes = sorted(order)
        survivor = max(spokes, key=order.index)
        removed = next(spoke for spoke in spokes if spoke != survivor)
        expected = {edge(hub, survivor)}
        witnesses = {edge(*spokes): {frozenset()}, edge(hub, removed): {frozenset({survivor})}}
    calls = []

    def ci(left, right, given, **kwargs):
        assert kwargs["significance_level"] == 0.037
        assert len(given) <= depth
        calls.append((edge(left, right), frozenset(given)))
        return calls[-1] in rules

    required_directed = [tuple(pair) for pair in required]
    required_directed += [(v, u) for u, v in required_directed]
    knowledge = ExpertKnowledge(required_edges=required_directed,
        forbidden_edges=[tuple(pair) for pair in forbidden], temporal_order=list(tiers))
    data = pd.DataFrame({name: [0, 1, 1, 0] for name in order})
    before = data.copy(deep=True)
    graph, separating = PC()._build_skeleton(
        data, ci_test=ci, variant=variant, max_cond_vars=depth,
        expert_knowledge=knowledge, enforce_expert_knowledge=enforce,
        significance_level=0.037, n_jobs=1, show_progress=False)
    assert data.equals(before), "input data or column order changed"
    assert set(graph) == set(order), "node identity changed"
    assert {edge(*pair) for pair in graph.edges()} == expected, "wrong skeleton"
    assert set(separating) == set(witnesses), "missing or spurious separating-set entry"
    assert all(frozenset(given) in witnesses[pair] for pair, given in separating.items()), "invalid CI witness"
    assert calls, "CI callback was bypassed"


def scenarios():
    rows = []
    for names in (("hub", "north", "south"), ("anchor", "left", "right")):
        hub, a, b = names
        rules = {(edge(a, b), frozenset()), (edge(hub, a), frozenset({b})),
                 (edge(hub, b), frozenset({a}))}
        for order in permutations(names):
            for depth in (0, 1):
                rows.append(("renamed-round", order, rules, depth, {}))
            rows.append(("parallel-preserved", order, rules, 1, {"variant": "parallel"}))
            rows.append(("orig-preserved", order, rules, 1, {"variant": "orig"}))
            rows.append(("required", order, rules, 1, {"required": {edge(hub, a)}}))
            rows.append(("forbidden", order, rules, 1, {"forbidden": {edge(hub, a)}}))
            rows.append(("not-enforced", order, rules, 1,
                         {"required": {edge(hub, a)}, "forbidden": {edge(hub, b)}, "enforce": False}))
            rows.append(("temporal", order, rules, 1, {"tiers": [[hub, a], [b]]}))
    hub, a, b, support = "center", "east", "west", "support"
    names = (hub, a, b, support)
    rules = {(edge(*pair), frozenset()) for pair in combinations((a, b, support), 2)}
    rules |= {(edge(hub, a), frozenset({b, support})), (edge(hub, b), frozenset({a, support}))}
    for order in permutations(names):
        for depth in (1, 2):
            rows.append(("second-depth", order, rules, depth, {}))
    names = ("alpha", "beta", "gone")
    rules = {(edge("alpha", "gone"), frozenset()), (edge("beta", "gone"), frozenset()),
             (edge("alpha", "beta"), frozenset({"gone"}))}
    for order in permutations(names):
        rows.append(("refresh-each-depth", order, rules, 1, {}))
    return rows


def main():
    assert module.__file__.startswith("/workspace/pgmpy/"), "imported image source"
    failed = 0
    rows = scenarios()
    for label, order, rules, depth, options in rows:
        try:
            check(order, rules, depth, **options)
        except Exception as error:
            failed += 1
            print(f"FAIL {label} {order} depth={depth}: {type(error).__name__}: {error}")
    print(f"{len(rows) - failed} passed, {failed} failed")
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
