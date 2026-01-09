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
"""

import textwrap
from typing import Optional, Callable, List, Any
from dataclasses import dataclass, field
from contextlib import contextmanager

from flowly.core.ir import (
    FlowChart, Node as IRNode, StartNode, EndNode,
    ProcessNode, DecisionNode, Edge
)


# Registry for the current flow being built
_current_flow: Optional["FlowContext"] = None


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
        self._decision_stack: List[tuple[DecisionDef, str, bool]] = []  # (def, label, negated)

        # Loop context stack for tracking while loops (for continue/break)
        self._loop_stack: List[tuple[DecisionNode | None, DecisionDef | None, List]] = []  # (decision_node, decision_def, break_exits)

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
        source = textwrap.dedent(source)        # Parse AST
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

        # Set global context
        global _current_flow
        _current_flow = ctx

        try:
            # Process the function body
            self._process_statements(func_def.body, ctx)

            # Add end node if there are dangling exits
            if ctx._exits:
                end = EndNode(label="End")
                self.chart.add_node(end)
                ctx._connect_exits_to_target(end.id)
        finally:
            _current_flow = None
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
            func = self._closure_vars.get(func_name) or self._func.__globals__.get(func_name)

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
            return self._closure_vars.get(node.id) or self._func.__globals__.get(node.id)
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
        elif isinstance(while_stmt.test, ast.NameConstant) and while_stmt.test.value is True:
            # Python 3.7 compatibility
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
                    source_node = exit_node_or_def._get_node_for_target(self.chart, loop_node.id)
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
                    source_node = exit_node_or_def._get_node_for_target(self.chart, loop_node.id)
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
                source_node = exit_node_or_def._get_node_for_target(self.chart, decision_node.id)
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
                source_node = exit_node_or_def._get_node_for_target(self.chart, loop_node.id)
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
