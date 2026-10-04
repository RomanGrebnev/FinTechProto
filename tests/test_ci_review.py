"""scripts/ci_review.py: result.json + PR files listing -> review payload; retire earlier reviews. No network."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("ci_review", Path(__file__).resolve().parents[1] / "scripts/ci_review.py")
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)

SHA = "b3e91a4803308f12c12d5e8a2772949de3e87a8e"


def finding(rid, sev, conclusion, evidence, citations=("mifid2-art25-2",), title="Title"):
    return {"id": f"fnd-{rid}", "requirement_id": rid, "severity": sev, "conclusion": conclusion,
            "effective_conclusion": conclusion, "title": title, "evidence": list(evidence),
            "citations": list(citations), "reasoning_summary": f"{rid} is wrong. More detail here."}


def code(path, a, b=None):
    return {"type": "code", "artifact_id": "art-1.0.0-rc.7-code", "path": path, "start_line": a,
            "end_line": b or a, "quote": "x"}


def doc(name, quote):
    return {"type": "document_span", "artifact_id": f"art-1.0.0-rc.7-{name}", "quote": quote}


def result(gate="NOT_READY", findings=None):
    return {"format_version": 1, "status": "ok", "exit_code": 1,
            "release": {"id": "rel-1.0.0-rc.7", "version": "1.0.0-rc.7", "source": "ci", "git_sha": SHA},
            "readiness": {"gate": gate, "counts": {"blockers": 2, "missing_evidence": 0, "high": 1,
                                                    "requirements_total": 10}},
            "findings": findings if findings is not None else FINDINGS}


FINDINGS = [
    finding("FR-SUITABILITY-01", "blocker", "potential_violation",
            [code("frontend/src/pages/Onboarding.jsx", 25, 26), code("frontend/src/pages/Onboarding.jsx", 27),
             code("frontend/src/pages/Onboarding.jsx", 40), code("backend/app/advisor.py", 17, 19)],
            citations=("mifid2-art25-2", "esma-suitability-2023"), title="Suitability assessment is incomplete"),
    finding("FR-CIF-STATUS-01", "blocker", "potential_violation",
            [doc("business-plan", "an information and education service"), doc("business-plan", "second span"),
             doc("PRODUCT_GUIDE", "not financial advice")],
            citations=("cmf-l541-1", "unknown-provision"), title="Product wording contradicts the advice"),
    finding("GDPR-ERASURE-01", "high", "insufficient_evidence",
            [{"type": "missing", "artifact_kind": "privacy_policy"}], citations=("gdpr-art17",)),
    finding("SEC-01", "medium", "satisfied", [code("backend/app/config.py", 3)]),  # closed: never shown
]

# Onboarding.jsx: hunk +20,10 (lines 20..29, one removed line in between); advisor.py not changed in the PR.
FILES = [
    {"filename": "frontend/src/pages/Onboarding.jsx", "status": "modified",
     "patch": "@@ -20,9 +20,10 @@ export default\n ctx20\n ctx21\n-old\n+new22\n ctx23\n ctx24\n+new25\n ctx26\n"
              " ctx27\n ctx28\n ctx29"},
    {"filename": "backend/app/config.py", "status": "modified", "patch": "@@ -1,3 +1,3 @@\n a\n-b\n+c\n d"},
]

FIX_PLAN = """# Compliance fix plan

## 1. FR-SUITABILITY-01: Suitability assessment is incomplete · 🔴 blocker

**Required change**

Add three profile fields to onboarding. Then more.

## Appendix: documents

| # | Requirement | Action | Evidence |
|---|---|---|---|
| A1 | FR-CIF-STATUS-01 · 🔴 blocker | Register as a CIF with ORIAS. Then join. | cif-registration.md |
| A3 | FR-CIF-STATUS-01 | Update the terms. | terms.md |
"""


def build(gate="NOT_READY", findings=None):
    fixes, actions = cr.parse_fix_plan(FIX_PLAN)
    return cr.build_review(result(gate, findings), FILES, fixes, actions, app_url="https://cco.example")


def test_diff_lines_right_side():
    assert cr.diff_lines(FILES[0]["patch"]) == set(range(20, 30))
    assert cr.diff_lines(None) == set()


def test_parse_fix_plan():
    fixes, actions = cr.parse_fix_plan(FIX_PLAN)
    assert fixes == {"FR-SUITABILITY-01": "Add three profile fields to onboarding."}
    assert actions == {"FR-CIF-STATUS-01": "Register as a CIF with ORIAS."}


def test_inline_comments_only_on_diff_lines():
    p = build()
    assert p["event"] == "REQUEST_CHANGES"
    assert p["commit_id"] == SHA
    assert [{k: v for k, v in c.items() if k != "body"} for c in p["comments"]] == [
        {"path": "frontend/src/pages/Onboarding.jsx", "line": 27, "side": "RIGHT", "start_line": 25,
         "start_side": "RIGHT"},
    ]
    body = p["comments"][0]["body"]
    assert "🔴 blocker" in body and "FR-SUITABILITY-01: Suitability assessment is incomplete" in body
    assert "**Why:** FR-SUITABILITY-01 is wrong." in body and "More detail" not in body
    assert "[MiFID II Art. 25(2)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0065)" in body
    assert "**Fix:** Add three profile fields to onboarding." in body


def test_body_tables():
    body = build()["body"]
    assert body.startswith(cr.MARKER)
    assert "❌ NOT READY" in body and "1 inline comment(s)" in body
    code_tbl = body.split("### Findings in unchanged code")[1].split("###")[0]
    assert "`frontend/src/pages/Onboarding.jsx:40`" in code_tbl
    assert "`backend/app/advisor.py:17-19`" in code_tbl
    assert "GDPR" not in code_tbl and "SEC-01" not in body
    docs = body.split("### Documents (reviewed in CCOmmit)")[1]
    assert docs.count("FR-CIF-STATUS-01](https://cco.example/r/rel-1.0.0-rc.7/findings/fnd-FR-CIF-STATUS-01)") == 2
    assert "**business-plan**: “an information and education service”" in docs and "second span" not in docs
    assert "**PRODUCT_GUIDE**" in docs
    assert "| Register as a CIF with ORIAS. |" in docs
    assert "unknown-provision" in docs  # unknown citation ids are kept as text
    assert "🔵 insufficient evidence" in docs and "missing privacy policy" in docs
    assert "[open in CCOmmit](https://cco.example/r/rel-1.0.0-rc.7/overview)" in body


@pytest.mark.parametrize("gate,event", [("NOT_READY", "REQUEST_CHANGES"), ("REVIEW_REQUIRED", "COMMENT"),
                                        ("READY", "COMMENT")])
def test_event_follows_gate(gate, event):
    assert build(gate)["event"] == event


def test_clean_result_has_no_tables():
    p = build("READY", findings=[FINDINGS[3]])
    assert p["comments"] == [] and "###" not in p["body"]


class FakeGh(cr.Gh):
    def __init__(self, reviews=(), files=FILES, fail_request_changes=False):
        self.reviews, self.files, self.fail = list(reviews), files, fail_request_changes
        self.calls: list[tuple[str, str, dict | None]] = []

    def api(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and "/reviews" in path:
            return self.reviews if "page=1" in path else []
        if method == "GET" and "/files" in path:
            return self.files if "page=1" in path else []
        if method == "POST" and payload and payload["event"] == "REQUEST_CHANGES" and self.fail:
            raise RuntimeError("gh api POST failed: Review Can not request changes on your own pull request")
        if method == "POST":
            return {"id": 99, "state": "CHANGES_REQUESTED" if payload["event"] == "REQUEST_CHANGES" else "COMMENTED",
                    "html_url": "https://github.com/o/r/pull/1#pullrequestreview-99"}
        return {}


def writes(gh):
    return [(m, p, d) for m, p, d in gh.calls if m != "GET"]


def run(tmp_path, gh, gate="NOT_READY", extra=()):
    (tmp_path / "result.json").write_text(json.dumps(result(gate)))
    (tmp_path / "fix-plan.md").write_text(FIX_PLAN)
    return cr.main(["--repo", "o/r", "--pr", "1", "--result", str(tmp_path / "result.json"), *extra], gh=gh)


def test_rerun_retires_previous_reviews(tmp_path):
    old = "<!-- ccommit-review -->\n## old"
    gh = FakeGh(reviews=[
        {"id": 1, "state": "CHANGES_REQUESTED", "body": old},
        {"id": 2, "state": "COMMENTED", "body": old},
        {"id": 3, "state": "DISMISSED", "body": old},
        {"id": 4, "state": "COMMENTED", "body": "a human review"},
        {"id": 5, "state": "COMMENTED", "body": "<!-- ccommit-review-superseded -->\n> **Superseded**"},
    ])
    assert run(tmp_path, gh) == 0
    w = writes(gh)
    assert w[0] == ("PUT", "repos/o/r/pulls/1/reviews/1/dismissals",
                    {"message": "Superseded by a newer CCOmmit run.", "event": "DISMISS"})
    assert w[1][:2] == ("PUT", "repos/o/r/pulls/1/reviews/2")
    assert w[1][2]["body"].startswith(cr.SUPERSEDED_MARKER) and cr.MARKER not in w[1][2]["body"]
    assert w[2][:2] == ("POST", "repos/o/r/pulls/1/reviews") and w[2][2]["event"] == "REQUEST_CHANGES"
    assert len(w) == 3


def test_own_pr_falls_back_to_comment(tmp_path):
    gh = FakeGh(fail_request_changes=True)
    assert run(tmp_path, gh) == 0
    posts = [d["event"] for m, _, d in writes(gh) if m == "POST"]
    assert posts == ["REQUEST_CHANGES", "COMMENT"]


def test_dry_run_posts_nothing(tmp_path, capsys):
    gh = FakeGh(reviews=[{"id": 1, "state": "CHANGES_REQUESTED", "body": cr.MARKER}])
    assert run(tmp_path, gh, extra=["--dry-run"]) == 0
    assert writes(gh) == []
    assert json.loads(capsys.readouterr().out)["event"] == "REQUEST_CHANGES"


def test_engine_error_posts_nothing(tmp_path):
    gh = FakeGh()
    (tmp_path / "result.json").write_text(json.dumps({**result(), "status": "engine_error"}))
    assert cr.main(["--repo", "o/r", "--pr", "1", "--result", str(tmp_path / "result.json")], gh=gh) == 0
    assert gh.calls == []
