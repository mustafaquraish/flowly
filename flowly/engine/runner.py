"""FlowRunner for step-by-step execution of flowcharts."""

from typing import Dict, List, Optional, Any

from flowly.core.ir import FlowChart, Node, Edge, StartNode, EndNode


class FlowRunner:
    """
    Executes a flowchart step-by-step, tracking the current position and history.
    
    For nodes with multiple outgoing edges (decisions), use get_options() and 
    choose_path() to manually select the path.
    """
    
    def __init__(self, flowchart: FlowChart):
        self.flowchart = flowchart
        self.current_node: Optional[Node] = None
        self.context: Dict[str, Any] = {}
        self.history: List[str] = []

    def start(self, start_node_id: Optional[str] = None) -> None:
        """Start execution from a StartNode or specified node ID."""
        if start_node_id:
            self.current_node = self.flowchart.get_node(start_node_id)
        else:
            # Find the first StartNode
            for node in self.flowchart.nodes.values():
                if isinstance(node, StartNode):
                    self.current_node = node
                    break
        
        if not self.current_node:
            raise ValueError("No StartNode found and no start_node_id provided.")
        
        self._record_visit()

    def step(self) -> None:
        """Advance to the next node. Raises error if multiple paths exist."""
        if not self.current_node:
            raise RuntimeError("Runner not started or already finished.")

        if isinstance(self.current_node, EndNode):
            return

        outgoing = [e for e in self.flowchart.edges if e.source_id == self.current_node.id]

        if not outgoing:
            return

        if len(outgoing) == 1:
            self.current_node = self.flowchart.get_node(outgoing[0].target_id)
            self._record_visit()
        else:
            raise ValueError(
                f"Multiple outgoing paths from {self.current_node.label}. Use choose_path()."
            )

    def get_options(self) -> List[Edge]:
        """Get available outgoing edges from current node."""
        if not self.current_node:
            return []
        return [e for e in self.flowchart.edges if e.source_id == self.current_node.id]

    def choose_path(self, edge_index: int) -> None:
        """Choose a path by index from get_options()."""
        options = self.get_options()
        if edge_index < 0 or edge_index >= len(options):
            raise IndexError("Invalid edge index.")
        
        selected_edge = options[edge_index]
        self.current_node = self.flowchart.get_node(selected_edge.target_id)
        self._record_visit()

    def _record_visit(self) -> None:
        """Record the current node in history."""
        if self.current_node:
            self.history.append(self.current_node.id)

