"""
Demo of shared_nodes feature for AST-based flowcharts.

The shared_nodes=True option allows the same function call in multiple
places to connect to the SAME node, creating a true DAG with merge points.
"""

from flowly.frontend.ast_builder import flowchart
from flowly.backend.html import HtmlExporter
from flowly.core.serialization import JsonSerializer
import json


@flowchart(name="Server Troubleshooting (Shared Nodes)", shared_nodes=True)
def server_troubleshooting_shared():
    """
    Server troubleshooting with shared nodes.
    
    Same function calls like verify_fix() will connect to the same node,
    allowing multiple paths to merge at common points.
    """
    
    check_server_status()
    
    if is_server_down():
        ping_server()
        
        if ping_responds():
            attempt_ssh()  # First path to SSH
        else:
            check_power()
            power_cycle()
            
            if recovered():
                attempt_ssh()  # Second path to same SSH node!
            else:
                contact_datacenter()
                escalate_hardware()
                return
    else:
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
            
            if ddos():
                enable_mitigation()
            else:
                contact_isp()
                return
    
    # All paths that didn't return should verify the fix
    verify_fix()
    
    if fixed():
        incident_resolved()
    else:
        deep_dive()


@flowchart(name="Server Troubleshooting (Normal)", shared_nodes=False)
def server_troubleshooting_normal():
    """Same flow but without shared nodes - each call creates a new node."""
    
    check_server_status()
    
    if is_server_down():
        ping_server()
        
        if ping_responds():
            attempt_ssh()
        else:
            check_power()
            power_cycle()
            
            if recovered():
                attempt_ssh()  # This creates a SECOND node!
            else:
                contact_datacenter()
                escalate_hardware()
                return
    else:
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
            
            if ddos():
                enable_mitigation()
            else:
                contact_isp()
                return
    
    verify_fix()
    
    if fixed():
        incident_resolved()
    else:
        deep_dive()


def print_comparison():
    """Compare shared vs normal mode."""
    shared = server_troubleshooting_shared.flowchart
    normal = server_troubleshooting_normal.flowchart
    
    print("="*60)
    print("COMPARISON: shared_nodes=True vs shared_nodes=False")
    print("="*60)
    
    print(f"\nWith shared_nodes=True:")
    print(f"  Nodes: {len(shared.nodes)}")
    print(f"  Edges: {len(shared.edges)}")
    
    print(f"\nWith shared_nodes=False:")
    print(f"  Nodes: {len(normal.nodes)}")
    print(f"  Edges: {len(normal.edges)}")
    
    print(f"\nDifference: {len(normal.nodes) - len(shared.nodes)} fewer nodes with shared mode")
    
    # Show which nodes are shared
    shared_labels = [n.label for n in shared.nodes.values()]
    normal_labels = [n.label for n in normal.nodes.values()]
    
    # Count duplicates in normal mode
    from collections import Counter
    normal_counts = Counter(normal_labels)
    duplicates = {k: v for k, v in normal_counts.items() if v > 1}
    
    if duplicates:
        print(f"\nDuplicate nodes in normal mode (become shared in shared mode):")
        for label, count in duplicates.items():
            print(f"  - '{label}' appears {count} times")


if __name__ == "__main__":
    print_comparison()
    
    # Export both
    shared_html = HtmlExporter.to_html(server_troubleshooting_shared.flowchart)
    with open("build/ast_shared_nodes.html", "w") as f:
        f.write(shared_html)
    print(f"\nExported shared version to: build/ast_shared_nodes.html")
    
    normal_html = HtmlExporter.to_html(server_troubleshooting_normal.flowchart)
    with open("build/ast_normal_nodes.html", "w") as f:
        f.write(normal_html)
    print(f"Exported normal version to: build/ast_normal_nodes.html")
