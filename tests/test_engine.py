import pytest
from flowly.core.ir import FlowChart, StartNode, ProcessNode, DecisionNode, EndNode, Edge
from flowly.engine import FlowRunner


class TestFlowRunnerBasic:
    """Basic FlowRunner functionality tests."""
    
    @pytest.fixture
    def linear_graph(self):
        chart = FlowChart("Linear")
        start = chart.add_node(StartNode(label="Start"))
        proc = chart.add_node(ProcessNode(label="Process"))
        end = chart.add_node(EndNode(label="End"))
        
        chart.add_edge(Edge(start.id, proc.id))
        chart.add_edge(Edge(proc.id, end.id))
        return chart, start, proc, end

    def test_runner_steps_linear(self, linear_graph):
        chart, start, proc, end = linear_graph
        runner = FlowRunner(chart)
        
        runner.start()
        assert runner.current_node == start
        
        runner.step()
        assert runner.current_node == proc
        
        runner.step()
        assert runner.current_node == end

    def test_runner_decision(self):
        chart = FlowChart("Decision")
        start = chart.add_node(StartNode(label="Start"))
        dec = chart.add_node(DecisionNode(label="Decide"))
        res1 = chart.add_node(ProcessNode(label="A"))
        res2 = chart.add_node(ProcessNode(label="B"))
        
        chart.add_edge(Edge(start.id, dec.id))
        chart.add_edge(Edge(dec.id, res1.id, label="Yes"))
        chart.add_edge(Edge(dec.id, res2.id, label="No"))
        
        runner = FlowRunner(chart)
        runner.start()
        runner.step() # At Decide
        
        options = runner.get_options()
        assert len(options) == 2
        
        # Choose "No" (index 1 assuming order, but safer to find by label)
        target_edge = next(e for e in options if e.label == "No")
        idx = options.index(target_edge)
        
        runner.choose_path(idx)
        assert runner.current_node == res2

    def test_runner_invalid_step_at_decision(self):
        chart = FlowChart()
        n1 = chart.add_node(StartNode())
        n2 = chart.add_node(DecisionNode())
        n3 = chart.add_node(EndNode())
        n4 = chart.add_node(EndNode())
        
        chart.add_edge(Edge(n1.id, n2.id))
        chart.add_edge(Edge(n2.id, n3.id))
        chart.add_edge(Edge(n2.id, n4.id))
        
        runner = FlowRunner(chart)
        runner.start()
        runner.step() # At Decision
        
        # Should raise error because multiple paths exist
        with pytest.raises(ValueError):
            runner.step()


class TestFlowRunnerEdgeCases:
    """Edge case and error handling tests for FlowRunner."""
    
    def test_start_without_start_node_raises(self):
        """Test that starting without a StartNode raises an error."""
        chart = FlowChart("No Start")
        chart.add_node(ProcessNode(label="Process"))
        
        runner = FlowRunner(chart)
        
        with pytest.raises(ValueError, match="No StartNode"):
            runner.start()
    
    def test_start_with_explicit_node_id(self):
        """Test starting from a specific node ID."""
        chart = FlowChart("Explicit Start")
        start = chart.add_node(StartNode(node_id="my-start", label="Start"))
        end = chart.add_node(EndNode(label="End"))
        chart.add_edge(Edge(start.id, end.id))
        
        runner = FlowRunner(chart)
        runner.start(start_node_id="my-start")
        
        assert runner.current_node == start
    
    def test_step_without_start_raises(self):
        """Test that stepping without starting raises an error."""
        chart = FlowChart()
        chart.add_node(StartNode())
        
        runner = FlowRunner(chart)
        
        with pytest.raises(RuntimeError, match="not started"):
            runner.step()
    
    def test_step_at_end_node(self):
        """Test that stepping at EndNode does nothing."""
        chart = FlowChart()
        start = chart.add_node(StartNode())
        end = chart.add_node(EndNode())
        chart.add_edge(Edge(start.id, end.id))
        
        runner = FlowRunner(chart)
        runner.start()
        runner.step()  # Now at End
        
        # Stepping at end should not crash
        runner.step()
        assert runner.current_node == end
    
    def test_step_at_dead_end(self):
        """Test stepping from a node with no outgoing edges."""
        chart = FlowChart()
        start = chart.add_node(StartNode())
        proc = chart.add_node(ProcessNode(label="Dead End"))
        chart.add_edge(Edge(start.id, proc.id))
        # No edge from proc to anywhere
        
        runner = FlowRunner(chart)
        runner.start()
        runner.step()  # Now at Dead End
        
        # Stepping should not crash (node has no outgoing edges)
        runner.step()
        assert runner.current_node == proc
    
    def test_choose_path_invalid_index_raises(self):
        """Test that invalid edge index raises IndexError."""
        chart = FlowChart()
        start = chart.add_node(StartNode())
        dec = chart.add_node(DecisionNode())
        a = chart.add_node(EndNode(label="A"))
        b = chart.add_node(EndNode(label="B"))
        
        chart.add_edge(Edge(start.id, dec.id))
        chart.add_edge(Edge(dec.id, a.id))
        chart.add_edge(Edge(dec.id, b.id))
        
        runner = FlowRunner(chart)
        runner.start()
        runner.step()  # At decision
        
        with pytest.raises(IndexError):
            runner.choose_path(99)
        
        with pytest.raises(IndexError):
            runner.choose_path(-1)
    
    def test_get_options_before_start_returns_empty(self):
        """Test that get_options returns empty list before starting."""
        chart = FlowChart()
        chart.add_node(StartNode())
        
        runner = FlowRunner(chart)
        
        assert runner.get_options() == []
    
    def test_history_tracks_visited_nodes(self):
        """Test that history correctly tracks visited nodes."""
        chart = FlowChart()
        start = chart.add_node(StartNode(label="Start"))
        proc = chart.add_node(ProcessNode(label="Process"))
        end = chart.add_node(EndNode(label="End"))
        
        chart.add_edge(Edge(start.id, proc.id))
        chart.add_edge(Edge(proc.id, end.id))
        
        runner = FlowRunner(chart)
        runner.start()
        runner.step()
        runner.step()
        
        assert runner.history == [start.id, proc.id, end.id]
    
    def test_context_is_empty_dict_initially(self):
        """Test that context starts as empty dict."""
        chart = FlowChart()
        chart.add_node(StartNode())
        
        runner = FlowRunner(chart)
        
        assert runner.context == {}
