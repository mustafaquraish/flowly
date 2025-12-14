"""
Demo: Using FlowTracer to build flowcharts from Python code.

IMPORTANT: The FlowTracer captures the EXECUTED PATH through code.
It does NOT build complete flowcharts with all branches - for that,
use FlowBuilder instead.

FlowTracer is useful for:
- Documenting what path was taken through a procedure
- Creating execution traces
- Generating flowcharts that show "what happened" vs "what could happen"

For complete flowcharts with all branches, use FlowBuilder (see demo.py).
"""

import sys
import os

# Ensure flowly is in path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from flowly.frontend import FlowTracer, SimpleFlowTracer
from flowly.backend.mermaid import MermaidExporter
from flowly.backend.html import HtmlExporter
from flowly.core.serialization import JsonSerializer


def create_server_troubleshooting_flow(
    server_responding: bool = True,
    cpu_high: bool = False,
    memory_high: bool = False
):
    """
    Create a server troubleshooting flowchart.
    
    The flowchart generated depends on the runtime parameters,
    allowing you to visualize different paths through the same logic.
    """
    with FlowTracer("Server Troubleshooting") as flow:
        flow.node("Alert Received", description="""
An automated alert has been triggered indicating a potential issue.

## Initial Steps
- Note the timestamp
- Check if recurring
- Identify affected services
""")
        
        flow.node("Check Dashboard", description="""
Open the server status dashboard to assess system health.

## Key Metrics
- CPU Usage
- Memory
- Disk I/O
- Network latency
""")
        
        if flow.decision("Is server responding?", server_responding):
            flow.node("Check Resource Usage")
            
            if flow.decision("High CPU (>80%)?", cpu_high):
                flow.node("Identify Top Process", description="""
Run diagnostic commands:
```bash
top -bn1 | head -20
ps aux --sort=-%cpu | head -10
```
""")
                flow.node("Consider Scaling/Restart")
            else:
                if flow.decision("High Memory?", memory_high):
                    flow.node("Check for Memory Leaks")
                    flow.node("Analyze Heap Dumps")
                else:
                    flow.node("Check Network/IO")
                    flow.node("Review Recent Deployments")
        else:
            flow.node("Attempt Ping", description="""
Test basic connectivity:
```bash
ping -c 5 <server_ip>
```
""")
            
            flow.node("Check Cloud Console")
            flow.node("Escalate to Infrastructure Team")
            flow.end("Escalated")
    
    return flow.build()


def create_user_signup_flow(
    email_valid: bool = True,
    username_available: bool = True,
    password_strong: bool = True
):
    """
    Create a user signup flow demonstrating validation steps.
    """
    with SimpleFlowTracer("User Signup") as flow:
        flow.Node("User Submits Form")
        
        if flow.Decision("Is email format valid?", email_valid,
                        yes_label="Valid", no_label="Invalid"):
            
            if flow.Decision("Is username available?", username_available,
                           yes_label="Available", no_label="Taken"):
                
                if flow.Decision("Is password strong enough?", password_strong,
                               yes_label="Strong", no_label="Weak"):
                    flow.Node("Create User Account")
                    flow.Node("Send Verification Email")
                    flow.Node("Redirect to Dashboard")
                else:
                    flow.Node("Show Password Requirements")
                    flow.End("Registration Incomplete")
            else:
                flow.Node("Suggest Alternative Usernames")
                flow.End("Registration Incomplete")
        else:
            flow.Node("Show Email Format Error")
            flow.End("Registration Incomplete")
    
    return flow.build()


def create_retry_with_backoff_flow(max_attempts: int = 3, success_on: int = 2):
    """
    Create a flow showing retry logic with a loop.
    
    Args:
        max_attempts: Maximum retry attempts
        success_on: Which attempt succeeds (0-indexed, -1 for never)
    """
    attempt = 0
    success = False
    
    with FlowTracer("Retry with Backoff") as flow:
        flow.node("Start Operation")
        
        while flow.until("Retry operation?", attempt < max_attempts and not success):
            flow.node(f"Attempt #{attempt + 1}", description=f"""
Attempting operation (try {attempt + 1} of {max_attempts}).

If this fails, will wait {2 ** attempt} seconds before retry.
""")
            
            # Simulate success/failure
            if attempt == success_on:
                success = True
                flow.node("Operation Succeeded!")
            else:
                flow.node("Operation Failed")
                if attempt < max_attempts - 1:
                    flow.node(f"Wait {2 ** attempt}s (backoff)")
            
            attempt += 1
        
        if flow.decision("Was operation successful?", success):
            flow.node("Process Results")
            flow.node("Send Success Notification")
        else:
            flow.node("Log Failure")
            flow.node("Send Alert to On-Call")
            flow.end("Operation Failed After Retries")
    
    return flow.build()


def main():
    print("=" * 60)
    print("FlowTracer Demo - Generating Flowcharts from Python Code")
    print("=" * 60)
    
    # Demo 1: Server Troubleshooting (happy path - server responding, low resources)
    print("\n1. Server Troubleshooting Flow (server OK, low CPU/memory)")
    chart1 = create_server_troubleshooting_flow(
        server_responding=True, 
        cpu_high=False, 
        memory_high=False
    )
    print(f"   Generated: {len(chart1.nodes)} nodes, {len(chart1.edges)} edges")
    
    # Demo 2: Server Troubleshooting (server down)
    print("\n2. Server Troubleshooting Flow (server NOT responding)")
    chart2 = create_server_troubleshooting_flow(server_responding=False)
    print(f"   Generated: {len(chart2.nodes)} nodes, {len(chart2.edges)} edges")
    
    # Demo 3: User Signup (all valid)
    print("\n3. User Signup Flow (all validations pass)")
    chart3 = create_user_signup_flow(
        email_valid=True,
        username_available=True,
        password_strong=True
    )
    print(f"   Generated: {len(chart3.nodes)} nodes, {len(chart3.edges)} edges")
    
    # Demo 4: User Signup (weak password)
    print("\n4. User Signup Flow (weak password)")
    chart4 = create_user_signup_flow(
        email_valid=True,
        username_available=True,
        password_strong=False
    )
    print(f"   Generated: {len(chart4.nodes)} nodes, {len(chart4.edges)} edges")
    
    # Demo 5: Retry with loop
    print("\n5. Retry Flow (succeeds on attempt 2)")
    chart5 = create_retry_with_backoff_flow(max_attempts=3, success_on=1)
    print(f"   Generated: {len(chart5.nodes)} nodes, {len(chart5.edges)} edges")
    
    # Export one to Mermaid
    print("\n" + "=" * 60)
    print("Mermaid Export (Server Troubleshooting - OK path)")
    print("=" * 60)
    mermaid = MermaidExporter.to_mermaid(chart1)
    print(mermaid)
    
    # Export to HTML
    print("\n" + "=" * 60)
    print("Exporting to build/tracer_demo.html")
    print("=" * 60)
    
    os.makedirs("build", exist_ok=True)
    html = HtmlExporter.to_html(chart1)
    with open("build/tracer_demo.html", "w") as f:
        f.write(html)
    print("Done! Open build/tracer_demo.html in a browser.")
    
    # Export JSON
    json_str = JsonSerializer.to_json(chart1)
    with open("build/tracer_demo.json", "w") as f:
        f.write(json_str)
    print("Also exported build/tracer_demo.json")


if __name__ == "__main__":
    main()
