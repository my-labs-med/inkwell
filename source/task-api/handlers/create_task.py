from inkwell import tasks_repo
from inkwell.dates import utc_now
from inkwell.http import ApiError, api_handler, header, json_body, respond, user_id
from inkwell.tasks import new_task, public
from inkwell.validation import validate_task

MAX_TASKS = 500


@api_handler
def handler(event, context):
    owner = user_id(event)
    fields = validate_task(json_body(event), partial=False)
    if tasks_repo.count_tasks(owner) >= MAX_TASKS:
        raise ApiError(409, "TASK_LIMIT", f"You can keep at most {MAX_TASKS} tasks")
    task = new_task(owner, fields, utc_now(), header(event, "X-Client-Date"))
    tasks_repo.put_task(task)
    return respond(201, public(task))
