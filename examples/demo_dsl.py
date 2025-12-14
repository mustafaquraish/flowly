"""
Demo of the explicit DSL-based flowchart builder.

All nodes are explicitly defined - no implicit magic, no LSP errors.
"""

from flowly.frontend.dsl import Flow, Node, Decision
from flowly.backend.html import HtmlExporter


# =============================================================================
# STEP 1: Define your nodes explicitly with metadata
# =============================================================================

# Process nodes - these are your actions/steps
check_input = Node(
    "Check User Input",
    description="""
Validate the incoming user data.

## Checks performed:
- Format validation
- Required fields
- Data type verification
"""
)

process_data = Node(
    "Process Data", 
    description="Transform and normalize the validated data."
)

save_result = Node(
    "Save Result",
    description="Persist the processed data to the database."
)

log_error = Node(
    "Log Error",
    description="Record the error details for debugging."
)

notify_user = Node(
    "Notify User",
    description="Send an error notification to the user."
)

# Decision nodes - these are your conditions
is_valid = Decision(
    "Is input valid?",
    description="Check if all validation rules pass.",
    yes_label="Valid",
    no_label="Invalid"
)

should_retry = Decision(
    "Retry?",
    description="Should we attempt to reprocess?",
    yes_label="Yes",
    no_label="No, give up"
)


# =============================================================================
# STEP 2: Define your flow using Python control flow
# =============================================================================

@Flow("Data Processing Pipeline")
def data_pipeline(flow):
    """
    A simple data processing pipeline.
    
    The flow parameter provides:
    - flow.step("Label", description="...") for inline nodes
    - flow.end("Label") for explicit end points
    """
    
    # Calling a node adds it to the flow
    check_input()
    
    # Decisions work in if statements
    if is_valid():
        process_data()
        save_result()
        
        # Inline step for one-offs (no need to define globally)
        flow.step("Send Success Email")
    else:
        log_error()
        notify_user()
        
        # Explicit end for this branch
        flow.end("Failed")
        return  # Return ends this path
    
    # This only runs for the success path
    flow.step("Cleanup Resources")


# =============================================================================
# STEP 3: A more complex example - Server Troubleshooting
# =============================================================================

# Define all nodes with full metadata
alert_received = Node(
    "Alert Received",
    description="""
An automated alert has been triggered indicating **high latency**.

## Initial Information
- Alert Source: Monitoring System
- Severity: P2 (High)  
- SLA: 30 minutes to acknowledge
"""
)

check_dashboard = Node(
    "Check Server Dashboard",
    description="""
Open the server status dashboard to get an overview.

## Key Metrics
1. CPU Usage (>80% is concerning)
2. Memory pressure
3. Disk I/O
4. Network latency
"""
)

ping_server = Node("Ping Server IP", description="Basic connectivity test: `ping -c 5 <server_ip>`")
check_power = Node("Check Physical Power", description="Access the Lights-Out Management interface")
power_cycle = Node("Power Cycle", description="⚠️ Warning: This causes a brief outage")
contact_dc = Node("Contact Data Center", description="Escalate to DC Operations team")
attempt_ssh = Node("Attempt SSH", description="Try `ssh -o ConnectTimeout=10 admin@<server>`")

check_metrics = Node("Check CPU/RAM Metrics", description="Run `top`, `free -h`, `vmstat`")
identify_process = Node("Identify Top Process", description="Find resource-hungry process with `ps aux`")
restart_service = Node("Restart Service", description="`systemctl restart myapp`")
kill_process = Node("Kill Suspicious Process", description="⚠️ Security: Unknown process detected")
security_audit = Node("Flag for Security Audit", description="Create security incident ticket")

check_network = Node("Check Network", description="Check bandwidth with `iftop`, `nethogs`")
enable_mitigation = Node("Enable DDoS Mitigation", description="Activate Cloudflare 'Under Attack' mode")

verify_fix = Node("Verify Fix", description="Confirm latency is back to normal (<100ms p99)")
deep_dive = Node("Deep Dive Logs", description="Analyze application and database logs")

# Decisions
is_down = Decision("Is Server Down?", yes_label="Down", no_label="Up but slow")
ping_ok = Decision("Ping Responds?")
recovered = Decision("Did it recover?")
high_cpu = Decision("High CPU Load?", description="CPU consistently above 80%?")
is_app = Decision("Is it our app?", yes_label="Our App", no_label="Unknown Process")
is_ddos = Decision("DDoS Attack?")
is_fixed = Decision("Latency Normal?")


@Flow("Server Troubleshooting Guide")
def server_troubleshooting(flow):
    """Complete server troubleshooting runbook."""
    
    alert_received()
    check_dashboard()
    
    if is_down():
        # Server is completely down
        ping_server()
        
        if ping_ok():
            attempt_ssh()  # Can reach it
        else:
            # Hardware issue likely
            check_power()
            power_cycle()
            
            if recovered():
                attempt_ssh()  # Same node - explicit reuse!
            else:
                contact_dc()
                flow.end("Escalate to Hardware Team")
                return
    else:
        # Server is up but slow
        check_metrics()
        
        if high_cpu():
            identify_process()
            
            if is_app():
                restart_service()
            else:
                kill_process()
                security_audit()
        else:
            check_network()
            
            if is_ddos():
                enable_mitigation()
            else:
                flow.end("Contact ISP")
                return
    
    # Common verification path
    verify_fix()
    
    if is_fixed():
        flow.end("Incident Resolved ✅")
    else:
        deep_dive()
        flow.end("Escalate to Senior Engineer")


# =============================================================================
# STEP 4: Export and use
# =============================================================================

if __name__ == "__main__":
    # Print info about the simple flow
    print("="*60)
    print("Data Processing Pipeline")
    print("="*60)
    chart1 = data_pipeline.chart
    print(f"Nodes: {len(chart1.nodes)}")
    print(f"Edges: {len(chart1.edges)}")
    
    # Print info about the complex flow
    print("\n" + "="*60)
    print("Server Troubleshooting Guide")
    print("="*60)
    chart2 = server_troubleshooting.chart
    print(f"Nodes: {len(chart2.nodes)}")
    print(f"Edges: {len(chart2.edges)}")
    
    # Show nodes
    print("\nNodes:")
    for node in chart2.nodes.values():
        desc = node.metadata.get("description", "")[:40] if node.metadata else ""
        print(f"  {type(node).__name__:15} {node.label[:30]:30} {desc}...")
    
    # Export to HTML
    html = HtmlExporter.to_html(chart2)
    with open("build/dsl_troubleshoot.html", "w") as f:
        f.write(html)
    print(f"\nExported to: build/dsl_troubleshoot.html")
