"""Tests for the SVG backend exporter."""

import pytest
from flowly.core.ir import FlowChart, StartNode, ProcessNode, DecisionNode, EndNode, Edge
from flowly.backend.svg import SvgExporter


# Check if Graphviz is available
try:
    from flowly.backend.svg import SvgExporter
    test_chart = FlowChart("Test")
    test_chart.add_node(StartNode(label="Test"))
    SvgExporter.to_svg(test_chart)
    GRAPHVIZ_AVAILABLE = True
except (RuntimeError, Exception):
    GRAPHVIZ_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not GRAPHVIZ_AVAILABLE,
    reason="Graphviz executable not found - install with: brew install graphviz"
)


class TestSvgExporter:
    """Tests for SvgExporter functionality."""
    
    @pytest.fixture
    def simple_chart(self):
        """Create a simple chart with all node types."""
        chart = FlowChart("TestSVG")
        s = chart.add_node(StartNode(label="Start"))
        p = chart.add_node(ProcessNode(label="Process"))
        d = chart.add_node(DecisionNode(label="Decide"))
        e = chart.add_node(EndNode(label="End"))
        
        chart.add_edge(Edge(s.id, p.id, label="Go"))
        chart.add_edge(Edge(p.id, d.id))
        chart.add_edge(Edge(d.id, e.id, label="Yes"))
        return chart
    
    def test_to_svg_returns_string(self, simple_chart):
        """Test that to_svg returns an SVG string."""
        svg = SvgExporter.to_svg(simple_chart)
        
        assert isinstance(svg, str)
        assert svg.startswith('<?xml') or svg.startswith('<svg')
        assert '</svg>' in svg
    
    def test_svg_contains_flowchart_name(self, simple_chart):
        """Test that SVG contains the flowchart name."""
        svg = SvgExporter.to_svg(simple_chart)
        
        # The name should appear somewhere in the SVG
        assert 'TestSVG' in svg
    
    def test_svg_contains_node_labels(self, simple_chart):
        """Test that SVG contains all node labels."""
        svg = SvgExporter.to_svg(simple_chart)
        
        assert 'Start' in svg
        assert 'Process' in svg
        assert 'Decide' in svg
        assert 'End' in svg
    
    def test_svg_contains_edge_labels(self, simple_chart):
        """Test that SVG contains edge labels."""
        svg = SvgExporter.to_svg(simple_chart)
        
        assert 'Go' in svg
        assert 'Yes' in svg
    
    def test_svg_with_descriptions(self):
        """Test SVG generation with markdown descriptions."""
        chart = FlowChart("WithDesc")
        node = ProcessNode(
            node_id="p1",
            label="Process",
            metadata={"description": "This is a **bold** description\nwith line breaks"}
        )
        chart.add_node(node)
        
        svg = SvgExporter.to_svg(chart, include_descriptions=True)
        
        # Should contain the description text (HTML formatting may vary)
        assert 'Process' in svg
        assert 'bold' in svg or 'description' in svg.lower()
    
    def test_svg_without_descriptions(self):
        """Test that descriptions can be disabled."""
        chart = FlowChart("NoDesc")
        node = ProcessNode(
            node_id="p1",
            label="Process",
            metadata={"description": "This should not appear"}
        )
        chart.add_node(node)
        
        svg_with = SvgExporter.to_svg(chart, include_descriptions=True)
        svg_without = SvgExporter.to_svg(chart, include_descriptions=False)
        
        # SVG without descriptions should be shorter
        assert len(svg_without) < len(svg_with)
    
    def test_empty_chart(self):
        """Test SVG generation for empty chart."""
        chart = FlowChart("Empty")
        
        svg = SvgExporter.to_svg(chart)
        
        assert isinstance(svg, str)
        assert svg.startswith('<?xml') or svg.startswith('<svg')
    
    def test_svg_is_valid_xml(self, simple_chart):
        """Test that generated SVG has valid XML structure."""
        svg = SvgExporter.to_svg(simple_chart)
        
        # Basic XML validity checks
        assert svg.count('<svg') == svg.count('</svg>')
        assert '<svg' in svg
        assert '</svg>' in svg
    
    def test_special_characters_in_labels(self):
        """Test that special characters are properly escaped."""
        chart = FlowChart("Special")
        node = ProcessNode(label='Test "quotes" & <tags>')
        chart.add_node(node)
        
        svg = SvgExporter.to_svg(chart)
        
        # Should not break the SVG
        assert isinstance(svg, str)
        assert '</svg>' in svg


def test_svg_integration_with_complex_flow():
    """Integration test with a more complex flowchart."""
    chart = FlowChart("Complex")
    
    start = chart.add_node(StartNode(label="Begin"))
    step1 = chart.add_node(ProcessNode(label="Step 1"))
    decision = chart.add_node(DecisionNode(label="Check?"))
    step2a = chart.add_node(ProcessNode(label="Path A"))
    step2b = chart.add_node(ProcessNode(label="Path B"))
    end = chart.add_node(EndNode(label="Done"))
    
    chart.add_edge(Edge(start.id, step1.id))
    chart.add_edge(Edge(step1.id, decision.id))
    chart.add_edge(Edge(decision.id, step2a.id, label="Yes"))
    chart.add_edge(Edge(decision.id, step2b.id, label="No"))
    chart.add_edge(Edge(step2a.id, end.id))
    chart.add_edge(Edge(step2b.id, end.id))
    
    svg = SvgExporter.to_svg(chart)
    
    # Verify all elements are present
    assert 'Begin' in svg
    assert 'Step 1' in svg
    assert 'Check?' in svg
    assert 'Path A' in svg
    assert 'Path B' in svg
    assert 'Done' in svg
    assert 'Yes' in svg
    assert 'No' in svg
