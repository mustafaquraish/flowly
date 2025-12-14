"""
Recreate the complex server troubleshooting flow using StaticFlowBuilder.

This demonstrates using StaticFlowBuilder for a complex graph with cross-connections.
For graphs like this with multiple merge points and cross-edges, we need to use
the connect() method for manual edge creation.
"""

from flowly.frontend.static import StaticFlowBuilder
from flowly.core.serialization import JsonSerializer
import json


def create_server_troubleshooting_flow_static():
    """
    Creates the same complex flowchart as tests/complex_flow.py
    using the StaticFlowBuilder API.
    """
    flow = StaticFlowBuilder("Server Layout Inspection")
    
    # Since this is a complex graph with cross-connections,
    # we won't use the context manager for the whole flow.
    # Instead, we'll build it step by step with manual connections.
    
    flow._flowchart = flow._flowchart or __import__('flowly.core.ir', fromlist=['FlowChart']).FlowChart(flow.name)
    flow._started = True
    flow._pending_merge_nodes = []
    
    from flowly.core.ir import StartNode, EndNode, ProcessNode, DecisionNode, Edge
    
    # === 1. Verification Phase ===
    start = StartNode(label="Alert Received: High Latency", metadata={"description": """
An automated alert has been triggered indicating **high latency** on one or more production servers.

## Initial Information
- Alert Source: Monitoring System (Datadog/PagerDuty)
- Severity: P2 (High)
- SLA: 30 minutes to acknowledge

## Checklist
- [ ] Note the timestamp of the alert
- [ ] Check if this is a recurring issue
- [ ] Identify affected services
"""})
    flow._flowchart.add_node(start)
    
    check_status = ProcessNode(label="Check Server Status Dashboard", metadata={"description": """
Open the server status dashboard to get an overview of the system health.

## Key Metrics to Check
1. **CPU Usage**: Look for sustained >80% usage
2. **Memory**: Check for memory pressure or OOM events
3. **Disk I/O**: High iowait can cause latency
4. **Network**: Check for packet loss or high latency

## Tools
- Grafana: `https://grafana.internal/d/server-health`
- Datadog: Check the APM traces
"""})
    flow._flowchart.add_node(check_status)
    flow.connect(start, check_status)
    
    is_down = DecisionNode(label="Is Server Down?", metadata={"description": """
Determine if the server is completely unreachable or just experiencing degraded performance.

**Down** = No response to health checks, SSH unavailable
**Up but slow** = Responds but with high latency
"""})
    flow._flowchart.add_node(is_down)
    flow.connect(check_status, is_down)
    
    # === Branch A: Server is Down ===
    ping_check = ProcessNode(label="Ping Server IP", metadata={"description": """
Run a basic network connectivity test.

```bash
ping -c 5 <server_ip>
```

Look for:
- 100% packet loss = Network issue or server down
- High latency (>100ms) = Network congestion
"""})
    flow._flowchart.add_node(ping_check)
    flow.connect(is_down, ping_check, label="Yes")
    
    is_pingable = DecisionNode(label="Ping Response?")
    flow._flowchart.add_node(is_pingable)
    flow.connect(ping_check, is_pingable)
    
    # A.1: Hardware failure path
    check_power = ProcessNode(label="Check Physical Power/LOM", metadata={"description": """
Access the Lights-Out Management (LOM) interface to check physical server status.

## Steps
1. Log into iLO/DRAC/IPMI console
2. Check power status LED
3. Review hardware event logs
4. Check for any amber/red LEDs indicating failure
"""})
    flow._flowchart.add_node(check_power)
    flow.connect(is_pingable, check_power, label="No")
    
    power_cycle = ProcessNode(label="Power Cycle", metadata={"description": """
Perform a graceful power cycle through the LOM interface.

⚠️ **Warning**: This will cause a brief outage. Ensure:
- Change ticket is created
- Stakeholders are notified
- Failover is active (if applicable)
"""})
    flow._flowchart.add_node(power_cycle)
    flow.connect(check_power, power_cycle)
    
    did_recover = DecisionNode(label="Did it recover?")
    flow._flowchart.add_node(did_recover)
    flow.connect(power_cycle, did_recover)
    
    contact_dc = ProcessNode(label="Contact Data Center Ops", metadata={"description": """
Server did not recover after power cycle. This indicates a potential hardware failure.

**Contact**: DC Operations Team
**Phone**: +1-555-DC-HELP
**Ticket**: Create a DCOPS ticket with server details
"""})
    flow._flowchart.add_node(contact_dc)
    flow.connect(did_recover, contact_dc, label="No")
    
    escalate_hw = EndNode(label="Escalate to Hardware Team", metadata={"description": """
# Escalation Complete

The issue has been escalated to the Hardware Team for physical intervention.

**Expected Response Time**: 2-4 hours
**Next Steps**: Monitor the DCOPS ticket for updates
"""})
    flow._flowchart.add_node(escalate_hw)
    flow.connect(contact_dc, escalate_hw)
    
    # A.2: OS/Network path
    ssh_attempt = ProcessNode(label="Attempt SSH", metadata={"description": """
Try to establish an SSH connection to the server.

```bash
ssh -o ConnectTimeout=10 admin@<server_ip>
```

If successful, proceed with OS-level diagnostics.
"""})
    flow._flowchart.add_node(ssh_attempt)
    flow.connect(is_pingable, ssh_attempt, label="Yes")
    flow.connect(did_recover, ssh_attempt, label="Yes")  # Cross-connection!
    
    # === Branch B: Server is Up but Slow ===
    check_metrics = ProcessNode(label="Check CPU/RAM Metrics", metadata={"description": """
Run system resource checks:

```bash
top -bn1 | head -20
free -h
vmstat 1 5
```

Look for:
- High CPU usage by specific processes
- Memory exhaustion / swap usage
- I/O wait issues
"""})
    flow._flowchart.add_node(check_metrics)
    flow.connect(is_down, check_metrics, label="No")
    
    high_load = DecisionNode(label="High CPU Load?", metadata={"description": "CPU usage consistently above 80%?"})
    flow._flowchart.add_node(high_load)
    flow.connect(check_metrics, high_load)
    
    # B.1: Application Issue
    top_proc = ProcessNode(label="Identify Top Process", metadata={"description": """
Identify which process is consuming the most resources.

```bash
ps aux --sort=-%cpu | head -10
```
"""})
    flow._flowchart.add_node(top_proc)
    flow.connect(high_load, top_proc, label="Yes")
    
    is_known_app = DecisionNode(label="Is it main app?", metadata={"description": "Is the high-CPU process our application or something unexpected?"})
    flow._flowchart.add_node(is_known_app)
    flow.connect(top_proc, is_known_app)
    
    restart_service = ProcessNode(label="Restart Service", metadata={"description": """
Restart the application service:

```bash
systemctl restart myapp
```

Monitor logs for startup errors:
```bash
journalctl -u myapp -f
```
"""})
    flow._flowchart.add_node(restart_service)
    flow.connect(is_known_app, restart_service, label="Yes")
    
    verify_fix = DecisionNode(label="Latency Normal?", metadata={"description": "Check if latency has returned to normal levels (<100ms p99)"})
    flow._flowchart.add_node(verify_fix)
    flow.connect(restart_service, verify_fix)
    
    resolved = EndNode(label="Incident Resolved", metadata={"description": """
# ✅ Incident Resolved

The issue has been resolved. Don't forget to:
1. Update the incident ticket
2. Write a brief post-mortem if needed
3. Thank the team!
"""})
    flow._flowchart.add_node(resolved)
    flow.connect(verify_fix, resolved, label="Yes")
    
    # B.2: Unknown Process / Security
    kill_proc = ProcessNode(label="Kill Suspicious Process", metadata={"description": """
⚠️ **Security Alert**: Unknown process consuming resources.

```bash
kill -9 <pid>
```

Preserve evidence before killing:
```bash
cat /proc/<pid>/cmdline
ls -la /proc/<pid>/exe
```
"""})
    flow._flowchart.add_node(kill_proc)
    flow.connect(is_known_app, kill_proc, label="No")
    
    security_audit = ProcessNode(label="Flag for Security Audit", metadata={"description": """
Create a security incident ticket with:
- Process details
- Network connections (`netstat -tulpn`)
- Recent logins (`last`)
- Modified files (`find / -mmin -60 -type f`)
"""})
    flow._flowchart.add_node(security_audit)
    flow.connect(kill_proc, security_audit)
    flow.connect(security_audit, verify_fix)  # Cross-connection!
    
    # B.3: Network Issue (Low CPU)
    check_net = ProcessNode(label="Check Network Bandwidth", metadata={"description": """
Check network utilization:

```bash
iftop -i eth0
nethogs
```

Look for unusual traffic patterns or bandwidth saturation.
"""})
    flow._flowchart.add_node(check_net)
    flow.connect(high_load, check_net, label="No")
    
    ddos_check = DecisionNode(label="DDoS Attack?", metadata={"description": "Signs of DDoS: unusual traffic volume, many connections from same source"})
    flow._flowchart.add_node(ddos_check)
    flow.connect(check_net, ddos_check)
    
    enable_mitigation = ProcessNode(label="Enable Mitigation", metadata={"description": """
Enable DDoS mitigation:

1. Activate Cloudflare "Under Attack" mode
2. Enable rate limiting
3. Block suspicious IP ranges
4. Contact upstream provider if needed
"""})
    flow._flowchart.add_node(enable_mitigation)
    flow.connect(ddos_check, enable_mitigation, label="Yes")
    flow.connect(enable_mitigation, verify_fix)  # Cross-connection!
    
    isp_issue = EndNode(label="Contact ISP / Upstream", metadata={"description": """
Network issue appears to be upstream. Contact the ISP/network provider.

**ISP Support**: +1-555-ISP-HELP
**Circuit ID**: Check the network documentation
"""})
    flow._flowchart.add_node(isp_issue)
    flow.connect(ddos_check, isp_issue, label="No")
    
    # Loop from verify fix back to investigation if fail
    deep_dive = ProcessNode(label="Deep Dive Logs", metadata={"description": """
The initial fix didn't resolve the issue. Time for deep investigation:

1. Check application logs
2. Review recent deployments
3. Check for configuration changes
4. Analyze database slow query logs
"""})
    flow._flowchart.add_node(deep_dive)
    flow.connect(verify_fix, deep_dive, label="No")
    flow.connect(deep_dive, escalate_hw)  # Cross-connection!
    
    return flow.build()


def compare_flows():
    """Compare the static flow with the original FlowBuilder flow."""
    import sys
    sys.path.insert(0, "/Users/mustafa/dev/flowly")
    from tests.complex_flow import create_server_troubleshooting_flow
    
    original = create_server_troubleshooting_flow()
    static = create_server_troubleshooting_flow_static()
    
    print("=== Comparison ===")
    print(f"Original: {len(original.nodes)} nodes, {len(original.edges)} edges")
    print(f"Static:   {len(static.nodes)} nodes, {len(static.edges)} edges")
    print()
    
    # Compare node labels
    original_labels = sorted([n.label for n in original.nodes.values()])
    static_labels = sorted([n.label for n in static.nodes.values()])
    
    if original_labels == static_labels:
        print("✓ Node labels match!")
    else:
        print("✗ Node labels differ:")
        print(f"  Only in original: {set(original_labels) - set(static_labels)}")
        print(f"  Only in static: {set(static_labels) - set(original_labels)}")
    
    # Compare edge structure (by label pairs)
    def get_edge_set(flow):
        edges = set()
        for e in flow.edges:
            src = flow.nodes[e.source_id].label
            tgt = flow.nodes[e.target_id].label
            lbl = e.label or ""
            edges.add((src, tgt, lbl))
        return edges
    
    original_edges = get_edge_set(original)
    static_edges = get_edge_set(static)
    
    if original_edges == static_edges:
        print("✓ Edge structure matches!")
    else:
        print("✗ Edge structure differs:")
        missing = original_edges - static_edges
        extra = static_edges - original_edges
        if missing:
            print(f"  Missing in static: {missing}")
        if extra:
            print(f"  Extra in static: {extra}")
    
    return original_labels == static_labels and original_edges == static_edges


def export_json():
    """Export the static flow to JSON."""
    flow = create_server_troubleshooting_flow_static()
    data = JsonSerializer.to_dict(flow)
    
    with open("build/static_complex_flow.json", "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Exported to build/static_complex_flow.json")
    return data


if __name__ == "__main__":
    # Compare the flows
    match = compare_flows()
    print()
    
    if match:
        print("SUCCESS: The flows are structurally identical!")
        export_json()
    else:
        print("FAILURE: The flows differ!")
