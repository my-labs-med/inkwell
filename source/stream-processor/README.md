# stream-processor

Consumes the `tasks` table stream (`NEW_AND_OLD_IMAGES`) and maintains each user's stats in the `stats`
table. Handler: `stream_processor.handler.handler`. Configure the event source mapping with
`ReportBatchItemFailures`.

| Task change | Effect |
|---|---|
| becomes `done` | +1 for the day and the total, check milestones |
| leaves `done` | −1 for the day and the total |
| deleted while `done` | history kept |

Counters are exactly-once: a per-task marker written in the same transaction makes retried records
no-ops. When a milestone is reached, the user's email is looked up in Cognito and a short note is sent
through SES. Each milestone is sent at most once; a permanent SES rejection is logged and skipped so it
never blocks the stream.

**Environment:** `TASKS_TABLE`, `STATS_TABLE`, `USER_POOL_ID`, `SENDER_EMAIL`, `APP_URL`,
`DONE_MILESTONES` (default `1,10,50,100`), `STREAK_MILESTONES` (default `7,30`).
