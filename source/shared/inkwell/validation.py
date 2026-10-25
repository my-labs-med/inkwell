import unicodedata

from inkwell.http import ApiError

STATUSES = ("todo", "doing", "done")
TITLE_MAX = 120
DESCRIPTION_MAX = 1000
FIELDS = {"title", "description", "status"}


def _invalid(message):
    return ApiError(400, "VALIDATION", message)


def _has_control_chars(text, allowed=""):
    return any(unicodedata.category(ch) == "Cc" and ch not in allowed for ch in text)


def validate_status(value):
    if value not in STATUSES:
        raise _invalid(f"status must be one of: {', '.join(STATUSES)}")
    return value


def validate_task(data, *, partial):
    unknown = set(data) - FIELDS
    if unknown:
        raise _invalid(f"Unknown field(s): {', '.join(sorted(unknown))}")

    fields = {}
    if "title" in data or not partial:
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            raise _invalid("title is required")
        title = title.strip()
        if len(title) > TITLE_MAX:
            raise _invalid(f"title must be at most {TITLE_MAX} characters")
        if _has_control_chars(title):
            raise _invalid("title contains invalid characters")
        fields["title"] = title

    if "description" in data:
        description = data["description"]
        if not isinstance(description, str):
            raise _invalid("description must be a string")
        description = description.rstrip()
        if len(description) > DESCRIPTION_MAX:
            raise _invalid(f"description must be at most {DESCRIPTION_MAX} characters")
        if _has_control_chars(description, allowed="\n\t"):
            raise _invalid("description contains invalid characters")
        fields["description"] = description

    if "status" in data:
        fields["status"] = validate_status(data["status"])

    if partial and not fields:
        raise _invalid("Nothing to update")
    return fields
