"""Offline contracts for the advisor's independent evidence research."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from src.advisor import evidence, research
from src.advisor.evidence import build_evidence_bundle
from src.advisor.models import AnalystRequest
from src.advisor.verification import analyze_verified
from src.agent.types import RetrievedSource
from src.discussion.types import DiscussionConfig, DiscussionMessage, DiscussionResult


NOW = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)
QUESTION = "Should Arsenal buy another attacker?"
ARTICLE = "https://example.test/arsenal"


def source(content="Arsenal need forward depth.", url=ARTICLE, **metadata):
    return RetrievedSource(
        content=content,
        source=url,
        metadata={"retrieved_at": NOW.isoformat(), **metadata},
    )


def saved_discussion(*, attached=(), contents=None):
    contents = contents or [
        "An attacker could improve depth.",
        "The total fee and wages constrain this choice.",
        "Retaining the budget could help other positions.",
    ]
    return DiscussionResult(
        config=DiscussionConfig(
            discussion_id="research-test", topic=QUESTION, num_rounds=2,
            agent_ids=["agent-a", "agent-b"], graph={"agent-a": ["agent-b"]},
            llm_model="offline-test", llm_temperature=0,
            timestamp=(NOW - timedelta(days=2)).isoformat(),
            metadata={"status": "completed"},
        ),
        messages=[
            DiscussionMessage(
                round_num=index, sender_id="agent-a" if index % 2 == 0 else "agent-b",
                recipient_ids=["agent-b" if index % 2 == 0 else "agent-a"],
                content=content, timestamp=(NOW - timedelta(hours=3 - index)).isoformat(),
                sources_used=list(attached) if index == 0 else [],
            )
            for index, content in enumerate(contents)
        ],
    )


def bundle(*, preview=False, attached=(), contents=None):
    discussion = saved_discussion(attached=attached, contents=contents)
    request = AnalystRequest(
        discussion_id="research-test", mode="match_preview" if preview else "decision",
        question=QUESTION,
        **({"team_a": "Arsenal", "team_b": "Chelsea", "evidence_cutoff": NOW,
            "match_kickoff": NOW + timedelta(days=1)} if preview else {}),
    )
    return build_evidence_bundle(request, discussion)


def tool_call(name, arguments, identifier="call-1", **extra):
    return {
        "id": identifier, "type": "function",
        "function": {"name": name, "arguments": arguments if isinstance(arguments, str)
                     else json.dumps(arguments)},
        **extra,
    }


class ResearchClient:
    def __init__(self, answers=None, error=None):
        self.answers = list(answers or [{"content": "Enough research for the analyst."}])
        self.error = error
        self.histories = []

    def generate(self, messages, tools=None):
        assert {tool.name for tool in tools or []} == {
            "knowledge_search", "web_search", "read_web_page",
        }
        for tool in tools:
            assert tool.parameters["additionalProperties"] is False
            assert tool.parameters["required"] == [tool.argument]
        self.histories.append(deepcopy(messages))
        if self.error:
            raise self.error
        return deepcopy(self.answers[min(len(self.histories) - 1, len(self.answers) - 1)])


def run(original=None, client=None, knowledge=None, web=None, page=None):
    return research.research_evidence(
        original or bundle(), llm_client=client or ResearchClient(),
        knowledge_provider=knowledge or (lambda _: []),
        web_provider=web or (lambda _: []), page_provider=page or (lambda _: []),
    )


def test_queries_both_providers_and_reads_two_discovered_articles():
    calls = []

    def knowledge(query):
        calls.append(("knowledge", query))
        return [source("A knowledge database excerpt.", "dataset:forward-depth")]

    def web(query):
        calls.append(("web", query))
        return [source(f"Article {index} discovery snippet.", f"https://example.test/{index}")
                for index in range(3)]

    def page(url):
        calls.append(("page", url))
        return source(f"Full article text for {url}.", url)

    result = run(knowledge=knowledge, web=web, page=page)
    assert calls == [
        ("knowledge", QUESTION), ("web", QUESTION),
        ("page", "https://example.test/0"), ("page", "https://example.test/1"),
    ]
    assert [attempt.tool for attempt in result.research.attempts] == [
        "knowledge_search", "web_search", "read_web_page", "read_web_page",
    ]
    assert all(attempt.status == "success" for attempt in result.research.attempts)
    assert {item.content_kind for item in result.research.evidence} == {
        "knowledge_excerpt", "search_excerpt", "page_excerpt",
    }


def test_full_original_transcript_and_snapshot_are_preserved_without_mutation():
    original = bundle(contents=["First " + "quoted argument " * 2500, "Second complete message."])
    before = original.model_dump(mode="json")
    result = run(original, knowledge=lambda _: [source("New independent evidence.", "dataset:new")])
    assert original.model_dump(mode="json") == before
    assert result.messages == original.messages
    assert result.messages[0].content == before["messages"][0]["content"]
    assert result.evidence[:len(original.evidence)] == original.evidence
    assert result.snapshot_sha256 == original.snapshot_sha256
    assert result.request == original.request
    assert result.research is not None and original.research is None


def test_research_ids_and_metadata_identify_independent_origins():
    result = run(knowledge=lambda _: [source(
        "An independent database excerpt.", "dataset:depth", title="Squad depth report",
        published_at=(NOW - timedelta(days=1)).isoformat(),
    )])
    item = result.research.evidence[0]
    assert item.id == "R001" and item.kind == "source"
    assert item.message_ref is None and item.origin == "knowledge_base"
    assert item.title == "Squad depth report" and item.query == QUESTION
    assert item.retrieved_at == NOW and item.content_kind == "knowledge_excerpt"
    assert result.source_mentions[item.id] == []
    assert all(item.id not in message.source_ids for message in result.messages)
    assert result.source_aliases[item.id] == ["dataset:depth"]
    publication = result.source_publications[item.id][0]
    assert publication.message_ref is None and publication.metadata_field == "published_at"
    assert publication.parsed_at == NOW - timedelta(days=1)
    assert result.research.attempts[0].source_ids == [item.id]


def test_canonical_urls_and_whitespace_duplicates_share_an_evidence_id():
    first = source("An excerpt with whitespace.", f"{ARTICLE}/?utm_source=agent-a")
    second = source("An  excerpt\nwith whitespace.", f"{ARTICLE}?utm_medium=agent-b#quote")
    result = run(web=lambda _: [first, second])
    assert len(result.research.evidence) == 1
    item = result.research.evidence[0]
    assert result.research.attempts[1].source_ids == [item.id]
    assert result.source_groups[f"url:{ARTICLE}"] == [item.id]
    assert set(result.source_aliases[item.id]) == {first.source, second.source}


def test_discovery_reads_article_even_when_snippet_matches_existing_discussion_source():
    attached = source("Existing article excerpt.", published_at=(NOW - timedelta(days=2)).isoformat())
    original = bundle(attached=[attached])
    pages = []

    def page(url):
        pages.append(url)
        return source("The actual article has additional details.", url)

    result = run(original, web=lambda _: [attached], page=page)
    assert pages == [ARTICLE]
    assert result.research.attempts[1].source_ids == ["S001"]
    assert [item.id for item in result.evidence if item.excerpt == attached.content] == ["S001"]
    assert any(item.origin == "web_page" for item in result.research.evidence)
    assert result.messages == original.messages


def test_discovery_preserves_the_web_url_when_deduplicating_a_named_knowledge_document():
    pages = []

    def page(url):
        pages.append(url)
        return source("Additional full article text.", url)

    result = run(
        knowledge=lambda _: [source("The same source excerpt.", "dataset:article", canonical_url=ARTICLE)],
        web=lambda _: [source("The same source excerpt.")], page=page,
    )
    assert pages == [ARTICLE]
    assert result.research.attempts[0].source_ids == result.research.attempts[1].source_ids
    assert set(result.source_aliases["R001"]) == {"dataset:article", ARTICLE}
    assert any(item.origin == "web_page" for item in result.research.evidence)


def test_model_gap_tools_execute_with_matching_assistant_and_tool_ids():
    calls = []
    extra = {"google": {"thought_signature": "offline-signature"}}
    client = ResearchClient([
        {"content": "Check wages and counterarguments.", "tool_calls": [
            tool_call("knowledge_search", {"query": "Arsenal wage budget"}, "knowledge-gap", extra_content=extra),
            tool_call("web_search", {"query": "Arsenal transfer drawbacks"}, "web-gap"),
        ]},
        {"content": "Read the selected source.", "tool_calls": [
            tool_call("read_web_page", {"url": ARTICLE}, "article-gap"),
        ]},
        {"content": "Research is ready."},
    ])

    def knowledge(query):
        calls.append(("knowledge", query))
        return [source("The wage budget is a constraint.", "dataset:wages")] if query != QUESTION else []

    def web(query):
        calls.append(("web", query))
        return [source("A transfer can crowd out other spending.")] if query != QUESTION else []

    def page(url):
        calls.append(("page", url))
        return source("The article explains the budget tradeoff.", url)

    result = run(client=client, knowledge=knowledge, web=web, page=page)
    assert calls == [
        ("knowledge", QUESTION), ("web", QUESTION),
        ("knowledge", "Arsenal wage budget"), ("web", "Arsenal transfer drawbacks"),
        ("page", ARTICLE),
    ]
    assert len(client.histories) == 3
    assistant = client.histories[1][2]
    assert assistant["role"] == "assistant"
    assert [call["id"] for call in assistant["tool_calls"]] == ["knowledge-gap", "web-gap"]
    assert assistant["tool_calls"][0]["extra_content"] == extra
    assert [(message["role"], message["tool_call_id"]) for message in client.histories[1][3:]] == [
        ("tool", "knowledge-gap"), ("tool", "web-gap"),
    ]
    for message in client.histories[1][3:]:
        payload = json.loads(message["content"])
        assert payload["evidence"][0]["id"].startswith("R")
    assert client.histories[2][-1]["tool_call_id"] == "article-gap"
    assert len(result.research.evidence) == 3


def test_real_provider_call_budget_is_enforced():
    calls = []
    client = ResearchClient([{"tool_calls": [
        tool_call("knowledge_search", {"query": f"missing fact {index}"}, f"budget-{index}")
        for index in range(8)
    ]}])
    result = run(client=client,
                 knowledge=lambda query: calls.append(("knowledge", query)) or [],
                 web=lambda query: calls.append(("web", query)) or [])
    assert len(calls) == research.MAX_TOOL_CALLS
    assert len(result.research.attempts) == research.MAX_TOOL_CALLS
    assert len(client.histories) == 1
    assert any("call budget" in item for item in result.research.limitations)


def test_unknown_malformed_and_repeated_tool_requests_are_bounded():
    provider_queries = []
    bad_calls = [
        tool_call("unrecognized_tool", {"query": "anything"}, "unknown"),
        tool_call("knowledge_search", "{invalid json", "invalid-json"),
        tool_call("knowledge_search", {"query": 7}, "wrong-type"),
        tool_call("knowledge_search", {"query": " "}, "blank"),
        tool_call("knowledge_search", {"query": "q" * 501}, "long"),
        tool_call("read_web_page", {"url": " "}, "blank-url"),
        tool_call("knowledge_search", {"query": f" {QUESTION} "}, "repeated"),
    ]
    client = ResearchClient([{"tool_calls": bad_calls}])
    result = run(client=client, knowledge=lambda query: provider_queries.append(query) or [])
    assert provider_queries == [QUESTION]
    assert len(client.histories) == research.MAX_TOOL_ROUNDS
    assert len(result.research.attempts) == 2
    tool_results = [json.loads(message["content"]) for message in client.histories[1]
                    if message["role"] == "tool"]
    assert all("error" in item for item in tool_results[:-1])
    assert tool_results[-1]["evidence"] == []
    assert any("round budget" in item for item in result.research.limitations)


def test_one_provider_failure_preserves_other_provider_and_article_results():
    def broken_knowledge(_):
        raise RuntimeError("An implementation error containing private provider details")

    result = run(knowledge=broken_knowledge, web=lambda _: [source("A discovery excerpt.")],
                 page=lambda url: source("Full relevant article text.", url))
    assert [attempt.status for attempt in result.research.attempts] == ["failed", "success", "success"]
    assert {item.origin for item in result.research.evidence} == {"web_search", "web_page"}
    assert "private provider details" not in " ".join(result.research.limitations)
    assert any("Knowledge search was unavailable" in item for item in result.missing_information)


def test_model_failure_keeps_initial_evidence_and_explains_missing_followup():
    result = run(client=ResearchClient(error=RuntimeError("Simulated model outage")),
                 knowledge=lambda _: [source("Useful independent evidence.", "dataset:depth")])
    assert result.research.evidence[0].excerpt == "Useful independent evidence."
    assert any("model-directed research could not finish" in item for item in result.missing_information)


def test_restore_research_keeps_every_excerpt_id_and_original_discussion():
    original = bundle()
    first = run(original, knowledge=lambda _: [source(
        "The database records a budget constraint.", "dataset:budget",
        published_at=(NOW - timedelta(days=1)).isoformat(),
    )], web=lambda _: [source("A public source records squad needs.")])
    restored = research.restore_research_bundle(original, first.research, first.evidence)
    assert restored.evidence == first.evidence
    assert restored.research == first.research
    assert restored.messages == original.messages
    assert restored.snapshot_sha256 == original.snapshot_sha256
    assert restored.source_mentions["R001"] == []
    assert restored.source_publications["R001"][0].parsed_at == NOW - timedelta(days=1)
    assert original.research is None
    restored.research.limitations.append("Independent copy.")
    assert "Independent copy." not in first.research.limitations


def test_restore_research_rejects_reused_ids_with_changed_content():
    original = bundle()
    changed = original.evidence[0].model_copy(update={"excerpt": "A different message."})
    with pytest.raises(ValueError, match="inconsistent content"):
        research.restore_research_bundle(original, None, [changed])


def test_gap_research_searches_missing_sides_and_keeps_prior_trace_and_sources():
    first = run(knowledge=lambda _: [source("Original research.", "dataset:initial")])
    before = first.model_dump(mode="json")
    queries = []
    client = ResearchClient()
    gaps = ["benefits of buying an attacker", "drawbacks of keeping the current squad"]

    def web(query):
        queries.append(query)
        return [source("Additional evidence for " + query)]

    result = research.research_evidence(
        first, llm_client=client, research_gaps=gaps,
        knowledge_provider=lambda _: [], web_provider=web, page_provider=lambda _: [],
    )
    assert len(queries) == 2
    assert gaps[0] in queries[0] and gaps[1] in queries[1]
    assert all(QUESTION in query for query in queries)
    assert result.research.attempts[:len(first.research.attempts)] == first.research.attempts
    assert result.research.evidence[0] == first.research.evidence[0]
    assert {item.id for item in result.research.evidence} == {"R001", "R002", "R003"}
    assert json.loads(client.histories[0][1]["content"])["research_gaps"] == gaps
    assert result.snapshot_sha256 == first.snapshot_sha256
    assert first.model_dump(mode="json") == before


def test_gap_research_can_reformulate_empty_searches_through_model_tools():
    queries = []
    client = ResearchClient([
        {"tool_calls": [tool_call("web_search", {"query": "Arsenal forward rotation injury depth"})]},
        {"content": "Relevant evidence found."},
    ])

    def web(query):
        queries.append(query)
        return [source("The current squad has limited forward depth.")] if query.endswith("injury depth") else []

    result = research.research_evidence(
        bundle(), llm_client=client, research_gaps=["benefits of another attacker"],
        knowledge_provider=lambda _: [], web_provider=web, page_provider=lambda _: [],
    )
    assert len(queries) == 2
    assert queries[-1] == "Arsenal forward rotation injury depth"
    assert result.research.evidence[0].excerpt == "The current squad has limited forward depth."
    assert result.research.attempts[-1].status == "success"


@pytest.mark.parametrize("metadata", [
    {},
    {"date": (NOW - timedelta(days=1)).isoformat()},
    {"published_at": (NOW + timedelta(seconds=1)).isoformat()},
    {"published_at": "2030-01-09T12:00:00"},
    {"published_at": (NOW - timedelta(days=1)).isoformat(), "modified_at": (NOW + timedelta(seconds=1)).isoformat()},
    {"published_at": (NOW - timedelta(days=1)).isoformat(), "modified_at": "not-a-timestamp"},
    {"published_at": (NOW - timedelta(days=1)).isoformat(), "modified_at": "2030-01-09T15:00:00"},
])
def test_preview_excludes_knowledge_without_valid_pre_cutoff_content_dates(metadata):
    result = run(bundle(preview=True), knowledge=lambda _: [source("Potential later knowledge.", "dataset:dates", **metadata)])
    assert result.research.evidence == []
    assert result.research.attempts[0].status == "excluded"
    assert result.has_time_eligible_sources is False
    assert any("pre-cutoff" in item for item in result.research.limitations)


def test_preview_accepts_dated_knowledge_without_inventing_a_discussion_attachment():
    result = run(bundle(preview=True), knowledge=lambda _: [source(
        "Historical squad information.", "dataset:dated",
        published_at=(NOW - timedelta(days=2)).isoformat(),
        modified_at=(NOW - timedelta(days=1)).isoformat(),
    )])
    assert result.has_sources is True and result.has_time_eligible_sources is True
    item = result.research.evidence[0]
    assert item.origin == "knowledge_base" and item.message_ref is None
    assert item.published_at == NOW - timedelta(days=2)
    assert item.modified_at == NOW - timedelta(days=1)


@pytest.mark.parametrize("tool", ["web_search", "read_web_page"])
def test_preview_rejects_live_web_content_with_old_publication_without_a_capture(tool):
    old_page = source("A live article that may have changed.", published_at=(NOW - timedelta(days=2)).isoformat())
    client = ResearchClient([{"tool_calls": [tool_call("read_web_page", {"url": ARTICLE})]}, {"content": "Finished."}])
    result = run(bundle(preview=True), client=client,
                 web=(lambda _: [old_page]) if tool == "web_search" else None,
                 page=(lambda _: old_page) if tool == "read_web_page" else None)
    assert result.research.evidence == [] and result.has_time_eligible_sources is False
    assert any("Live web material" in item for item in result.research.limitations)
    assert any(attempt.tool == tool and attempt.status == "excluded" for attempt in result.research.attempts)


@pytest.mark.parametrize("metadata", [
    {"captured_at": (NOW + timedelta(seconds=1)).isoformat()},
    {"captured_at": "invalid capture"},
    {"captured_at": (NOW - timedelta(days=1)).isoformat(), "modified_at": (NOW + timedelta(seconds=1)).isoformat()},
    {"captured_at": (NOW - timedelta(days=1)).isoformat(), "modified_at": "invalid update"},
])
def test_preview_excludes_late_or_undated_captures_and_invalid_updates(metadata):
    candidate = source("Article content with uncertain timing.",
                       published_at=(NOW - timedelta(days=2)).isoformat(), **metadata)
    result = run(bundle(preview=True), web=lambda _: [candidate])
    assert result.research.evidence == []
    assert result.research.attempts[1].status == "excluded"
    assert result.has_time_eligible_sources is False


def test_research_excerpt_budget_excludes_oversized_input_instead_of_truncating_it():
    result = run(knowledge=lambda _: [source("x" * (research.MAX_NEW_EVIDENCE_CHARS + 1), "dataset:oversized")])
    assert result.research.evidence == []
    assert result.research.attempts[0].status == "excluded"
    assert any("input budget" in item for item in result.research.limitations)


class WorkflowAnalyst(ResearchClient):
    """Use the real research pass, then draft only from the final registry."""

    def __init__(self):
        super().__init__()
        self.final_payload = None

    def generate(self, messages, tools=None):
        if tools is not None:
            return super().generate(messages, tools=tools)
        self.final_payload = json.loads(messages[1]["content"])

        def point(text, reference):
            return {"text": text, "support": "inference", "evidence_ids": [reference]}

        return {"content": json.dumps({
            "action": "Buy another attacker",
            "findings": [
                {"claim": "Arsenal have limited forward depth.", "support": "source_backed", "evidence_ids": ["R001"]},
                {"claim": "A transfer involves a fee and wages.", "support": "source_backed", "evidence_ids": ["R002"]},
                {"claim": "A participant argues for improved depth.", "support": "discussion_claim", "evidence_ids": ["M001"]},
            ],
            "do_it": {
                "option": "Buy the attacker",
                "pros": [point("An extra attacker could improve depth.", "R001")],
                "cons": [point("The cost could constrain other investment.", "R003")],
            },
            "do_not_do_it": {
                "option": "Do not buy the attacker",
                "pros": [point("The club could retain its budget for other positions.", "R003")],
                "cons": [point("Existing forward depth could remain limited.", "R001")],
            },
            "recommendation": {
                "text": "Buy only if the total cost fits the budget.",
                "rationale": "Forward depth could improve while spending remains a constraint.",
                "evidence_ids": ["R001", "R003"],
                "conditions": ["The total cost fits the club's budget."],
                "uncertainty": "The discussion does not establish a price or quantify the benefit.",
            },
        })}


class WorkflowVerifier:
    def __init__(self, reject=False):
        self.reject = reject
        self.payloads = []

    def generate(self, messages, tools=None):
        assert tools is None
        payload = json.loads(messages[1]["content"])
        self.payloads.append(payload)
        registry = {item["id"]: item for item in payload["evidence"]}
        checks = []
        for claim in payload["claims"]:
            verdict, role = {
                "fact": ("supported", "supports"),
                "inference": ("grounded_inference", "premise"),
                "reported_claim": ("discussion_only", "expresses"),
            }[claim["kind"]]
            checks.append({
                "claim_id": claim["id"],
                "verdict": "unsupported" if self.reject else verdict,
                "reason": "The supplied excerpt does not support this claim." if self.reject
                          else "The supplied excerpt provides the fact or conditional premise.",
                "quotes": [] if self.reject else [
                    {"evidence_id": reference, "quote": registry[reference]["excerpt"], "role": role}
                    for reference in claim["evidence_ids"]
                ],
                "unused_evidence_ids": claim["evidence_ids"] if self.reject else [],
            })
        return {"content": json.dumps({"checks": checks})}


def verified_workflow(monkeypatch, *, reject=False):
    discussion = saved_discussion()
    original = bundle()
    providers = []

    def load(identifier):
        assert identifier == original.request.discussion_id
        return discussion

    def knowledge(query):
        providers.append(("knowledge", query))
        return [source("Arsenal have limited forward depth.", "dataset:arsenal-depth")]

    def web(query):
        providers.append(("web", query))
        return [source("Buying an attacker involves a transfer fee and wages.")]

    def page(url):
        providers.append(("page", url))
        return source("Spending on Arsenal's attacker could reduce the budget for other positions.", url)

    monkeypatch.setattr(evidence, "get_saved_discussion", load)
    monkeypatch.setattr(research, "_knowledge_search", knowledge)
    monkeypatch.setattr(research, "_web_search", web)
    monkeypatch.setattr(research, "_read_page", page)
    analyst, verifier = WorkflowAnalyst(), WorkflowVerifier(reject=reject)
    checked = analyze_verified(original.request, analyst_client=analyst, verifier_client=verifier)
    return checked, analyst, verifier, original, providers


def test_verified_decision_receives_discussion_database_and_web_evidence(monkeypatch):
    checked, analyst, verifier, original, providers = verified_workflow(monkeypatch)
    assert providers == [("knowledge", QUESTION), ("web", QUESTION), ("page", ARTICLE)]
    assert len(analyst.histories) == 1
    final_registry = {item["id"]: item for item in analyst.final_payload["evidence"]}
    assert set(final_registry) == {"M001", "M002", "M003", "R001", "R002", "R003"}
    for item in original.evidence:
        assert final_registry[item.id]["excerpt"] == item.excerpt
    assert final_registry["R001"]["origin"] == "knowledge_base"
    assert final_registry["R002"]["origin"] == "web_search"
    assert final_registry["R003"]["origin"] == "web_page"
    assert all(final_registry[identifier]["speaker"] is None for identifier in ["R001", "R002", "R003"])
    verified_ids = {item["id"] for payload in verifier.payloads for item in payload["evidence"]}
    assert {"M001", "R001", "R002", "R003"} <= verified_ids
    assert checked.response.status == "partial"
    assert checked.response.report.recommendation is not None
    assert checked.response.report.recommendation.evidence_ids == ["R001", "R003"]
    assert checked.response.snapshot_sha256 == original.snapshot_sha256
    assert [item.id for item in checked.response.research.evidence] == ["R001", "R002", "R003"]
    assert {check.verdict for check in checked.verification.checks} == {
        "supported", "grounded_inference", "discussion_only",
    }


def test_research_trace_survives_verification_removing_every_report_claim(monkeypatch):
    checked, analyst, verifier, original, providers = verified_workflow(monkeypatch, reject=True)
    assert providers[:3] == [("knowledge", QUESTION), ("web", QUESTION), ("page", ARTICLE)]
    assert len(providers) == 7
    assert "benefits of taking the action" in providers[3][1]
    assert providers[4][0] == "web" and providers[5][0] == "web"
    assert len(analyst.histories) == 2
    assert analyst.final_payload is not None and verifier.payloads
    assert checked.response.status == "insufficient_evidence" and checked.response.report is None
    assert checked.response.snapshot_sha256 == original.snapshot_sha256
    assert [attempt.status for attempt in checked.response.research.attempts] == ["success"] * 7
    assert {item.origin for item in checked.response.research.evidence} == {
        "knowledge_base", "web_search", "web_page",
    }
    assert all(item.message_ref is None for item in checked.response.research.evidence)
    assert all(check.verdict == "unsupported" for check in checked.verification.checks)
