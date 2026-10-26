# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Terraform for the full stack under `source/infrastructure`: a reusable Lambda module, a REST API with Cognito authorizer and an optional per-user stats cache, edge and origin WAF web ACLs, CloudFront with cache and security header policies, alarms, a dead-letter queue and a budget
- Offline Terraform tests against mocked providers
- X-Ray sampling rule that traces every Inkwell request
- Architecture diagram with its draw.io source

### Changed

- Lambda functions and the X-Ray layer target arm64 (Graviton)
- The stack deploys to a configurable region (default `eu-north-1`); only the CloudFront web ACL stays in `us-east-1`

## [1.0.0] - 2026-10-25

### Added

- Task API: list, create, get, update and delete tasks, one Lambda per route, scoped to the signed-in Cognito user
- Stats API (`GET /stats`): streaks and daily completions, designed to be cached per user at API Gateway
- DynamoDB Streams processor that keeps per-user stats exactly once and emails milestone congratulations through SES
- Configurable milestone thresholds (`DONE_MILESTONES`, `STREAK_MILESTONES`)
- Inkwell web client: HTML, CSS and vanilla JS with Cognito Hosted UI sign-in (PKCE), an ink-dot calendar, a streak counter, light and dark themes, and instant delete with undo
- Self-hosted fonts and icons under `/assets` for long-lived CloudFront caching
- Strict request limits (4 KB bodies) so AWS WAF can enforce a tight size rule
- X-Ray tracing of DynamoDB, SES and Cognito calls via a Lambda layer
- `deployment/run-unit-tests.sh` and `deployment/build-dist.sh`
