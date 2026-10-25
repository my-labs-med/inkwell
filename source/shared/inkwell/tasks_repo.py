from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from inkwell.aws import tasks_table

STATUS_INDEX = "byStatus"


def _query_all(**kwargs):
    items = []
    while True:
        page = tasks_table().query(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _is_condition_failure(err):
    return err.response["Error"]["Code"] == "ConditionalCheckFailedException"


def list_tasks(user_id, status=None):
    if status:
        return _query_all(
            IndexName=STATUS_INDEX,
            KeyConditionExpression=Key("userId").eq(user_id)
            & Key("statusCreatedAt").begins_with(f"{status}#"),
            ScanIndexForward=False,
        )
    return _query_all(KeyConditionExpression=Key("userId").eq(user_id), ScanIndexForward=False)


def count_tasks(user_id):
    total = 0
    kwargs = {"KeyConditionExpression": Key("userId").eq(user_id), "Select": "COUNT"}
    while True:
        page = tasks_table().query(**kwargs)
        total += page["Count"]
        if "LastEvaluatedKey" not in page:
            return total
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def put_task(task):
    tasks_table().put_item(Item=task, ConditionExpression="attribute_not_exists(taskId)")


def get_task(user_id, task_id):
    return tasks_table().get_item(Key={"userId": user_id, "taskId": task_id}).get("Item")


def update_task(user_id, task_id, updates, removals, expected_status):
    names = {"#status": "status"}
    values = {":expected": expected_status}
    sets = []
    for index, (field, value) in enumerate(updates.items()):
        names[f"#s{index}"] = field
        values[f":s{index}"] = value
        sets.append(f"#s{index} = :s{index}")
    expression = "SET " + ", ".join(sets)
    if removals:
        for index, field in enumerate(removals):
            names[f"#r{index}"] = field
        expression += " REMOVE " + ", ".join(f"#r{index}" for index in range(len(removals)))
    try:
        result = tasks_table().update_item(
            Key={"userId": user_id, "taskId": task_id},
            UpdateExpression=expression,
            ConditionExpression="attribute_exists(taskId) AND #status = :expected",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as err:
        if _is_condition_failure(err):
            return None
        raise
    return result["Attributes"]


def delete_task(user_id, task_id):
    try:
        tasks_table().delete_item(
            Key={"userId": user_id, "taskId": task_id},
            ConditionExpression="attribute_exists(taskId)",
        )
    except ClientError as err:
        if _is_condition_failure(err):
            return False
        raise
    return True
