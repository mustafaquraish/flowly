import graphviz
import re
from typing import Optional, Union
from flowly.core.ir import FlowChart, MultiFlowChart, StartNode, EndNode, DecisionNode, SubFlowNode


class GraphvizExporter:
    """Exports a FlowChart or MultiFlowChart to Graphviz/Dot format or renders it."""

    # Node type to shape mapping
    # Note: We use boxes with type indicators for decisions rather than diamonds
    # because Graphviz stretches diamonds for long text, making them unsymmetrical.
    _SHAPES = {
        "start_end": "ellipse",
        "process": "box",
        "decision": "box",  # Use box instead of diamond (add indicator in label)
        "subflow": "box",   # Use box instead of component (add indicator in label)
    }
    
    # Node type indicators (used in labels since we use uniform box shapes)
    _INDICATORS = {
        "start": "▶ ",
        "end": "⏹ ",
        "process": "",
        "decision": "◆ ",  # Diamond indicator for decision nodes
        "subflow": "📋 ",
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
        - <U> for underline
        
        Note: <A HREF> is technically supported but causes "Unknown HTML element"
        errors with some Graphviz versions. We use underlined text instead.
        """
        import re
        
        # Use Unicode private use area characters as unique placeholders
        HEADER_B = '\uE000'
        HEADER_E = '\uE001'
        BOLD_B = '\uE002'
        BOLD_E = '\uE003'
        ITALIC_B = '\uE004'
        ITALIC_E = '\uE005'
        UNDERLINE_B = '\uE006'
        UNDERLINE_E = '\uE007'
        
        # Convert markdown links [text](url) -> underlined text
        # Just show the link text underlined (URL would make labels too long)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', f'{UNDERLINE_B}\\1{UNDERLINE_E}', text)
        
        # Escape special HTML characters (after link extraction)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
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
        text = text.replace(UNDERLINE_B, '<U>').replace(UNDERLINE_E, '</U>')
        
        return text

    @staticmethod
    def _add_chart_to_digraph(
        dot: graphviz.Digraph,
        flowchart: FlowChart,
        include_descriptions: bool = True,
        as_subgraph: bool = False,
        subgraph_name: Optional[str] = None,
    ) -> None:
        """
        Add a flowchart's nodes and edges to a Digraph.
        
        Args:
            dot: The Digraph to add to
            flowchart: The flowchart to add
            include_descriptions: If True, include descriptions in labels
            as_subgraph: If True, add as a cluster subgraph
            subgraph_name: Name for the subgraph cluster
        """
        if as_subgraph and subgraph_name:
            # Create a cluster subgraph
            with dot.subgraph(name=f'cluster_{flowchart.id}') as c:
                c.attr(label=subgraph_name, style='dashed', color='#5b5fc7')
                GraphvizExporter._add_nodes_and_edges(
                    c, flowchart, include_descriptions
                )
        else:
            GraphvizExporter._add_nodes_and_edges(
                dot, flowchart, include_descriptions
            )

    @staticmethod
    def _add_nodes_and_edges(
        dot: graphviz.Digraph,
        flowchart: FlowChart,
        include_descriptions: bool = True,
    ) -> None:
        """Add nodes and edges from a flowchart to a digraph."""
        for node in flowchart.nodes.values():
            # Determine shape and indicator based on node type
            if isinstance(node, StartNode):
                shape = GraphvizExporter._SHAPES["start_end"]
                indicator = GraphvizExporter._INDICATORS["start"]
            elif isinstance(node, EndNode):
                shape = GraphvizExporter._SHAPES["start_end"]
                indicator = GraphvizExporter._INDICATORS["end"]
            elif isinstance(node, DecisionNode):
                shape = GraphvizExporter._SHAPES["decision"]
                indicator = GraphvizExporter._INDICATORS["decision"]
            elif isinstance(node, SubFlowNode):
                shape = GraphvizExporter._SHAPES["subflow"]
                indicator = GraphvizExporter._INDICATORS["subflow"]
            else:
                shape = GraphvizExporter._SHAPES["process"]
                indicator = GraphvizExporter._INDICATORS["process"]
            
            # Prepare label with type indicator
            node_label = f"{indicator}{node.label}"
            
            # Use HTML label if description exists and is enabled
            description = node.metadata.get("description") if include_descriptions else None
            if description:
                label = GraphvizExporter._html_label(node_label, description)
            else:
                label = node_label
            
            dot.node(node.id, label=label, shape=shape)

        for edge in flowchart.edges:
            # Skip hidden cross-chart edges
            if edge.metadata.get("hidden") or edge.metadata.get("crossChart"):
                continue
            dot.edge(edge.source_id, edge.target_id, label=edge.label or "")

    @staticmethod
    def to_digraph(
        flowchart: Union[FlowChart, MultiFlowChart], 
        include_descriptions: bool = True
    ) -> graphviz.Digraph:
        """
        Converts FlowChart or MultiFlowChart to a graphviz.Digraph object.
        
        Args:
            flowchart: The flowchart or multi-flowchart to convert
            include_descriptions: If True, include node descriptions in HTML labels
        """
        if isinstance(flowchart, MultiFlowChart):
            dot = graphviz.Digraph(name=flowchart.name, comment=flowchart.name)
            dot.attr(rankdir='TB', compound='true')
            
            # Add main chart first
            main_chart = flowchart.get_main_chart()
            if main_chart:
                GraphvizExporter._add_chart_to_digraph(
                    dot, main_chart, include_descriptions,
                    as_subgraph=True, subgraph_name=main_chart.name
                )
            
            # Add other charts as subgraphs
            for chart_id, chart in flowchart.charts.items():
                if chart_id != flowchart.main_chart_id:
                    GraphvizExporter._add_chart_to_digraph(
                        dot, chart, include_descriptions,
                        as_subgraph=True, subgraph_name=chart.name
                    )
            
            # Cross-chart edges (SubFlowNode -> target chart's start)
            # NOTE: We do NOT render these in static formats (mermaid/graphviz/svg)
            # as they make the output noisy. They are only useful in the interactive
            # HTML viewer where users can navigate between charts.
            # The subflow nodes already have the "component" shape which
            # indicates they link to another chart.
        else:
            dot = graphviz.Digraph(name=flowchart.name, comment=flowchart.name)
            dot.attr(rankdir='TB')
            GraphvizExporter._add_nodes_and_edges(dot, flowchart, include_descriptions)

        return dot

    @staticmethod
    def to_dot(flowchart: Union[FlowChart, MultiFlowChart]) -> str:
        """Returns the DOT source string for the flowchart."""
        return GraphvizExporter.to_digraph(flowchart).source

    @staticmethod
    def render(
        flowchart: Union[FlowChart, MultiFlowChart], 
        filename: str, 
        format: str = 'png', 
        view: bool = False
    ):
        """Renders the flowchart to a file."""
        dot = GraphvizExporter.to_digraph(flowchart)
        dot.render(filename, format=format, view=view)
