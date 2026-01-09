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

    def test_shared_node_with_continue_has_single_outgoing(self):
        """Test that a shared node used before continue has exactly one outgoing edge per usage context."""
        shared_node = Node("Shared Node")
        cond1 = Decision("Condition 1?")
        cond2 = Decision("Condition 2?")
        outer_cond = Decision("Outer loop?")

        @Flow("SharedNodeContinue")
        def shared_continue(flow):
            while outer_cond():
                if cond1():
                    shared_node()
                    continue
                if cond2():
                    shared_node()
                    continue
            flow.step("Done")

        chart = shared_continue.chart

        # Find the shared node
        shared = [n for n in chart.nodes.values() if n.label == "Shared Node"][0]
        outgoing = [e for e in chart.edges if e.source_id == shared.id]

        # The shared node should have exactly 1 outgoing edge (to the loop decision)
        # NOT 2 edges (one per usage)
        assert len(outgoing) == 1, f"Expected 1 outgoing edge, got {len(outgoing)}"

        # The outgoing edge should go to the loop decision
        outer_dec = [n for n in chart.nodes.values() if n.label == "Outer loop?"][0]
        assert outgoing[0].target_id == outer_dec.id

    def test_shared_node_different_continuations(self):
        """Test shared node used in branches that continue to the same next step."""
        shared = Node("Shared")
        cond = Decision("Which?")
        next_step = Node("Next")

        @Flow("SharedDifferentContinue")
        def shared_diff(flow):
            if cond():
                shared()
            else:
                shared()
            next_step()

        chart = shared_diff.chart

        shared_node = [n for n in chart.nodes.values() if n.label == "Shared"][0]
        next_node = [n for n in chart.nodes.values() if n.label == "Next"][0]

        # Shared should have exactly 1 outgoing edge to Next
        outgoing = [e for e in chart.edges if e.source_id == shared_node.id]
        assert len(outgoing) == 1
        assert outgoing[0].target_id == next_node.id

    def test_shared_node_in_loop_with_multiple_continue_points(self):
        """Test shared node used at multiple continue points in a loop - mimics perf_oncall.py pattern."""
        create_task = Node("Create Task")
        cond1 = Decision("Dashboard regression?")
        cond2 = Decision("Config issue?")
        cond3 = Decision("Jobs failing?")
        outer = Decision("More to check?")

        @Flow("MultiContinueShared")
        def multi_continue(flow):
            while outer():
                if cond1():
                    create_task()
                    continue

                if cond3():
                    if cond2():
                        create_task()
                        continue

                    create_task()
                    continue

            flow.step("Done")

        chart = multi_continue.chart

        # Find create_task node
        task_node = [n for n in chart.nodes.values() if n.label == "Create Task"][0]
        outgoing = [e for e in chart.edges if e.source_id == task_node.id]

        # Should have exactly 1 outgoing edge (to the outer loop decision)
        assert len(outgoing) == 1, f"Expected 1 outgoing edge from Create Task, got {len(outgoing)}"

        outer_dec = [n for n in chart.nodes.values() if n.label == "More to check?"][0]
        assert outgoing[0].target_id == outer_dec.id


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


class TestContinueBreak:
    """Test continue and break statements in while loops."""
    
    def test_simple_continue(self):
        """Test continue statement jumps back to loop decision."""
        cond = Decision("More items?", yes_label="Yes", no_label="Done")
        check = Decision("Skip this?", yes_label="Skip", no_label="Process")
        process = Node("Process Item")
        
        @Flow("ContinueLoop")
        def continue_loop(flow):
            while cond():
                if check():
                    continue
                process()
            flow.step("Finished")
        
        chart = continue_loop.chart
        
        # Find the nodes
        decision = [n for n in chart.nodes.values() if n.label == "More items?"][0]
        skip_decision = [n for n in chart.nodes.values() if n.label == "Skip this?"][0]
        
        # The skip decision should have an edge back to the loop decision
        back_edges = [e for e in chart.edges if e.source_id == skip_decision.id and e.target_id == decision.id]
        assert len(back_edges) == 1
        assert back_edges[0].label == "Skip"
    
    def test_simple_break(self):
        """Test break statement exits the loop."""
        cond = Decision("More items?", yes_label="Yes", no_label="Done")
        check = Decision("Stop now?", yes_label="Stop", no_label="Continue")
        process = Node("Process Item")
        
        @Flow("BreakLoop")
        def break_loop(flow):
            while cond():
                if check():
                    break
                process()
            flow.step("Finished")
        
        chart = break_loop.chart
        
        # Find the nodes
        stop_decision = [n for n in chart.nodes.values() if n.label == "Stop now?"][0]
        finished = [n for n in chart.nodes.values() if n.label == "Finished"][0]
        
        # The stop decision's "Stop" branch should connect to Finished
        stop_edges = [e for e in chart.edges if e.source_id == stop_decision.id and e.target_id == finished.id]
        assert len(stop_edges) == 1
        assert stop_edges[0].label == "Stop"
    
    def test_continue_with_statement_before(self):
        """Test continue after processing a statement."""
        cond = Decision("More?")
        check = Decision("Skip rest?")
        step1 = Node("Step 1")
        step2 = Node("Step 2")
        
        @Flow("ContinueAfterStep")
        def continue_after_step(flow):
            while cond():
                step1()
                if check():
                    continue
                step2()
            flow.step("Done")
        
        chart = continue_after_step.chart
        
        # Find nodes
        decision = [n for n in chart.nodes.values() if n.label == "More?"][0]
        skip_decision = [n for n in chart.nodes.values() if n.label == "Skip rest?"][0]
        step1_node = [n for n in chart.nodes.values() if n.label == "Step 1"][0]
        
        # Skip decision Yes branch should go back to loop decision
        back_edges = [e for e in chart.edges if e.source_id == skip_decision.id and e.target_id == decision.id]
        assert len(back_edges) == 1
        
        # Step 1 should connect to skip decision
        step1_to_check = [e for e in chart.edges if e.source_id == step1_node.id and e.target_id == skip_decision.id]
        assert len(step1_to_check) == 1
    
    def test_break_with_statement_before(self):
        """Test break after processing a statement."""
        cond = Decision("More?")
        check = Decision("Exit now?")
        step1 = Node("Step 1")
        step2 = Node("Step 2")
        
        @Flow("BreakAfterStep")
        def break_after_step(flow):
            while cond():
                step1()
                if check():
                    break
                step2()
            flow.step("Done")
        
        chart = break_after_step.chart
        
        # Find nodes
        exit_decision = [n for n in chart.nodes.values() if n.label == "Exit now?"][0]
        done = [n for n in chart.nodes.values() if n.label == "Done"][0]
        
        # Exit decision Yes branch should go to Done
        exit_edges = [e for e in chart.edges if e.source_id == exit_decision.id and e.target_id == done.id]
        assert len(exit_edges) == 1
    
    def test_nested_continue(self):
        """Test continue in nested if statements."""
        outer_cond = Decision("Outer loop?")
        inner_check1 = Decision("Check 1?")
        inner_check2 = Decision("Check 2?")
        process = Node("Process")
        
        @Flow("NestedContinue")
        def nested_continue(flow):
            while outer_cond():
                if inner_check1():
                    if inner_check2():
                        continue
                    process()
            flow.step("Done")
        
        chart = nested_continue.chart
        
        # Find the outer loop decision
        outer = [n for n in chart.nodes.values() if n.label == "Outer loop?"][0]
        inner2 = [n for n in chart.nodes.values() if n.label == "Check 2?"][0]
        
        # Check 2's Yes branch should go back to outer loop
        back_edges = [e for e in chart.edges if e.source_id == inner2.id and e.target_id == outer.id]
        assert len(back_edges) == 1
    
    def test_nested_break(self):
        """Test break in nested if statements."""
        outer_cond = Decision("Outer loop?")
        inner_check1 = Decision("Check 1?")
        inner_check2 = Decision("Check 2?")
        process = Node("Process")
        
        @Flow("NestedBreak")
        def nested_break(flow):
            while outer_cond():
                if inner_check1():
                    if inner_check2():
                        break
                    process()
            flow.step("Done")
        
        chart = nested_break.chart
        
        # Find the done node
        done = [n for n in chart.nodes.values() if n.label == "Done"][0]
        inner2 = [n for n in chart.nodes.values() if n.label == "Check 2?"][0]
        
        # Check 2's Yes branch should go to Done
        exit_edges = [e for e in chart.edges if e.source_id == inner2.id and e.target_id == done.id]
        assert len(exit_edges) == 1
    
    def test_continue_and_break_in_same_loop(self):
        """Test both continue and break in the same loop."""
        cond = Decision("More items?")
        skip_check = Decision("Skip?")
        stop_check = Decision("Stop?")
        process = Node("Process")
        
        @Flow("ContinueAndBreak")
        def continue_and_break(flow):
            while cond():
                if skip_check():
                    continue
                if stop_check():
                    break
                process()
            flow.step("Finished")
        
        chart = continue_and_break.chart
        
        # Find nodes
        loop_decision = [n for n in chart.nodes.values() if n.label == "More items?"][0]
        skip_dec = [n for n in chart.nodes.values() if n.label == "Skip?"][0]
        stop_dec = [n for n in chart.nodes.values() if n.label == "Stop?"][0]
        finished = [n for n in chart.nodes.values() if n.label == "Finished"][0]
        
        # Skip decision should have edge back to loop
        skip_back = [e for e in chart.edges if e.source_id == skip_dec.id and e.target_id == loop_decision.id]
        assert len(skip_back) == 1
        
        # Stop decision should have edge to Finished
        stop_exit = [e for e in chart.edges if e.source_id == stop_dec.id and e.target_id == finished.id]
        assert len(stop_exit) == 1
    
    def test_continue_in_else_branch(self):
        """Test continue in the else branch of an if inside a loop."""
        cond = Decision("More?")
        check = Decision("Process?")
        process = Node("Process")
        
        @Flow("ContinueInElse")
        def continue_in_else(flow):
            while cond():
                if check():
                    process()
                else:
                    continue
            flow.step("Done")
        
        chart = continue_in_else.chart
        
        # Find nodes
        loop_decision = [n for n in chart.nodes.values() if n.label == "More?"][0]
        check_decision = [n for n in chart.nodes.values() if n.label == "Process?"][0]
        
        # Check decision's No branch should go back to loop decision
        back_edges = [e for e in chart.edges if e.source_id == check_decision.id and e.target_id == loop_decision.id]
        assert any(e.label == "No" for e in back_edges)
    
    def test_break_in_else_branch(self):
        """Test break in the else branch of an if inside a loop."""
        cond = Decision("More?")
        check = Decision("Process?")
        process = Node("Process")
        
        @Flow("BreakInElse")
        def break_in_else(flow):
            while cond():
                if check():
                    process()
                else:
                    break
            flow.step("Done")
        
        chart = break_in_else.chart
        
        # Find nodes
        check_decision = [n for n in chart.nodes.values() if n.label == "Process?"][0]
        done = [n for n in chart.nodes.values() if n.label == "Done"][0]
        
        # Check decision's No branch should go to Done
        exit_edges = [e for e in chart.edges if e.source_id == check_decision.id and e.target_id == done.id]
        assert any(e.label == "No" for e in exit_edges)
    
    def test_multiple_breaks_in_loop(self):
        """Test multiple break statements in a single loop."""
        cond = Decision("More?")
        check1 = Decision("Error 1?")
        check2 = Decision("Error 2?")
        process = Node("Process")
        
        @Flow("MultipleBreaks")
        def multiple_breaks(flow):
            while cond():
                if check1():
                    break
                process()
                if check2():
                    break
            flow.step("Done")
        
        chart = multiple_breaks.chart
        
        # Find nodes
        check1_dec = [n for n in chart.nodes.values() if n.label == "Error 1?"][0]
        check2_dec = [n for n in chart.nodes.values() if n.label == "Error 2?"][0]
        done = [n for n in chart.nodes.values() if n.label == "Done"][0]
        
        # Both check decisions should have edges to Done
        check1_exit = [e for e in chart.edges if e.source_id == check1_dec.id and e.target_id == done.id]
        check2_exit = [e for e in chart.edges if e.source_id == check2_dec.id and e.target_id == done.id]
        assert len(check1_exit) == 1
        assert len(check2_exit) == 1
    
    def test_multiple_continues_in_loop(self):
        """Test multiple continue statements in a single loop."""
        cond = Decision("More?")
        check1 = Decision("Skip 1?")
        check2 = Decision("Skip 2?")
        process = Node("Process")
        
        @Flow("MultipleContinues")
        def multiple_continues(flow):
            while cond():
                if check1():
                    continue
                if check2():
                    continue
                process()
            flow.step("Done")
        
        chart = multiple_continues.chart
        
        # Find nodes
        loop_decision = [n for n in chart.nodes.values() if n.label == "More?"][0]
        check1_dec = [n for n in chart.nodes.values() if n.label == "Skip 1?"][0]
        check2_dec = [n for n in chart.nodes.values() if n.label == "Skip 2?"][0]
        
        # Both check decisions should have edges back to loop decision
        check1_back = [e for e in chart.edges if e.source_id == check1_dec.id and e.target_id == loop_decision.id]
        check2_back = [e for e in chart.edges if e.source_id == check2_dec.id and e.target_id == loop_decision.id]
        assert len(check1_back) == 1
        assert len(check2_back) == 1


class TestNotCondition:
    """Test negated conditions (not) in if and while statements."""
    
    def test_if_not_simple(self):
        """Test simple if not condition."""
        cond = Decision("Is valid?", yes_label="Valid", no_label="Invalid")
        handle_invalid = Node("Handle Invalid")
        
        @Flow("IfNot")
        def if_not(flow):
            if not cond():
                handle_invalid()
            flow.step("Done")
        
        chart = if_not.chart
        
        # Find nodes
        decision = [n for n in chart.nodes.values() if n.label == "Is valid?"][0]
        invalid_node = [n for n in chart.nodes.values() if n.label == "Handle Invalid"][0]
        done = [n for n in chart.nodes.values() if n.label == "Done"][0]
        
        # The "Invalid" (no) branch should go to handle_invalid
        invalid_edges = [e for e in chart.edges if e.source_id == decision.id and e.target_id == invalid_node.id]
        assert len(invalid_edges) == 1
        assert invalid_edges[0].label == "Invalid"
        
        # The "Valid" (yes) branch should go directly to Done
        valid_edges = [e for e in chart.edges if e.source_id == decision.id and e.target_id == done.id]
        assert len(valid_edges) == 1
        assert valid_edges[0].label == "Valid"
    
    def test_if_not_with_else(self):
        """Test if not with else branch."""
        cond = Decision("Success?", yes_label="Yes", no_label="No")
        handle_error = Node("Handle Error")
        handle_success = Node("Handle Success")
        
        @Flow("IfNotElse")
        def if_not_else(flow):
            if not cond():
                handle_error()
            else:
                handle_success()
            flow.step("Done")
        
        chart = if_not_else.chart
        
        # Find nodes
        decision = [n for n in chart.nodes.values() if n.label == "Success?"][0]
        error_node = [n for n in chart.nodes.values() if n.label == "Handle Error"][0]
        success_node = [n for n in chart.nodes.values() if n.label == "Handle Success"][0]
        
        # The "No" branch should go to handle_error (if not body)
        error_edges = [e for e in chart.edges if e.source_id == decision.id and e.target_id == error_node.id]
        assert len(error_edges) == 1
        assert error_edges[0].label == "No"
        
        # The "Yes" branch should go to handle_success (else body)
        success_edges = [e for e in chart.edges if e.source_id == decision.id and e.target_id == success_node.id]
        assert len(success_edges) == 1
        assert success_edges[0].label == "Yes"
    
    def test_while_not(self):
        """Test while not condition."""
        cond = Decision("Done?", yes_label="Yes", no_label="No")
        process = Node("Process")
        
        @Flow("WhileNot")
        def while_not(flow):
            while not cond():
                process()
            flow.step("Finished")
        
        chart = while_not.chart
        
        # Find nodes
        decision = [n for n in chart.nodes.values() if n.label == "Done?"][0]
        process_node = [n for n in chart.nodes.values() if n.label == "Process"][0]
        finished = [n for n in chart.nodes.values() if n.label == "Finished"][0]
        
        # The "No" branch should go to process (while not body)
        process_edges = [e for e in chart.edges if e.source_id == decision.id and e.target_id == process_node.id]
        assert len(process_edges) == 1
        assert process_edges[0].label == "No"
        
        # Process should loop back to decision
        back_edges = [e for e in chart.edges if e.source_id == process_node.id and e.target_id == decision.id]
        assert len(back_edges) == 1
        
        # The "Yes" branch should exit to Finished
        exit_edges = [e for e in chart.edges if e.source_id == decision.id and e.target_id == finished.id]
        assert len(exit_edges) == 1
        assert exit_edges[0].label == "Yes"
    
    def test_nested_if_not(self):
        """Test nested if not conditions."""
        outer = Decision("Outer valid?")
        inner = Decision("Inner valid?")
        handle_outer = Node("Handle Outer Invalid")
        handle_inner = Node("Handle Inner Invalid")
        
        @Flow("NestedIfNot")
        def nested_if_not(flow):
            if not outer():
                handle_outer()
            else:
                if not inner():
                    handle_inner()
            flow.step("Done")
        
        chart = nested_if_not.chart
        
        # Find nodes
        outer_dec = [n for n in chart.nodes.values() if n.label == "Outer valid?"][0]
        inner_dec = [n for n in chart.nodes.values() if n.label == "Inner valid?"][0]
        handle_outer_node = [n for n in chart.nodes.values() if n.label == "Handle Outer Invalid"][0]
        handle_inner_node = [n for n in chart.nodes.values() if n.label == "Handle Inner Invalid"][0]
        
        # Outer No -> handle_outer
        outer_no = [e for e in chart.edges if e.source_id == outer_dec.id and e.target_id == handle_outer_node.id]
        assert len(outer_no) == 1
        assert outer_no[0].label == "No"
        
        # Outer Yes -> inner decision
        outer_yes = [e for e in chart.edges if e.source_id == outer_dec.id and e.target_id == inner_dec.id]
        assert len(outer_yes) == 1
        assert outer_yes[0].label == "Yes"
        
        # Inner No -> handle_inner
        inner_no = [e for e in chart.edges if e.source_id == inner_dec.id and e.target_id == handle_inner_node.id]
        assert len(inner_no) == 1
        assert inner_no[0].label == "No"
    
    def test_if_not_vs_if_comparison(self):
        """Test that if not properly inverts compared to regular if."""
        cond1 = Decision("Cond 1?", yes_label="T1", no_label="F1")
        cond2 = Decision("Cond 2?", yes_label="T2", no_label="F2")
        step_t1 = Node("T1 Step")
        step_f2 = Node("F2 Step")
        
        @Flow("IfComparison")
        def if_comparison(flow):
            # Regular if - body executes on Yes
            if cond1():
                step_t1()
            # Negated if - body executes on No
            if not cond2():
                step_f2()
            flow.step("Done")
        
        chart = if_comparison.chart
        
        dec1 = [n for n in chart.nodes.values() if n.label == "Cond 1?"][0]
        dec2 = [n for n in chart.nodes.values() if n.label == "Cond 2?"][0]
        t1 = [n for n in chart.nodes.values() if n.label == "T1 Step"][0]
        f2 = [n for n in chart.nodes.values() if n.label == "F2 Step"][0]
        
        # Regular if: Yes -> body
        t1_edge = [e for e in chart.edges if e.source_id == dec1.id and e.target_id == t1.id]
        assert t1_edge[0].label == "T1"
        
        # Negated if: No -> body
        f2_edge = [e for e in chart.edges if e.source_id == dec2.id and e.target_id == f2.id]
        assert f2_edge[0].label == "F2"
    
    def test_while_not_with_continue(self):
        """Test while not with continue statement."""
        cond = Decision("Finished?", yes_label="Done", no_label="Continue")
        check = Decision("Skip?")
        process = Node("Process")
        
        @Flow("WhileNotContinue")
        def while_not_continue(flow):
            while not cond():
                if check():
                    continue
                process()
            flow.step("End")
        
        chart = while_not_continue.chart
        
        # Find nodes
        decision = [n for n in chart.nodes.values() if n.label == "Finished?"][0]
        skip_dec = [n for n in chart.nodes.values() if n.label == "Skip?"][0]
        process_node = [n for n in chart.nodes.values() if n.label == "Process"][0]
        
        # The "Continue" (no) branch should enter loop body
        body_entry = [e for e in chart.edges if e.source_id == decision.id and e.target_id == skip_dec.id]
        assert len(body_entry) == 1
        assert body_entry[0].label == "Continue"
        
        # Continue should go back to decision
        back_edges = [e for e in chart.edges if e.source_id == skip_dec.id and e.target_id == decision.id]
        assert len(back_edges) == 1
    
    def test_while_not_with_break(self):
        """Test while not with break statement."""
        cond = Decision("Empty?", yes_label="Empty", no_label="HasData")
        check = Decision("Exit now?")
        process = Node("Process")
        
        @Flow("WhileNotBreak")
        def while_not_break(flow):
            while not cond():
                if check():
                    break
                process()
            flow.step("End")
        
        chart = while_not_break.chart
        
        # Find nodes
        decision = [n for n in chart.nodes.values() if n.label == "Empty?"][0]
        exit_dec = [n for n in chart.nodes.values() if n.label == "Exit now?"][0]
        end_node = [n for n in chart.nodes.values() if n.label == "End"][0]
        
        # The "HasData" (no) branch should enter loop body
        body_entry = [e for e in chart.edges if e.source_id == decision.id and e.target_id == exit_dec.id]
        assert len(body_entry) == 1
        assert body_entry[0].label == "HasData"
        
        # Break should go to End
        break_edges = [e for e in chart.edges if e.source_id == exit_dec.id and e.target_id == end_node.id]
        assert len(break_edges) == 1
        
        # The "Empty" (yes) branch should also go to End (loop exit)
        exit_edges = [e for e in chart.edges if e.source_id == decision.id and e.target_id == end_node.id]
        assert len(exit_edges) == 1
        assert exit_edges[0].label == "Empty"
    
    def test_custom_labels_with_not(self):
        """Test that custom labels are properly swapped with not."""
        cond = Decision("Ready?", yes_label="Proceed", no_label="Wait")
        wait_step = Node("Wait Step")
        
        @Flow("CustomLabelsNot")
        def custom_labels_not(flow):
            if not cond():
                wait_step()
            flow.step("Continue")
        
        chart = custom_labels_not.chart
        
        decision = [n for n in chart.nodes.values() if n.label == "Ready?"][0]
        wait_node = [n for n in chart.nodes.values() if n.label == "Wait Step"][0]
        continue_node = [n for n in chart.nodes.values() if n.label == "Continue"][0]
        
        # if not body uses No label ("Wait")
        wait_edge = [e for e in chart.edges if e.source_id == decision.id and e.target_id == wait_node.id]
        assert wait_edge[0].label == "Wait"
        
        # else path (skipped body) uses Yes label ("Proceed")
        proceed_edge = [e for e in chart.edges if e.source_id == decision.id and e.target_id == continue_node.id]
        assert proceed_edge[0].label == "Proceed"


class TestWhileTrue:
    """Test while True infinite loops."""
    
    def test_simple_while_true(self):
        """Test simple while True with break."""
        process = Node("Process")
        check = Decision("Done?")
        
        @Flow("WhileTrue")
        def while_true(flow):
            while True:
                process()
                if check():
                    break
            flow.step("End")
        
        chart = while_true.chart
        
        # Should have a loop node
        loop_nodes = [n for n in chart.nodes.values() if n.label == "(loop)"]
        assert len(loop_nodes) == 1
        loop_node = loop_nodes[0]
        
        # Process should connect from loop node
        process_node = [n for n in chart.nodes.values() if n.label == "Process"][0]
        loop_to_process = [e for e in chart.edges if e.source_id == loop_node.id and e.target_id == process_node.id]
        assert len(loop_to_process) == 1
    
    def test_while_true_no_break_no_exit(self):
        """Test while True without break has no exit to End."""
        process = Node("Process Forever")
        
        @Flow("InfiniteLoop")
        def infinite_loop(flow):
            while True:
                process()
            flow.step("Never Reached")
        
        chart = infinite_loop.chart
        
        # The "Never Reached" step should NOT have any incoming edges from the loop
        # because the loop never exits
        never_reached = [n for n in chart.nodes.values() if n.label == "Never Reached"]
        # Actually, Never Reached won't exist because there are no exits from while True
        # Let's check if End exists with no incoming edges
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        
        # There should be no end node because while True with no break never exits
        # Or there might be one with no incoming edges
        if end_nodes:
            for end_node in end_nodes:
                incoming = [e for e in chart.edges if e.target_id == end_node.id]
                # End should have no incoming edges from loop body
                process_node = [n for n in chart.nodes.values() if n.label == "Process Forever"][0]
                process_to_end = [e for e in chart.edges if e.source_id == process_node.id and e.target_id == end_node.id]
                assert len(process_to_end) == 0
    
    def test_while_true_with_continue(self):
        """Test while True with continue."""
        check = Decision("Skip?")
        process = Node("Process")
        exit_check = Decision("Exit?")
        
        @Flow("WhileTrueContinue")
        def while_true_continue(flow):
            while True:
                if check():
                    continue
                process()
                if exit_check():
                    break
            flow.step("End")
        
        chart = while_true_continue.chart
        
        # Find nodes
        loop_node = [n for n in chart.nodes.values() if n.label == "(loop)"][0]
        skip_dec = [n for n in chart.nodes.values() if n.label == "Skip?"][0]
        
        # Skip decision Yes should go back to loop
        skip_back = [e for e in chart.edges if e.source_id == skip_dec.id and e.target_id == loop_node.id]
        assert len(skip_back) == 1
    
    def test_while_true_multiple_breaks(self):
        """Test while True with multiple break points."""
        check1 = Decision("Error?")
        check2 = Decision("Done?")
        process = Node("Process")
        
        @Flow("WhileTrueMultiBreak")
        def while_true_multi_break(flow):
            while True:
                if check1():
                    break
                process()
                if check2():
                    break
            flow.step("End")
        
        chart = while_true_multi_break.chart
        
        # Find nodes
        error_dec = [n for n in chart.nodes.values() if n.label == "Error?"][0]
        done_dec = [n for n in chart.nodes.values() if n.label == "Done?"][0]
        end_node = [n for n in chart.nodes.values() if n.label == "End"][0]
        
        # Both decisions should have paths to End
        error_to_end = [e for e in chart.edges if e.source_id == error_dec.id and e.target_id == end_node.id]
        done_to_end = [e for e in chart.edges if e.source_id == done_dec.id and e.target_id == end_node.id]
        assert len(error_to_end) == 1
        assert len(done_to_end) == 1
    
    def test_while_true_with_explicit_end(self):
        """Test while True with flow.end() inside."""
        check = Decision("Fatal error?")
        process = Node("Process")
        
        @Flow("WhileTrueExplicitEnd")
        def while_true_explicit_end(flow):
            while True:
                if check():
                    flow.end("Fatal Error Exit")
                    break
                process()
            flow.step("Normal Exit")
        
        chart = while_true_explicit_end.chart
        
        # Should have two end-like nodes
        fatal_end = [n for n in chart.nodes.values() if n.label == "Fatal Error Exit"]
        assert len(fatal_end) == 1
    
    def test_while_true_back_edge(self):
        """Test that while True creates proper back edges."""
        process = Node("Process")
        check = Decision("Continue?")
        
        @Flow("WhileTrueBackEdge")
        def while_true_back_edge(flow):
            while True:
                process()
                if check():
                    continue
                break
            flow.step("End")
        
        chart = while_true_back_edge.chart
        
        # Find nodes
        loop_node = [n for n in chart.nodes.values() if n.label == "(loop)"][0]
        check_dec = [n for n in chart.nodes.values() if n.label == "Continue?"][0]
        
        # Continue (Yes) should go back to loop
        continue_back = [e for e in chart.edges if e.source_id == check_dec.id and e.target_id == loop_node.id]
        assert len(continue_back) == 1
    
    def test_while_true_nested_if(self):
        """Test while True with nested if statements."""
        check1 = Decision("Condition 1?")
        check2 = Decision("Condition 2?")
        action1 = Node("Action 1")
        action2 = Node("Action 2")
        
        @Flow("WhileTrueNestedIf")
        def while_true_nested_if(flow):
            while True:
                if check1():
                    action1()
                    if check2():
                        break
                else:
                    action2()
                    break
            flow.step("End")
        
        chart = while_true_nested_if.chart
        
        # Both break paths should lead to End
        end_node = [n for n in chart.nodes.values() if n.label == "End"][0]
        check2_dec = [n for n in chart.nodes.values() if n.label == "Condition 2?"][0]
        action2_node = [n for n in chart.nodes.values() if n.label == "Action 2"][0]
        
        check2_to_end = [e for e in chart.edges if e.source_id == check2_dec.id and e.target_id == end_node.id]
        action2_to_end = [e for e in chart.edges if e.source_id == action2_node.id and e.target_id == end_node.id]
        assert len(check2_to_end) == 1
        assert len(action2_to_end) == 1
    
    def test_while_true_only_break(self):
        """Test while True with only a break statement."""
        check = Decision("Condition?")
        
        @Flow("WhileTrueOnlyBreak")
        def while_true_only_break(flow):
            while True:
                if check():
                    break
            flow.step("End")
        
        chart = while_true_only_break.chart
        
        # Loop should have minimal structure
        loop_node = [n for n in chart.nodes.values() if n.label == "(loop)"][0]
        check_dec = [n for n in chart.nodes.values() if n.label == "Condition?"][0]
        end_node = [n for n in chart.nodes.values() if n.label == "End"][0]
        
        # Loop -> Check
        loop_to_check = [e for e in chart.edges if e.source_id == loop_node.id and e.target_id == check_dec.id]
        assert len(loop_to_check) == 1
        
        # Check Yes -> End (break)
        check_to_end = [e for e in chart.edges if e.source_id == check_dec.id and e.target_id == end_node.id]
        assert len(check_to_end) == 1
        
        # Check No -> Loop (back edge)
        check_to_loop = [e for e in chart.edges if e.source_id == check_dec.id and e.target_id == loop_node.id]
        assert len(check_to_loop) == 1
    
    def test_while_true_break_with_statement_after(self):
        """Test that statements after break in while True are unreachable."""
        check = Decision("Exit?")
        before = Node("Before")
        after = Node("After Break")
        
        @Flow("WhileTrueAfterBreak")
        def while_true_after_break(flow):
            while True:
                before()
                if check():
                    break
                after()
            flow.step("End")
        
        chart = while_true_after_break.chart
        
        # After should only be reachable from check's No branch
        after_node = [n for n in chart.nodes.values() if n.label == "After Break"][0]
        check_dec = [n for n in chart.nodes.values() if n.label == "Exit?"][0]
        
        incoming = [e for e in chart.edges if e.target_id == after_node.id]
        assert len(incoming) == 1
        assert incoming[0].source_id == check_dec.id
        assert incoming[0].label == "No"


class TestErrorHandling:
    """Test error handling."""
    
    def test_undefined_node_error(self):
        """Test that undefined nodes give clear error."""
        # Error is raised at decoration time when AST is analyzed
        with pytest.raises(NameError, match="not defined"):
            @Flow("Undefined")
            def undefined(flow):
                undefined_node()  # Not defined!
