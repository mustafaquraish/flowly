import pytest
from flowly.core.ir import FlowChart, StartNode, ProcessNode, DecisionNode, EndNode, Edge
from flowly.engine import FlowRunner

@pytest.fixture
def linear_graph():
    chart = FlowChart("Linear")
    start = chart.add_node(StartNode(label="Start"))
    proc = chart.add_node(ProcessNode(label="Process"))
    end = chart.add_node(EndNode(label="End"))
    
    chart.add_edge(Edge(start.id, proc.id))
    chart.add_edge(Edge(proc.id, end.id))
    return chart, start, proc, end

def test_runner_steps_linear(linear_graph):
    chart, start, proc, end = linear_graph
    runner = FlowRunner(chart)
    
    runner.start()
    assert runner.current_node == start
    
    runner.step()
    assert runner.current_node == proc
    
    runner.step()
    assert runner.current_node == end

def test_runner_decision():
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

def test_runner_invalid_step_at_decision():
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
