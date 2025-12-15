import pytest
from flowly.core.ir import FlowChart, Node, StartNode, EndNode, ProcessNode, DecisionNode, Edge

def test_node_creation():
    node = Node(label="Test Node")
    assert node.label == "Test Node"
    assert node.id is not None
    assert isinstance(node.metadata, dict)

def test_graph_add_node():
    chart = FlowChart("Test Chart")
    node = StartNode(label="Start")
    chart.add_node(node)
    
    assert node.id in chart.nodes
    assert chart.get_node(node.id) == node

def test_graph_add_edge():
    chart = FlowChart()
    n1 = chart.add_node(StartNode(label="A"))
    n2 = chart.add_node(EndNode(label="B"))
    
    edge = Edge(n1.id, n2.id, label="Go")
    chart.add_edge(edge)
    
    assert len(chart.edges) == 1
    assert chart.edges[0].source_id == n1.id
    assert chart.edges[0].target_id == n2.id

def test_add_duplicate_node_raises_error():
    chart = FlowChart()
    node = Node(node_id="123")
    chart.add_node(node)
    
    with pytest.raises(ValueError):
        chart.add_node(Node(node_id="123"))

def test_add_edge_missing_nodes_raises_error():
    chart = FlowChart()
    n1 = chart.add_node(Node())
    
    with pytest.raises(ValueError):
        chart.add_edge(Edge(n1.id, "missing_id"))

def test_duplicate_edges_are_prevented():
    """Test that duplicate edges (same source, target, label) are not added."""
    chart = FlowChart()
    n1 = chart.add_node(StartNode(label="A"))
    n2 = chart.add_node(EndNode(label="B"))
    
    # Add first edge
    edge1 = Edge(n1.id, n2.id, label="Go")
    chart.add_edge(edge1)
    assert len(chart.edges) == 1
    
    # Try to add duplicate - should not increase edge count
    edge2 = Edge(n1.id, n2.id, label="Go")
    returned_edge = chart.add_edge(edge2)
    assert len(chart.edges) == 1
    assert returned_edge == edge1  # Returns existing edge

def test_different_labeled_edges_are_allowed():
    """Test that edges with different labels between same nodes are allowed."""
    chart = FlowChart()
    n1 = chart.add_node(DecisionNode(label="Check"))
    n2 = chart.add_node(ProcessNode(label="Action"))
    
    # Add edges with different labels
    edge1 = Edge(n1.id, n2.id, label="Yes")
    edge2 = Edge(n1.id, n2.id, label="No")
    chart.add_edge(edge1)
    chart.add_edge(edge2)
    
    assert len(chart.edges) == 2
    labels = [e.label for e in chart.edges]
    assert "Yes" in labels
    assert "No" in labels

def test_unlabeled_duplicate_edges_are_prevented():
    """Test that duplicate edges without labels are prevented."""
    chart = FlowChart()
    n1 = chart.add_node(ProcessNode(label="A"))
    n2 = chart.add_node(ProcessNode(label="B"))
    
    # Add edges without labels
    edge1 = Edge(n1.id, n2.id)
    edge2 = Edge(n1.id, n2.id)
    chart.add_edge(edge1)
    chart.add_edge(edge2)
    
    assert len(chart.edges) == 1

