from flowly.core.ir import FlowChart, StartNode, EndNode, DecisionNode


class MermaidExporter:
    """Exports a FlowChart to Mermaid.js syntax."""

    # Mermaid shape syntax: (Start/End use stadium, Process uses rectangle, Decision uses rhombus)
    _SHAPES = {
        "start_end": ('(["', '"])'),  # Stadium shape for Start/End
        "process": ('["', '"]'),        # Rectangle for Process
        "decision": ('{"', '"}'),       # Rhombus for Decision
    }

    @staticmethod
    def _sanitize(text: str) -> str:
        """Escape special characters for Mermaid syntax."""
        return text.replace('"', '#quot;').replace("(", "#40;").replace(")", "#41;")
    
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
    def to_mermaid(flowchart: FlowChart, direction: str = "TD", include_descriptions: bool = True) -> str:
        """
        Convert flowchart to Mermaid diagram syntax.
        
        Args:
            flowchart: The flowchart to convert
            direction: Graph direction (TD, LR, etc.)
            include_descriptions: If True, include descriptions in node labels
        """
        lines = [f"graph {direction}"]
        
        # Add nodes with appropriate shapes
        for node in flowchart.nodes.values():
            label = MermaidExporter._sanitize(node.label)
            
            # Add description to label if available
            if include_descriptions and node.metadata.get("description"):
                desc = node.metadata["description"]
                # Convert markdown and sanitize
                desc = MermaidExporter._markdown_to_mermaid(desc)
                desc = MermaidExporter._sanitize(desc)
                # Combine label with description (full text, no truncation)
                label = f"{label}<br/><i>{desc}</i>"
            
            if isinstance(node, (StartNode, EndNode)):
                shape = "start_end"
            elif isinstance(node, DecisionNode):
                shape = "decision"
            else:
                shape = "process"
            lines.append("    " + MermaidExporter._format_node(node.id, label, shape))

        # Add edges
        for edge in flowchart.edges:
            if edge.label:
                clean_label = MermaidExporter._sanitize(edge.label)
                lines.append(f"    {edge.source_id} -- {clean_label} --> {edge.target_id}")
            else:
                lines.append(f"    {edge.source_id} --> {edge.target_id}")

        return "\n".join(lines)
