"""
Explicit flowchart builder using Python control flow.

This module provides a way to define flowcharts using Python syntax
where all nodes are explicitly defined - no implicit magic.

Example:
    from flowly.frontend.dsl import Flow, Node, Decision

    # Define nodes with metadata
    check_input = Node("Check Input", description="Validate user input")
    process = Node("Process Data", description="Transform the data")
    error = Node("Handle Error", description="Log and notify")

    # Define decisions
    is_valid = Decision("Is input valid?")

    # Build the flow using Python control flow
    @Flow("My Process")
    def my_flow(flow):
        check_input()

        if is_valid():
            process()
        else:
            error()

        flow.step("Cleanup")  # Inline node for one-offs

    chart = my_flow.chart

Subflows with Circular References:
    The @Subflow decorator supports forward references and circular links.
    Definition order doesn't matter - you can reference a flow before it's defined.

    @Subflow("Process A")
    def process_a(flow):
        flow.step("Do A")
        process_b()  # Forward reference - works even though process_b defined later

    @Subflow("Process B")
    def process_b(flow):
        flow.step("Do B")
        process_a()  # Back reference - creates circular link

    @Flow("Main")
    def main_flow(flow):
        process_a()  # Enter the cycle
"""

import textwrap
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from flowly.core.ir import (
    DecisionNode,
    Edge,
    EndNode,
    FlowChart,
    MultiFlowChart,
    Node as IRNode,
    ProcessNode,
    StartNode,
    SubFlowNode as IRSubFlowNode,
)


# Registry for the current flow being built
_current_flow: Optional["FlowContext"] = None

# Global registry of all flow builders (for forward references)
# Maps function name -> SubflowBuilder (populated at decoration time)
_subflow_registry: Dict[str, "SubflowBuilder"] = {}

# Track which FlowBuilder is currently building (for subflow reference tracking)
_building_flow_builder: Optional["FlowBuilder"] = None


@dataclass
class NodeDef:
    """
    A node definition that can be called to add it to the current flow.

    Create nodes at module level, then call them inside a @Flow function.
    """

    label: str
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # Internal: the actual IR nodes (created when used - may be multiple if different outgoing edges needed)
    _ir_nodes: List[IRNode] = field(default_factory=list, repr=False)
    # Track which IR node is currently "active" for edge tracking
    _current_ir_node: Optional[IRNode] = field(default=None, repr=False)

    def __post_init__(self):
        if self.description:
            self.description = textwrap.dedent(self.description)

    def __call__(self) -> "NodeDef":
        """Add this node to the current flow."""
        if _current_flow is None:
            raise RuntimeError(
                f"Node '{self.label}' called outside of a @Flow function. "
                "Nodes can only be called inside a flow definition."
            )
        _current_flow._add_process_node(self)
        return self

    def _create_new_node(self, flowchart: FlowChart) -> ProcessNode:
        """Create a new IR node instance."""
        meta = dict(self.metadata)
        if self.description:
            meta["description"] = self.description
        node = ProcessNode(label=self.label, metadata=meta)
        flowchart.add_node(node)
        self._ir_nodes.append(node)
        return node

    def _get_node_for_target(self, flowchart: FlowChart, target_id: str) -> ProcessNode:
        """
        Get an IR node that can have an outgoing edge to target_id.

        If an existing node has no outgoing edges or already has an edge to target_id,
        return that node. Otherwise, create a new node.
        """
        for node in self._ir_nodes:
            # Check existing outgoing edges from this node
            outgoing = [e for e in flowchart.edges if e.source_id == node.id]
            if not outgoing:
                # No outgoing edges yet - this node can be used
                return node
            # Check if any edge already goes to target_id
            if any(e.target_id == target_id for e in outgoing):
                # Already has edge to this target - can reuse
                return node

        # No suitable existing node - create new one
        return self._create_new_node(flowchart)

    def _get_or_create_node(self, flowchart: FlowChart) -> ProcessNode:
        """Get an IR node without knowing the target yet. Used for initial placement."""
        if not self._ir_nodes:
            return self._create_new_node(flowchart)
        # Return the most recently created node (will be checked for conflicts later)
        return self._ir_nodes[-1]

    def _reset(self):
        """Reset for new flow building."""
        self._ir_nodes = []
        self._current_ir_node = None


@dataclass
class DecisionDef:
    """
    A decision node definition that can be called in if statements.

    Create decisions at module level, then use them in if/while inside @Flow.
    """

    label: str
    description: Optional[str] = None
    yes_label: str = "Yes"
    no_label: str = "No"
    metadata: dict = field(default_factory=dict)

    # Internal
    _ir_node: Optional[DecisionNode] = field(default=None, repr=False)

    def __post_init__(self):
        if self.description:
            self.description = textwrap.dedent(self.description)

    def __call__(self) -> bool:
        """
        Add this decision to the current flow.

        Returns True so it works in if statements (both branches are traced).
        """
        if _current_flow is None:
            raise RuntimeError(
                f"Decision '{self.label}' called outside of a @Flow function."
            )
        _current_flow._add_decision_node(self)
        # Return True - the actual branching is handled by AST analysis
        return True

    def _get_or_create_node(self, flowchart: FlowChart) -> DecisionNode:
        """Get the IR node, creating it if needed."""
        if self._ir_node is None:
            meta = dict(self.metadata)
            if self.description:
                meta["description"] = self.description
            self._ir_node = DecisionNode(label=self.label, metadata=meta)
            flowchart.add_node(self._ir_node)
        return self._ir_node

    def _reset(self):
        """Reset for new flow building."""
        self._ir_node = None


# Convenience aliases
Node = NodeDef
Decision = DecisionDef


class FlowContext:
    """
    Context for building a flow.

    This is passed to the flow function and provides methods for
    inline node creation and flow control.
    """

    def __init__(self, name: str, flowchart: FlowChart):
        self.name = name
        self.flowchart = flowchart

        # Track exits: list of (node, edge_label) that need to connect to next
        self._exits: List[tuple[IRNode, Optional[str]]] = []

        # Track nodes used in this flow (for reset)
        self._used_nodes: List[NodeDef | DecisionDef] = []

        # Decision context stack for tracking branches
        self._decision_stack: List[tuple[DecisionDef, str, bool]] = (
            []
        )  # (def, label, negated)

        # Loop context stack for tracking while loops (for continue/break)
        self._loop_stack: List[tuple[DecisionNode | None, DecisionDef | None, List]] = (
            []
        )  # (decision_node, decision_def, break_exits)

        # Track edges already created FROM a node to avoid duplicates from different branches
        # Key: (source_id, target_id), Value: edge_label
        self._created_edges: set[tuple[str, str]] = set()

    def _resolve_exit_node(self, exit_item: tuple, target_id: str) -> IRNode:
        """
        Resolve an exit item to the appropriate IR node for connecting to target_id.

        exit_item is either (IRNode, label) or (NodeDef, label).
        For NodeDef, we find or create an IR node that can have an edge to target_id.
        """
        exit_node_or_def, _ = exit_item

        if isinstance(exit_node_or_def, NodeDef):
            # This is a reusable node - find the right IR node for this target
            return exit_node_or_def._get_node_for_target(self.flowchart, target_id)
        else:
            # It's already an IR node
            return exit_node_or_def

    def _connect_exits_to_target(self, target_id: str) -> None:
        """Connect all current exits to a target node, resolving NodeDefs as needed."""
        for exit_item in self._exits:
            exit_node_or_def, edge_label = exit_item
            source_node = self._resolve_exit_node(exit_item, target_id)
            edge = Edge(source_node.id, target_id, label=edge_label)
            self.flowchart.add_edge(edge)

    def step(self, label: str, description: Optional[str] = None) -> ProcessNode:
        """
        Create an inline process node (for one-off steps).

        Use this when you don't need to reuse the node.
        """
        meta = {"description": textwrap.dedent(description)} if description else {}
        node = ProcessNode(label=label, metadata=meta)
        self.flowchart.add_node(node)

        # Connect from exits
        self._connect_exits_to_target(node.id)

        self._exits = [(node, None)]
        return node

    def decision(
        self,
        label: str,
        description: Optional[str] = None,
        yes_label: str = "Yes",
        no_label: str = "No",
    ) -> bool:
        """
        Create an inline decision node (for one-off decisions).

        Use this when you don't need to reuse the decision.
        Works just like Decision() but defined inline.

        Example:
            if flow.decision("Is valid?"):
                flow.step("Process")
            else:
                flow.step("Reject")
        """
        # Create an inline DecisionDef
        inline_decision = DecisionDef(
            label=label,
            description=description,
            yes_label=yes_label,
            no_label=no_label,
        )
        # Add the decision node to the flow
        self._add_decision_node(inline_decision)
        # Return True so it works in if statements
        return True

    def end(self, label: str = "End", description: Optional[str] = None) -> EndNode:
        """
        Create an explicit end node.

        Use this to terminate a branch.
        """
        meta = {"description": textwrap.dedent(description)} if description else {}
        node = EndNode(label=label, metadata=meta)
        self.flowchart.add_node(node)

        # Connect from exits
        self._connect_exits_to_target(node.id)

        self._exits = []  # End terminates the path
        return node

    def _add_process_node(self, node_def: NodeDef) -> None:
        """Add a process node to the flow."""
        ir_node = node_def._get_or_create_node(self.flowchart)
        node_def._current_ir_node = ir_node
        self._used_nodes.append(node_def)

        # Connect from exits
        self._connect_exits_to_target(ir_node.id)

        # Store the node_def itself in exits so we can resolve the correct IR node later
        self._exits = [(node_def, None)]

    def _add_decision_node(self, decision_def: DecisionDef) -> None:
        """Add a decision node to the flow."""
        ir_node = decision_def._get_or_create_node(self.flowchart)
        self._used_nodes.append(decision_def)

        # Connect from exits
        self._connect_exits_to_target(ir_node.id)

        # Decision clears exits - branches set them
        self._exits = []

        # Push to decision stack (def, label, negated=False)
        self._decision_stack.append((decision_def, decision_def.yes_label, False))


class FlowBuilder:
    """
    Decorator that builds a flowchart from a function using AST analysis.

    Usage:
        @Flow("My Flow")
        def my_flow(flow):
            # flow is a FlowContext with step(), end() methods
            ...

        chart = my_flow.chart
    """

    def __init__(self, name: str):
        self.name = name
        self.chart: Optional[FlowChart] = None
        self._func: Optional[Callable] = None
        self._referenced_subflows: List["SubflowBuilder"] = []

    def __call__(self, func: Callable) -> "FlowBuilder":
        """Decorate the flow function."""
        self._func = func
        self._closure_vars = self._capture_closure(func)
        self._build()
        return self

    def _capture_closure(self, func: Callable) -> dict:
        """Capture closure variables from the function."""
        import inspect

        closure_vars = {}

        # Get variables from closure (captured from enclosing scope)
        if func.__closure__ and func.__code__.co_freevars:
            for name, cell in zip(func.__code__.co_freevars, func.__closure__):
                try:
                    closure_vars[name] = cell.cell_contents
                except ValueError:
                    # Cell is empty
                    pass

        # Also look up the call stack for locals where decorator was applied
        # This handles the case where nodes are defined in the same function
        # that contains the flow function
        frame = inspect.currentframe()
        try:
            # Go up the call stack to find the frame where @Flow was applied
            # Frame 0: _capture_closure
            # Frame 1: __call__
            # Frame 2: Module/function where decorator is applied
            for _ in range(10):  # Safety limit
                frame = frame.f_back
                if frame is None:
                    break
                # Check if this frame has our nodes
                for name, value in frame.f_locals.items():
                    if isinstance(value, (NodeDef, DecisionDef)):
                        if name not in closure_vars:
                            closure_vars[name] = value
        finally:
            del frame

        return closure_vars

    def _build(self) -> None:
        """Build the flowchart using AST analysis."""
        import ast
        import inspect
        import textwrap

        # Get source
        source = inspect.getsource(self._func)
        source = textwrap.dedent(source)  # Parse AST
        tree = ast.parse(source)
        func_def = tree.body[0]

        if not isinstance(func_def, ast.FunctionDef):
            raise ValueError("Expected a function definition")

        # Create flowchart and context
        self.chart = FlowChart(self.name)
        ctx = FlowContext(self.name, self.chart)

        # Create start node
        start = StartNode(label=self.name)
        self.chart.add_node(start)
        ctx._exits = [(start, None)]

        # Save previous context for nested builds (e.g., when subflow A builds subflow B)
        global _current_flow, _building_flow_builder
        prev_flow = _current_flow
        prev_builder = _building_flow_builder
        
        # Set global contexts for flow building and subflow tracking
        _current_flow = ctx
        _building_flow_builder = self

        try:
            # Process the function body
            self._process_statements(func_def.body, ctx)

            # Add end node if there are dangling exits
            if ctx._exits:
                end = EndNode(label="End")
                self.chart.add_node(end)
                ctx._connect_exits_to_target(end.id)
        finally:
            # Restore previous context (important for nested builds)
            _current_flow = prev_flow
            _building_flow_builder = prev_builder
            # Reset all used nodes for potential reuse
            for node in ctx._used_nodes:
                node._reset()

    def _process_statements(self, stmts: List, ctx: FlowContext) -> None:
        """Process a list of statements."""
        for stmt in stmts:
            self._process_statement(stmt, ctx)

    def _process_statement(self, stmt, ctx: FlowContext) -> None:
        """Process a single statement."""
        import ast

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            # Function call - execute it
            self._execute_call(stmt.value, ctx)

        elif isinstance(stmt, ast.If):
            self._process_if(stmt, ctx)

        elif isinstance(stmt, ast.While):
            self._process_while(stmt, ctx)

        elif isinstance(stmt, ast.Continue):
            self._process_continue(stmt, ctx)

        elif isinstance(stmt, ast.Break):
            self._process_break(stmt, ctx)

        elif isinstance(stmt, ast.Return):
            # Check if returning a call like `return flow.end("Failed")`
            if stmt.value is not None and isinstance(stmt.value, ast.Call):
                self._execute_call(stmt.value, ctx)
            # Return = end this path (clear exits so no End node is auto-added)
            ctx._exits = []

        elif isinstance(stmt, ast.Pass):
            pass

    def _execute_call(self, call, ctx: FlowContext) -> Any:
        """Execute a function call in the flow context."""
        import ast

        # Get the function object
        if isinstance(call.func, ast.Name):
            # Simple name - look up in closure vars first, then function's globals
            func_name = call.func.id
            func = self._closure_vars.get(func_name) or self._func.__globals__.get(
                func_name
            )

            if func is None:
                raise NameError(
                    f"Node or function '{func_name}' is not defined. "
                    f"Define it with: {func_name} = Node(\"{func_name.replace('_', ' ').title()}\")"
                )

            if isinstance(func, (NodeDef, DecisionDef)):
                func()
            elif callable(func):
                # Regular function - might be flow.step() or similar
                # Evaluate args and call
                args = [self._eval_arg(a, ctx) for a in call.args]
                kwargs = {kw.arg: self._eval_arg(kw.value, ctx) for kw in call.keywords}
                return func(*args, **kwargs)

        elif isinstance(call.func, ast.Attribute):
            # Method call like flow.step()
            if isinstance(call.func.value, ast.Name) and call.func.value.id == "flow":
                method_name = call.func.attr
                method = getattr(ctx, method_name, None)

                if method is None:
                    raise AttributeError(f"FlowContext has no method '{method_name}'")

                args = [self._eval_arg(a, ctx) for a in call.args]
                kwargs = {kw.arg: self._eval_arg(kw.value, ctx) for kw in call.keywords}
                return method(*args, **kwargs)

    def _eval_arg(self, node, ctx: FlowContext) -> Any:
        """Evaluate an AST node to get its value."""
        import ast

        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            # Check closure vars first, then globals
            return self._closure_vars.get(node.id) or self._func.__globals__.get(
                node.id
            )
        elif isinstance(node, ast.Str):  # Python 3.7 compat
            return node.s
        else:
            # For complex expressions, use ast.literal_eval or return None
            try:
                return ast.literal_eval(node)
            except:
                return None

    def _process_if(self, if_stmt, ctx: FlowContext) -> None:
        """Process an if statement."""
        import ast

        # Check if the condition is negated
        negated = False
        test_expr = if_stmt.test

        if isinstance(test_expr, ast.UnaryOp) and isinstance(test_expr.op, ast.Not):
            negated = True
            test_expr = test_expr.operand

        # Execute the condition (should be a Decision call)
        if isinstance(test_expr, ast.Call):
            self._execute_call(test_expr, ctx)

        # Get the decision from the stack
        if not ctx._decision_stack:
            raise RuntimeError("If statement without a Decision call in condition")

        decision_def, _, _ = ctx._decision_stack.pop()
        decision_node = decision_def._ir_node

        # Determine branch labels based on negation
        if negated:
            # `if not cond()` - body is the "No" branch, else is the "Yes" branch
            body_label = decision_def.no_label
            else_label = decision_def.yes_label
        else:
            # Normal `if cond()` - body is the "Yes" branch, else is the "No" branch
            body_label = decision_def.yes_label
            else_label = decision_def.no_label

        # Save exits for merging later
        all_exits = []

        # Process "if" body
        ctx._exits = [(decision_node, body_label)]
        self._process_statements(if_stmt.body, ctx)
        all_exits.extend(ctx._exits)

        # Process "else" body
        if if_stmt.orelse:
            ctx._exits = [(decision_node, else_label)]

            if len(if_stmt.orelse) == 1 and isinstance(if_stmt.orelse[0], ast.If):
                # elif
                self._process_if(if_stmt.orelse[0], ctx)
            else:
                self._process_statements(if_stmt.orelse, ctx)

            all_exits.extend(ctx._exits)
        else:
            # No else - other path continues
            all_exits.append((decision_node, else_label))

        # Merge exits
        ctx._exits = all_exits

    def _process_while(self, while_stmt, ctx: FlowContext) -> None:
        """Process a while loop."""
        import ast

        # Check for `while True` (infinite loop)
        is_infinite_loop = False
        if isinstance(while_stmt.test, ast.Constant) and while_stmt.test.value is True:
            is_infinite_loop = True
        elif hasattr(ast, "NameConstant") and isinstance(
            while_stmt.test, ast.NameConstant
        ):
            # Python 3.7 compatibility (ast.NameConstant deprecated in 3.8+)
            if while_stmt.test.value is True:
                is_infinite_loop = True

        if is_infinite_loop:
            # `while True` - create an implicit decision node for the loop point
            # This allows continue statements to loop back
            loop_node = ProcessNode(label="(loop)")
            self.chart.add_node(loop_node)

            # Connect current exits to loop node, resolving NodeDefs
            for exit_item in ctx._exits:
                exit_node_or_def, edge_label = exit_item
                if isinstance(exit_node_or_def, NodeDef):
                    source_node = exit_node_or_def._get_node_for_target(
                        self.chart, loop_node.id
                    )
                else:
                    source_node = exit_node_or_def
                edge = Edge(source_node.id, loop_node.id, label=edge_label)
                self.chart.add_edge(edge)

            # Push loop context (no decision node, no decision def, empty break_exits list)
            break_exits: List[tuple[IRNode, Optional[str]]] = []
            ctx._loop_stack.append((loop_node, None, break_exits))

            # Process loop body
            ctx._exits = [(loop_node, None)]
            self._process_statements(while_stmt.body, ctx)

            # Back-edge to loop node (for any exits that didn't hit break), resolving NodeDefs
            for exit_item in ctx._exits:
                exit_node_or_def, _ = exit_item
                if isinstance(exit_node_or_def, NodeDef):
                    source_node = exit_node_or_def._get_node_for_target(
                        self.chart, loop_node.id
                    )
                else:
                    source_node = exit_node_or_def
                edge = Edge(source_node.id, loop_node.id)
                self.chart.add_edge(edge)

            # Pop loop context
            ctx._loop_stack.pop()

            # Exits are from break statements only
            ctx._exits = break_exits
            return

        # Check if the condition is negated
        negated = False
        test_expr = while_stmt.test

        if isinstance(test_expr, ast.UnaryOp) and isinstance(test_expr.op, ast.Not):
            negated = True
            test_expr = test_expr.operand

        # Execute the condition (should be a Decision call)
        if isinstance(test_expr, ast.Call):
            self._execute_call(test_expr, ctx)

        if not ctx._decision_stack:
            raise RuntimeError("While statement without a Decision call in condition")

        decision_def, _, _ = ctx._decision_stack.pop()
        decision_node = decision_def._ir_node

        # Determine branch labels based on negation
        if negated:
            # `while not cond()` - body is the "No" branch, exit is the "Yes" branch
            body_label = decision_def.no_label
            exit_label = decision_def.yes_label
        else:
            # Normal `while cond()` - body is the "Yes" branch, exit is the "No" branch
            body_label = decision_def.yes_label
            exit_label = decision_def.no_label

        # Push loop context for continue/break handling
        break_exits: List[tuple[IRNode, Optional[str]]] = []
        ctx._loop_stack.append((decision_node, decision_def, break_exits))

        # Process loop body
        ctx._exits = [(decision_node, body_label)]
        self._process_statements(while_stmt.body, ctx)

        # Back-edge to decision (for any exits that didn't hit break/continue)
        # Need to resolve NodeDefs when adding back-edges
        for exit_item in ctx._exits:
            exit_node_or_def, _ = exit_item
            if isinstance(exit_node_or_def, NodeDef):
                source_node = exit_node_or_def._get_node_for_target(
                    self.chart, decision_node.id
                )
            else:
                source_node = exit_node_or_def
            edge = Edge(source_node.id, decision_node.id)
            self.chart.add_edge(edge)

        # Pop loop context
        ctx._loop_stack.pop()

        # Exit: from decision's exit branch + any break exits
        ctx._exits = [(decision_node, exit_label)] + break_exits

    def _process_continue(self, cont_stmt, ctx: FlowContext) -> None:
        """Process a continue statement."""
        if not ctx._loop_stack:
            raise RuntimeError("continue statement outside of a while loop")

        loop_node, decision_def, _ = ctx._loop_stack[-1]

        # Connect current exits to the loop decision node, resolving NodeDefs
        for exit_item in ctx._exits:
            exit_node_or_def, edge_label = exit_item
            if isinstance(exit_node_or_def, NodeDef):
                source_node = exit_node_or_def._get_node_for_target(
                    self.chart, loop_node.id
                )
            else:
                source_node = exit_node_or_def
            edge = Edge(source_node.id, loop_node.id, label=edge_label)
            self.chart.add_edge(edge)

        # Clear exits - continue redirects flow back to the loop
        ctx._exits = []

    def _process_break(self, break_stmt, ctx: FlowContext) -> None:
        """Process a break statement."""
        if not ctx._loop_stack:
            raise RuntimeError("break statement outside of a while loop")

        _, _, break_exits = ctx._loop_stack[-1]

        # Save current exits to break_exits - they will be processed after the loop
        break_exits.extend(ctx._exits)

        # Clear exits - break redirects flow out of the loop
        ctx._exits = []


# Main decorator
Flow = FlowBuilder


# Add multi_chart property to FlowBuilder
@property
def _multi_chart(self: FlowBuilder) -> MultiFlowChart:
    """
    Get a MultiFlowChart containing this flow and all referenced subflows.

    This recursively collects all subflows that are referenced (directly or indirectly)
    from this flow and creates a MultiFlowChart with them.
    """
    if self.chart is None:
        raise RuntimeError("FlowBuilder has not been built yet")

    multi = MultiFlowChart(self.name)
    multi.add_chart(self.chart, is_main=True)

    # Recursively collect all referenced subflows
    collected: Set["SubflowBuilder"] = set()

    def collect_subflows(flow_builder: FlowBuilder) -> None:
        for subflow in flow_builder._referenced_subflows:
            if subflow not in collected:
                collected.add(subflow)
                if subflow.chart:
                    multi.add_chart(subflow.chart, is_main=False)
                    # Recursively collect subflows from this subflow
                    if subflow._flow_builder:
                        collect_subflows(subflow._flow_builder)

    collect_subflows(self)
    
    # Fix any SubFlowNodes with missing targetChartId (can happen with circular references)
    # Build a map of subflow name -> chart_id for resolution
    name_to_chart_id: Dict[str, str] = {}
    for chart_id, chart in multi.charts.items():
        name_to_chart_id[chart.name] = chart_id
    
    # Now fix any SubFlowNodes with None targetChartId
    for chart_id, chart in multi.charts.items():
        for node in chart.nodes.values():
            if isinstance(node, IRSubFlowNode) and node.target_chart_id is None:
                # Resolve by name
                if node.label in name_to_chart_id:
                    node.target_chart_id = name_to_chart_id[node.label]
    
    return multi


# Monkey-patch the property onto FlowBuilder
FlowBuilder.multi_chart = _multi_chart


@dataclass
class _SubFlowDef:
    """
    Internal subflow node definition used by SubflowBuilder.

    This is not part of the public API - use @Subflow decorator instead.
    """

    label: str
    target: Optional["FlowBuilder"] = None
    target_chart_id: Optional[str] = None
    subflow_builder: Optional["SubflowBuilder"] = None  # For lazy chart ID resolution
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # Internal
    _ir_node: Optional[IRSubFlowNode] = field(default=None, repr=False)

    def __post_init__(self):
        if self.description:
            self.description = textwrap.dedent(self.description)

    def _get_target_chart_id(self) -> Optional[str]:
        """Get the target chart ID from either direct ID or from FlowBuilder or SubflowBuilder."""
        if self.target_chart_id:
            return self.target_chart_id
        if self.target and self.target.chart:
            return self.target.chart.id
        # Lazy resolution from SubflowBuilder (handles circular references)
        if self.subflow_builder:
            self.subflow_builder._ensure_built()
            if self.subflow_builder.chart:
                return self.subflow_builder.chart.id
        return None

    def _get_or_create_node(self, flowchart: FlowChart) -> IRSubFlowNode:
        """Get the IR node, creating it if needed."""
        if self._ir_node is None:
            meta = dict(self.metadata)
            if self.description:
                meta["description"] = self.description
            self._ir_node = IRSubFlowNode(
                label=self.label,
                target_chart_id=self._get_target_chart_id(),
                metadata=meta,
            )
            flowchart.add_node(self._ir_node)
        return self._ir_node

    def _reset(self):
        """Reset for new flow building."""
        self._ir_node = None


class SubflowBuilder:
    """
    Decorator that creates a subflow which can be called directly from other flows.

    This provides a cleaner API than manually creating SubFlow nodes - simply
    decorate a flow function with @Subflow and call it like a function from
    within another @Flow function.

    Forward References & Circular Links:
        Subflows can reference each other regardless of definition order.
        The chart is built lazily on first use, allowing circular references.

        @Subflow("Flow A")
        def flow_a(flow):
            flow.step("In A")
            flow_b()  # Forward reference - flow_b defined later

        @Subflow("Flow B")
        def flow_b(flow):
            flow.step("In B")
            flow_a()  # Back reference - creates circular link

    Usage:
        @Subflow("Triage Flow")
        def triage_flow(flow):
            flow.step("Assess severity")
            flow.step("Route to team")

        @Flow("Main Flow")
        def main_flow(flow):
            flow.step("Identify problem")
            triage_flow()  # Creates a SubFlowNode linking to triage_flow

        # Auto-combine all referenced subflows
        multi = main_flow.multi_chart

    When triage_flow() is called inside main_flow, it:
    1. Creates a SubFlowNode with label "Triage Flow"
    2. Links it to triage_flow's chart
    3. Registers triage_flow in main_flow's referenced subflows

    The multi_chart property returns a MultiFlowChart with all referenced subflows.
    """

    def __init__(self, name: str):
        self.name = name
        self.chart: Optional[FlowChart] = None
        self._func: Optional[Callable] = None
        self._flow_builder: Optional[FlowBuilder] = None
        self._decorated: bool = False
        self._building: bool = False  # Guard against recursive builds
        self._func_name: Optional[str] = None  # For forward reference lookup

    def __call__(self, func_or_nothing: Optional[Callable] = None) -> "SubflowBuilder":
        """
        Handle both decoration and invocation.

        When used as @Subflow("name"), receives the function to decorate.
        When used as subflow_name() inside a @Flow, invokes as a subflow link.
        """
        if not self._decorated:
            # First call - decorating a function
            if func_or_nothing is None:
                raise TypeError(
                    f"@Subflow('{self.name}') must be used to decorate a function"
                )
            self._func = func_or_nothing
            self._func_name = func_or_nothing.__name__
            self._decorated = True
            
            # Register in global registry for forward reference resolution
            _subflow_registry[self._func_name] = self
            
            # DON'T build yet - defer until first use
            # This allows forward references between subflows
            return self
        else:
            # Subsequent call - invoking as a subflow link
            self._invoke()
            return self

    def _ensure_built(self) -> None:
        """Build the chart if not already built. Handles circular references."""
        if self.chart is not None:
            return  # Already built
        
        if self._building:
            # We're in a circular reference - the chart will be set after build
            return
        
        if self._func is None:
            raise RuntimeError(f"Subflow '{self.name}' has no function defined")
        
        self._building = True
        try:
            self._flow_builder = FlowBuilder(self.name)(self._func)
            self.chart = self._flow_builder.chart
        finally:
            self._building = False

    def _invoke(self) -> None:
        """
        Invoke this subflow from within another flow.

        This is called when the subflow is used like a function: subflow_name()
        It creates a SubFlowNode in the current flow that links to this subflow's chart.
        """
        if _current_flow is None:
            raise RuntimeError(
                f"Subflow '{self.name}' called outside of a @Flow function. "
                "Subflows can only be called inside a flow definition."
            )

        # Ensure the subflow chart is built (lazy build)
        self._ensure_built()

        # Create an internal subflow definition
        # Store subflow_builder for lazy chart ID resolution (handles circular references)
        subflow_def = _SubFlowDef(
            label=self.name,
            target=self._flow_builder,
            target_chart_id=self.chart.id if self.chart else None,
            subflow_builder=self,  # For lazy resolution if chart_id is None
        )

        # Add the subflow node to current flow
        _current_flow._add_subflow_node(subflow_def)

        # Register this subflow as referenced by the parent flow
        _register_subflow_reference(_current_flow, self)

    def __repr__(self) -> str:
        return f"SubflowBuilder(name={self.name!r})"


# Alias for @Subflow decorator
Subflow = SubflowBuilder


# Registry to track which FlowBuilder is currently building
_building_flow_builder: Optional[FlowBuilder] = None


def _register_subflow_reference(ctx: FlowContext, subflow: SubflowBuilder) -> None:
    """Register a subflow reference with the current flow being built."""
    global _building_flow_builder
    if _building_flow_builder is not None:
        if subflow not in _building_flow_builder._referenced_subflows:
            _building_flow_builder._referenced_subflows.append(subflow)


# Add SubFlow support to FlowContext
def _add_subflow_node(self: FlowContext, subflow_def: _SubFlowDef) -> None:
    """Add a subflow node to the flow."""
    ir_node = subflow_def._get_or_create_node(self.flowchart)
    self._used_nodes.append(subflow_def)

    # Connect from exits
    self._connect_exits_to_target(ir_node.id)

    # SubFlow node becomes the new exit
    self._exits = [(ir_node, None)]


# Monkey-patch the method onto FlowContext
FlowContext._add_subflow_node = _add_subflow_node
