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
    PAINT_PROJECT_EXTENSION,
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


def _default_test_graph() -> Dict[str, Any]:
    """Create a default test graph with three connected nodes."""
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
    # Search for both .ovproj and .ovpaint files
    return sorted(list(projects_dir.glob(f"*{PROJECT_EXTENSION}")) + 
                  list(projects_dir.glob(f"*{PAINT_PROJECT_EXTENSION}")))


def _default_paint_data() -> Dict[str, Any]:
    """Create a default paint project structure."""
    return {
        "canvas_size": [1280, 720],
        "layers": [
            {
                "name": "Background",
                "visible": True,
                "opacity": 1.0,
                "data_path": None # null means blank/transparent for now
            }
        ],
        "tool_settings": {
            "last_tool": "brush",
            "foreground_color": [0, 0, 0, 255],
            "background_color": [255, 255, 255, 255],
            "brush_size": 5
        }
    }


def create_project_file(base_dir: Path, project_name: str, extension: str = PROJECT_EXTENSION) -> Path:
    """
    Create a new project file with default structure.
    
    Args:
        base_dir: Base directory containing the Projects folder
        project_name: Human-readable name for the project
        extension: The file extension (.ovproj or .ovpaint)
        
    Returns:
        Path to the created project file
    """
    projects_dir = get_projects_dir(base_dir)
    
    # Sanitize filename - keep only alphanumeric and safe characters
    safe_name = "".join(
        c if c.isalnum() or c in SAFE_FILENAME_CHARS else FILENAME_REPLACEMENT_CHAR
        for c in project_name
    ).strip(FILENAME_REPLACEMENT_CHAR)
    
    if not safe_name:
        safe_name = "new_project"

    project_path = projects_dir / f"{safe_name}{extension}"
    counter = 1
    while project_path.exists():
        project_path = projects_dir / f"{safe_name}_{counter}{extension}"
        counter += 1

    payload: Dict[str, object] = {
        FIELD_SCHEMA_VERSION: SCHEMA_VERSION,
        FIELD_NAME: project_name,
        FIELD_CREATED_AT: datetime.now().isoformat(timespec="seconds"),
        FIELD_IMAGE_PATHS: [],
        FIELD_FILTER_STACKS: {},
        FIELD_OUTPUT_PRESETS: {},
    }

    if extension == PROJECT_EXTENSION:
        payload[FIELD_NODE_GRAPH] = _default_test_graph()
    elif extension == PAINT_PROJECT_EXTENSION:
        payload.update(_default_paint_data())

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

    # Metadata defaults
    payload.setdefault(FIELD_SCHEMA_VERSION, SCHEMA_VERSION)
    payload.setdefault(FIELD_NAME, project_path.stem)
    payload.setdefault(FIELD_CREATED_AT, datetime.now().isoformat(timespec="seconds"))
    payload.setdefault(FIELD_IMAGE_PATHS, [])
    payload.setdefault(FIELD_FILTER_STACKS, {})
    payload.setdefault(FIELD_OUTPUT_PRESETS, {})

    # Extension-specific normalization
    extension = project_path.suffix.lower()

    if extension == PROJECT_EXTENSION:
        node_graph = payload.get(FIELD_NODE_GRAPH)
        if not isinstance(node_graph, dict):
            node_graph = _default_test_graph()

        nodes = node_graph.get(FIELD_NODES)
        if not isinstance(nodes, list) or not nodes:
            default_graph = _default_test_graph()
            node_graph[FIELD_NODES] = default_graph[FIELD_NODES]
            node_graph[FIELD_CONNECTIONS] = default_graph[FIELD_CONNECTIONS]
        else:
            normalized_nodes: List[Dict[str, Any]] = []
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                node_id = str(node.get(FIELD_NODE_ID) or uuid.uuid4())
                node_type = str(node.get(FIELD_NODE_TYPE) or NODE_TYPE_DEFAULT)
                x = float(node.get(FIELD_NODE_X, 100.0))
                y = float(node.get(FIELD_NODE_Y, 100.0))
                normalized_nodes.append({FIELD_NODE_ID: node_id, FIELD_NODE_TYPE: node_type, FIELD_NODE_X: x, FIELD_NODE_Y: y})
            
            node_graph[FIELD_NODES] = normalized_nodes

        connections = node_graph.get(FIELD_CONNECTIONS)
        if not isinstance(connections, list):
            node_graph[FIELD_CONNECTIONS] = []
        else:
            known_ids = {str(node.get(FIELD_NODE_ID)) for node in node_graph.get(FIELD_NODES, [])}
            normalized_connections: List[Dict[str, str]] = []
            occupied_inputs = set()
            for connection in connections:
                if not isinstance(connection, dict):
                    continue
                normalized = _normalize_connection(connection)
                if not normalized[FIELD_FROM_NODE] or not normalized[FIELD_TO_NODE]:
                    continue
                if normalized[FIELD_FROM_NODE] not in known_ids or normalized[FIELD_TO_NODE] not in known_ids:
                    continue
                
                input_key = (normalized[FIELD_TO_NODE], normalized[FIELD_TO_PORT])
                if input_key in occupied_inputs:
                    continue
                
                occupied_inputs.add(input_key)
                normalized_connections.append(normalized)
            node_graph[FIELD_CONNECTIONS] = normalized_connections
        
        payload[FIELD_NODE_GRAPH] = node_graph

    elif extension == PAINT_PROJECT_EXTENSION:
        default_paint = _default_paint_data()
        payload.setdefault("canvas_size", default_paint["canvas_size"])
        payload.setdefault("layers", default_paint["layers"])
        payload.setdefault("tool_settings", default_paint["tool_settings"])

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
        node_id = str(node.get("id") or uuid.uuid4())
        node_type = str(node.get("type") or "Test Node")
        x = float(node.get("x", 100.0))
        y = float(node.get("y", 100.0))
        normalized_nodes.append({"id": node_id, "type": node_type, "x": x, "y": y})

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
        if from_port != "output" or to_port != "input":
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
