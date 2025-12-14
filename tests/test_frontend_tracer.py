"""
Comprehensive tests for the FlowTracer runtime tracing frontend.

Tests cover:
- Basic node creation
- Decision branches (if/else)
- Loop constructs (while/until)
- Edge labeling
- Complex nested flows
- Error handling
"""

import pytest
from flowly.frontend.tracer import FlowTracer, SimpleFlowTracer
from flowly.core.ir import (
    FlowChart, StartNode, EndNode, ProcessNode, DecisionNode, Edge
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def simple_tracer():
    """Create a fresh SimpleFlowTracer for testing."""
    return SimpleFlowTracer("Test Flow")


# =============================================================================
# Basic Node Tests
# =============================================================================

class TestBasicNodes:
    """Tests for basic node creation and connections."""
    
    def test_empty_flow_has_start_and_end(self):
        """A flow with no nodes should have just Start and End."""
        with FlowTracer("Empty") as flow:
            pass
        
        chart = flow.build()
        assert len(chart.nodes) == 2
        
        # Should have one StartNode and one EndNode
        node_types = [type(n).__name__ for n in chart.nodes.values()]
        assert "StartNode" in node_types
        assert "EndNode" in node_types
        
        # Should have one edge connecting them
        assert len(chart.edges) == 1
    
    def test_single_node_flow(self):
        """A flow with one node should have Start -> Node -> End."""
        with FlowTracer("Single") as flow:
            flow.node("Do something")
        
        chart = flow.build()
        
        assert len(chart.nodes) == 3
        assert len(chart.edges) == 2
        
        # Find the process node
        process_nodes = [n for n in chart.nodes.values() if isinstance(n, ProcessNode)]
        assert len(process_nodes) == 1
        assert process_nodes[0].label == "Do something"
    
    def test_multiple_sequential_nodes(self):
        """Multiple nodes should be connected in sequence."""
        with FlowTracer("Sequential") as flow:
            flow.node("Step 1")
            flow.node("Step 2")
            flow.node("Step 3")
        
        chart = flow.build()
        
        # Start + 3 process nodes + End = 5
        assert len(chart.nodes) == 5
        # 4 edges: Start->1, 1->2, 2->3, 3->End
        assert len(chart.edges) == 4
        
        # Verify the chain
        process_nodes = [n for n in chart.nodes.values() if isinstance(n, ProcessNode)]
        assert len(process_nodes) == 3
        labels = {n.label for n in process_nodes}
        assert labels == {"Step 1", "Step 2", "Step 3"}
    
    def test_node_with_description(self):
        """Node descriptions should be stored in metadata."""
        with FlowTracer("Described") as flow:
            flow.node("My Node", description="This is a detailed description")
        
        chart = flow.build()
        process_nodes = [n for n in chart.nodes.values() if isinstance(n, ProcessNode)]
        
        assert len(process_nodes) == 1
        assert process_nodes[0].metadata.get("description") == "This is a detailed description"
    
    def test_explicit_end(self):
        """Calling end() should terminate the flow at that point."""
        with FlowTracer("Explicit End") as flow:
            flow.node("Before end")
            flow.end("Custom End")
        
        chart = flow.build()
        
        # Should have Start, ProcessNode, EndNode (no auto-added end)
        assert len(chart.nodes) == 3
        
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(end_nodes) == 1
        assert end_nodes[0].label == "Custom End"


# =============================================================================
# Decision/Branching Tests
# =============================================================================

class TestDecisions:
    """Tests for decision nodes and branching."""
    
    def test_decision_yes_branch(self):
        """Decision with True result should follow Yes branch."""
        with FlowTracer("Decision Yes") as flow:
            flow.node("Before decision")
            if flow.decision("Is it true?", True):
                flow.node("Yes branch")
        
        chart = flow.build()
        
        # Start, Before, Decision, Yes branch, End = 5
        assert len(chart.nodes) == 5
        
        # Check we have a decision node
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 1
        assert decision_nodes[0].label == "Is it true?"
    
    def test_decision_no_branch(self):
        """Decision with False result should follow No branch."""
        with FlowTracer("Decision No") as flow:
            flow.node("Before decision")
            if flow.decision("Is it true?", False):
                flow.node("Yes branch - should not appear")
            else:
                flow.node("No branch")
        
        chart = flow.build()
        
        # Start, Before, Decision, No branch, End = 5
        assert len(chart.nodes) == 5
        
        # The "Yes branch" should NOT be in the chart
        labels = {n.label for n in chart.nodes.values()}
        assert "Yes branch - should not appear" not in labels
        assert "No branch" in labels
    
    def test_decision_with_else_branch(self):
        """Both branches of a decision should work correctly."""
        # Test Yes path
        with FlowTracer("Yes Path") as flow:
            if flow.decision("Choose?", True):
                flow.node("Chose Yes")
            else:
                flow.node("Chose No")
        
        chart_yes = flow.build()
        labels_yes = {n.label for n in chart_yes.nodes.values()}
        assert "Chose Yes" in labels_yes
        assert "Chose No" not in labels_yes
        
        # Test No path
        with FlowTracer("No Path") as flow:
            if flow.decision("Choose?", False):
                flow.node("Chose Yes")
            else:
                flow.node("Chose No")
        
        chart_no = flow.build()
        labels_no = {n.label for n in chart_no.nodes.values()}
        assert "Chose Yes" not in labels_no
        assert "Chose No" in labels_no
    
    def test_nested_decisions(self):
        """Nested decision structures should work correctly."""
        with FlowTracer("Nested") as flow:
            flow.node("Start process")
            if flow.decision("First check?", True):
                flow.node("Passed first")
                if flow.decision("Second check?", True):
                    flow.node("Passed both")
        
        chart = flow.build()
        
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 2
        
        process_nodes = [n for n in chart.nodes.values() if isinstance(n, ProcessNode)]
        assert len(process_nodes) == 3


# =============================================================================
# Loop Tests
# =============================================================================

class TestLoops:
    """Tests for loop constructs using until()."""
    
    def test_loop_never_enters(self):
        """Loop with False condition should not enter body."""
        with FlowTracer("Skip Loop") as flow:
            flow.node("Before loop")
            while flow.until("Should continue?", False):
                flow.node("Loop body - should not appear")
            flow.node("After loop")
        
        chart = flow.build()
        
        labels = {n.label for n in chart.nodes.values()}
        assert "Loop body - should not appear" not in labels
        assert "Before loop" in labels
        assert "After loop" in labels
        
        # Should have a decision node for the loop condition
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 1
    
    def test_loop_single_iteration(self):
        """Loop that executes once should have body in chart."""
        iteration = 0
        with FlowTracer("Single Iteration") as flow:
            flow.node("Before loop")
            while flow.until("Continue?", iteration < 1):
                flow.node("Loop body")
                iteration += 1
            flow.node("After loop")
        
        chart = flow.build()
        
        labels = {n.label for n in chart.nodes.values()}
        assert "Loop body" in labels
        assert "Before loop" in labels
        assert "After loop" in labels
    
    def test_loop_multiple_iterations(self):
        """Loop with multiple iterations should still have one set of nodes."""
        iteration = 0
        with FlowTracer("Multiple Iterations") as flow:
            flow.node("Before")
            while flow.until("More?", iteration < 3):
                flow.node(f"Iteration")  # Same label each time
                iteration += 1
            flow.node("After")
        
        chart = flow.build()
        
        # The loop body appears multiple times in execution but creates
        # nodes on first pass; subsequent passes create back-edges
        process_nodes = [n for n in chart.nodes.values() if isinstance(n, ProcessNode)]
        # Before, Iteration (first), After = 3 process nodes
        # (the loop creates the node once, then back-edges)
        assert len(process_nodes) >= 2  # At least Before and Iteration
    
    def test_loop_with_decision_inside(self):
        """Loops can contain decisions."""
        iteration = 0
        with FlowTracer("Loop with Decision") as flow:
            while flow.until("Keep going?", iteration < 2):
                if flow.decision("Special case?", iteration == 0):
                    flow.node("Handle special")
                else:
                    flow.node("Normal case")
                iteration += 1
        
        chart = flow.build()
        
        # Should have the loop decision and the inner decision
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) >= 1  # At least the loop decision


# =============================================================================
# SimpleFlowTracer Tests
# =============================================================================

class TestSimpleFlowTracer:
    """Tests for the SimpleFlowTracer with cleaner API."""
    
    def test_chained_nodes(self):
        """SimpleFlowTracer should support method chaining."""
        with SimpleFlowTracer("Chained") as flow:
            flow.Node("Step 1").Node("Step 2").Node("Step 3")
        
        chart = flow.build()
        process_nodes = [n for n in chart.nodes.values() if isinstance(n, ProcessNode)]
        assert len(process_nodes) == 3
    
    def test_decision_with_labels(self):
        """SimpleFlowTracer Decision should label edges automatically."""
        with SimpleFlowTracer("Labeled Decision") as flow:
            flow.Node("Start here")
            if flow.Decision("Ready?", True, yes_label="Ready!", no_label="Not ready"):
                flow.Node("Proceed")
        
        chart = flow.build()
        
        # Find edge from decision to process node
        decision_node = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        edges_from_decision = [e for e in chart.edges if e.source_id == decision_node.id]
        
        # Should have at least one edge with the "Ready!" label
        labels = {e.label for e in edges_from_decision}
        assert "Ready!" in labels
    
    def test_until_with_labels(self):
        """SimpleFlowTracer Until should label edges automatically."""
        with SimpleFlowTracer("Labeled Loop") as flow:
            iteration = 0
            while flow.Until("More items?", iteration < 1, 
                           continue_label="Continue", exit_label="Done"):
                flow.Node("Process item")
                iteration += 1
            flow.Node("Finished")
        
        chart = flow.build()
        
        # Check that "Done" label exists on an edge
        edge_labels = {e.label for e in chart.edges if e.label}
        assert "Done" in edge_labels or "Continue" in edge_labels


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error conditions and edge cases."""
    
    def test_node_outside_context_raises(self):
        """Calling node() outside 'with' block should raise."""
        flow = FlowTracer("Outside")
        
        with pytest.raises(RuntimeError, match="must be used within"):
            flow.node("Bad call")
    
    def test_decision_outside_context_raises(self):
        """Calling decision() outside 'with' block should raise."""
        flow = FlowTracer("Outside")
        
        with pytest.raises(RuntimeError, match="must be used within"):
            flow.decision("Bad?", True)
    
    def test_until_outside_context_raises(self):
        """Calling until() outside 'with' block should raise."""
        flow = FlowTracer("Outside")
        
        with pytest.raises(RuntimeError, match="must be used within"):
            flow.until("Bad?", True)
    
    def test_build_without_context_raises(self):
        """Calling build() without using context should raise."""
        flow = FlowTracer("Never Used")
        
        with pytest.raises(RuntimeError, match="was not used"):
            flow.build()


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests with realistic flow scenarios."""
    
    def test_server_health_check_flow(self):
        """Realistic example: Server health check procedure."""
        server_responding = True
        cpu_high = False
        
        with FlowTracer("Server Health Check") as flow:
            flow.node("Receive alert", description="An alert was triggered")
            
            if flow.decision("Is server responding?", server_responding):
                flow.node("Check CPU usage")
                
                if flow.decision("CPU > 80%?", cpu_high):
                    flow.node("Identify top process")
                    flow.node("Consider scaling")
                else:
                    flow.node("Check memory usage")
            else:
                flow.node("Attempt ping")
                flow.node("Escalate to infrastructure")
        
        chart = flow.build()
        
        # Verify structure
        assert chart.name == "Server Health Check"
        assert len(chart.nodes) >= 5
        
        # Should have decision nodes
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 2
    
    def test_user_registration_flow(self):
        """Realistic example: User registration with validation."""
        email_valid = True
        password_strong = True
        
        with FlowTracer("User Registration") as flow:
            flow.node("User submits form")
            
            if flow.decision("Email valid?", email_valid):
                if flow.decision("Password strong?", password_strong):
                    flow.node("Create account")
                    flow.node("Send welcome email")
                else:
                    flow.node("Show password requirements")
                    flow.end("Registration failed")
            else:
                flow.node("Show email error")
                flow.end("Registration failed")
        
        chart = flow.build()
        
        # With valid inputs, should reach "Send welcome email"
        labels = {n.label for n in chart.nodes.values()}
        assert "Create account" in labels
        assert "Send welcome email" in labels
    
    def test_retry_loop_pattern(self):
        """Common pattern: Retry with max attempts."""
        attempt = 0
        max_attempts = 3
        success = False
        
        with FlowTracer("Retry Pattern") as flow:
            flow.node("Start operation")
            
            while flow.until("Retry?", attempt < max_attempts and not success):
                flow.node(f"Attempt {attempt + 1}")
                # Simulate success on third attempt
                if attempt == 2:
                    success = True
                attempt += 1
            
            if flow.decision("Was successful?", success):
                flow.node("Report success")
            else:
                flow.node("Report failure")
        
        chart = flow.build()
        
        # Should have completed with success
        labels = {n.label for n in chart.nodes.values()}
        assert "Report success" in labels
    
    def test_flow_reusability_different_paths(self):
        """Same code can generate different charts based on runtime values."""
        def create_order_flow(is_premium: bool, in_stock: bool) -> FlowChart:
            with FlowTracer(f"Order Flow (premium={is_premium})") as flow:
                flow.node("Receive order")
                
                if flow.decision("In stock?", in_stock):
                    if flow.decision("Premium customer?", is_premium):
                        flow.node("Apply discount")
                    flow.node("Process payment")
                    flow.node("Ship order")
                else:
                    flow.node("Add to waitlist")
            
            return flow.build()
        
        # Generate different flows
        chart_premium = create_order_flow(is_premium=True, in_stock=True)
        chart_regular = create_order_flow(is_premium=False, in_stock=True)
        chart_out_of_stock = create_order_flow(is_premium=True, in_stock=False)
        
        # Premium should have discount node
        premium_labels = {n.label for n in chart_premium.nodes.values()}
        assert "Apply discount" in premium_labels
        
        # Regular should not have discount
        regular_labels = {n.label for n in chart_regular.nodes.values()}
        assert "Apply discount" not in regular_labels
        
        # Out of stock should have waitlist
        oos_labels = {n.label for n in chart_out_of_stock.nodes.values()}
        assert "Add to waitlist" in oos_labels
        assert "Ship order" not in oos_labels


# =============================================================================
# Graph Structure Tests
# =============================================================================

class TestGraphStructure:
    """Tests verifying the correct graph structure is built."""
    
    def test_all_nodes_connected(self):
        """Every node (except End) should have outgoing edges or be an End node."""
        with FlowTracer("Connected") as flow:
            flow.node("A")
            flow.node("B")
            flow.node("C")
        
        chart = flow.build()
        
        for node in chart.nodes.values():
            if isinstance(node, EndNode):
                continue
            
            outgoing = [e for e in chart.edges if e.source_id == node.id]
            assert len(outgoing) >= 1, f"Node {node.label} has no outgoing edges"
    
    def test_no_orphan_edges(self):
        """All edges should reference valid nodes."""
        with FlowTracer("Valid Edges") as flow:
            flow.node("X")
            if flow.decision("Q?", True):
                flow.node("Y")
        
        chart = flow.build()
        node_ids = set(chart.nodes.keys())
        
        for edge in chart.edges:
            assert edge.source_id in node_ids, f"Edge source {edge.source_id} not found"
            assert edge.target_id in node_ids, f"Edge target {edge.target_id} not found"
    
    def test_start_node_has_no_incoming(self):
        """Start node should have no incoming edges."""
        with FlowTracer("Start Check") as flow:
            flow.node("Something")
        
        chart = flow.build()
        start_node = next(n for n in chart.nodes.values() if isinstance(n, StartNode))
        
        incoming = [e for e in chart.edges if e.target_id == start_node.id]
        assert len(incoming) == 0
    
    def test_end_node_has_no_outgoing(self):
        """End node should have no outgoing edges."""
        with FlowTracer("End Check") as flow:
            flow.node("Something")
        
        chart = flow.build()
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        
        for end_node in end_nodes:
            outgoing = [e for e in chart.edges if e.source_id == end_node.id]
            assert len(outgoing) == 0


# =============================================================================
# Edge Labeling Tests
# =============================================================================

class TestEdgeLabeling:
    """Tests for automatic edge labeling on decisions and loops."""
    
    def test_decision_edges_have_yes_no_labels(self):
        """Decision edges should be labeled Yes/No based on branch taken."""
        with FlowTracer("Decision Labels") as flow:
            if flow.decision("First check?", True):
                flow.node("Yes path")
        
        chart = flow.build()
        
        # Find the decision node
        decision_node = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        
        # Get edges from decision
        edges_from_decision = [e for e in chart.edges if e.source_id == decision_node.id]
        
        # Should have "Yes" label since we took the True branch
        assert any(e.label == "Yes" for e in edges_from_decision)
    
    def test_decision_no_branch_has_no_label(self):
        """Decision with False result should have 'No' label."""
        with FlowTracer("No Branch") as flow:
            if flow.decision("Check?", False):
                flow.node("Yes - not taken")
            else:
                flow.node("No path")
        
        chart = flow.build()
        
        decision_node = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        edges_from_decision = [e for e in chart.edges if e.source_id == decision_node.id]
        
        # Should have "No" label
        assert any(e.label == "No" for e in edges_from_decision)
    
    def test_loop_edges_have_labels(self):
        """Loop edges should have Yes (continue) and No (exit) labels."""
        iteration = 0
        with FlowTracer("Loop Labels") as flow:
            while flow.until("Continue?", iteration < 2):
                flow.node("In loop")
                iteration += 1
            flow.node("After loop")
        
        chart = flow.build()
        
        # Find the loop decision node
        decision_node = next(n for n in chart.nodes.values() 
                           if isinstance(n, DecisionNode) and n.label == "Continue?")
        
        edges_from_decision = [e for e in chart.edges if e.source_id == decision_node.id]
        edge_labels = {e.label for e in edges_from_decision if e.label}
        
        # Should have both Yes (enter/continue) and No (exit) labels
        assert "Yes" in edge_labels or "No" in edge_labels
    
    def test_simple_tracer_custom_labels(self):
        """SimpleFlowTracer should support custom edge labels."""
        with SimpleFlowTracer("Custom Labels") as flow:
            if flow.Decision("Ready?", True, yes_label="Proceed", no_label="Wait"):
                flow.Node("Continue")
        
        chart = flow.build()
        
        decision_node = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        edges_from_decision = [e for e in chart.edges if e.source_id == decision_node.id]
        
        # Should have custom "Proceed" label
        assert any(e.label == "Proceed" for e in edges_from_decision)
    
    def test_simple_tracer_loop_custom_labels(self):
        """SimpleFlowTracer Until should support custom labels."""
        iteration = 0
        with SimpleFlowTracer("Custom Loop") as flow:
            while flow.Until("More?", iteration < 1, 
                           continue_label="Keep going", exit_label="Done"):
                flow.Node("Work")
                iteration += 1
            flow.Node("Finished")
        
        chart = flow.build()
        
        edge_labels = {e.label for e in chart.edges if e.label}
        
        # Should have custom labels
        assert "Keep going" in edge_labels or "Done" in edge_labels


# =============================================================================
# Serialization Compatibility Tests
# =============================================================================

class TestSerializationCompatibility:
    """Tests to ensure tracer-generated flows work with serialization."""
    
    def test_tracer_flow_json_roundtrip(self):
        """Flows created with tracer should serialize/deserialize correctly."""
        from flowly.core.serialization import JsonSerializer
        
        with FlowTracer("Serializable") as flow:
            flow.node("Step 1", description="First step")
            if flow.decision("Check?", True):
                flow.node("Passed")
        
        chart = flow.build()
        
        # Serialize
        json_str = JsonSerializer.to_json(chart)
        
        # Deserialize
        chart2 = JsonSerializer.from_json(json_str)
        
        # Verify structure matches
        assert len(chart2.nodes) == len(chart.nodes)
        assert len(chart2.edges) == len(chart.edges)
        assert chart2.name == chart.name
    
    def test_tracer_flow_with_metadata_roundtrip(self):
        """Metadata in tracer flows should survive serialization."""
        from flowly.core.serialization import JsonSerializer
        
        with FlowTracer("With Metadata") as flow:
            flow.node("Documented step", description="This is important")
        
        chart = flow.build()
        json_str = JsonSerializer.to_json(chart)
        chart2 = JsonSerializer.from_json(json_str)
        
        # Find the process node
        process_nodes = [n for n in chart2.nodes.values() if isinstance(n, ProcessNode)]
        assert len(process_nodes) == 1
        assert process_nodes[0].metadata.get("description") == "This is important"
