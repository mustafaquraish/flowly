"""
Comprehensive tests for the static FlowBuilder with context manager syntax.

Tests cover:
- Basic node creation
- Decision branches (both paths)
- Loop constructs
- Nested structures
- Edge cases
- Complex real-world examples
"""

import pytest
from flowly.frontend.static import StaticFlowBuilder
from flowly.core.ir import (
    FlowChart, StartNode, EndNode, ProcessNode, DecisionNode, Edge
)


# =============================================================================
# Basic Node Tests
# =============================================================================

class TestBasicNodes:
    """Tests for basic node creation."""
    
    def test_empty_flow_has_start_and_end(self):
        """A flow with no nodes should have just Start and End."""
        with StaticFlowBuilder("Empty") as flow:
            pass
        
        chart = flow.build()
        assert len(chart.nodes) == 2
        assert len(chart.edges) == 1
        
        node_types = [type(n).__name__ for n in chart.nodes.values()]
        assert "StartNode" in node_types
        assert "EndNode" in node_types
    
    def test_single_node_flow(self):
        """A flow with one node should have Start -> Node -> End."""
        with StaticFlowBuilder("Single") as flow:
            flow.node("Do something")
        
        chart = flow.build()
        assert len(chart.nodes) == 3
        assert len(chart.edges) == 2
    
    def test_sequential_nodes(self):
        """Multiple nodes should be connected in sequence."""
        with StaticFlowBuilder("Sequential") as flow:
            flow.node("Step 1")
            flow.node("Step 2")
            flow.node("Step 3")
        
        chart = flow.build()
        assert len(chart.nodes) == 5  # Start + 3 + End
        assert len(chart.edges) == 4
    
    def test_custom_start_label(self):
        """Start node can have custom label."""
        with StaticFlowBuilder("Custom Start") as flow:
            flow.start("Begin Here", description="Starting point")
            flow.node("Next step")
        
        chart = flow.build()
        start = next(n for n in chart.nodes.values() if isinstance(n, StartNode))
        assert start.label == "Begin Here"
        assert start.metadata.get("description") == "Starting point"
    
    def test_node_with_description(self):
        """Nodes can have descriptions in metadata."""
        with StaticFlowBuilder("Described") as flow:
            flow.node("My Node", description="Detailed description")
        
        chart = flow.build()
        process = next(n for n in chart.nodes.values() if isinstance(n, ProcessNode))
        assert process.metadata.get("description") == "Detailed description"
    
    def test_explicit_end(self):
        """Explicit end node terminates the flow."""
        with StaticFlowBuilder("Explicit End") as flow:
            flow.node("Before")
            flow.end("Custom End", description="Done!")
        
        chart = flow.build()
        ends = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(ends) == 1
        assert ends[0].label == "Custom End"


# =============================================================================
# Decision/Branch Tests
# =============================================================================

class TestDecisions:
    """Tests for decision nodes with both branches."""
    
    def test_decision_with_both_branches(self):
        """Decision should have both yes and no branches."""
        with StaticFlowBuilder("Decision") as flow:
            flow.node("Before")
            with flow.decision("Choose?") as branch:
                with branch.yes():
                    flow.node("Yes path")
                with branch.no():
                    flow.node("No path")
            flow.node("After")
        
        chart = flow.build()
        
        # Should have: Start, Before, Decision, Yes path, No path, After, End
        assert len(chart.nodes) == 7
        
        # Decision should have 2 outgoing edges
        decision = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        outgoing = [e for e in chart.edges if e.source_id == decision.id]
        assert len(outgoing) == 2
        
        labels = {e.label for e in outgoing}
        assert "Yes" in labels
        assert "No" in labels
    
    def test_decision_branches_merge(self):
        """Both branches should merge at the next node after decision."""
        with StaticFlowBuilder("Merge") as flow:
            with flow.decision("Pick?") as branch:
                with branch.yes():
                    flow.node("A")
                with branch.no():
                    flow.node("B")
            flow.node("Merged")
        
        chart = flow.build()
        
        # Find the merge node
        merged = next(n for n in chart.nodes.values() 
                     if isinstance(n, ProcessNode) and n.label == "Merged")
        
        # Should have 2 incoming edges
        incoming = [e for e in chart.edges if e.target_id == merged.id]
        assert len(incoming) == 2
    
    def test_decision_custom_labels(self):
        """Decision branches can have custom labels."""
        with StaticFlowBuilder("Custom Labels") as flow:
            with flow.decision("Ready?") as branch:
                with branch.yes("Proceed"):
                    flow.node("Go ahead")
                with branch.no("Wait"):
                    flow.node("Hold on")
        
        chart = flow.build()
        decision = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        outgoing = [e for e in chart.edges if e.source_id == decision.id]
        labels = {e.label for e in outgoing}
        assert "Proceed" in labels
        assert "Wait" in labels
    
    def test_decision_with_end_in_branch(self):
        """A branch can end early with explicit end()."""
        with StaticFlowBuilder("Early End") as flow:
            flow.node("Start process")
            with flow.decision("Valid?") as branch:
                with branch.yes():
                    flow.node("Continue")
                with branch.no():
                    flow.node("Error")
                    flow.end("Failed")
            flow.node("Success path only")
        
        chart = flow.build()
        
        # Should have 2 end nodes
        ends = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(ends) == 2
    
    def test_nested_decisions(self):
        """Decisions can be nested."""
        with StaticFlowBuilder("Nested") as flow:
            with flow.decision("First?") as d1:
                with d1.yes():
                    flow.node("First yes")
                    with flow.decision("Second?") as d2:
                        with d2.yes():
                            flow.node("Both yes")
                        with d2.no():
                            flow.node("First yes, second no")
                with d1.no():
                    flow.node("First no")
            flow.node("End")
        
        chart = flow.build()
        
        # Should have 2 decision nodes
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 2
        
        # Each decision should have 2 outgoing edges
        for d in decisions:
            outgoing = [e for e in chart.edges if e.source_id == d.id]
            assert len(outgoing) == 2


# =============================================================================
# Loop Tests
# =============================================================================

class TestLoops:
    """Tests for loop constructs."""
    
    def test_simple_loop(self):
        """Basic loop with body and exit."""
        with StaticFlowBuilder("Simple Loop") as flow:
            flow.node("Before loop")
            with flow.loop("Continue?"):
                flow.node("Loop body")
            flow.node("After loop")
        
        chart = flow.build()
        
        # Find the loop decision
        decision = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        
        # Should have 2 outgoing edges (continue + exit)
        outgoing = [e for e in chart.edges if e.source_id == decision.id]
        assert len(outgoing) == 2
        
        # Should have back-edge from body to decision
        body = next(n for n in chart.nodes.values() 
                   if isinstance(n, ProcessNode) and n.label == "Loop body")
        back_edges = [e for e in chart.edges 
                     if e.source_id == body.id and e.target_id == decision.id]
        assert len(back_edges) == 1
    
    def test_loop_custom_labels(self):
        """Loop can have custom continue/exit labels."""
        with StaticFlowBuilder("Custom Loop") as flow:
            with flow.loop("More?", continue_label="Again", exit_label="Done"):
                flow.node("Work")
            flow.node("Finished")
        
        chart = flow.build()
        decision = next(n for n in chart.nodes.values() if isinstance(n, DecisionNode))
        outgoing = [e for e in chart.edges if e.source_id == decision.id]
        labels = {e.label for e in outgoing}
        assert "Again" in labels
        assert "Done" in labels
    
    def test_loop_with_decision_inside(self):
        """Loop can contain decision nodes."""
        with StaticFlowBuilder("Loop with Decision") as flow:
            with flow.loop("Repeat?"):
                flow.node("Start iteration")
                with flow.decision("Special case?") as branch:
                    with branch.yes():
                        flow.node("Handle special")
                    with branch.no():
                        flow.node("Normal processing")
                flow.node("End iteration")
            flow.node("Done")
        
        chart = flow.build()
        
        # Should have 2 decision nodes (loop + inner)
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 2


# =============================================================================
# Complex Structure Tests
# =============================================================================

class TestComplexStructures:
    """Tests for complex flowchart structures."""
    
    def test_multiple_decisions_sequential(self):
        """Multiple decisions in sequence."""
        with StaticFlowBuilder("Sequential Decisions") as flow:
            with flow.decision("First?") as d1:
                with d1.yes():
                    flow.node("First yes")
                with d1.no():
                    flow.node("First no")
            
            with flow.decision("Second?") as d2:
                with d2.yes():
                    flow.node("Second yes")
                with d2.no():
                    flow.node("Second no")
            
            flow.node("Final")
        
        chart = flow.build()
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 2
    
    def test_decision_inside_one_branch(self):
        """Decision inside only one branch of another decision."""
        with StaticFlowBuilder("Asymmetric") as flow:
            with flow.decision("Outer?") as outer:
                with outer.yes():
                    with flow.decision("Inner?") as inner:
                        with inner.yes():
                            flow.node("Inner yes")
                        with inner.no():
                            flow.node("Inner no")
                with outer.no():
                    flow.node("Outer no - simple")
            flow.node("Merged")
        
        chart = flow.build()
        
        # The merged node should be reachable from all 3 terminal paths
        merged = next(n for n in chart.nodes.values() 
                     if isinstance(n, ProcessNode) and n.label == "Merged")
        incoming = [e for e in chart.edges if e.target_id == merged.id]
        assert len(incoming) == 3  # Inner yes, Inner no, Outer no


# =============================================================================
# Graph Structure Validation Tests  
# =============================================================================

class TestGraphStructure:
    """Tests for validating graph structure."""
    
    def test_no_orphan_nodes(self):
        """All nodes should be reachable from start."""
        with StaticFlowBuilder("Reachable") as flow:
            with flow.decision("A?") as a:
                with a.yes():
                    flow.node("A yes")
                with a.no():
                    flow.node("A no")
            flow.node("End point")
        
        chart = flow.build()
        
        # BFS from start
        start = next(n for n in chart.nodes.values() if isinstance(n, StartNode))
        visited = {start.id}
        queue = [start.id]
        
        while queue:
            current = queue.pop(0)
            for edge in chart.edges:
                if edge.source_id == current and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append(edge.target_id)
        
        # All nodes should be visited
        assert visited == set(chart.nodes.keys())
    
    def test_no_orphan_edges(self):
        """All edges should reference valid nodes."""
        with StaticFlowBuilder("Valid Edges") as flow:
            with flow.decision("Q?") as q:
                with q.yes():
                    flow.node("Y")
                with q.no():
                    flow.node("N")
        
        chart = flow.build()
        node_ids = set(chart.nodes.keys())
        
        for edge in chart.edges:
            assert edge.source_id in node_ids
            assert edge.target_id in node_ids
    
    def test_start_has_no_incoming(self):
        """Start node should have no incoming edges."""
        with StaticFlowBuilder("Start Check") as flow:
            flow.node("Something")
        
        chart = flow.build()
        start = next(n for n in chart.nodes.values() if isinstance(n, StartNode))
        incoming = [e for e in chart.edges if e.target_id == start.id]
        assert len(incoming) == 0
    
    def test_end_has_no_outgoing(self):
        """End nodes should have no outgoing edges."""
        with StaticFlowBuilder("End Check") as flow:
            with flow.decision("X?") as x:
                with x.yes():
                    flow.end("End A")
                with x.no():
                    flow.node("Continue")
        
        chart = flow.build()
        for node in chart.nodes.values():
            if isinstance(node, EndNode):
                outgoing = [e for e in chart.edges if e.source_id == node.id]
                assert len(outgoing) == 0


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error conditions."""
    
    def test_node_outside_context_raises(self):
        """Calling node() outside 'with' block should raise."""
        flow = StaticFlowBuilder("Outside")
        with pytest.raises(RuntimeError, match="within 'with' block"):
            flow.node("Bad")
    
    def test_decision_outside_context_raises(self):
        """Calling decision() outside 'with' block should raise."""
        flow = StaticFlowBuilder("Outside")
        with pytest.raises(RuntimeError, match="within 'with' block"):
            with flow.decision("Bad?"):
                pass
    
    def test_build_without_context_raises(self):
        """Calling build() without using context should raise."""
        flow = StaticFlowBuilder("Never Used")
        with pytest.raises(RuntimeError):
            flow.build()


# =============================================================================
# Integration Tests - Real World Examples
# =============================================================================

class TestRealWorldExamples:
    """Real-world flowchart examples."""
    
    def test_user_login_flow(self):
        """User login with validation."""
        with StaticFlowBuilder("User Login") as flow:
            flow.start("User visits login page")
            flow.node("Enter credentials")
            
            with flow.decision("Credentials valid?") as valid:
                with valid.yes():
                    with flow.decision("2FA enabled?") as twofa:
                        with twofa.yes():
                            flow.node("Enter 2FA code")
                            with flow.decision("2FA valid?") as twofa_valid:
                                with twofa_valid.yes():
                                    flow.node("Login successful")
                                with twofa_valid.no():
                                    flow.node("2FA failed")
                                    flow.end("Return to login")
                        with twofa.no():
                            flow.node("Login successful (no 2FA)")
                with valid.no():
                    flow.node("Show error message")
                    flow.end("Return to login")
            
            flow.node("Redirect to dashboard")
        
        chart = flow.build()
        
        # Verify structure
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 3
        
        ends = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(ends) == 3  # 2 early returns + 1 normal end
    
    def test_order_processing_flow(self):
        """E-commerce order processing."""
        with StaticFlowBuilder("Order Processing") as flow:
            flow.start("Order received")
            
            with flow.decision("Payment verified?") as payment:
                with payment.yes():
                    flow.node("Reserve inventory")
                    
                    with flow.decision("In stock?") as stock:
                        with stock.yes():
                            flow.node("Create shipping label")
                            flow.node("Send to warehouse")
                        with stock.no():
                            flow.node("Backorder items")
                            flow.node("Notify customer")
                    
                    flow.node("Send confirmation email")
                    
                with payment.no():
                    flow.node("Payment failed")
                    flow.end("Cancel order")
            
            flow.end("Order complete")
        
        chart = flow.build()
        
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 2
    
    def test_retry_loop_pattern(self):
        """Retry pattern with loop."""
        with StaticFlowBuilder("Retry Pattern") as flow:
            flow.node("Start operation")
            
            with flow.loop("Retry?", continue_label="Try again", exit_label="Give up"):
                flow.node("Attempt operation")
                with flow.decision("Success?") as success:
                    with success.yes():
                        flow.node("Operation completed")
                    with success.no():
                        flow.node("Log failure")
            
            with flow.decision("Was successful?") as final:
                with final.yes():
                    flow.node("Report success")
                with final.no():
                    flow.node("Report failure")
        
        chart = flow.build()
        
        # Should have loop decision + inner decision + final decision
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 3


# =============================================================================
# Serialization Compatibility Tests
# =============================================================================

class TestSerializationCompatibility:
    """Tests for JSON serialization compatibility."""
    
    def test_static_flow_json_roundtrip(self):
        """Flows should serialize/deserialize correctly."""
        from flowly.core.serialization import JsonSerializer
        
        with StaticFlowBuilder("Serializable") as flow:
            flow.node("Step 1")
            with flow.decision("Check?") as d:
                with d.yes():
                    flow.node("Yes")
                with d.no():
                    flow.node("No")
        
        chart = flow.build()
        
        json_str = JsonSerializer.to_json(chart)
        chart2 = JsonSerializer.from_json(json_str)
        
        assert len(chart2.nodes) == len(chart.nodes)
        assert len(chart2.edges) == len(chart.edges)
