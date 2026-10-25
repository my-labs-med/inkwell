from inkwell import tasks_repo
from inkwell.http import ApiError, api_handler, path_param, respond, user_id
from inkwell.ids import is_ulid
from inkwell.tasks import public


@api_handler
def handler(event, context):
    owner = user_id(event)
    task_id = path_param(event, "id")
    task = tasks_repo.get_task(owner, task_id) if is_ulid(task_id) else None
    if task is None:
        raise ApiError(404, "NOT_FOUND", "Task not found")
    return respond(200, public(task))
