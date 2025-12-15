"""
Command-line interface for Flowly.

Usage:
    flowly ./examples/demo_dsl.py -o ./build/
    flowly ./examples/demo_dsl.py -o ./build/ --format mermaid
    flowly ./examples/demo_dsl.py -o ./build/ --format graphviz
    flowly ./examples/demo_dsl.py -o ./build/ --format svg
"""

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple

from flowly.frontend.dsl import Flow
from flowly.core.ir import FlowChart
from flowly.backend.html import HtmlExporter
from flowly.backend.mermaid import MermaidExporter
from flowly.backend.graphviz import GraphvizExporter
from flowly.backend.svg import SvgExporter
from flowly.core.serialization import JsonSerializer


def discover_flowcharts(filepath: Path) -> List[Tuple[str, FlowChart]]:
    """
    Load a Python file and discover all Flow decorator instances at module level.
    
    Returns a list of (name, flowchart) tuples.
    """
    # Load the module
    spec = importlib.util.spec_from_file_location("user_module", filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {filepath}")
    
    module = importlib.util.module_from_spec(spec)
    
    # Add the file's directory to sys.path so imports work
    file_dir = str(filepath.parent.resolve())
    if file_dir not in sys.path:
        sys.path.insert(0, file_dir)
    
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"Error executing {filepath}: {e}") from e
    
    # Find all Flow decorator instances (they have a .chart attribute)
    flowcharts = []
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, Flow) and obj.chart is not None:
            flowcharts.append((name, obj.chart))
    
    return flowcharts


def export_flowchart(
    chart: FlowChart,
    output_path: Path,
    format: str
) -> Path:
    """Export a flowchart to the specified format."""
    
    if format == "html":
        content = HtmlExporter.to_html(chart)
        ext = ".html"
    elif format == "mermaid":
        content = MermaidExporter.to_mermaid(chart)
        ext = ".mmd"
    elif format == "graphviz" or format == "dot":
        content = GraphvizExporter.to_dot(chart)
        ext = ".dot"
    elif format == "svg":
        content = SvgExporter.to_svg(chart)
        ext = ".svg"
    elif format == "json":
        content = JsonSerializer.to_json(chart)
        ext = ".json"
    else:
        raise ValueError(f"Unknown format: {format}. Use: html, mermaid, graphviz, svg, json")
    
    # Create output filename
    # Sanitize the chart name for use as filename
    safe_name = chart.name.lower().replace(" ", "_").replace("/", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    
    output_file = output_path / f"{safe_name}{ext}"
    output_file.write_text(content)
    
    return output_file


def main(argv: List[str] = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="flowly",
        description="Export flowcharts from Python files.",
        epilog="Example: flowly ./examples/demo_dsl.py -o ./build/"
    )
    
    parser.add_argument(
        "input",
        type=Path,
        help="Python file containing flowchart definitions"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("."),
        help="Output directory (default: current directory)"
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["html", "mermaid", "graphviz", "dot", "svg", "json"],
        default="html",
        help="Output format (default: html)"
    )
    
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List flowcharts in file without exporting"
    )
    
    parser.add_argument(
        "-n", "--name",
        type=str,
        help="Export only the flowchart with this variable name"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args(argv)
    
    # Validate input file
    if not args.input.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 1
    
    if not args.input.is_file():
        print(f"Error: Not a file: {args.input}", file=sys.stderr)
        return 1
    
    # Discover flowcharts
    try:
        flowcharts = discover_flowcharts(args.input)
    except Exception as e:
        print(f"Error loading file: {e}", file=sys.stderr)
        return 1
    
    if not flowcharts:
        print(f"No flowcharts found in {args.input}", file=sys.stderr)
        return 1
    
    # List mode
    if args.list:
        print(f"Flowcharts in {args.input}:")
        for name, chart in flowcharts:
            print(f"  {name}: \"{chart.name}\" ({len(chart.nodes)} nodes, {len(chart.edges)} edges)")
        return 0
    
    # Filter by name if specified
    if args.name:
        flowcharts = [(n, c) for n, c in flowcharts if n == args.name]
        if not flowcharts:
            print(f"Error: No flowchart named '{args.name}' found", file=sys.stderr)
            return 1
    
    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)
    
    # Export each flowchart
    for name, chart in flowcharts:
        try:
            output_file = export_flowchart(chart, args.output, args.format)
            if args.verbose:
                print(f"Exported '{chart.name}' -> {output_file}")
            else:
                print(f"{output_file}")
        except Exception as e:
            print(f"Error exporting {name}: {e}", file=sys.stderr)
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
