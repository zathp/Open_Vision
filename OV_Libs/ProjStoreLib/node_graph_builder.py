"""
Node graph construction helpers for pipeline execution.

This module provides a builder class that creates node dictionaries and
connection dictionaries compatible with Open Vision's pipeline system.
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from OV_Libs.constants import (
    FIELD_CONNECTIONS,
    FIELD_FROM_NODE,
    FIELD_FROM_PORT,
    FIELD_NODE_ID,
    FIELD_NODE_TYPE,
    FIELD_NODE_X,
    FIELD_NODE_Y,
    FIELD_NODES,
    FIELD_TO_NODE,
    FIELD_TO_PORT,
)
from OV_Libs.ProjStoreLib.pipeline_builder import build_pipeline_from_graph


class NodeGraphBuilder:
    """Build node graphs with explicit input/output slot counts.

    The builder keeps an in-memory graph and validates links as you add them.
    Each node can expose any number of input and output slots.

    Notes:
        - A single input slot accepts one inbound connection.
        - An output slot can fan out to multiple downstream inputs.
        - Generated graph data is compatible with ``build_pipeline_from_graph``.
    """

    def __init__(
        self,
        start_x: float = 100.0,
        start_y: float = 100.0,
        x_spacing: float = 220.0,
    ) -> None:
        self.start_x = float(start_x)
        self.start_y = float(start_y)
        self.x_spacing = float(x_spacing)

        self._nodes_by_id: Dict[str, Dict[str, Any]] = {}
        self._node_order: List[str] = []
        self._connections: List[Dict[str, str]] = []

        self._input_links: Dict[Tuple[str, int], str] = {}
        self._output_links: Dict[Tuple[str, int], List[str]] = {}

    @staticmethod
    def _port_name(kind: str, index: int, total: int) -> str:
        if total == 1:
            return kind
        return f"{kind}_{index}"

    @staticmethod
    def _validate_slot_count(name: str, count: int) -> None:
        if count < 0:
            raise ValueError(f"{name} must be >= 0")

    def add_node(
        self,
        node_id: str,
        node_type: str,
        input_count: int = 1,
        output_count: int = 1,
        x: Optional[float] = None,
        y: Optional[float] = None,
        **node_data: Any,
    ) -> Dict[str, Any]:
        """Add a node with configurable input/output slots.

        Args:
            node_id: Unique node identifier.
            node_type: Node type used to select an executor.
            input_count: Number of input slots exposed by the node.
            output_count: Number of output slots exposed by the node.
            x: Optional x-position. Auto-assigned when omitted.
            y: Optional y-position. Auto-assigned when omitted.
            **node_data: Extra properties copied into the node dictionary.

        Returns:
            The created node dictionary.
        """
        normalized_id = str(node_id).strip()
        normalized_type = str(node_type).strip()

        if not normalized_id:
            raise ValueError("node_id is required")
        if not normalized_type:
            raise ValueError("node_type is required")
        if normalized_id in self._nodes_by_id:
            raise ValueError(f"Node already exists: {normalized_id}")

        self._validate_slot_count("input_count", input_count)
        self._validate_slot_count("output_count", output_count)

        node_index = len(self._node_order)
        node_x = float(x) if x is not None else self.start_x + (node_index * self.x_spacing)
        node_y = float(y) if y is not None else self.start_y

        input_ports = [
            self._port_name("input", index, input_count)
            for index in range(input_count)
        ]
        output_ports = [
            self._port_name("output", index, output_count)
            for index in range(output_count)
        ]

        node: Dict[str, Any] = {
            FIELD_NODE_ID: normalized_id,
            FIELD_NODE_TYPE: normalized_type,
            FIELD_NODE_X: node_x,
            FIELD_NODE_Y: node_y,
            "input_ports": input_ports,
            "output_ports": output_ports,
            "linked_inputs": [None] * input_count,
            "linked_outputs": [[] for _ in range(output_count)],
        }
        node.update(node_data)

        self._nodes_by_id[normalized_id] = node
        self._node_order.append(normalized_id)

        return deepcopy(node)

    def connect(
        self,
        from_node_id: str,
        to_node_id: str,
        from_output_index: int = 0,
        to_input_index: int = 0,
    ) -> Dict[str, str]:
        """Connect one node output slot to another node input slot."""
        source_id = str(from_node_id).strip()
        target_id = str(to_node_id).strip()

        if source_id == target_id:
            raise ValueError("Cannot connect a node to itself")
        if source_id not in self._nodes_by_id:
            raise ValueError(f"Unknown source node: {source_id}")
        if target_id not in self._nodes_by_id:
            raise ValueError(f"Unknown target node: {target_id}")

        source = self._nodes_by_id[source_id]
        target = self._nodes_by_id[target_id]

        output_ports = source.get("output_ports", [])
        input_ports = target.get("input_ports", [])

        if not output_ports:
            raise ValueError(f"Node has no outputs: {source_id}")
        if not input_ports:
            raise ValueError(f"Node has no inputs: {target_id}")

        if not (0 <= from_output_index < len(output_ports)):
            raise ValueError(f"Invalid output index {from_output_index} for node {source_id}")
        if not (0 <= to_input_index < len(input_ports)):
            raise ValueError(f"Invalid input index {to_input_index} for node {target_id}")

        occupied_key = (target_id, to_input_index)
        if occupied_key in self._input_links:
            raise ValueError(
                f"Input slot already connected: {target_id}[{to_input_index}]"
            )

        from_port = output_ports[from_output_index]
        to_port = input_ports[to_input_index]

        duplicate = any(
            connection
            for connection in self._connections
            if connection[FIELD_FROM_NODE] == source_id
            and connection[FIELD_FROM_PORT] == from_port
            and connection[FIELD_TO_NODE] == target_id
            and connection[FIELD_TO_PORT] == to_port
        )
        if duplicate:
            raise ValueError("Connection already exists")

        connection = {
            FIELD_FROM_NODE: source_id,
            FIELD_FROM_PORT: from_port,
            FIELD_TO_NODE: target_id,
            FIELD_TO_PORT: to_port,
        }
        self._connections.append(connection)

        self._input_links[occupied_key] = source_id
        self._output_links.setdefault((source_id, from_output_index), []).append(target_id)

        target["linked_inputs"][to_input_index] = source_id
        target_outputs = source["linked_outputs"][from_output_index]
        if target_id not in target_outputs:
            target_outputs.append(target_id)

        return deepcopy(connection)

    def connect_chain(
        self,
        node_ids: List[str],
        from_output_index: int = 0,
        to_input_index: int = 0,
    ) -> List[Dict[str, str]]:
        """Connect a list of nodes as a linked chain: n1 -> n2 -> n3 -> ..."""
        if len(node_ids) < 2:
            return []

        created: List[Dict[str, str]] = []
        for index in range(len(node_ids) - 1):
            created.append(
                self.connect(
                    node_ids[index],
                    node_ids[index + 1],
                    from_output_index=from_output_index,
                    to_input_index=to_input_index,
                )
            )
        return created

    def connect_many_to_input(self, from_node_ids: List[str], to_node_id: str) -> List[Dict[str, str]]:
        """Connect many upstream nodes into consecutive input slots of one node."""
        target_id = str(to_node_id).strip()
        if target_id not in self._nodes_by_id:
            raise ValueError(f"Unknown target node: {target_id}")

        target_inputs = self._nodes_by_id[target_id].get("input_ports", [])
        if len(from_node_ids) > len(target_inputs):
            raise ValueError(
                f"Target node {target_id} only has {len(target_inputs)} input slots"
            )

        created: List[Dict[str, str]] = []
        for slot_index, source_id in enumerate(from_node_ids):
            created.append(
                self.connect(
                    source_id,
                    target_id,
                    from_output_index=0,
                    to_input_index=slot_index,
                )
            )
        return created

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Return node list in insertion order."""
        return [deepcopy(self._nodes_by_id[node_id]) for node_id in self._node_order]

    def get_connections(self) -> List[Dict[str, str]]:
        """Return all connections in creation order."""
        return deepcopy(self._connections)

    def to_graph(self) -> Dict[str, Any]:
        """Return ``{"nodes": [...], "connections": [...]}`` graph payload."""
        return {
            FIELD_NODES: self.get_nodes(),
            FIELD_CONNECTIONS: self.get_connections(),
        }

    def build_pipeline(self) -> Tuple[Dict[str, Any], bool, List[str]]:
        """Build an execution pipeline from current graph state."""
        graph = self.to_graph()
        return build_pipeline_from_graph(graph[FIELD_NODES], graph[FIELD_CONNECTIONS])
