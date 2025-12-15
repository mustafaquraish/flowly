"""Demo showing markdown rendering in node descriptions.

This example demonstrates how descriptions with markdown formatting
are rendered in both Mermaid and Graphviz backends.
"""

from flowly.frontend.dsl import Flow, Node, Decision
from flowly.backend.mermaid import MermaidExporter
from flowly.backend.graphviz import GraphvizExporter


# Define nodes with markdown descriptions
start = Node(
    "Start Processing",
    description="Initialize the data pipeline\nwith **robust** error handling"
)

validate = Node(
    "Validate Input", 
    description="""Check data quality:
- Required fields present
- Types are **correct**
- Values in *valid* range
Use `validate_schema()` function"""
)

check = Decision(
    "Valid?",
    description="Returns `True` if validation passed,\n`False` otherwise"
)

process = Node(
    "Process Data",
    description="Transform using:\n- **Normalize** values\n- *Clean* strings\n- Apply `filters`"
)

error = Node(
    "Log Error",
    description="Record validation failure with **timestamp** and *reason*"
)

end = Node("Complete")


# Build flow using decorator
@Flow("Markdown Demo")
def markdown_flow(flow):
    """Demo flow with markdown descriptions."""
    start()
    validate()
    
    if check():
        process()
    else:
        error()
    
    end()


# Export to Mermaid (descriptions as tooltips)
mermaid_output = MermaidExporter.to_mermaid(markdown_flow.chart)
print("=== MERMAID OUTPUT (with descriptions) ===")
print(mermaid_output)
print()

# Export to Graphviz (descriptions in HTML labels)
dot_output = GraphvizExporter.to_dot(markdown_flow.chart)
print("=== GRAPHVIZ OUTPUT (with HTML descriptions) ===")
print(dot_output)
print()

# Can disable descriptions if needed
mermaid_no_desc = MermaidExporter.to_mermaid(markdown_flow.chart, include_descriptions=False)
print("=== MERMAID OUTPUT (without descriptions) ===")
print(mermaid_no_desc)
