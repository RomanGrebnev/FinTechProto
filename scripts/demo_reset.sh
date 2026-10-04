#!/usr/bin/env bash
# Reset the replayable demo: close the open demo PR, put demo/base and demo/release back on v0.9.0,
# delete the demo tag v1.0.0-demo. Never touches main, v0.9.0, demo/rc, demo/v1, demo/push1, demo/push2.
# Usage: scripts/demo_reset.sh --yes
set -euo pipefail

BASE_REF="v0.9.0^{commit}"
SHA="$(git rev-parse "$BASE_REF")"
REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

echo "Repo: $REPO"
echo "1. close open PRs demo/release -> demo/base (gh pr close)"
echo "2. git push -f origin $SHA:refs/heads/demo/base"
echo "3. git push -f origin $SHA:refs/heads/demo/release"
echo "4. delete tag v1.0.0-demo (local + remote) if present"
if [ "${1:-}" != "--yes" ]; then
  echo "Dry run. Re-run with --yes to act."
  exit 0
fi

for pr in $(gh pr list --repo "$REPO" --base demo/base --head demo/release --state open --json number --jq '.[].number'); do
  echo "closing PR #$pr"
  gh pr close "$pr" --repo "$REPO" --comment "Demo reset."
done

git push -f origin "$SHA:refs/heads/demo/base"
git push -f origin "$SHA:refs/heads/demo/release"

if git rev-parse -q --verify "refs/tags/v1.0.0-demo" >/dev/null; then
  git tag -d v1.0.0-demo
fi
if git ls-remote --exit-code --tags origin v1.0.0-demo >/dev/null 2>&1; then
  git push origin ":refs/tags/v1.0.0-demo"
fi
echo "Reset done: demo/base and demo/release at ${SHA:0:7} (v0.9.0)."
