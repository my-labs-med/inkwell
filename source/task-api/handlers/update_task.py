from inkwell import tasks_repo
from inkwell.dates import utc_now
from inkwell.http import ApiError, api_handler, header, json_body, path_param, respond, user_id
from inkwell.ids import is_ulid
from inkwell.tasks import changes_for, public
from inkwell.validation import validate_task

NOT_FOUND = ApiError(404, "NOT_FOUND", "Task not found")
ATTEMPTS = 3


@api_handler
def handler(event, context):
    owner = user_id(event)
    task_id = path_param(event, "id")
    if not is_ulid(task_id):
        raise NOT_FOUND
    fields = validate_task(json_body(event), partial=True)
    client_date = header(event, "X-Client-Date")
    for _ in range(ATTEMPTS):
        existing = tasks_repo.get_task(owner, task_id)
        if existing is None:
            raise NOT_FOUND
        updates, removals = changes_for(existing, fields, utc_now(), client_date)
        task = tasks_repo.update_task(owner, task_id, updates, removals, existing["status"])
        if task is not None:
            return respond(200, public(task))
    raise ApiError(409, "CONFLICT", "Task changed while saving, please retry")
