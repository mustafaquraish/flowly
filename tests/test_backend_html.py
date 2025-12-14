from flowly.core.ir import FlowChart, StartNode, EndNode, Edge
from flowly.backend.html import HtmlExporter

def test_html_export_structure():
    """Test that HTML export produces valid structure with bundled flowplay."""
    chart = FlowChart("HtmlTest")
    s = chart.add_node(StartNode(label="Start"))
    e = chart.add_node(EndNode(label="End"))
    chart.add_edge(Edge(s.id, e.id))
    
    html = HtmlExporter.to_html(chart)
    
    # Basic HTML structure
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html
    
    # Should have the flowplay app
    assert "FlowPlay" in html
    assert "class FlowPlay" in html  # FlowPlay class from app.js
    
    # Should contain flow name
    assert "HtmlTest" in html
    
    # Should have the node IDs in the bundled JSON
    assert s.id in html
    assert "StartNode" in html

def test_html_embedded_json():
    """Test that the flow JSON is embedded as bundledFlowJSON."""
    chart = FlowChart("JSON Embed")
    chart.add_node(StartNode(label="Foo"))
    
    html = HtmlExporter.to_html(chart)
    
    # Check for bundled JSON structure
    assert 'const bundledFlowJSON = {' in html
    assert '"nodes":' in html
    assert '"edges":' in html
    assert '"label": "Foo"' in html


def test_html_contains_styles():
    """Test that CSS styles are inlined."""
    chart = FlowChart("StyleTest")
    chart.add_node(StartNode(label="Start"))
    
    html = HtmlExporter.to_html(chart)
    
    # Should have inlined CSS from styles.css
    assert "<style>" in html
    assert "--bg-primary:" in html  # CSS variable from flowplay styles
    assert "#flowchart-container" in html


def test_html_contains_scripts():
    """Test that JS is inlined and external CDNs are preserved."""
    chart = FlowChart("ScriptTest")
    chart.add_node(StartNode(label="Start"))
    
    html = HtmlExporter.to_html(chart)
    
    # Should have inlined app.js content
    assert "class FlowPlay" in html
    assert "loadFlowData" in html
    
    # Should preserve external CDN links
    assert "d3js.org" in html
    assert "dagre" in html
