from pathlib import Path
from typing import List, Optional

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QInputDialog,
)

from node_editor_window import NodeEditorWindow
from project_store import create_project_file, list_project_files, load_project_name


class OpenVisionMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Open Vision - Project Menu")
        self.resize(900, 580)

        self.base_dir = Path(__file__).resolve().parent
        self.project_files: List[Path] = []
        self.editor_window: Optional[NodeEditorWindow] = None

        self._build_ui()
        self._connect_signals()
        self.refresh_projects()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)

        controls_col = QVBoxLayout()
        details_col = QVBoxLayout()

        self.btn_create_project = QPushButton("Create Project")
        self.btn_open_project_file = QPushButton("Open Project File")
        self.btn_refresh_projects = QPushButton("Refresh Projects")
        self.btn_launch_selected = QPushButton("Launch Selected Project")

        self.projects_list = QListWidget()

        self.label_menu_title = QLabel("Open Vision Project Menu")
        self.label_menu_title.setAlignment(Qt.AlignCenter)
        self.label_menu_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.label_project_hint = QLabel("Create a project or pick an existing project file to open the node canvas.")
        self.label_project_hint.setWordWrap(True)
        self.label_selected_project = QLabel("Selected project: none")

        controls_col.addWidget(self.label_menu_title)
        controls_col.addWidget(self.btn_create_project)
        controls_col.addWidget(self.btn_open_project_file)
        controls_col.addWidget(self.btn_refresh_projects)
        controls_col.addWidget(self.btn_launch_selected)
        controls_col.addWidget(self.label_selected_project)
        controls_col.addStretch(1)

        details_col.addWidget(QLabel("Available Projects"))
        details_col.addWidget(self.projects_list)
        details_col.addWidget(self.label_project_hint)

        root.addLayout(controls_col, stretch=1)
        root.addLayout(details_col, stretch=2)

    def _connect_signals(self) -> None:
        self.btn_create_project.clicked.connect(self.create_project)
        self.btn_open_project_file.clicked.connect(self.open_project_file)
        self.btn_refresh_projects.clicked.connect(self.refresh_projects)
        self.btn_launch_selected.clicked.connect(self.launch_selected_project)
        self.projects_list.currentRowChanged.connect(self.on_project_selected)
        self.projects_list.itemDoubleClicked.connect(self.launch_selected_project)

    def refresh_projects(self) -> None:
        self.project_files = list_project_files(self.base_dir)
        self.projects_list.clear()

        for project_path in self.project_files:
            project_name = load_project_name(project_path)
            self.projects_list.addItem(f"{project_name} ({project_path.name})")

        if self.project_files:
            self.projects_list.setCurrentRow(0)
        else:
            self.label_selected_project.setText("Selected project: none")

    def on_project_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.project_files):
            self.label_selected_project.setText("Selected project: none")
            return

        selected_path = self.project_files[index]
        project_name = load_project_name(selected_path)
        self.label_selected_project.setText(f"Selected project: {project_name}")

    def create_project(self) -> None:
        name, ok = QInputDialog.getText(self, "Create Project", "Project name:")
        if not ok or not name.strip():
            return

        project_path = create_project_file(self.base_dir, name.strip())
        self.refresh_projects()
        self._select_project(project_path)
        QMessageBox.information(self, "Project Created", f"Created project file:\n{project_path}")

    def open_project_file(self) -> None:
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project File",
            str(self.base_dir),
            "Open Vision Project (*.ovproj)",
        )
        if not selected_file:
            return

        project_path = Path(selected_file)
        if project_path.parent.resolve() == (self.base_dir / "Projects").resolve():
            self.refresh_projects()
            self._select_project(project_path)
            self.launch_project(project_path)
            return

        self.launch_project(project_path)

    def launch_selected_project(self) -> None:
        index = self.projects_list.currentRow()
        if index < 0 or index >= len(self.project_files):
            QMessageBox.warning(self, "No Project Selected", "Select a project first.")
            return

        self.launch_project(self.project_files[index])

    def launch_project(self, project_path: Path) -> None:
        self.editor_window = NodeEditorWindow(project_path=project_path)
        self.editor_window.show()

    def _select_project(self, project_path: Path) -> None:
        for index, known_path in enumerate(self.project_files):
            if known_path.resolve() == project_path.resolve():
                self.projects_list.setCurrentRow(index)
                break


def main() -> None:
    app = QApplication(sys.argv)
    window = OpenVisionMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()