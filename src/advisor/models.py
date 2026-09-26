"""Request and report models for the Football Strategy Analyst."""

from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


AnalysisMode = Literal["decision", "match_review", "match_preview"]
ReportStatus = Literal[
    "complete", "partial", "insufficient_evidence", "failed"
]
Support = Literal[
    "discussion_claim", "source_backed", "inference", "disputed"
]


# NEW: reject empty strings and strings containing only whitespace.
Text = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
SnapshotHash = Annotated[
    str,
    Field(pattern=r"^[0-9a-f]{64}$"),
]


# NEW: all models reject unexpected fields, including nested models.
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalystRequest(StrictModel):
    discussion_id: Text = Field(pattern=r"^[A-Za-z0-9_-]+$")
    mode: AnalysisMode
    question: Text

    team_a: Text | None = None
    team_b: Text | None = None

    evidence_cutoff: AwareDatetime | None = None
    match_kickoff: AwareDatetime | None = None

    @model_validator(mode="after")
    def check_match_request(self):
        if self.mode in {"match_review", "match_preview"}:
            if self.team_a is None or self.team_b is None:
                raise ValueError(
                    "Match analyses require team_a and team_b."
                )

            if self.team_a.casefold() == self.team_b.casefold():
                raise ValueError("The two teams must be different.")

        if self.mode == "match_preview":
            if (
                self.evidence_cutoff is None
                or self.match_kickoff is None
            ):
                raise ValueError(
                    "A match preview requires an evidence cutoff "
                    "and kickoff."
                )

            if self.evidence_cutoff >= self.match_kickoff:
                raise ValueError(
                    "The evidence cutoff must be before kickoff."
                )

        return self

class EvidenceItem(StrictModel):
    """A quoted discussion message or retrieved source excerpt."""

    id: Text
    kind: Literal["message", "source"]
    message_ref: Text | None = None
    excerpt: Text
    source: Text | None = None

    # CHANGED: timestamps must include their timezone.
    published_at: AwareDatetime | None = None
    origin: Literal["discussion", "knowledge_base", "web_search", "web_page"] = "discussion"
    title: Text | None = None
    query: Text | None = None
    retrieved_at: AwareDatetime | None = None
    modified_at: AwareDatetime | None = None
    content_kind: Literal["knowledge_excerpt", "search_excerpt", "page_excerpt"] | None = None

    @model_validator(mode="after")
    def check_source(self):
        # NEW: source evidence must identify its source.
        if self.kind == "source" and self.source is None:
            raise ValueError(
                "Source evidence requires a source identifier."
            )
        if (self.kind == "message" or self.origin == "discussion") and self.message_ref is None:
            raise ValueError("Discussion evidence must identify its original message.")
        if self.origin != "discussion" and (self.kind != "source" or self.message_ref is not None):
            raise ValueError("Independent research must be source evidence without a discussion attachment.")
        return self


class ResearchAttempt(StrictModel):
    tool: Literal["knowledge_search", "web_search", "read_web_page"]
    query: Text | None = None
    url: Text | None = None
    status: Literal["success", "empty", "failed", "excluded"]
    source_ids: list[Text] = Field(default_factory=list)
    reason: Text | None = None


class ResearchTrace(StrictModel):
    attempts: list[ResearchAttempt] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    limitations: list[Text] = Field(default_factory=list)


class Finding(StrictModel):
    claim: Text
    evidence_ids: list[Text] = Field(min_length=1)
    support: Support


class SupportedPoint(StrictModel):
    text: Text
    evidence_ids: list[Text] = Field(min_length=1)

    # NEW: a proposed consequence can be marked as an inference.
    support: Support


class OptionAssessment(StrictModel):
    option: Text
    pros: list[SupportedPoint] = Field(default_factory=list)
    cons: list[SupportedPoint] = Field(default_factory=list)


class TeamPlan(StrictModel):
    team: Text
    should_do: list[SupportedPoint] = Field(default_factory=list)
    should_avoid: list[SupportedPoint] = Field(default_factory=list)


class Recommendation(StrictModel):
    text: Text
    rationale: Text
    evidence_ids: list[Text] = Field(min_length=1)
    conditions: list[Text] = Field(default_factory=list)

    # CHANGED: uncertainty must be explained.
    uncertainty: Text


# NEW: predictions require reasoning, evidence and an outcome scope.
class Prediction(StrictModel):
    outcome: Text
    scope: Literal["ninety_minutes", "qualification"]
    rationale: Text
    evidence_ids: list[Text] = Field(min_length=1)
    conditions: list[Text] = Field(default_factory=list)
    uncertainty: Text


# NEW: each team gets its own retrospective analysis.
class TeamReview(StrictModel):
    team: Text
    actual_actions: list[SupportedPoint] = Field(default_factory=list)
    what_worked: list[SupportedPoint] = Field(default_factory=list)
    what_failed: list[SupportedPoint] = Field(default_factory=list)
    responses_to_opponent: list[SupportedPoint] = Field(
        default_factory=list
    )
    plausible_adjustments: list[OptionAssessment] = Field(
        default_factory=list
    )


# NEW: visit all nested objects so no citation location is missed.
def _objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)

    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


class ReportBase(StrictModel):
    # CHANGED: request, status and snapshot are stored in AnalystResponse.
    evidence: list[EvidenceItem] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    assumptions: list[Text] = Field(default_factory=list)
    recommendation: Recommendation | None = None

    @model_validator(mode="after")
    def check_references(self):
        # NEW: evidence identifiers must be unique.
        ids = [item.id for item in self.evidence]

        if len(ids) != len(set(ids)):
            raise ValueError("Evidence IDs must be unique.")

        known = set(ids)
        source_ids = {
            item.id
            for item in self.evidence
            if item.kind == "source"
        }

        # NEW: check citations in findings, recommendations,
        # pros, cons, team plans, adjustments and predictions.
        for node in _objects(self.model_dump()):
            references = set(node.get("evidence_ids", []))
            unknown = references - known

            if unknown:
                raise ValueError(
                    f"Unknown evidence IDs: {sorted(unknown)}"
                )

            if (
                node.get("support") == "source_backed"
                and not references.intersection(source_ids)
            ):
                raise ValueError(
                    "A source-backed point must cite source evidence."
                )

        # These checks establish valid references.
        # Matching excerpts and assessing claim support come later.
        return self


class DecisionReport(ReportBase):
    mode: Literal["decision"] = "decision"
    action: Text

    # CHANGED: partial reports can omit unsupported assessments.
    do_it: OptionAssessment | None = None
    do_not_do_it: OptionAssessment | None = None

    alternatives: list[OptionAssessment] = Field(default_factory=list)


class MatchReviewReport(ReportBase):
    mode: Literal["match_review"] = "match_review"
    what_happened: list[Finding] = Field(default_factory=list)

    # NEW: explicit analysis of each team.
    team_a_review: TeamReview | None = None
    team_b_review: TeamReview | None = None


class MatchPreviewReport(ReportBase):
    mode: Literal["match_preview"] = "match_preview"
    team_a_plan: TeamPlan | None = None
    team_b_plan: TeamPlan | None = None

    # CHANGED: replaces the unsupported predicted_outcome string.
    prediction: Prediction | None = None


# NEW: the mode field explicitly selects the correct report model.
AnalystReport = Annotated[
    DecisionReport | MatchReviewReport | MatchPreviewReport,
    Field(discriminator="mode"),
]


# NEW: every result uses this response wrapper.
# Failures can be represented without inventing report content.
class AnalystResponse(StrictModel):
    # Preserves the original question, mode, cutoff and kickoff.
    request: AnalystRequest

    status: ReportStatus
    snapshot_sha256: SnapshotHash | None = None
    report_version: Literal[1] = 1
    report: AnalystReport | None = None

    missing_information: list[Text] = Field(default_factory=list)
    error: Text | None = None
    research: ResearchTrace | None = None

    @model_validator(mode="after")
    def check_response(self):
        # NEW: failure requires an explanation and no report.
        if self.status == "failed":
            if self.report is not None or self.error is None:
                raise ValueError(
                    "A failed response needs an error and no report."
                )
            return self

        if self.error is not None:
            raise ValueError(
                "The error field is reserved for failed responses."
            )

        # NEW: insufficient evidence does not require fabricated sections.
        if self.status == "insufficient_evidence":
            if self.report is not None or not self.missing_information:
                raise ValueError(
                    "Explain missing evidence and omit the report."
                )
            return self

        report = self.report

        if report is None or self.snapshot_sha256 is None:
            raise ValueError(
                "Complete/partial responses need a report "
                "and snapshot hash."
            )

        # NEW: prevent returning the wrong kind of analysis.
        if report.mode != self.request.mode:
            raise ValueError(
                "Report mode must match request mode."
            )

        if isinstance(report, MatchReviewReport):
            teams = (report.team_a_review, report.team_b_review)
        elif isinstance(report, MatchPreviewReport):
            teams = (report.team_a_plan, report.team_b_plan)
        else:
            teams = ()

        # NEW: avoid accidentally analyzing the same team twice.
        if (
            teams
            and all(teams)
            and teams[0].team.casefold() == teams[1].team.casefold()
        ):
            raise ValueError("The two teams must be different.")

        # NEW: partial reports must explain their missing coverage.
        if self.status == "partial":
            if not self.missing_information:
                raise ValueError(
                    "A partial response must explain what is missing."
                )

            has_cited_analysis = any(
                node.get("evidence_ids")
                for node in _objects(report.model_dump())
            )

            if not report.evidence or not has_cited_analysis:
                raise ValueError(
                    "Use insufficient_evidence when no supported "
                    "analysis is available."
                )

            return self

        # NEW: complete reports require actual analytical content.
        if (
            not report.evidence
            or not report.findings
            or report.recommendation is None
        ):
            raise ValueError(
                "A complete report needs evidence, findings "
                "and a recommendation."
            )

        if isinstance(report, DecisionReport):
            for option in (report.do_it, report.do_not_do_it):
                if option is None or not option.pros or not option.cons:
                    raise ValueError(
                        "Complete decisions need pros and cons "
                        "for both options. Use partial when evidence "
                        "for a required section is missing."
                    )

        elif isinstance(report, MatchReviewReport):
            if not report.what_happened or any(
                team is None or not team.actual_actions
                for team in teams
            ):
                raise ValueError(
                    "Complete reviews need events and actual "
                    "actions for both teams."
                )

        else:
            if self.request.match_kickoff is None:
                raise ValueError(
                    "A complete preview needs the match kickoff time."
                )

            if report.prediction is None or any(
                team is None
                or not team.should_do
                or not team.should_avoid
                for team in teams
            ):
                raise ValueError(
                    "Complete previews need both team plans "
                    "and a prediction."
                )

        return self
