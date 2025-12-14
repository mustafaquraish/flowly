"""
Static flowchart builder using context managers for clean Python-like syntax.

This module provides a builder that creates complete flowcharts with all branches
defined statically. Unlike the runtime tracer, this captures ALL branches in
decision nodes and loops.

Example:
    from flowly.frontend.static import StaticFlowBuilder
    
    with StaticFlowBuilder("My Flow") as flow:
        flow.node("Step 1")
        
        with flow.decision("Is condition met?") as branch:
            with branch.yes():
                flow.node("Yes branch")
            with branch.no():
                flow.node("No branch")
        
        flow.node("After decision")
        
        with flow.loop("Keep going?"):
            flow.node("Loop body")
        
        flow.node("Done")
    
    chart = flow.build()
"""

from typing import Optional, List
from contextlib import contextmanager
from flowly.core.ir import (
    FlowChart, Node, StartNode, EndNode, ProcessNode, DecisionNode, Edge
)


class BranchContext:
    """Context for handling decision branches (yes/no paths)."""
    
    def __init__(self, builder: "StaticFlowBuilder", decision_node: DecisionNode):
        self._builder = builder
        self._decision_node = decision_node
        self._yes_exits: List[Node] = []  # Nodes that exit the yes branch
        self._no_exits: List[Node] = []   # Nodes that exit the no branch
        self._has_yes = False
        self._has_no = False
    
    @contextmanager
    def yes(self, label: str = "Yes"):
        """Define the 'yes' (true) branch of the decision."""
        self._has_yes = True
        
        # Set up to connect from decision with label
        self._builder._current_node = self._decision_node
        self._builder._pending_edge_label = label
        
        # Clear any pending merges from outer context and save them
        outer_merges = self._builder._pending_merge_nodes[:]
        self._builder._pending_merge_nodes = []
        
        yield
        
        # Record exit point of yes branch (current node after branch body)
        if self._builder._current_node and self._builder._current_node != self._decision_node:
            self._yes_exits.append(self._builder._current_node)
        
        # Also collect any pending merges that were created inside (from nested decisions)
        self._yes_exits.extend(self._builder._pending_merge_nodes)
        self._builder._pending_merge_nodes = []
        
        # Restore outer merges
        self._builder._pending_merge_nodes = outer_merges
    
    @contextmanager
    def no(self, label: str = "No"):
        """Define the 'no' (false) branch of the decision."""
        self._has_no = True
        
        # Set up to connect from decision with label
        self._builder._current_node = self._decision_node
        self._builder._pending_edge_label = label
        
        # Clear any pending merges from outer context and save them
        outer_merges = self._builder._pending_merge_nodes[:]
        self._builder._pending_merge_nodes = []
        
        yield
        
        # Record exit point of no branch
        if self._builder._current_node and self._builder._current_node != self._decision_node:
            self._no_exits.append(self._builder._current_node)
        
        # Also collect any pending merges from nested decisions
        self._no_exits.extend(self._builder._pending_merge_nodes)
        self._builder._pending_merge_nodes = []
        
        # Restore outer merges
        self._builder._pending_merge_nodes = outer_merges


class StaticFlowBuilder:
    """
    A static flowchart builder using context managers for branches.
    
    This builder creates complete flowcharts with all branches defined.
    Use context managers to define decision branches and loops.
    """
    
    def __init__(self, name: str = "FlowChart"):
        self.name = name
        self._flowchart: Optional[FlowChart] = None
        self._current_node: Optional[Node] = None
        self._started = False
        self._pending_edge_label: Optional[str] = None
        self._pending_merge_nodes: List[Node] = []
    
    def __enter__(self) -> "StaticFlowBuilder":
        """Start building - creates the flowchart and start node."""
        self._flowchart = FlowChart(self.name)
        self._started = True
        self._pending_merge_nodes = []
        
        # Create start node
        start = StartNode(label="Start")
        self._flowchart.add_node(start)
        self._current_node = start
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """End building - creates the end node if needed."""
        if exc_type is not None:
            return False
        
        # Handle any pending merges
        if self._pending_merge_nodes:
            end = EndNode(label="End")
            self._flowchart.add_node(end)
            for exit_node in self._pending_merge_nodes:
                if exit_node and not isinstance(exit_node, EndNode):
                    self._connect_direct(exit_node, end)
            self._pending_merge_nodes = []
        elif self._current_node and not isinstance(self._current_node, EndNode):
            end = EndNode(label="End")
            self._flowchart.add_node(end)
            self._connect_direct(self._current_node, end)
        
        return False
    
    def _connect_direct(self, source: Node, target: Node, label: Optional[str] = None) -> Edge:
        """Create an edge between two nodes (no pending label handling)."""
        edge = Edge(source.id, target.id, label=label)
        self._flowchart.add_edge(edge)
        return edge
    
    def _connect(self, source: Node, target: Node, label: Optional[str] = None) -> Edge:
        """Create an edge, using pending label if set."""
        actual_label = self._pending_edge_label if label is None else label
        self._pending_edge_label = None
        return self._connect_direct(source, target, actual_label)
    
    def start(self, label: str = "Start", description: Optional[str] = None) -> Node:
        """Set a custom label/description for the start node."""
        if not self._started:
            raise RuntimeError("Must be used within 'with' block")
        
        for node in self._flowchart.nodes.values():
            if isinstance(node, StartNode):
                node.label = label
                if description:
                    node.metadata["description"] = description
                return node
        
        raise RuntimeError("Start node not found")
    
    def node(self, label: str, description: Optional[str] = None) -> Node:
        """Add a process node to the flow."""
        if not self._started:
            raise RuntimeError("Must be used within 'with' block")
        
        metadata = {"description": description} if description else {}
        node = ProcessNode(label=label, metadata=metadata)
        self._flowchart.add_node(node)
        
        # Handle pending merges from decision branches
        if self._pending_merge_nodes:
            for exit_node in self._pending_merge_nodes:
                if exit_node and not isinstance(exit_node, EndNode):
                    self._connect_direct(exit_node, node)
            self._pending_merge_nodes = []
        elif self._current_node:
            self._connect(self._current_node, node)
        
        self._current_node = node
        return node
    
    @contextmanager
    def decision(self, question: str, description: Optional[str] = None):
        """
        Create a decision node with yes/no branches.
        
        Usage:
            with flow.decision("Is X?") as branch:
                with branch.yes():
                    flow.node("Yes path")
                with branch.no():
                    flow.node("No path")
            flow.node("After decision")  # Both branches merge here
        """
        if not self._started:
            raise RuntimeError("Must be used within 'with' block")
        
        metadata = {"description": description} if description else {}
        decision_node = DecisionNode(label=question, metadata=metadata)
        self._flowchart.add_node(decision_node)
        
        # Connect from current position or pending merges
        if self._pending_merge_nodes:
            for exit_node in self._pending_merge_nodes:
                if exit_node and not isinstance(exit_node, EndNode):
                    self._connect_direct(exit_node, decision_node)
            self._pending_merge_nodes = []
        elif self._current_node:
            self._connect(self._current_node, decision_node)
        
        self._current_node = decision_node
        
        # Create branch context
        branch_ctx = BranchContext(self, decision_node)
        
        yield branch_ctx
        
        # After both branches are defined, collect all exit points for merging
        all_exits = []
        
        # Filter out EndNodes - they don't merge
        for exit_node in branch_ctx._yes_exits:
            if exit_node and not isinstance(exit_node, EndNode):
                all_exits.append(exit_node)
        
        for exit_node in branch_ctx._no_exits:
            if exit_node and not isinstance(exit_node, EndNode):
                all_exits.append(exit_node)
        
        # Set up pending merges for the next node
        self._pending_merge_nodes = all_exits
        self._current_node = None  # Will be set by next node() call
    
    @contextmanager
    def loop(self, condition: str, continue_label: str = "Yes", 
             exit_label: str = "No", description: Optional[str] = None):
        """
        Create a loop construct with a decision node.
        
        Usage:
            with flow.loop("More items?"):
                flow.node("Process item")
            flow.node("Done with loop")
        """
        if not self._started:
            raise RuntimeError("Must be used within 'with' block")
        
        metadata = {"description": description} if description else {}
        decision_node = DecisionNode(label=condition, metadata=metadata)
        self._flowchart.add_node(decision_node)
        
        # Connect from current position or pending merges
        if self._pending_merge_nodes:
            for exit_node in self._pending_merge_nodes:
                if exit_node and not isinstance(exit_node, EndNode):
                    self._connect_direct(exit_node, decision_node)
            self._pending_merge_nodes = []
        elif self._current_node:
            self._connect(self._current_node, decision_node)
        
        # Enter loop body (continue branch)
        self._current_node = decision_node
        self._pending_edge_label = continue_label
        
        yield
        
        # Connect end of loop body back to decision (back edge)
        if self._current_node and self._current_node != decision_node:
            self._connect_direct(self._current_node, decision_node)
        
        # Handle any nested decision exits - they also loop back
        if self._pending_merge_nodes:
            for exit_node in self._pending_merge_nodes:
                if exit_node and not isinstance(exit_node, EndNode):
                    self._connect_direct(exit_node, decision_node)
            self._pending_merge_nodes = []
        
        # Exit edge will be created by next node
        self._current_node = decision_node
        self._pending_edge_label = exit_label
    
    def end(self, label: str = "End", description: Optional[str] = None) -> Node:
        """Explicitly end the flow at this point."""
        if not self._started:
            raise RuntimeError("Must be used within 'with' block")
        
        metadata = {"description": description} if description else {}
        end_node = EndNode(label=label, metadata=metadata)
        self._flowchart.add_node(end_node)
        
        # Handle pending merges
        if self._pending_merge_nodes:
            for exit_node in self._pending_merge_nodes:
                if exit_node and not isinstance(exit_node, EndNode):
                    self._connect_direct(exit_node, end_node)
            self._pending_merge_nodes = []
        elif self._current_node:
            self._connect(self._current_node, end_node)
        
        self._current_node = end_node
        return end_node
    
    def connect(self, source: Node, target: Node, label: Optional[str] = None) -> Edge:
        """
        Manually connect two nodes with an edge.
        
        Use this for complex graphs that need cross-connections between branches.
        This doesn't affect the automatic flow tracking.
        
        Args:
            source: The source node
            target: The target node
            label: Optional edge label
            
        Returns:
            The created Edge
        """
        if not self._started:
            raise RuntimeError("Must be used within 'with' block")
        return self._connect_direct(source, target, label)
    
    def action(self, label: str, description: Optional[str] = None) -> Node:
        """Alias for node() - adds a process/action node."""
        return self.node(label, description)
    
    def build(self) -> FlowChart:
        """Get the constructed FlowChart."""
        if not self._flowchart:
            raise RuntimeError("FlowBuilder was not used")
        return self._flowchart


# Convenience alias
FlowBuilder = StaticFlowBuilder
