import os

DEFAULT_DONE = "1,10,50,100"
DEFAULT_STREAK = "7,30"


def thresholds(kind):
    name, default = {
        "done": ("DONE_MILESTONES", DEFAULT_DONE),
        "streak": ("STREAK_MILESTONES", DEFAULT_STREAK),
    }[kind]
    raw = os.environ.get(name) or default
    return sorted({int(part) for part in raw.split(",") if part.strip()})


def pick(kind, value, sent):
    reached = [n for n in thresholds(kind) if n <= value]
    if not reached:
        return None
    milestone = f"{kind}:{reached[-1]}"
    return None if milestone in sent else milestone


def describe(milestones_sent):
    return [{"id": m, "title": message(m)[0]} for m in milestones_sent]


def message(milestone):
    kind, number = milestone.split(":")
    number = int(number)
    if kind == "done" and number == 1:
        return (
            "Your first ink mark",
            "You finished your first task in Inkwell. Every page starts with one line.",
        )
    if kind == "done":
        return (
            f"{number} tasks, inked",
            f"You've finished {number} tasks in Inkwell. That's a lot of crossed-out lines.",
        )
    return (
        f"A {number}-day streak",
        f"You've finished something {number} days in a row. Keep the ink flowing.",
    )
