"""HTML exporter that bundles flowcharts into standalone interactive HTML files."""

import json
import re
import sys
from pathlib import Path

from flowly.core.ir import FlowChart
from flowly.core.serialization import JsonSerializer

# Handle importlib.resources compatibility across Python versions
if sys.version_info >= (3, 9):
    from importlib.resources import files
else:
    from importlib_resources import files


class HtmlExporter:
    """Exports a FlowChart to a standalone interactive HTML player.
    
    This exporter bundles the flowplay application files (HTML, CSS, JS)
    into a single standalone HTML file with the flow data embedded as
    a global JavaScript variable `bundledFlowJSON`.
    """
    
    @staticmethod
    def _read_flowplay_file(filename: str) -> str:
        """Read a file from the bundled flowplay package data."""
        try:
            # Get the flowly package directory
            flowly_package = files('flowly')
            # Navigate to the flowplay directory (../flowplay from flowly)
            flowplay_path = flowly_package.parent / 'flowplay' / filename
            return flowplay_path.read_text(encoding='utf-8')
        except Exception as e:
            # Fallback to filesystem for development mode
            fallback_path = Path(__file__).parent.parent.parent / "flowplay" / filename
            if fallback_path.exists():
                return fallback_path.read_text(encoding='utf-8')
            raise FileNotFoundError(f"Flowplay file not found: {filename}") from e
    
    @staticmethod
    def _extract_body_content(html: str) -> str:
        """Extract content between <body> tags, excluding script src tags."""
        # Find body content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        if not body_match:
            raise ValueError("Could not find body content in index.html")
        
        body_content = body_match.group(1)
        
        # Remove the external script tag (app.js) - we'll inline it
        body_content = re.sub(r'<script\s+src=["\']app\.js["\']\s*></script>', '', body_content)
        
        return body_content.strip()
    
    @staticmethod
    def _extract_head_content(html: str) -> str:
        """Extract content from <head> tags, excluding local CSS link."""
        # Find head content
        head_match = re.search(r'<head[^>]*>(.*?)</head>', html, re.DOTALL)
        if not head_match:
            raise ValueError("Could not find head content in index.html")
        
        head_content = head_match.group(1)
        
        # Remove the local stylesheet link (styles.css) - we'll inline it
        head_content = re.sub(r'<link\s+rel=["\']stylesheet["\']\s+href=["\']styles\.css["\']\s*/?\s*>', '', head_content)
        
        return head_content.strip()

    @staticmethod
    def to_html(flowchart: FlowChart) -> str:
        """Returns the complete standalone HTML string with bundled flowplay."""
        # Convert chart to dictionary and JSON
        data = JsonSerializer.to_dict(flowchart)
        json_str = json.dumps(data, indent=2)
        
        # Read flowplay source files
        index_html = HtmlExporter._read_flowplay_file("index.html")
        styles_css = HtmlExporter._read_flowplay_file("styles.css")
        app_js = HtmlExporter._read_flowplay_file("app.js")
        
        # Extract parts from index.html
        head_content = HtmlExporter._extract_head_content(index_html)
        body_content = HtmlExporter._extract_body_content(index_html)
        
        # Build the standalone HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
{head_content}
    <title>{flowchart.name} - FlowPlay</title>
    <style>
{styles_css}
    </style>
</head>
<body>
{body_content}

    <script>
// Bundled flow data - loaded by FlowPlay if present
const bundledFlowJSON = {json_str};
    </script>
    <script>
{app_js}
    </script>
</body>
</html>'''
        
        return html

    @staticmethod
    def save(flowchart: FlowChart, filename: str):
        """Saves the HTML to a file."""
        html = HtmlExporter.to_html(flowchart)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
