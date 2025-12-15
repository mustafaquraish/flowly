"""
Flowly - A Python library for creating and visualizing flowcharts.

Main APIs:
- FlowBuilder: Imperative API for manual graph construction
- Flow: Decorator-based DSL using Python control flow syntax
- FlowTracer: Runtime tracer that captures executed paths

Backends:
- HtmlExporter: Interactive HTML player
- MermaidExporter: Mermaid.js diagram syntax
- GraphvizExporter: Graphviz DOT format
- SvgExporter: SVG format (requires Graphviz)
"""

from flowly.core.ir import FlowChart, Node, Edge, StartNode, EndNode, ProcessNode, DecisionNode
from flowly.core.serialization import JsonSerializer
from flowly.frontend import FlowBuilder, Flow, FlowTracer
from flowly.backend import HtmlExporter, MermaidExporter, GraphvizExporter, SvgExporter

__all__ = [
    # Core IR
    "FlowChart",
    "Node", 
    "Edge",
    "StartNode",
    "EndNode", 
    "ProcessNode",
    "DecisionNode",
    # Serialization
    "JsonSerializer",
    # Frontends
    "FlowBuilder",
    "Flow",
    "FlowTracer",
    # Backends
    "HtmlExporter",
    "MermaidExporter", 
    "GraphvizExporter",
    "SvgExporter",
]