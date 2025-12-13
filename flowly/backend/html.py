import json
from flowly.core.ir import FlowChart
from flowly.core.serialization import JsonSerializer

class HtmlExporter:
    """Exports a FlowChart to a standalone interactive HTML player."""
    
    TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f6f8; color: #333; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
        #app {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 600px; width: 100%; }}
        h1 {{ margin-top: 0; color: #2c3e50; font-size: 1.5rem; }}
        .node-label {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; }}
        .node-type {{ font-size: 0.8rem; text-transform: uppercase; color: #7f8c8d; margin-bottom: 0.5rem; letter-spacing: 0.05em; }}
        .options {{ display: flex; flex-direction: column; gap: 0.5rem; }}
        button {{ background: #3498db; color: white; border: none; padding: 0.75rem 1rem; border-radius: 4px; cursor: pointer; font-size: 1rem; text-align: left; transition: background 0.2s; }}
        button:hover {{ background: #2980b9; }}
        button:disabled {{ background: #bdc3c7; cursor: not-allowed; }}
        .history {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee; font-size: 0.9rem; color: #95a5a6; }}
    </style>
</head>
<body>
    <div id="app">
        <div id="content">Loading...</div>
    </div>

    <script>
        const flowData = {flow_json};

        class FlowRunner {{
            constructor(data) {{
                this.nodes = {{}};
                this.edges = data.edges;
                this.currentNode = null;
                this.history = [];

                data.nodes.forEach(n => {{ this.nodes[n.id] = n; }});
            }}

            start() {{
                // Find start node
                const startNode = Object.values(this.nodes).find(n => n.type === 'StartNode');
                if (startNode) {{
                    this.moveTo(startNode);
                }} else {{
                    console.error("No StartNode found");
                }}
            }}

            moveTo(node) {{
                this.currentNode = node;
                this.history.push(node.label);
                this.render();
                
                // Auto-advance if generic ProcessNode with 1 output?
                // For UI player, maybe we prefer "Next" button always?
                // Let's implement auto-advance for now to match Python runner,
                // but maybe add a small delay or "Continue" button could be better for UI.
                // For now: pure auto-advance if 1 path and not a Decision/End node? 
                // Actually, let's treat everything as requiring interaction except purely internal nodes if we wanted.
                // But to match Python behavior exactly:
                
                const frameId = requestAnimationFrame(() => {{
                     const opts = this.getOptions();
                     if (opts.length === 1 && (node.type === 'StartNode' || node.type === 'ProcessNode')) {{
                         // Simple auto-next
                         // Adding a wrapper to let user see the node? 
                         // For a visual player, "Process" nodes usually equate to "Show something then click next".
                         // So let's NOT auto-advance in the UI unless it's strictly a logic node (not implemented yet).
                         // Wait, the Python runner auto-advanced. 
                         // If we auto-advance here, the user won't see "Enter Address".
                         // So for the HTML Player, we should probably render the "Next" button even for single options.
                     }}
                }});
            }}

            getOptions() {{
                if (!this.currentNode) return [];
                return this.edges.filter(e => e.source === this.currentNode.id);
            }}

            selectOption(index) {{
                const opts = this.getOptions();
                if (opts[index]) {{
                    const targetId = opts[index].target;
                    this.moveTo(this.nodes[targetId]);
                }}
            }}
            
            render() {{
                const app = document.getElementById('content');
                if (!this.currentNode) return;
                
                let html = `<div class="node-type">${{this.currentNode.type}}</div>`;
                html += `<div class="node-label">${{this.currentNode.label}}</div>`;
                
                if (this.currentNode.type === 'EndNode') {{
                    html += `<p>Flow completed.</p>`;
                    html += `<button onclick="runner.start()">Restart</button>`;
                }} else {{
                    const opts = this.getOptions();
                    if (opts.length === 0) {{
                        html += `<p>Dead end.</p>`;
                    }} else {{
                        html += `<div class="options">`;
                        opts.forEach((opt, idx) => {{
                            const label = opt.label || 'Next';
                            html += `<button onclick="runner.selectOption(${{idx}})">${{label}}</button>`;
                        }});
                        html += `</div>`;
                    }}
                }}

                app.innerHTML = html;
            }}
        }}

        const runner = new FlowRunner(flowData);
        runner.start();
    </script>
</body>
</html>
    """

    @staticmethod
    def to_html(flowchart: FlowChart) -> str:
        """Returns the complete HTML string."""
        # Convert chart to dictionary
        data = JsonSerializer.to_dict(flowchart)
        # Serialize to JSON string for embedding
        json_str = json.dumps(data)
        
        return HtmlExporter.TEMPLATE.format(
            title=flowchart.name,
            flow_json=json_str
        )

    @staticmethod
    def save(flowchart: FlowChart, filename: str):
        """Saves the HTML to a file."""
        html = HtmlExporter.to_html(flowchart)
        with open(filename, 'w') as f:
            f.write(html)
