"""
Tests for the AST-based flowchart builder.
"""

import pytest
from flowly.frontend.ast_builder import flowchart, flowchart_from_source, ASTFlowBuilder
from flowly.core.ir import StartNode, EndNode, ProcessNode, DecisionNode


class TestBasicAST:
    """Test basic AST parsing."""
    
    def test_simple_function(self):
        """Test a simple function with just calls."""
        @flowchart
        def simple():
            step_one()
            step_two()
            step_three()
        
        chart = simple.flowchart
        
        # Should have: Start, 3 process nodes, End
        assert len(chart.nodes) == 5
        assert len(chart.edges) == 4
        
        # Check node types
        types = [type(n).__name__ for n in chart.nodes.values()]
        assert types.count("StartNode") == 1
        assert types.count("ProcessNode") == 3
        assert types.count("EndNode") == 1
    
    def test_function_call_labels(self):
        """Test that function calls are converted to readable labels."""
        @flowchart
        def process():
            check_user_input()
            validate_data()
        
        chart = process.flowchart
        labels = [n.label for n in chart.nodes.values()]
        
        assert "Check User Input" in labels
        assert "Validate Data" in labels
    
    def test_custom_name(self):
        """Test custom flowchart name."""
        @flowchart(name="My Custom Flow")
        def my_func():
            do_something()
        
        assert my_func.flowchart.name == "My Custom Flow"
    
    def test_function_still_callable(self):
        """Test that decorated function is still callable."""
        @flowchart
        def add_numbers():
            return 42
        
        # The function should still work
        result = add_numbers()
        # Note: The actual function body uses undefined functions,
        # but since we're just testing the decorator mechanics,
        # we should at least be able to call it (even if it fails)
        assert hasattr(add_numbers, 'flowchart')


class TestIfStatements:
    """Test if/else AST parsing."""
    
    def test_simple_if(self):
        """Test simple if statement."""
        @flowchart
        def process():
            if check_condition():
                do_something()
        
        chart = process.flowchart
        
        # Should have: Start, Decision, Process (yes branch), End
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 1
        assert "Check Condition" in decision_nodes[0].label
    
    def test_if_else(self):
        """Test if/else branches."""
        @flowchart
        def process():
            if is_valid():
                handle_valid()
            else:
                handle_invalid()
        
        chart = process.flowchart
        
        # Both branches should exist
        labels = [n.label for n in chart.nodes.values()]
        assert "Handle Valid" in labels
        assert "Handle Invalid" in labels
        
        # Check edge labels
        edge_labels = [e.label for e in chart.edges if e.label]
        assert "Yes" in edge_labels
        assert "No" in edge_labels
    
    def test_nested_if(self):
        """Test nested if statements."""
        @flowchart
        def process():
            if outer_condition():
                if inner_condition():
                    deep_action()
        
        chart = process.flowchart
        
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 2
    
    def test_if_elif_else(self):
        """Test if/elif/else chains."""
        @flowchart
        def process():
            if condition_a():
                action_a()
            elif condition_b():
                action_b()
            else:
                action_c()
        
        chart = process.flowchart
        
        # Should have 2 decision nodes (if and elif)
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 2
        
        # All actions should be present
        labels = [n.label for n in chart.nodes.values()]
        assert "Action A" in labels
        assert "Action B" in labels
        assert "Action C" in labels
    
    def test_branches_merge(self):
        """Test that branches merge at next statement."""
        @flowchart
        def process():
            if condition():
                yes_action()
            else:
                no_action()
            
            after_decision()
        
        chart = process.flowchart
        
        # Find the "after_decision" node
        after_node = None
        for n in chart.nodes.values():
            if n.label == "After Decision":
                after_node = n
                break
        
        assert after_node is not None
        
        # Should have 2 incoming edges (from both branches)
        incoming = [e for e in chart.edges if e.target_id == after_node.id]
        assert len(incoming) == 2


class TestLoops:
    """Test loop AST parsing."""
    
    def test_while_loop(self):
        """Test while loop creates decision with back-edge."""
        @flowchart
        def process():
            while has_more_items():
                process_item()
        
        chart = process.flowchart
        
        # Should have a decision node for the while condition
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 1
        
        # Should have a back-edge
        decision = decision_nodes[0]
        back_edges = [e for e in chart.edges if e.target_id == decision.id and e.source_id != decision.id]
        # One from before the loop, one from inside the loop
        assert len(back_edges) >= 1
    
    def test_for_loop(self):
        """Test for loop creates iteration decision."""
        @flowchart
        def process():
            for item in get_items():
                handle_item()
        
        chart = process.flowchart
        
        decision_nodes = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decision_nodes) == 1
        assert "More" in decision_nodes[0].label


class TestReturn:
    """Test return statement handling."""
    
    def test_return_creates_end(self):
        """Test that return creates an end node."""
        @flowchart
        def process():
            do_something()
            return
        
        chart = process.flowchart
        
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(end_nodes) == 1
        assert end_nodes[0].label == "Return"
    
    def test_return_with_value(self):
        """Test return with value shows in label."""
        @flowchart
        def process():
            return success
        
        chart = process.flowchart
        
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(end_nodes) == 1
        assert "Success" in end_nodes[0].label
    
    def test_multiple_returns(self):
        """Test multiple return paths create multiple ends."""
        @flowchart
        def process():
            if error_condition():
                return
            
            do_work()
            return
        
        chart = process.flowchart
        
        end_nodes = [n for n in chart.nodes.values() if isinstance(n, EndNode)]
        assert len(end_nodes) == 2


class TestComplexExpressions:
    """Test complex expression handling."""
    
    def test_comparison_operators(self):
        """Test comparison operators in conditions."""
        @flowchart
        def process():
            if x > 10:
                handle_large()
        
        chart = process.flowchart
        
        decision = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)][0]
        assert ">" in decision.label
    
    def test_boolean_operators(self):
        """Test boolean operators in conditions."""
        @flowchart
        def process():
            if condition_a() and condition_b():
                both_true()
        
        chart = process.flowchart
        
        decision = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)][0]
        assert "and" in decision.label
    
    def test_function_with_args(self):
        """Test function calls with arguments."""
        @flowchart
        def process():
            send_email(recipient, subject)
        
        chart = process.flowchart
        
        labels = [n.label for n in chart.nodes.values()]
        # Should include the arguments
        assert any("Recipient" in label for label in labels)


class TestFromSource:
    """Test building from source string."""
    
    def test_from_source(self):
        """Test flowchart_from_source function."""
        source = '''
def my_process():
    step_one()
    if check():
        step_two()
    step_three()
'''
        chart = flowchart_from_source(source, "Test Flow")
        
        assert chart.name == "Test Flow"
        assert len(chart.nodes) == 6  # Start, 3 steps, decision, end
    
    def test_from_source_invalid(self):
        """Test that invalid source raises error."""
        with pytest.raises(ValueError):
            flowchart_from_source("x = 1", "Test")


class TestRealWorldExamples:
    """Test real-world-like examples."""
    
    def test_order_processing(self):
        """Test an order processing flow."""
        @flowchart
        def order_processing():
            receive_order()
            validate_order()
            
            if payment_successful():
                if in_stock():
                    reserve_inventory()
                    ship_order()
                else:
                    backorder()
            else:
                cancel_order()
            
            send_notification()
        
        chart = order_processing.flowchart
        
        # Verify structure
        assert len(chart.nodes) >= 10
        
        # Verify decisions
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) == 2
    
    def test_user_authentication(self):
        """Test a user authentication flow."""
        @flowchart
        def authenticate():
            get_credentials()
            
            if user_exists():
                if password_valid():
                    if mfa_required():
                        verify_mfa()
                    create_session()
                else:
                    increment_failed_attempts()
                    if too_many_attempts():
                        lock_account()
                        return
            else:
                prompt_registration()
            
            redirect_user()
        
        chart = authenticate.flowchart
        
        # Should have multiple decision points
        decisions = [n for n in chart.nodes.values() if isinstance(n, DecisionNode)]
        assert len(decisions) >= 4


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_empty_function(self):
        """Test function with just pass."""
        @flowchart
        def empty():
            pass
        
        chart = empty.flowchart
        
        # Should have Start and End
        assert len(chart.nodes) == 2
    
    def test_docstring_ignored(self):
        """Test that docstrings are handled."""
        @flowchart
        def documented():
            """This is a docstring."""
            do_work()
        
        chart = documented.flowchart
        
        # Docstring shouldn't create extra nodes
        labels = [n.label for n in chart.nodes.values()]
        assert not any("docstring" in label.lower() for label in labels)
    
    def test_chained_calls(self):
        """Test chained method calls."""
        @flowchart
        def process():
            data.transform().save()
        
        chart = process.flowchart
        
        # Should handle chained calls
        assert len(chart.nodes) >= 2


class TestSharedNodes:
    """Test shared_nodes feature."""
    
    def test_shared_nodes_merges_same_call(self):
        """Test that shared_nodes=True merges same function calls."""
        @flowchart(shared_nodes=True)
        def process():
            if condition():
                step_a()
                common_step()
            else:
                step_b()
                common_step()  # Should connect to same node!
            
            final()
        
        chart = process.flowchart
        
        # Find common_step nodes
        common_nodes = [n for n in chart.nodes.values() if n.label == "Common Step"]
        assert len(common_nodes) == 1  # Only ONE common_step node
        
        # That node should have 2 incoming edges
        common_id = common_nodes[0].id
        incoming = [e for e in chart.edges if e.target_id == common_id]
        assert len(incoming) == 2
    
    def test_normal_mode_creates_duplicates(self):
        """Test that normal mode (shared_nodes=False) creates separate nodes."""
        @flowchart(shared_nodes=False)
        def process():
            if condition():
                step_a()
                common_step()
            else:
                step_b()
                common_step()  # Creates a SECOND node
        
        chart = process.flowchart
        
        # Find common_step nodes
        common_nodes = [n for n in chart.nodes.values() if n.label == "Common Step"]
        assert len(common_nodes) == 2  # TWO separate nodes
    
    def test_shared_nodes_with_decisions(self):
        """Test shared nodes work with complex branching."""
        @flowchart(shared_nodes=True)
        def process():
            if a():
                x()
                if b():
                    shared()
                else:
                    y()
                    shared()
            else:
                z()
                shared()  # Third path to same node!
        
        chart = process.flowchart
        
        shared_nodes = [n for n in chart.nodes.values() if n.label == "Shared"]
        assert len(shared_nodes) == 1
        
        # Should have 3 incoming edges
        shared_id = shared_nodes[0].id
        incoming = [e for e in chart.edges if e.target_id == shared_id]
        assert len(incoming) == 3
