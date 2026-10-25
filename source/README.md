# Source

Each folder is one component with its own README and tests.

| Folder | What it is | Deployed as |
|---|---|---|
| [shared](./shared/README.md) | `inkwell` package: HTTP helpers, validation, DynamoDB repositories, milestones | bundled into both Lambda packages |
| [task-api](./task-api/README.md) | one handler per API route | `task-api.zip`, six Lambda functions |
| [stream-processor](./stream-processor/README.md) | DynamoDB Streams consumer: stats + milestone emails | `stream-processor.zip`, one Lambda function |
| [frontend](./frontend/README.md) | static HTML/CSS/vanilla JS client | S3 + CloudFront |
| [infrastructure](./infrastructure/README.md) | Terraform for the whole stack | — |

`conftest.py` holds the pytest fixtures shared by every component: in-memory DynamoDB, SES and
Cognito through moto, plus API Gateway and stream event builders.

## Test

```bash
cd deployment
./run-unit-tests.sh
```

## Build

```bash
cd deployment
./build-dist.sh
```

Outputs `deployment/dist/task-api.zip`, `stream-processor.zip` and `xray-layer.zip`. The layer is built
for `arm64` (Graviton) and Python 3.12.
