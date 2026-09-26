"""Regression tests for evidence preparation and the verified analyst flow."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.advisor import decision, evidence
from src.advisor.evidence import build_evidence_bundle
from src.advisor.match_analysis import _mentions
from src.advisor.models import AnalystRequest
from src.advisor.verification import analyze_verified
from src.agent.types import RetrievedSource
from src.discussion.types import (
    DiscussionConfig,
    DiscussionMessage,
    DiscussionResult,
)


NOW = datetime(2030, 1, 10, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolate_analysis_from_research(monkeypatch):
    """These tests cover report generation; research has its own stubbed suite."""
    from src.advisor import match_analysis
    monkeypatch.setattr(decision, "research_evidence", lambda bundle, **_: bundle)
    monkeypatch.setattr(match_analysis, "research_evidence", lambda bundle, **_: bundle)


def source(content, name="https://example.test/arsenal", **metadata):
    return RetrievedSource(content=content, source=name, metadata=metadata)


def message(content, sources=(), timestamp=NOW, sender="agent-a"):
    return DiscussionMessage(
        round_num=1,
        sender_id=sender,
        recipient_ids=["agent-b"],
        content=content,
        timestamp=timestamp.isoformat(),
        sources_used=list(sources),
    )


def discussion(messages):
    return DiscussionResult(
        config=DiscussionConfig(
            discussion_id="advisor-test",
            topic="Should Arsenal buy another attacker?",
            num_rounds=1,
            agent_ids=["agent-a", "agent-b"],
            graph={"agent-a": ["agent-b"]},
            llm_model="test-model",
            llm_temperature=0,
            metadata={"status": "completed"},
        ),
        messages=list(messages),
    )


def decision_request():
    return AnalystRequest(
        discussion_id="advisor-test",
        mode="decision",
        question="Should Arsenal buy a solid attacker?",
    )


def point(text, ref="S001", support="inference"):
    return {"text": text, "evidence_ids": [ref], "support": support}


def balanced_draft():
    return {
        "action": "Buy an attacker",
        "findings": [{
            "claim": "A transfer requires a fee and wages.",
            "evidence_ids": ["S001"],
            "support": "source_backed",
        }],
        "do_it": {
            "option": "Buy an attacker",
            "pros": [point("An extra attacker could improve forward depth.")],
            "cons": [point("A transfer could reduce money available elsewhere.")],
        },
        "do_not_do_it": {
            "option": "Do not buy an attacker",
            "pros": [point("Retaining the money could preserve budget flexibility.")],
            "cons": [point("The existing lack of depth could remain.")],
        },
        "recommendation": {
            "text": "Buy only if the total cost fits the budget.",
            "rationale": "Extra forward depth could help, while cost constrains the choice.",
            "evidence_ids": ["S001"],
            "conditions": ["The total cost fits the available budget."],
            "uncertainty": "The discussion does not quantify the budget or the benefit.",
        },
    }


class DraftClient:
    def __init__(self, draft):
        self.draft = draft
        self.payloads = []

    def generate(self, messages, tools=None):
        assert tools is None
        self.payloads.append(json.loads(messages[1]["content"]))
        return {"content": json.dumps(self.draft)}


class VerifierClient:
    """Return valid quoted checks while recording the actual evidence input."""

    def __init__(self):
        self.payloads = []

    def generate(self, messages, tools=None):
        assert tools is None
        payload = json.loads(messages[1]["content"])
        self.payloads.append(payload)
        registry = {item["id"]: item for item in payload["evidence"]}
        checks = []

        for claim in payload["claims"]:
            role = "supports" if claim["kind"] == "fact" else "premise"
            verdict = "supported" if claim["kind"] == "fact" else "grounded_inference"
            checks.append({
                "claim_id": claim["id"],
                "verdict": verdict,
                "reason": "The cited text supplies the stated fact or conditional premise.",
                "quotes": [{
                    "evidence_id": ref,
                    "quote": registry[ref]["excerpt"],
                    "role": role,
                } for ref in claim["evidence_ids"]],
                "unused_evidence_ids": [],
            })

        return {"content": json.dumps({"checks": checks})}


def test_verified_decision_preserves_action_and_no_action_assessments(monkeypatch):
    text = (
        "Arsenal need forward depth. A transfer requires a fee and wages. "
        "Without buying, Arsenal retain money but have less forward depth."
    )
    saved = discussion([message("Consider both buying and saving.", [source(text)])])
    monkeypatch.setattr(evidence, "get_saved_discussion", lambda _: saved)
    analyst = DraftClient(balanced_draft())
    verifier = VerifierClient()

    result = analyze_verified(
        decision_request(), analyst_client=analyst, verifier_client=verifier,
    )

    assert result.response.status == "complete"
    report = result.response.report
    assert report.do_it.pros and report.do_it.cons
    assert report.do_not_do_it.pros and report.do_not_do_it.cons
    assert report.recommendation.evidence_ids == ["S001"]
    assert report.evidence[-1].excerpt == text
    assert result.verification.evidence[-1].excerpt == text
    assert len(result.verification.checks) == 6
    assert {check.verdict for check in result.verification.checks} == {
        "supported", "grounded_inference",
    }
    assert analyst.payloads[0]["question"] == decision_request().question
    assert verifier.payloads


def test_decision_keeps_qualification_after_character_700(monkeypatch):
    qualification = "However, the proposed transfer is unaffordable without selling players."
    text = "Extra forward depth might help. " + "Context. " * 100 + qualification
    assert text.index(qualification) > 700
    saved = discussion([message("Consider the full source.", [source(text)])])
    monkeypatch.setattr(evidence, "get_saved_discussion", lambda _: saved)
    analyst = DraftClient(balanced_draft())
    verifier = VerifierClient()

    result = analyze_verified(
        decision_request(), analyst_client=analyst, verifier_client=verifier,
    )

    supplied = next(item for item in analyst.payloads[0]["evidence"] if item["id"] == "S001")
    assert supplied["excerpt"] == text
    assert qualification in result.response.report.evidence[-1].excerpt
    assert all(
        qualification in item["excerpt"]
        for payload in verifier.payloads
        for item in payload["evidence"]
        if item["id"] == "S001"
    )


def test_decision_omits_oversized_source_instead_of_truncating(monkeypatch):
    saved = discussion([
        message("The discussion claims buying could help.", [source("x" * 65_000)]),
    ])
    monkeypatch.setattr(evidence, "get_saved_discussion", lambda _: saved)
    analyst = DraftClient({
        "action": "Buy an attacker",
        "findings": [{
            "claim": "The discussion claims buying could help.",
            "evidence_ids": ["M001"],
            "support": "discussion_claim",
        }],
    })

    result = decision.analyze_decision(decision_request(), analyst)

    assert result.status == "partial"
    assert [item["id"] for item in analyst.payloads[0]["evidence"]] == ["M001"]
    assert all(item.kind != "source" for item in result.report.evidence)
    assert any("omitted" in note.casefold() for note in result.missing_information)


@pytest.mark.parametrize("team", ["الأهلي", "الزمالك", "日本"])
def test_team_matching_does_not_match_unrelated_non_latin_text(team):
    assert not _mentions("هذا خبر عن الطقس اليوم", team)
    assert _mentions(f"تقرير عن {team} في المباراة", team)


def test_reader_groups_tracking_aliases_and_preserves_publication_origin():
    text = "Arsenal need more forward depth."
    stamp = (NOW - timedelta(days=1)).isoformat()
    saved = discussion([
        message("First claim", [source(
            text,
            "https://example.test/article?utm_source=agent-a",
            publication_time=stamp,
        )]),
        message("Second claim", [source(
            text,
            "https://example.test/article?utm_source=agent-b",
            published_at=stamp,
        )], sender="agent-b"),
    ])

    bundle = build_evidence_bundle(decision_request(), saved)

    sources = [item for item in bundle.evidence if item.kind == "source"]
    assert len(sources) == 1
    assert list(bundle.source_groups) == ["url:https://example.test/article"]
    assert bundle.source_mentions["S001"] == ["M001", "M002"]
    assert len(bundle.source_aliases["S001"]) == 2
    assert {record.metadata_field for record in bundle.source_publications["S001"]} == {
        "publication_time", "published_at",
    }
    assert bundle.has_sources
    assert bundle.has_time_eligible_sources is None


def test_preview_excludes_late_messages_and_unestablished_source_dates():
    cutoff = NOW
    request = AnalystRequest(
        discussion_id="advisor-test", mode="match_preview", question="Who wins?",
        team_a="Arsenal", team_b="Chelsea", evidence_cutoff=cutoff,
        match_kickoff=cutoff + timedelta(days=1),
    )
    early = cutoff - timedelta(hours=1)
    sources = [
        source("Arsenal have depth.", published_at=(early - timedelta(hours=1)).isoformat()),
        source("Chelsea have depth.", "https://example.test/late", published_at=(cutoff + timedelta(hours=1)).isoformat()),
        source("An undated fact.", "https://example.test/undated", date=early.isoformat()),
        source("A date without timezone.", "https://example.test/naive", published_at="2030-01-09T00:00:00"),
    ]
    saved = discussion([
        message("Available discussion", sources, timestamp=early),
        message("Later result is leaked", timestamp=cutoff + timedelta(hours=1)),
    ])

    bundle = build_evidence_bundle(request, saved)

    assert [item.id for item in bundle.evidence] == ["M001", "S001"]
    assert bundle.excluded_message_count == 1
    assert bundle.excluded_source_count == 3
    assert bundle.has_time_eligible_sources is True
    assert all("Later result" not in item.excerpt for item in bundle.evidence)
    assert bundle.source_publications["S001"][0].metadata_field == "published_at"
