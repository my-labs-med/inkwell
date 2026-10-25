# task-api

One Lambda function per route, all deployed from the same `task-api.zip` with a different handler.
Every route sits behind the API Gateway Cognito authorizer; the user ID comes from the token's `sub`.

| Method | Path | Handler |
|---|---|---|
| `GET` | `/tasks?status=` | `handlers.list_tasks.handler` |
| `POST` | `/tasks` | `handlers.create_task.handler` |
| `GET` | `/tasks/{id}` | `handlers.get_task.handler` |
| `PUT` | `/tasks/{id}` | `handlers.update_task.handler` |
| `DELETE` | `/tasks/{id}` | `handlers.delete_task.handler` |
| `GET` | `/stats` | `handlers.get_stats.handler` |

Errors use `{"error": {"code", "message"}}`. Task routes send `Cache-Control: no-store`; `/stats` sends
`private, max-age=60`. Requests may include `X-Client-Date: YYYY-MM-DD` so completions land on the
user's local day.

**Environment:** `TASKS_TABLE`, `STATS_TABLE`, optional `ALLOWED_ORIGIN` (CORS for local development).
