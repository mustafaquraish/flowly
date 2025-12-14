"""
Demo of AST-based flowchart builder.

This shows how to write Python code that reads like pseudocode and
automatically generates a complete flowchart from static AST analysis.
"""

from flowly.frontend.ast_builder import flowchart
from flowly.backend.html import HtmlExporter


@flowchart
def simple_process():
    """A simple process with one decision."""
    check_input()
    
    if is_valid():
        process_data()
        save_result()
    else:
        log_error()
        notify_user()
    
    cleanup()


@flowchart
def login_flow():
    """User login flow with retry logic."""
    display_login_form()
    
    while not credentials_valid():
        show_error_message()
        get_new_credentials()
    
    create_session()
    redirect_to_dashboard()


@flowchart
def order_processing():
    """E-commerce order processing flow."""
    receive_order()
    validate_order()
    
    if payment_successful():
        if in_stock():
            reserve_inventory()
            create_shipment()
            send_confirmation()
        else:
            notify_backorder()
            add_to_waitlist()
    else:
        notify_payment_failed()
        cancel_order()
    
    update_analytics()


@flowchart(name="Server Troubleshooting")
def server_troubleshoot():
    """Server troubleshooting guide - similar to the complex flow."""
    check_server_status()
    
    if is_server_down():
        ping_server()
        
        if ping_responds():
            attempt_ssh()
        else:
            check_physical_power()
            power_cycle()
            
            if did_recover():
                attempt_ssh()
            else:
                contact_data_center()
                return  # Escalate to hardware team
    else:
        check_cpu_metrics()
        
        if high_cpu_load():
            identify_top_process()
            
            if is_main_app():
                restart_service()
            else:
                kill_suspicious_process()
                flag_for_security()
        else:
            check_network()
            
            if ddos_attack():
                enable_mitigation()
            else:
                contact_isp()
                return
    
    verify_fix()
    
    if latency_normal():
        close_incident()
    else:
        deep_dive_logs()


def print_flowchart(chart, name):
    """Print flowchart details."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"Nodes: {len(chart.nodes)}")
    for n in chart.nodes.values():
        print(f"  {type(n).__name__:15} {n.label}")
    
    print(f"\nEdges: {len(chart.edges)}")
    for e in chart.edges:
        src = chart.nodes[e.source_id].label[:25]
        tgt = chart.nodes[e.target_id].label[:25]
        lbl = f"--{e.label}-->" if e.label else "-->"
        print(f"  {src:25} {lbl:10} {tgt}")


if __name__ == "__main__":
    # Print all flowcharts
    print_flowchart(simple_process.flowchart, "Simple Process")
    print_flowchart(login_flow.flowchart, "Login Flow")
    print_flowchart(order_processing.flowchart, "Order Processing")
    print_flowchart(server_troubleshoot.flowchart, "Server Troubleshooting")
    
    # Export to HTML
    html = HtmlExporter.to_html(server_troubleshoot.flowchart)
    with open("build/ast_server_troubleshoot.html", "w") as f:
        f.write(html)
    print(f"\n\nExported server troubleshooting to build/ast_server_troubleshoot.html")
