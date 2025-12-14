"""
Tests for the explicit DSL-based flowchart builder.
"""

import pytest
from flowly.frontend.dsl import Flow, Node, Decision, NodeDef, DecisionDef
from flowly.core.ir import StartNode, EndNode, ProcessNode, DecisionNode


class TestNodeDefinition:
    """Test Node and Decision definition."""
    
    def test_node_creation(self):
        """Test creating a Node definition."""
        node = Node("My Node", description="A test node")
        
        assert node.label == "My Node"
        assert node.description == "A test node"
    
    def test_node_with_metadata(self):
        """Test Node with custom metadata."""
        node = Node("Node", metadata={"custom": "value"})
        
        assert node.metadata["custom"] == "value"
    
    def test_decision_creation(self):
        """Test creating a Decision definition."""
        dec = Decision("Is it?", yes_label="Yep", no_label="Nope")
        
        assert dec.label == "Is it?"
        assert dec.yes_label == "Yep"
        assert dec.no_label == "Nope"
    
    def test_node_outside_flow_raises(self):
        """Test that calling a node outside a flow raises error."""
        node = Node("Test")
        
        with pytest.raises(RuntimeError, match="outside of a @Flow function"):
            node()
    
    def test_decision_outside_flow_raises(self):
        """Test that calling a decision outside a flow raises error."""
        dec = Decision("Test?")
        
        with pytest.raises(RuntimeError, match="outside of a @Flow function"):
            dec()


class TestSimpleFlows:
    """Test simple flow definitions."""
    
    def test_empty_flow(self):
        """Test a flow with no steps."""
        @Flow("Empty")
        def empty(flow):
            pass
        
        chart = empty.chart
        
        # Should have Start and End
        assert len(chart.nodes) == 2
        assert any(isinstance(n, StartNode) for n in chart.nodes.values())
        assert any(isinstance(n, EndNode) for n in chart.nodes.values())
    
    def test_single_node_flow(self):
        """Test a flow with one node."""
        step = Node("Single Step")
        
        @Flow("Single")
        def single(flow):
            step()
        
        chart = single.chart
        
        # Start, Step, End
        assert len(chart.nodes) == 3
        assert any(n.label == "Single Step" for n in chart.nodes.values())
    
    def test_sequential_nodes(self):
        """Test a flow with sequential nodes."""
        a = Node("Step A")
        b = Node("Step B")
        c = Node("Step C")
        
        @Flow("Sequential")
        def seq(flow):
            a()
            b()
            c()
        
        chart = seq.chart
        
        # Start, A, B, C, End
        assert len(chart.nodes) == 5
        assert len(chart.edges) == 4
    
    def test_inline_step(self):
        """Test inline step creation."""
        @Flow("Inline")
        def inline(flow):
            flow.step("Inline Step", description="Created inline")
        
        chart = inline.chart
        
        labels = [n.label for n in chart.nodes.values()]
        assert "Inline Step" in labels
    
    def test_explicit_end(self):
        """Test explicit end node."""
        @Flow("Explicit End")
        def explicit(flow):
            flow.step("Do something")
            flow.end("Custom End", description="We're done")
        
        chart = explicit.chart
        
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(end_nodes) == 1
        assert end_nodes[0].label == "Custom End"


class TestDecisions:
    """Test decision handling."""
    
    def test_simple_if(self):
        """Test simple if statement."""
        step = Node("Step")
        cond = Decision("Condition?")
        
        @Flow("If")
        def if_flow(flow):
            if cond():
                step()
        
        chart = if_flow.chart
        
        # Should have decision node
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 1
        assert decisions[0].label == "Condition?"
    
    def test_if_else(self):
        """Test if/else branches."""
        yes_step = Node("Yes Step")
        no_step = Node("No Step")
        cond = Decision("Which way?", yes_label="This", no_label="That")
        
        @Flow("IfElse")
        def if_else(flow):
            if cond():
                yes_step()
            else:
                no_step()
        
        chart = if_else.chart
        
        # Check edge labels
        edge_labels = [e.label for e in chart.edges if e.label]
        assert "This" in edge_labels
        assert "That" in edge_labels
    
    def test_nested_if(self):
        """Test nested if statements."""
        outer = Decision("Outer?")
        inner = Decision("Inner?")
        deep = Node("Deep")
        
        @Flow("Nested")
        def nested(flow):
            if outer():
                if inner():
                    deep()
        
        chart = nested.chart
        
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 2


class TestNodeReuse:
    """Test node reuse (same node multiple times)."""
    
    def test_same_node_reused(self):
        """Test that calling the same node twice reuses it."""
        shared = Node("Shared Step")
        cond = Decision("Which path?")
        
        @Flow("Reuse")
        def reuse(flow):
            if cond():
                flow.step("Path A")
                shared()  # First use
            else:
                flow.step("Path B")
                shared()  # Second use - same node!
        
        chart = reuse.chart
        
        # Should only have ONE "Shared Step" node
        shared_nodes = [n for n in chart.nodes.values() if n.label == "Shared Step"]
        assert len(shared_nodes) == 1
        
        # That node should have 2 incoming edges
        shared_id = shared_nodes[0].id
        incoming = [e for e in chart.edges if e.target_id == shared_id]
        assert len(incoming) == 2


class TestComplexFlows:
    """Test complex flow patterns."""
    
    def test_multiple_ends(self):
        """Test flow with multiple end points."""
        cond = Decision("Success?")
        
        @Flow("MultiEnd")
        def multi(flow):
            if cond():
                flow.end("Success")
            else:
                flow.end("Failure")
        
        chart = multi.chart
        
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(end_nodes) == 2
    
    def test_while_loop(self):
        """Test while loop."""
        more = Decision("More items?", yes_label="Yes", no_label="Done")
        process = Node("Process Item")
        
        @Flow("Loop")
        def loop(flow):
            while more():
                process()
            flow.step("Finished")
        
        chart = loop.chart
        
        # Should have a back-edge
        decision = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)][0]
        
        # Find edges going TO the decision
        back_edges = [e for e in chart.edges if e.target_id == decision.id]
        assert len(back_edges) >= 2  # One from start, one from loop body


class TestMetadataPreservation:
    """Test that metadata is preserved."""
    
    def test_node_description_preserved(self):
        """Test that node descriptions are in the chart."""
        node = Node("Test", description="My description")
        
        @Flow("Meta")
        def meta(flow):
            node()
        
        chart = meta.chart
        
        test_node = [n for n in chart.nodes.values() if n.label == "Test"][0]
        assert test_node.metadata.get("description") == "My description"
    
    def test_decision_description_preserved(self):
        """Test that decision descriptions are preserved."""
        dec = Decision("Test?", description="Important choice")
        
        @Flow("DecMeta")
        def dec_meta(flow):
            if dec():
                pass
        
        chart = dec_meta.chart
        
        dec_node = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)][0]
        assert dec_node.metadata.get("description") == "Important choice"


class TestErrorHandling:
    """Test error handling."""
    
    def test_undefined_node_error(self):
        """Test that undefined nodes give clear error."""
        # Error is raised at decoration time when AST is analyzed
        with pytest.raises(NameError, match="not defined"):
            @Flow("Undefined")
            def undefined(flow):
                undefined_node()  # Not defined!
