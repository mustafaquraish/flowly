from flowly.core.ir import FlowChart, StartNode, EndNode, ProcessNode, DecisionNode, Edge
from flowly.backend.mermaid import MermaidExporter

def test_mermaid_shapes():
    chart = FlowChart("UseShapes")
    s = chart.add_node(StartNode(node_id="A", label="Start"))
    p = chart.add_node(ProcessNode(node_id="B", label="Proc"))
    d = chart.add_node(DecisionNode(node_id="C", label="Disc"))
    e = chart.add_node(EndNode(node_id="D", label="Stop"))
    
    chart.add_edge(Edge(s.id, p.id))
    chart.add_edge(Edge(p.id, d.id))
    chart.add_edge(Edge(d.id, e.id))
    
    output = MermaidExporter.to_mermaid(chart)
    
    assert 'A(["Start"])' in output
    assert 'B["Proc"]' in output
    assert 'C{"Disc"}' in output
    assert 'D(["Stop"])' in output

def test_mermaid_edges_with_labels():
    chart = FlowChart()
    n1 = chart.add_node(StartNode(node_id="A"))
    n2 = chart.add_node(EndNode(node_id="B"))
    chart.add_edge(Edge("A", "B", label="Yes"))
    
    output = MermaidExporter.to_mermaid(chart)
    assert "A -- Yes --> B" in output

def test_mermaid_sanitization():
    chart = FlowChart()
    n1 = chart.add_node(ProcessNode(node_id="A", label='Say "Hello"'))
    
    output = MermaidExporter.to_mermaid(chart)
    assert 'A["Say #quot;Hello#quot;"]' in output
