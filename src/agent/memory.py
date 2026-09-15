import re
from typing import Any
from .interfaces import MemoryInterface

# We'll try to import the LLM client from Week 1 to power the summarizer
try:
    from src.rag.search import get_client
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from src.rag.search import get_client


class ConversationMemory(MemoryInterface):
    """
    A memory implementation that maintains a recent conversation history
    AND maintains a running summary of older messages that have fallen out of the window.
    """

    def __init__(self, max_turns: int = 5):
        self.history: list[dict[str, Any]] = []
        self.max_turns = max_turns
        self.summary: str = "No previous context."

    def add(self, data: Any) -> None:
        """
        Adds a new interaction to the history.
        Expected data format: {"task": str, "response": str}
        """
        if not isinstance(data, dict):
            raise ValueError("ConversationMemory expects data to be a dictionary.")
        
        if "task" not in data or "response" not in data:
            raise ValueError("Data dictionary must contain 'task' and 'response' keys.")

        self.history.append(data)

        # Enforce sliding window by summarizing the oldest message before dropping it
        if len(self.history) > self.max_turns:
            self._summarize_oldest()

    def _summarize_oldest(self) -> None:
        """
        Pops the oldest interaction and uses the LLM to update the running summary.
        """
        oldest_turn = self.history.pop(0)
        
        try:
            client, model = get_client()
            
            prompt = (
                "You are a memory-management assistant for an AI agent.\n"
                f"Current Conversation Summary:\n{self.summary}\n\n"
                "Next interaction to incorporate into the summary:\n"
                f"User: {oldest_turn['task']}\n"
                f"Agent: {oldest_turn['response']}\n\n"
                "Please write a new, concise paragraph summarizing the entire conversation so far. "
                "Keep important facts, stances, and entities."
            )
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.summary = response.choices[0].message.content.strip()
            print(f"[Memory Updated] New Summary generated: {self.summary[:50]}...")
            
        except Exception as e:
            print(f"[Memory Warning] Failed to generate summary (API error). Oldest message dropped. Error: {e}")

    def get_messages(self) -> list[dict[str, str]]:
        """
        Returns the conversation history as a list of alternating user and assistant messages
        suitable for direct inclusion in chat completion payloads.
        """
        messages = []
        for index, turn in enumerate(self.history):
            raw_task = turn.get("task", "")
            round_match = re.search(r"Round:\s*(\d+)\s*of\s*(\d+)", raw_task)
            if round_match:
                task_summary = f"Discussion Turn (Round {round_match.group(1)} of {round_match.group(2)})"
            elif "initial opinion" in raw_task.lower():
                task_summary = "Discussion Turn (Round 0: Initial Opinion)"
            else:
                task_lines = [line.strip() for line in raw_task.split("\n") if line.strip()]
                task_summary = task_lines[0] if task_lines else f"Discussion Turn {index + 1}"
            messages.append({"role": "user", "content": task_summary})
            messages.append({"role": "assistant", "content": turn.get("response", "")})
        return messages

    def get_relevant(self, query: str) -> str:
        """
        Returns the running summary of older messages that have fallen out of the window.
        """
        if self.summary and self.summary != "No previous context.":
            return self.summary
        return ""
