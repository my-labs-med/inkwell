#!/bin/bash
#
# Packages the Lambda code into deployment/dist/:
#   task-api.zip          handlers for every API route (one function per route, same package)
#   stream-processor.zip  DynamoDB Streams consumer
#   xray-layer.zip        Lambda layer with the AWS X-Ray SDK (arm64, Python 3.12)
#   ./deployment/build-dist.sh
#
# Zips are byte-identical for identical inputs, so Terraform only redeploys what changed.
#
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
dist="$root/deployment/dist"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT
mkdir -p "$staging/out"

deterministic_zip() {
  python3 - "$1" "$2" <<'EOF'
import os
import sys
import zipfile

source, target = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for folder, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            path = os.path.join(folder, name)
            info = zipfile.ZipInfo(os.path.relpath(path, source), date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as handle:
                archive.writestr(info, handle.read())
EOF
}

package() {
  local name="$1"
  shift
  mkdir -p "$staging/$name"
  for dir in "$@"; do
    cp -r "$dir" "$staging/$name/"
  done
  deterministic_zip "$staging/$name" "$staging/out/$name.zip"
}

package task-api "$root/source/shared/inkwell" "$root/source/task-api/handlers"
package stream-processor "$root/source/shared/inkwell" "$root/source/stream-processor/stream_processor"

uv pip install --quiet --no-deps --target "$staging/xray-layer/python" \
  --python-platform aarch64-manylinux2014 --python-version 3.12 --only-binary :all: \
  -r "$root/source/shared/requirements.txt"
deterministic_zip "$staging/xray-layer" "$staging/out/xray-layer.zip"

rm -rf "$dist"
mkdir -p "$dist"
mv "$staging/out/"*.zip "$dist/"
ls -1 "$dist" | sed "s|^|built deployment/dist/|"
