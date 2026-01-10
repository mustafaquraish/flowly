"""
Comprehensive tests for backend exporters with MultiFlowChart support.

Uses the SAME flow definitions as test_zz_e2e.py to ensure consistency.
Tests all backends (Mermaid, Graphviz, SVG, HTML, JSON) with:
- The complex single flowchart (COMPLEX_SINGLE_FLOW)
- The complex multi-chart flow (COMPLEX_MULTI_FLOW)
- Same edge and node expectations as the E2E tests
- CLI export for all format combinations
"""

import pytest
import tempfile
import subprocess
import sys
from pathlib import Path

from flowly.backend.mermaid import MermaidExporter
from flowly.backend.graphviz import GraphvizExporter
from flowly.backend.html import HtmlExporter
from flowly.backend.svg import SvgExporter
from flowly.core.serialization import JsonSerializer


# =============================================================================
# Shared Flow Definitions - IDENTICAL to test_zz_e2e.py
# =============================================================================

COMPLEX_SINGLE_FLOW = """
from flowly.frontend.dsl import Flow, Node, Decision

# Define nodes with descriptions containing markdown links
start_check = Decision("Initial check?", description="See the [troubleshooting guide](https://wiki.example.com/troubleshoot) for details")
process_a = Node("Process A", description="First processing step. Check [docs](https://docs.example.com/process-a) for more info.")
process_b = Node("Process B", description="Second processing step with **bold** and *italic* text")
branch = Decision("Branch decision?", yes_label="Left", no_label="Right", description="Review [decision matrix](https://wiki.example.com/matrix)")
left_process = Node("Left Path", description="Handle left branch - see `config.yaml` for settings")
right_process = Node("Right Path", description="Handle right branch per [SOP](https://wiki.example.com/sop)")
continue_check = Decision("Continue loop?", yes_label="Yes", no_label="Done")

@Flow("Complex Single Flow")
def complex_flow(flow):
    # Initial branching
    if start_check():
        process_a()
    else:
        process_b()

    # Loop with branching inside
    while continue_check():
        if branch():
            left_process()
        else:
            right_process()
        continue

    flow.end("Flow Complete")
"""

COMPLEX_MULTI_FLOW = '''
from flowly.frontend.dsl import Flow, Subflow, Node, Decision

# Forward declaration pattern - subflows can reference each other before definition
# The order of definitions doesn't matter!

# Define all decisions at module level
is_resolved = Decision("Issue fully resolved?")
is_complex = Decision("Is it a complex issue?")
needs_analysis = Decision("Needs deeper analysis?")
is_urgent = Decision("Is it urgent?")

@Subflow("Quick Fix")
def quick_fix(flow):
    """Simple fix that doesn't need escalation."""
    flow.step("Apply known fix")
    flow.step("Verify fix worked")
    flow.end("Quick fix complete")

@Subflow("Resolve")
def resolve_issue(flow):
    """Resolution process - may loop back to analyze if not fully resolved."""
    flow.step("Implement solution")
    flow.step("Run validation tests")
    
    if is_resolved():
        flow.end("Resolution complete")
    else:
        # Circular reference back to analyze!
        analyze_issue()

@Subflow("Escalate")
def escalate_issue(flow):
    """Escalation process for complex issues."""
    flow.step("Contact senior engineer")
    flow.step("Document issue details")
    flow.step("Schedule review meeting")
    # Escalation leads to resolution
    resolve_issue()

@Subflow("Analyze")
def analyze_issue(flow):
    """Deep analysis - determines next steps."""
    flow.step("Gather logs and metrics")
    flow.step("Identify root cause")
    
    if is_complex():
        escalate_issue()  # Forward reference - escalate defined above
    else:
        quick_fix()  # Simple issues get quick fix

@Subflow("Triage")
def triage_issue(flow):
    """Initial triage process."""
    flow.step("Review incoming ticket")
    flow.step("Check for duplicates")
    
    if needs_analysis():
        analyze_issue()
    else:
        flow.step("Close as duplicate/invalid")
        flow.end("Triage complete - no action needed")

@Flow("Support Workflow")
def support_workflow(flow):
    """Main support workflow with multiple linked subflows."""
    flow.step("Receive support request")
    
    if is_urgent():
        # Urgent issues go straight to analysis
        analyze_issue()
    else:
        # Normal flow through triage
        triage_issue()
    
    flow.end("Workflow complete")
'''

# Expected edges for COMPLEX_SINGLE_FLOW - same as test_zz_e2e.py
SINGLE_FLOW_EXPECTED_EDGES = [
    # (source_label, target_label, edge_label or None)
    ("Complex Single Flow", "Initial check?", None),  # Start -> first decision
    ("Initial check?", "Process A", "Yes"),
    ("Initial check?", "Process B", "No"),
    ("Process A", "Continue loop?", None),
    ("Process B", "Continue loop?", None),
    ("Continue loop?", "Branch decision?", "Yes"),
    ("Continue loop?", "Flow Complete", "Done"),
    ("Branch decision?", "Left Path", "Left"),
    ("Branch decision?", "Right Path", "Right"),
    ("Left Path", "Continue loop?", None),  # Loop back
    ("Right Path", "Continue loop?", None),  # Loop back
]

# Expected chart names for COMPLEX_MULTI_FLOW - same as test_zz_e2e.py
MULTI_FLOW_EXPECTED_CHARTS = [
    "Support Workflow", "Triage", "Analyze", "Escalate", "Resolve", "Quick Fix"
]


# =============================================================================
# Helper to load flow from code string
# =============================================================================

def load_flow_from_code(code: str, flow_name: str, get_multi: bool = False):
    """
    Execute flow code and return the chart or multi_chart.
    
    We write to a temp file because the DSL uses inspect.getsource()
    which requires the code to exist as an actual file.
    """
    import tempfile
    import importlib.util
    import os
    
    # Write code to a temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        # Load as a module
        spec = importlib.util.spec_from_file_location("temp_flow_module", temp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the flow by name
        for name, obj in module.__dict__.items():
            if hasattr(obj, 'chart') and hasattr(obj, 'name') and obj.name == flow_name:
                if get_multi and hasattr(obj, 'multi_chart'):
                    return obj.multi_chart
                return obj.chart
        
        raise ValueError(f"Flow '{flow_name}' not found in code")
    finally:
        # Clean up temp file
        os.unlink(temp_path)


def load_single_flow():
    """Load the COMPLEX_SINGLE_FLOW and return the chart."""
    return load_flow_from_code(COMPLEX_SINGLE_FLOW, "Complex Single Flow")


def load_multi_flow():
    """Load the COMPLEX_MULTI_FLOW and return the multi_chart."""
    return load_flow_from_code(COMPLEX_MULTI_FLOW, "Support Workflow", get_multi=True)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def single_flow_chart():
    """The complex single flowchart from test_zz_e2e.py."""
    return load_single_flow()


@pytest.fixture
def multi_flow_chart():
    """The complex multi-flowchart from test_zz_e2e.py."""
    return load_multi_flow()


# =============================================================================
# Mermaid Backend Tests - Complex Single Flow
# =============================================================================

class TestMermaidSingleFlow:
    """Test MermaidExporter with the COMPLEX_SINGLE_FLOW."""

    def test_contains_all_node_labels(self, single_flow_chart):
        """Test that all expected node labels are present."""
        output = MermaidExporter.to_mermaid(single_flow_chart)
        
        # All labels from SINGLE_FLOW_EXPECTED_EDGES
        expected_labels = set()
        for source, target, _ in SINGLE_FLOW_EXPECTED_EDGES:
            expected_labels.add(source)
            expected_labels.add(target)
        
        for label in expected_labels:
            assert label in output, f"Missing node label in Mermaid: {label}"

    def test_contains_all_edge_labels(self, single_flow_chart):
        """Test that all expected edge labels are present."""
        output = MermaidExporter.to_mermaid(single_flow_chart)
        
        for _, _, edge_label in SINGLE_FLOW_EXPECTED_EDGES:
            if edge_label:
                assert edge_label in output, f"Missing edge label in Mermaid: {edge_label}"

    def test_decision_nodes_use_diamond_shape(self, single_flow_chart):
        """Test that DecisionNodes use diamond/rhombus shape with icon."""
        output = MermaidExporter.to_mermaid(single_flow_chart)
        
        # Decision nodes should use {"..."} shape with ◆ icon
        assert '{"◆' in output  # Diamond icon for decisions
        assert 'Initial check?' in output
        assert 'Branch decision?' in output
        assert 'Continue loop?' in output

    def test_start_end_nodes_use_stadium_shape(self, single_flow_chart):
        """Test that Start/End nodes use stadium shape with icons."""
        output = MermaidExporter.to_mermaid(single_flow_chart)
        
        # Start/End nodes should use (["..."]) shape with icons
        assert '(["▶' in output  # Start icon
        assert '(["⏹' in output  # End icon
        assert 'Complex Single Flow' in output
        assert 'Flow Complete' in output

    def test_process_nodes_use_rectangle_shape(self, single_flow_chart):
        """Test that ProcessNodes use rectangle shape."""
        output = MermaidExporter.to_mermaid(single_flow_chart)
        
        # Process nodes should use ["..."] shape
        # These may have description text appended after them
        assert '["Process A' in output
        assert '["Process B' in output
        assert '["Left Path' in output
        assert '["Right Path' in output

    def test_graph_direction(self, single_flow_chart):
        """Test that graph starts with correct direction."""
        output_td = MermaidExporter.to_mermaid(single_flow_chart, direction="TD")
        output_lr = MermaidExporter.to_mermaid(single_flow_chart, direction="LR")
        
        assert output_td.startswith("graph TD")
        assert output_lr.startswith("graph LR")


# =============================================================================
# Mermaid Backend Tests - Complex Multi Flow
# =============================================================================

class TestMermaidMultiFlow:
    """Test MermaidExporter with the COMPLEX_MULTI_FLOW."""

    def test_contains_all_chart_names(self, multi_flow_chart):
        """Test that all expected chart names are present as subgraphs."""
        output = MermaidExporter.to_mermaid(multi_flow_chart)
        
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            # Chart names may have spaces replaced with underscores
            assert chart_name in output or chart_name.replace(" ", "_") in output, \
                f"Missing chart name in Mermaid: {chart_name}"

    def test_has_subgraphs(self, multi_flow_chart):
        """Test that MultiFlowChart creates Mermaid subgraphs."""
        output = MermaidExporter.to_mermaid(multi_flow_chart)
        
        assert "subgraph" in output
        assert output.count("subgraph") == 6  # 6 charts
        assert output.count("end") >= 6  # 6 subgraph closings

    def test_subflow_nodes_use_special_shape(self, multi_flow_chart):
        """Test that SubFlowNodes use the subroutine shape [[...]]."""
        output = MermaidExporter.to_mermaid(multi_flow_chart)
        
        # SubFlowNode should use [[...]] shape
        assert "[[" in output and "]]" in output

    def test_no_cross_chart_edges_in_static_output(self, multi_flow_chart):
        """Test that cross-chart edges are NOT rendered (to reduce noise)."""
        output = MermaidExporter.to_mermaid(multi_flow_chart)
        
        # Cross-chart links should NOT be rendered in static mermaid output
        # (they are only useful in interactive HTML viewer)
        assert "-.->" not in output

    def test_contains_decision_labels(self, multi_flow_chart):
        """Test that all decision labels are present."""
        output = MermaidExporter.to_mermaid(multi_flow_chart)
        
        expected_decisions = [
            "Issue fully resolved?",
            "Is it a complex issue?",
            "Needs deeper analysis?",
            "Is it urgent?",
        ]
        for decision in expected_decisions:
            assert decision in output, f"Missing decision in Mermaid: {decision}"

    def test_contains_process_step_labels(self, multi_flow_chart):
        """Test that key process steps are present."""
        output = MermaidExporter.to_mermaid(multi_flow_chart)
        
        expected_steps = [
            "Receive support request",
            "Apply known fix",
            "Verify fix worked",
            "Implement solution",
            "Run validation tests",
            "Contact senior engineer",
            "Gather logs and metrics",
            "Identify root cause",
            "Review incoming ticket",
            "Check for duplicates",
        ]
        for step in expected_steps:
            assert step in output, f"Missing process step in Mermaid: {step}"


# =============================================================================
# Graphviz Backend Tests - Complex Single Flow
# =============================================================================

class TestGraphvizSingleFlow:
    """Test GraphvizExporter with the COMPLEX_SINGLE_FLOW."""

    def test_contains_all_node_labels(self, single_flow_chart):
        """Test that all expected node labels are present."""
        output = GraphvizExporter.to_dot(single_flow_chart)
        
        expected_labels = set()
        for source, target, _ in SINGLE_FLOW_EXPECTED_EDGES:
            expected_labels.add(source)
            expected_labels.add(target)
        
        for label in expected_labels:
            assert label in output, f"Missing node label in Graphviz: {label}"

    def test_contains_all_edge_labels(self, single_flow_chart):
        """Test that all expected edge labels are present."""
        output = GraphvizExporter.to_dot(single_flow_chart)
        
        for _, _, edge_label in SINGLE_FLOW_EXPECTED_EDGES:
            if edge_label:
                assert edge_label in output, f"Missing edge label in Graphviz: {edge_label}"

    def test_decision_nodes_use_box_with_indicator(self, single_flow_chart):
        """Test that DecisionNodes use box shape with diamond indicator in label."""
        output = GraphvizExporter.to_dot(single_flow_chart)
        
        # Decisions use box shape (not diamond) to avoid stretching
        # The ◆ indicator in the label identifies them as decisions
        assert '"◆ ' in output  # Diamond indicator for decisions
        assert 'Initial check?' in output
        assert 'shape=box' in output

    def test_start_end_nodes_use_ellipse_shape(self, single_flow_chart):
        """Test that Start/End nodes use ellipse shape."""
        output = GraphvizExporter.to_dot(single_flow_chart)
        
        assert "shape=ellipse" in output

    def test_process_nodes_use_box_shape(self, single_flow_chart):
        """Test that ProcessNodes use box shape."""
        output = GraphvizExporter.to_dot(single_flow_chart)
        
        assert "shape=box" in output

    def test_returns_valid_digraph(self, single_flow_chart):
        """Test that output is a valid digraph."""
        import graphviz
        dot = GraphvizExporter.to_digraph(single_flow_chart)
        
        assert isinstance(dot, graphviz.Digraph)
        assert dot.name == "Complex Single Flow"


# =============================================================================
# Graphviz Backend Tests - Complex Multi Flow
# =============================================================================

class TestGraphvizMultiFlow:
    """Test GraphvizExporter with the COMPLEX_MULTI_FLOW."""

    def test_contains_all_chart_names(self, multi_flow_chart):
        """Test that all expected chart names are present as clusters."""
        output = GraphvizExporter.to_dot(multi_flow_chart)
        
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in output, f"Missing chart name in Graphviz: {chart_name}"

    def test_has_cluster_subgraphs(self, multi_flow_chart):
        """Test that MultiFlowChart creates Graphviz cluster subgraphs."""
        output = GraphvizExporter.to_dot(multi_flow_chart)
        
        # Graphviz may quote the cluster name
        assert 'subgraph "cluster_' in output or 'subgraph cluster_' in output

    def test_subflow_nodes_use_box_with_indicator(self, multi_flow_chart):
        """Test that SubFlowNodes use box shape with clipboard indicator in label."""
        output = GraphvizExporter.to_dot(multi_flow_chart)
        
        # SubFlowNodes use box shape with 📋 indicator
        assert '"📋 ' in output  # Clipboard indicator for subflow nodes
        assert 'shape=box' in output

    def test_no_cross_chart_edges_in_static_output(self, multi_flow_chart):
        """Test that cross-chart edges are NOT rendered (to reduce noise)."""
        output = GraphvizExporter.to_dot(multi_flow_chart)
        
        # Cross-chart links should NOT be rendered in static graphviz output
        # (they are only useful in interactive HTML viewer)
        # We verify by checking there's no "go to" label which would be on cross-chart edges
        assert 'label="go to"' not in output

    def test_contains_decision_labels(self, multi_flow_chart):
        """Test that all decision labels are present."""
        output = GraphvizExporter.to_dot(multi_flow_chart)
        
        expected_decisions = [
            "Issue fully resolved?",
            "Is it a complex issue?",
            "Needs deeper analysis?",
            "Is it urgent?",
        ]
        for decision in expected_decisions:
            assert decision in output, f"Missing decision in Graphviz: {decision}"

    def test_contains_process_step_labels(self, multi_flow_chart):
        """Test that key process steps are present."""
        output = GraphvizExporter.to_dot(multi_flow_chart)
        
        expected_steps = [
            "Receive support request",
            "Apply known fix",
            "Implement solution",
            "Contact senior engineer",
            "Gather logs and metrics",
            "Review incoming ticket",
        ]
        for step in expected_steps:
            assert step in output, f"Missing process step in Graphviz: {step}"

    def test_returns_valid_digraph(self, multi_flow_chart):
        """Test that output is a valid digraph."""
        import graphviz
        dot = GraphvizExporter.to_digraph(multi_flow_chart)
        
        assert isinstance(dot, graphviz.Digraph)
        assert dot.name == "Support Workflow"


# =============================================================================
# HTML Backend Tests - Complex Single Flow
# =============================================================================

class TestHtmlSingleFlow:
    """Test HtmlExporter with the COMPLEX_SINGLE_FLOW."""

    def test_produces_valid_html(self, single_flow_chart):
        """Test that output is valid HTML structure."""
        html = HtmlExporter.to_html(single_flow_chart)
        
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "FlowPlay" in html

    def test_contains_bundled_json(self, single_flow_chart):
        """Test that flow JSON is embedded."""
        html = HtmlExporter.to_html(single_flow_chart)
        
        assert "bundledFlowJSON" in html
        assert '"nodes":' in html
        assert '"edges":' in html

    def test_contains_all_node_labels(self, single_flow_chart):
        """Test that all expected node labels are in the JSON."""
        html = HtmlExporter.to_html(single_flow_chart)
        
        expected_labels = set()
        for source, target, _ in SINGLE_FLOW_EXPECTED_EDGES:
            expected_labels.add(source)
            expected_labels.add(target)
        
        for label in expected_labels:
            assert label in html, f"Missing node label in HTML: {label}"

    def test_contains_node_types(self, single_flow_chart):
        """Test that node types are present in JSON."""
        html = HtmlExporter.to_html(single_flow_chart)
        
        assert "StartNode" in html
        assert "EndNode" in html
        assert "DecisionNode" in html
        assert "ProcessNode" in html

    def test_contains_styles_and_scripts(self, single_flow_chart):
        """Test that CSS and JS are bundled."""
        html = HtmlExporter.to_html(single_flow_chart)
        
        assert "<style>" in html
        assert "class FlowPlay" in html
        assert "d3js.org" in html
        assert "dagre" in html


# =============================================================================
# HTML Backend Tests - Complex Multi Flow
# =============================================================================

class TestHtmlMultiFlow:
    """Test HtmlExporter with the COMPLEX_MULTI_FLOW."""

    def test_produces_valid_html(self, multi_flow_chart):
        """Test that output is valid HTML structure."""
        html = HtmlExporter.to_html(multi_flow_chart)
        
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_contains_multi_chart_json_structure(self, multi_flow_chart):
        """Test that MultiFlowChart JSON structure is correct."""
        html = HtmlExporter.to_html(multi_flow_chart)
        
        assert '"charts":' in html
        assert '"mainChartId":' in html
        # The isMultiChart flag is computed at runtime in JS based on "charts" presence
        # Just verify the multi-chart structure exists
        assert '"name": "Support Workflow"' in html or '"name":"Support Workflow"' in html

    def test_contains_all_chart_names(self, multi_flow_chart):
        """Test that all chart names are in the JSON."""
        html = HtmlExporter.to_html(multi_flow_chart)
        
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in html, f"Missing chart name in HTML: {chart_name}"

    def test_contains_subflow_node_type(self, multi_flow_chart):
        """Test that SubFlowNode type is in the JSON."""
        html = HtmlExporter.to_html(multi_flow_chart)
        
        assert "SubFlowNode" in html
        assert "targetChartId" in html

    def test_contains_decision_labels(self, multi_flow_chart):
        """Test that all decision labels are in the JSON."""
        html = HtmlExporter.to_html(multi_flow_chart)
        
        expected_decisions = [
            "Issue fully resolved?",
            "Is it a complex issue?",
            "Needs deeper analysis?",
            "Is it urgent?",
        ]
        for decision in expected_decisions:
            assert decision in html, f"Missing decision in HTML: {decision}"

    def test_six_charts_in_json(self, multi_flow_chart):
        """Test that all 6 charts are present (main + 5 subflows)."""
        html = HtmlExporter.to_html(multi_flow_chart)
        
        # Count chart name occurrences - each should appear at least once
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in html


# =============================================================================
# Cross-Backend Consistency Tests
# =============================================================================

class TestCrossBackendConsistency:
    """Test that all backends produce consistent output for the same flows."""

    def test_single_flow_same_node_count(self, single_flow_chart):
        """Test that all backends reference the same number of nodes."""
        mermaid = MermaidExporter.to_mermaid(single_flow_chart)
        graphviz = GraphvizExporter.to_dot(single_flow_chart)
        html = HtmlExporter.to_html(single_flow_chart)
        
        # All expected labels should be in all outputs
        expected_labels = set()
        for source, target, _ in SINGLE_FLOW_EXPECTED_EDGES:
            expected_labels.add(source)
            expected_labels.add(target)
        
        for label in expected_labels:
            assert label in mermaid, f"Missing in Mermaid: {label}"
            assert label in graphviz, f"Missing in Graphviz: {label}"
            assert label in html, f"Missing in HTML: {label}"

    def test_multi_flow_same_chart_count(self, multi_flow_chart):
        """Test that all backends reference the same charts."""
        mermaid = MermaidExporter.to_mermaid(multi_flow_chart)
        graphviz = GraphvizExporter.to_dot(multi_flow_chart)
        html = HtmlExporter.to_html(multi_flow_chart)
        
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            # Allow for space/underscore variations
            mermaid_has = chart_name in mermaid or chart_name.replace(" ", "_") in mermaid
            graphviz_has = chart_name in graphviz
            html_has = chart_name in html
            
            assert mermaid_has, f"Missing chart in Mermaid: {chart_name}"
            assert graphviz_has, f"Missing chart in Graphviz: {chart_name}"
            assert html_has, f"Missing chart in HTML: {chart_name}"

    def test_decision_nodes_in_all_backends(self, multi_flow_chart):
        """Test that all decisions appear in all backend outputs."""
        mermaid = MermaidExporter.to_mermaid(multi_flow_chart)
        graphviz = GraphvizExporter.to_dot(multi_flow_chart)
        html = HtmlExporter.to_html(multi_flow_chart)
        
        expected_decisions = [
            "Issue fully resolved?",
            "Is it a complex issue?",
            "Needs deeper analysis?",
            "Is it urgent?",
        ]
        
        for decision in expected_decisions:
            assert decision in mermaid, f"Missing decision in Mermaid: {decision}"
            assert decision in graphviz, f"Missing decision in Graphviz: {decision}"
            assert decision in html, f"Missing decision in HTML: {decision}"


# =============================================================================
# CLI Export Tests - All Formats for Single Flow
# =============================================================================

class TestCLISingleFlowExport:
    """Test CLI export for COMPLEX_SINGLE_FLOW in all formats."""

    @pytest.fixture
    def single_flow_file(self, tmp_path):
        """Create a temp file with the single flow code."""
        flow_file = tmp_path / "single_flow.py"
        flow_file.write_text(COMPLEX_SINGLE_FLOW)
        return flow_file

    def test_cli_export_single_flow_html(self, single_flow_file, tmp_path):
        """Test CLI export to HTML format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(single_flow_file), 
             "-o", str(output_dir), "-f", "html"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        # Verify output file exists and contains expected content
        html_files = list(output_dir.glob("*.html"))
        assert len(html_files) == 1
        content = html_files[0].read_text()
        assert "Complex Single Flow" in content
        assert "Initial check?" in content

    def test_cli_export_single_flow_mermaid(self, single_flow_file, tmp_path):
        """Test CLI export to Mermaid format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(single_flow_file),
             "-o", str(output_dir), "-f", "mermaid"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        mmd_files = list(output_dir.glob("*.mmd"))
        assert len(mmd_files) == 1
        content = mmd_files[0].read_text()
        assert "graph TD" in content
        assert "Initial check?" in content

    def test_cli_export_single_flow_graphviz(self, single_flow_file, tmp_path):
        """Test CLI export to Graphviz format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(single_flow_file),
             "-o", str(output_dir), "-f", "graphviz"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        dot_files = list(output_dir.glob("*.dot"))
        assert len(dot_files) == 1
        content = dot_files[0].read_text()
        assert "digraph" in content
        assert "Initial check?" in content

    def test_cli_export_single_flow_json(self, single_flow_file, tmp_path):
        """Test CLI export to JSON format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(single_flow_file),
             "-o", str(output_dir), "-f", "json"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) == 1
        content = json_files[0].read_text()
        assert '"nodes":' in content
        assert "Initial check?" in content


# =============================================================================
# CLI Export Tests - All Formats for Multi Flow
# =============================================================================

class TestCLIMultiFlowExport:
    """Test CLI export for COMPLEX_MULTI_FLOW in all formats."""

    @pytest.fixture
    def multi_flow_file(self, tmp_path):
        """Create a temp file with the multi flow code."""
        flow_file = tmp_path / "multi_flow.py"
        flow_file.write_text(COMPLEX_MULTI_FLOW)
        return flow_file

    def test_cli_export_multi_flow_html(self, multi_flow_file, tmp_path):
        """Test CLI export MultiFlowChart to HTML format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(multi_flow_file),
             "-o", str(output_dir), "-f", "html"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        html_files = list(output_dir.glob("*.html"))
        assert len(html_files) == 1
        content = html_files[0].read_text()
        
        # Verify multi-chart structure
        assert '"charts":' in content
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in content, f"Missing chart: {chart_name}"

    def test_cli_export_multi_flow_mermaid(self, multi_flow_file, tmp_path):
        """Test CLI export MultiFlowChart to Mermaid format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(multi_flow_file),
             "-o", str(output_dir), "-f", "mermaid"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        mmd_files = list(output_dir.glob("*.mmd"))
        assert len(mmd_files) == 1
        content = mmd_files[0].read_text()
        
        # Verify multi-chart structure with subgraphs
        assert "subgraph" in content
        assert content.count("subgraph") == 6  # 6 charts
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in content or chart_name.replace(" ", "_") in content, \
                f"Missing chart: {chart_name}"

    def test_cli_export_multi_flow_graphviz(self, multi_flow_file, tmp_path):
        """Test CLI export MultiFlowChart to Graphviz format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(multi_flow_file),
             "-o", str(output_dir), "-f", "graphviz"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        dot_files = list(output_dir.glob("*.dot"))
        assert len(dot_files) == 1
        content = dot_files[0].read_text()
        
        # Verify multi-chart structure with clusters
        assert 'subgraph "cluster_' in content or 'subgraph cluster_' in content
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in content, f"Missing chart: {chart_name}"

    def test_cli_export_multi_flow_json(self, multi_flow_file, tmp_path):
        """Test CLI export MultiFlowChart to JSON format."""
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(multi_flow_file),
             "-o", str(output_dir), "-f", "json"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) == 1
        content = json_files[0].read_text()
        
        # Verify multi-chart JSON structure
        assert '"charts":' in content
        assert '"mainChartId":' in content
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in content, f"Missing chart: {chart_name}"


# =============================================================================
# SVG Backend Tests (requires graphviz executable)
# =============================================================================

# Check if graphviz executable is available
def graphviz_available():
    """Check if graphviz is installed."""
    try:
        import graphviz
        # Try to render something simple
        g = graphviz.Digraph()
        g.node("a")
        g.pipe(format='svg')
        return True
    except Exception:
        return False


# =============================================================================
# Markdown Link Handling Tests
# =============================================================================

class TestMarkdownLinkHandling:
    """Test that markdown links are properly converted in all backends."""

    def test_mermaid_converts_links_to_text(self, single_flow_chart):
        """Test that Mermaid converts [text](url) to just 'text'."""
        output = MermaidExporter.to_mermaid(single_flow_chart)
        
        # Links should be converted to plain text (no clickable links in Mermaid nodes)
        # The original description has: [troubleshooting guide](https://wiki.example.com/troubleshoot)
        assert "troubleshooting guide" in output
        # The URL should NOT appear in raw form
        assert "https://wiki.example.com/troubleshoot" not in output
        # The markdown link syntax should be removed
        assert "[troubleshooting guide](" not in output
        
        # Also check other links
        assert "docs" in output  # from [docs](...)
        assert "decision matrix" in output  # from [decision matrix](...)
        assert "SOP" in output  # from [SOP](...)

    def test_graphviz_converts_links_to_underlined_text(self, single_flow_chart):
        """Test that Graphviz converts [text](url) to <U>text</U>."""
        output = GraphvizExporter.to_dot(single_flow_chart)
        
        # Links should become underlined text (Graphviz has limited HTML support)
        # Check for the troubleshooting guide link
        assert "<U>troubleshooting guide</U>" in output
        
        # Check for other links
        assert "<U>docs</U>" in output
        assert "<U>decision matrix</U>" in output
        assert "<U>SOP</U>" in output
        
        # URLs should NOT appear (they would make labels too long)
        assert "https://wiki.example.com" not in output

    @pytest.mark.skipif(not graphviz_available(), reason="Graphviz executable not installed")
    def test_svg_contains_link_text(self, single_flow_chart):
        """Test that SVG output contains the link text."""
        svg = SvgExporter.to_svg(single_flow_chart)
        
        # The link text should appear
        assert "troubleshooting guide" in svg
        assert "docs" in svg

    def test_mermaid_handles_markdown_formatting(self, single_flow_chart):
        """Test that Mermaid handles bold/italic/code markdown."""
        output = MermaidExporter.to_mermaid(single_flow_chart)
        
        # Bold and italic should be stripped (Mermaid doesn't support in labels)
        # Process B has: "Second processing step with **bold** and *italic* text"
        assert "bold" in output
        assert "italic" in output
        # The markdown markers should be stripped
        assert "**bold**" not in output
        assert "*italic*" not in output
        
        # Code backticks should be converted to quotes
        # Left Path has: "Handle left branch - see `config.yaml` for settings"
        assert "config.yaml" in output

    def test_graphviz_handles_markdown_formatting(self, single_flow_chart):
        """Test that Graphviz converts bold/italic/code to HTML tags."""
        output = GraphvizExporter.to_dot(single_flow_chart)
        
        # Bold should become <B>
        assert "<B>bold</B>" in output
        # Italic should become <I>
        assert "<I>italic</I>" in output
        # Code backticks should become <I> (italic for code)
        assert "<I>config.yaml</I>" in output


@pytest.mark.skipif(not graphviz_available(), reason="Graphviz executable not installed")
class TestSvgSingleFlow:
    """Test SvgExporter with the COMPLEX_SINGLE_FLOW."""

    def test_produces_valid_svg(self, single_flow_chart):
        """Test that output is valid SVG."""
        svg = SvgExporter.to_svg(single_flow_chart)
        
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_contains_all_node_labels(self, single_flow_chart):
        """Test that all expected node labels are in the SVG."""
        svg = SvgExporter.to_svg(single_flow_chart)
        
        expected_labels = set()
        for source, target, _ in SINGLE_FLOW_EXPECTED_EDGES:
            expected_labels.add(source)
            expected_labels.add(target)
        
        for label in expected_labels:
            assert label in svg, f"Missing node label in SVG: {label}"


@pytest.mark.skipif(not graphviz_available(), reason="Graphviz executable not installed")
class TestSvgMultiFlow:
    """Test SvgExporter with the COMPLEX_MULTI_FLOW."""

    def test_produces_valid_svg(self, multi_flow_chart):
        """Test that output is valid SVG."""
        svg = SvgExporter.to_svg(multi_flow_chart)
        
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_contains_all_chart_names(self, multi_flow_chart):
        """Test that all chart names are in the SVG."""
        svg = SvgExporter.to_svg(multi_flow_chart)
        
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in svg, f"Missing chart name in SVG: {chart_name}"

    def test_contains_decision_labels(self, multi_flow_chart):
        """Test that decision labels are in the SVG."""
        svg = SvgExporter.to_svg(multi_flow_chart)
        
        expected_decisions = [
            "Issue fully resolved?",
            "Is it a complex issue?",
            "Needs deeper analysis?",
            "Is it urgent?",
        ]
        for decision in expected_decisions:
            assert decision in svg, f"Missing decision in SVG: {decision}"


@pytest.mark.skipif(not graphviz_available(), reason="Graphviz executable not installed")
class TestCLISvgExport:
    """Test CLI SVG export for both single and multi flows."""

    def test_cli_export_single_flow_svg(self, tmp_path):
        """Test CLI export single flow to SVG format."""
        flow_file = tmp_path / "single_flow.py"
        flow_file.write_text(COMPLEX_SINGLE_FLOW)
        
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file),
             "-o", str(output_dir), "-f", "svg"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        svg_files = list(output_dir.glob("*.svg"))
        assert len(svg_files) == 1
        content = svg_files[0].read_text()
        assert "<svg" in content
        assert "Initial check?" in content

    def test_cli_export_multi_flow_svg(self, tmp_path):
        """Test CLI export MultiFlowChart to SVG format."""
        flow_file = tmp_path / "multi_flow.py"
        flow_file.write_text(COMPLEX_MULTI_FLOW)
        
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file),
             "-o", str(output_dir), "-f", "svg"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        svg_files = list(output_dir.glob("*.svg"))
        assert len(svg_files) == 1
        content = svg_files[0].read_text()
        
        # Verify multi-chart content
        assert "<svg" in content
        for chart_name in MULTI_FLOW_EXPECTED_CHARTS:
            assert chart_name in content, f"Missing chart in SVG: {chart_name}"
