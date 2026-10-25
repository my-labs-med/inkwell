import json

import boto3
import pytest
from boto3.dynamodb.types import TypeSerializer
from moto import mock_aws

from inkwell import aws

SENDER = "inkwell@example.com"
USER_EMAIL = "reader@example.com"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("TASKS_TABLE", "tasks")
    monkeypatch.setenv("STATS_TABLE", "stats")
    monkeypatch.setenv("SENDER_EMAIL", SENDER)
    monkeypatch.setenv("APP_URL", "https://inkwell.example.com")
    monkeypatch.delenv("ALLOWED_ORIGIN", raising=False)
    monkeypatch.delenv("DONE_MILESTONES", raising=False)
    monkeypatch.delenv("STREAK_MILESTONES", raising=False)


@pytest.fixture(autouse=True)
def aws_mock(env):
    with mock_aws():
        aws.reset()
        dynamodb = boto3.client("dynamodb")
        dynamodb.create_table(
            TableName="tasks",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "taskId", "AttributeType": "S"},
                {"AttributeName": "statusCreatedAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "taskId", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "byStatus",
                    "KeySchema": [
                        {"AttributeName": "userId", "KeyType": "HASH"},
                        {"AttributeName": "statusCreatedAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
        dynamodb.create_table(
            TableName="stats",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "userId", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "userId", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
        )
        yield
        aws.reset()


@pytest.fixture
def mail(monkeypatch):
    ses = boto3.client("ses")
    ses.verify_email_identity(EmailAddress=SENDER)
    cognito = boto3.client("cognito-idp")
    pool_id = cognito.create_user_pool(PoolName="inkwell")["UserPool"]["Id"]
    monkeypatch.setenv("USER_POOL_ID", pool_id)
    user = cognito.admin_create_user(
        UserPoolId=pool_id,
        Username=USER_EMAIL,
        UserAttributes=[{"Name": "email", "Value": USER_EMAIL}],
    )["User"]
    sub = next(a["Value"] for a in user["Attributes"] if a["Name"] == "sub")
    return {"sub": sub, "email": USER_EMAIL}


def sent_emails():
    from moto.backends import get_backend

    backend = get_backend("ses")["123456789012"]["us-east-1"]
    return backend.sent_messages


def api_event(user="user-a", body=None, path=None, query=None, headers=None):
    event = {
        "requestContext": {"authorizer": {"claims": {"sub": user}} if user else {}},
        "headers": headers or {},
        "pathParameters": path,
        "queryStringParameters": query,
        "body": body if body is None or isinstance(body, str) else json.dumps(body),
    }
    return event


def payload(response):
    return json.loads(response["body"]) if response["body"] else None


_serializer = TypeSerializer()
_sequence = iter(range(1, 10**9))


def stream_record(event_name, old=None, new=None):
    def image(item):
        return {key: _serializer.serialize(value) for key, value in item.items()}

    data = {"SequenceNumber": str(next(_sequence))}
    if old:
        data["OldImage"] = image(old)
    if new:
        data["NewImage"] = image(new)
    return {"eventID": data["SequenceNumber"], "eventName": event_name, "dynamodb": data}


def task_image(user="user-a", task_id="01JB0000000000000000000000", status="todo", day=None):
    item = {
        "userId": user,
        "taskId": task_id,
        "title": "Write",
        "status": status,
        "createdAt": "2026-10-25T10:00:00.000Z",
    }
    if status == "done":
        item["completedDay"] = day or "2026-10-25"
    return item
