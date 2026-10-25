from inkwell.dates import client_day, iso
from inkwell.ids import new_ulid

PRIVATE_FIELDS = {"userId", "statusCreatedAt"}


def new_task(user_id, fields, now, client_date=None):
    created_at = iso(now)
    status = fields.get("status", "todo")
    task = {
        "userId": user_id,
        "taskId": new_ulid(int(now.timestamp() * 1000)),
        "title": fields["title"],
        "description": fields.get("description", ""),
        "status": status,
        "statusCreatedAt": f"{status}#{created_at}",
        "createdAt": created_at,
        "updatedAt": created_at,
    }
    if status == "done":
        task["completedAt"] = created_at
        task["completedDay"] = client_day(client_date, now)
    return task


def changes_for(existing, fields, now, client_date=None):
    updates = {**fields, "updatedAt": iso(now)}
    removals = []
    status = fields.get("status")
    if status and status != existing["status"]:
        updates["statusCreatedAt"] = f"{status}#{existing['createdAt']}"
        if status == "done":
            updates["completedAt"] = iso(now)
            updates["completedDay"] = client_day(client_date, now)
        elif existing["status"] == "done":
            removals = ["completedAt", "completedDay"]
    return updates, removals


def public(task):
    return {key: value for key, value in task.items() if key not in PRIVATE_FIELDS}
