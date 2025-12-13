from flowly.frontend import FlowBuilder
from flowly.core.ir import StartNode, ProcessNode, DecisionNode

def test_builder_chain():
    builder = FlowBuilder("Builder Test")
    start = builder.start("Beginning")
    process = builder.action("Do Work")
    builder.connect(start, process)
    
    chart = builder.build()
    
    assert len(chart.nodes) == 2
    assert len(chart.edges) == 1
    
    assert isinstance(chart.get_node(start.id), StartNode)
    assert isinstance(chart.get_node(process.id), ProcessNode)

def test_builder_complex_flow():
    b = FlowBuilder()
    start = b.start("S")
    dec = b.decision("D")
    b.connect(start, dec)
    
    y = b.action("Yes")
    n = b.action("No")
    
    b.connect(dec, y, label="y")
    b.connect(dec, n, label="n")
    
    chart = b.build()
    assert len(chart.nodes) == 4
    assert len(chart.edges) == 3
