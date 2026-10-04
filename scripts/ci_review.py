#!/usr/bin/env python3
"""Post CCOmmit findings as a GitHub PR review (stdlib only).

Code findings whose line sits in the PR diff become inline comments on that line. Code findings outside the diff
go to a table in the review body, document findings to a separate "Documents" table that points to the CCOmmit app
(counsel reviews those there, not in the code review).

Inputs: out/result.json (CiResult written by `cco audit`), out/fix-plan.md (fix text and legal basis), and the
PR's changed files (`gh api repos/{o}/{r}/pulls/{n}/files`, or a saved listing via --files).

Event: REQUEST_CHANGES when the gate is NOT_READY, COMMENT otherwise. Before posting, earlier CCOmmit reviews
(found by the hidden marker) are retired: dismissed if they requested changes, otherwise their body is marked
superseded. So only the latest CCOmmit review is live.

Usage:
  scripts/ci_review.py --repo OWNER/NAME --pr N [--result out/result.json] [--fix-plan out/fix-plan.md]
                       [--files files.json] [--sha SHA] [--app-url URL] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MARKER = "<!-- ccommit-review -->"
SUPERSEDED_MARKER = "<!-- ccommit-review-superseded -->"
PROBLEMS = ("potential_violation", "insufficient_evidence")
SEV_BADGE = {"blocker": "🔴 blocker", "high": "🟠 high", "medium": "🟡 medium", "low": "⚪ low"}
GATE_TEXT = {"NOT_READY": "❌ NOT READY", "REVIEW_REQUIRED": "⚠️ REVIEW REQUIRED", "READY": "✅ READY"}
DEFAULT_APP_URL = "http://127.0.0.1:20001"

# Official links for the provisions the CCOmmit pack cites (backend cco/legal/seed.py). Unknown ids render as text.
_EURLEX = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:"
_ESMA = ("https://www.esma.europa.eu/sites/default/files/2023-04/"
         "ESMA35-43-3172_Guidelines_on_certain_aspects_of_the_MiFID_II_suitability_requirements.pdf")
CITATION_LINKS: dict[str, tuple[str, str]] = {  # id -> (short label, url)
    "mifid2-art4-1-4": ("MiFID II Art. 4(1)(4)", _EURLEX + "32014L0065"),
    "mifid2-art25-2": ("MiFID II Art. 25(2)", _EURLEX + "32014L0065"),
    "mifid2-art25-6": ("MiFID II Art. 25(6)", _EURLEX + "32014L0065"),
    "delreg565-art54-2": ("Delegated Reg. 2017/565 Art. 54(2)", _EURLEX + "32017R0565"),
    "delreg565-art54-5": ("Delegated Reg. 2017/565 Art. 54(5)", _EURLEX + "32017R0565"),
    "delreg565-art54-7": ("Delegated Reg. 2017/565 Art. 54(7)", _EURLEX + "32017R0565"),
    "gdpr-art13": ("GDPR Art. 13", _EURLEX + "32016R0679"),
    "gdpr-art17": ("GDPR Art. 17", _EURLEX + "32016R0679"),
    "gdpr-art32": ("GDPR Art. 32", _EURLEX + "32016R0679"),
    "aiact-art50": ("AI Act Art. 50", _EURLEX + "32024R1689"),
    "cmf-l541-1": ("Code monétaire et financier Art. L541-1",
                   "https://www.legifrance.gouv.fr/codes/id/LEGITEXT000006072026"),
    "cmf-l546-1": ("Code monétaire et financier Art. L546-1",
                   "https://www.legifrance.gouv.fr/codes/id/LEGITEXT000006072026"),
    "esma-suitability-2023": ("ESMA suitability guidelines (ESMA35-43-3172)", _ESMA),
    "esma-suitability-2023-gg4": ("ESMA suitability guidelines, GG 4 (ESMA35-43-3172)", _ESMA),
    "amf-doc-2006-23": ("AMF DOC-2006-23", "https://www.amf-france.org/fr/reglementation/doctrine/doc-2006-23"),
    "amf-doc-2008-23": ("AMF DOC-2008-23", "https://www.amf-france.org/fr/reglementation/doctrine/doc-2008-23"),
    "cnil-information-notice": ("CNIL: information and transparency",
                                "https://www.cnil.fr/fr/conformite-rgpd-information-des-personnes-et-transparence"),
    "cnil-right-to-erasure": ("CNIL: right to erasure",
                              "https://www.cnil.fr/fr/le-droit-leffacement-supprimer-vos-donnees-en-ligne"),
}


# ------------------------------------------------------------------ pure helpers


def citation_md(cid: str) -> str:
    label, url = CITATION_LINKS.get(cid, (cid, ""))
    return f"[{label}]({url})" if url else label


def one_line(text: str, limit: int = 240) -> str:
    """First sentence of a Markdown text, flattened to one line."""
    flat = " ".join((text or "").split())
    m = re.match(r"(.+?[.!?])(\s|$)", flat)
    out = m.group(1) if m else flat
    return out if len(out) <= limit else out[: limit - 1].rstrip() + "…"


def clip(text: str, limit: int) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def parse_fix_plan(md: str) -> tuple[dict[str, str], dict[str, str]]:
    """(code fixes, document actions): requirement id -> first sentence of its 'Required change' in the fix plan,
    and requirement id -> the first appendix action (documents and organisational steps for the founder)."""
    fixes: dict[str, str] = {}
    for sec in re.split(r"^#{2,3} ", md, flags=re.M)[1:]:
        m = re.match(r"(?:\d+\.\s+)?([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\b", sec)
        body = sec.split("**Required change**", 1)
        if m and len(body) == 2 and m.group(1) not in fixes:
            fixes[m.group(1)] = one_line(body[1].strip())
    actions: dict[str, str] = {}
    for m in re.finditer(r"^\|\s*A\d+\s*\|\s*([A-Z][A-Z0-9-]+)[^|]*\|([^|]*)\|", md, flags=re.M):
        actions.setdefault(m.group(1), one_line(m.group(2).strip()))
    return fixes, actions


def runs(lines: list[int]) -> list[tuple[int, int]]:
    """Sorted line numbers -> [(first, last)] runs of consecutive lines."""
    out: list[tuple[int, int]] = []
    for n in sorted(set(lines)):
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


def doc_name(artifact_id: str, version: str) -> str:
    """art-1.0.0-rc.3-business-plan -> business-plan."""
    prefix = f"art-{version}-"
    return artifact_id[len(prefix):] if artifact_id.startswith(prefix) else artifact_id


def diff_lines(patch: str | None) -> set[int]:
    """RIGHT-side line numbers that a review comment can attach to (added and context lines in the hunks)."""
    lines: set[int] = set()
    if not patch:
        return lines
    n = 0
    for row in patch.split("\n"):
        h = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
        if h:
            n = int(h.group(1))
            continue
        if row.startswith("-") or row.startswith("\\"):
            continue
        if n:
            lines.add(n)
            n += 1
    return lines


def diff_map(files: list[dict]) -> dict[str, set[int]]:
    return {f["filename"]: diff_lines(f.get("patch")) for f in files if f.get("status") != "removed"}


def _problems(result: dict) -> list[dict]:
    sev = {"blocker": 0, "high": 1, "medium": 2, "low": 3}
    fs = [f for f in result.get("findings", []) if f.get("effective_conclusion", f.get("conclusion")) in PROBLEMS]
    return sorted(fs, key=lambda f: (sev.get(f.get("severity"), 9), f.get("requirement_id", "")))


def _badge(f: dict) -> str:
    if f.get("effective_conclusion", f.get("conclusion")) == "insufficient_evidence":
        return "🔵 insufficient evidence"
    return SEV_BADGE.get(f.get("severity"), f.get("severity", ""))


def _laws(f: dict) -> str:
    return " · ".join(citation_md(c) for c in f.get("citations", [])) or "n/a"


def inline_body(f: dict, fix: str | None) -> str:
    lines = [
        f"**{_badge(f)}** · **{f['requirement_id']}: {f.get('title', '')}**",
        "",
        f"**Why:** {one_line(f.get('reasoning_summary', ''))}",
        f"**Law:** {_laws(f)}",
    ]
    if fix:
        lines.append(f"**Fix:** {fix}")
    lines += ["", "<sub>CCOmmit · AI finding, not legal advice · counsel review in CCOmmit</sub>"]
    return "\n".join(lines)


def _app_link(app_url: str, result: dict, finding_id: str | None = None) -> str:
    rid = result.get("release", {}).get("id")
    if not rid:
        return app_url
    tail = f"findings/{finding_id}" if finding_id else "overview"
    return f"{app_url.rstrip('/')}/r/{rid}/{tail}"


def build_review(result: dict, files: list[dict], fixes: dict[str, str], actions: dict[str, str] | None = None, *,
                 app_url: str = DEFAULT_APP_URL, sha: str | None = None) -> dict:
    """The POST /pulls/{n}/reviews payload. Pure: no I/O.

    Per finding and file, cited lines inside the diff are merged into runs of consecutive lines and get one inline
    comment each (multi-line when the run spans several lines). Cited lines outside the diff go to one table row
    per file; document spans to one row per document."""
    actions = actions or {}
    in_diff = diff_map(files)
    rel = result.get("release", {})
    comments: list[dict] = []
    unchanged: list[tuple[dict, str]] = []  # (finding, location)
    documents: list[tuple[dict, str]] = []

    for f in _problems(result):
        refs = f.get("evidence", [])
        by_path: dict[str, list[int]] = {}
        for r in (r for r in refs if r.get("type") == "code"):
            by_path.setdefault(r["path"], []).extend(range(r["start_line"], max(r["start_line"], r["end_line"]) + 1))
        for path, lines in by_path.items():
            hit = [n for n in lines if n in in_diff.get(path, set())]
            miss = [n for n in lines if n not in in_diff.get(path, set())]
            for lo, hi in runs(hit):
                c = {"path": path, "line": hi, "side": "RIGHT",
                     "body": inline_body(f, fixes.get(f["requirement_id"]))}
                if lo != hi:
                    c.update(start_line=lo, start_side="RIGHT")
                comments.append(c)
            if miss:
                spans = ", ".join(str(lo) if lo == hi else f"{lo}-{hi}" for lo, hi in runs(miss))
                unchanged.append((f, f"`{path}:{spans}`"))
        docs: dict[str, str] = {}
        for r in (r for r in refs if r.get("type") == "document_span"):
            docs.setdefault(doc_name(r.get("artifact_id", ""), rel.get("version", "")), r.get("quote", ""))
        for name, quote in docs.items():
            documents.append((f, f"**{name}**: “{clip(quote, 100)}”"))
        for r in (r for r in refs if r.get("type") == "missing"):
            kind = r.get("artifact_kind", "evidence")
            (unchanged if kind == "code_repo" else documents).append((f, f"missing {kind.replace('_', ' ')}"))
        if not refs:
            documents.append((f, "no evidence found"))

    rd = result.get("readiness", {})
    gate = rd.get("gate", "REVIEW_REQUIRED")
    c = rd.get("counts", {})
    body = [
        MARKER,
        f"## CCOmmit compliance review · {rel.get('version', '?')} · {GATE_TEXT.get(gate, gate)}",
        "",
        f"{c.get('blockers', 0)} blockers · {c.get('missing_evidence', 0)} missing evidence · {c.get('high', 0)} high"
        f" · {c.get('requirements_total', 0)} requirements evaluated · AI assessment, not legal advice.",
        "",
        f"**{len(comments)} inline comment(s)** on changed code.",
    ]
    if unchanged:
        body += ["", "### Findings in unchanged code", "", "| Severity | Requirement | Location | Law |",
                 "|---|---|---|---|"]
        body += [f"| {_badge(f)} | {f['requirement_id']}: {cell(f.get('title', ''))} | {loc} | {_laws(f)} |"
                 for f, loc in unchanged]
    if documents:
        body += ["", "### Documents (reviewed in CCOmmit)", "",
                 "Business plan, terms, privacy policy and CIF findings are reviewed by counsel in CCOmmit, "
                 "not in this code review.", "",
                 "| Severity | Requirement | Evidence | Law | Action |", "|---|---|---|---|---|"]
        body += [f"| {_badge(f)} | [{f['requirement_id']}]({_app_link(app_url, result, f.get('id'))}): "
                 f"{cell(f.get('title', ''))} | {cell(loc)} | {_laws(f)} | {cell(actions.get(f['requirement_id'], ''))} |"
                 for f, loc in documents]
    body += ["", f"→ Full assessment: [open in CCOmmit]({_app_link(app_url, result)}) · "
                 "fix plan: artifact `ccommit-result/fix-plan.md`"]

    payload = {"body": "\n".join(body) + "\n",
               "event": "REQUEST_CHANGES" if gate == "NOT_READY" else "COMMENT",
               "comments": comments}
    sha = sha or rel.get("git_sha")
    if sha:
        payload["commit_id"] = sha
    return payload


# ------------------------------------------------------------------ GitHub


class Gh:
    """Thin `gh api` wrapper; tests replace it with a fake that records calls."""

    def api(self, method: str, path: str, payload: dict | None = None) -> object:
        cmd = ["gh", "api", "-X", method, path, "-H", "Accept: application/vnd.github+json"]
        if payload is not None:
            cmd += ["--input", "-"]
        p = subprocess.run(cmd, input=json.dumps(payload) if payload is not None else None,
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"gh api {method} {path} failed: {(p.stderr + ' ' + p.stdout).strip()[:800]}")
        return json.loads(p.stdout) if p.stdout.strip() else None

    def pages(self, path: str) -> list:
        out: list = []
        page = 1
        while True:
            sep = "&" if "?" in path else "?"
            chunk = self.api("GET", f"{path}{sep}per_page=100&page={page}") or []
            out += chunk
            if len(chunk) < 100:
                return out
            page += 1


def retire_previous(gh: Gh, repo: str, pr: int) -> list[str]:
    """Dismiss earlier CCOmmit reviews that requested changes; mark the others superseded. Returns actions."""
    done = []
    for r in gh.pages(f"repos/{repo}/pulls/{pr}/reviews"):
        body = r.get("body") or ""
        if MARKER not in body:
            continue
        if r.get("state") == "CHANGES_REQUESTED":
            gh.api("PUT", f"repos/{repo}/pulls/{pr}/reviews/{r['id']}/dismissals",
                   {"message": "Superseded by a newer CCOmmit run.", "event": "DISMISS"})
            done.append(f"dismissed {r['id']}")
        elif r.get("state") == "COMMENTED":
            new = SUPERSEDED_MARKER + "\n> **Superseded** by a newer CCOmmit run.\n\n" + body.replace(MARKER, "")
            gh.api("PUT", f"repos/{repo}/pulls/{pr}/reviews/{r['id']}", {"body": new})
            done.append(f"superseded {r['id']}")
    return done


def post_review(gh: Gh, repo: str, pr: int, payload: dict) -> dict:
    retire_previous(gh, repo, pr)
    try:
        return gh.api("POST", f"repos/{repo}/pulls/{pr}/reviews", payload)  # type: ignore[return-value]
    except RuntimeError as e:
        # GitHub refuses REQUEST_CHANGES on your own PR (local runs as the PR author). Keep the verdict in the body.
        if payload["event"] == "REQUEST_CHANGES" and "own pull request" in str(e):
            return gh.api("POST", f"repos/{repo}/pulls/{pr}/reviews",  # type: ignore[return-value]
                          {**payload, "event": "COMMENT"})
        raise


def main(argv: list[str] | None = None, gh: Gh | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--pr", type=int, default=int(os.environ["PR_NUMBER"]) if os.environ.get("PR_NUMBER") else None)
    ap.add_argument("--result", default="out/result.json")
    ap.add_argument("--fix-plan", default=None, help="default: fix-plan.md next to the result")
    ap.add_argument("--files", default=None, help="saved PR files listing (JSON); default: fetched with gh")
    ap.add_argument("--sha", default=os.environ.get("SHA"))
    ap.add_argument("--app-url", default=os.environ.get("CCOMMIT_APP_URL") or DEFAULT_APP_URL)
    ap.add_argument("--dry-run", action="store_true", help="print the review payload, post nothing")
    a = ap.parse_args(argv)
    gh = gh or Gh()

    result = json.loads(Path(a.result).read_text("utf-8"))
    if result.get("status") != "ok":
        print("ci_review: engine error result, no review posted", file=sys.stderr)
        return 0
    fp = Path(a.fix_plan) if a.fix_plan else Path(a.result).with_name("fix-plan.md")
    fixes, actions = parse_fix_plan(fp.read_text("utf-8")) if fp.is_file() else ({}, {})
    if a.files:
        files = json.loads(Path(a.files).read_text("utf-8"))
    else:
        if not (a.repo and a.pr):
            ap.error("--repo and --pr are required to fetch the PR files (or pass --files)")
        files = gh.pages(f"repos/{a.repo}/pulls/{a.pr}/files")

    payload = build_review(result, files, fixes, actions, app_url=a.app_url, sha=a.sha)
    if a.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if not (a.repo and a.pr):
        ap.error("--repo and --pr are required to post")
    r = post_review(gh, a.repo, a.pr, payload)
    print(f"ci_review: posted {r.get('state', '?')} review {r.get('html_url', '')} "
          f"with {len(payload['comments'])} inline comment(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
