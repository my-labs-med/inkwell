from inkwell import tasks_repo
from inkwell.http import ApiError, api_handler, path_param, respond, user_id
from inkwell.ids import is_ulid


@api_handler
def handler(event, context):
    owner = user_id(event)
    task_id = path_param(event, "id")
    if not (is_ulid(task_id) and tasks_repo.delete_task(owner, task_id)):
        raise ApiError(404, "NOT_FOUND", "Task not found")
    return respond(204)
