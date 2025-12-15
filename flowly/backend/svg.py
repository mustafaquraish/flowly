"""SVG backend for flowcharts using Graphviz.

This backend exports flowcharts to SVG (Scalable Vector Graphics) format,
which can be:
- Embedded in HTML documents
- Opened in web browsers
- Included in documentation
- Edited with vector graphics tools

Requirements:
    Graphviz must be installed on your system:
    - macOS: brew install graphviz
    - Ubuntu/Debian: sudo apt-get install graphviz
    - Windows: Download from https://graphviz.org/download/

Example:
    >>> from flowly import Flow, Node, SvgExporter
    >>> 
    >>> @Flow("My Flow")
    ... def my_flow(flow):
    ...     Node("Step 1")()
    ...     Node("Step 2")()
    >>> 
    >>> svg_string = SvgExporter.to_svg(my_flow.chart)
    >>> with open("output.svg", "w") as f:
    ...     f.write(svg_string)
"""

import re
from flowly.backend.graphviz import GraphvizExporter


__all__ = ["SvgExporter"]


class SvgExporter:
    """Exports a FlowChart to SVG format using Graphviz."""
    
    @staticmethod
    def to_svg(flowchart, include_descriptions: bool = True) -> str:
        """
        Convert flowchart to SVG string using Graphviz.
        
        Args:
            flowchart: The flowchart to convert
            include_descriptions: If True, include node descriptions in labels
            
        Returns:
            SVG string with embedded flowchart
            
        Raises:
            RuntimeError: If Graphviz executable is not available
        """
        try:
            # Use GraphvizExporter to create the Digraph
            digraph = GraphvizExporter.to_digraph(flowchart, include_descriptions=include_descriptions)
            
            # Render to SVG format
            # The pipe() method returns bytes, so decode to string
            svg_bytes = digraph.pipe(format='svg')
            svg_string = svg_bytes.decode('utf-8')
            
            return svg_string
            
        except Exception as e:
            # Check if it's a Graphviz installation issue
            if 'graphviz' in str(e).lower() or 'dot' in str(e).lower():
                raise RuntimeError(
                    "Graphviz executable not found. "
                    "Please install Graphviz: https://graphviz.org/download/"
                ) from e
            raise
