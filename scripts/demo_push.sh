#!/usr/bin/env bash
# Force-update the disposable PR head demo/release to demo/step1 (fixes 3-6, red) or demo/step2 (all fixes, green).
# Usage: scripts/demo_push.sh 1|2 --yes
set -euo pipefail

N="${1:-}"
case "$N" in 1|2) ;; *) echo "usage: $0 1|2 --yes" >&2; exit 64 ;; esac
CMD=(git push -f origin "refs/heads/demo/step${N}:refs/heads/demo/release")

echo "Will run: ${CMD[*]}"
if [ "${2:-}" != "--yes" ]; then
  echo "Dry run. Re-run with --yes to act."
  exit 0
fi
git rev-parse --verify -q "refs/heads/demo/step${N}" >/dev/null || { echo "local branch demo/step${N} not found" >&2; exit 1; }
"${CMD[@]}"
echo "demo/release now at $(git rev-parse --short "demo/step${N}") (demo/step${N})"
