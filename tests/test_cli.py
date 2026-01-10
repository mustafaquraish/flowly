"""
Tests for the CLI module.
"""

import os
import tempfile
from pathlib import Path

import pytest
from flowly.cli import discover_flowcharts, export_flowchart, main
from flowly.core.ir import Edge, EndNode, FlowChart, StartNode


# Check if Graphviz is available for SVG tests
try:
    from flowly.backend.svg import SvgExporter

    test_chart = FlowChart("Test")
    test_chart.add_node(StartNode(label="Test"))
    SvgExporter.to_svg(test_chart)
    GRAPHVIZ_AVAILABLE = True
except (RuntimeError, Exception):
    GRAPHVIZ_AVAILABLE = False


class TestDiscoverFlowcharts:
    """Tests for flowchart discovery from Python files."""

    def test_discover_flow_from_file(self, tmp_path):
        """Test discovering a Flow-decorated function."""
        test_file = tmp_path / "test_flow.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow, Node

step = Node("Do something")

@Flow("Test Flow")
def my_flow(flow):
    step()
"""
        )

        flowcharts = discover_flowcharts(test_file)

        assert len(flowcharts) == 1
        name, chart = flowcharts[0]
        assert name == "my_flow"
        assert chart.name == "Test Flow"

    def test_discover_multiple_flows(self, tmp_path):
        """Test discovering multiple flows from one file."""
        test_file = tmp_path / "multi_flow.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow

@Flow("Flow A")
def flow_a(flow):
    flow.step("A step")

@Flow("Flow B")
def flow_b(flow):
    flow.step("B step")
"""
        )

        flowcharts = discover_flowcharts(test_file)

        assert len(flowcharts) == 2
        names = {name for name, _ in flowcharts}
        assert names == {"flow_a", "flow_b"}

    def test_discover_no_flows(self, tmp_path):
        """Test file with no flows returns empty list."""
        test_file = tmp_path / "no_flow.py"
        test_file.write_text(
            """
x = 1
def not_a_flow():
    pass
"""
        )

        flowcharts = discover_flowcharts(test_file)

        assert flowcharts == []

    def test_discover_invalid_file_raises(self, tmp_path):
        """Test that invalid Python raises an error."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("this is not valid python {{{{")

        with pytest.raises(RuntimeError, match="Error executing"):
            discover_flowcharts(test_file)

    def test_discover_nonexistent_file_raises(self, tmp_path):
        """Test that missing file raises RuntimeError."""
        missing = tmp_path / "does_not_exist.py"

        with pytest.raises(RuntimeError, match="Error executing"):
            discover_flowcharts(missing)

    def test_discover_flow_with_subflows_returns_multichart(self, tmp_path):
        """Test that a flow using @Subflow returns a MultiFlowChart."""
        from flowly.core.ir import MultiFlowChart

        test_file = tmp_path / "subflow_test.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow, Subflow

@Subflow("Helper Flow")
def helper(flow):
    flow.step("Helper action")

@Flow("Main Flow")
def main_flow(flow):
    flow.step("Main action")
    helper()
"""
        )

        flowcharts = discover_flowcharts(test_file)

        # Should only return main_flow (subflow is combined into it)
        assert len(flowcharts) == 1
        name, chart = flowcharts[0]
        assert name == "main_flow"

        # Should be a MultiFlowChart with 2 charts
        assert isinstance(chart, MultiFlowChart)
        assert len(chart.charts) == 2
        assert chart.name == "Main Flow"

    def test_discover_excludes_pure_subflows(self, tmp_path):
        """Test that pure subflows (only used by other flows) are excluded from top-level."""
        test_file = tmp_path / "pure_subflow.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow, Subflow

@Subflow("Sub A")
def sub_a(flow):
    flow.step("A")

@Subflow("Sub B")
def sub_b(flow):
    flow.step("B")

@Flow("Main")
def main(flow):
    sub_a()
    sub_b()
"""
        )

        flowcharts = discover_flowcharts(test_file)

        # Only main should be returned, sub_a and sub_b are combined into it
        assert len(flowcharts) == 1
        name, _ = flowcharts[0]
        assert name == "main"


class TestExportFlowchart:
    """Tests for flowchart export to different formats."""

    @pytest.fixture
    def simple_chart(self):
        """Create a simple test chart."""
        chart = FlowChart("Test Chart")
        start = chart.add_node(StartNode(label="Start"))
        end = chart.add_node(EndNode(label="End"))
        chart.add_edge(Edge(start.id, end.id))
        return chart

    def test_export_html(self, simple_chart, tmp_path):
        """Test HTML export."""
        output = export_flowchart(simple_chart, tmp_path, "html")

        assert output.suffix == ".html"
        assert output.exists()
        content = output.read_text()
        assert "<!DOCTYPE html>" in content

    def test_export_mermaid(self, simple_chart, tmp_path):
        """Test Mermaid export."""
        output = export_flowchart(simple_chart, tmp_path, "mermaid")

        assert output.suffix == ".mmd"
        assert output.exists()
        content = output.read_text()
        assert "graph TD" in content

    def test_export_graphviz(self, simple_chart, tmp_path):
        """Test Graphviz/DOT export."""
        output = export_flowchart(simple_chart, tmp_path, "graphviz")

        assert output.suffix == ".dot"
        assert output.exists()
        content = output.read_text()
        assert "digraph" in content

    def test_export_dot_alias(self, simple_chart, tmp_path):
        """Test 'dot' format alias works."""
        output = export_flowchart(simple_chart, tmp_path, "dot")

        assert output.suffix == ".dot"

    @pytest.mark.skipif(not GRAPHVIZ_AVAILABLE, reason="Graphviz not installed")
    def test_export_svg(self, simple_chart, tmp_path):
        """Test SVG export."""
        output = export_flowchart(simple_chart, tmp_path, "svg")

        assert output.suffix == ".svg"
        assert output.exists()
        content = output.read_text()
        assert "<svg" in content or "<?xml" in content
        assert "</svg>" in content

    def test_export_json(self, simple_chart, tmp_path):
        """Test JSON export."""
        output = export_flowchart(simple_chart, tmp_path, "json")

        assert output.suffix == ".json"
        assert output.exists()
        content = output.read_text()
        assert '"nodes"' in content

    def test_export_unknown_format_raises(self, simple_chart, tmp_path):
        """Test that unknown format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format"):
            export_flowchart(simple_chart, tmp_path, "unknown")

    def test_export_sanitizes_filename(self, tmp_path):
        """Test that special characters are sanitized from filename."""
        chart = FlowChart("My Flow / With <Special> Chars!")
        chart.add_node(StartNode(label="Start"))

        output = export_flowchart(chart, tmp_path, "json")

        # Should not contain special characters
        assert "/" not in output.name
        assert "<" not in output.name


class TestMainCLI:
    """Tests for the main CLI entrypoint."""

    def test_main_missing_file_returns_error(self, tmp_path):
        """Test that missing input file returns error code."""
        result = main(["nonexistent.py"])

        assert result == 1

    def test_main_directory_returns_error(self, tmp_path):
        """Test that passing a directory returns error."""
        result = main([str(tmp_path)])

        assert result == 1

    def test_main_list_mode(self, tmp_path, capsys):
        """Test --list flag lists flowcharts."""
        test_file = tmp_path / "flow.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow

@Flow("Listed Flow")
def my_flow(flow):
    flow.step("Step")
"""
        )

        result = main([str(test_file), "--list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "my_flow" in captured.out
        assert "Listed Flow" in captured.out

    def test_main_export_to_output_dir(self, tmp_path):
        """Test exporting to specified output directory."""
        test_file = tmp_path / "flow.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow

@Flow("Export Test")
def my_flow(flow):
    flow.step("Step")
"""
        )
        output_dir = tmp_path / "output"

        result = main([str(test_file), "-o", str(output_dir), "-f", "json"])

        assert result == 0
        assert output_dir.exists()
        assert any(output_dir.glob("*.json"))

    def test_main_filter_by_name(self, tmp_path):
        """Test --name flag filters to specific flowchart."""
        test_file = tmp_path / "flows.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow

@Flow("Flow A")
def flow_a(flow):
    flow.step("A")

@Flow("Flow B")
def flow_b(flow):
    flow.step("B")
"""
        )
        output_dir = tmp_path / "output"

        result = main(
            [str(test_file), "-o", str(output_dir), "-n", "flow_a", "-f", "json"]
        )

        assert result == 0
        # Should only have one file
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) == 1
        assert (
            "flow_a" in json_files[0].read_text()
            or "Flow A" in json_files[0].read_text()
        )

    def test_main_name_not_found_returns_error(self, tmp_path, capsys):
        """Test --name with non-existent name returns error."""
        test_file = tmp_path / "flow.py"
        test_file.write_text(
            """
from flowly.frontend.dsl import Flow

@Flow("My Flow")
def my_flow(flow):
    flow.step("Step")
"""
        )

        result = main([str(test_file), "-n", "nonexistent"])

        assert result == 1
        captured = capsys.readouterr()
        assert "nonexistent" in captured.err

    def test_main_no_flows_returns_error(self, tmp_path, capsys):
        """Test file with no flows returns error."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("x = 1")

        result = main([str(test_file)])

        assert result == 1
        captured = capsys.readouterr()
        assert "No flowcharts found" in captured.err
