import graphviz
import re
from flowly.core.ir import FlowChart, StartNode, EndNode, DecisionNode


class GraphvizExporter:
    """Exports a FlowChart to Graphviz/Dot format or renders it."""

    # Node type to shape mapping
    _SHAPES = {
        "start_end": "ellipse",
        "process": "box",
        "decision": "diamond",
    }
    
    @staticmethod
    def _markdown_to_html_label(label: str, description: str = None) -> str:
        """
        Convert node label and markdown description to Graphviz HTML-like label.
        
        Graphviz supports HTML-like labels with:
        - <B>bold</B>
        - <I>italic</I>
        - <BR/> line breaks
        - <FONT> tags for styling
        - Tables for layout
        
        Returns an HTML-like label string that Graphviz can render.
        """
        if not description:
            # Just return the label in bold
            return f'<<B>{GraphvizExporter._escape_html(label)}</B>>'
        
        # Start building HTML table for better layout
        parts = []
        parts.append('<')
        parts.append('<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">')
        
        # Add label as header
        parts.append(f'<TR><TD><B>{GraphvizExporter._escape_html(label)}</B></TD></TR>')
        
        # Process description markdown
        desc_html = GraphvizExporter._markdown_to_html(description)
        parts.append(f'<TR><TD><FONT POINT-SIZE="10">{desc_html}</FONT></TD></TR>')
        
        parts.append('</TABLE>')
        parts.append('>')
        
        return ''.join(parts)
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters for Graphviz."""
        return (
            text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )
    
    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """
        Convert markdown to Graphviz HTML-like formatting.
        
        Supports:
        - **bold** -> <B>bold</B>
        - *italic* -> <I>italic</I>
        - `code` -> monospace
        - Line breaks
        """
        # Escape HTML first
        text = GraphvizExporter._escape_html(text)
        
        # Convert line breaks
        text = text.replace('\n', '<BR/>')
        
        # Bold: **text** or __text__
        text = re.sub(r'\*\*([^*]+)\*\*', r'<B>\1</B>', text)
        text = re.sub(r'__([^_]+)__', r'<B>\1</B>', text)
        
        # Italic: *text* or _text_ (do after bold to avoid conflicts)
        text = re.sub(r'\*([^*]+)\*', r'<I>\1</I>', text)
        text = re.sub(r'_([^_]+)_', r'<I>\1</I>', text)
        
        # Code: `text` (use fixed-width font)
        text = re.sub(r'`([^`]+)`', r'<FONT FACE="monospace">\1</FONT>', text)
        
        return text

    @staticmethod
    def to_digraph(flowchart: FlowChart, include_descriptions: bool = True) -> graphviz.Digraph:
        """
        Converts FlowChart to a graphviz.Digraph object.
        
        Args:
            flowchart: The flowchart to convert
            include_descriptions: If True, include node descriptions in HTML labels
        """
        dot = graphviz.Digraph(name=flowchart.name, comment=flowchart.name)
        dot.attr(rankdir='TB')

        for node in flowchart.nodes.values():
            if isinstance(node, (StartNode, EndNode)):
                shape = GraphvizExporter._SHAPES["start_end"]
            elif isinstance(node, DecisionNode):
                shape = GraphvizExporter._SHAPES["decision"]
            else:
                shape = GraphvizExporter._SHAPES["process"]
            
            # Use HTML label if description exists and is enabled
            description = node.metadata.get("description") if include_descriptions else None
            if description:
                label = GraphvizExporter._markdown_to_html_label(node.label, description)
            else:
                label = node.label
            
            dot.node(node.id, label=label, shape=shape)

        for edge in flowchart.edges:
            dot.edge(edge.source_id, edge.target_id, label=edge.label or "")

        return dot

    @staticmethod
    def to_dot(flowchart: FlowChart) -> str:
        """Returns the DOT source string for the flowchart."""
        return GraphvizExporter.to_digraph(flowchart).source

    @staticmethod
    def render(flowchart: FlowChart, filename: str, format: str = 'png', view: bool = False):
        """Renders the flowchart to a file."""
        dot = GraphvizExporter.to_digraph(flowchart)
        dot.render(filename, format=format, view=view)
