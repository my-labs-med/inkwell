import logging

from botocore.exceptions import ClientError

from inkwell import milestones, stats_repo
from inkwell.dates import days_before, streak_ending
from stream_processor import mailer
from stream_processor.transitions import classify

log = logging.getLogger()
log.setLevel(logging.INFO)

PERMANENT_SEND_ERRORS = {
    "MessageRejected",
    "MailFromDomainNotVerifiedException",
    "AccountSendingPausedException",
    "ConfigurationSetDoesNotExistException",
    "InvalidParameterException",
    "ResourceNotFoundException",
}


def celebrate(user_id, day):
    summary = stats_repo.get_summary(user_id)
    active = stats_repo.list_days(user_id, days_before(day, stats_repo.HISTORY_DAYS))
    streak = streak_ending(day, active)
    if streak > summary["longestStreak"]:
        stats_repo.raise_longest_streak(user_id, streak)

    sent = set(summary["milestones"])
    for kind, value in (("done", summary["totalDone"]), ("streak", streak)):
        milestone = milestones.pick(kind, value, sent)
        if milestone and stats_repo.claim_milestone(user_id, milestone):
            notify(user_id, milestone)


def notify(user_id, milestone):
    try:
        recipient = mailer.email_for(user_id)
        if recipient is None:
            log.warning("No email for user %s, skipping %s", user_id, milestone)
            return
        mailer.send(recipient, *milestones.message(milestone))
        log.info("Sent milestone %s to user %s", milestone, user_id)
    except ClientError as err:
        code = err.response["Error"]["Code"]
        if code in PERMANENT_SEND_ERRORS:
            log.error("Dropping milestone %s for user %s: %s", milestone, user_id, code)
            return
        stats_repo.release_milestone(user_id, milestone)
        raise
    except Exception:
        stats_repo.release_milestone(user_id, milestone)
        raise


def process(record):
    transition = classify(record)
    if transition is None:
        return
    if transition.kind == "removed":
        stats_repo.drop_marker(transition.user_id, transition.task_id)
    elif transition.day is None:
        log.warning("Task %s has no completedDay, skipping", transition.task_id)
    elif transition.kind == "uncompleted":
        stats_repo.uncomplete(transition.user_id, transition.task_id, transition.day)
    else:
        stats_repo.complete(transition.user_id, transition.task_id, transition.day)
        celebrate(transition.user_id, transition.day)


def handler(event, context):
    records = event.get("Records", [])
    for index, record in enumerate(records):
        try:
            process(record)
        except Exception:
            log.exception("Failed to process record %s", record.get("eventID"))
            return {
                "batchItemFailures": [
                    {"itemIdentifier": r["dynamodb"]["SequenceNumber"]} for r in records[index:]
                ]
            }
    return {"batchItemFailures": []}
