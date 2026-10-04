# G3: live CI demo, exact commands

Repo: `RomanGrebnev/FinTechProto` (private). CCOmmit: `sri-ram-swaminathan/llm_law_hackathon`, branch `ft/cco-mvp`.
Run everything from a FinTechProto clone. Stable refs, never rewritten: `v0.9.0`, `demo/rc`, `demo/v1`, `demo/push1`, `demo/push2`.
The live PR uses only `demo/base` (base) and `demo/release` (head). `main` is never touched.

## 0. One-time setup

```bash
R=RomanGrebnev/FinTechProto

# Actions must be enabled for the repo (Settings > Actions > General > Allow all actions). Check:
gh api repos/$R/actions/permissions --jq .enabled

# Secrets. MISTRAL_API_KEY is read from CCOmmit's .env without printing it.
grep '^MISTRAL_API_KEY=' ~/Documents/projects/llm_law_hackathon/.env | cut -d= -f2- | tr -d '"' | gh secret set MISTRAL_API_KEY --repo $R
# CCOMMIT_REPO_TOKEN: fine-grained PAT, repo sri-ram-swaminathan/llm_law_hackathon, permission Contents: read-only.
gh secret set CCOMMIT_REPO_TOKEN --repo $R        # paste the token when prompted
gh secret list --repo $R
```

Push the stable refs and seed the demo branches (once):

```bash
git push origin v0.9.0 demo/rc demo/v1 demo/push1 demo/push2
git push origin v0.9.0^{commit}:refs/heads/demo/base v0.9.0^{commit}:refs/heads/demo/release
git fetch origin demo/push1:demo/push1 demo/push2:demo/push2 2>/dev/null || true   # local copies for demo_push.sh
```

Branch protection on `demo/base`: `compliance` is a required check; force-push stays allowed so the reset works;
admins are not enforced, so you can always reset.

```bash
gh api -X PUT repos/$R/branches/demo/base/protection --input - <<'EOF'
{
  "required_status_checks": {"strict": false, "contexts": ["compliance"]},
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": true,
  "allow_deletions": false
}
EOF
```

Optional, for `main`: the same call on `branches/main/protection` (without `allow_force_pushes`). The demo never touches `main`.

Sanity check of the workflow file on a demo ref:

```bash
git show demo/push1:.github/workflows/compliance.yml | grep -E 'pull_request:|pull_request_target|tags:|workflow_dispatch|contents: read|pull-requests: write'
# expect pull_request, tags, workflow_dispatch, both permissions, and NO pull_request_target
```

## 1. Reset to the starting state (also the way to replay)

```bash
scripts/demo_reset.sh            # prints what it will do
scripts/demo_reset.sh --yes      # closes the demo PR, demo/base + demo/release -> v0.9.0, deletes tag v1.0.0-demo
```

## 2. Open the PR

demo/release and demo/base are both at v0.9.0, so GitHub refuses a PR with no diff. Push 1 first, then open it:

```bash
scripts/demo_push.sh 1 --yes
gh pr create --repo $R --base demo/base --head demo/release \
  --title "Release 1.0.0" --body "Wealthpilot 1.0.0 release candidate."
```

## 3. Push 1: red

The `compliance` check starts on the PR (about 5 to 15 minutes with the live model). Expected: failure, one PR comment
(marker `<!-- ccommit-check -->`) that lists the two blockers W1 and W2, and one PR review (see "PR review" below).

```bash
gh pr checks --repo $R --watch demo/release
gh pr view --repo $R demo/release --comments | head -20
```

## 4. Push 2: green

Push 2 adds the suitability and CIF fixes, `compliance/cif-registration.md`, and `compliance/cco-baseline.json`
(counsel's W8 "not applicable" review, exported with `cco export-baseline 0.9.0`).
The same PR comment is edited in place (no second comment). A new PR review is posted (COMMENT) and the push-1 review
is dismissed, so only the latest CCOmmit review is live.

```bash
scripts/demo_push.sh 2 --yes
gh pr checks --repo $R --watch demo/release
```

## 5. Merge, tag

```bash
gh pr merge --repo $R demo/release --merge
git fetch origin demo/base
git tag v1.0.0-demo origin/demo/base
git push origin v1.0.0-demo          # runs the check again on the tag (push of tags v*)
```

## 6. Import the result into the local CCOmmit

```bash
RUN=$(gh run list --repo $R --workflow compliance --limit 1 --json databaseId --jq '.[0].databaseId')
rm -rf /tmp/ccr && gh run download $RUN --repo $R -n ccommit-result -D /tmp/ccr
cd ~/Documents/projects/llm_law_hackathon/backend
uv run cco import /tmp/ccr/result.json
```

(`cco import` also accepts the artifact zip. The UI's "Import CI run" button takes the same file.)
Importing the same release twice fails with "already exists"; the PR run is named `1.0.0-rc.<run number>`.

## 7. Reset and replay

```bash
cd <FinTechProto clone>
scripts/demo_reset.sh --yes
scripts/demo_push.sh 1 --yes
gh pr create --repo $R --base demo/base --head demo/release --title "Release 1.0.0" --body "Wealthpilot 1.0.0 release candidate."
# red -> scripts/demo_push.sh 2 --yes -> green -> merge -> tag, as above
```

The reset closes the PR, so a replay starts with no reviews; a new PR gets a fresh review on its first run.

## PR review

On pull requests `ci_run.sh` runs `scripts/ci_review.py` after the audit (stdlib Python, uses `gh`). It reads
`out/result.json`, `out/fix-plan.md` and the PR's files (`gh api repos/{o}/{r}/pulls/{n}/files`) and posts one review:

- **Inline comments** on the code lines that findings cite (`potential_violation` / `insufficient_evidence`), when the
  line is in a diff hunk on the right side. Consecutive cited lines become one multi-line comment. Each comment
  carries the severity badge, the requirement, a one-line why, the law with its official link, and the fix.
- **Findings in unchanged code**: cited lines outside the diff, as a table in the review body.
- **Documents (reviewed in CCOmmit)**: business plan, terms, privacy policy and CIF findings, as a table with links to
  the finding in the CCOmmit app (`CCOMMIT_APP_URL`, repo variable; default `http://127.0.0.1:20001`).
- **Event**: `REQUEST_CHANGES` when the gate is NOT_READY, `COMMENT` otherwise. GitHub refuses REQUEST_CHANGES on
  your own PR (a local run as the PR author); the script then posts a COMMENT with the same body.
- **Re-runs**: earlier CCOmmit reviews (marker `<!-- ccommit-review -->`) are dismissed if they requested changes,
  otherwise their body is marked superseded. Only the latest review is live.

Preview without posting, or post from a local audit:

```bash
python3 scripts/ci_review.py --repo $R --pr 1 --result /tmp/ccommit-out/result.json --dry-run
python3 scripts/ci_review.py --repo $R --pr 1 --result /tmp/ccommit-out/result.json
```

A local result for the push-1 code (no runner needed):

```bash
B=$(mktemp -d); git archive demo/push1 | tar -x -C $B
cd ~/Documents/projects/llm_law_hackathon && set -a && . ./.env && set +a && cd backend
uv run cco audit --bundle $B --version 1.0.0 --sha $(git -C <FinTechProto clone> rev-parse demo/push1) \
  --out /tmp/ccommit-out --pr 1 --run-number 1 --branch demo/release
```

## How the demo refs were built

- `demo/push1` = `v0.9.0` + workflow and scripts + T07 commits (`26d8ff4 a9fb7c0 c8d4217 9fc14be cdf9a0f`)
  + `privacy-policy.md` and `terms.md` taken from `dbd5d3c` + `version` = 1.0.0.
- `demo/push2` = `demo/push1` + T13 commits (`513fd0f 5cc9009`; `0042de0` is empty because `version` is already 1.0.0)
  + `cif-registration.md` from `dbd5d3c` + `compliance/cco-baseline.json`.
- Splitting `dbd5d3c`: `git checkout dbd5d3c -- compliance/privacy-policy.md compliance/terms.md` for push 1,
  `git checkout dbd5d3c -- compliance/cif-registration.md` for push 2.

## Run the check locally

```bash
CCOMMIT_DIR=~/Documents/projects/llm_law_hackathon OUT_DIR=/tmp/ccommit-out bash scripts/ci_run.sh
echo $?     # 1 NOT_READY, 0 READY or REVIEW_REQUIRED, 2 engine error
```
