"""CI partitions must preserve coverage and keep module fixtures together."""

import pytest

from scripts.pytest_shard import select_nodes


@pytest.mark.parametrize("total", [1, 2, 4, 7])
def test_every_collected_node_belongs_to_exactly_one_shard(total):
    nodes = [f"tests/test_{file}.py::test_case[{case}::value]"
             for file in range(13) for case in range(file + 1)]
    shards = [select_nodes(nodes, index, total) for index in range(total)]
    assert sorted(node for shard in shards for node in shard) == sorted(nodes)
    files = [{node.split("::", 1)[0] for node in shard} for shard in shards]
    assert sum(map(len, files)) == len(set.union(*files))
    assert shards == [select_nodes(list(reversed(nodes)), index, total)[::-1]
                      for index in range(total)]


@pytest.mark.parametrize("index,total", [(-1, 4), (4, 4), (0, 0)])
def test_invalid_shards_are_rejected(index, total):
    with pytest.raises(ValueError, match="shard index"):
        select_nodes(["tests/test_one.py::test_one"], index, total)
