import uuid
from typing import Dict, List, Optional, Any, Union

class Node:
    """Base class for all nodes in the Flowly graph."""
    def __init__(self, node_id: Optional[str] = None, label: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.id = node_id if node_id else str(uuid.uuid4())
        self.label = label
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id} label='{self.label}'>"

class StartNode(Node):
    """Represents the entry point of the flow."""
    pass

class EndNode(Node):
    """Represents a termination point of the flow."""
    pass

class ProcessNode(Node):
    """Represents an action or process step."""
    pass

class DecisionNode(Node):
    """Represents a branching point in the flow."""
    pass

class Edge:
    """Represents a connection between two nodes."""
    def __init__(self, source_id: str, target_id: str, label: Optional[str] = None, condition: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.source_id = source_id
        self.target_id = target_id
        self.label = label  # Display text for the edge
        self.condition = condition  # Logic condition for taking this path (for future use/runners)
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<Edge {self.source_id} -> {self.target_id} label='{self.label}'>"

class FlowChart:
    """Represents the entire flowchart graph."""
    def __init__(self, name: str = "FlowChart", metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.metadata = metadata or {}

    def add_node(self, node: Node) -> Node:
        if node.id in self.nodes:
            raise ValueError(f"Node with id {node.id} already exists.")
        self.nodes[node.id] = node
        return node

    def add_edge(self, edge: Edge) -> Edge:
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} does not exist.")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} does not exist.")
        self.edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)
