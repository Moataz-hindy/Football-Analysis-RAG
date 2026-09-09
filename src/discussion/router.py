from typing import List
from src.discussion.graph import DiscussionGraph

class GraphRouter:
    """
    Stateless message router that utilizes the DiscussionGraph to determine
    message recipients without maintaining any inbox state.
    """
    def __init__(self, graph: DiscussionGraph = None):
        self.graph = graph or DiscussionGraph()
        
        if not self.graph.is_strongly_connected():
            raise ValueError(
                "The provided discussion graph is NOT strongly connected. "
                "A strongly connected graph is required for Task 4.1."
            )
            
    def get_recipients(self, sender_id: str) -> List[str]:
        """
        Given a sender, returns the list of agent IDs that should receive the message.
        The orchestrator is responsible for actually delivering the messages.
        """
        return self.graph.get_outbound_edges(sender_id)
