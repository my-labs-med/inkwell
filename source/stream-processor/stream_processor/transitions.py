from dataclasses import dataclass

from boto3.dynamodb.types import TypeDeserializer

_deserializer = TypeDeserializer()


@dataclass(frozen=True)
class Transition:
    kind: str
    user_id: str
    task_id: str
    day: str | None = None


def _image(record, name):
    raw = record.get("dynamodb", {}).get(name)
    if not raw:
        return {}
    return {key: _deserializer.deserialize(value) for key, value in raw.items()}


def _is_done(image):
    return image.get("status") == "done"


def classify(record):
    old = _image(record, "OldImage")
    new = _image(record, "NewImage")
    event = record.get("eventName")
    task = new or old
    if not task:
        return None
    user_id, task_id = task["userId"], task["taskId"]

    if event in ("INSERT", "MODIFY") and _is_done(new) and not _is_done(old):
        return Transition("completed", user_id, task_id, new.get("completedDay"))
    if event == "MODIFY" and _is_done(old) and not _is_done(new):
        return Transition("uncompleted", user_id, task_id, old.get("completedDay"))
    if event == "REMOVE" and _is_done(old):
        return Transition("removed", user_id, task_id)
    return None
