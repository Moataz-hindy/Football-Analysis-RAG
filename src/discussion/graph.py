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

    @classmethod
    def build_dynamic_discussion_graph(cls, agents: list[str]) -> "DiscussionGraph":
        """Construct a strongly-connected discussion graph for variable agent counts (2, 3, 4, 5, 6, N).

        Supports dynamic agent selection and custom profile personas.
        Guarantees nx.is_strongly_connected(graph).
        """
        if not agents or len(agents) < 2:
            raise ValueError("Discussion graph requires at least 2 agents.")

        instance = cls.__new__(cls)
        instance.graph = nx.DiGraph()
        unique_agents = list(dict.fromkeys(agents))  # preserve order without dupes
        instance.graph.add_nodes_from(unique_agents)
        n = len(unique_agents)

        if n == 2:
            instance.graph.add_edge(unique_agents[0], unique_agents[1])
            instance.graph.add_edge(unique_agents[1], unique_agents[0])
            return instance

        # Bidirectional ring topology
        for i in range(n):
            u = unique_agents[i]
            v = unique_agents[(i + 1) % n]
            instance.graph.add_edge(u, v)
            instance.graph.add_edge(v, u)

        # Cross-thematic dialogue edges (chords across the circle)
        half = n // 2
        for i in range(n):
            u = unique_agents[i]
            target = unique_agents[(i + half) % n]
            instance.graph.add_edge(u, target)

        if not instance.is_strongly_connected():
            # Safety full-mesh fallback
            for u in unique_agents:
                for v in unique_agents:
                    if u != v:
                        instance.graph.add_edge(u, v)

        return instance


def build_discussion_graph(agents: list[str]) -> DiscussionGraph:
    """Convenience functional wrapper for dynamic discussion graph construction."""
    return DiscussionGraph.build_dynamic_discussion_graph(agents)


# Deterministic order the 2-6 agent presets draw from; the full roster is the
# specialist set the default discussion graph is built from.
DEFAULT_AGENT_ROSTER: tuple[str, ...] = (
    "tactical_analyst",
    "statistical_analyst",
    "performance_analyst",
    "context_analyst",
    "refereeing_analyst",
    "fan_analyst",
)


def select_agent_roster(num_agents: int) -> tuple[str, ...]:
    """Return the agent subset for a 2-6 agent deliberation, in roster order."""
    if not isinstance(num_agents, int) or isinstance(num_agents, bool):
        raise ValueError("The number of discussion agents must be an integer")
    if not 2 <= num_agents <= len(DEFAULT_AGENT_ROSTER):
        raise ValueError(
            f"Choose between 2 and {len(DEFAULT_AGENT_ROSTER)} discussion agents"
        )
    return DEFAULT_AGENT_ROSTER[:num_agents]
