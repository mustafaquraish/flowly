from flowly.core.ir import FlowChart, StartNode, ProcessNode, Edge, DecisionNode
from flowly.backend.graphviz import GraphvizExporter
import graphviz

def test_to_digraph_structure():
    chart = FlowChart("TestGraph")
    s = chart.add_node(StartNode(label="Start"))
    p = chart.add_node(ProcessNode(label="Proc"))
    chart.add_edge(Edge(s.id, p.id, label="Go"))
    
    dot = GraphvizExporter.to_digraph(chart)
    
    assert isinstance(dot, graphviz.Digraph)
    assert dot.name == "TestGraph"
    
    # Check source contains node labels
    source = dot.source
    assert 'label=Start' in source
    assert 'label=Proc' in source
    assert 'label=Go' in source
    # Check shapes
    assert 'shape=ellipse' in source
    assert 'shape=box' in source

def test_decision_shape():
    chart = FlowChart()
    d = chart.add_node(DecisionNode(label="?"))
    
    dot = GraphvizExporter.to_digraph(chart)
    assert 'shape=diamond' in dot.source
