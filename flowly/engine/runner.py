from typing import Dict, List, Optional, Any
from flowly.core.ir import FlowChart, Node, Edge, StartNode, EndNode, DecisionNode

class FlowRunner:
    def __init__(self, flowchart: FlowChart):
        self.flowchart = flowchart
        self.current_node: Optional[Node] = None
        self.context: Dict[str, Any] = {}
        self.history: List[str] = [] # List of node IDs visited

    def start(self, start_node_id: Optional[str] = None):
        """Starts the execution. If no node provided, looks for a StartNode."""
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

    def step(self):
        """
        Advances to the next node if possible.
        For DecisionNodes, this might throw an error or return available options.
        """
        if not self.current_node:
            raise RuntimeError("Runner not started or already finished.")

        if isinstance(self.current_node, EndNode):
            print("Reached EndNode.")
            return

        # Get outgoing edges
        outgoing = [e for e in self.flowchart.edges if e.source_id == self.current_node.id]

        if not outgoing:
            # Dead end?
            return

        if len(outgoing) == 1:
            # Automatic transition
            self.current_node = self.flowchart.get_node(outgoing[0].target_id)
            self._record_visit()
        else:
            # Multiple paths (e.g. DecisionNode or ambiguous process)
            # For now, if decision node, we stop and ask caller to choose
             raise ValueError(f"Multiple outgoing paths from {self.current_node.label}. Use choose_path().")

    def get_options(self) -> List[Edge]:
        """Returns valid outgoing edges from current node."""
        if not self.current_node:
            return []
        return [e for e in self.flowchart.edges if e.source_id == self.current_node.id]

    def choose_path(self, edge_index: int):
        """Manually choose a path by index of get_options()."""
        options = self.get_options()
        if edge_index < 0 or edge_index >= len(options):
            raise IndexError("Invalid edge index.")
        
        selected_edge = options[edge_index]
        self.current_node = self.flowchart.get_node(selected_edge.target_id)
        self._record_visit()

    def _record_visit(self):
        if self.current_node:
            self.history.append(self.current_node.id)

