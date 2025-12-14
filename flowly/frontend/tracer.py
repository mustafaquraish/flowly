"""
Runtime tracer for automatically building FlowIR from Python code execution.

IMPORTANT: This tracer captures the EXECUTED PATH through code, not all possible
branches. If you need a complete flowchart with all branches, use FlowBuilder.

Use cases for FlowTracer:
- Documenting what path was taken through a procedure
- Creating execution traces/logs as flowcharts
- Generating "what happened" diagrams vs "what could happen"
- Building different flowcharts from the same code based on runtime conditions

For complete flowcharts with explicit branches, use FlowBuilder instead.

Example:
    from flowly.frontend.tracer import FlowTracer
    
    with FlowTracer("My Flow") as flow:
        flow.node("Step 1: Do something")
        
        if flow.decision("Is condition met?", some_actual_condition):
            flow.node("Yes branch")  # Only included if condition is True
        else:
            flow.node("No branch")   # Only included if condition is False
        
        flow.node("Done")
    
    chart = flow.build()  # Contains only the executed path
"""

from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from flowly.core.ir import (
    FlowChart, Node, StartNode, EndNode, ProcessNode, DecisionNode, Edge
)


class FlowTracer:
    """
    A runtime tracer that builds a FlowChart by tracking execution flow.
    
    The tracer maintains a "current node" pointer and automatically creates
    edges as new nodes are added or control flow primitives are used.
    """
    
    def __init__(self, name: str = "FlowChart"):
        self.name = name
        self._flowchart: Optional[FlowChart] = None
        self._current_node: Optional[Node] = None
        self._started = False
        self._finished = False
        
        # For automatic edge labeling from decisions/loops
        self._pending_edge_label: Optional[str] = None
        
        # Stack for tracking decision points (for connecting else branches)
        self._decision_stack: List[Dict[str, Any]] = []
        
        # Stack for tracking loop entry points (for back-edges)
        self._loop_stack: List[Dict[str, Any]] = []
        
    def __enter__(self) -> "FlowTracer":
        """Start tracing - creates the start node."""
        self._flowchart = FlowChart(self.name)
        self._started = True
        self._finished = False
        
        # Create start node
        start = StartNode(label="Start")
        self._flowchart.add_node(start)
        self._current_node = start
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """End tracing - creates the end node and final connection."""
        if exc_type is not None:
            # Exception occurred, don't suppress it
            return False
        
        # Create end node and connect
        if self._current_node and not self._finished:
            end = EndNode(label="End")
            self._flowchart.add_node(end)
            self._connect(self._current_node, end)
            self._finished = True
        
        return False
    
    def _connect(self, source: Node, target: Node, label: Optional[str] = None) -> Edge:
        """Create an edge between two nodes."""
        # If source is a decision node and no label provided, use pending label
        if label is None and self._pending_edge_label:
            label = self._pending_edge_label
            self._pending_edge_label = None
        
        edge = Edge(source.id, target.id, label=label)
        self._flowchart.add_edge(edge)
        return edge
    
    def node(self, label: str, description: Optional[str] = None) -> Node:
        """
        Add a process node to the flow.
        
        Args:
            label: Short label for the node
            description: Optional longer description (stored in metadata)
        
        Returns:
            The created ProcessNode
        """
        if not self._started:
            raise RuntimeError("FlowTracer must be used within a 'with' block")
        
        metadata = {"description": description} if description else {}
        node = ProcessNode(label=label, metadata=metadata)
        self._flowchart.add_node(node)
        
        # Connect from current node
        if self._current_node:
            self._connect(self._current_node, node)
        
        self._current_node = node
        return node
    
    def decision(self, question: str, result: bool, description: Optional[str] = None) -> bool:
        """
        Add a decision node and track the branch taken.
        
        This method should be used in an if statement:
        
            if flow.decision("Is X true?", actual_condition):
                # Yes branch
            else:
                # No branch
        
        Args:
            question: The question/condition text for the decision node
            result: The actual boolean result (determines which branch to take)
            description: Optional longer description
        
        Returns:
            The result parameter (for use in if statement)
        """
        if not self._started:
            raise RuntimeError("FlowTracer must be used within a 'with' block")
        
        metadata = {"description": description} if description else {}
        decision_node = DecisionNode(label=question, metadata=metadata)
        self._flowchart.add_node(decision_node)
        
        # Connect from current node
        if self._current_node:
            self._connect(self._current_node, decision_node)
        
        # Push decision context for tracking branches
        self._decision_stack.append({
            "node": decision_node,
            "result": result,
            "branch_taken": "Yes" if result else "No",
            "exit_nodes": [],  # Nodes that should connect to merge point
        })
        
        # Set pending edge label for the branch we're taking
        self._pending_edge_label = "Yes" if result else "No"
        
        # Create edge to the branch we're taking
        # The actual branch node will be created by the next node() call
        self._current_node = decision_node
        
        return result
    
    def end_decision(self) -> None:
        """
        Mark the end of a decision block (called after if/else completes).
        
        This creates a merge point for the branches.
        """
        if not self._decision_stack:
            raise RuntimeError("end_decision() called without matching decision()")
        
        ctx = self._decision_stack.pop()
        
        # The current node is the last node of the taken branch
        # We'll record it so future nodes connect properly
        # (In simple cases, current_node is already correct)
    
    def branch(self, label: str) -> None:
        """
        Start a new branch from the current decision node.
        
        This is used to label the edge to the current branch.
        Should be called right after entering an if/else block.
        """
        if not self._decision_stack:
            raise RuntimeError("branch() called outside of decision context")
        
        ctx = self._decision_stack[-1]
        decision_node = ctx["node"]
        
        # Update the last edge's label if it connects from the decision
        # (The edge was created when we called node() after decision())
        for edge in reversed(self._flowchart.edges):
            if edge.source_id == decision_node.id and edge.label is None:
                edge.label = label
                break
    
    def until(self, condition: str, result: bool = False, description: Optional[str] = None) -> bool:
        """
        Loop construct - creates a decision node for loop continuation.
        
        Usage:
            iteration = 0
            while flow.until("Continue processing?", iteration < 3):
                flow.node(f"Process item {iteration}")
                iteration += 1
        
        Args:
            condition: The condition description for the loop
            result: Whether to continue looping (True = continue, False = exit)
            description: Optional longer description
        
        Returns:
            The result parameter (for use in while statement)
        """
        if not self._started:
            raise RuntimeError("FlowTracer must be used within a 'with' block")
        
        # Check if we're already in this loop (back-edge case)
        if self._loop_stack and self._loop_stack[-1].get("condition") == condition:
            # We're looping back - create back-edge to the decision node
            loop_ctx = self._loop_stack[-1]
            decision_node = loop_ctx["node"]
            
            if result:
                # Continue looping - connect current to decision with "Yes" label
                if self._current_node and self._current_node.id != decision_node.id:
                    self._connect(self._current_node, decision_node, label="Yes")
                self._current_node = decision_node
                loop_ctx["iteration"] += 1
                # Set pending label for next iteration body
                self._pending_edge_label = "Yes"
                return True
            else:
                # Exit loop - connect current to decision, then decision exits
                if self._current_node and self._current_node.id != decision_node.id:
                    self._connect(self._current_node, decision_node, label="Yes")
                
                # Pop loop context
                self._loop_stack.pop()
                
                # Current node becomes the decision (exit edge will be created by next node)
                self._current_node = decision_node
                loop_ctx["exited"] = True
                # Set pending label for exit edge
                self._pending_edge_label = "No"
                return False
        else:
            # First entry into loop - create decision node
            metadata = {"description": description} if description else {}
            decision_node = DecisionNode(label=condition, metadata=metadata)
            self._flowchart.add_node(decision_node)
            
            # Connect from current node
            if self._current_node:
                self._connect(self._current_node, decision_node)
            
            # Push loop context
            self._loop_stack.append({
                "condition": condition,
                "node": decision_node,
                "iteration": 0,
                "exited": False,
            })
            
            if result:
                # Enter loop body - set pending label for edge to loop body
                self._current_node = decision_node
                self._pending_edge_label = "Yes"
                return True
            else:
                # Skip loop entirely - set pending label for exit edge
                self._loop_stack.pop()
                self._current_node = decision_node
                self._pending_edge_label = "No"
                return False
    
    def end(self, label: str = "End", description: Optional[str] = None) -> Node:
        """
        Explicitly end the flow at this point.
        
        Useful for early termination branches.
        """
        if not self._started:
            raise RuntimeError("FlowTracer must be used within a 'with' block")
        
        metadata = {"description": description} if description else {}
        end_node = EndNode(label=label, metadata=metadata)
        self._flowchart.add_node(end_node)
        
        if self._current_node:
            self._connect(self._current_node, end_node)
        
        self._current_node = None
        self._finished = True
        return end_node
    
    def build(self) -> FlowChart:
        """
        Get the constructed FlowChart.
        
        Should be called after the 'with' block completes.
        """
        if not self._flowchart:
            raise RuntimeError("FlowTracer was not used or has no flowchart")
        return self._flowchart


class SimpleFlowTracer(FlowTracer):
    """
    A simplified tracer with a cleaner API for basic flows.
    
    Provides Node(), Decision(), and Until() as capitalized methods
    with support for custom edge labels and method chaining.
    """
    
    def Node(self, label: str, description: Optional[str] = None) -> "SimpleFlowTracer":
        """Add a process node. Returns self for chaining."""
        self.node(label, description)
        return self
    
    def Decision(self, question: str, result: bool, 
                 yes_label: str = "Yes", no_label: str = "No",
                 description: Optional[str] = None) -> bool:
        """
        Decision point with custom edge labeling.
        
        Args:
            question: The decision question
            result: The actual condition result
            yes_label: Label for the "true" edge (default: "Yes")
            no_label: Label for the "false" edge (default: "No")
            description: Optional description
        
        Returns:
            The result value
        """
        # Call parent decision (which sets default Yes/No labels)
        ret = self.decision(question, result, description)
        
        # Override with custom labels if provided
        self._pending_edge_label = yes_label if result else no_label
        
        return ret
    
    def Until(self, condition: str, result: bool,
              continue_label: str = "Yes", exit_label: str = "No",
              description: Optional[str] = None) -> bool:
        """
        Loop construct with custom edge labeling.
        
        Args:
            condition: The loop condition description
            result: Whether to continue (True) or exit (False)
            continue_label: Label for the continue edge (default: "Yes")
            exit_label: Label for the exit edge (default: "No")
            description: Optional description
        
        Returns:
            The result value
        """
        ret = self.until(condition, result, description)
        
        # Override with custom labels
        if result:
            self._pending_edge_label = continue_label
        else:
            self._pending_edge_label = exit_label
        
        return ret
    
    def End(self, label: str = "End", description: Optional[str] = None) -> "SimpleFlowTracer":
        """Explicitly end the flow. Returns self for chaining."""
        self.end(label, description)
        return self
