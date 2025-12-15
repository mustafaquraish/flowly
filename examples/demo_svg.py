"""Demo showing SVG export using the SVG backend.

This example demonstrates how to export flowcharts to SVG format,
which requires Graphviz to be installed on the system.
"""

from flowly.frontend.dsl import Flow, Node, Decision
from flowly.backend.svg import SvgExporter


# Define nodes
check_status = Node("Check Server Status")
is_healthy = Decision("Healthy?")
log_success = Node("Log: Server OK")
restart = Node("Restart Server")
verify = Node("Verify Restart")
alert = Node("Send Alert")


# Build flow
@Flow("Server Health Check")
def health_check(flow):
    """Simple server health check workflow."""
    check_status()
    
    if is_healthy():
        log_success()
    else:
        restart()
        verify()
        
        if is_healthy():
            log_success()
        else:
            alert()


# Try to export to SVG
try:
    svg_output = SvgExporter.to_svg(health_check.chart)
    
    # Save to file
    with open("build/health_check.svg", "w") as f:
        f.write(svg_output)
    
    print("✓ SVG exported successfully to: build/health_check.svg")
    print(f"  SVG size: {len(svg_output)} bytes")
    print("\nYou can:")
    print("  - Open it in a web browser")
    print("  - Embed it in HTML")
    print("  - Include it in documentation")
    
except RuntimeError as e:
    print(f"✗ Error: {e}")
    print("\nTo use SVG export, install Graphviz:")
    print("  macOS:   brew install graphviz")
    print("  Ubuntu:  sudo apt-get install graphviz")
    print("  Windows: Download from https://graphviz.org/download/")
