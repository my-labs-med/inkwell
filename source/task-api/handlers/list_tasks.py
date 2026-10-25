from inkwell import tasks_repo
from inkwell.http import api_handler, query_param, respond, user_id
from inkwell.tasks import public
from inkwell.validation import validate_status


@api_handler
def handler(event, context):
    owner = user_id(event)
    status = query_param(event, "status")
    if status is not None:
        validate_status(status)
    tasks = tasks_repo.list_tasks(owner, status)
    return respond(200, {"tasks": [public(task) for task in tasks]})
