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
        # Data/Tactics Cluster
        self.graph.add_edge("tactical_analyst", "performance_analyst")
        self.graph.add_edge("performance_analyst", "statistical_analyst")
        self.graph.add_edge("statistical_analyst", "tactical_analyst")
        
        # Emotion/Context Cluster
        self.graph.add_edge("fan_analyst", "refereeing_analyst")
        self.graph.add_edge("refereeing_analyst", "context_analyst")
        self.graph.add_edge("context_analyst", "fan_analyst")
        
        # Cross-Cluster Bridges (to ensure strong connectivity)
        # Tactics informs the Fan
        self.graph.add_edge("tactical_analyst", "fan_analyst")
        # Fan challenges the Statistical analyst
        self.graph.add_edge("fan_analyst", "statistical_analyst")
        # Context explains things to the Tactical analyst
        self.graph.add_edge("context_analyst", "tactical_analyst")
        # Performance challenges the Refereeing
        self.graph.add_edge("performance_analyst", "refereeing_analyst")
        # Refereeing uses Stats
        self.graph.add_edge("refereeing_analyst", "statistical_analyst")
        # Stats grounds Context
        self.graph.add_edge("statistical_analyst", "context_analyst")
        
    def is_strongly_connected(self) -> bool:
        """Verifies that every agent can eventually reach every other agent."""
        return nx.is_strongly_connected(self.graph)
        
    def get_outbound_edges(self, node: str) -> list[str]:
        """Returns the list of agents that should receive a message from the given node."""
        if node not in self.graph:
            raise ValueError(f"Agent '{node}' not found in the discussion graph.")
        return list(self.graph.successors(node))
