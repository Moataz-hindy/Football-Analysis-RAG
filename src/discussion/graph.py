import networkx as nx

class DiscussionGraph:
    """
    Represents the strongly connected agent communication graph.
    Defines who can speak to whom based on persona synergies and conflicts.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_graph()
        
    def _build_graph(self):
        # 1. Add all persona nodes
        personas = [
            "context_analyst",
            "fan_analyst",
            "performance_analyst",
            "refereeing_analyst",
            "statistical_analyst",
            "tactical_analyst"
        ]
        self.graph.add_nodes_from(personas)
        
        # 2. Add edges (relationships)
        # Reciprocal Core Debate Pairs (Enables direct rebuttal & dialog)
        # Tactical Coach <-> Ex-Player Pundit (tactical theory vs. on-pitch reality)
        self.graph.add_edge("tactical_analyst", "performance_analyst")
        self.graph.add_edge("performance_analyst", "tactical_analyst")

        # Fan Supporter <-> Refereeing Expert (partisan grievance vs. IFAB rules)
        self.graph.add_edge("fan_analyst", "refereeing_analyst")
        self.graph.add_edge("refereeing_analyst", "fan_analyst")

        # Tactical Coach <-> Data Analyst (formation concepts vs. empirical xG validation)
        self.graph.add_edge("tactical_analyst", "statistical_analyst")
        self.graph.add_edge("statistical_analyst", "tactical_analyst")

        # Studio Host / Anchor Moderation & Synthesis
        # Anchor prompts Fan, Coach, and Ex-Player to steer discussion
        self.graph.add_edge("context_analyst", "fan_analyst")
        self.graph.add_edge("context_analyst", "tactical_analyst")
        self.graph.add_edge("context_analyst", "performance_analyst")

        # Core perspectives feed conclusions back to Anchor for round synthesis
        self.graph.add_edge("statistical_analyst", "context_analyst")
        self.graph.add_edge("refereeing_analyst", "context_analyst")
        self.graph.add_edge("performance_analyst", "context_analyst")

        # Cross-Thematic Bridges
        # Fan challenges cold data models
        self.graph.add_edge("fan_analyst", "statistical_analyst")
        # Tactical coach informs the Fan with structural insights
        self.graph.add_edge("tactical_analyst", "fan_analyst")
        # Ex-Player challenges Refereeing interpretation of contact severity
        self.graph.add_edge("performance_analyst", "refereeing_analyst")
        
    def is_strongly_connected(self) -> bool:
        """Verifies that every agent can eventually reach every other agent."""
        return nx.is_strongly_connected(self.graph)
        
    def get_outbound_edges(self, node: str) -> list[str]:
        """Returns the list of agents that should receive a message from the given node."""
        if node not in self.graph:
            raise ValueError(f"Agent '{node}' not found in the discussion graph.")
        return list(self.graph.successors(node))
