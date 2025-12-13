import json
from flowly.core.ir import FlowChart, StartNode, ProcessNode, Edge
from flowly.core.serialization import JsonSerializer

def test_json_roundtrip():
    chart = FlowChart("Test")
    n1 = chart.add_node(StartNode(label="S"))
    n2 = chart.add_node(ProcessNode(label="P", metadata={"foo": "bar"}))
    chart.add_edge(Edge(n1.id, n2.id, label="Go"))
    
    json_str = JsonSerializer.to_json(chart)
    
    # Verify JSON structure loosely
    data = json.loads(json_str)
    assert data["name"] == "Test"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    
    # Reconstruct
    chart2 = JsonSerializer.from_json(json_str)
    assert chart2.name == chart.name
    assert len(chart2.nodes) == 2
    
    # Check node reconstruction
    n2_reconstructed = chart2.get_node(n2.id)
    assert isinstance(n2_reconstructed, ProcessNode)
    assert n2_reconstructed.label == "P"
    assert n2_reconstructed.metadata["foo"] == "bar"
    
    # Check edges
    assert len(chart2.edges) == 1
    edge = chart2.edges[0]
    assert edge.source_id == n1.id
    assert edge.target_id == n2.id
