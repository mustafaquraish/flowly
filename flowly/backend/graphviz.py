import graphviz
import re
from typing import Optional
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
    def _html_label(label: str, description: Optional[str] = None) -> str:
        """Generate HTML-like label for a node, optionally including description."""
        if description:
            desc_html = GraphvizExporter._markdown_to_html(description)
            return (
                f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="4" CELLPADDING="8">'
                f'<TR><TD ALIGN="LEFT"><B>{label}</B></TD></TR>'
                f'<TR><TD ALIGN="LEFT" BALIGN="LEFT"><FONT POINT-SIZE="10">{desc_html}</FONT></TD></TR>'
                f'</TABLE>>'
            )
        else:
            return f'<<B>{label}</B>>'
    
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
        Convert markdown to Graphviz HTML-like labels.
        
        Graphviz supports a limited subset of HTML in labels:
        - <B> for bold
        - <I> for italic
        - <BR/> for line breaks
        - <FONT> for styling
        """
        import re
        
        # Escape special HTML characters first (before adding our own HTML tags)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Use Unicode private use area characters as unique placeholders
        HEADER_B = '\uE000'
        HEADER_E = '\uE001'
        BOLD_B = '\uE002'
        BOLD_E = '\uE003'
        ITALIC_B = '\uE004'
        ITALIC_E = '\uE005'
        
        # Convert markdown headers (## Header -> <B>Header</B>)
        text = re.sub(r'^#{1,6}\s+(.+)$', f'{HEADER_B}\\1{HEADER_E}', text, flags=re.MULTILINE)
        
        # Replace markdown line breaks
        text = text.replace('\n', '<BR/>')
        
        # Convert code blocks/inline code to italic
        text = re.sub(r'`([^`]+)`', f'{ITALIC_B}\\1{ITALIC_E}', text)
        
        # Bold: **text** or __text__
        text = re.sub(r'\*\*([^*]+)\*\*', f'{BOLD_B}\\1{BOLD_E}', text)
        text = re.sub(r'__([^_]+)__', f'{BOLD_B}\\1{BOLD_E}', text)
        
        # Italic: *text* or _text_
        text = re.sub(r'\*([^*]+)\*', f'{ITALIC_B}\\1{ITALIC_E}', text)
        text = re.sub(r'_([^_]+)_', f'{ITALIC_B}\\1{ITALIC_E}', text)
        
        # Now replace placeholders with actual HTML tags
        text = text.replace(HEADER_B, '<B>').replace(HEADER_E, '</B>')
        text = text.replace(BOLD_B, '<B>').replace(BOLD_E, '</B>')
        text = text.replace(ITALIC_B, '<I>').replace(ITALIC_E, '</I>')
        
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
                label = GraphvizExporter._html_label(node.label, description)
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
