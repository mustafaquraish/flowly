"""
Intermediate Representation (IR) for flowcharts.

This module defines the core data structures used to represent flowcharts:
- Node types: Node, StartNode, EndNode, ProcessNode, DecisionNode
- Edge: Connections between nodes
- FlowChart: Container for the complete graph
- MultiFlowChart: Container for multiple disjoint flowcharts with cross-links
"""

import uuid
from typing import Any, Dict, List, Optional


class Node:
    """Base class for all nodes in the Flowly graph."""

    def __init__(
        self,
        node_id: Optional[str] = None,
        label: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
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


class SubFlowNode(Node):
    """
    Represents a link to another flowchart within a MultiFlowChart.

    When the user navigates to this node and presses Enter, they will
    be taken to the start node of the target flowchart.
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        label: str = "",
        target_chart_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(node_id, label, metadata)
        self.target_chart_id = target_chart_id  # ID of the target FlowChart


class Edge:
    """Represents a connection between two nodes."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        label: Optional[str] = None,
        condition: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.label = label  # Display text for the edge
        self.condition = (
            condition  # Logic condition for taking this path (for future use/runners)
        )
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<Edge {self.source_id} -> {self.target_id} label='{self.label}'>"


class FlowChart:
    """Represents the entire flowchart graph."""

    def __init__(
        self,
        name: str = "FlowChart",
        chart_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = chart_id if chart_id else str(uuid.uuid4())
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

        # Check for duplicate edges (same source, target, and label)
        for existing_edge in self.edges:
            if (
                existing_edge.source_id == edge.source_id
                and existing_edge.target_id == edge.target_id
                and existing_edge.label == edge.label
            ):
                # Duplicate edge detected - skip adding it
                return existing_edge

        self.edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def get_start_node(self) -> Optional[StartNode]:
        """Get the start node of this flowchart."""
        for node in self.nodes.values():
            if isinstance(node, StartNode):
                return node
        return None


class MultiFlowChart:
    """
    Container for multiple disjoint flowcharts that can be linked together.

    This allows creating complex documentation with multiple related flowcharts
    that can reference each other. For example, a main troubleshooting flow
    that links to sub-flows for specific topics.

    The charts are rendered on the same canvas but in separate areas.
    Users can navigate between charts via SubFlowNode nodes.
    """

    def __init__(
        self, name: str = "MultiFlowChart", metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.charts: Dict[str, FlowChart] = {}  # chart_id -> FlowChart
        self.main_chart_id: Optional[str] = None  # ID of the primary/entry flowchart
        self.metadata = metadata or {}

    def add_chart(self, chart: FlowChart, is_main: bool = False) -> FlowChart:
        """
        Add a flowchart to this multi-flowchart container.

        Args:
            chart: The FlowChart to add
            is_main: If True, this chart will be the main/entry chart

        Returns:
            The added FlowChart
        """
        if chart.id in self.charts:
            raise ValueError(f"Chart with id {chart.id} already exists.")
        self.charts[chart.id] = chart

        if is_main or self.main_chart_id is None:
            self.main_chart_id = chart.id

        return chart

    def get_chart(self, chart_id: str) -> Optional[FlowChart]:
        """Get a flowchart by its ID."""
        return self.charts.get(chart_id)

    def get_main_chart(self) -> Optional[FlowChart]:
        """Get the main/entry flowchart."""
        if self.main_chart_id:
            return self.charts.get(self.main_chart_id)
        return None

    def link_charts(
        self,
        source_chart_id: str,
        source_node_id: str,
        target_chart_id: str,
        label: Optional[str] = None,
    ) -> None:
        """
        Create a link from a node in one chart to another chart.

        This updates the source node to be a SubFlowNode pointing to
        the target chart.

        Args:
            source_chart_id: ID of the chart containing the source node
            source_node_id: ID of the node that will link to the target
            target_chart_id: ID of the chart to link to
            label: Optional label for the link (updates node label if provided)
        """
        source_chart = self.charts.get(source_chart_id)
        if not source_chart:
            raise ValueError(f"Source chart {source_chart_id} not found.")

        if target_chart_id not in self.charts:
            raise ValueError(f"Target chart {target_chart_id} not found.")

        source_node = source_chart.get_node(source_node_id)
        if not source_node:
            raise ValueError(
                f"Source node {source_node_id} not found in chart {source_chart_id}."
            )

        # Convert the source node to a SubFlowNode or update its target
        if isinstance(source_node, SubFlowNode):
            source_node.target_chart_id = target_chart_id
            if label:
                source_node.label = label
        else:
            # Create a new SubFlowNode with the same properties
            subflow_node = SubFlowNode(
                node_id=source_node.id,
                label=label or source_node.label,
                target_chart_id=target_chart_id,
                metadata=source_node.metadata,
            )
            source_chart.nodes[source_node.id] = subflow_node
