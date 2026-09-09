import sys
import os

# Add root to pythonpath for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.discussion.graph import DiscussionGraph
from src.discussion.router import GraphRouter

def test_graph_connectivity():
    graph = DiscussionGraph()
    is_connected = graph.is_strongly_connected()
    print(f"Graph is strongly connected: {is_connected}")
    assert is_connected, "Graph must be strongly connected!"
    
def test_router_outputs():
    router = GraphRouter()
    
    tactical_recipients = router.get_recipients("tactical_analyst")
    print(f"Tactical Analyst sends to: {tactical_recipients}")
    assert "fan_analyst" in tactical_recipients
    assert "performance_analyst" in tactical_recipients
    
    fan_recipients = router.get_recipients("fan_analyst")
    print(f"Fan Analyst sends to: {fan_recipients}")
    assert "refereeing_analyst" in fan_recipients
    assert "statistical_analyst" in fan_recipients

if __name__ == "__main__":
    print("Running graph routing tests...\n")
    test_graph_connectivity()
    test_router_outputs()
    print("\nAll tests passed successfully!")
