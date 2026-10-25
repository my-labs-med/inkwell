from inkwell import milestones, stats_repo
from inkwell.dates import client_day, days_before, utc_now
from inkwell.http import api_handler, header, respond, user_id


@api_handler
def handler(event, context):
    owner = user_id(event)
    today = client_day(header(event, "X-Client-Date"), utc_now())
    summary = stats_repo.get_summary(owner)
    days = stats_repo.list_days(owner, days_before(today, stats_repo.HISTORY_DAYS))
    summary["milestones"] = milestones.describe(summary["milestones"])
    return respond(200, {**summary, "days": days}, cache="private, max-age=60")
