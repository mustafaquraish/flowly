"""
Server troubleshooting flow using AST-based flowchart builder.

This demonstrates how to write pseudocode-style Python that automatically
generates a flowchart through static AST analysis.
"""

from flowly.frontend.ast_builder import flowchart
from flowly.backend.html import HtmlExporter
from flowly.core.serialization import JsonSerializer
import json


@flowchart(name="Server Troubleshooting Guide")
def server_troubleshooting():
    """
    Server troubleshooting guide written as pseudocode.
    
    The @flowchart decorator will parse this function's AST
    and build a complete flowchart with all branches.
    """
    
    # Initial triage
    check_server_status_dashboard()
    
    if is_server_down():
        # Server is completely down
        ping_server_ip()
        
        if ping_responds():
            # Network is fine, try SSH
            attempt_ssh()
            check_os_level_issues()
        else:
            # No ping response - hardware issue likely
            check_physical_power_lom()
            power_cycle_server()
            
            if server_recovered():
                attempt_ssh()
                check_os_level_issues()
            else:
                contact_data_center_ops()
                escalate_to_hardware_team()
                return  # End this path
    else:
        # Server is up but slow
        check_cpu_ram_metrics()
        
        if high_cpu_load():
            identify_top_process()
            
            if is_main_application():
                restart_service()
            else:
                # Unknown process - security concern
                kill_suspicious_process()
                flag_for_security_audit()
        else:
            # Not CPU - check network
            check_network_bandwidth()
            
            if ddos_attack_detected():
                enable_ddos_mitigation()
            else:
                # Upstream network issue
                contact_isp()
                return  # End this path
    
    # Verify the fix worked
    verify_latency_normal()
    
    if latency_is_normal():
        mark_incident_resolved()
    else:
        deep_dive_into_logs()
        escalate_to_senior_engineer()


def print_chart_stats(chart, name):
    """Print statistics about the chart."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    
    from flowly.core.ir import StartNode, EndNode, ProcessNode, DecisionNode
    
    starts = sum(1 for n in chart.nodes.values() if isinstance(n, StartNode))
    ends = sum(1 for n in chart.nodes.values() if isinstance(n, EndNode))
    processes = sum(1 for n in chart.nodes.values() if isinstance(n, ProcessNode))
    decisions = sum(1 for n in chart.nodes.values() if isinstance(n, DecisionNode))
    
    print(f"Total nodes: {len(chart.nodes)}")
    print(f"  - Start nodes: {starts}")
    print(f"  - End nodes: {ends}")
    print(f"  - Process nodes: {processes}")
    print(f"  - Decision nodes: {decisions}")
    print(f"Total edges: {len(chart.edges)}")
    

def compare_with_original():
    """Compare the AST-generated flow with the original manual one."""
    import sys
    sys.path.insert(0, "/Users/mustafa/dev/flowly")
    from tests.complex_flow import create_server_troubleshooting_flow
    
    original = create_server_troubleshooting_flow()
    ast_flow = server_troubleshooting.flowchart
    
    print("\n" + "="*60)
    print("  COMPARISON: Original vs AST-generated")
    print("="*60)
    
    print(f"\nOriginal flow:")
    print(f"  - Nodes: {len(original.nodes)}")
    print(f"  - Edges: {len(original.edges)}")
    
    print(f"\nAST-generated flow:")
    print(f"  - Nodes: {len(ast_flow.nodes)}")
    print(f"  - Edges: {len(ast_flow.edges)}")
    
    print(f"\nNote: The AST flow may differ because:")
    print(f"  - It uses structured if/else which requires branches to merge")
    print(f"  - The original has some cross-connections (ssh_attempt reachable")
    print(f"    from multiple paths) that require explicit connect() calls")
    print(f"  - The AST approach is great for structured flows but complex")
    print(f"    graphs with arbitrary cross-connections need the manual builder")


if __name__ == "__main__":
    chart = server_troubleshooting.flowchart
    
    print_chart_stats(chart, "Server Troubleshooting (AST-generated)")
    
    # Export to HTML
    html = HtmlExporter.to_html(chart)
    with open("build/ast_server_troubleshoot.html", "w") as f:
        f.write(html)
    print(f"\nExported to: build/ast_server_troubleshoot.html")
    
    # Export to JSON
    data = JsonSerializer.to_dict(chart)
    with open("build/ast_server_troubleshoot.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Exported to: build/ast_server_troubleshoot.json")
    
    # Compare with original
    compare_with_original()
