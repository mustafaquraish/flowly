from flowly.frontend import FlowBuilder
from flowly.core.ir import FlowChart

def create_server_troubleshooting_flow() -> FlowChart:
    """
    Creates a complex flowchart representing a Server Troubleshooting Guide.
    
    Features:
    - Multiple branching depths
    - Loops (Retry logic)
    - Metadata usage
    - ~15+ nodes
    """
    b = FlowBuilder("Server Layout Inspection")
    
    # 1. Verification Phase
    start = b.start("Alert Received: High Latency", description="""
An automated alert has been triggered indicating **high latency** on one or more production servers.

## Initial Information
- Alert Source: Monitoring System (Datadog/PagerDuty)
- Severity: P2 (High)
- SLA: 30 minutes to acknowledge

## Checklist
- [ ] Note the timestamp of the alert
- [ ] Check if this is a recurring issue
- [ ] Identify affected services
""")
    
    check_status = b.action("Check Server Status Dashboard", description="""
Open the server status dashboard to get an overview of the system health.

## Key Metrics to Check
1. **CPU Usage**: Look for sustained >80% usage
2. **Memory**: Check for memory pressure or OOM events
3. **Disk I/O**: High iowait can cause latency
4. **Network**: Check for packet loss or high latency

## Tools
- Grafana: `https://grafana.internal/d/server-health`
- Datadog: Check the APM traces
""")
    b.connect(start, check_status)
    
    is_down = b.decision("Is Server Down?", description="""
Determine if the server is completely unreachable or just experiencing degraded performance.

**Down** = No response to health checks, SSH unavailable
**Up but slow** = Responds but with high latency
""")
    b.connect(check_status, is_down)
    
    # Branch A: Server is Down
    ping_check = b.action("Ping Server IP", description="""
Run a basic network connectivity test.

```bash
ping -c 5 <server_ip>
```

Look for:
- 100% packet loss = Network issue or server down
- High latency (>100ms) = Network congestion
""")
    b.connect(is_down, ping_check, label="Yes")
    
    is_pingable = b.decision("Ping Response?")
    b.connect(ping_check, is_pingable)
    
    # A.1: Hardware failure path
    check_power = b.action("Check Physical Power/LOM", description="""
Access the Lights-Out Management (LOM) interface to check physical server status.

## Steps
1. Log into iLO/DRAC/IPMI console
2. Check power status LED
3. Review hardware event logs
4. Check for any amber/red LEDs indicating failure
""")
    b.connect(is_pingable, check_power, label="No")
    
    power_cycle = b.action("Power Cycle", description="""
Perform a graceful power cycle through the LOM interface.

⚠️ **Warning**: This will cause a brief outage. Ensure:
- Change ticket is created
- Stakeholders are notified
- Failover is active (if applicable)
""")
    b.connect(check_power, power_cycle)
    
    did_recover = b.decision("Did it recover?")
    b.connect(power_cycle, did_recover)
    
    # Loop back if not recovered, but maybe with a limit (implicit)
    contact_dc = b.action("Contact Data Center Ops", description="""
Server did not recover after power cycle. This indicates a potential hardware failure.

**Contact**: DC Operations Team
**Phone**: +1-555-DC-HELP
**Ticket**: Create a DCOPS ticket with server details
""")
    b.connect(did_recover, contact_dc, label="No")
    
    escalate_hw = b.end("Escalate to Hardware Team", description="""
# Escalation Complete

The issue has been escalated to the Hardware Team for physical intervention.

**Expected Response Time**: 2-4 hours
**Next Steps**: Monitor the DCOPS ticket for updates
""")
    b.connect(contact_dc, escalate_hw)
    
    # A.2: OS/Network path
    ssh_attempt = b.action("Attempt SSH", description="""
Try to establish an SSH connection to the server.

```bash
ssh -o ConnectTimeout=10 admin@<server_ip>
```

If successful, proceed with OS-level diagnostics.
""")
    b.connect(is_pingable, ssh_attempt, label="Yes")
    b.connect(did_recover, ssh_attempt, label="Yes") # Recovered from power cycle
    
    # Branch B: Server is Up but Slow (High Latency)
    check_metrics = b.action("Check CPU/RAM Metrics", description="""
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
""")
    b.connect(is_down, check_metrics, label="No")
    
    high_load = b.decision("High CPU Load?", description="CPU usage consistently above 80%?")
    b.connect(check_metrics, high_load)
    
    # B.1: Application Issue
    top_proc = b.action("Identify Top Process", description="""
Identify which process is consuming the most resources.

```bash
ps aux --sort=-%cpu | head -10
```
""")
    b.connect(high_load, top_proc, label="Yes")
    
    is_known_app = b.decision("Is it main app?", description="Is the high-CPU process our application or something unexpected?")
    b.connect(top_proc, is_known_app)
    
    restart_service = b.action("Restart Service", description="""
Restart the application service:

```bash
systemctl restart myapp
```

Monitor logs for startup errors:
```bash
journalctl -u myapp -f
```
""")
    b.connect(is_known_app, restart_service, label="Yes")
    
    verify_fix = b.decision("Latency Normal?", description="Check if latency has returned to normal levels (<100ms p99)")
    b.connect(restart_service, verify_fix)
    
    resolved = b.end("Incident Resolved", description="""
# ✅ Incident Resolved

The issue has been resolved. Don't forget to:
1. Update the incident ticket
2. Write a brief post-mortem if needed
3. Thank the team!
""")
    b.connect(verify_fix, resolved, label="Yes")
    
    # B.2: Unknown Process / Security
    kill_proc = b.action("Kill Suspicious Process", description="""
⚠️ **Security Alert**: Unknown process consuming resources.

```bash
kill -9 <pid>
```

Preserve evidence before killing:
```bash
cat /proc/<pid>/cmdline
ls -la /proc/<pid>/exe
```
""")
    b.connect(is_known_app, kill_proc, label="No")
    
    security_audit = b.action("Flag for Security Audit", description="""
Create a security incident ticket with:
- Process details
- Network connections (`netstat -tulpn`)
- Recent logins (`last`)
- Modified files (`find / -mmin -60 -type f`)
""")
    b.connect(kill_proc, security_audit)
    b.connect(security_audit, verify_fix)
    
    # B.3: Network Issue (Low CPU)
    check_net = b.action("Check Network Bandwidth", description="""
Check network utilization:

```bash
iftop -i eth0
nethogs
```

Look for unusual traffic patterns or bandwidth saturation.
""")
    b.connect(high_load, check_net, label="No")
    
    ddos_check = b.decision("DDoS Attack?", description="Signs of DDoS: unusual traffic volume, many connections from same source")
    b.connect(check_net, ddos_check)
    
    enable_mitigation = b.action("Enable Mitigation", description="""
Enable DDoS mitigation:

1. Activate Cloudflare "Under Attack" mode
2. Enable rate limiting
3. Block suspicious IP ranges
4. Contact upstream provider if needed
""")
    b.connect(ddos_check, enable_mitigation, label="Yes")
    b.connect(enable_mitigation, verify_fix)
    
    isp_issue = b.end("Contact ISP / Upstream", description="""
Network issue appears to be upstream. Contact the ISP/network provider.

**ISP Support**: +1-555-ISP-HELP
**Circuit ID**: Check the network documentation
""")
    b.connect(ddos_check, isp_issue, label="No")
    
    # Loop from verify fix back to investigation if fail
    deep_dive = b.action("Deep Dive Logs", description="""
The initial fix didn't resolve the issue. Time for deep investigation:

1. Check application logs
2. Review recent deployments
3. Check for configuration changes
4. Analyze database slow query logs
""")
    b.connect(verify_fix, deep_dive, label="No")
    b.connect(deep_dive, escalate_hw) # Give up and escalate
    
    return b.build()

