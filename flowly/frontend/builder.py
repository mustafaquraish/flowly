from typing import Optional, Dict, Any
from flowly.core.ir import FlowChart, Node, StartNode, ProcessNode, DecisionNode, EndNode, Edge

class FlowBuilder:
    def __init__(self, name: str = "FlowChart"):
        self.flowchart = FlowChart(name)
        # Keep track of last added node for simple linear chaining if we want to add convenience methods later
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

