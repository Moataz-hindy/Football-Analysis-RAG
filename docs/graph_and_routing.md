# Agent Graph & Message Routing

This document outlines the design decisions and architecture for the multi-agent graph (Task 4.1) and message routing (Task 4.3) implemented for Week 3.

## 1. How the Graph is Created
The agents are represented as nodes in a directed graph using the `networkx` library (`src/discussion/graph.py`). The relationships (edges) are explicitly defined based on the thematic synergies and natural conflicts between the six personas:
- `context_analyst`
- `fan_analyst`
- `performance_analyst`
- `refereeing_analyst`
- `statistical_analyst`
- `tactical_analyst`

The graph is logically divided into two primary clusters:
- **Data & Tactics Cluster:** Tactical ↔ Performance ↔ Statistical
- **Emotion & Context Cluster:** Fan ↔ Refereeing ↔ Context

We then added specific directed bridge edges between the two clusters to ensure information flows between the analytical and emotional perspectives (e.g., Tactical informs the Fan, Stats grounds Context).

## 2. Why This Approach Was Chosen
We chose a **Persona-Driven Thematic Graph** over a simple "broadcast to everyone" (Complete Graph) or a "Ring Topology".
- A Complete Graph would cause context windows to explode, as every agent would process every message from every round, and it fails the rubric requirement that the graph should have a "meaningful role in determining communication".
- A Ring Topology creates unnatural debate dynamics (e.g., if agent A insults agent F, agent F cannot reply directly).

By explicitly wiring the graph according to persona relationships, we simulate a realistic football panel show where specific domain experts naturally challenge or inform specific counterparts.

## 3. How Strong Connectivity is Guaranteed
Strong connectivity means every agent can eventually reach every other agent through the directed paths of the graph. 

This is mathematically guaranteed on initialization. The `DiscussionGraph` class internally relies on the `networkx.is_strongly_connected(self.graph)` algorithm. If the explicitly configured edges ever fail to form a strongly connected graph, the router raises a `ValueError` immediately upon initialization, preventing an invalid discussion run.

## 4. How the Graph Affects Discussion Behavior
The graph directly dictates the flow of information via the **Stateless Router** (`src/discussion/router.py`). 

When an agent generates a message, it is not broadcast to the entire room. Instead, the `GraphRouter.get_recipients(sender_id)` utility uses the directed edges of the graph to determine exactly which neighbors receive the message. 

Because of this:
- The `Fan Analyst` will primarily react to the `Refereeing Analyst` and `Context Analyst`.
- The `Statistical Analyst` will crunch data for the `Performance` and `Tactical` analysts, while occasionally grounding the `Context Analyst`.

This segmented routing prevents the debate from becoming a chaotic free-for-all, allowing localized sub-debates to form and organically bleed across the network.

## 5. Decoupling from Orchestration
To prevent architectural conflicts with the discussion orchestrator (Task 4.2), the routing logic is implemented as a **stateless utility**. The `GraphRouter` simply takes a sender ID and returns a list of recipient IDs. It does not attempt to manage message queues, inboxes, or blackboard state, leaving the orchestrator completely free to implement push, pull, or framework-specific delivery mechanisms.
