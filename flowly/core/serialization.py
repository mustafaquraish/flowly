import json
from typing import Dict, Any, Type
# We might add yaml support later if requested, keeping it simple with JSON first but structurally ready.
# To support YAML without extra deps, we'd need PyYAML, but standard lib only has json.
# For now, let's implement JSON fully and structure for extensibility.

from flowly.core.ir import FlowChart, Node, Edge, StartNode, EndNode, ProcessNode, DecisionNode

NODE_TYPE_MAP: Dict[str, Type[Node]] = {
    "Node": Node,
    "StartNode": StartNode,
    "EndNode": EndNode,
    "ProcessNode": ProcessNode,
    "DecisionNode": DecisionNode,
}

class JsonSerializer:
    @staticmethod
    def to_dict(flowchart: FlowChart) -> Dict[str, Any]:
        nodes_data = []
        for node in flowchart.nodes.values():
            nodes_data.append({
                "id": node.id,
                "type": node.__class__.__name__,
                "label": node.label,
                "metadata": node.metadata
            })
            
        edges_data = []
        # Build edge lookup maps for graph navigation
        incoming_edges: Dict[str, list] = {}
        outgoing_edges: Dict[str, list] = {}
        
        for idx, edge in enumerate(flowchart.edges):
            edge_id = f"e{idx}"
            edges_data.append({
                "id": edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "label": edge.label,
                "condition": edge.condition,
                "metadata": edge.metadata
            })
            
            # Track incoming edges per node
            if edge.target_id not in incoming_edges:
                incoming_edges[edge.target_id] = []
            incoming_edges[edge.target_id].append(edge_id)
            
            # Track outgoing edges per node
            if edge.source_id not in outgoing_edges:
                outgoing_edges[edge.source_id] = []
            outgoing_edges[edge.source_id].append(edge_id)
            
        return {
            "name": flowchart.name,
            "metadata": flowchart.metadata,
            "nodes": nodes_data,
            "edges": edges_data,
            "graph": {
                "incomingEdges": incoming_edges,
                "outgoingEdges": outgoing_edges
            }
        }

    @staticmethod
    def to_json(flowchart: FlowChart, indent: int = 2) -> str:
        return json.dumps(JsonSerializer.to_dict(flowchart), indent=indent)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> FlowChart:
        chart = FlowChart(name=data.get("name", "LoadedFlowChart"), metadata=data.get("metadata"))
        
        # Reconstruct nodes
        for node_data in data.get("nodes", []):
            type_name = node_data.get("type", "Node")
            cls = NODE_TYPE_MAP.get(type_name, Node)
            # Instantiate
            node = cls(
                node_id=node_data.get("id"),
                label=node_data.get("label", ""),
                metadata=node_data.get("metadata")
            )
            chart.add_node(node)
            
        # Reconstruct edges
        for edge_data in data.get("edges", []):
            edge = Edge(
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                label=edge_data.get("label"),
                condition=edge_data.get("condition"),
                metadata=edge_data.get("metadata")
            )
            chart.add_edge(edge)
            
        return chart

    @staticmethod
    def from_json(json_str: str) -> FlowChart:
        data = json.loads(json_str)
        return JsonSerializer.from_dict(data)
