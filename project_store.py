import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

PROJECTS_DIR_NAME = "Projects"
PROJECT_EXTENSION = ".ovproj"


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
        "name": project_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "image_paths": [],
    }

    project_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return project_path


def load_project_name(project_path: Path) -> str:
    try:
        payload = json.loads(project_path.read_text(encoding="utf-8"))
    except Exception:
        return project_path.stem

    return str(payload.get("name") or project_path.stem)
