# Agent Graph & Message Routing

This document outlines the design decisions, mathematical properties, and architecture for the multi-agent graph (Task 4.1) and message routing (Task 4.3) implemented for Week 3.

---

## 1. How the Graph is Created

The participating agents are represented as nodes in a directed graph (`networkx.DiGraph`) constructed in `src/discussion/graph.py`. The graph consists of 6 nodes:
- `context_analyst` (Lead Studio Host & Anchor)
- `fan_analyst` (Egyptian & African Football Supporter)
- `performance_analyst` (International Ex-Player Pundit)
- `refereeing_analyst` (VAR & Refereeing Expert)
- `statistical_analyst` (Lead Data Analyst)
- `tactical_analyst` (Tactical Coach)

The graph defines 15 directed edges organized into three functional layers:

### A. Reciprocal Core Debate Pairs (Two-Way Rebuttals)
To enable authentic, direct dialogue and counter-arguments rather than one-way monologues, core domain counterparts are connected bidirectionally:
- **`tactical_analyst` ↔ `performance_analyst`**: The Tactical Coach diagrams structural systems and pressing triggers; the Ex-Player Pundit counters with dressing-room reality, physical fatigue, and on-pitch execution.
- **`fan_analyst` ↔ `refereeing_analyst`**: The Supporter questions controversial penalty calls or perceived referee bias; the Referee Expert defends decisions using IFAB Law 12 and VAR protocols.
- **`tactical_analyst` ↔ `statistical_analyst`**: The Coach explains tactical formations and transitions; the Data Analyst verifies or challenges those claims with expected goals (xG), field tilt, and shot maps.

### B. Studio Host / Anchor Moderation Flow
In television football studios (e.g. beIN Sports, Match of the Day), the Host acts as the debate moderator and central narrative conductor:
- **Prompting (`context_analyst` → `fan_analyst`, `tactical_analyst`, `performance_analyst`)**: The Host steers the discussion by challenging the fan's emotions, the coach's system, and the ex-player's mentality.
- **Synthesis (`statistical_analyst`, `refereeing_analyst`, `performance_analyst` → `context_analyst`)**: Core domain experts feed objective metrics, officiating rulings, and player assessments back to the Host for round-level synthesis.

### C. Cross-Domain Thematic Bridges
- **`fan_analyst` → `statistical_analyst`**: The Supporter challenges cold corporate analytics and algorithmic models that overlook heart and underdog determination.
- **`tactical_analyst` → `fan_analyst`**: The Coach explains defensive blocks and rest defense to help the supporter understand why late structural fatigue occurred.
- **`performance_analyst` → `refereeing_analyst`**: The Ex-Player challenges the referee's interpretation of physical contact, challenge intent, and force from a player's perspective.

---

## 2. Why This Approach Was Chosen

In accordance with **Week 3 Section 11 & 12**, communication must be constrained by domain relationships rather than unconstrained broadcasting:
1. **Prevents Full-Broadcast Context Explosion**: A complete graph ($K_6$) would send every message to all 6 agents every round ($6 \times 6 = 36$ messages/round). This rapidly exhausts token limits and dilutes agent specialization into generic consensus.
2. **Avoids Ring Topology Pathology**: A simple directed cycle ($A \to B \to C \dots$) suffers from **0.0% reciprocity**, creating a "game of telephone" where an agent can never directly rebut someone who challenged them.
3. **Ensures Rapid Information Propagation**: With a low diameter of 3 hops, ideas and evidence introduced by any agent propagate across the network within the 3-round debate horizon.
4. **Balanced In-Degree & Out-Degree**: Every agent has an in-degree of 2 to 3 and an out-degree of 2 to 3. No agent is isolated or starved of context.

---

## 3. How Strong Connectivity is Guaranteed

Strong connectivity means that for every pair of agents $u$ and $v$, there exists a directed path from $u$ to $v$.

1. **Mathematical Verification**: The `DiscussionGraph` class runs `networkx.is_strongly_connected(self.graph)` at initialization.
2. **Fail-Fast Safety**: The `GraphRouter` (`src/discussion/router.py`) asserts strong connectivity on instantiation. If any edge modification breaks strong connectivity, a `ValueError` is raised immediately before any LLM calls or discussion rounds execute.
3. **Automated Unit Testing**: The test suite includes `tests/test_graph_routing.py::test_graph_connectivity`, which runs in continuous integration.

---

## 4. How the Graph Affects Discussion Behavior

The graph directly dictates message delivery via the stateless `GraphRouter.get_recipients(sender_id)`.

- **Localized Friction & Clashes**: The Supporter and the Referee directly trade arguments in consecutive rounds. The Supporter criticizes officiating, the Referee explains Law 12 in the next turn, and the Supporter can immediately respond.
- **Data Grounding**: The Statistical Analyst's numbers directly check the Tactical Coach's assertions before reaching the broader studio narrative.
- **Balanced Workload**: In each round, every agent receives 2 or 3 curated messages in their inbox, allowing them to formulate focused, substantive rebuttals without hitting token limits.

---

## 5. Decoupling from Orchestration

The routing logic is strictly stateless. `GraphRouter` accepts a `sender_id` and returns a `list[str]` of recipient IDs. It maintains no message queues or inbox state. The `DiscussionOrchestrator` (`src/discussion/orchestrator.py`) handles message queuing, inbox delivery across rounds, and state persistence.
