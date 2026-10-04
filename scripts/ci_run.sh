#!/usr/bin/env bash
# Run CCOmmit's headless release check against this product checkout (SPEC 6.12).
# Used by .github/workflows/compliance.yml and runnable locally.
#
# Inputs (env, all optional unless noted):
#   CCOMMIT_DIR   CCOmmit checkout (default ./_ccommit); the CLI lives in $CCOMMIT_DIR/backend
#   OUT_DIR       output dir (default ./out)
#   VERSION       product version (default: ./version file, else the tag name without "v")
#   SHA           commit under test (default: git rev-parse HEAD)
#   BASELINE      baseline file (default: compliance/cco-baseline.json if it exists)
#   PR_NUMBER, RUN_NUMBER, RUN_URL, BRANCH   set on pull requests; PR_NUMBER enables the PR comment
#   GH_REPO       owner/name, needed for the PR comment (GitHub Actions sets GITHUB_REPOSITORY)
#   GH_TOKEN      token for gh (PR comment)
#   MISTRAL_API_KEY  required by the engine
#   GITHUB_STEP_SUMMARY  if set, the comment is appended to it
#   CCOMMIT_APP_URL  CCOmmit app base URL for the review's links (default http://127.0.0.1:20001)
#
# On pull requests it also posts a PR review (scripts/ci_review.py): inline comments on the changed lines that
# findings cite, REQUEST_CHANGES when NOT_READY. The upserted summary comment stays.
#
# Exit code is the audit's: 1 NOT_READY, 0 READY/REVIEW_REQUIRED, 2 engine error.
set -uo pipefail

MARKER='<!-- ccommit-check -->'
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

CCOMMIT_DIR="$(cd "${CCOMMIT_DIR:-./_ccommit}" 2>/dev/null && pwd)" || { echo "CCOMMIT_DIR not found" >&2; exit 2; }
OUT_DIR="${OUT_DIR:-$ROOT/out}"
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

if [ -z "${VERSION:-}" ]; then
  if [ -f version ]; then
    VERSION="$(tr -d '[:space:]' < version)"
  elif [ -n "${GITHUB_REF_NAME:-}" ]; then
    VERSION="${GITHUB_REF_NAME#v}"
  else
    VERSION="$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')"
  fi
fi
SHA="${SHA:-$(git rev-parse HEAD)}"
BASELINE="${BASELINE:-}"
if [ -z "$BASELINE" ] && [ -f compliance/cco-baseline.json ]; then
  BASELINE="$ROOT/compliance/cco-baseline.json"
fi
[ -n "$VERSION" ] || { echo "cannot determine VERSION" >&2; exit 2; }

echo "ci_run: version=$VERSION sha=$SHA baseline=${BASELINE:-none} pr=${PR_NUMBER:-none} out=$OUT_DIR"

# 1. Bundle = tracked files at HEAD, extracted into a directory (code at the root, next to compliance/).
BUNDLE="$(mktemp -d)"
trap 'rm -rf "$BUNDLE"' EXIT
git archive HEAD | tar -x -C "$BUNDLE"

# 2. Audit.
args=(audit --bundle "$BUNDLE" --version "$VERSION" --sha "$SHA" --out "$OUT_DIR")
[ -n "$BASELINE" ] && args+=(--baseline "$BASELINE")
[ -n "${PR_NUMBER:-}" ] && args+=(--pr "$PR_NUMBER")
[ -n "${RUN_NUMBER:-}" ] && args+=(--run-number "$RUN_NUMBER")
[ -n "${RUN_URL:-}" ] && args+=(--run-url "$RUN_URL")
[ -n "${BRANCH:-}" ] && args+=(--branch "$BRANCH")

(cd "$CCOMMIT_DIR/backend" && uv run cco "${args[@]}")
CODE=$?

# 3. Comment text. Exit 2 (or no output at all) is never shown as NOT READY.
COMMENT="$OUT_DIR/comment.md"
if [ "$CODE" -ne 0 ] && [ "$CODE" -ne 1 ]; then
  CODE=2
fi
if [ "$CODE" -eq 2 ] || [ ! -s "$COMMENT" ]; then
  cat > "$COMMENT" <<EOF
$MARKER
## CCOmmit could not run

The release check did not complete (engine error, not a compliance verdict). Version \`$VERSION\`, commit \`${SHA:0:7}\`.
Re-run the job. This is **not** a NOT READY result.
${RUN_URL:+
[Run log]($RUN_URL)}
EOF
  CODE=2
fi

# 4. Step summary.
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  cat "$COMMENT" >> "$GITHUB_STEP_SUMMARY"
fi

# 5. Annotations.
if [ "$CODE" -eq 2 ]; then
  echo "::error title=CCOmmit could not run::Engine error; no verdict was produced."
elif [ "$CODE" -eq 0 ] && command -v jq >/dev/null 2>&1 && \
     [ "$(jq -r '.readiness.gate // ""' "$OUT_DIR/result.json" 2>/dev/null)" = "REVIEW_REQUIRED" ]; then
  echo "::warning title=CCOmmit::REVIEW_REQUIRED: findings still need counsel review."
fi

# 6. Upsert the single PR comment (found by the hidden marker). Failure here never changes the exit code.
if [ -n "${PR_NUMBER:-}" ]; then
  REPO="${GH_REPO:-${GITHUB_REPOSITORY:-}}"
  if [ -z "$REPO" ] || ! command -v gh >/dev/null 2>&1; then
    echo "ci_run: skipping PR comment (no repo or gh)" >&2
  else
    cid="$(gh api "repos/$REPO/issues/$PR_NUMBER/comments" --paginate \
            --jq ".[] | select(.body | contains(\"$MARKER\")) | .id" 2>/dev/null | head -n1)"
    if [ -n "$cid" ]; then
      gh api -X PATCH "repos/$REPO/issues/comments/$cid" -F "body=@$COMMENT" >/dev/null \
        && echo "ci_run: updated PR comment $cid" || echo "ci_run: could not update PR comment" >&2
    else
      gh api -X POST "repos/$REPO/issues/$PR_NUMBER/comments" -F "body=@$COMMENT" >/dev/null \
        && echo "ci_run: created PR comment" || echo "ci_run: could not create PR comment" >&2
    fi
  fi
fi

# 7. PR review with inline code comments (pull requests only, never on an engine error). Never changes the exit code.
if [ -n "${PR_NUMBER:-}" ] && [ "$CODE" -ne 2 ] && [ -s "$OUT_DIR/result.json" ]; then
  REPO="${GH_REPO:-${GITHUB_REPOSITORY:-}}"
  if [ -z "$REPO" ] || ! command -v gh >/dev/null 2>&1; then
    echo "ci_run: skipping PR review (no repo or gh)" >&2
  else
    python3 "$ROOT/scripts/ci_review.py" --repo "$REPO" --pr "$PR_NUMBER" --sha "$SHA" \
      --result "$OUT_DIR/result.json" --fix-plan "$OUT_DIR/fix-plan.md" \
      || echo "ci_run: could not post PR review" >&2
  fi
fi

exit "$CODE"
