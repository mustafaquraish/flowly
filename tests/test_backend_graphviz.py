"""Tests for the Graphviz backend exporter."""

import pytest
import graphviz
from flowly.core.ir import FlowChart, StartNode, ProcessNode, Edge, DecisionNode, EndNode
from flowly.backend.graphviz import GraphvizExporter


class TestGraphvizExporter:
    """Tests for GraphvizExporter functionality."""
    
    @pytest.fixture
    def simple_chart(self):
        """Create a simple chart with all node types."""
        chart = FlowChart("TestGraph")
        s = chart.add_node(StartNode(label="Start"))
        p = chart.add_node(ProcessNode(label="Proc"))
        d = chart.add_node(DecisionNode(label="Decision"))
        e = chart.add_node(EndNode(label="End"))
        
        chart.add_edge(Edge(s.id, p.id, label="Go"))
        chart.add_edge(Edge(p.id, d.id))
        chart.add_edge(Edge(d.id, e.id, label="Yes"))
        return chart
    
    def test_to_digraph_structure(self, simple_chart):
        """Test that to_digraph creates a proper Digraph object."""
        dot = GraphvizExporter.to_digraph(simple_chart)
        
        assert isinstance(dot, graphviz.Digraph)
        assert dot.name == "TestGraph"
        
        source = dot.source
        assert 'label=Start' in source
        assert 'label=Proc' in source
        assert 'label=Go' in source
        assert 'shape=ellipse' in source  # Start/End
        assert 'shape=box' in source  # Process
    
    def test_to_digraph_shapes(self, simple_chart):
        """Test that node types get correct shapes."""
        dot = GraphvizExporter.to_digraph(simple_chart)
        source = dot.source
        
        # Start and End use ellipse
        assert 'shape=ellipse' in source
        # Process uses box
        assert 'shape=box' in source
        # Decision uses diamond
        assert 'shape=diamond' in source
    
    def test_to_dot_returns_string(self, simple_chart):
        """Test that to_dot() returns DOT source as a string."""
        dot_source = GraphvizExporter.to_dot(simple_chart)
        
        assert isinstance(dot_source, str)
        assert "digraph TestGraph" in dot_source
        assert "Start" in dot_source
    
    def test_node_with_description(self):
        """Test node rendering with markdown description in HTML label."""
        flowchart = FlowChart(name="documented")
        node = ProcessNode(
            node_id="p1",
            label="Process",
            metadata={"description": "Processes data\nwith **bold** and *italic* formatting"}
        )
        flowchart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(flowchart)
        source = dot.source
        
        # Should use HTML-like label with table
        assert "<TABLE" in source
        assert "<B>Process</B>" in source
        assert "<BR/>" in source  # Line break from \\n
        assert "<B>bold</B>" in source
        assert "<I>italic</I>" in source
    
    def test_markdown_to_html(self):
        """Test markdown to HTML conversion for Graphviz."""
        # Bold
        result = GraphvizExporter._markdown_to_html("**bold** and __also bold__")
        assert "<B>bold</B>" in result
        assert "<B>also bold</B>" in result
        
        # Italic
        result = GraphvizExporter._markdown_to_html("*italic* and _also italic_")
        assert "<I>italic</I>" in result
        assert "<I>also italic</I>" in result
        
        # Code
        result = GraphvizExporter._markdown_to_html("`code snippet`")
        assert '<FONT FACE="monospace">code snippet</FONT>' in result
        
        # Line breaks
        result = GraphvizExporter._markdown_to_html("line1\nline2")
        assert "<BR/>" in result
        
        # HTML escaping
        result = GraphvizExporter._markdown_to_html("test & <tag>")
        assert "&amp;" in result
        assert "&lt;tag&gt;" in result
    
    def test_html_label_without_description(self):
        """Test HTML label generation without description."""
        label = GraphvizExporter._markdown_to_html_label("Simple Label")
        
        # Should be simple bold label
        assert "<B>Simple Label</B>" in label
        assert "<TABLE" not in label
    
    def test_html_label_with_description(self):
        """Test HTML label generation with description."""
        label = GraphvizExporter._markdown_to_html_label("Label", "Description with **bold**")
        
        # Should have table structure
        assert "<TABLE" in label
        assert "<B>Label</B>" in label
        assert "<B>bold</B>" in label
    
    def test_description_disabled(self):
        """Test that descriptions can be disabled."""
        flowchart = FlowChart(name="nodesc")
        node = ProcessNode(
            node_id="p1",
            label="Process",
            metadata={"description": "This should not appear"}
        )
        flowchart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(flowchart, include_descriptions=False)
        source = dot.source
        
        # Should not have HTML table
        assert "<TABLE" not in source
        assert "This should not appear" not in source
    
    def test_to_dot_matches_to_digraph_source(self, simple_chart):
        """Test that to_dot output matches to_digraph().source."""
        dot_source = GraphvizExporter.to_dot(simple_chart)
        digraph = GraphvizExporter.to_digraph(simple_chart)
        
        assert dot_source == digraph.source
    
    def test_empty_chart(self):
        """Test exporting an empty chart."""
        chart = FlowChart("Empty")
        
        dot = GraphvizExporter.to_digraph(chart)
        
        assert isinstance(dot, graphviz.Digraph)
        assert "Empty" in dot.source
    
    def test_edge_labels_included(self):
        """Test that edge labels are included in output."""
        chart = FlowChart("Labeled Edges")
        a = chart.add_node(ProcessNode(label="A"))
        b = chart.add_node(ProcessNode(label="B"))
        chart.add_edge(Edge(a.id, b.id, label="My Label"))
        
        source = GraphvizExporter.to_dot(chart)
        
        assert "My Label" in source
    
    def test_edge_without_label(self):
        """Test edges without labels don't cause issues."""
        chart = FlowChart("No Label")
        a = chart.add_node(ProcessNode(label="A"))
        b = chart.add_node(ProcessNode(label="B"))
        chart.add_edge(Edge(a.id, b.id))  # No label
        
        source = GraphvizExporter.to_dot(chart)
        
        # Should still have the edge
        assert a.id in source
        assert b.id in source


# Keep original function-based tests for backward compatibility
def test_to_digraph_structure():
    chart = FlowChart("TestGraph")
    s = chart.add_node(StartNode(label="Start"))
    p = chart.add_node(ProcessNode(label="Proc"))
    chart.add_edge(Edge(s.id, p.id, label="Go"))
    
    dot = GraphvizExporter.to_digraph(chart)
    
    assert isinstance(dot, graphviz.Digraph)
    assert dot.name == "TestGraph"
    
    source = dot.source
    assert 'label=Start' in source
    assert 'label=Proc' in source
    assert 'label=Go' in source
    assert 'shape=ellipse' in source
    assert 'shape=box' in source


def test_decision_shape():
    chart = FlowChart()
    d = chart.add_node(DecisionNode(label="?"))
    
    dot = GraphvizExporter.to_digraph(chart)
    assert 'shape=diamond' in dot.source
