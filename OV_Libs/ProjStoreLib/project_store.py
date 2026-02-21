"""
Project file storage and management for Open Vision.

This module handles the persistence layer for Open Vision projects,
including creating, loading, and saving project files in the .ovproj format.

The project file schema includes:
- Project metadata (name, creation date, schema version)
- Image paths
- Filter stacks
- Node graph data (nodes and connections)
- Output presets

Functions:
    create_project_file: Create a new project file with default structure
    list_project_files: List all project files in the Projects directory
    load_project_name: Load just the project name from a file
    load_project_data: Load complete project data with validation
    save_project_data: Save project data to file
    load_project_graph: Load node graph from project file
    save_project_graph: Save node graph to project file
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from OV_Libs.constants import (
    PROJECTS_DIR_NAME,
    PROJECT_EXTENSION,
    SCHEMA_VERSION,
    SAFE_FILENAME_CHARS,
    FILENAME_REPLACEMENT_CHAR,
    DEFAULT_INPUT_NODE_X,
    DEFAULT_INPUT_NODE_Y,
    DEFAULT_PROCESS_NODE_X,
    DEFAULT_PROCESS_NODE_Y,
    DEFAULT_OUTPUT_NODE_X,
    DEFAULT_OUTPUT_NODE_Y,
    NODE_TYPE_INPUT,
    NODE_TYPE_PROCESS,
    NODE_TYPE_OUTPUT,
    NODE_TYPE_DEFAULT,
    PORT_INPUT,
    PORT_OUTPUT,
    FIELD_SCHEMA_VERSION,
    FIELD_NAME,
    FIELD_CREATED_AT,
    FIELD_IMAGE_PATHS,
    FIELD_FILTER_STACKS,
    FIELD_NODE_GRAPH,
    FIELD_OUTPUT_PRESETS,
    FIELD_NODES,
    FIELD_CONNECTIONS,
    FIELD_NODE_ID,
    FIELD_NODE_TYPE,
    FIELD_NODE_X,
    FIELD_NODE_Y,
    FIELD_FROM_NODE,
    FIELD_FROM_PORT,
    FIELD_TO_NODE,
    FIELD_TO_PORT,
)


def _create_node_dict(node_id: str, node_type: str, x: float, y: float) -> Dict[str, Any]:
    """Helper to create a node dictionary with standard fields."""
    return {
        FIELD_NODE_ID: node_id,
        FIELD_NODE_TYPE: node_type,
        FIELD_NODE_X: x,
        FIELD_NODE_Y: y,
    }


def _create_connection_dict(from_node: str, to_node: str, 
                           from_port: str = PORT_OUTPUT, to_port: str = PORT_INPUT) -> Dict[str, str]:
    """Helper to create a connection dictionary with standard fields."""
    return {
        FIELD_FROM_NODE: from_node,
        FIELD_FROM_PORT: from_port,
        FIELD_TO_NODE: to_node,
        FIELD_TO_PORT: to_port,
    }


def _normalize_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize node data while preserving optional graph UI metadata."""
    node_id = str(node.get("id") or uuid.uuid4())
    node_type = str(node.get("type") or NODE_TYPE_DEFAULT)
    x = float(node.get("x", 100.0))
    y = float(node.get("y", 100.0))

    normalized: Dict[str, Any] = {"id": node_id, "type": node_type, "x": x, "y": y}

    width_value = node.get("width")
    if width_value is not None:
        try:
            normalized["width"] = max(1.0, float(width_value))
        except (TypeError, ValueError):
            pass

    height_value = node.get("height")
    if height_value is not None:
        try:
            normalized["height"] = max(1.0, float(height_value))
        except (TypeError, ValueError):
            pass

    input_count_value = node.get("input_count")
    if input_count_value is not None:
        try:
            normalized["input_count"] = max(0, int(input_count_value))
        except (TypeError, ValueError):
            pass

    output_count_value = node.get("output_count")
    if output_count_value is not None:
        try:
            normalized["output_count"] = max(0, int(output_count_value))
        except (TypeError, ValueError):
            pass

    input_ports_value = node.get("input_ports")
    if isinstance(input_ports_value, list):
        normalized_input_ports = [str(value) for value in input_ports_value if str(value).strip()]
        if normalized_input_ports:
            normalized["input_ports"] = normalized_input_ports

    output_ports_value = node.get("output_ports")
    if isinstance(output_ports_value, list):
        normalized_output_ports = [str(value) for value in output_ports_value if str(value).strip()]
        if normalized_output_ports:
            normalized["output_ports"] = normalized_output_ports

    core_keys = {
        "id",
        "type",
        "x",
        "y",
        "width",
        "height",
        "input_count",
        "output_count",
        "input_ports",
        "output_ports",
    }
    for key, value in node.items():
        if key in core_keys:
            continue
        normalized[key] = value

    return normalized


def _default_test_graph() -> Dict[str, Any]:
    """Create a default graph with three connected nodes."""
    input_id = str(uuid.uuid4())
    process_id = str(uuid.uuid4())
    output_id = str(uuid.uuid4())

    return {
        FIELD_NODES: [
            _create_node_dict(input_id, NODE_TYPE_INPUT, DEFAULT_INPUT_NODE_X, DEFAULT_INPUT_NODE_Y),
            _create_node_dict(process_id, NODE_TYPE_PROCESS, DEFAULT_PROCESS_NODE_X, DEFAULT_PROCESS_NODE_Y),
            _create_node_dict(output_id, NODE_TYPE_OUTPUT, DEFAULT_OUTPUT_NODE_X, DEFAULT_OUTPUT_NODE_Y),
        ],
        FIELD_CONNECTIONS: [
            _create_connection_dict(input_id, process_id),
            _create_connection_dict(process_id, output_id),
        ],
    }


def _empty_graph() -> Dict[str, Any]:
    return {
        FIELD_NODES: [],
        FIELD_CONNECTIONS: [],
    }


def _normalize_connection(connection: Dict[str, Any]) -> Dict[str, str]:
    """
    Normalize connection data to use consistent field names.
    
    Handles both legacy and modern connection formats.
    """
    if FIELD_FROM_NODE in connection or FIELD_TO_NODE in connection:
        from_node = str(connection.get(FIELD_FROM_NODE) or "")
        from_port = str(connection.get(FIELD_FROM_PORT) or PORT_OUTPUT)
        to_node = str(connection.get(FIELD_TO_NODE) or "")
        to_port = str(connection.get(FIELD_TO_PORT) or PORT_INPUT)
    else:
        # Legacy format using "from" and "to"
        from_node = str(connection.get("from") or "")
        from_port = PORT_OUTPUT
        to_node = str(connection.get("to") or "")
        to_port = PORT_INPUT

    return {
        FIELD_FROM_NODE: from_node,
        FIELD_FROM_PORT: from_port,
        FIELD_TO_NODE: to_node,
        FIELD_TO_PORT: to_port,
    }


def get_projects_dir(base_dir: Path) -> Path:
    projects_dir = base_dir / PROJECTS_DIR_NAME
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir


def list_project_files(base_dir: Path) -> List[Path]:
    projects_dir = get_projects_dir(base_dir)
    return sorted(projects_dir.glob(f"*{PROJECT_EXTENSION}"))


def create_project_file(base_dir: Path, project_name: str) -> Path:
    """
    Create a new project file with default structure.
    
    Args:
        base_dir: Base directory containing the Projects folder
        project_name: Human-readable name for the project
        
    Returns:
        Path to the created project file
        
    Raises:
        ValueError: If project_name is empty after sanitization
    """
    projects_dir = get_projects_dir(base_dir)
    
    # Sanitize filename - keep only alphanumeric and safe characters
    safe_name = "".join(
        c if c.isalnum() or c in SAFE_FILENAME_CHARS else FILENAME_REPLACEMENT_CHAR
        for c in project_name
    ).strip(FILENAME_REPLACEMENT_CHAR)
    
    if not safe_name:
        safe_name = "new_project"

    project_path = projects_dir / f"{safe_name}{PROJECT_EXTENSION}"
    counter = 1
    while project_path.exists():
        project_path = projects_dir / f"{safe_name}_{counter}{PROJECT_EXTENSION}"
        counter += 1

    payload: Dict[str, object] = {
        FIELD_SCHEMA_VERSION: SCHEMA_VERSION,
        FIELD_NAME: project_name,
        FIELD_CREATED_AT: datetime.now().isoformat(timespec="seconds"),
        FIELD_IMAGE_PATHS: [],
        FIELD_FILTER_STACKS: {},
        FIELD_NODE_GRAPH: _empty_graph(),
        FIELD_OUTPUT_PRESETS: {},
    }

    project_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return project_path


def load_project_name(project_path: Path) -> str:
    """
    Load the project name from a project file.
    
    Args:
        project_path: Path to the project file
        
    Returns:
        The project name, or the filename stem if loading fails
    """
    try:
        payload = json.loads(project_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return project_path.stem

    return str(payload.get(FIELD_NAME) or project_path.stem)


def load_project_data(project_path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(project_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    node_graph = payload.get("node_graph")
    if not isinstance(node_graph, dict):
        node_graph = _empty_graph()

    nodes = node_graph.get("nodes")
    if not isinstance(nodes, list):
        node_graph["nodes"] = []
    else:
        normalized_nodes: List[Dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            normalized_nodes.append(_normalize_node(node))
        node_graph["nodes"] = normalized_nodes
    connections = node_graph.get("connections")
    if not isinstance(connections, list):
        node_graph["connections"] = []
    else:
        known_ids = {str(node.get("id")) for node in node_graph.get("nodes", []) if isinstance(node, dict)}
        normalized_connections: List[Dict[str, str]] = []
        occupied_inputs = set()
        for connection in connections:
            if not isinstance(connection, dict):
                continue

            normalized = _normalize_connection(connection)
            from_node = normalized["from_node"]
            from_port = normalized["from_port"]
            to_node = normalized["to_node"]
            to_port = normalized["to_port"]

            if not from_node or not to_node or from_node == to_node:
                continue
            if from_node not in known_ids or to_node not in known_ids:
                continue
            if not from_port or not to_port:
                continue

            input_key = (to_node, to_port)
            if input_key in occupied_inputs:
                continue

            occupied_inputs.add(input_key)
            normalized_connections.append(normalized)

        node_graph["connections"] = normalized_connections

    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("name", project_path.stem)
    payload.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    payload.setdefault("image_paths", [])
    payload.setdefault("filter_stacks", {})
    payload.setdefault("output_presets", {})
    payload["node_graph"] = node_graph

    return payload


def save_project_data(project_path: Path, payload: Dict[str, Any]) -> None:
    payload["schema_version"] = SCHEMA_VERSION
    project_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_project_nodes(project_path: Path) -> List[Dict[str, Any]]:
    payload = load_project_data(project_path)
    node_graph = payload.get("node_graph", {})
    return list(node_graph.get("nodes", []))


def save_project_nodes(project_path: Path, nodes: List[Dict[str, Any]]) -> None:
    payload = load_project_data(project_path)
    node_graph = payload.get("node_graph")
    if not isinstance(node_graph, dict):
        node_graph = {}

    node_graph["nodes"] = nodes
    node_graph.setdefault("connections", [])
    payload["node_graph"] = node_graph
    save_project_data(project_path, payload)


def load_project_graph(project_path: Path) -> Dict[str, Any]:
    payload = load_project_data(project_path)
    node_graph = payload.get("node_graph", {})
    connections = []
    for connection in list(node_graph.get("connections", [])):
        if isinstance(connection, dict):
            connections.append(_normalize_connection(connection))

    return {
        "nodes": list(node_graph.get("nodes", [])),
        "connections": connections,
    }


def save_project_graph(project_path: Path, nodes: List[Dict[str, Any]], connections: List[Dict[str, str]]) -> None:
    payload = load_project_data(project_path)
    node_graph = payload.get("node_graph")
    if not isinstance(node_graph, dict):
        node_graph = {}

    normalized_nodes: List[Dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        normalized_nodes.append(_normalize_node(node))

    known_ids = {str(node.get("id")) for node in normalized_nodes}
    normalized_connections: List[Dict[str, str]] = []
    occupied_inputs = set()
    for connection in connections:
        if not isinstance(connection, dict):
            continue

        normalized = _normalize_connection(connection)
        from_node = normalized["from_node"]
        from_port = normalized["from_port"]
        to_node = normalized["to_node"]
        to_port = normalized["to_port"]

        if not from_node or not to_node or from_node == to_node:
            continue
        if from_node not in known_ids or to_node not in known_ids:
            continue
        if not from_port or not to_port:
            continue

        input_key = (to_node, to_port)
        if input_key in occupied_inputs:
            continue

        occupied_inputs.add(input_key)
        normalized_connections.append(normalized)

    node_graph["nodes"] = normalized_nodes
    node_graph["connections"] = normalized_connections
    payload["node_graph"] = node_graph
    save_project_data(project_path, payload)
