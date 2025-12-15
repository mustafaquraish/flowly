"""Tests for the Mermaid backend exporter."""

import pytest
from flowly.core.ir import FlowChart, StartNode, EndNode, ProcessNode, DecisionNode, Edge
from flowly.backend.mermaid import MermaidExporter


class TestMermaidExporter:
    """Tests for MermaidExporter functionality."""
    
    @pytest.fixture
    def simple_chart(self):
        """Create a simple chart with all node types."""
        chart = FlowChart("Test")
        s = chart.add_node(StartNode(node_id="A", label="Start"))
        p = chart.add_node(ProcessNode(node_id="B", label="Proc"))
        d = chart.add_node(DecisionNode(node_id="C", label="Decide"))
        e = chart.add_node(EndNode(node_id="D", label="Stop"))
        
        chart.add_edge(Edge(s.id, p.id))
        chart.add_edge(Edge(p.id, d.id))
        chart.add_edge(Edge(d.id, e.id, label="Yes"))
        return chart
    
    def test_output_starts_with_graph(self, simple_chart):
        """Test output starts with graph directive."""
        output = MermaidExporter.to_mermaid(simple_chart)
        
        assert output.startswith("graph TD")
    
    def test_custom_direction(self, simple_chart):
        """Test custom direction parameter."""
        output_lr = MermaidExporter.to_mermaid(simple_chart, direction="LR")
        output_tb = MermaidExporter.to_mermaid(simple_chart, direction="TB")
        
        assert output_lr.startswith("graph LR")
        assert output_tb.startswith("graph TB")
    
    def test_node_shapes(self, simple_chart):
        """Test correct shapes for each node type."""
        output = MermaidExporter.to_mermaid(simple_chart)
        
        # Start/End use stadium shape: (["..."])
        assert 'A(["Start"])' in output
        assert 'D(["Stop"])' in output
        # Process uses rectangle: ["..."]
        assert 'B["Proc"]' in output
        # Decision uses rhombus: {"..."}
        assert 'C{"Decide"}' in output
    
    def test_edge_with_label(self):
        """Test edges with labels."""
        chart = FlowChart()
        n1 = chart.add_node(StartNode(node_id="A"))
        n2 = chart.add_node(EndNode(node_id="B"))
        chart.add_edge(Edge("A", "B", label="Yes"))
        
        output = MermaidExporter.to_mermaid(chart)
        
        assert "A -- Yes --> B" in output
    
def test_mermaid_edge_with_no_label():
    """Test edge rendering without a label."""
    flowchart = FlowChart(name="simple")
    flowchart.add_node(StartNode(node_id="start", label="Begin"))
    flowchart.add_node(EndNode(node_id="end", label="Finish"))
    flowchart.add_edge(Edge(source_id="start", target_id="end"))  # No label
    
    result = MermaidExporter.to_mermaid(flowchart)
    
    assert "start --> end" in result


def test_mermaid_node_with_description():
    """Test node rendering with markdown description."""
    flowchart = FlowChart(name="documented")
    node = ProcessNode(
        node_id="process1",
        label="Process Data",
        metadata={"description": "This processes the data\nwith **bold** and *italic* text"}
    )
    flowchart.add_node(node)
    
    result = MermaidExporter.to_mermaid(flowchart)
    
    # Check node label includes description in italics
    assert 'process1["Process Data<br/><i>' in result
    assert "This processes the data" in result
    # Check description is visible (not hidden in click handlers)
    assert "<br/>" in result
    assert "<i>" in result and "</i>" in result


def test_mermaid_markdown_conversion():
    """Test markdown to Mermaid conversion."""
    # Line breaks
    assert "<br/>" in MermaidExporter._markdown_to_mermaid("line1\nline2")
    
    # Code blocks become quotes
    assert '"code"' in MermaidExporter._markdown_to_mermaid("`code`")
    
    # Bold is simplified (Mermaid has limited support)
    result = MermaidExporter._markdown_to_mermaid("**bold** text")
    assert "bold" in result
    
    # Italic is simplified
    result = MermaidExporter._markdown_to_mermaid("*italic* text")
    assert "italic" in result


def test_mermaid_description_disabled():
    """Test that descriptions can be disabled."""
    flowchart = FlowChart(name="nodesc")
    node = ProcessNode(
        node_id="p1",
        label="Process",
        metadata={"description": "This should not appear"}
    )
    flowchart.add_node(node)
    
    result = MermaidExporter.to_mermaid(flowchart, include_descriptions=False)
    
    # Description should not be in output
    assert "click p1" not in result
    assert "This should not appear" not in result
    
    
    def test_sanitization_quotes(self):
        """Test that quotes are escaped."""
        chart = FlowChart()
        chart.add_node(ProcessNode(node_id="A", label='Say "Hello"'))
        
        output = MermaidExporter.to_mermaid(chart)
        
        assert '#quot;' in output
        assert '"Hello"' not in output  # Should be escaped
    
    def test_sanitization_parentheses(self):
        """Test that parentheses are escaped."""
        chart = FlowChart()
        chart.add_node(ProcessNode(node_id="A", label="Call func()"))
        
        output = MermaidExporter.to_mermaid(chart)
        
        assert "#40;" in output  # (
        assert "#41;" in output  # )
    
    def test_empty_chart(self):
        """Test exporting an empty chart."""
        chart = FlowChart("Empty")
        
        output = MermaidExporter.to_mermaid(chart)
        
        assert output == "graph TD"
    
    def test_edge_label_sanitization(self):
        """Test that edge labels are also sanitized."""
        chart = FlowChart()
        a = chart.add_node(ProcessNode(node_id="A", label="A"))
        b = chart.add_node(ProcessNode(node_id="B", label="B"))
        chart.add_edge(Edge("A", "B", label='Has "quotes"'))
        
        output = MermaidExporter.to_mermaid(chart)
        
        assert "#quot;" in output


# Keep original function-based tests for backward compatibility
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


class TestMermaidMarkdownRendering:
    """Test suite for comprehensive markdown rendering in Mermaid."""
    
    def test_markdown_headers_stripped(self):
        """Test that markdown headers have ## markers removed."""
        chart = FlowChart("header_test")
        node = ProcessNode(
            label="Check",
            metadata={"description": """## Important Steps

Follow these carefully.

## Warning
Be cautious.
"""}
        )
        chart.add_node(node)
        
        output = MermaidExporter.to_mermaid(chart)
        
        # Headers should NOT have ## markers
        assert "##" not in output
        # But the text should be there
        assert "Important Steps" in output
        assert "Warning" in output
    
    def test_full_multiline_description_displayed(self):
        """Test that full multiline descriptions are displayed without truncation."""
        chart = FlowChart("multiline_test")
        node = ProcessNode(
            label="Process",
            metadata={"description": """Line 1 of description
Line 2 of description
Line 3 of description
Line 4 of description
Line 5 of description"""}
        )
        chart.add_node(node)
        
        output = MermaidExporter.to_mermaid(chart)
        
        # All lines should be present (no ... truncation)
        assert "Line 1 of description" in output
        assert "Line 2 of description" in output
        assert "Line 3 of description" in output
        assert "Line 4 of description" in output
        assert "Line 5 of description" in output
        # Line breaks should be converted to <br/>
        assert "<br/>" in output
    
    def test_no_ellipsis_truncation(self):
        """Test that descriptions are NOT truncated with ..."""
        chart = FlowChart("truncation_test")
        node = ProcessNode(
            label="Node",
            metadata={"description": "This is a moderately long description that should be displayed in full without any truncation markers."}
        )
        chart.add_node(node)
        
        output = MermaidExporter.to_mermaid(chart)
        
        # Full text should be present
        assert "moderately long description" in output
        assert "displayed in full" in output
        assert "without any truncation markers" in output
        # Should NOT have ellipsis
        assert "..." not in output
    
    def test_complex_markdown_features(self):
        """Test that complex markdown is properly converted."""
        chart = FlowChart("complex_test")
        node = ProcessNode(
            label="Commands",
            metadata={"description": """## Run These Commands

Execute `ping -c 5 server` first.

Then run `ssh admin@server`.

**Important**: Use sudo if needed.
*Note*: Check logs after.
"""}
        )
        chart.add_node(node)
        
        output = MermaidExporter.to_mermaid(chart)
        
        # Check markdown is converted
        assert "##" not in output  # Headers stripped
        assert "Run These Commands" in output
        assert "ping -c 5 server" in output  # Code converted
        assert "ssh admin@server" in output
        assert "Important" in output  # Bold converted
        assert "Note" in output  # Italic converted
        assert "<br/>" in output  # Line breaks
    
    def test_very_long_description_no_truncation(self):
        """Test that very long descriptions are fully displayed."""
        long_desc = """This is the first line of a very long description.
And this is the second line which continues.
Third line adds more information.
Fourth line provides additional details.
Fifth line concludes the extensive description.
Sixth line to ensure we're well past any truncation threshold.
Seventh line for good measure.
Eighth line to be absolutely certain."""
        
        chart = FlowChart("long_desc_test")
        node = ProcessNode(
            label="Long",
            metadata={"description": long_desc}
        )
        chart.add_node(node)
        
        output = MermaidExporter.to_mermaid(chart)
        
        # All lines should be present
        assert "first line" in output
        assert "second line" in output
        assert "Third line" in output
        assert "Fourth line" in output
        assert "Fifth line" in output
        assert "Sixth line" in output
        assert "Seventh line" in output
        assert "Eighth line" in output
        # No truncation
        assert "..." not in output
    
    def test_list_items_fully_displayed(self):
        """Test that numbered lists are fully displayed."""
        chart = FlowChart("list_test")
        node = ProcessNode(
            label="Checklist",
            metadata={"description": """Complete these:

1. First task
2. Second task  
3. Third task
4. Fourth task
5. Fifth task
6. Sixth task
"""}
        )
        chart.add_node(node)
        
        output = MermaidExporter.to_mermaid(chart)
        
        # All list items should appear
        assert "First task" in output
        assert "Second task" in output
        assert "Third task" in output
        assert "Fourth task" in output
        assert "Fifth task" in output
        assert "Sixth task" in output
        assert "..." not in output

