#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="${1:-$ROOT/release/Smart-Label-Windows-Development-Source.zip}"
STAGE="$(mktemp -d)"
PACKAGE_ROOT="$STAGE/Smart-Label"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$PACKAGE_ROOT" "$(dirname "$OUTPUT")"

cd "$ROOT"
git ls-files --cached -z | while IFS= read -r -d '' file; do
  case "$file" in
    .git/*|.worktrees/*|.venv/*|build/*|dist/*|release/*|*/__pycache__/*|*.pyc|*.command|*.icns|build_app.sh|setup.sh|run.sh|scripts/verify_macos_release.sh|scripts/install_locate_anything_cpp.sh)
      continue
      ;;
  esac
  mkdir -p "$PACKAGE_ROOT/$(dirname "$file")"
  cp -p "$file" "$PACKAGE_ROOT/$file"
done

cp -p "$ROOT/docs/windows-install-build.md" "$PACKAGE_ROOT/WINDOWS-DEVELOPMENT.md"
rm -rf "$PACKAGE_ROOT/docs/superpowers"

rm -f "$OUTPUT"
(
  cd "$STAGE"
  zip -X -q -r "$OUTPUT" Smart-Label
)

echo "Windows development package: $OUTPUT"
