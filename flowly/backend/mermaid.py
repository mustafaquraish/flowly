from typing import Dict, Any, Optional
from flowly.core.ir import FlowChart, Node, Edge, StartNode, EndNode, ProcessNode, DecisionNode

class MermaidExporter:
    """Exports a FlowChart to Mermaid.js syntax."""

    @staticmethod
    def _sanitize(text: str) -> str:
        """Sanitizes text for Mermaid."""
        return text.replace('"', '#quot;').replace("(", "#40;").replace(")", "#41;")

    @staticmethod
    def _get_node_shape_start(node_id: str, label: str) -> str:
        return f'{node_id}(["{label}"])'

    @staticmethod
    def _get_node_shape_end(node_id: str, label: str) -> str:
        return f'{node_id}(["{label}"])'

    @staticmethod
    def _get_node_shape_process(node_id: str, label: str) -> str:
        return f'{node_id}["{label}"]'

    @staticmethod
    def _get_node_shape_decision(node_id: str, label: str) -> str:
        return f'{node_id}{{"{label}"}}'

    @staticmethod
    def to_mermaid(flowchart: FlowChart, direction: str = "TD") -> str:
        lines = [f"graph {direction}"]
        
        # Add nodes with appropriate shapes
        for node in flowchart.nodes.values():
            label = MermaidExporter._sanitize(node.label)
            if isinstance(node, StartNode):
                lines.append("    " + MermaidExporter._get_node_shape_start(node.id, label))
            elif isinstance(node, EndNode):
                lines.append("    " + MermaidExporter._get_node_shape_end(node.id, label))
            elif isinstance(node, DecisionNode):
                lines.append("    " + MermaidExporter._get_node_shape_decision(node.id, label))
            else: # ProcessNode or generic
                lines.append("    " + MermaidExporter._get_node_shape_process(node.id, label))

        # Add edges
        for edge in flowchart.edges:
            source = edge.source_id
            target = edge.target_id
            label = edge.label
            
            arrow = "-->"
            if label:
                clean_label = MermaidExporter._sanitize(label)
                lines.append(f"    {source} -- {clean_label} --> {target}")
            else:
                lines.append(f"    {source} --> {target}")

        return "\n".join(lines)
