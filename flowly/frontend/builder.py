"""Imperative FlowBuilder for manual flowchart construction."""

from typing import Optional

from flowly.core.ir import FlowChart, Node, StartNode, ProcessNode, DecisionNode, EndNode, Edge


class FlowBuilder:
    """
    Imperative API for building flowcharts by manually adding nodes and edges.
    
    Example:
        builder = FlowBuilder("My Flow")
        start = builder.start("Begin")
        proc = builder.action("Do something")
        end = builder.end("Done")
        builder.connect(start, proc)
        builder.connect(proc, end)
        chart = builder.build()
    """
    
    def __init__(self, name: str = "FlowChart"):
        self.flowchart = FlowChart(name)
        self.last_node: Optional[Node] = None

    def start(self, label: str = "Start", node_id: Optional[str] = None, description: Optional[str] = None) -> Node:
        metadata = {"description": description} if description else {}
        node = StartNode(node_id=node_id, label=label, metadata=metadata)
        self.flowchart.add_node(node)
        self.last_node = node
        return node

    def action(self, label: str, node_id: Optional[str] = None, description: Optional[str] = None) -> Node:
        metadata = {"description": description} if description else {}
        node = ProcessNode(node_id=node_id, label=label, metadata=metadata)
        self.flowchart.add_node(node)
        self.last_node = node
        return node

    def decision(self, label: str, node_id: Optional[str] = None, description: Optional[str] = None) -> Node:
        metadata = {"description": description} if description else {}
        node = DecisionNode(node_id=node_id, label=label, metadata=metadata)
        self.flowchart.add_node(node)
        self.last_node = node
        return node

    def end(self, label: str = "End", node_id: Optional[str] = None, description: Optional[str] = None) -> Node:
        metadata = {"description": description} if description else {}
        node = EndNode(node_id=node_id, label=label, metadata=metadata)
        self.flowchart.add_node(node)
        self.last_node = node
        return node

    def connect(self, source: Node, target: Node, label: Optional[str] = None, condition: Optional[str] = None) -> Edge:
        edge = Edge(source.id, target.id, label=label, condition=condition)
        self.flowchart.add_edge(edge)
        return edge

    def build(self) -> FlowChart:
        return self.flowchart

