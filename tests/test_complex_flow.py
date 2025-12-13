from flowly.engine import FlowRunner
from flowly.core.serialization import JsonSerializer
from flowly.backend.mermaid import MermaidExporter
from flowly.backend.graphviz import GraphvizExporter
from flowly.backend.html import HtmlExporter
import graphviz

def test_complex_flow_structure(complex_flowchart):
    # Sanity check size
    assert len(complex_flowchart.nodes) > 15
    assert len(complex_flowchart.edges) > 15
    
    # Ensure start node exists
    start_nodes = [n for n in complex_flowchart.nodes.values() if n.__class__.__name__ == 'StartNode']
    assert len(start_nodes) == 1

def test_complex_flow_serialization_roundtrip(complex_flowchart):
    json_data = JsonSerializer.to_json(complex_flowchart)
    reloaded = JsonSerializer.from_json(json_data)
    
    assert len(reloaded.nodes) == len(complex_flowchart.nodes)
    assert len(reloaded.edges) == len(complex_flowchart.edges)
    assert reloaded.name == complex_flowchart.name

def test_complex_flow_walkthrough_happy_path(complex_flowchart):
    """Path: High Load -> Restart Service -> Resolved"""
    runner = FlowRunner(complex_flowchart)
    runner.start() # Alert Received
    
    # Check Status -> Is Down?
    runner.step() # Check Status
    runner.step() # Is Down?
    
    # Choice: No (Server is Up)
    opts = runner.get_options()
    no_down = next(o for o in opts if o.label == "No")
    runner.choose_path(opts.index(no_down))
    
    # Check Metrics -> High Load?
    runner.step() # Check Metrics -> Moves to High Load
    
    # Choice: Yes
    opts = runner.get_options()
    yes_load = next(o for o in opts if o.label == "Yes")
    runner.choose_path(opts.index(yes_load))
    
    # Identify Top Proc -> Is main app?
    runner.step() # Identify -> Moves to "Is main app?"
    
    # Choice: Yes
    opts = runner.get_options()
    yes_app = next(o for o in opts if o.label == "Yes")
    runner.choose_path(opts.index(yes_app))
    
    # Restart Service -> Latency Normal?
    runner.step() # Restart Service -> Moves to "Latency Normal?"
    
    # Choice: Yes
    opts = runner.get_options()
    yes_fixed = next(o for o in opts if o.label == "Yes")
    runner.choose_path(opts.index(yes_fixed))
    
    # Incident Resolved
    assert runner.current_node.label == "Incident Resolved"

def test_complex_flow_backends_no_crash(complex_flowchart):
    import os
    build_dir = os.path.join(os.path.dirname(__file__), "..", "build")
    os.makedirs(build_dir, exist_ok=True)

    # Mermaid
    mermaid_out = MermaidExporter.to_mermaid(complex_flowchart)
    assert "graph TD" in mermaid_out
    assert "Incident Resolved" in mermaid_out
    
    with open(os.path.join(build_dir, "complex_flow.mmd"), "w") as f:
        f.write(mermaid_out)
    
    # Graphviz
    dot = GraphvizExporter.to_digraph(complex_flowchart)
    assert "digraph" in str(dot)
    
    # Save DOT source
    with open(os.path.join(build_dir, "complex_flow.dot"), "w") as f:
        f.write(dot.source)
        
    # Try to render if dot is installed (might fail if graphviz binary not on system, so just warning or skip)
    # For now we assume strict check is not needed, but let's try-catch to avoid test failure if binary missing
    try:
        GraphvizExporter.render(complex_flowchart, os.path.join(build_dir, "complex_flow"))
    except graphviz.backend.ExecutableNotFound:
        # It's expected in some envs, but the python lib part passed.
        pass

    # HTML Player
    html_out = HtmlExporter.to_html(complex_flowchart)
    assert "<html" in html_out
    
    with open(os.path.join(build_dir, "complex_flow.html"), "w") as f:
        f.write(html_out)
        
    # JSON Artifact for Web App
    json_out = JsonSerializer.to_json(complex_flowchart)
    with open(os.path.join(build_dir, "complex_flow.json"), "w") as f:
        f.write(json_out)
