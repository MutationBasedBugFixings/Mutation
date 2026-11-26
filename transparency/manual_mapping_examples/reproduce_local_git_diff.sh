#!/usr/bin/env bash
set -euo pipefail

# Manual mapping examples: Cli-3, Cli-4, Cli-5, Cli-8
# This script generates the exact local git diff from Defects4J's local tags.
# It does NOT run RQ5.

export PATH="/home1/furqan/tools_and_libs/defects4j/framework/bin:$PATH"

command -v defects4j >/dev/null || {
  echo "ERROR: defects4j is not on PATH"
  exit 1
}

ROOT="${1:-$HOME/manual_mapping/defects4j}"
WORK_ROOT="$ROOT/checkouts"
OUT_ROOT="$ROOT/local_git_diff"

mkdir -p "$WORK_ROOT" "$OUT_ROOT"

for BUG in 3 4 5 8; do
  PROJECT="Cli"
  WORK="$WORK_ROOT/${PROJECT}-${BUG}"
  OUT="$OUT_ROOT/${PROJECT}-${BUG}"
  mkdir -p "$OUT"

  echo
  echo "===== ${PROJECT}-${BUG} ====="

  if [[ ! -d "$WORK/.git" ]]; then
    defects4j checkout -p "$PROJECT" -v "${BUG}b" -w "$WORK"
  else
    echo "Existing checkout found: $WORK"
  fi

  BUGGY_TAG="D4J_${PROJECT}_${BUG}_BUGGY_VERSION"
  FIXED_TAG="D4J_${PROJECT}_${BUG}_FIXED_VERSION"

  git -C "$WORK" show-ref --verify --quiet "refs/tags/$BUGGY_TAG" || {
    echo "ERROR: Missing tag $BUGGY_TAG in $WORK"
    exit 1
  }
  git -C "$WORK" show-ref --verify --quiet "refs/tags/$FIXED_TAG" || {
    echo "ERROR: Missing tag $FIXED_TAG in $WORK"
    exit 1
  }

  BUGGY_HASH=$(git -C "$WORK" rev-parse "${BUGGY_TAG}^{commit}")
  FIXED_HASH=$(git -C "$WORK" rev-parse "${FIXED_TAG}^{commit}")

  # Full patch (production + test changes) in developer direction.
  git -C "$WORK" diff --binary --no-ext-diff --unified=80 \
    "$BUGGY_HASH" "$FIXED_HASH" > "$OUT/${PROJECT}-${BUG}.full.patch"

  git -C "$WORK" diff --name-status "$BUGGY_HASH" "$FIXED_HASH" \
    > "$OUT/changed_files.txt"

  git -C "$WORK" diff --stat "$BUGGY_HASH" "$FIXED_HASH" \
    > "$OUT/diff_stat.txt"

  {
    echo "Benchmark: Defects4J"
    echo "Project: $PROJECT"
    echo "Bug ID: $BUG"
    echo "Buggy tag: $BUGGY_TAG"
    echo "Fixed tag: $FIXED_TAG"
    echo "Local buggy tag commit: $BUGGY_HASH"
    echo "Local fixed tag commit: $FIXED_HASH"
    echo "Direction: BUGGY -> FIXED"
    echo "Patch: ${PROJECT}-${BUG}.full.patch"
  } > "$OUT/metadata.txt"

  echo "Generated: $OUT/${PROJECT}-${BUG}.full.patch"
  echo "Buggy local tag commit: $BUGGY_HASH"
  echo "Fixed local tag commit: $FIXED_HASH"
done

echo
echo "All four local full diffs generated under: $OUT_ROOT"
