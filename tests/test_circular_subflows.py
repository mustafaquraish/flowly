"""Test circular subflows with forward references."""

from flowly.frontend.dsl import Decision, Flow, Node, Subflow

# Define all decisions at module level
is_resolved = Decision("Issue fully resolved?")
is_complex = Decision("Is it a complex issue?")
needs_analysis = Decision("Needs deeper analysis?")
is_urgent = Decision("Is it urgent?")


@Subflow("Quick Fix")
def quick_fix(flow):
    flow.step("Apply known fix")
    flow.step("Verify fix worked")
    flow.end("Quick fix complete")


@Subflow("Resolve")
def resolve_issue(flow):
    flow.step("Implement solution")
    flow.step("Run validation tests")

    if is_resolved():
        flow.end("Resolution complete")
    else:
        analyze_issue()  # Circular reference back!


@Subflow("Escalate")
def escalate_issue(flow):
    flow.step("Contact senior engineer")
    flow.step("Document issue details")
    flow.step("Schedule review meeting")
    resolve_issue()


@Subflow("Analyze")
def analyze_issue(flow):
    flow.step("Gather logs and metrics")
    flow.step("Identify root cause")

    if is_complex():
        escalate_issue()  # Forward reference
    else:
        quick_fix()


@Subflow("Triage")
def triage_issue(flow):
    flow.step("Review incoming ticket")
    flow.step("Check for duplicates")

    if needs_analysis():
        analyze_issue()
    else:
        flow.step("Close as duplicate/invalid")
        flow.end("Triage complete")


@Flow("Support Workflow")
def support_workflow(flow):
    flow.step("Receive support request")

    if is_urgent():
        analyze_issue()
    else:
        triage_issue()

    flow.end("Workflow complete")


if __name__ == "__main__":
    print("Building multi_chart...")

    # Debug: check what's in _referenced_subflows for each flow
    print(f"\nMain flow ({support_workflow.name}) referenced subflows:")
    for sf in support_workflow._referenced_subflows:
        print(f"  - {sf.name}")
        if sf._flow_builder:
            print(
                f"    Flow builder subflows: {[s.name for s in sf._flow_builder._referenced_subflows]}"
            )

    mc = support_workflow.multi_chart
    print(f"\nSUCCESS! Got {len(mc.charts)} charts")
    for chart_id, chart in mc.charts.items():
        print(f"  - {chart.name}: {len(chart.nodes)} nodes, {len(chart.edges)} edges")
