"""
Tests for JSON serialization.

IMPORTANT: The serialization format is consumed by the flowplay HTML frontend.
These tests verify that the serialized format contains all fields that flowplay
expects. Changes to serialization MUST maintain compatibility with flowplay.

See flowplay/app.js for how these fields are used:
- nodes[].id, nodes[].type, nodes[].label, nodes[].metadata
- edges[].id, edges[].source, edges[].target, edges[].label
- graph.incomingEdges[nodeId] -> list of edge IDs
- graph.outgoingEdges[nodeId] -> list of edge IDs
"""

import json

import pytest
from flowly.core.ir import (
    DecisionNode,
    Edge,
    EndNode,
    FlowChart,
    ProcessNode,
    StartNode,
)
from flowly.core.serialization import JsonSerializer


class TestJsonRoundtrip:
    """Tests for serialization/deserialization round-trips."""

    def test_basic_roundtrip(self):
        """Basic round-trip preserves chart structure."""
        chart = FlowChart("Test")
        n1 = chart.add_node(StartNode(label="S"))
        n2 = chart.add_node(ProcessNode(label="P", metadata={"foo": "bar"}))
        chart.add_edge(Edge(n1.id, n2.id, label="Go"))

        json_str = JsonSerializer.to_json(chart)
        chart2 = JsonSerializer.from_json(json_str)

        assert chart2.name == chart.name
        assert len(chart2.nodes) == 2
        assert len(chart2.edges) == 1

        # Check node reconstruction
        n2_reconstructed = chart2.get_node(n2.id)
        assert isinstance(n2_reconstructed, ProcessNode)
        assert n2_reconstructed.label == "P"
        assert n2_reconstructed.metadata["foo"] == "bar"

        # Check edges
        edge = chart2.edges[0]
        assert edge.source_id == n1.id
        assert edge.target_id == n2.id

    def test_all_node_types_preserved(self):
        """All node types survive round-trip."""
        chart = FlowChart("All Types")
        start = chart.add_node(StartNode(label="Start"))
        proc = chart.add_node(ProcessNode(label="Process"))
        dec = chart.add_node(DecisionNode(label="Decision"))
        end = chart.add_node(EndNode(label="End"))

        chart.add_edge(Edge(start.id, proc.id))
        chart.add_edge(Edge(proc.id, dec.id))
        chart.add_edge(Edge(dec.id, end.id))

        chart2 = JsonSerializer.from_json(JsonSerializer.to_json(chart))

        assert isinstance(chart2.get_node(start.id), StartNode)
        assert isinstance(chart2.get_node(proc.id), ProcessNode)
        assert isinstance(chart2.get_node(dec.id), DecisionNode)
        assert isinstance(chart2.get_node(end.id), EndNode)

    def test_edge_properties_preserved(self):
        """Edge label, condition, and metadata survive round-trip."""
        chart = FlowChart("Edges")
        a = chart.add_node(ProcessNode(label="A"))
        b = chart.add_node(ProcessNode(label="B"))
        chart.add_edge(
            Edge(a.id, b.id, label="Yes", condition="x > 0", metadata={"priority": 1})
        )

        chart2 = JsonSerializer.from_json(JsonSerializer.to_json(chart))
        edge = chart2.edges[0]

        assert edge.label == "Yes"
        assert edge.condition == "x > 0"
        assert edge.metadata["priority"] == 1


class TestFlowplayFormat:
    """
    Tests that verify the JSON format required by the flowplay HTML frontend.

    The flowplay app.js expects specific fields in the JSON structure.
    These tests act as a contract to ensure serialization changes don't
    break the frontend.
    """

    @pytest.fixture
    def sample_chart(self):
        """Create a chart with multiple nodes and edges for testing."""
        chart = FlowChart("Sample Flow")
        start = chart.add_node(StartNode(node_id="start", label="Begin"))
        proc = chart.add_node(ProcessNode(node_id="proc", label="Do Work"))
        dec = chart.add_node(DecisionNode(node_id="dec", label="Is Done?"))
        end = chart.add_node(EndNode(node_id="end", label="Finish"))

        chart.add_edge(Edge(start.id, proc.id, label="Start"))
        chart.add_edge(Edge(proc.id, dec.id))
        chart.add_edge(Edge(dec.id, end.id, label="Yes"))
        chart.add_edge(Edge(dec.id, proc.id, label="No"))  # Loop back

        return chart

    def test_top_level_structure(self, sample_chart):
        """
        Flowplay expects: name, metadata, nodes, edges, graph

        See app.js loadFlowData() which destructures these fields.
        """
        data = JsonSerializer.to_dict(sample_chart)

        assert "name" in data
        assert "metadata" in data
        assert "nodes" in data
        assert "edges" in data
        assert "graph" in data

    def test_node_structure(self, sample_chart):
        """
        Flowplay expects each node to have: id, type, label, metadata

        - id: Used for lookups and edge references
        - type: Used to determine node shape (StartNode, EndNode, DecisionNode, ProcessNode)
        - label: Displayed text on the node
        - metadata: Additional data like description
        """
        data = JsonSerializer.to_dict(sample_chart)

        for node in data["nodes"]:
            assert "id" in node, "Node must have 'id' for flowplay lookups"
            assert "type" in node, "Node must have 'type' for shape rendering"
            assert "label" in node, "Node must have 'label' for display"
            assert "metadata" in node, "Node must have 'metadata' for description panel"

            # Type must be a valid node type name
            assert node["type"] in [
                "StartNode",
                "EndNode",
                "ProcessNode",
                "DecisionNode",
                "Node",
            ]

    def test_edge_structure(self, sample_chart):
        """
        Flowplay expects each edge to have: id, source, target, label, condition, metadata

        - id: Used for edge lookups in graph.incomingEdges/outgoingEdges
        - source/target: Node IDs for drawing connections
        - label: Text displayed on the edge (e.g., "Yes", "No")
        """
        data = JsonSerializer.to_dict(sample_chart)

        for edge in data["edges"]:
            assert "id" in edge, "Edge must have 'id' for graph lookups"
            assert "source" in edge, "Edge must have 'source' node ID"
            assert "target" in edge, "Edge must have 'target' node ID"
            assert "label" in edge, "Edge must have 'label' (can be null)"
            assert "condition" in edge, "Edge must have 'condition' (can be null)"
            assert "metadata" in edge, "Edge must have 'metadata'"

    def test_edge_ids_are_sequential(self, sample_chart):
        """
        Flowplay uses edge IDs like 'e0', 'e1', 'e2' for consistent lookups.

        The graph.incomingEdges and graph.outgoingEdges reference these IDs.
        """
        data = JsonSerializer.to_dict(sample_chart)

        expected_ids = [f"e{i}" for i in range(len(data["edges"]))]
        actual_ids = [edge["id"] for edge in data["edges"]]

        assert actual_ids == expected_ids

    def test_graph_incoming_edges(self, sample_chart):
        """
        Flowplay uses graph.incomingEdges[nodeId] to find edges pointing TO a node.

        This is used for:
        - Highlighting incoming connections
        - Navigation (going back to previous node)
        - Determining if a node has been reached
        """
        data = JsonSerializer.to_dict(sample_chart)

        assert "incomingEdges" in data["graph"]
        incoming = data["graph"]["incomingEdges"]

        # Build expected incoming edges from edges list
        expected_incoming = {}
        for edge in data["edges"]:
            target = edge["target"]
            if target not in expected_incoming:
                expected_incoming[target] = []
            expected_incoming[target].append(edge["id"])

        # Verify they match
        for node_id, edge_ids in expected_incoming.items():
            assert node_id in incoming, f"Missing incoming edges for {node_id}"
            assert set(incoming[node_id]) == set(edge_ids)

    def test_graph_outgoing_edges(self, sample_chart):
        """
        Flowplay uses graph.outgoingEdges[nodeId] to find edges going FROM a node.

        This is used for:
        - Determining available next steps
        - Rendering decision options
        - Navigation (going to next node)
        """
        data = JsonSerializer.to_dict(sample_chart)

        assert "outgoingEdges" in data["graph"]
        outgoing = data["graph"]["outgoingEdges"]

        # Build expected outgoing edges from edges list
        expected_outgoing = {}
        for edge in data["edges"]:
            source = edge["source"]
            if source not in expected_outgoing:
                expected_outgoing[source] = []
            expected_outgoing[source].append(edge["id"])

        # Verify they match
        for node_id, edge_ids in expected_outgoing.items():
            assert node_id in outgoing, f"Missing outgoing edges for {node_id}"
            assert set(outgoing[node_id]) == set(edge_ids)

    def test_decision_node_has_multiple_outgoing(self, sample_chart):
        """
        Decision nodes typically have multiple outgoing edges (Yes/No branches).

        Flowplay renders these as clickable options for the user.
        """
        data = JsonSerializer.to_dict(sample_chart)
        outgoing = data["graph"]["outgoingEdges"]

        # Decision node should have 2 outgoing edges (Yes and No)
        assert "dec" in outgoing
        assert len(outgoing["dec"]) == 2

    def test_loop_creates_multiple_incoming(self, sample_chart):
        """
        When a node is part of a loop, it has multiple incoming edges.

        Flowplay uses this to show that a node can be reached from multiple paths.
        """
        data = JsonSerializer.to_dict(sample_chart)
        incoming = data["graph"]["incomingEdges"]

        # Process node has incoming from start AND from decision (loop)
        assert "proc" in incoming
        assert len(incoming["proc"]) == 2

    def test_node_ids_match_edge_references(self, sample_chart):
        """
        All edge source/target IDs must reference valid node IDs.

        Flowplay looks up nodes by ID when traversing edges.
        """
        data = JsonSerializer.to_dict(sample_chart)

        node_ids = {node["id"] for node in data["nodes"]}

        for edge in data["edges"]:
            assert (
                edge["source"] in node_ids
            ), f"Edge source '{edge['source']}' not in nodes"
            assert (
                edge["target"] in node_ids
            ), f"Edge target '{edge['target']}' not in nodes"

    def test_metadata_includes_description(self):
        """
        Node metadata.description is shown in flowplay's detail panel.
        """
        chart = FlowChart("Described")
        node = chart.add_node(
            ProcessNode(
                label="Important Step",
                metadata={"description": "This step does important things"},
            )
        )

        data = JsonSerializer.to_dict(chart)
        node_data = data["nodes"][0]

        assert node_data["metadata"]["description"] == "This step does important things"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_chart(self):
        """Empty chart serializes correctly."""
        chart = FlowChart("Empty")
        data = JsonSerializer.to_dict(chart)

        assert data["name"] == "Empty"
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["graph"]["incomingEdges"] == {}
        assert data["graph"]["outgoingEdges"] == {}

    def test_single_node_no_edges(self):
        """Chart with one node and no edges."""
        chart = FlowChart("Single")
        chart.add_node(ProcessNode(label="Alone"))

        data = JsonSerializer.to_dict(chart)

        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 0

    def test_null_metadata_becomes_empty_dict(self):
        """Null metadata should become empty dict, not null."""
        chart = FlowChart("Test")
        node = chart.add_node(ProcessNode(label="No Meta"))

        data = JsonSerializer.to_dict(chart)

        # Metadata should be a dict, not None
        assert data["nodes"][0]["metadata"] == {}

    def test_special_characters_in_labels(self):
        """Labels with special characters serialize correctly."""
        chart = FlowChart("Special <>&\"' Chars")
        chart.add_node(ProcessNode(label='Has <html> & "quotes"'))

        json_str = JsonSerializer.to_json(chart)
        data = json.loads(json_str)

        assert data["name"] == "Special <>&\"' Chars"
        assert data["nodes"][0]["label"] == 'Has <html> & "quotes"'

    def test_unicode_in_labels(self):
        """Unicode characters serialize correctly."""
        chart = FlowChart("Unicode: 日本語")
        chart.add_node(ProcessNode(label="Step: 处理 → 完成 ✓"))

        json_str = JsonSerializer.to_json(chart)
        chart2 = JsonSerializer.from_json(json_str)

        assert chart2.name == "Unicode: 日本語"
        assert list(chart2.nodes.values())[0].label == "Step: 处理 → 完成 ✓"


# Keep original test for backward compatibility
def test_json_roundtrip():
    chart = FlowChart("Test")
    n1 = chart.add_node(StartNode(label="S"))
    n2 = chart.add_node(ProcessNode(label="P", metadata={"foo": "bar"}))
    chart.add_edge(Edge(n1.id, n2.id, label="Go"))

    json_str = JsonSerializer.to_json(chart)

    data = json.loads(json_str)
    assert data["name"] == "Test"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    chart2 = JsonSerializer.from_json(json_str)
    assert chart2.name == chart.name
    assert len(chart2.nodes) == 2

    n2_reconstructed = chart2.get_node(n2.id)
    assert isinstance(n2_reconstructed, ProcessNode)
    assert n2_reconstructed.label == "P"
    assert n2_reconstructed.metadata["foo"] == "bar"

    assert len(chart2.edges) == 1
    edge = chart2.edges[0]
    assert edge.source_id == n1.id
    assert edge.target_id == n2.id


class TestSubFlowNodeSerialization:
    """Tests for SubFlowNode serialization."""

    def test_subflow_node_serialization(self):
        """SubFlowNode includes targetChartId in serialization."""
        from flowly.core.ir import SubFlowNode

        chart = FlowChart("With SubFlow")
        start = chart.add_node(StartNode(label="Start"))
        subflow = chart.add_node(
            SubFlowNode(label="Go to Triage", target_chart_id="triage-chart-123")
        )
        chart.add_edge(Edge(start.id, subflow.id))

        data = JsonSerializer.to_dict(chart)

        # Find the subflow node in serialized data
        subflow_data = [n for n in data["nodes"] if n["type"] == "SubFlowNode"][0]

        assert subflow_data["label"] == "Go to Triage"
        assert subflow_data["targetChartId"] == "triage-chart-123"

    def test_subflow_node_roundtrip(self):
        """SubFlowNode survives round-trip serialization."""
        from flowly.core.ir import SubFlowNode

        chart = FlowChart("Roundtrip SubFlow")
        start = chart.add_node(StartNode(label="Start"))
        subflow = chart.add_node(
            SubFlowNode(
                label="Navigate",
                target_chart_id="target-456",
                metadata={"description": "Go to sub-workflow"},
            )
        )
        chart.add_edge(Edge(start.id, subflow.id))

        json_str = JsonSerializer.to_json(chart)
        chart2 = JsonSerializer.from_json(json_str)

        # Find the reconstructed subflow node
        subflow2 = [n for n in chart2.nodes.values() if isinstance(n, SubFlowNode)][0]

        assert subflow2.label == "Navigate"
        assert subflow2.target_chart_id == "target-456"
        assert subflow2.metadata["description"] == "Go to sub-workflow"

    def test_subflow_without_target_serializes(self):
        """SubFlowNode with no target_chart_id still serializes."""
        from flowly.core.ir import SubFlowNode

        chart = FlowChart("No Target")
        subflow = chart.add_node(SubFlowNode(label="Placeholder"))

        data = JsonSerializer.to_dict(chart)
        subflow_data = data["nodes"][0]

        assert subflow_data["type"] == "SubFlowNode"
        assert subflow_data["targetChartId"] is None


class TestMultiFlowChartSerialization:
    """Tests for MultiFlowChart serialization."""

    def test_multi_chart_basic_serialization(self):
        """MultiFlowChart serializes to proper format."""
        from flowly.core.ir import MultiFlowChart

        multi = MultiFlowChart(name="Multi Test")

        chart1 = FlowChart("Flow 1", chart_id="flow-1")
        chart1.add_node(StartNode(label="Start 1"))

        chart2 = FlowChart("Flow 2", chart_id="flow-2")
        chart2.add_node(StartNode(label="Start 2"))

        multi.add_chart(chart1, is_main=True)
        multi.add_chart(chart2)

        data = JsonSerializer.multi_to_dict(multi)

        assert data["type"] == "MultiFlowChart"
        assert data["name"] == "Multi Test"
        assert data["mainChartId"] == "flow-1"
        assert len(data["charts"]) == 2
        assert "flow-1" in data["charts"]
        assert "flow-2" in data["charts"]

    def test_multi_chart_contains_full_chart_data(self):
        """Each chart in MultiFlowChart has complete serialization."""
        from flowly.core.ir import MultiFlowChart

        multi = MultiFlowChart(name="Full Data")

        chart = FlowChart("Complete", chart_id="complete")
        start = chart.add_node(StartNode(label="Begin"))
        proc = chart.add_node(ProcessNode(label="Process"))
        chart.add_edge(Edge(start.id, proc.id, label="Go"))

        multi.add_chart(chart)

        data = JsonSerializer.multi_to_dict(multi)
        chart_data = data["charts"]["complete"]

        # Chart data should have all standard fields
        assert "name" in chart_data
        assert "nodes" in chart_data
        assert "edges" in chart_data
        assert "graph" in chart_data
        assert chart_data["id"] == "complete"

    def test_multi_chart_roundtrip(self):
        """MultiFlowChart survives round-trip serialization."""
        from flowly.core.ir import MultiFlowChart

        multi = MultiFlowChart(name="Roundtrip Multi")

        main_chart = FlowChart("Main", chart_id="main")
        main_chart.add_node(StartNode(label="Main Start"))

        sub_chart = FlowChart("Sub", chart_id="sub")
        sub_chart.add_node(StartNode(label="Sub Start"))

        multi.add_chart(main_chart, is_main=True)
        multi.add_chart(sub_chart)

        json_str = JsonSerializer.multi_to_json(multi)
        multi2 = JsonSerializer.multi_from_json(json_str)

        assert multi2.name == "Roundtrip Multi"
        assert len(multi2.charts) == 2
        assert multi2.main_chart_id == "main"

        # Verify charts are reconstructed
        main2 = multi2.get_chart("main")
        assert main2 is not None
        assert main2.name == "Main"

        sub2 = multi2.get_chart("sub")
        assert sub2 is not None
        assert sub2.name == "Sub"

    def test_multi_chart_with_subflow_links(self):
        """MultiFlowChart with SubFlowNode cross-references serializes correctly."""
        from flowly.core.ir import MultiFlowChart, SubFlowNode

        multi = MultiFlowChart(name="Linked Charts")

        # Main chart with a SubFlowNode
        main = FlowChart("Main", chart_id="main")
        start = main.add_node(StartNode(label="Start"))
        link = main.add_node(SubFlowNode(label="Go to Sub", target_chart_id="sub"))
        main.add_edge(Edge(start.id, link.id))

        # Sub chart
        sub = FlowChart("Sub", chart_id="sub")
        sub.add_node(StartNode(label="Sub Start"))

        multi.add_chart(main, is_main=True)
        multi.add_chart(sub)

        # Serialize and deserialize
        json_str = JsonSerializer.multi_to_json(multi)
        multi2 = JsonSerializer.multi_from_json(json_str)

        # Verify the SubFlowNode's target is preserved
        main2 = multi2.get_chart("main")
        subflow_nodes = [n for n in main2.nodes.values() if isinstance(n, SubFlowNode)]
        assert len(subflow_nodes) == 1
        assert subflow_nodes[0].target_chart_id == "sub"

    def test_empty_multi_chart(self):
        """Empty MultiFlowChart serializes correctly."""
        from flowly.core.ir import MultiFlowChart

        multi = MultiFlowChart(name="Empty")

        data = JsonSerializer.multi_to_dict(multi)

        assert data["type"] == "MultiFlowChart"
        assert data["name"] == "Empty"
        assert data["mainChartId"] is None
        assert data["charts"] == {}
