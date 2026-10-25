from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from inkwell.aws import stats_table

SUMMARY = "SUMMARY"
HISTORY_DAYS = 371


def _day_key(day):
    return f"DAY#{day}"


def _marker_key(task_id):
    return f"DONE#{task_id}"


def _condition_failed(err):
    code = err.response["Error"]["Code"]
    if code == "ConditionalCheckFailedException":
        return True
    if code == "TransactionCanceledException":
        reasons = err.response.get("CancellationReasons") or []
        return any(reason.get("Code") == "ConditionalCheckFailed" for reason in reasons)
    return False


def _transact(items):
    table = stats_table()
    client = table.meta.client
    try:
        client.transact_write_items(
            TransactItems=[{op: {"TableName": table.name, **body}} for op, body in items]
        )
    except ClientError as err:
        if _condition_failed(err):
            return False
        raise
    return True


def _counter(user_id, sk, delta):
    return (
        "Update",
        {
            "Key": {"userId": user_id, "sk": sk},
            "UpdateExpression": "ADD #n :d",
            "ExpressionAttributeNames": {"#n": "count"},
            "ExpressionAttributeValues": {":d": delta},
        },
    )


def complete(user_id, task_id, day):
    return _transact(
        [
            (
                "Put",
                {
                    "Item": {"userId": user_id, "sk": _marker_key(task_id), "day": day},
                    "ConditionExpression": "attribute_not_exists(sk)",
                },
            ),
            _counter(user_id, _day_key(day), 1),
            _counter(user_id, SUMMARY, 1),
        ]
    )


def uncomplete(user_id, task_id, day):
    return _transact(
        [
            (
                "Delete",
                {
                    "Key": {"userId": user_id, "sk": _marker_key(task_id)},
                    "ConditionExpression": "attribute_exists(sk)",
                },
            ),
            _counter(user_id, _day_key(day), -1),
            _counter(user_id, SUMMARY, -1),
        ]
    )


def drop_marker(user_id, task_id):
    stats_table().delete_item(Key={"userId": user_id, "sk": _marker_key(task_id)})


def get_summary(user_id):
    item = stats_table().get_item(Key={"userId": user_id, "sk": SUMMARY}, ConsistentRead=True)
    item = item.get("Item") or {}
    return {
        "totalDone": int(item.get("count", 0)),
        "longestStreak": int(item.get("longestStreak", 0)),
        "milestones": sorted(item.get("milestones", set())),
    }


def list_days(user_id, since_day):
    kwargs = {
        "KeyConditionExpression": Key("userId").eq(user_id)
        & Key("sk").between(_day_key(since_day), _day_key("9999-12-31")),
        "ConsistentRead": True,
    }
    days = {}
    while True:
        page = stats_table().query(**kwargs)
        for item in page.get("Items", []):
            count = int(item.get("count", 0))
            if count > 0:
                days[item["sk"].removeprefix("DAY#")] = count
        if "LastEvaluatedKey" not in page:
            return days
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def raise_longest_streak(user_id, streak):
    try:
        stats_table().update_item(
            Key={"userId": user_id, "sk": SUMMARY},
            UpdateExpression="SET longestStreak = :s",
            ConditionExpression="attribute_not_exists(longestStreak) OR longestStreak < :s",
            ExpressionAttributeValues={":s": streak},
        )
    except ClientError as err:
        if not _condition_failed(err):
            raise


def claim_milestone(user_id, milestone):
    try:
        stats_table().update_item(
            Key={"userId": user_id, "sk": SUMMARY},
            UpdateExpression="ADD milestones :m",
            ConditionExpression="attribute_not_exists(milestones) OR NOT contains(milestones, :v)",
            ExpressionAttributeValues={":m": {milestone}, ":v": milestone},
        )
    except ClientError as err:
        if _condition_failed(err):
            return False
        raise
    return True


def release_milestone(user_id, milestone):
    stats_table().update_item(
        Key={"userId": user_id, "sk": SUMMARY},
        UpdateExpression="DELETE milestones :m",
        ExpressionAttributeValues={":m": {milestone}},
    )
