# infrastructure

Terraform for the whole stack, in `us-east-1`, with local state.

| File | Creates |
|---|---|
| `dynamodb.tf` | `tasks` table (`byStatus` GSI, Streams) and `stats` table |
| `cognito.tf` | user pool, managed login domain, web app client |
| `lambda.tf` | six API functions and the stream processor (via `modules/lambda-function`), X-Ray layer, stream mapping, dead-letter queue |
| `api_gateway.tf` | REST API under `/api`, Cognito authorizer, `prod` stage, throttling, access logs, optional stats cache |
| `waf.tf` | edge web ACL on CloudFront; regional web ACL that only admits requests from CloudFront |
| `frontend.tf` | private S3 bucket, frontend upload, generated `js/config.js`, CloudFront with cache and security header policies |
| `ses.tf` | sender and demo recipient identities |
| `monitoring.tf` | SNS alerts, Lambda/API/stream alarms, monthly budget |

`modules/lambda-function` packages one function with its own IAM role (its own log group, X-Ray, plus
the exact statements passed in), a log group with retention, and active tracing.

## Deploy

Prerequisites: AWS credentials for the target account, Terraform ≥ 1.5, Python 3.12, `pip`.

```bash
./deployment/build-dist.sh

cd source/infrastructure
cp terraform.tfvars.example terraform.tfvars    # set sender_email and alert_email
terraform init
terraform plan
terraform apply
```

After the first apply:

1. Click the SES verification link sent to `sender_email` (and to each `demo_recipient_emails` address).
2. Confirm the SNS subscription email sent to `alert_email`.
3. Open the `app_url` output and sign up.

The Lambda code ships from `deployment/dist/`, so run `build-dist.sh` before any apply that should
pick up code changes.

## Demo switches

Set these in `terraform.tfvars` and run `terraform apply`:

| Variable | Effect |
|---|---|
| `done_milestones = "1,3,5"` | milestone emails after 1, 3 and 5 completions |
| `blocked_countries = ["TN"]` | the edge WAF returns 403 for that country |
| `enable_api_cache = true` | API Gateway caches `GET /api/stats` per user for 60 s (~$0.02/hour, switch off afterwards) |

## Checks to show

| Check | Expected |
|---|---|
| `curl -I <app_url>assets/icons.svg` twice | `x-cache: Hit from cloudfront` the second time |
| `curl <api_url_direct>/api/stats` | `403`: the API only accepts traffic from CloudFront |
| POST a body over 4 KB to `<app_url>api/tasks` | `403` from the edge WAF |
| Complete a task | milestone email, a new dot in the calendar |
| X-Ray service map | API Gateway → Lambda → DynamoDB / SES / Cognito |

## Test

```bash
terraform init -backend=false
terraform validate
terraform test
```

`tests/stack.tftest.hcl` applies the configuration against mocked providers. It needs no AWS
credentials, but it does read the zips built by `build-dist.sh`.

## Tear down

```bash
terraform destroy
```

The site bucket is emptied automatically. The API Gateway CloudWatch logging role is an
account-level setting; destroying it leaves the account's API Gateway logging role unset.
