from flowly.core.ir import FlowChart, StartNode, EndNode, Edge
from flowly.backend.html import HtmlExporter

def test_html_export_structure():
    chart = FlowChart("HtmlTest")
    s = chart.add_node(StartNode(label="Start"))
    e = chart.add_node(EndNode(label="End"))
    chart.add_edge(Edge(s.id, e.id))
    
    html = HtmlExporter.to_html(chart)
    
    assert "<!DOCTYPE html>" in html
    assert "class FlowRunner" in html
    assert "HtmlTest" in html
    assert s.id in html
    assert "StartNode" in html

def test_html_embedded_json():
    chart = FlowChart("JSON Embed")
    chart.add_node(StartNode(label="Foo"))
    
    html = HtmlExporter.to_html(chart)
    
    # Check if JSON structure is present roughly
    assert 'const flowData = {' in html
    assert '"nodes":' in html
    assert '"edges":' in html
    assert '"label": "Foo"' in html
