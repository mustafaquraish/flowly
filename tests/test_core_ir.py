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
