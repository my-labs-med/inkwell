import pytest

from inkwell.http import ApiError, json_body
from inkwell.validation import validate_task


def error_code(fn):
    with pytest.raises(ApiError) as caught:
        fn()
    return caught.value.status, caught.value.code


@pytest.mark.parametrize(
    "data",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 121},
        {"title": 5},
        {"title": "bad\x07bell"},
        {"title": "ok", "description": "x" * 1001},
        {"title": "ok", "description": 3},
        {"title": "ok", "status": "archived"},
        {"title": "ok", "userId": "someone-else"},
        {},
    ],
)
def test_rejects_invalid_create(data):
    assert error_code(lambda: validate_task(data, partial=False)) == (400, "VALIDATION")


def test_accepts_boundaries_and_trims():
    fields = validate_task(
        {"title": "  " + "x" * 120 + " ", "description": "line\n\tnext  ", "status": "doing"},
        partial=False,
    )
    assert fields == {"title": "x" * 120, "description": "line\n\tnext", "status": "doing"}


def test_partial_requires_a_field():
    assert error_code(lambda: validate_task({}, partial=True)) == (400, "VALIDATION")
    assert validate_task({"status": "done"}, partial=True) == {"status": "done"}


@pytest.mark.parametrize(
    "body,expected",
    [
        ("not json", (400, "INVALID_JSON")),
        ("[1, 2]", (400, "INVALID_JSON")),
        ("", (400, "INVALID_JSON")),
        ('{"title": "' + "x" * 4090 + '"}', (413, "TOO_LARGE")),
    ],
)
def test_json_body_errors(body, expected):
    assert error_code(lambda: json_body({"body": body})) == expected
