#!/bin/bash
#
# Runs every lint check and unit test in the repository.
#   cd deployment && ./run-unit-tests.sh
#
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

headline() {
  echo "------------------------------------------------------------------------------"
  echo "$1"
  echo "------------------------------------------------------------------------------"
}

headline "[Setup] Installing Python dev dependencies"
uv sync --quiet

headline "[Lint] ruff"
uv run ruff check .
uv run ruff format --check .

headline "[Test] Lambda functions (pytest + moto)"
uv run pytest -q

headline "[Test] Frontend (node --test)"
node --test "source/frontend/test/"*.test.mjs

headline "[Build] Lambda packages (needed by the Terraform tests)"
"$root/deployment/build-dist.sh"

headline "[Test] Terraform (validate + mocked apply)"
terraform -chdir=source/infrastructure init -backend=false -input=false >/dev/null
terraform -chdir=source/infrastructure fmt -check -recursive
terraform -chdir=source/infrastructure validate
terraform -chdir=source/infrastructure test
