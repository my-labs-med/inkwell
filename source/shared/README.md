# shared

The `inkwell` package, bundled into every Lambda package.

| Module | Responsibility |
|---|---|
| `http.py` | Lambda proxy responses, error shape, body/header/claim parsing, 4 KB body limit |
| `validation.py` | task field rules (title 1–120, description ≤ 1,000, status `todo`/`doing`/`done`) |
| `tasks.py` | task shape: new task, update diff, public view |
| `tasks_repo.py` | `tasks` table access (base table + `byStatus` GSI) |
| `stats_repo.py` | `stats` table access: exactly-once completion counters, streaks, milestone claims |
| `milestones.py` | milestone thresholds, selection and wording |
| `dates.py`, `ids.py` | local-day handling, streak math, ULID task IDs |
| `aws.py`, `tracing.py` | cached boto3 clients, X-Ray patching when the SDK layer is present |

`requirements.txt` lists what goes into the X-Ray layer. `boto3` comes from the Lambda runtime.
