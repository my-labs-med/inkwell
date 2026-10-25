from inkwell.dates import streak_ending
from inkwell.ids import is_ulid, new_ulid
from inkwell.milestones import describe, pick


def test_ulids_sort_by_time():
    earlier = new_ulid(1_700_000_000_000)
    later = new_ulid(1_700_000_000_001)
    assert is_ulid(earlier) and earlier < later


def test_ulid_now():
    assert is_ulid(new_ulid())
    assert not is_ulid("01JB000000000000000000000I")
    assert not is_ulid(None)


def test_streak_ending():
    active = {"2026-10-23", "2026-10-24", "2026-10-25", "2026-10-20"}
    assert streak_ending("2026-10-25", active) == 3
    assert streak_ending("2026-10-22", active) == 0


def test_pick_highest_unsent(monkeypatch):
    monkeypatch.setenv("DONE_MILESTONES", "1,10,50")
    assert pick("done", 0, set()) is None
    assert pick("done", 12, set()) == "done:10"
    assert pick("done", 12, {"done:10"}) is None
    assert pick("done", 60, {"done:1"}) == "done:50"
    assert pick("done", 60, {"done:50"}) is None


def test_describe_gives_titles():
    assert describe(["done:1", "streak:7"]) == [
        {"id": "done:1", "title": "Your first ink mark"},
        {"id": "streak:7", "title": "A 7-day streak"},
    ]


def test_default_thresholds():
    assert pick("done", 1, set()) == "done:1"
    assert pick("streak", 6, set()) is None
    assert pick("streak", 30, {"streak:7"}) == "streak:30"
