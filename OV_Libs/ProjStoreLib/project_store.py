import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PROJECTS_DIR_NAME = "Projects"
PROJECT_EXTENSION = ".ovproj"
SCHEMA_VERSION = 1


def _default_test_graph() -> Dict[str, Any]:
    input_id = str(uuid.uuid4())
    process_id = str(uuid.uuid4())
    output_id = str(uuid.uuid4())

    return {
        "nodes": [
            {"id": input_id, "type": "Test Input", "x": 80.0, "y": 100.0},
            {"id": process_id, "type": "Test Process", "x": 340.0, "y": 240.0},
            {"id": output_id, "type": "Test Output", "x": 620.0, "y": 100.0},
        ],
        "connections": [
            {"from_node": input_id, "from_port": "output", "to_node": process_id, "to_port": "input"},
            {"from_node": process_id, "from_port": "output", "to_node": output_id, "to_port": "input"},
        ],
    }


def _normalize_connection(connection: Dict[str, Any]) -> Dict[str, str]:
    if "from_node" in connection or "to_node" in connection:
        from_node = str(connection.get("from_node") or "")
        from_port = str(connection.get("from_port") or "output")
        to_node = str(connection.get("to_node") or "")
        to_port = str(connection.get("to_port") or "input")
    else:
        from_node = str(connection.get("from") or "")
        from_port = "output"
        to_node = str(connection.get("to") or "")
        to_port = "input"

    return {
        "from_node": from_node,
        "from_port": from_port,
        "to_node": to_node,
        "to_port": to_port,
    }


def get_projects_dir(base_dir: Path) -> Path:
    projects_dir = base_dir / PROJECTS_DIR_NAME
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir


def list_project_files(base_dir: Path) -> List[Path]:
    projects_dir = get_projects_dir(base_dir)
    return sorted(projects_dir.glob(f"*{PROJECT_EXTENSION}"))


def create_project_file(base_dir: Path, project_name: str) -> Path:
    projects_dir = get_projects_dir(base_dir)
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in project_name).strip("_")
    if not safe_name:
        safe_name = "new_project"

    project_path = projects_dir / f"{safe_name}{PROJECT_EXTENSION}"
    counter = 1
    while project_path.exists():
        project_path = projects_dir / f"{safe_name}_{counter}{PROJECT_EXTENSION}"
        counter += 1

    payload: Dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "name": project_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "image_paths": [],
        "filter_stacks": {},
        "node_graph": _default_test_graph(),
        "output_presets": {},
    }

    project_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return project_path


def load_project_name(project_path: Path) -> str:
    try:
        payload = json.loads(project_path.read_text(encoding="utf-8"))
    except Exception:
        return project_path.stem

    return str(payload.get("name") or project_path.stem)


def load_project_data(project_path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(project_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    node_graph = payload.get("node_graph")
    if not isinstance(node_graph, dict):
        node_graph = _default_test_graph()

    nodes = node_graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        default_graph = _default_test_graph()
        node_graph["nodes"] = default_graph["nodes"]
        node_graph["connections"] = default_graph["connections"]
    else:
        normalized_nodes: List[Dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or uuid.uuid4())
            node_type = str(node.get("type") or "Test Node")
            x = float(node.get("x", 100.0))
            y = float(node.get("y", 100.0))
            normalized_nodes.append({"id": node_id, "type": node_type, "x": x, "y": y})

        if normalized_nodes:
            node_graph["nodes"] = normalized_nodes
        else:
            default_graph = _default_test_graph()
            node_graph["nodes"] = default_graph["nodes"]
            node_graph["connections"] = default_graph["connections"]
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
            if from_port != "output" or to_port != "input":
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
