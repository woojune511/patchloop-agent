from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from moto import mock_dynamodb
from moto.dynamodb.models.table import Table


def _create_table(
    *,
    name: str = "events",
    with_index: bool = False,
) -> Any:
    resource = boto3.resource("dynamodb", region_name="us-east-1")
    kwargs: dict[str, Any] = {
        "TableName": name,
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    }
    if with_index:
        kwargs["AttributeDefinitions"].extend(
            [
                {"AttributeName": "group", "AttributeType": "S"},
                {"AttributeName": "sequence", "AttributeType": "N"},
            ]
        )
        kwargs["GlobalSecondaryIndexes"] = [
            {
                "IndexName": "group-sequence",
                "KeySchema": [
                    {"AttributeName": "group", "KeyType": "HASH"},
                    {"AttributeName": "sequence", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ]
    return resource.create_table(**kwargs)


def _put_partition(
    table: Any,
    partition: str,
    count: int,
    *,
    states: tuple[str, ...] = ("keep", "drop"),
) -> None:
    for index in range(count):
        table.put_item(
            Item={
                "pk": partition,
                "sk": f"{index:02d}",
                "state": states[index % len(states)],
                "payload": f"value-{partition}-{index}",
            }
        )


def test_submitted_table_query_is_imported() -> None:
    expected = Path("/workspace/moto/dynamodb/models/table.py").resolve()
    actual = Path(inspect.getsourcefile(Table.query) or "").resolve()
    assert actual == expected


@mock_dynamodb
def test_scanned_count_excludes_other_partitions() -> None:
    table = _create_table()
    _put_partition(table, "target", 4)
    _put_partition(table, "other", 7)

    response = table.query(KeyConditionExpression=Key("pk").eq("target"))

    assert response["Count"] == 4
    assert response["ScannedCount"] == 4
    assert {item["pk"] for item in response["Items"]} == {"target"}


@mock_dynamodb
def test_filter_expression_counts_items_before_filtering() -> None:
    table = _create_table()
    _put_partition(table, "target", 5)
    _put_partition(table, "other", 3)

    response = table.query(
        KeyConditionExpression=Key("pk").eq("target"),
        FilterExpression=Attr("state").eq("keep"),
    )

    assert response["Count"] == 3
    assert response["ScannedCount"] == 5
    assert {item["state"] for item in response["Items"]} == {"keep"}


@mock_dynamodb
def test_range_condition_counts_only_matching_key_range() -> None:
    table = _create_table()
    _put_partition(table, "target", 8)
    _put_partition(table, "other", 4)

    response = table.query(
        KeyConditionExpression=(
            Key("pk").eq("target") & Key("sk").between("02", "05")
        )
    )

    assert response["Count"] == 4
    assert response["ScannedCount"] == 4
    assert [item["sk"] for item in response["Items"]] == ["02", "03", "04", "05"]


@mock_dynamodb
def test_each_page_counts_only_items_evaluated_on_that_page() -> None:
    table = _create_table()
    _put_partition(table, "target", 7)

    pages: list[dict[str, Any]] = []
    start_key: dict[str, Any] | None = None
    while True:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("pk").eq("target"),
            "Limit": 3,
        }
        if start_key is not None:
            kwargs["ExclusiveStartKey"] = start_key
        page = table.query(**kwargs)
        pages.append(page)
        start_key = page.get("LastEvaluatedKey")
        if start_key is None:
            break

    assert [page["Count"] for page in pages] == [3, 3, 1]
    assert [page["ScannedCount"] for page in pages] == [3, 3, 1]
    assert [item["sk"] for page in pages for item in page["Items"]] == [
        "00",
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
    ]


@mock_dynamodb
def test_limit_is_applied_before_filter_expression() -> None:
    table = _create_table()
    _put_partition(table, "target", 6)

    first = table.query(
        KeyConditionExpression=Key("pk").eq("target"),
        FilterExpression=Attr("state").eq("keep"),
        Limit=3,
    )
    second = table.query(
        KeyConditionExpression=Key("pk").eq("target"),
        FilterExpression=Attr("state").eq("keep"),
        Limit=3,
        ExclusiveStartKey=first["LastEvaluatedKey"],
    )

    assert first["ScannedCount"] == 3
    assert first["Count"] == 2
    assert second["ScannedCount"] == 3
    assert second["Count"] == 1
    assert "LastEvaluatedKey" not in second


@mock_dynamodb
def test_projection_and_reverse_order_do_not_change_count() -> None:
    table = _create_table()
    _put_partition(table, "target", 4)

    response = table.query(
        KeyConditionExpression=Key("pk").eq("target"),
        ProjectionExpression="payload",
        ScanIndexForward=False,
    )

    assert response["Count"] == 4
    assert response["ScannedCount"] == 4
    assert [item["payload"] for item in response["Items"]] == [
        "value-target-3",
        "value-target-2",
        "value-target-1",
        "value-target-0",
    ]
    assert all(set(item) == {"payload"} for item in response["Items"])


@mock_dynamodb
def test_index_query_scopes_count_to_index_key_condition() -> None:
    table = _create_table(with_index=True)
    for index in range(9):
        table.put_item(
            Item={
                "pk": f"item-{index}",
                "sk": "record",
                "group": "alpha" if index < 5 else "beta",
                "sequence": index if index < 5 else index - 5,
                "payload": f"value-{index}",
            }
        )

    response = table.query(
        IndexName="group-sequence",
        KeyConditionExpression=(
            Key("group").eq("alpha") & Key("sequence").between(1, 3)
        ),
    )

    assert response["Count"] == 3
    assert response["ScannedCount"] == 3
    assert [item["sequence"] for item in response["Items"]] == [1, 2, 3]


@mock_dynamodb
def test_empty_query_reports_zero_without_page_token() -> None:
    table = _create_table()
    _put_partition(table, "other", 3)

    response = table.query(KeyConditionExpression=Key("pk").eq("missing"))

    assert response["Count"] == 0
    assert response["ScannedCount"] == 0
    assert "LastEvaluatedKey" not in response
