from typing import Union
from flowly.core.ir import FlowChart, MultiFlowChart, StartNode, EndNode, DecisionNode, SubFlowNode


class MermaidExporter:
    """Exports a FlowChart or MultiFlowChart to Mermaid.js syntax."""

    # Mermaid shape syntax: (Start/End use stadium, Process uses rectangle, Decision uses rhombus)
    _SHAPES = {
        "start_end": ('(["', '"])'),  # Stadium shape for Start/End
        "process": ('["', '"]'),        # Rectangle for Process
        "decision": ('{"', '"}'),       # Rhombus for Decision - Mermaid renders these nicely
        "subflow": ('[[', ']]'),        # Subroutine shape for SubFlow
    }
    
    # Node type icons for clarity
    _ICONS = {
        "start": "▶",
        "end": "⏹",
        "process": "",  # No icon for process nodes
        "decision": "◆",
        "subflow": "📋",
    }
    

    @staticmethod
    def _sanitize(text: str) -> str:
        """Escape special characters for Mermaid syntax."""
        return text.replace('"', '#quot;').replace("(", "#40;").replace(")", "#41;")
    
    
    @staticmethod
    def _wrap_text(text: str, max_width: int = 25) -> str:
        """
        Wrap text to fit within max_width characters per line.
        Uses <br/> for line breaks in Mermaid.
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_len = len(word)
            if current_length + word_len + (1 if current_line else 0) <= max_width:
                current_line.append(word)
                current_length += word_len + (1 if len(current_line) > 1 else 0)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_len
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '<br/>'.join(lines)
    
    @staticmethod
    def _markdown_to_mermaid(text: str) -> str:
        """
        Convert markdown to Mermaid-compatible formatting.
        
        Mermaid supports limited formatting in labels:
        - Line breaks with <br/>
        - Bold text (but limited in node labels)
        - Basic HTML entities
        
        Note: Full markdown rendering is limited in node labels, but descriptions
        can use line breaks and basic formatting.
        """
        import re
        
        # Remove markdown headers (## Header -> just Header)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Convert markdown links [text](url) -> just the text
        # Mermaid doesn't support clickable links in node labels
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Replace markdown line breaks (double space + newline or explicit newline)
        text = text.replace('\n', '<br/>')
        
        # Convert code blocks/inline code (Mermaid doesn't support well, so use quotes)
        text = re.sub(r'`([^`]+)`', r'"\1"', text)
        
        # Bold: **text** or __text__ (limited support, keep simple)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        
        # Italic: *text* or _text_ (limited support, keep simple)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        return text

    @staticmethod
    def _format_node(node_id: str, label: str, shape_key: str) -> str:
        """Format a node with the given shape."""
        left, right = MermaidExporter._SHAPES[shape_key]
        return f'{node_id}{left}{label}{right}'

    @staticmethod
    def _chart_to_mermaid_lines(
        flowchart: FlowChart, 
        include_descriptions: bool = True,
        prefix: str = "",
        chart_name: str = None,
    ) -> list:
        """
        Convert a single flowchart to Mermaid lines.
        
        Args:
            flowchart: The flowchart to convert
            include_descriptions: If True, include descriptions in node labels
            prefix: Prefix for node IDs (to avoid collisions in multi-chart)
            chart_name: Optional name for subgraph
        
        Returns:
            List of Mermaid syntax lines
        """
        lines = []
        
        # Add subgraph wrapper if chart_name is provided
        if chart_name:
            safe_name = chart_name.replace(' ', '_').replace('"', '')
            lines.append(f'    subgraph {safe_name}["{chart_name}"]')
            indent = "        "
        else:
            indent = "    "
        
        # Add nodes with appropriate shapes
        for node in flowchart.nodes.values():
            raw_label = node.label
            
            # Add description to label if available
            description_text = ""
            if include_descriptions and node.metadata.get("description"):
                desc = node.metadata["description"]
                # Convert markdown and sanitize
                desc = MermaidExporter._markdown_to_mermaid(desc)
                desc = MermaidExporter._sanitize(desc)
                description_text = f"<br/><i>{desc}</i>"
            
            # Determine shape and icon based on node type
            if isinstance(node, StartNode):
                icon = MermaidExporter._ICONS["start"]
                shape = "start_end"
                wrapped_label = MermaidExporter._wrap_text(raw_label)
                label = f"{icon} {wrapped_label}"
            elif isinstance(node, EndNode):
                icon = MermaidExporter._ICONS["end"]
                shape = "start_end"
                wrapped_label = MermaidExporter._wrap_text(raw_label)
                label = f"{icon} {wrapped_label}"
            elif isinstance(node, DecisionNode):
                icon = MermaidExporter._ICONS["decision"]
                shape = "decision"
                # Mermaid renders diamonds nicely, keep all decisions as diamonds
                wrapped_label = MermaidExporter._wrap_text(raw_label)
                label = f"{icon} {wrapped_label}"
            elif isinstance(node, SubFlowNode):
                icon = MermaidExporter._ICONS["subflow"]
                shape = "subflow"
                wrapped_label = MermaidExporter._wrap_text(raw_label)
                label = f"{icon} {wrapped_label}"
            else:
                # Process node
                shape = "process"
                wrapped_label = MermaidExporter._wrap_text(raw_label)
                label = wrapped_label
            
            # Sanitize and add description
            label = MermaidExporter._sanitize(label) + description_text
            
            node_id = f"{prefix}{node.id}" if prefix else node.id
            lines.append(indent + MermaidExporter._format_node(node_id, label, shape))

        # Add edges
        for edge in flowchart.edges:
            source_id = f"{prefix}{edge.source_id}" if prefix else edge.source_id
            target_id = f"{prefix}{edge.target_id}" if prefix else edge.target_id
            
            # Skip hidden cross-chart edges in mermaid output
            if edge.metadata.get("hidden") or edge.metadata.get("crossChart"):
                continue
            
            if edge.label:
                clean_label = MermaidExporter._sanitize(edge.label)
                lines.append(f"{indent}{source_id} -- {clean_label} --> {target_id}")
            else:
                lines.append(f"{indent}{source_id} --> {target_id}")
        
        # Close subgraph if opened
        if chart_name:
            lines.append("    end")
        
        return lines

    @staticmethod
    def to_mermaid(
        flowchart: Union[FlowChart, MultiFlowChart], 
        direction: str = "TD", 
        include_descriptions: bool = True
    ) -> str:
        """
        Convert flowchart to Mermaid diagram syntax.
        
        Args:
            flowchart: The flowchart or multi-flowchart to convert
            direction: Graph direction (TD, LR, etc.)
            include_descriptions: If True, include descriptions in node labels
        
        Returns:
            Mermaid diagram syntax as a string
        """
        lines = [f"graph {direction}"]
        
        if isinstance(flowchart, MultiFlowChart):
            # Multi-chart: render each chart as a subgraph
            # Start with main chart
            main_chart = flowchart.get_main_chart()
            if main_chart:
                lines.extend(MermaidExporter._chart_to_mermaid_lines(
                    main_chart, 
                    include_descriptions=include_descriptions,
                    chart_name=main_chart.name,
                ))
            
            # Add other charts
            for chart_id, chart in flowchart.charts.items():
                if chart_id != flowchart.main_chart_id:
                    lines.extend(MermaidExporter._chart_to_mermaid_lines(
                        chart,
                        include_descriptions=include_descriptions,
                        chart_name=chart.name,
                    ))
            
            # Add cross-chart links (SubFlowNode -> target chart's start)
            # NOTE: We do NOT render these in static formats (mermaid/graphviz/svg)
            # as they make the output noisy. They are only useful in the interactive
            # HTML viewer where users can navigate between charts.
            # The subflow nodes already have the [[...]] subroutine shape which
            # indicates they link to another chart.
        else:
            # Single chart: render normally
            lines.extend(MermaidExporter._chart_to_mermaid_lines(
                flowchart, 
                include_descriptions=include_descriptions,
            ))

        return "\n".join(lines)
