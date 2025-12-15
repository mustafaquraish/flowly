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
        
        # Code (rendered as italic in Graphviz)
        result = GraphvizExporter._markdown_to_html("`code snippet`")
        assert '<I>code snippet</I>' in result
        
        # Line breaks
        result = GraphvizExporter._markdown_to_html("line1\nline2")
        assert "<BR/>" in result
    
    def test_html_label_without_description(self):
        """Test HTML label generation without description."""
        label = GraphvizExporter._html_label("Simple Label")
        
        # Should be simple bold label
        assert "<B>Simple Label</B>" in label
        assert "<TABLE" not in label
    
    def test_html_label_with_description(self):
        """Test HTML label generation with description."""
        label = GraphvizExporter._html_label("Label", "Description with **bold**")
        
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


class TestGraphvizMarkdownRendering:
    """Test suite for comprehensive markdown rendering in Graphviz."""
    
    def test_complex_markdown_with_headers(self):
        """Test markdown headers are rendered as bold."""
        chart = FlowChart("markdown_test")
        node = ProcessNode(
            label="Step",
            metadata={"description": """Check the following:

## Key Metrics
Monitor these values carefully.

## Warning Signs
Watch for anomalies.
"""}
        )
        chart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(chart)
        source = dot.source
        
        # Headers should be bold, not have ## markers
        assert "<B>Key Metrics</B>" in source
        assert "<B>Warning Signs</B>" in source
        assert "##" not in source
    
    def test_markdown_code_blocks(self):
        """Test inline code rendering."""
        chart = FlowChart("code_test")
        node = ProcessNode(
            label="Command",
            metadata={"description": "Run `ssh user@server` to connect.\n\nThen use `top` command."}
        )
        chart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(chart)
        source = dot.source
        
        # Code should be italicized (we convert ` to <I>)
        assert "<I>ssh user@server</I>" in source
        assert "<I>top</I>" in source
    
    def test_markdown_bold_and_italic(self):
        """Test bold and italic markdown."""
        chart = FlowChart("formatting_test")
        node = ProcessNode(
            label="Formatted",
            metadata={"description": "This is **bold text** and this is *italic text*."}
        )
        chart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(chart)
        source = dot.source
        
        assert "<B>bold text</B>" in source
        assert "<I>italic text</I>" in source
    
    def test_multiline_description_with_lists(self):
        """Test that multiline descriptions with lists are fully displayed."""
        chart = FlowChart("list_test")
        node = ProcessNode(
            label="Steps",
            metadata={"description": """Complete these tasks:

1. First item
2. Second item
3. Third item
4. Fourth item
5. Fifth item

All items should appear in the output.
"""}
        )
        chart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(chart)
        source = dot.source
        
        # All list items should be present (no truncation)
        assert "First item" in source
        assert "Second item" in source
        assert "Third item" in source
        assert "Fourth item" in source
        assert "Fifth item" in source
        assert "All items should appear" in source
        # Should NOT have truncation marker
        assert "..." not in source
    
    def test_very_long_description_no_truncation(self):
        """Test that very long descriptions are NOT truncated with ..."""
        long_desc = "This is a very long description. " * 20  # 700+ chars
        chart = FlowChart("long_test")
        node = ProcessNode(
            label="Long",
            metadata={"description": long_desc}
        )
        chart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(chart)
        source = dot.source
        
        # Full description should be present, no ... truncation
        assert long_desc.replace('\n', '<BR/>') in source or "very long description" in source
        # Check we don't have the old truncation pattern
        word_count = source.count("very long description")
        assert word_count >= 15  # Should have most/all repetitions
    
    def test_mixed_markdown_features(self):
        """Test complex markdown with multiple features."""
        chart = FlowChart("complex_test")
        node = ProcessNode(
            label="Complex",
            metadata={"description": """## Troubleshooting Steps

**Important**: Follow these carefully.

1. Check `systemctl status` output
2. Review logs with `tail -f /var/log/app.log`
3. Verify *network connectivity*

**Note**: Use `sudo` if needed.
"""}
        )
        chart.add_node(node)
        
        dot = GraphvizExporter.to_digraph(chart)
        source = dot.source
        
        # Check all elements are present
        assert "<B>Troubleshooting Steps</B>" in source  # Header
        assert "<B>Important</B>" in source  # Bold
        assert "<I>systemctl status</I>" in source  # Code
        assert "<I>tail -f /var/log/app.log</I>" in source  # Code
        assert "<I>network connectivity</I>" in source  # Italic
        assert "<B>Note</B>" in source  # Bold
        assert "<I>sudo</I>" in source  # Code

