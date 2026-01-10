import pytest
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


def test_node_creation():
    node = Node(label="Test Node")
    assert node.label == "Test Node"
    assert node.id is not None
    assert isinstance(node.metadata, dict)


def test_graph_add_node():
    chart = FlowChart("Test Chart")
    node = StartNode(label="Start")
    chart.add_node(node)

    assert node.id in chart.nodes
    assert chart.get_node(node.id) == node


def test_graph_add_edge():
    chart = FlowChart()
    n1 = chart.add_node(StartNode(label="A"))
    n2 = chart.add_node(EndNode(label="B"))

    edge = Edge(n1.id, n2.id, label="Go")
    chart.add_edge(edge)

    assert len(chart.edges) == 1
    assert chart.edges[0].source_id == n1.id
    assert chart.edges[0].target_id == n2.id


def test_add_duplicate_node_raises_error():
    chart = FlowChart()
    node = Node(node_id="123")
    chart.add_node(node)

    with pytest.raises(ValueError):
        chart.add_node(Node(node_id="123"))


def test_add_edge_missing_nodes_raises_error():
    chart = FlowChart()
    n1 = chart.add_node(Node())

    with pytest.raises(ValueError):
        chart.add_edge(Edge(n1.id, "missing_id"))


def test_duplicate_edges_are_prevented():
    """Test that duplicate edges (same source, target, label) are not added."""
    chart = FlowChart()
    n1 = chart.add_node(StartNode(label="A"))
    n2 = chart.add_node(EndNode(label="B"))

    # Add first edge
    edge1 = Edge(n1.id, n2.id, label="Go")
    chart.add_edge(edge1)
    assert len(chart.edges) == 1

    # Try to add duplicate - should not increase edge count
    edge2 = Edge(n1.id, n2.id, label="Go")
    returned_edge = chart.add_edge(edge2)
    assert len(chart.edges) == 1
    assert returned_edge == edge1  # Returns existing edge


def test_different_labeled_edges_are_allowed():
    """Test that edges with different labels between same nodes are allowed."""
    chart = FlowChart()
    n1 = chart.add_node(DecisionNode(label="Check"))
    n2 = chart.add_node(ProcessNode(label="Action"))

    # Add edges with different labels
    edge1 = Edge(n1.id, n2.id, label="Yes")
    edge2 = Edge(n1.id, n2.id, label="No")
    chart.add_edge(edge1)
    chart.add_edge(edge2)

    assert len(chart.edges) == 2
    labels = [e.label for e in chart.edges]
    assert "Yes" in labels
    assert "No" in labels


def test_unlabeled_duplicate_edges_are_prevented():
    """Test that duplicate edges without labels are prevented."""
    chart = FlowChart()
    n1 = chart.add_node(ProcessNode(label="A"))
    n2 = chart.add_node(ProcessNode(label="B"))

    # Add edges without labels
    edge1 = Edge(n1.id, n2.id)
    edge2 = Edge(n1.id, n2.id)
    chart.add_edge(edge1)
    chart.add_edge(edge2)

    assert len(chart.edges) == 1


class TestSubFlowNode:
    """Test SubFlowNode - a node that links to another flowchart."""

    def test_subflow_node_creation(self):
        """Test creating a SubFlowNode."""
        node = SubFlowNode(label="Go to Triage", target_chart_id="triage-chart-id")
        assert node.label == "Go to Triage"
        assert node.target_chart_id == "triage-chart-id"
        assert node.id is not None

    def test_subflow_node_without_target(self):
        """Test creating a SubFlowNode without initial target."""
        node = SubFlowNode(label="Placeholder")
        assert node.label == "Placeholder"
        assert node.target_chart_id is None

    def test_subflow_node_in_chart(self):
        """Test adding a SubFlowNode to a FlowChart."""
        chart = FlowChart("Main Flow")
        start = chart.add_node(StartNode(label="Start"))
        subflow = chart.add_node(
            SubFlowNode(label="Go to Sub", target_chart_id="sub-1")
        )
        chart.add_edge(Edge(start.id, subflow.id))

        assert len(chart.nodes) == 2
        assert isinstance(chart.get_node(subflow.id), SubFlowNode)


class TestMultiFlowChart:
    """Test MultiFlowChart - container for multiple disjoint flowcharts."""

    def test_multi_flowchart_creation(self):
        """Test creating an empty MultiFlowChart."""
        multi = MultiFlowChart(name="My Multi Flow")
        assert multi.name == "My Multi Flow"
        assert len(multi.charts) == 0
        assert multi.main_chart_id is None

    def test_add_single_chart(self):
        """Test adding a single chart (becomes main by default)."""
        multi = MultiFlowChart()
        chart = FlowChart("Flow 1", chart_id="flow-1")

        multi.add_chart(chart)

        assert len(multi.charts) == 1
        assert multi.main_chart_id == "flow-1"
        assert multi.get_chart("flow-1") == chart
        assert multi.get_main_chart() == chart

    def test_add_multiple_charts(self):
        """Test adding multiple charts."""
        multi = MultiFlowChart()
        chart1 = FlowChart("Main Flow", chart_id="main")
        chart2 = FlowChart("Sub Flow", chart_id="sub")

        multi.add_chart(chart1, is_main=True)
        multi.add_chart(chart2)

        assert len(multi.charts) == 2
        assert multi.main_chart_id == "main"
        assert multi.get_main_chart() == chart1

    def test_explicit_main_chart(self):
        """Test explicitly setting a chart as main."""
        multi = MultiFlowChart()
        chart1 = FlowChart("Flow 1", chart_id="f1")
        chart2 = FlowChart("Flow 2", chart_id="f2")

        multi.add_chart(chart1)  # Would become main by default
        multi.add_chart(chart2, is_main=True)  # Explicitly make this main

        assert multi.main_chart_id == "f2"

    def test_duplicate_chart_id_raises_error(self):
        """Test that adding a chart with duplicate ID raises error."""
        multi = MultiFlowChart()
        chart1 = FlowChart("Flow 1", chart_id="same-id")
        chart2 = FlowChart("Flow 2", chart_id="same-id")

        multi.add_chart(chart1)

        with pytest.raises(ValueError, match="already exists"):
            multi.add_chart(chart2)

    def test_link_charts(self):
        """Test linking a node in one chart to another chart."""
        multi = MultiFlowChart()

        # Create main chart with a process node
        main = FlowChart("Main", chart_id="main")
        start = main.add_node(StartNode(label="Start"))
        process = main.add_node(ProcessNode(label="Go to Triage"))
        main.add_edge(Edge(start.id, process.id))

        # Create sub chart
        sub = FlowChart("Triage", chart_id="triage")
        sub_start = sub.add_node(StartNode(label="Triage Start"))

        multi.add_chart(main, is_main=True)
        multi.add_chart(sub)

        # Link the process node to the sub chart
        multi.link_charts("main", process.id, "triage")

        # The process node should now be a SubFlowNode
        linked_node = main.get_node(process.id)
        assert isinstance(linked_node, SubFlowNode)
        assert linked_node.target_chart_id == "triage"

    def test_link_charts_missing_source_chart_raises(self):
        """Test linking with missing source chart raises error."""
        multi = MultiFlowChart()
        chart = FlowChart("Flow", chart_id="f1")
        multi.add_chart(chart)

        with pytest.raises(ValueError, match="Source chart"):
            multi.link_charts("missing", "node-id", "f1")

    def test_link_charts_missing_target_chart_raises(self):
        """Test linking with missing target chart raises error."""
        multi = MultiFlowChart()
        chart = FlowChart("Flow", chart_id="f1")
        node = chart.add_node(ProcessNode(label="Test"))
        multi.add_chart(chart)

        with pytest.raises(ValueError, match="Target chart"):
            multi.link_charts("f1", node.id, "missing")

    def test_link_charts_missing_node_raises(self):
        """Test linking with missing node raises error."""
        multi = MultiFlowChart()
        chart1 = FlowChart("Flow 1", chart_id="f1")
        chart2 = FlowChart("Flow 2", chart_id="f2")
        multi.add_chart(chart1)
        multi.add_chart(chart2)

        with pytest.raises(ValueError, match="Source node"):
            multi.link_charts("f1", "missing-node", "f2")


class TestFlowChartGetStartNode:
    """Test FlowChart.get_start_node() helper."""

    def test_get_start_node_exists(self):
        """Test getting start node when it exists."""
        chart = FlowChart("Test")
        start = chart.add_node(StartNode(label="Begin"))
        chart.add_node(ProcessNode(label="Middle"))
        chart.add_node(EndNode(label="End"))

        assert chart.get_start_node() == start

    def test_get_start_node_not_exists(self):
        """Test getting start node when none exists."""
        chart = FlowChart("Test")
        chart.add_node(ProcessNode(label="Middle"))

        assert chart.get_start_node() is None
