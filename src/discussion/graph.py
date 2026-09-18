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

    @classmethod
    def create_symmetrical_3v3(
        cls,
        camp_a: dict[str, str],
        camp_b: dict[str, str],
    ) -> "DiscussionGraph":
        """Build a strongly-connected symmetrical 3v3 debate graph.

        Connects two opposing camps (Camp A vs. Camp B) where each camp has
        a 'coach', a 'fan', and a 'pundit':
        1. Reciprocal Counterparts (Cross-camp direct ideological clash):
           - coach_a <-> coach_b (tactical chess match)
           - fan_a <-> fan_b (terrace passion & rivalry)
           - pundit_a <-> pundit_b (on-pitch physical reality)
        2. Intra-camp Consultation (allies coordinating arguments):
           - coach_a <-> pundit_a, coach_b <-> pundit_b
           - pundit_a <-> fan_a, pundit_b <-> fan_b
        3. Cross-camp Pressure (interrogating opposing perspectives):
           - coach_a -> fan_b, coach_b -> fan_a
           - fan_a -> pundit_b, fan_b -> pundit_a

        Guarantees nx.is_strongly_connected(graph).
        """
        instance = cls.__new__(cls)
        instance.graph = nx.DiGraph()

        coach_a = camp_a["coach"]
        fan_a = camp_a["fan"]
        pundit_a = camp_a["pundit"]

        coach_b = camp_b["coach"]
        fan_b = camp_b["fan"]
        pundit_b = camp_b["pundit"]

        nodes = [coach_a, fan_a, pundit_a, coach_b, fan_b, pundit_b]
        instance.graph.add_nodes_from(nodes)

        # 1. Reciprocal Cross-Camp Counterparts
        instance.graph.add_edge(coach_a, coach_b)
        instance.graph.add_edge(coach_b, coach_a)

        instance.graph.add_edge(fan_a, fan_b)
        instance.graph.add_edge(fan_b, fan_a)

        instance.graph.add_edge(pundit_a, pundit_b)
        instance.graph.add_edge(pundit_b, pundit_a)

        # 2. Intra-Camp Consultation
        instance.graph.add_edge(coach_a, pundit_a)
        instance.graph.add_edge(pundit_a, coach_a)
        instance.graph.add_edge(coach_b, pundit_b)
        instance.graph.add_edge(pundit_b, coach_b)

        instance.graph.add_edge(pundit_a, fan_a)
        instance.graph.add_edge(fan_a, pundit_a)
        instance.graph.add_edge(pundit_b, fan_b)
        instance.graph.add_edge(fan_b, pundit_b)

        # 3. Cross-Camp Interrogation Bridges
        instance.graph.add_edge(coach_a, fan_b)
        instance.graph.add_edge(coach_b, fan_a)

        instance.graph.add_edge(fan_a, pundit_b)
        instance.graph.add_edge(fan_b, pundit_a)

        if not instance.is_strongly_connected():
            raise ValueError("Generated symmetrical 3v3 graph is not strongly connected")

        return instance
