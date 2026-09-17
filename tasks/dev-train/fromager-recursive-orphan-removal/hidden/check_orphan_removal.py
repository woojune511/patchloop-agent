"""Evaluator-only graph invariants derived independently from the public contract."""

from collections import Counter

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

import fromager.dependency_graph as module
from fromager.requirements_file import RequirementType


def key(name):
    return "" if name == "" else name if "==" in name else name + "==1"


def graph_case(edges, removals, extra_nodes=()):
    graph = module.DependencyGraph()
    normalized = [(key(a), key(b), kind) for a, b, kind in edges]
    names = {key(name) for name in extra_nodes}
    names.update(endpoint for a, b, _ in normalized for endpoint in (a, b))
    for node_key in sorted(names - {""}):
        name, version = node_key.split("==")
        graph.nodes[node_key] = module.DependencyNode(
            canonicalize_name(name), Version(version), download_url="https://example.invalid/" + name,
            pre_built=True, constraint=Requirement(name + ">=0"),
        )
    for parent, child, kind in normalized:
        name, version = child.split("==")
        parent_name, parent_version = parent.split("==") if parent else (None, None)
        graph.add_dependency(
            canonicalize_name(parent_name) if parent else None,
            Version(parent_version) if parent else None,
            RequirementType(kind), Requirement(name + ">=0"), Version(version),
        )
    for removed in removals:
        target = key(removed)
        before = set(graph.nodes)
        metadata = {
            node_key: (node.canonicalized_name, node.version, node.download_url,
                       node.pre_built, str(node.constraint))
            for node_key, node in graph.nodes.items()
        }
        outgoing = Counter(
            (parent, edge.key, str(edge.req_type), str(edge.req))
            for parent, node in graph.nodes.items() for edge in node.children
        )
        removed_set = {target} if target in before else set()
        while True:
            affected = {child for parent, child, _, _ in outgoing if parent in removed_set}
            newly_parentless = {
                child for child in affected - removed_set
                if all(parent in removed_set for parent, dest, _, _ in outgoing if dest == child)
            }
            if not newly_parentless:
                break
            removed_set.update(newly_parentless)
        expected_nodes = before - removed_set
        expected_edges = Counter({edge: count for edge, count in outgoing.items()
                                  if edge[0] in expected_nodes and edge[1] in expected_nodes})
        name, version = target.split("==")
        graph.remove_dependency(canonicalize_name(name), Version(version))
        assert set(graph.nodes) == expected_nodes, "wrong surviving node set"
        actual_children = Counter(
            (parent, edge.key, str(edge.req_type), str(edge.req))
            for parent, node in graph.nodes.items() for edge in node.children
        )
        actual_parents = Counter(
            (edge.key, child, str(edge.req_type), str(edge.req))
            for child, node in graph.nodes.items() for edge in node.parents
        )
        assert actual_children == actual_parents == expected_edges, "edge reciprocity changed"
        assert {
            node_key: (node.canonicalized_name, node.version, node.download_url,
                       node.pre_built, str(node.constraint))
            for node_key, node in graph.nodes.items()
        } == {node_key: metadata[node_key] for node_key in expected_nodes}, "metadata changed"


def cases():
    def edges(*pairs):
        return [(a, b, "install") for a, b in pairs]

    chain = edges(("", "g0"), *((f"g{i}", f"g{i+1}") for i in range(7)))
    diamond = edges(("", "apex"), ("apex", "west"), ("apex", "east"),
                    ("west", "join"), ("east", "join"), ("join", "tail"))
    shared = edges(("", "north"), ("", "south"), ("north", "center"),
                   ("south", "center"), ("center", "end"))
    return [
        ("single", edges(("", "solo")), ["solo"], ()),
        ("deep", chain, ["g0"], ()),
        ("interior", chain, ["g3"], ()),
        ("leaf", chain, ["g7"], ()),
        ("diamond", diamond, ["apex"], ()),
        ("diamond-anchored", diamond + edges(("", "join")), ["apex"], ()),
        ("shared", shared, ["north"], ()),
        ("shared-sequential", shared, ["north", "south"], ()),
        ("duplicate-edge-types", [("", "head", "toplevel"),
            ("head", "body", "build-system"), ("head", "body", "install"),
            ("body", "tail", "build-backend")], ["head"], ()),
        ("multiple-incoming", edges(("", "a"), ("", "b"), ("a", "c"),
                                    ("b", "c"), ("c", "d")), ["c"], ()),
        ("target-version", edges(("", "pkg==1"), ("", "pkg==2"),
                                 ("pkg==1", "old"), ("pkg==2", "new")), ["pkg==2"], ()),
        ("child-version", edges(("", "one"), ("one", "lib==1"),
                                ("", "lib==2"), ("lib==1", "tail")), ["one"], ()),
        ("unrelated-orphan", chain, ["g0"], ("unrelated",)),
        ("absent", shared, ["absent"], ("untouched",)),
        ("absent-version", edges(("", "package==1")), ["package==2"], ()),
        ("repeated", diamond, ["apex", "apex"], ()),
    ]


def main():
    assert module.__file__.startswith("/workspace/src/"), "evaluator imported image source"
    failures = 0
    for label, edges, removals, extra_nodes in cases():
        try:
            graph_case(edges, removals, extra_nodes)
        except Exception as error:
            failures += 1
            print(f"FAIL {label}: {type(error).__name__}: {error}")
    print(f"{len(cases()) - failures} passed, {failures} failed")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
