"""
JSON serialization for FlowChart and MultiFlowChart objects.

The serialized format is designed to support both round-trip deserialization
and direct consumption by the flowplay HTML frontend.
"""

import json
from typing import Any, Dict, Type

from flowly.core.ir import (
    DecisionNode,
    Edge,
    EndNode,
    FlowChart,
    MultiFlowChart,
    Node,
    ProcessNode,
    StartNode,
    SubFlowNode,
)

NODE_TYPE_MAP: Dict[str, Type[Node]] = {
    "Node": Node,
    "StartNode": StartNode,
    "EndNode": EndNode,
    "ProcessNode": ProcessNode,
    "DecisionNode": DecisionNode,
    "SubFlowNode": SubFlowNode,
}


class JsonSerializer:
    """
    Serializes and deserializes FlowChart objects to/from JSON.

    The serialized format includes a 'graph' field with precomputed edge lookups
    (incomingEdges, outgoingEdges) that are used by the flowplay HTML frontend
    for efficient graph navigation. These are NOT used during deserialization
    since they can be recomputed from the edges list.
    """

    @staticmethod
    def to_dict(flowchart: FlowChart) -> Dict[str, Any]:
        nodes_data = []
        for node in flowchart.nodes.values():
            node_data = {
                "id": node.id,
                "type": node.__class__.__name__,
                "label": node.label,
                "metadata": node.metadata,
            }
            # Add SubFlowNode-specific fields
            if isinstance(node, SubFlowNode):
                node_data["targetChartId"] = node.target_chart_id
            nodes_data.append(node_data)

        edges_data = []
        # Build edge lookup maps for graph navigation
        incoming_edges: Dict[str, list] = {}
        outgoing_edges: Dict[str, list] = {}

        for idx, edge in enumerate(flowchart.edges):
            edge_id = f"e{idx}"
            edges_data.append(
                {
                    "id": edge_id,
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "label": edge.label,
                    "condition": edge.condition,
                    "metadata": edge.metadata,
                }
            )

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
            # Precomputed edge lookups for the flowplay HTML frontend.
            # Maps node IDs to lists of edge IDs for efficient traversal.
            "graph": {"incomingEdges": incoming_edges, "outgoingEdges": outgoing_edges},
        }

    @staticmethod
    def to_json(flowchart: FlowChart, indent: int = 2) -> str:
        return json.dumps(JsonSerializer.to_dict(flowchart), indent=indent)

    @staticmethod
    def from_dict(data: Dict[str, Any], skip_cross_chart_edges: bool = False) -> FlowChart:
        chart = FlowChart(
            name=data.get("name", "LoadedFlowChart"), metadata=data.get("metadata")
        )

        # Reconstruct nodes
        node_ids = set()
        for node_data in data.get("nodes", []):
            type_name = node_data.get("type", "Node")
            cls = NODE_TYPE_MAP.get(type_name, Node)

            # Handle SubFlowNode specially due to extra field
            if cls == SubFlowNode:
                node = SubFlowNode(
                    node_id=node_data.get("id"),
                    label=node_data.get("label", ""),
                    target_chart_id=node_data.get("targetChartId"),
                    metadata=node_data.get("metadata"),
                )
            else:
                node = cls(
                    node_id=node_data.get("id"),
                    label=node_data.get("label", ""),
                    metadata=node_data.get("metadata"),
                )
            chart.add_node(node)
            node_ids.add(node.id)

        # Reconstruct edges
        for edge_data in data.get("edges", []):
            # Skip cross-chart edges when deserializing MultiFlowChart components
            # These edges reference nodes in other charts and are only used for
            # frontend navigation, not for round-trip serialization
            if skip_cross_chart_edges:
                metadata = edge_data.get("metadata") or {}
                if metadata.get("crossChart"):
                    continue
                # Also skip edges that reference nodes not in this chart
                if edge_data["source"] not in node_ids or edge_data["target"] not in node_ids:
                    continue
            
            edge = Edge(
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                label=edge_data.get("label"),
                condition=edge_data.get("condition"),
                metadata=edge_data.get("metadata"),
            )
            chart.add_edge(edge)

        return chart

    @staticmethod
    def from_json(json_str: str) -> FlowChart:
        data = json.loads(json_str)
        return JsonSerializer.from_dict(data)

    @staticmethod
    def multi_to_dict(multi_chart: MultiFlowChart) -> Dict[str, Any]:
        """
        Serialize a MultiFlowChart to a dictionary.

        The format includes all charts and identifies the main chart.
        Each chart is serialized with its full node/edge data.

        Cross-chart navigation is handled by adding edges from SubFlowNodes
        to the start node of their target charts. This way the UI doesn't
        need special SubFlowNode handling - it just renders nodes and edges.

        IMPORTANT: Edge IDs are made globally unique by prefixing with chart index
        to avoid collisions when merging charts in the frontend.
        """
        # First, build a map of chart_id -> start_node_id
        chart_start_nodes: Dict[str, str] = {}
        for chart_id, chart in multi_chart.charts.items():
            start_node = chart.get_start_node()
            if start_node:
                chart_start_nodes[chart_id] = start_node.id

        charts_data = {}
        for chart_idx, (chart_id, chart) in enumerate(multi_chart.charts.items()):
            chart_dict = JsonSerializer.to_dict(chart)
            chart_dict["id"] = chart_id

            # Make edge IDs globally unique by prefixing with chart index
            # This prevents collisions when merging charts in the frontend
            edge_id_prefix = f"c{chart_idx}_"
            edge_id_map: Dict[str, str] = {}  # old_id -> new_id

            for edge_data in chart_dict["edges"]:
                old_id = edge_data["id"]
                new_id = edge_id_prefix + old_id
                edge_id_map[old_id] = new_id
                edge_data["id"] = new_id

            # Update graph lookup maps with new edge IDs
            new_incoming: Dict[str, list] = {}
            for node_id, edge_ids in chart_dict["graph"]["incomingEdges"].items():
                new_incoming[node_id] = [edge_id_map.get(eid, eid) for eid in edge_ids]
            chart_dict["graph"]["incomingEdges"] = new_incoming

            new_outgoing: Dict[str, list] = {}
            for node_id, edge_ids in chart_dict["graph"]["outgoingEdges"].items():
                new_outgoing[node_id] = [edge_id_map.get(eid, eid) for eid in edge_ids]
            chart_dict["graph"]["outgoingEdges"] = new_outgoing

            # Find SubFlowNodes and add cross-chart edges to target chart's start node
            cross_edge_idx = 0
            for node_data in chart_dict["nodes"]:
                if node_data.get("type") == "SubFlowNode":
                    target_chart_id = node_data.get("targetChartId")
                    if target_chart_id and target_chart_id in chart_start_nodes:
                        target_start_id = chart_start_nodes[target_chart_id]
                        target_chart = multi_chart.charts.get(target_chart_id)
                        target_name = target_chart.name if target_chart else "Subflow"

                        # Create cross-chart edge (hidden - not rendered, just for navigation)
                        # Use unique prefix including chart index and "cross" marker
                        edge_id = f"c{chart_idx}_cross{cross_edge_idx}"
                        cross_edge = {
                            "id": edge_id,
                            "source": node_data["id"],
                            "target": target_start_id,
                            "label": f"Go to: {target_name}",
                            "condition": None,
                            "metadata": {"crossChart": True, "hidden": True},
                        }
                        chart_dict["edges"].append(cross_edge)

                        # Update graph lookups
                        source_id = node_data["id"]
                        if source_id not in chart_dict["graph"]["outgoingEdges"]:
                            chart_dict["graph"]["outgoingEdges"][source_id] = []
                        # Insert at beginning so subflow link appears first
                        chart_dict["graph"]["outgoingEdges"][source_id].insert(
                            0, edge_id
                        )

                        if target_start_id not in chart_dict["graph"]["incomingEdges"]:
                            chart_dict["graph"]["incomingEdges"][target_start_id] = []
                        chart_dict["graph"]["incomingEdges"][target_start_id].append(
                            edge_id
                        )

                        cross_edge_idx += 1

            charts_data[chart_id] = chart_dict

        return {
            "type": "MultiFlowChart",
            "name": multi_chart.name,
            "metadata": multi_chart.metadata,
            "mainChartId": multi_chart.main_chart_id,
            "charts": charts_data,
        }

    @staticmethod
    def multi_to_json(multi_chart: MultiFlowChart, indent: int = 2) -> str:
        """Serialize a MultiFlowChart to JSON string."""
        return json.dumps(JsonSerializer.multi_to_dict(multi_chart), indent=indent)

    @staticmethod
    def multi_from_dict(data: Dict[str, Any]) -> MultiFlowChart:
        """
        Deserialize a MultiFlowChart from a dictionary.
        """
        multi_chart = MultiFlowChart(
            name=data.get("name", "LoadedMultiFlowChart"), metadata=data.get("metadata")
        )

        main_chart_id = data.get("mainChartId")

        # Reconstruct each chart
        for chart_id, chart_data in data.get("charts", {}).items():
            # Skip cross-chart edges as they reference nodes in other charts
            chart = JsonSerializer.from_dict(chart_data, skip_cross_chart_edges=True)
            # Preserve the original chart ID
            chart.id = chart_id
            is_main = chart_id == main_chart_id
            multi_chart.add_chart(chart, is_main=is_main)

        return multi_chart

    @staticmethod
    def multi_from_json(json_str: str) -> MultiFlowChart:
        """Deserialize a MultiFlowChart from JSON string."""
        data = json.loads(json_str)
        return JsonSerializer.multi_from_dict(data)
