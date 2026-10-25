import json
from datetime import UTC, datetime, timedelta

from conftest import api_event, payload
from handlers import create_task, delete_task, get_stats, get_task, list_tasks, update_task
from inkwell import tasks_repo

TODAY = datetime.now(UTC).date()


def create(title="Write chapter", user="user-a", **fields):
    response = create_task.handler(api_event(user, {"title": title, **fields}), None)
    assert response["statusCode"] == 201, response
    return payload(response)


def update(task_id, body, user="user-a", headers=None):
    return update_task.handler(api_event(user, body, {"id": task_id}, headers=headers), None)


def test_create_returns_public_task():
    task = create()
    assert len(task["taskId"]) == 26
    assert task["status"] == "todo"
    assert task["description"] == ""
    assert "userId" not in task and "statusCreatedAt" not in task
    stored = tasks_repo.get_task("user-a", task["taskId"])
    assert stored["statusCreatedAt"] == f"todo#{task['createdAt']}"


def test_list_newest_first_and_filter_by_status():
    first = create("one")
    second = create("two", status="done")
    third = create("three")
    response = list_tasks.handler(api_event(), None)
    ids = [t["taskId"] for t in payload(response)["tasks"]]
    assert ids == [third["taskId"], second["taskId"], first["taskId"]]
    done = payload(list_tasks.handler(api_event(query={"status": "done"}), None))["tasks"]
    assert [t["taskId"] for t in done] == [second["taskId"]]


def test_list_rejects_unknown_status():
    response = list_tasks.handler(api_event(query={"status": "archived"}), None)
    assert response["statusCode"] == 400


def test_other_users_cannot_touch_task():
    task = create()
    path = {"id": task["taskId"]}
    assert get_task.handler(api_event("user-b", path=path), None)["statusCode"] == 404
    assert update(task["taskId"], {"title": "mine"}, user="user-b")["statusCode"] == 404
    assert delete_task.handler(api_event("user-b", path=path), None)["statusCode"] == 404
    assert get_task.handler(api_event(path=path), None)["statusCode"] == 200


def test_malformed_id_is_not_found():
    for handler in (get_task, delete_task):
        assert handler.handler(api_event(path={"id": "../etc"}), None)["statusCode"] == 404
    assert update("nope", {"title": "x"})["statusCode"] == 404


def test_task_limit(monkeypatch):
    monkeypatch.setattr(create_task.tasks_repo, "count_tasks", lambda user: 500)
    response = create_task.handler(api_event(body={"title": "one more"}), None)
    assert response["statusCode"] == 409
    assert payload(response)["error"]["code"] == "TASK_LIMIT"


def test_completion_uses_client_date_within_a_day():
    task = create()
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    done = payload(update(task["taskId"], {"status": "done"}, headers={"x-client-date": tomorrow}))
    assert done["completedDay"] == tomorrow
    assert done["completedAt"]
    assert tasks_repo.get_task("user-a", task["taskId"])["statusCreatedAt"].startswith("done#")


def test_completion_ignores_implausible_client_date():
    for value in ((TODAY - timedelta(days=3)).isoformat(), "garbage", "2026-02-30"):
        task = create()
        done = payload(update(task["taskId"], {"status": "done"}, headers={"X-Client-Date": value}))
        assert done["completedDay"] == TODAY.isoformat()


def test_reopening_clears_completion():
    task = create(status="done")
    assert task["completedDay"]
    reopened = payload(update(task["taskId"], {"status": "todo"}))
    assert "completedDay" not in reopened and "completedAt" not in reopened


def test_title_edit_keeps_status_fields():
    task = create(status="done")
    edited = payload(update(task["taskId"], {"title": "Renamed"}))
    assert edited["title"] == "Renamed"
    assert edited["completedDay"] == task["completedDay"]


def test_update_requires_fields():
    task = create()
    assert update(task["taskId"], {})["statusCode"] == 400


def test_delete_then_get():
    task = create()
    path = {"id": task["taskId"]}
    response = delete_task.handler(api_event(path=path), None)
    assert response["statusCode"] == 204 and response["body"] == ""
    assert get_task.handler(api_event(path=path), None)["statusCode"] == 404


def test_missing_identity_is_unauthorized():
    response = list_tasks.handler(api_event(user=None), None)
    assert response["statusCode"] == 401
    assert payload(response)["error"]["code"] == "UNAUTHORIZED"


def test_cache_headers():
    assert list_tasks.handler(api_event(), None)["headers"]["Cache-Control"] == "no-store"
    stats = get_stats.handler(api_event(), None)
    assert stats["headers"]["Cache-Control"] == "private, max-age=60"
    assert payload(stats) == {"totalDone": 0, "longestStreak": 0, "milestones": [], "days": {}}


def test_cors_header_only_when_configured(monkeypatch):
    assert "Access-Control-Allow-Origin" not in list_tasks.handler(api_event(), None)["headers"]
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://localhost:8000")
    headers = list_tasks.handler(api_event(), None)["headers"]
    assert headers["Access-Control-Allow-Origin"] == "http://localhost:8000"


def test_unexpected_errors_are_masked(monkeypatch):
    def boom(*args):
        raise RuntimeError("secret detail")

    monkeypatch.setattr(list_tasks.tasks_repo, "list_tasks", boom)
    response = list_tasks.handler(api_event(), None)
    assert response["statusCode"] == 500
    assert "secret" not in json.dumps(payload(response))


def test_concurrent_status_change_is_recomputed(monkeypatch):
    task = create(status="done")
    real_get = tasks_repo.get_task
    stale = {"served": False}

    def get_then_race(user, task_id):
        current = real_get(user, task_id)
        if not stale["served"]:
            stale["served"] = True
            tasks_repo.update_task(user, task_id, {"status": "todo"}, ["completedDay"], "done")
        return current

    monkeypatch.setattr(update_task.tasks_repo, "get_task", get_then_race)
    response = update(task["taskId"], {"status": "doing"})
    assert response["statusCode"] == 200
    stored = real_get("user-a", task["taskId"])
    assert stored["status"] == "doing"
    assert stored["statusCreatedAt"].startswith("doing#")


def test_bad_base64_body_is_rejected():
    event = api_event(body="abc")
    event["isBase64Encoded"] = True
    assert create_task.handler(event, None)["statusCode"] == 400
