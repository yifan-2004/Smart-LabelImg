#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="${1:-$ROOT/release/Smart-Label-Local-Web-Source.zip}"
STAGE="$(mktemp -d)"
PACKAGE_ROOT="$STAGE/Smart-Label-Web"
trap 'rm -rf "$STAGE"' EXIT

FILES=(
  README.md LICENSE THIRD_PARTY_NOTICES.md docs/local-web.md docs/images/web-annotation.jpg pyproject.toml
  licenses/MobileSAM-Apache-2.0.txt licenses/LabelImg-MIT.txt
  requirements-web.txt requirements-web-dev.txt requirements-ai.txt
  setup_web.sh run_web.sh setup_web.ps1 run_web.ps1 setup_web.bat run_web.bat
  models/mobile_sam.pt
  examples/make_web_demo.py examples/web-demo/classes.txt
  examples/web-demo/frame_001.png examples/web-demo/frame_002.png examples/web-demo/frame_003.png
  examples/web-demo/frame_001.txt examples/web-demo/frame_002.txt examples/web-demo/frame_003.txt
  smart_labelimg/__init__.py smart_labelimg/annotation.py smart_labelimg/ai_backend.py
  smart_labelimg/labels.py smart_labelimg/paths.py smart_labelimg/propagation.py
  smart_labelimg/web_app.py smart_labelimg/web_service.py
  smart_labelimg/web/static/index.html smart_labelimg/web/static/styles.css smart_labelimg/web/static/app.js
  tests/conftest.py tests/test_annotation_io.py tests/test_ai_backend.py tests/test_propagation.py
  tests/test_web_launcher.py tests/test_web_service.py tests/test_web_static.py
  tests/test_local_web_package.py tests/frontend/workflow.test.cjs
  scripts/create_local_web_package.sh
)

mkdir -p "$PACKAGE_ROOT" "$(dirname "$OUTPUT")"
for file in "${FILES[@]}"; do
  if [ ! -f "$ROOT/$file" ]; then
    echo "Missing required local-web file: $file" >&2
    exit 1
  fi
  mkdir -p "$PACKAGE_ROOT/$(dirname "$file")"
  cp -p "$ROOT/$file" "$PACKAGE_ROOT/$file"
done

rm -f "$OUTPUT"
(
  cd "$STAGE"
  zip -X -q -r "$OUTPUT" Smart-Label-Web
)
echo "Local web source package: $OUTPUT"
