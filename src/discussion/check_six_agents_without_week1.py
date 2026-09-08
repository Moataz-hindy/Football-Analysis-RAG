"""Temporary, real six-agent test without Week 1 retrieval.

Uses a shared rolling output-token budget instead of a fixed pause.
No database, embeddings, web search, or disk persistence.
"""
import re
import time
from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from openai import RateLimitError
from src.agent.agent import Agent
from src.agent.config import AgentConfig
from src.agent.interfaces import MemoryInterface, RetrievalInterface
from src.agent.llm import OpenAICompatibleLLM
from src.agent.persona_loader import load_persona
from src.agent.tool_registery import ToolRegistry
from src.agent.types import RetrievedSource
from src.discussion.orchestrator import (
    DiscussionOrchestrator,
    DiscussionRunError,
)
from src.discussion.router import GraphRouter
from src.tools.calculator import CalculatorTool


# Settings for THIS temporary test only.
MAX_OUTPUT_TOKENS = 400
OUTPUT_TOKENS_PER_MINUTE = 1000
WINDOW_SECONDS = 65.0  # Small safety margin beyond one minute.
TOTAL_ROUNDS = 3


def heading(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}", flush=True)


class DisabledRetrieval(RetrievalInterface):
    def retrieve(self, query: str) -> list[RetrievedSource]:
        return []


class TemporaryMemory(MemoryInterface):
    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []

    def get_relevant(self, query: str) -> str:
        return "\n\n".join(
            f"Previous task: {item['task']}\n"
            f"Previous response: {item['response']}"
            for item in self.history
        )

    def add(self, data: dict[str, str]) -> None:
        self.history.append(dict(data))


class OutputBudget:
    """Shared by every agent; suitable for this sequential test.

    Tracks reported output tokens from recent completed requests.
    It does not track other programs or other provider limits.
    """

    def __init__(self) -> None:
        # Each entry is: (request completion time, output tokens).
        self.recent: deque[tuple[float, int]] = deque()
        self.requests = 0
        self.total_output_tokens = 0

    def wait_for_room(self) -> None:
        while True:
            now = time.monotonic()

            # Forget requests outside our rolling window.
            while (
                self.recent
                and now - self.recent[0][0] >= WINDOW_SECONDS
            ):
                self.recent.popleft()

            used = sum(tokens for _, tokens in self.recent)

            # Reserve enough space for the NEXT request's maximum.
            if used + MAX_OUTPUT_TOKENS <= OUTPUT_TOKENS_PER_MINUTE:
                return

            # Wait until the oldest recorded request leaves the window.
            wait_seconds = WINDOW_SECONDS - (
                now - self.recent[0][0]
            )

            print(
                f"\n  [Budget pause] Recent output: {used} tokens."
                f" Waiting {wait_seconds:.1f}s...",
                flush=True,
            )
            time.sleep(max(wait_seconds, 0.1))

    def record(self, tokens: int) -> None:
        self.recent.append((time.monotonic(), tokens))
        self.total_output_tokens += tokens


class BudgetedLLM(OpenAICompatibleLLM):
    """Use the real adapter while controlling this test's output budget."""

    def __init__(self, agent_id: str, budget: OutputBudget) -> None:
        super().__init__(
            max_tokens=MAX_OUTPUT_TOKENS,
            max_retries=0,
        )
        self.agent_id = agent_id
        self.budget = budget

    def generate(self, messages, tools=None):
        self.budget.wait_for_room()
        self.budget.requests += 1

        print(
            f"  API request #{self.budget.requests}"
            f" | {self.agent_id}",
            flush=True,
        )

        # Retry only rate-limit errors, with a bounded number of attempts.
        for attempt in range(4):
            try:
                result = super().generate(messages=messages, tools=tools)
                break

            except RateLimitError as error:
                # After four unsuccessful attempts, stop normally with an error.
                if attempt == 3:
                    raise

                # Extract the waiting time from Groq's error message.
                match = re.search(
                    r"try again in\s+([0-9]+(?:\.[0-9]+)?)s",
                    str(error),
                    flags=re.IGNORECASE,
                )

                # Use the provider's delay plus a small safety margin.
                # If no delay was supplied, fall back to 65 seconds.
                wait_seconds = float(match.group(1)) + 2 if match else 65.0

                print(
                    f"\n  [Provider rate limit] Waiting {wait_seconds:.1f}s"
                    f" before retry {attempt + 1}/3...",
                    flush=True,
                )

                time.sleep(wait_seconds)

                # Other local budget constraints must still be respected.
                self.budget.wait_for_room()
                self.budget.requests += 1

        raw = self.last_response
        choice = raw.choices[0]

        # Use actual reported usage, not the maximum allowance.
        # If usage is missing, conservatively charge the full allowance.
        tokens = getattr(raw.usage, "completion_tokens", None)
        if tokens is None:
            tokens = MAX_OUTPUT_TOKENS

        self.budget.record(tokens)

        print(
            f"  Output tokens: {tokens}"
            f" | Finish: {choice.finish_reason}",
            flush=True,
        )

        if choice.finish_reason == "length":
            raise RuntimeError(
                "Response reached the output limit. "
                "Check that reasoning is disabled. "
                "This test will not accept truncated answers."
            )

        if not result["tool_calls"] and not result["content"].strip():
            raise RuntimeError("The model returned an empty answer.")

        return result


class ReportingAgent(Agent):
    """Adds readable progress without changing the orchestrator."""

    def __init__(self, agent_id: str, config: AgentConfig) -> None:
        super().__init__(config, max_tool_rounds=3)
        self.agent_id = agent_id
        self.discussion_round = 0

    def show_response(self, response) -> None:
        print(f"\n{response.content}", flush=True)

        if response.tool_calls:
            print("\n  Tools executed:", flush=True)
            for call in response.tool_calls:
                print(
                    f"    {call.name}({call.arguments})"
                    f" -> {call.result}",
                    flush=True,
                )
        else:
            print("\n  Tools executed: none", flush=True)

        print(
            f"  Knowledge-base sources: {len(response.sources)}",
            flush=True,
        )

    def run(self, task):
        heading(f"ROUND 0 — INITIAL OPINION | {self.agent_id}")
        response = super().run(task)
        self.show_response(response)
        return response

    def run_discussion_turn(self, task, received_messages=None):
        self.discussion_round += 1
        heading(
            f"ROUND {self.discussion_round}/{TOTAL_ROUNDS}"
            f" | {self.agent_id}"
        )

        senders = [
            message["sender"]
            for message in (received_messages or [])
        ]
        print(
            f"  Received from: {', '.join(senders) or 'nobody'}",
            flush=True,
        )

        response = super().run_discussion_turn(
            task=task,
            received_messages=received_messages,
        )
        self.show_response(response)
        return response


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    router = GraphRouter()
    budget = OutputBudget()
    agents: dict[str, Agent] = {}

    for agent_id in sorted(router.graph.graph.nodes):
        persona = load_persona(
            project_root / "personas" / f"{agent_id}.yaml"
        )

        config = AgentConfig(
            persona=persona,
            memory=TemporaryMemory(),
            retrieval=DisabledRetrieval(),
            tools=ToolRegistry(tools=[CalculatorTool()]),
            llm=BudgetedLLM(agent_id, budget),
        )

        agents[agent_id] = ReportingAgent(agent_id, config)

    orchestrator = DiscussionOrchestrator(
        agents=agents,
        router=router,
    )

    topic = (
        "Should a team use high pressing or a conservative defensive "
        "approach in a hypothetical World Cup match? "
        "The only supplied data is 12 successful presses in 20 attempts. "
        "These are hypothetical numbers, not real match evidence. "
        "Use the calculator only when arithmetic is needed; you do not "
        "need to repeat a calculation already available to you. "
        "Do not infer pressing intensity, PPDA, pitch location, or "
        "scoring chances from these numbers alone. "
        "The only available tool is calculator. Internal retrieval "
        "and web search are disabled. Do not claim to have used them. "
        "Discuss from your persona's perspective and acknowledge "
        "missing evidence. Keep EVERY response under 80 words, using "
        "the requested STANCE, REASONING, and SOURCES USED headings."
    )

    heading("SIX-AGENT LIVE DISCUSSION TEST")
    print(f"Agents:            {len(agents)}")
    print(f"Discussion rounds: {TOTAL_ROUNDS}, plus initial opinions")
    print(f"Output allowance:  {MAX_OUTPUT_TOKENS} tokens per request")
    print("Enabled tools:     calculator")
    print("Week 1 / web:      disabled")
    print("Estimated time:    roughly 5–12 minutes; usage-dependent")
    print("Stop manually:     Ctrl+C")
    print("Save to disk:      disabled", flush=True)

    started = time.monotonic()

    try:
        state = orchestrator.run(
            topic=topic,
            total_rounds=TOTAL_ROUNDS,
        )

    except DiscussionRunError as error:
        heading("TEST STOPPED — AGENT FAILURE")
        print(f"Agent:             {error.agent_id}")
        print(f"Round:             {error.round_number}")
        print(f"Cause:             {error.__cause__}")
        print(f"Completed messages: {len(error.state.messages)}")
        print("Partial state is in memory only, not saved to disk.")
        raise

    expected = len(agents) * (TOTAL_ROUNDS + 1)

    assert state.current_round == TOTAL_ROUNDS
    assert len(state.messages) == expected

    for round_number in range(TOTAL_ROUNDS + 1):
        messages = [
            message
            for message in state.messages
            if message.round_number == round_number
        ]
        assert len(messages) == len(agents)
        assert {message.sender_id for message in messages} == set(agents)

    for message in state.messages:
        assert message.content.strip()
        assert message.recipient_ids == router.get_recipients(
            message.sender_id
        )
        assert message.sources == []

    elapsed = time.monotonic() - started
    tool_count = sum(
        len(message.tool_calls) for message in state.messages
    )

    heading("PASSED — LIVE ORCHESTRATION CHECK")
    print(f"Agents:             {len(agents)}")
    print(f"Discussion rounds:  {state.current_round}")
    print(f"Messages:           {len(state.messages)} / {expected}")
    print(f"API requests:       {budget.requests}")
    print(f"Tool executions:    {tool_count}")
    print(f"Output tokens:      {budget.total_output_tokens}")
    print(f"Elapsed time:       {elapsed / 60:.1f} minutes")
    print("\nVerified: expected participants and message counts,")
    print("non-empty answers, and graph-addressed recipients.")
    print("Not verified: factual quality or Week 1 retrieval.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest stopped by you. No discussion was saved.")