from typing import Optional
import graphviz
from flowly.core.ir import FlowChart, Node, Edge, StartNode, EndNode, ProcessNode, DecisionNode

class GraphvizExporter:
    """Exports a FlowChart to Graphviz/Dot format or renders it."""

    @staticmethod
    def to_digraph(flowchart: FlowChart) -> graphviz.Digraph:
        """Converts FlowChart to a graphviz.Digraph object."""
        dot = graphviz.Digraph(name=flowchart.name, comment=flowchart.name)
        dot.attr(rankdir='TB')  # Top to Bottom by default

        for node in flowchart.nodes.values():
            # Determine shape based on node type
            shape = "box" # Default
            if isinstance(node, StartNode) or isinstance(node, EndNode):
                shape = "ellipse"
            elif isinstance(node, DecisionNode):
                shape = "diamond"
            
            dot.node(node.id, label=node.label, shape=shape)

        for edge in flowchart.edges:
            label = edge.label if edge.label else ""
            dot.edge(edge.source_id, edge.target_id, label=label)

        return dot

    @staticmethod
    def render(flowchart: FlowChart, filename: str, format: str = 'png', view: bool = False):
        """Renders the flowchart to a file."""
        dot = GraphvizExporter.to_digraph(flowchart)
        dot.render(filename, format=format, view=view)
