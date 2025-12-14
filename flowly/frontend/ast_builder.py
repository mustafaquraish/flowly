"""
Static AST-based flowchart builder.

This module analyzes Python function AST to build flowcharts from code
that reads like pseudocode. It extracts control flow (if/else, while, for)
and function calls to create a complete flowchart with all branches.

Example:
    from flowly.frontend.ast_builder import flowchart
    
    @flowchart
    def my_process():
        step_one()
        
        if condition_check():
            do_this()
        else:
            do_that()
        
        final_step()
    
    # Get the flowchart
    chart = my_process.flowchart
"""

import ast
import inspect
import textwrap
from typing import Optional, List, Set, Callable, Any
from dataclasses import dataclass, field

from flowly.core.ir import (
    FlowChart, Node, StartNode, EndNode, ProcessNode, DecisionNode, Edge
)


@dataclass
class ASTFlowBuilder:
    """Builds a FlowChart from Python AST."""
    
    name: str
    flowchart: FlowChart = field(default_factory=lambda: None)
    _node_counter: int = field(default=0)
    
    # Track current connection points (nodes that need to connect to the next node)
    _current_exits: List[tuple[Node, Optional[str]]] = field(default_factory=list)
    
    # Track named nodes for goto/shared semantics
    _named_nodes: dict = field(default_factory=dict)
    
    # Mode: if True, same function name reuses node (goto semantics)
    shared_nodes: bool = field(default=False)
    
    def __post_init__(self):
        self.flowchart = FlowChart(self.name)
    
    def _add_node(self, node: Node) -> Node:
        """Add a node and connect from current exits."""
        self.flowchart.add_node(node)
        
        # Connect from all current exit points
        for exit_node, label in self._current_exits:
            edge = Edge(exit_node.id, node.id, label=label)
            self.flowchart.add_edge(edge)
        
        # This node becomes the new exit point
        self._current_exits = [(node, None)]
        return node
    
    def _add_decision(self, node: DecisionNode) -> DecisionNode:
        """Add a decision node (doesn't set as exit - branches do that)."""
        self.flowchart.add_node(node)
        
        # Connect from all current exit points
        for exit_node, label in self._current_exits:
            edge = Edge(exit_node.id, node.id, label=label)
            self.flowchart.add_edge(edge)
        
        # Clear exits - branches will set their own
        self._current_exits = []
        return node
    
    def build_from_function(self, func: Callable) -> FlowChart:
        """Build a flowchart from a function's AST."""
        # Get source code
        source = inspect.getsource(func)
        source = textwrap.dedent(source)
        
        # Parse AST
        tree = ast.parse(source)
        func_def = tree.body[0]
        
        if not isinstance(func_def, ast.FunctionDef):
            raise ValueError("Expected a function definition")
        
        # Create start node
        start_label = self._format_name(func_def.name)
        start = StartNode(label=start_label)
        self.flowchart.add_node(start)
        self._current_exits = [(start, None)]
        
        # Process function body
        self._process_statements(func_def.body)
        
        # Add end node if there are dangling exits
        if self._current_exits:
            end = EndNode(label="End")
            self._add_node(end)
        
        return self.flowchart
    
    def _process_statements(self, stmts: List[ast.stmt]) -> None:
        """Process a list of statements."""
        for stmt in stmts:
            self._process_statement(stmt)
    
    def _process_statement(self, stmt: ast.stmt) -> None:
        """Process a single statement."""
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            # Function call as statement: step()
            self._process_call(stmt.value)
        
        elif isinstance(stmt, ast.If):
            self._process_if(stmt)
        
        elif isinstance(stmt, ast.While):
            self._process_while(stmt)
        
        elif isinstance(stmt, ast.For):
            self._process_for(stmt)
        
        elif isinstance(stmt, ast.Return):
            self._process_return(stmt)
        
        elif isinstance(stmt, ast.Pass):
            # Skip pass statements
            pass
        
        elif isinstance(stmt, ast.Assign):
            # Variable assignment - could be treated as action
            self._process_assign(stmt)
        
        elif isinstance(stmt, ast.With):
            # With statement - process the body
            self._process_statements(stmt.body)
        
        # Other statement types can be added as needed
    
    def _get_call_key(self, call: ast.Call) -> str:
        """Get a unique key for a function call (used for shared nodes)."""
        if isinstance(call.func, ast.Name):
            return call.func.id
        elif isinstance(call.func, ast.Attribute):
            return f"{self._expr_to_label(call.func.value)}.{call.func.attr}"
        return self._call_to_label(call)
    
    def _process_call(self, call: ast.Call) -> None:
        """Process a function call as a process node."""
        label = self._call_to_label(call)
        
        if self.shared_nodes:
            # Check if we've seen this function before
            key = self._get_call_key(call)
            if key in self._named_nodes:
                # Connect to existing node instead of creating new one
                existing_node = self._named_nodes[key]
                for exit_node, edge_label in self._current_exits:
                    edge = Edge(exit_node.id, existing_node.id, label=edge_label)
                    self.flowchart.add_edge(edge)
                # The existing node becomes our exit
                self._current_exits = [(existing_node, None)]
                return
        
        node = ProcessNode(label=label)
        self._add_node(node)
        
        if self.shared_nodes:
            # Register this node for future references
            key = self._get_call_key(call)
            self._named_nodes[key] = node
    
    def _process_if(self, if_stmt: ast.If) -> None:
        """Process an if statement as a decision node."""
        # Create decision node from condition
        condition = self._expr_to_label(if_stmt.test)
        decision = DecisionNode(label=condition)
        self._add_decision(decision)
        
        # Track all exits from branches
        all_exits: List[tuple[Node, Optional[str]]] = []
        
        # Process "if" body (Yes branch)
        self._current_exits = [(decision, "Yes")]
        self._process_statements(if_stmt.body)
        # Collect exits from if-body (unless it ended with return/end)
        all_exits.extend(self._current_exits)
        
        # Process "else" body (No branch)
        if if_stmt.orelse:
            self._current_exits = [(decision, "No")]
            
            # Check if it's an elif (else with single if)
            if len(if_stmt.orelse) == 1 and isinstance(if_stmt.orelse[0], ast.If):
                # elif - process as nested if
                self._process_if(if_stmt.orelse[0])
            else:
                # Regular else
                self._process_statements(if_stmt.orelse)
            
            all_exits.extend(self._current_exits)
        else:
            # No else - decision's "No" path continues directly
            all_exits.append((decision, "No"))
        
        # Merge all exits
        self._current_exits = all_exits
    
    def _process_while(self, while_stmt: ast.While) -> None:
        """Process a while loop as a decision with back-edge."""
        # Create decision node from condition
        condition = self._expr_to_label(while_stmt.test)
        decision = DecisionNode(label=condition)
        self._add_decision(decision)
        
        # Process loop body (Yes/continue branch)
        self._current_exits = [(decision, "Yes")]
        self._process_statements(while_stmt.body)
        
        # Back-edge: end of loop body connects back to decision
        for exit_node, _ in self._current_exits:
            edge = Edge(exit_node.id, decision.id)
            self.flowchart.add_edge(edge)
        
        # Exit: No branch continues after loop
        self._current_exits = [(decision, "No")]
    
    def _process_for(self, for_stmt: ast.For) -> None:
        """Process a for loop as a decision with iteration."""
        # Create decision node for "more items?"
        iter_expr = self._expr_to_label(for_stmt.iter)
        target = self._expr_to_label(for_stmt.target)
        condition = f"More {target} in {iter_expr}?"
        decision = DecisionNode(label=condition)
        self._add_decision(decision)
        
        # Process loop body
        self._current_exits = [(decision, "Yes")]
        self._process_statements(for_stmt.body)
        
        # Back-edge
        for exit_node, _ in self._current_exits:
            edge = Edge(exit_node.id, decision.id)
            self.flowchart.add_edge(edge)
        
        # Exit
        self._current_exits = [(decision, "No")]
    
    def _process_return(self, ret_stmt: ast.Return) -> None:
        """Process a return statement as an end node."""
        if ret_stmt.value:
            label = f"Return: {self._expr_to_label(ret_stmt.value)}"
        else:
            label = "Return"
        
        end = EndNode(label=label)
        self._add_node(end)
        
        # Return terminates this path
        self._current_exits = []
    
    def _process_assign(self, assign: ast.Assign) -> None:
        """Process an assignment as a process node."""
        targets = ", ".join(self._expr_to_label(t) for t in assign.targets)
        value = self._expr_to_label(assign.value)
        label = f"{targets} = {value}"
        node = ProcessNode(label=label)
        self._add_node(node)
    
    def _call_to_label(self, call: ast.Call) -> str:
        """Convert a Call AST node to a readable label."""
        # Get function name
        if isinstance(call.func, ast.Name):
            func_name = call.func.id
        elif isinstance(call.func, ast.Attribute):
            func_name = f"{self._expr_to_label(call.func.value)}.{call.func.attr}"
        else:
            func_name = self._expr_to_label(call.func)
        
        # Format as readable label
        label = self._format_name(func_name)
        
        # Add arguments if any (simplified)
        if call.args or call.keywords:
            args = []
            for arg in call.args:
                args.append(self._expr_to_label(arg))
            for kw in call.keywords:
                args.append(f"{kw.arg}={self._expr_to_label(kw.value)}")
            if args:
                label += f" ({', '.join(args)})"
        
        return label
    
    def _expr_to_label(self, expr: ast.expr) -> str:
        """Convert an expression AST node to a readable string."""
        if isinstance(expr, ast.Name):
            return self._format_name(expr.id)
        
        elif isinstance(expr, ast.Call):
            return self._call_to_label(expr) + "?"
        
        elif isinstance(expr, ast.Compare):
            left = self._expr_to_label(expr.left)
            parts = [left]
            for op, comp in zip(expr.ops, expr.comparators):
                op_str = self._op_to_str(op)
                comp_str = self._expr_to_label(comp)
                parts.append(f"{op_str} {comp_str}")
            return " ".join(parts)
        
        elif isinstance(expr, ast.BoolOp):
            op_str = " and " if isinstance(expr.op, ast.And) else " or "
            return op_str.join(self._expr_to_label(v) for v in expr.values)
        
        elif isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.Not):
                return f"not {self._expr_to_label(expr.operand)}"
            return self._expr_to_label(expr.operand)
        
        elif isinstance(expr, ast.Constant):
            return repr(expr.value)
        
        elif isinstance(expr, ast.Attribute):
            return f"{self._expr_to_label(expr.value)}.{expr.attr}"
        
        elif isinstance(expr, ast.Subscript):
            return f"{self._expr_to_label(expr.value)}[{self._expr_to_label(expr.slice)}]"
        
        elif isinstance(expr, ast.List):
            items = ", ".join(self._expr_to_label(e) for e in expr.elts)
            return f"[{items}]"
        
        elif isinstance(expr, ast.Tuple):
            items = ", ".join(self._expr_to_label(e) for e in expr.elts)
            return f"({items})"
        
        elif isinstance(expr, ast.BinOp):
            left = self._expr_to_label(expr.left)
            right = self._expr_to_label(expr.right)
            op = self._binop_to_str(expr.op)
            return f"{left} {op} {right}"
        
        else:
            # Fallback: use ast.unparse if available (Python 3.9+)
            try:
                return ast.unparse(expr)
            except:
                return "<?>"
    
    def _op_to_str(self, op: ast.cmpop) -> str:
        """Convert comparison operator to string."""
        ops = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.Is: "is",
            ast.IsNot: "is not",
            ast.In: "in",
            ast.NotIn: "not in",
        }
        return ops.get(type(op), "?")
    
    def _binop_to_str(self, op: ast.operator) -> str:
        """Convert binary operator to string."""
        ops = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
            ast.Pow: "**",
            ast.FloorDiv: "//",
        }
        return ops.get(type(op), "?")
    
    def _format_name(self, name: str) -> str:
        """Format a snake_case name to Title Case."""
        # Replace underscores with spaces and title case
        return name.replace("_", " ").title()


class FlowchartFunction:
    """Wrapper that holds both the function and its flowchart."""
    
    def __init__(self, func: Callable, flowchart: FlowChart):
        self._func = func
        self.flowchart = flowchart
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
    
    def __call__(self, *args, **kwargs):
        """Call the underlying function."""
        return self._func(*args, **kwargs)
    
    def build(self) -> FlowChart:
        """Return the flowchart."""
        return self.flowchart


def flowchart(func: Callable = None, *, name: str = None, shared_nodes: bool = False) -> FlowchartFunction:
    """
    Decorator that builds a flowchart from a function's AST.
    
    Args:
        name: Custom name for the flowchart (defaults to function name)
        shared_nodes: If True, calling the same function multiple times
                      connects to the same node (useful for graphs with
                      multiple paths leading to the same step)
    
    Usage:
        @flowchart
        def my_process():
            step_one()
            if check_condition():
                do_this()
            else:
                do_that()
        
        # Access the flowchart
        chart = my_process.flowchart
        
        # Or with custom name and shared nodes (same function = same node)
        @flowchart(name="My Custom Flow", shared_nodes=True)
        def another_process():
            ...
    """
    def decorator(f: Callable) -> FlowchartFunction:
        chart_name = name or f.__name__.replace("_", " ").title()
        builder = ASTFlowBuilder(chart_name, shared_nodes=shared_nodes)
        chart = builder.build_from_function(f)
        return FlowchartFunction(f, chart)
    
    if func is not None:
        # @flowchart without arguments
        return decorator(func)
    else:
        # @flowchart(name="...") with arguments
        return decorator


# Convenience function to build from source string
def flowchart_from_source(source: str, name: str = "FlowChart") -> FlowChart:
    """
    Build a flowchart from Python source code string.
    
    The source should contain a single function definition.
    """
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    
    if not tree.body or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("Source must contain a function definition")
    
    func_def = tree.body[0]
    builder = ASTFlowBuilder(name)
    
    # Create start node
    start_label = builder._format_name(func_def.name)
    start = StartNode(label=start_label)
    builder.flowchart.add_node(start)
    builder._current_exits = [(start, None)]
    
    # Process function body
    builder._process_statements(func_def.body)
    
    # Add end node
    if builder._current_exits:
        end = EndNode(label="End")
        builder._add_node(end)
    
    return builder.flowchart
