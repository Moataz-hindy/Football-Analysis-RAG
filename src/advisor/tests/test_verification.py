"""Verifier contracts: auditable quotations, safe pruning and prediction gating."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.advisor.models import (
    AnalystRequest,
    AnalystResponse,
    DecisionReport,
    EvidenceItem,
    Finding,
    MatchPreviewReport,
    OptionAssessment,
    Prediction,
    Recommendation,
    ResearchAttempt,
    ResearchTrace,
    SupportedPoint,
    TeamPlan,
)
from src.advisor.verification import CitedClaim, analyze_verified, verify_claims, verify_response


class FakeVerifier:
    """Respond from supplied excerpts only, with optional malformed checks."""

    def __init__(self, change=None, fail_on=None):
        self.change = change
        self.fail_on = fail_on
        self.payloads = []

    def generate(self, messages, tools=None):
        assert tools is None
        payload = json.loads(messages[1]["content"])
        self.payloads.append(payload)
        if len(self.payloads) == self.fail_on:
            raise RuntimeError("Simulated provider failure")
        registry = {item["id"]: item for item in payload["evidence"]}
        checks = []
        for claim in payload["claims"]:
            verdict, role = {
                "fact": ("supported", "supports"),
                "inference": ("grounded_inference", "premise"),
                "reported_claim": ("discussion_only", "expresses"),
                "disputed": ("disputed", "supports"),
            }[claim["kind"]]
            check = {
                "claim_id": claim["id"],
                "verdict": verdict,
                "reason": "The quoted excerpt supplies the stated support.",
                "quotes": [{
                    "evidence_id": ref,
                    "quote": registry[ref]["excerpt"],
                    "role": role,
                } for ref in claim["evidence_ids"]],
                "unused_evidence_ids": [],
            }
            if self.change is not None:
                self.change(claim, check)
            checks.append(check)
        return {"content": json.dumps({"checks": checks})}


def source(ref="S1", excerpt="Arsenal have limited forward depth.", **kwargs):
    return EvidenceItem(
        id=ref, kind="source", message_ref="M1", excerpt=excerpt,
        source=f"https://example.test/{ref}", **kwargs,
    )


def claim(refs=("S1",), kind="fact", identifier="claim-1"):
    return CitedClaim(
        id=identifier, text="Arsenal have limited forward depth.",
        kind=kind, evidence_ids=list(refs),
    )


def response(findings=None, evidence=None):
    return AnalystResponse(
        request=AnalystRequest(
            discussion_id="verifier-test", mode="decision",
            question="Should Arsenal buy an attacker?",
        ),
        status="partial", snapshot_sha256="a" * 64,
        missing_information=["The budget and complete option assessments are missing."],
        report=DecisionReport(
            action="Buy an attacker", evidence=evidence or [source()],
            findings=findings or [Finding(
                claim="Arsenal have limited forward depth.",
                support="source_backed", evidence_ids=["S1"],
            )],
        ),
    )


@pytest.mark.parametrize("malformation", [
    "invented_quote", "invented_evidence", "missing_citation", "quoted_and_unused",
])
def test_invalid_quotation_or_citation_accounting_fails_closed(malformation):
    def change(_, check):
        if malformation == "invented_quote":
            check["quotes"][0]["quote"] = "Arsenal scored one hundred goals."
        elif malformation == "invented_evidence":
            check["quotes"][0]["evidence_id"] = "UNSUPPLIED"
        elif malformation == "missing_citation":
            check["quotes"] = []
        else:
            check["unused_evidence_ids"] = ["S1"]

    audit = verify_claims([claim()], [source()], FakeVerifier(change))
    assert audit.error
    assert audit.checks[0].verdict == "unassessed"
    assert not audit.checks[0].quotes


def test_quote_can_normalize_whitespace_without_changing_words():
    def change(_, check):
        check["quotes"][0]["quote"] = "Arsenal have limited forward depth."

    audit = verify_claims(
        [claim()], [source(excerpt="Arsenal\n have  limited forward depth.")],
        FakeVerifier(change),
    )
    assert audit.error is None
    assert audit.checks[0].verdict == "supported"


@pytest.mark.parametrize("returned_ids", [[], ["invented"], ["claim-1", "claim-1"]])
def test_missing_invented_or_duplicate_claim_checks_are_rejected(returned_ids):
    class WrongClaimClient:
        def generate(self, messages, tools=None):
            return {"content": json.dumps({"checks": [{
                "claim_id": ref, "verdict": "unassessed",
                "reason": "No assessment available.",
            } for ref in returned_ids]})}

    audit = verify_claims([claim()], [source()], WrongClaimClient())
    assert audit.error
    assert [check.claim_id for check in audit.checks] == ["claim-1"]
    assert audit.checks[0].verdict == "unassessed"


def test_unknown_input_citation_is_rejected_before_calling_the_model():
    client = FakeVerifier()
    with pytest.raises(ValueError, match="unknown evidence"):
        verify_claims([claim(refs=("missing",))], [source()], client)
    assert not client.payloads


def test_message_cannot_authenticate_a_factual_claim():
    message = EvidenceItem(
        id="M1", kind="message", message_ref="M1",
        excerpt="Arsenal have limited forward depth.",
    )
    audit = verify_claims([claim(refs=("M1",))], [message], FakeVerifier())
    assert audit.error
    assert audit.checks[0].verdict == "unassessed"


def test_reported_message_claim_stays_labeled_as_discussion_only():
    message = EvidenceItem(
        id="M1", kind="message", message_ref="M1",
        excerpt="Arsenal have limited forward depth.",
    )
    original = response(findings=[Finding(
        claim="The participant reported limited forward depth.",
        support="discussion_claim", evidence_ids=["M1"],
    )], evidence=[message])
    checked = verify_response(original, FakeVerifier())
    assert checked.response.status == "partial"
    assert checked.response.report.findings[0].support == "discussion_claim"
    assert checked.verification.checks[0].verdict == "discussion_only"


def test_all_unsupported_claims_are_removed_but_audit_keeps_original_evidence():
    def unsupported(_, check):
        check.update(verdict="unsupported", quotes=[], unused_evidence_ids=["S1"])

    original = response()
    before = original.model_dump(mode="json")
    checked = verify_response(original, FakeVerifier(unsupported))
    assert checked.response.status == "insufficient_evidence"
    assert checked.response.report is None
    assert checked.verification.evidence == original.report.evidence
    assert checked.verification.claims[0].id == "/findings/0"
    assert original.model_dump(mode="json") == before


def test_unused_refs_are_trimmed_without_mutating_original_report():
    original = response(findings=[Finding(
        claim="Arsenal have limited forward depth.", support="source_backed",
        evidence_ids=["S1", "S2"],
    )], evidence=[source(), source("S2", "The stadium opened in 2006.")])
    before = original.model_dump(mode="json")

    def remove_unused(_, check):
        check["quotes"] = [q for q in check["quotes"] if q["evidence_id"] == "S1"]
        check["unused_evidence_ids"] = ["S2"]

    checked = verify_response(original, FakeVerifier(remove_unused))
    assert checked.response.report.findings[0].evidence_ids == ["S1"]
    assert checked.verification.checks[0].unused_evidence_ids == ["S2"]
    assert original.model_dump(mode="json") == before


def test_provider_failure_returns_failed_without_fabricated_report():
    original = response()
    checked = verify_response(original, FakeVerifier(fail_on=1))
    assert checked.response.status == "failed"
    assert checked.response.error
    assert checked.response.report is None
    assert checked.verification.error
    assert checked.verification.evidence == original.report.evidence


def test_later_batch_failure_preserves_only_successfully_checked_claims():
    findings = [Finding(
        claim=f"Depth observation {number}", evidence_ids=["S1"],
        support="source_backed",
    ) for number in range(7)]
    checked = verify_response(response(findings=findings), FakeVerifier(fail_on=2))
    assert checked.response.status == "partial"
    assert len(checked.response.report.findings) == 6
    assert checked.verification.error
    assert checked.verification.checks[-1].verdict == "unassessed"


def test_middle_batch_provider_failure_does_not_block_later_independent_claims():
    claims = [claim(identifier=f"claim-{number}") for number in range(13)]
    client = FakeVerifier(fail_on=2)
    audit = verify_claims(claims, [source()], client)
    assert len(client.payloads) == 3
    assert [check.verdict for check in audit.checks] == (
        ["supported"] * 6 + ["unassessed"] * 6 + ["supported"]
    )
    assert "1 of 3 batches" in audit.error
    assert audit.checks[-1].quotes[0].quote == source().excerpt


def test_invalid_structured_output_is_retried_with_a_small_fixed_budget():
    client = FakeVerifier()

    def wrong_first_quote(_, check):
        if len(client.payloads) == 1:
            check["quotes"][0]["quote"] = "An invented first-attempt quotation."

    client.change = wrong_first_quote
    audit = verify_claims([claim()], [source()], client)
    assert len(client.payloads) == 2
    assert audit.error is None
    assert audit.checks[0].verdict == "supported"


def test_persistently_invalid_batch_does_not_block_later_independent_claims():
    client = FakeVerifier()

    def invalid_middle_batch(item, check):
        if item["id"] == "claim-6":
            check["quotes"][0]["quote"] = "An invented quotation."

    client.change = invalid_middle_batch
    audit = verify_claims(
        [claim(identifier=f"claim-{number}") for number in range(13)],
        [source()], client,
    )
    assert len(client.payloads) == 4  # First, two middle attempts, then last.
    assert [check.verdict for check in audit.checks] == (
        ["supported"] * 6 + ["unassessed"] + ["supported"] * 6
    )
    assert [item["id"] for item in client.payloads[2]["claims"]] == ["claim-6"]
    assert audit.error


@pytest.mark.parametrize("malformation", ["quote", "citation", "schema"])
def test_one_invalid_check_cannot_discard_a_valid_check_from_the_same_batch(malformation):
    def change(item, check):
        if item["id"] != "invalid":
            return
        if malformation == "quote":
            check["quotes"][0]["quote"] = "An invented quotation."
        elif malformation == "citation":
            check["quotes"][0]["evidence_id"] = "invented-evidence"
        else:
            check.pop("reason")

    client = FakeVerifier(change)
    audit = verify_claims(
        [claim(identifier="invalid"), claim(identifier="valid")], [source()], client,
    )
    assert [check.verdict for check in audit.checks] == ["unassessed", "supported"]
    assert audit.checks[1].quotes[0].quote == source().excerpt
    assert audit.error and "1 claim remains unassessed" in audit.error
    assert len(client.payloads) == 2
    assert [item["id"] for item in client.payloads[1]["claims"]] == ["invalid"]
    assert set(client.payloads[1]["previous_validation_errors"]) == {"invalid"}


def test_retry_can_recover_distinct_validation_failures_without_rechecking_valid_claims():
    client = FakeVerifier()

    def change(item, check):
        if len(client.payloads) != 1:
            return
        if item["id"] == "bad-quote":
            check["quotes"][0]["quote"] = "An invented quotation."
        elif item["id"] == "bad-citation":
            check["unused_evidence_ids"] = ["S1"]

    client.change = change
    audit = verify_claims(
        [claim(identifier=identifier) for identifier in ["bad-quote", "bad-citation", "valid"]],
        [source()], client,
    )
    assert audit.error is None
    assert [check.verdict for check in audit.checks] == ["supported"] * 3
    assert len(client.payloads) == 2
    retry = client.payloads[1]
    assert [item["id"] for item in retry["claims"]] == ["bad-quote", "bad-citation"]
    assert "does not occur" in retry["previous_validation_errors"]["bad-quote"]
    assert "exact citation set" in retry["previous_validation_errors"]["bad-citation"]
    assert "S1" in retry["previous_validation_errors"]["bad-citation"]


def test_unresolved_claim_reason_records_the_final_specific_validation_failure():
    client = FakeVerifier()

    def change(item, check):
        if item["id"] == "valid":
            return
        if len(client.payloads) == 1:
            check["quotes"][0]["quote"] = "An invented quotation."
        else:
            check["quotes"] = []

    client.change = change
    audit = verify_claims(
        [claim(identifier="invalid"), claim(identifier="valid")], [source()], client,
    )
    assert audit.checks[0].verdict == "unassessed"
    assert "exact citation set" in audit.checks[0].reason
    assert audit.checks[1].verdict == "supported"
    assert audit.error


@pytest.mark.parametrize("retry_failure", ["provider", "malformed_json"])
def test_retry_failure_affects_only_unresolved_claims(retry_failure):
    class RetryFailureVerifier(FakeVerifier):
        def generate(self, messages, tools=None):
            answer = super().generate(messages, tools)
            if len(self.payloads) == 2 and retry_failure == "malformed_json":
                return {"content": "not JSON"}
            return answer

    def bad_quote(item, check):
        if item["id"] == "invalid":
            check["quotes"][0]["quote"] = "An invented quotation."

    client = RetryFailureVerifier(bad_quote, fail_on=2 if retry_failure == "provider" else None)
    audit = verify_claims(
        [claim(identifier="invalid"), claim(identifier="valid")], [source()], client,
    )
    assert [check.verdict for check in audit.checks] == ["unassessed", "supported"]
    assert audit.error
    assert len(client.payloads) == 2
    assert [item["id"] for item in client.payloads[1]["claims"]] == ["invalid"]


def test_duplicate_check_invalidates_only_its_claim_and_never_enters_the_audit():
    class DuplicateCheckVerifier(FakeVerifier):
        def generate(self, messages, tools=None):
            answer = super().generate(messages, tools)
            result = json.loads(answer["content"])
            result["checks"].extend(
                check for check in list(result["checks"]) if check["claim_id"] == "duplicate"
            )
            return {"content": json.dumps(result)}

    client = DuplicateCheckVerifier()
    audit = verify_claims(
        [claim(identifier="duplicate"), claim(identifier="valid")], [source()], client,
    )
    assert [check.verdict for check in audit.checks] == ["unassessed", "supported"]
    assert [check.claim_id for check in audit.checks] == ["duplicate", "valid"]
    assert [item["id"] for item in client.payloads[1]["claims"]] == ["duplicate"]


def complete_decision_response():
    original = response()
    point = SupportedPoint(
        text="Depth could improve if an attacker is acquired.",
        support="inference", evidence_ids=["S1"],
    )
    original.report.do_it = OptionAssessment(
        option="Acquire an attacker", pros=[point], cons=[point],
    )
    original.report.do_not_do_it = OptionAssessment(
        option="Keep the current squad", pros=[point], cons=[point],
    )
    original.report.recommendation = Recommendation(
        text="Consider an affordable attacker.",
        rationale="Limited depth is a reason to examine the available options.",
        evidence_ids=["S1"], uncertainty="The price is unknown.",
    )
    data = original.model_dump()
    data.update(status="complete", missing_information=[])
    return AnalystResponse.model_validate(data)


@pytest.mark.parametrize("unsupported_options", [
    {"do_it"}, {"do_not_do_it"}, {"do_it", "do_not_do_it"},
])
def test_decision_recommendation_is_withheld_when_an_option_has_no_retained_points(unsupported_options):
    original = complete_decision_response()
    before = original.model_dump(mode="json")

    def unsupported_option(item, check):
        if any(item["id"].startswith(f"/{option}/") for option in unsupported_options):
            check.update(verdict="unsupported", quotes=[], unused_evidence_ids=["S1"])

    checked = verify_response(original, FakeVerifier(unsupported_option))
    assert checked.response.status == "partial"
    assert checked.response.report.recommendation is None
    assert checked.response.report.findings
    assert any("recommendation was withheld" in note for note in checked.response.missing_information)
    assert original.model_dump(mode="json") == before


def test_missing_pro_or_con_downgrades_complete_decision_without_fabricating_replacement():
    def unsupported_pro(item, check):
        if item["id"] == "/do_it/pros/0":
            check.update(verdict="unsupported", quotes=[], unused_evidence_ids=["S1"])

    checked = verify_response(complete_decision_response(), FakeVerifier(unsupported_pro))
    assert checked.response.status == "partial"
    assert checked.response.report.do_it.pros == []
    assert checked.response.report.do_it.cons
    assert checked.response.report.recommendation is not None
    assert any("decision assessment is incomplete" in note for note in checked.response.missing_information)


def test_recommendation_alone_cannot_stand_in_for_empty_decision_assessments():
    original = response()
    original.report.findings = []
    original.report.recommendation = complete_decision_response().report.recommendation
    checked = verify_response(original, FakeVerifier())
    assert checked.response.status == "insufficient_evidence"
    assert checked.response.report is None
    assert checked.verification.checks[0].verdict == "grounded_inference"
    assert any("recommendation was withheld" in note for note in checked.response.missing_information)


@pytest.mark.parametrize("initial_support,retained", [
    ("disputed", True), ("source_backed", False),
])
def test_disagreement_is_retained_only_as_an_explicit_dispute(initial_support, retained):
    evidence = [source(), source("S2", "Arsenal have adequate forward depth.")]
    original = response(findings=[Finding(
        claim="The assessments disagree about forward depth.",
        support=initial_support, evidence_ids=["S1", "S2"],
    )], evidence=evidence)

    def dispute(_, check):
        check["verdict"] = "disputed"
        check["quotes"][1]["role"] = "contradicts"

    checked = verify_response(original, FakeVerifier(dispute))
    assert checked.verification.checks[0].verdict == "disputed"
    if retained:
        assert checked.response.report.findings[0].support == "disputed"
        assert checked.response.status == "partial"
    else:
        assert checked.response.report is None
        assert checked.response.status == "insufficient_evidence"


def test_batching_checks_each_claim_once_with_the_full_cited_excerpt():
    excerpt = ("Arsenal have limited forward depth. " * 30).strip()
    claims = [claim(identifier=f"claim-{number}") for number in range(7)]
    client = FakeVerifier()
    audit = verify_claims(claims, [source(excerpt=excerpt)], client)
    assert audit.error is None
    assert len(client.payloads) == 2
    assert [check.claim_id for check in audit.checks] == [item.id for item in claims]
    assert all(payload["evidence"][0]["excerpt"] == excerpt for payload in client.payloads)


def test_oversized_claim_is_unassessed_without_truncating_or_blocking_other_claims():
    evidence = [source(excerpt="Arsenal " * 5000), source("S2", "Chelsea have depth.")]
    claims = [claim(), claim(refs=("S2",), identifier="small")]
    client = FakeVerifier()
    audit = verify_claims(claims, evidence, client)
    assert audit.error is None
    assert [check.verdict for check in audit.checks] == ["unassessed", "supported"]
    assert audit.evidence == evidence
    assert len(client.payloads) == 1
    assert [item["id"] for item in client.payloads[0]["claims"]] == ["small"]


def preview_response():
    now = datetime.now(timezone.utc)
    request = AnalystRequest(
        discussion_id="preview-test", mode="match_preview", question="Who may win?",
        team_a="Arsenal", team_b="Chelsea", evidence_cutoff=now - timedelta(hours=1),
        match_kickoff=now + timedelta(hours=2),
    )
    evidence = [
        source("S1", "Arsenal have limited forward depth.", published_at=now - timedelta(days=1)),
        source("S2", "Chelsea have pressing depth.", published_at=now - timedelta(days=1)),
    ]

    def plan(team, ref):
        return TeamPlan(
            team=team,
            should_do=[SupportedPoint(text="Manage the available depth.", support="inference", evidence_ids=[ref])],
            should_avoid=[SupportedPoint(text="Avoid excessive fatigue.", support="inference", evidence_ids=[ref])],
        )

    return AnalystResponse(
        request=request, status="complete", snapshot_sha256="b" * 64,
        report=MatchPreviewReport(
            evidence=evidence,
            findings=[Finding(claim="Arsenal have limited depth.", support="source_backed", evidence_ids=["S1"])],
            team_a_plan=plan("Arsenal", "S1"), team_b_plan=plan("Chelsea", "S2"),
            prediction=Prediction(
                outcome="Chelsea may have an advantage.", scope="ninety_minutes",
                rationale="Their greater depth may matter late in the match.",
                evidence_ids=["S1", "S2"], conditions=["Pressing depth is available."],
                uncertainty="The excerpts do not establish actual lineups.",
            ),
            recommendation=Recommendation(
                text="Manage fatigue.", rationale="Available depth constrains pressing.",
                evidence_ids=["S1", "S2"], uncertainty="Lineups are unknown.",
            ),
        ),
    )


@pytest.mark.parametrize("lost_coverage", ["team_plan", "prediction_citation"])
def test_prediction_is_withheld_when_pruning_removes_required_team_coverage(lost_coverage):
    original = preview_response()
    before = original.model_dump(mode="json")

    def remove_coverage(claim, check):
        if lost_coverage == "team_plan" and claim["id"] == "/team_b_plan/should_avoid/0":
            check.update(verdict="unsupported", quotes=[], unused_evidence_ids=["S2"])
        if lost_coverage == "prediction_citation" and claim["id"] == "/prediction":
            check["quotes"] = [q for q in check["quotes"] if q["evidence_id"] == "S1"]
            check["unused_evidence_ids"] = ["S2"]

    checked = verify_response(original, FakeVerifier(remove_coverage))
    assert checked.response.status == "partial"
    assert checked.response.report.prediction is None
    assert any("prediction was withheld" in note for note in checked.response.missing_information)
    assert original.model_dump(mode="json") == before


def test_preview_without_recorded_pre_cutoff_sources_keeps_plans_but_withholds_prediction():
    original = preview_response()
    original.report.evidence[1].published_at = None
    checked = verify_response(original, FakeVerifier())
    assert checked.response.status == "partial"
    assert checked.response.report.prediction is None
    assert checked.response.report.team_a_plan.should_do
    assert checked.response.report.team_b_plan.should_do


def test_successful_checks_keep_an_eligible_preview_complete():
    checked = verify_response(preview_response(), FakeVerifier())
    assert checked.response.status == "complete"
    assert checked.response.report.prediction.evidence_ids == ["S1", "S2"]


def repair_bundle(request, snapshot="a" * 64):
    from src.advisor.evidence import EvidenceBundle, MessageRecord
    attached = source()
    return EvidenceBundle(
        request=request, discussion_topic=request.question,
        snapshot_sha256=snapshot,
        messages=[MessageRecord(
            message_ref="M1", round_num=1, sender_id="agent-1", recipient_ids=[],
            content=attached.excerpt, source_ids=[attached.id],
        )],
        evidence=[attached], source_mentions={attached.id: ["M1"]},
        source_groups={attached.source: [attached.id]},
        source_aliases={attached.id: [attached.source]}, has_sources=True,
    )


def install_repair_stubs(monkeypatch, drafts, *, snapshot="a" * 64):
    from src.advisor import decision, evidence, research
    calls = {"analysis": [], "research": [], "load": []}

    def analyze(request, llm_client=None, *, evidence_bundle=None):
        calls["analysis"].append(evidence_bundle)
        return drafts[len(calls["analysis"]) - 1].model_copy(deep=True)

    def load(request):
        calls["load"].append(request)
        return repair_bundle(request, snapshot)

    def retrieve(bundle, llm_client=None, *, research_gaps=None):
        calls["research"].append(list(research_gaps))
        extra = EvidenceItem(
            id="R1", kind="source", origin="web_search",
            excerpt="An independent report discusses the financial tradeoffs.",
            source="https://example.test/financial-tradeoffs", query="transfer tradeoffs",
            content_kind="search_excerpt", retrieved_at=datetime.now(timezone.utc),
        )
        trace = bundle.research.model_copy(deep=True) if bundle.research else ResearchTrace()
        trace.evidence.append(extra)
        trace.attempts.append(ResearchAttempt(
            tool="web_search", query="transfer tradeoffs", status="success", source_ids=[extra.id],
        ))
        return research.restore_research_bundle(bundle, trace, [extra])

    monkeypatch.setattr(decision, "analyze_decision", analyze)
    monkeypatch.setattr(evidence, "load_discussion_evidence", load)
    monkeypatch.setattr(research, "research_evidence", retrieve)
    return calls


@pytest.mark.parametrize("initial_status", ["partial", "insufficient_evidence"])
def test_missing_decision_sections_trigger_one_targeted_research_and_regeneration(monkeypatch, initial_status):
    first = response()
    first.research = ResearchTrace(attempts=[ResearchAttempt(
        tool="knowledge_search", query="initial squad search", status="empty",
    )])
    if initial_status == "insufficient_evidence":
        first = AnalystResponse(
            request=first.request, status="insufficient_evidence",
            snapshot_sha256=first.snapshot_sha256, research=first.research,
            missing_information=["No supported option assessments were generated."],
        )
    calls = install_repair_stubs(monkeypatch, [first, complete_decision_response()])
    checked = analyze_verified(first.request, analyst_client=object(), verifier_client=FakeVerifier())
    assert len(calls["analysis"]) == 2
    assert calls["analysis"][0] is None
    assert calls["analysis"][1].snapshot_sha256 == first.snapshot_sha256
    assert [item.id for item in calls["analysis"][1].evidence] == ["S1", "R1"]
    assert calls["research"] == [[
        "benefits of taking the action", "drawbacks of taking the action",
        "benefits of not taking the action", "drawbacks of not taking the action",
    ]]
    assert checked.response.status == "complete"
    assert checked.response.report.do_it.pros and checked.response.report.do_it.cons
    assert checked.response.report.do_not_do_it.pros and checked.response.report.do_not_do_it.cons
    assert [attempt.tool for attempt in checked.response.research.attempts] == ["knowledge_search", "web_search"]
    assert checked.response.research.evidence[0].id == "R1"


def test_fully_populated_checked_assessment_does_not_trigger_additional_research(monkeypatch):
    first = complete_decision_response()
    calls = install_repair_stubs(monkeypatch, [first])
    checked = analyze_verified(first.request, verifier_client=FakeVerifier())
    assert checked.response.status == "complete"
    assert len(calls["analysis"]) == 1
    assert calls["research"] == [] and calls["load"] == []


def test_poorer_repair_cannot_erase_valid_original_assessments_or_newly_found_sources(monkeypatch):
    first = complete_decision_response()
    data = first.model_dump()
    data["status"] = "partial"
    data["report"]["do_not_do_it"] = None
    first = AnalystResponse.model_validate(data)
    original_points = first.report.do_it.model_dump()
    calls = install_repair_stubs(monkeypatch, [first, response()])
    checked = analyze_verified(first.request, verifier_client=FakeVerifier())
    assert len(calls["research"]) == 1
    assert checked.response.report.do_it.model_dump() == original_points
    assert checked.response.report.do_not_do_it is None
    assert checked.response.research.evidence[0].id == "R1"
    assert checked.response.research.attempts[-1].status == "success"
    assert any("one targeted follow-up" in note for note in checked.response.missing_information)
    assert any("benefits of not taking" in note for note in checked.response.research.limitations)


def test_follow_up_is_bounded_when_regenerated_sections_are_still_empty(monkeypatch):
    first = response()
    calls = install_repair_stubs(monkeypatch, [first, first])
    checked = analyze_verified(first.request, verifier_client=FakeVerifier())
    assert len(calls["analysis"]) == 2
    assert len(calls["research"]) == 1
    assert checked.response.status == "partial"
    assert checked.response.research.evidence[0].id == "R1"
    assert any("supported content is still missing" in note for note in checked.response.missing_information)


def test_changed_snapshot_aborts_follow_up_before_searching(monkeypatch):
    first = response()
    calls = install_repair_stubs(monkeypatch, [first], snapshot="b" * 64)
    checked = analyze_verified(first.request, verifier_client=FakeVerifier())
    assert len(calls["analysis"]) == 1
    assert len(calls["load"]) == 1
    assert calls["research"] == []
    assert checked.response.snapshot_sha256 == first.snapshot_sha256
    assert any("snapshot changed" in note for note in checked.response.missing_information)


def test_failed_generation_does_not_trigger_another_analysis_or_search(monkeypatch):
    first = AnalystResponse(
        request=response().request, status="failed", error="The analyst provider could not finish.",
    )
    calls = install_repair_stubs(monkeypatch, [first])
    checked = analyze_verified(first.request, verifier_client=FakeVerifier())
    assert checked.response.status == "failed"
    assert len(calls["analysis"]) == 1
    assert calls["research"] == [] and calls["load"] == []


def test_failed_verification_does_not_trigger_provider_retries_as_research(monkeypatch):
    first = response()
    calls = install_repair_stubs(monkeypatch, [first])
    checked = analyze_verified(first.request, verifier_client=FakeVerifier(fail_on=1))
    assert checked.response.status == "failed"
    assert len(calls["analysis"]) == 1
    assert calls["research"] == [] and calls["load"] == []
