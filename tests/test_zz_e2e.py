"""
End-to-end tests for the flowly CLI and FlowPlay JavaScript viewer.

These tests:
1. Generate Python flow files
2. Run the CLI to produce HTML
3. Load the HTML in a headless browser (Playwright)
4. Verify the JavaScript initializes correctly and state is set up properly

The tests are organized into two comprehensive test classes:
- TestSingleFlowChartComprehensive: Tests a complex single flowchart with branches and loops
- TestMultiFlowChartComprehensive: Tests a complex multi-chart flow with linked subflows
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Skip all tests if playwright is not installed or browsers aren't available
pytest.importorskip("playwright")

from playwright.sync_api import expect, sync_playwright


@pytest.fixture(scope="module")
def browser_context():
    """Create a browser context for all tests in this module."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        yield context
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    """Create a new page for each test."""
    page = browser_context.new_page()
    yield page
    page.close()


class TestSingleFlowChartComprehensive:
    """
    Comprehensive E2E test for a complex single flowchart.

    This tests a flowchart with:
    - Multiple decision nodes (branches)
    - Multiple process nodes
    - A while loop (creates back edges)
    - Multiple end conditions

    Verifies ALL edges exist and are properly rendered.
    """

    COMPLEX_SINGLE_FLOW = """
from flowly.frontend.dsl import Flow, Node, Decision

# Define nodes
start_check = Decision("Initial check?")
process_a = Node("Process A", description="First processing step")
process_b = Node("Process B", description="Second processing step")
branch = Decision("Branch decision?", yes_label="Left", no_label="Right")
left_process = Node("Left Path")
right_process = Node("Right Path")
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

    # Expected structure:
    # StartNode -> start_check (Decision)
    # start_check -> process_a (Yes) OR process_b (No)
    # process_a -> continue_check
    # process_b -> continue_check
    # continue_check -> branch (Yes) OR EndNode (No/Done)
    # branch -> left_process (Left) OR right_process (Right)
    # left_process -> continue_check (loop back)
    # right_process -> continue_check (loop back)

    EXPECTED_EDGES = [
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

    def test_complex_single_flow_all_edges(self, tmp_path, page):
        """
        Test that a complex single flowchart has ALL expected edges
        properly created and rendered in the SVG.
        """
        # Create flow file
        flow_file = tmp_path / "complex_single.py"
        flow_file.write_text(self.COMPLEX_SINGLE_FLOW)

        # Run CLI
        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Load in browser
        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.flowData !== null")
        page.wait_for_timeout(500)

        # Build lookup of nodes by label
        nodes = page.evaluate("Object.values(FlowState.nodes)")
        node_by_label = {n["label"]: n for n in nodes}

        # Verify all expected nodes exist
        expected_labels = set(e[0] for e in self.EXPECTED_EDGES) | set(
            e[1] for e in self.EXPECTED_EDGES
        )
        for label in expected_labels:
            assert label in node_by_label, f"Missing node: {label}"

        # Build edge lookup
        edges = page.evaluate("Object.values(FlowState.edges)")

        # Verify ALL expected edges exist
        for source_label, target_label, edge_label in self.EXPECTED_EDGES:
            source_id = node_by_label[source_label]["id"]
            target_id = node_by_label[target_label]["id"]

            # Find edge from source to target
            matching_edges = [
                e
                for e in edges
                if e["source"] == source_id and e["target"] == target_id
            ]

            assert (
                len(matching_edges) > 0
            ), f"Missing edge: {source_label} -> {target_label}"

            # Verify edge label if expected
            if edge_label:
                found_label = matching_edges[0].get("label")
                assert found_label == edge_label, (
                    f"Wrong label for edge {source_label} -> {target_label}: "
                    f"expected '{edge_label}', got '{found_label}'"
                )

            # Verify edge is rendered in SVG (not hidden)
            edge_id = matching_edges[0]["id"]
            svg_exists = page.evaluate(
                f"document.getElementById('edge-{edge_id}') !== null"
            )
            assert (
                svg_exists
            ), f"Edge not rendered in SVG: {edge_id} ({source_label} -> {target_label})"

    def test_complex_single_flow_navigation(self, tmp_path, page):
        """Test navigation through all paths in the complex single flow."""
        flow_file = tmp_path / "complex_single.py"
        flow_file.write_text(self.COMPLEX_SINGLE_FLOW)

        output_dir = tmp_path / "output"
        subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
        )

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.currentNode !== null")

        # Verify start at StartNode
        assert page.evaluate("FlowState.currentNode.type") == "StartNode"

        # Navigate: Start -> Initial check
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Initial check?"
        assert page.evaluate("FlowState.currentNode.type") == "DecisionNode"

        # Navigate: Initial check -> Process A (Yes)
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Process A"

        # Navigate: Process A -> Continue loop?
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Continue loop?"

        # Navigate: Continue loop -> Branch decision (Yes)
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Branch decision?"

        # Navigate: Branch decision -> Left Path (Left)
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Left Path"

        # Navigate: Left Path -> Continue loop (loop back)
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Continue loop?"

        # Navigate: Continue loop -> Flow Complete (Done)
        page.keyboard.press("2")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Flow Complete"
        assert page.evaluate("FlowState.currentNode.type") == "EndNode"

        # Verify history
        history_length = page.evaluate("FlowState.history.length")
        assert history_length >= 8  # All the steps we took (may vary slightly based on DSL)

    def test_complex_single_flow_ui_elements(self, tmp_path, page):
        """Test that UI elements work correctly for complex single flow."""
        flow_file = tmp_path / "complex_single.py"
        flow_file.write_text(self.COMPLEX_SINGLE_FLOW)

        output_dir = tmp_path / "output"
        subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
        )

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.currentNode !== null")

        # Test overlay shows correct content
        page.keyboard.press("1")  # Go to decision
        page.wait_for_timeout(600)

        title = page.locator("#overlay-title").text_content()
        assert title == "Initial check?"

        # Decision should have 2 buttons
        buttons = page.locator("#overlay-actions .edge-btn")
        assert buttons.count() == 2

        # Test restart
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        page.keyboard.press("r")
        page.wait_for_timeout(600)

        assert page.evaluate("FlowState.currentNode.type") == "StartNode"
        assert page.evaluate("FlowState.history.length") == 1

        # Test back navigation
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        page.keyboard.press("b")
        page.wait_for_timeout(600)

        assert page.evaluate("FlowState.currentNode.type") == "StartNode"


class TestMultiFlowChartComprehensive:
    """
    Comprehensive E2E test for a complex multi-chart flow with linked subflows.

    This tests a MultiFlowChart with:
    - 5 subflows with complex inter-linking
    - Circular references between subflows
    - Subflows calling back to other subflows (not just main)
    - Forward references (using subflows before they're defined)
    - All edges properly connected and rendered

    The flow topology is:
        Main -> Triage -> Analyze -> [Escalate | Quick Fix]
                           ^              |
                           |              v
                           +---- Resolve <+

    Where:
    - Main calls Triage
    - Triage calls Analyze  
    - Analyze can call Escalate or Quick Fix
    - Escalate calls Resolve
    - Resolve can call back to Analyze (circular!)
    - Quick Fix ends directly
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

    def test_complex_multi_flow_all_edges_rendered(self, tmp_path, page):
        """
        Test that ALL visible edges are rendered in SVG
        and every non-EndNode has at least one outgoing edge.
        """
        flow_file = tmp_path / "complex_multi.py"
        flow_file.write_text(self.COMPLEX_MULTI_FLOW)

        output_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.flowData !== null")
        page.wait_for_timeout(500)

        # Verify it's a MultiFlowChart with 6 charts (main + 5 subflows)
        assert page.evaluate("FlowState.isMultiChart") is True
        chart_count = page.evaluate("Object.keys(FlowState.allCharts).length")
        assert chart_count == 6, f"Expected 6 charts (main + 5 subflows), got {chart_count}"

        # Verify chart names
        chart_names = page.evaluate(
            "Object.values(FlowState.allCharts).map(c => c.name)"
        )
        expected_names = ["Support Workflow", "Triage", "Analyze", "Escalate", "Resolve", "Quick Fix"]
        for name in expected_names:
            assert name in chart_names, f"Missing chart: {name}"

        # Verify all visible edges are rendered
        edges = page.evaluate("Object.values(FlowState.edges)")
        for edge in edges:
            if edge.get("metadata", {}).get("hidden"):
                continue  # Skip hidden edges
            edge_id = edge["id"]
            svg_exists = page.evaluate(
                f"document.getElementById('edge-{edge_id}') !== null"
            )
            assert svg_exists, f"Edge '{edge_id}' not rendered in SVG"

        # Verify every non-EndNode has outgoing edges
        non_end_nodes = page.evaluate(
            "Object.values(FlowState.nodes).filter(n => n.type !== 'EndNode')"
        )
        for node in non_end_nodes:
            outgoing = page.evaluate(
                f"FlowState.graph.outgoingEdges['{node['id']}'] || []"
            )
            assert (
                len(outgoing) > 0
            ), f"Node '{node['label']}' (type={node['type']}) has no outgoing edges - dead end!"

        # Verify all nodes are rendered with positions
        nodes = page.evaluate("Object.values(FlowState.nodes)")
        for node in nodes:
            svg_exists = page.evaluate(
                f"document.getElementById('node-{node['id']}') !== null"
            )
            assert svg_exists, f"Node '{node['label']}' not rendered in SVG"
            assert node.get("x") is not None, f"Node '{node['label']}' missing x position"
            assert node.get("y") is not None, f"Node '{node['label']}' missing y position"

    def test_complex_multi_flow_cross_chart_navigation(self, tmp_path, page):
        """
        Test that SubFlowNodes have cross-chart navigation edges
        and can navigate to subflow start nodes.
        """
        flow_file = tmp_path / "complex_multi.py"
        flow_file.write_text(self.COMPLEX_MULTI_FLOW)

        output_dir = tmp_path / "output"
        subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
        )

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.currentNode !== null")

        # Find SubFlowNodes - should have 5 in this complex flow:
        # Main: Analyze, Triage
        # Triage: Analyze
        # Analyze: Escalate, Quick Fix
        # Escalate: Resolve
        # Resolve: Analyze (circular!)
        subflow_nodes = page.evaluate(
            """
            Object.values(FlowState.nodes).filter(n => n.type === 'SubFlowNode')
        """
        )
        assert len(subflow_nodes) >= 5, f"Expected at least 5 SubFlowNodes, got {len(subflow_nodes)}"

        # Verify each SubFlowNode has:
        # 1. A targetChartId
        # 2. A hidden cross-chart edge to the target chart's start node
        # 3. Can navigate to the target
        for subflow in subflow_nodes:
            subflow_id = subflow["id"]
            subflow_label = subflow["label"]
            target_chart_id = subflow.get("targetChartId")

            assert (
                target_chart_id is not None
            ), f"SubFlowNode '{subflow_label}' missing targetChartId"

            # Verify target chart exists
            target_chart = page.evaluate(f"FlowState.allCharts['{target_chart_id}']")
            assert (
                target_chart is not None
            ), f"Target chart '{target_chart_id}' not found for '{subflow_label}'"

            # Find hidden cross-chart edge
            cross_edge = page.evaluate(
                f"""
                Object.values(FlowState.edges).find(e =>
                    e.source === '{subflow_id}' &&
                    e.metadata?.crossChart === true
                )
            """
            )
            assert (
                cross_edge is not None
            ), f"SubFlowNode '{subflow_label}' missing cross-chart edge"
            assert (
                cross_edge["metadata"]["hidden"] is True
            ), f"Cross-chart edge should be hidden"
            assert (
                f"Go to: {subflow_label}" in cross_edge["label"]
            ), f"Cross-chart edge should have 'Go to:' label"

            # Verify target is the subflow's start node
            target_start = page.evaluate(
                f"""
                FlowState.allCharts['{target_chart_id}'].nodes.find(n => n.type === 'StartNode')
            """
            )
            assert (
                cross_edge["target"] == target_start["id"]
            ), f"Cross-chart edge should target subflow's start node"

    def test_complex_multi_flow_full_navigation(self, tmp_path, page):
        """
        Test full navigation through the multi-chart flow including
        jumping to subflows via cross-chart edges.
        """
        flow_file = tmp_path / "complex_multi.py"
        flow_file.write_text(self.COMPLEX_MULTI_FLOW)

        output_dir = tmp_path / "output"
        subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
        )

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.currentNode !== null")

        # Start at main flow start
        assert page.evaluate("FlowState.currentNode.type") == "StartNode"
        assert page.evaluate("FlowState.currentNode.label") == "Support Workflow"

        # Navigate: Start -> Receive support request (first step)
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Receive support request"

        # Navigate to "Is it urgent?" decision
        page.keyboard.press("1")
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Is it urgent?"
        assert page.evaluate("FlowState.currentNode.type") == "DecisionNode"

        # Navigate: Is urgent? -> Triage (No branch for non-urgent)
        # Find which button is the "No" branch
        page.keyboard.press("2")  # Try No
        page.wait_for_timeout(600)
        
        current_label = page.evaluate("FlowState.currentNode.label")
        assert current_label == "Triage", f"Expected Triage SubFlowNode, got {current_label}"
        assert page.evaluate("FlowState.currentNode.type") == "SubFlowNode"

        # Navigate: SubFlowNode -> Triage subflow start (via cross-chart edge)
        # The "Go to: Triage" edge should be available
        page.keyboard.press("1")
        page.wait_for_timeout(600)

        # Should now be at Triage start node (in the subflow)
        current = page.evaluate("FlowState.currentNode")
        assert current["type"] == "StartNode"
        assert current["label"] == "Triage"

        # Continue through triage subflow
        page.keyboard.press("1")  # -> Review incoming ticket
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Review incoming ticket"

        page.keyboard.press("1")  # -> Check for duplicates
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Check for duplicates"

        page.keyboard.press("1")  # -> Needs deeper analysis? (Decision)
        page.wait_for_timeout(600)
        assert page.evaluate("FlowState.currentNode.label") == "Needs deeper analysis?"
        assert page.evaluate("FlowState.currentNode.type") == "DecisionNode"

        # Verify history tracks cross-chart navigation
        history_length = page.evaluate("FlowState.history.length")
        assert history_length >= 6

    def test_complex_multi_flow_all_nodes_have_edges(self, tmp_path, page):
        """
        Test that EVERY non-EndNode in all charts has at least one outgoing edge.
        This ensures no nodes are accidentally "dead ends".
        """
        flow_file = tmp_path / "complex_multi.py"
        flow_file.write_text(self.COMPLEX_MULTI_FLOW)

        output_dir = tmp_path / "output"
        subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
        )

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.flowData !== null")

        # Get all non-EndNodes
        non_end_nodes = page.evaluate(
            """
            Object.values(FlowState.nodes).filter(n => n.type !== 'EndNode')
        """
        )

        # Every non-end node should have outgoing edges
        for node in non_end_nodes:
            node_id = node["id"]
            node_label = node["label"]
            outgoing = page.evaluate(
                f"FlowState.graph.outgoingEdges['{node_id}'] || []"
            )

            assert (
                len(outgoing) > 0
            ), f"Node '{node_label}' (type={node['type']}) has no outgoing edges - dead end!"

    def test_complex_multi_flow_svg_rendering(self, tmp_path, page):
        """
        Test that ALL nodes and visible edges are rendered in the SVG.
        """
        flow_file = tmp_path / "complex_multi.py"
        flow_file.write_text(self.COMPLEX_MULTI_FLOW)

        output_dir = tmp_path / "output"
        subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(flow_file), "-o", str(output_dir)],
            capture_output=True,
        )

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.flowData !== null")
        page.wait_for_timeout(500)

        # Verify all nodes have SVG elements
        nodes = page.evaluate("Object.values(FlowState.nodes)")
        for node in nodes:
            node_id = node["id"]
            svg_exists = page.evaluate(
                f"document.getElementById('node-{node_id}') !== null"
            )
            assert svg_exists, f"Node '{node['label']}' not rendered in SVG"

            # Verify node has x,y position (was laid out)
            assert (
                node.get("x") is not None
            ), f"Node '{node['label']}' missing x position"
            assert (
                node.get("y") is not None
            ), f"Node '{node['label']}' missing y position"

        # Verify all visible edges have SVG elements
        edges = page.evaluate("Object.values(FlowState.edges)")
        for edge in edges:
            if edge.get("metadata", {}).get("hidden"):
                continue  # Hidden edges shouldn't be rendered

            edge_id = edge["id"]
            svg_exists = page.evaluate(
                f"document.getElementById('edge-{edge_id}') !== null"
            )
            assert svg_exists, f"Edge '{edge_id}' not rendered in SVG"


class TestPerfOncallSample:
    """Test using the actual perf_oncall.py sample file."""

    def test_perf_oncall_comprehensive(self, page):
        """
        Comprehensive test of perf_oncall.py:
        - Generates valid MultiFlowChart
        - Has expected charts (main + Triaging subflow)
        - All nodes have SVG elements
        - SubFlowNode navigation works
        """
        import subprocess
        import sys
        from pathlib import Path

        perf_file = Path("/Users/mqh/dev/flowly/perf_oncall.py")
        if not perf_file.exists():
            pytest.skip("perf_oncall.py not found")

        output_dir = Path("/tmp/flowly_test_perf")
        output_dir.mkdir(exist_ok=True)

        result = subprocess.run(
            [sys.executable, "-m", "flowly.cli", str(perf_file), "-o", str(output_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        html_file = list(output_dir.glob("*.html"))[0]
        page.goto(f"file://{html_file}")
        page.wait_for_function("FlowState.flowData !== null")
        page.wait_for_timeout(500)

        # Verify MultiFlowChart structure
        assert page.evaluate("FlowState.isMultiChart") is True
        chart_count = page.evaluate("Object.keys(FlowState.allCharts).length")
        assert chart_count == 2, f"Expected 2 charts, got {chart_count}"

        chart_names = page.evaluate(
            "Object.values(FlowState.allCharts).map(c => c.name)"
        )
        assert "Training Performance Runbook" in chart_names
        assert "Triaging" in chart_names

        # Verify all nodes are rendered
        nodes = page.evaluate("Object.values(FlowState.nodes)")
        for node in nodes:
            svg_exists = page.evaluate(
                f"document.getElementById('node-{node['id']}') !== null"
            )
            assert svg_exists, f"Node '{node['label']}' not rendered"
            assert node.get("x") is not None, f"Node '{node['label']}' missing position"

        # Verify SubFlowNode exists and has proper linkage
        subflow_node = page.evaluate(
            """
            Object.values(FlowState.nodes).find(n => n.type === 'SubFlowNode')
        """
        )
        assert subflow_node is not None
        assert subflow_node["label"] == "Triaging"
        assert subflow_node.get("targetChartId") is not None

        # Verify cross-chart edge exists
        cross_edge = page.evaluate(
            f"""
            Object.values(FlowState.edges).find(e =>
                e.source === '{subflow_node["id"]}' &&
                e.metadata?.crossChart === true
            )
        """
        )
        assert cross_edge is not None
        assert "Go to: Triaging" in cross_edge["label"]

        # Verify all non-EndNodes have outgoing edges
        non_end_nodes = page.evaluate(
            """
            Object.values(FlowState.nodes).filter(n => n.type !== 'EndNode')
        """
        )
        for node in non_end_nodes:
            outgoing = page.evaluate(
                f"FlowState.graph.outgoingEdges['{node['id']}'] || []"
            )
            assert (
                len(outgoing) > 0
            ), f"Node '{node['label']}' has no outgoing edges - dead end!"
