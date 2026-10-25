from datetime import date, timedelta

import pytest

from conftest import api_event, payload, sent_emails, stream_record, task_image
from handlers import get_stats
from inkwell import stats_repo
from stream_processor import handler as stream
from stream_processor import mailer

TASK = "01JB0000000000000000000000"


def run(*records):
    return stream.handler({"Records": list(records)}, None)


def completed(task_id=TASK, user="user-a", day="2026-10-25"):
    return stream_record(
        "MODIFY",
        old=task_image(user, task_id),
        new=task_image(user, task_id, "done", day),
    )


def reopened(task_id=TASK, user="user-a", day="2026-10-25"):
    return stream_record(
        "MODIFY",
        old=task_image(user, task_id, "done", day),
        new=task_image(user, task_id),
    )


def marker_exists(task_id=TASK, user="user-a"):
    from inkwell.aws import stats_table

    return "Item" in stats_table().get_item(Key={"userId": user, "sk": f"DONE#{task_id}"})


@pytest.fixture(autouse=True)
def no_mail_by_default(monkeypatch, request):
    if "mail" not in request.fixturenames:
        monkeypatch.setattr(stream, "notify", lambda user, milestone: None)


def test_completion_counts_once_even_when_replayed():
    record = completed()
    assert run(record) == {"batchItemFailures": []}
    run(record)
    assert stats_repo.get_summary("user-a")["totalDone"] == 1
    assert stats_repo.list_days("user-a", "2026-01-01") == {"2026-10-25": 1}
    assert marker_exists()


def test_insert_as_done_counts():
    run(stream_record("INSERT", new=task_image(status="done")))
    assert stats_repo.get_summary("user-a")["totalDone"] == 1


def test_reopen_removes_completion_once():
    run(completed())
    record = reopened()
    run(record)
    run(record)
    assert stats_repo.get_summary("user-a")["totalDone"] == 0
    assert stats_repo.list_days("user-a", "2026-01-01") == {}
    assert not marker_exists()


def test_deleting_done_task_keeps_history():
    run(completed())
    run(stream_record("REMOVE", old=task_image(status="done")))
    assert stats_repo.get_summary("user-a")["totalDone"] == 1
    assert not marker_exists()


def test_irrelevant_changes_write_nothing():
    run(
        stream_record("INSERT", new=task_image()),
        stream_record("MODIFY", old=task_image(), new={**task_image(), "title": "New"}),
        stream_record("REMOVE", old=task_image()),
    )
    empty = {"totalDone": 0, "longestStreak": 0, "milestones": []}
    assert stats_repo.get_summary("user-a") == empty


def test_longest_streak_tracks_consecutive_days():
    start = date(2026, 10, 1)
    for offset in range(3):
        run(completed(f"01JB00000000000000000000{offset:02d}", day=str(start + timedelta(offset))))
    run(completed("01JB0000000000000000000099", day="2026-10-10"))
    assert stats_repo.get_summary("user-a")["longestStreak"] == 3


def test_failed_record_reports_it_and_the_rest(monkeypatch):
    records = [completed("01JB0000000000000000000001"), completed("01JB0000000000000000000002")]
    records.append(completed("01JB0000000000000000000003"))
    original = stream.process

    def flaky(record):
        if record is records[1]:
            raise RuntimeError("boom")
        original(record)

    monkeypatch.setattr(stream, "process", flaky)
    result = run(*records)
    expected = [r["dynamodb"]["SequenceNumber"] for r in records[1:]]
    assert [f["itemIdentifier"] for f in result["batchItemFailures"]] == expected


def test_stats_endpoint_reflects_stream():
    run(completed(day="2026-10-24"), completed("01JB0000000000000000000002", day="2026-10-25"))
    response = get_stats.handler(api_event(headers={"X-Client-Date": "2026-10-25"}), None)
    body = payload(response)
    assert body["totalDone"] == 2
    assert body["longestStreak"] == 2
    assert set(body["days"]) <= {"2026-10-24", "2026-10-25"}


def test_first_completion_emails_once(mail):
    record = completed(user=mail["sub"])
    run(record)
    run(record)
    emails = sent_emails()
    assert len(emails) == 1
    assert emails[0].destinations["ToAddresses"] == [mail["email"]]
    assert emails[0].subject == "Your first ink mark"
    assert stats_repo.get_summary(mail["sub"])["milestones"] == ["done:1"]


def test_demo_thresholds_send_one_email_per_milestone(mail, monkeypatch):
    monkeypatch.setenv("DONE_MILESTONES", "1,3")
    for n in range(3):
        run(completed(f"01JB00000000000000000000{n:02d}", user=mail["sub"]))
    assert [e.subject for e in sent_emails()] == ["Your first ink mark", "3 tasks, inked"]


def test_lowered_thresholds_never_burst(mail, monkeypatch):
    monkeypatch.setenv("DONE_MILESTONES", "100")
    for n in range(5):
        run(completed(f"01JB00000000000000000000{n:02d}", user=mail["sub"]))
    assert sent_emails() == []
    monkeypatch.setenv("DONE_MILESTONES", "1,3,5")
    run(completed("01JB0000000000000000000099", user=mail["sub"]))
    assert [e.subject for e in sent_emails()] == ["5 tasks, inked"]


def test_streak_milestone(mail, monkeypatch):
    monkeypatch.setenv("DONE_MILESTONES", "1000")
    monkeypatch.setenv("STREAK_MILESTONES", "7")
    start = date(2026, 10, 1)
    for offset in range(7):
        task_id = f"01JB00000000000000000000{offset:02d}"
        run(completed(task_id, user=mail["sub"], day=str(start + timedelta(offset))))
    assert [e.subject for e in sent_emails()] == ["A 7-day streak"]
    assert stats_repo.get_summary(mail["sub"])["longestStreak"] == 7


def test_failed_send_rolls_back_and_retries(mail, monkeypatch):
    real_send = mailer.send
    calls = {"n": 0}

    def flaky_send(*args):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("SES throttled")
        real_send(*args)

    monkeypatch.setattr(mailer, "send", flaky_send)
    record = completed(user=mail["sub"])
    result = run(record)
    assert len(result["batchItemFailures"]) == 1
    assert stats_repo.get_summary(mail["sub"])["milestones"] == []
    assert run(record) == {"batchItemFailures": []}
    assert len(sent_emails()) == 1
    assert stats_repo.get_summary(mail["sub"])["totalDone"] == 1


def test_permanent_send_failure_does_not_block_the_stream(mail, monkeypatch):
    from botocore.exceptions import ClientError

    def rejected(*args):
        raise ClientError({"Error": {"Code": "MessageRejected", "Message": "unverified"}}, "Send")

    monkeypatch.setattr(mailer, "send", rejected)
    assert run(completed(user=mail["sub"])) == {"batchItemFailures": []}
    assert stats_repo.get_summary(mail["sub"])["milestones"] == ["done:1"]
