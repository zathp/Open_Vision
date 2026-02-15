import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QLineF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from project_store import load_project_graph, save_project_graph


class PortItem(QGraphicsEllipseItem):
    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        node_id: str,
        port_kind: str,
        on_port_clicked: Callable[[str, str], None],
        parent=None,
    ) -> None:
        super().__init__(x, y, width, height, parent)
        self.node_id = node_id
        self.port_kind = port_kind
        self.on_port_clicked = on_port_clicked
        self.setAcceptedMouseButtons(Qt.LeftButton)

    def mousePressEvent(self, event) -> None:
        if self.on_port_clicked is not None:
            self.on_port_clicked(self.node_id, self.port_kind)
        event.accept()


class NodeItem(QGraphicsRectItem):
    def __init__(
        self,
        node_id: str,
        node_type: str,
        x: float,
        y: float,
        on_position_changed,
        on_port_clicked: Callable[[str, str], None],
    ) -> None:
        super().__init__(0, 0, 180, 70)
        self.node_id = node_id
        self.node_type = node_type
        self.on_position_changed = on_position_changed
        self.setPos(x, y)

        self.setBrush(QBrush(QColor("#2d2d30")))
        self.setPen(QPen(QColor("#8a8a8a"), 1.5))

        self.setFlags(
            QGraphicsRectItem.ItemIsMovable
            | QGraphicsRectItem.ItemIsSelectable
            | QGraphicsRectItem.ItemSendsGeometryChanges
        )

        label = QGraphicsSimpleTextItem(node_type, self)
        label.setBrush(QBrush(QColor("#f0f0f0")))
        label.setPos(12, 24)

        self.input_port = PortItem(-6, 28, 12, 12, node_id, "input", on_port_clicked, self)
        self.input_port.setBrush(QBrush(QColor("#9cdcfe")))
        self.input_port.setPen(QPen(QColor("#d0ebff"), 1.0))

        self.output_port = PortItem(174, 28, 12, 12, node_id, "output", on_port_clicked, self)
        self.output_port.setBrush(QBrush(QColor("#6aeb8f")))
        self.output_port.setPen(QPen(QColor("#c8ffd8"), 1.0))

    def input_anchor(self):
        return self.mapToScene(0, 35)

    def output_anchor(self):
        return self.mapToScene(180, 35)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionHasChanged and self.on_position_changed is not None:
            self.on_position_changed()
        return super().itemChange(change, value)


class NodeEditorWindow(QMainWindow):
    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self.project_path = project_path
        self.setWindowTitle(f"Open Vision Node Canvas - {project_path.stem}")
        self.resize(1300, 800)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 3000, 3000))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(self.view.renderHints())
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        self.view.setBackgroundBrush(QBrush(QColor("#1e1e1e")))

        self.node_items: Dict[str, NodeItem] = {}
        self.connections: List[Dict[str, str]] = []
        self.connection_items: List[QGraphicsLineItem] = []
        self.pending_output_node_id: Optional[str] = None

        self._build_ui()
        self._connect_signals()
        self._load_nodes_from_project()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        controls = QVBoxLayout()

        self.label_info = QLabel(
            "Click output port (right) then input port (left) to connect. "
            "Each input accepts one connection; outputs can connect to many inputs."
        )
        self.label_info.setWordWrap(True)

        self.btn_add_input = QPushButton("Add Test Input Node")
        self.btn_add_process = QPushButton("Add Test Process Node")
        self.btn_add_output = QPushButton("Add Test Output Node")
        self.btn_connect_selected = QPushButton("Connect Selected (Left -> Right)")
        self.btn_add_test_lines = QPushButton("Add Test Lines")
        self.btn_save_layout = QPushButton("Save Node Layout")

        controls.addWidget(self.label_info)
        controls.addWidget(self.btn_add_input)
        controls.addWidget(self.btn_add_process)
        controls.addWidget(self.btn_add_output)
        controls.addWidget(self.btn_connect_selected)
        controls.addWidget(self.btn_add_test_lines)
        controls.addWidget(self.btn_save_layout)
        controls.addStretch(1)

        root.addLayout(controls, stretch=1)
        root.addWidget(self.view, stretch=4)

    def _connect_signals(self) -> None:
        self.btn_add_input.clicked.connect(lambda: self.add_test_node("Test Input"))
        self.btn_add_process.clicked.connect(lambda: self.add_test_node("Test Process"))
        self.btn_add_output.clicked.connect(lambda: self.add_test_node("Test Output"))
        self.btn_connect_selected.clicked.connect(self.connect_selected_nodes)
        self.btn_add_test_lines.clicked.connect(self.add_test_lines)
        self.btn_save_layout.clicked.connect(self.save_layout)

    def _load_nodes_from_project(self) -> None:
        graph = load_project_graph(self.project_path)
        nodes = graph.get("nodes", [])
        connections = graph.get("connections", [])

        for node in nodes:
            self._create_node_item(
                node_id=str(node.get("id", uuid.uuid4())),
                node_type=str(node.get("type", "Test Node")),
                x=float(node.get("x", 120.0)),
                y=float(node.get("y", 120.0)),
            )

        self.connections = []
        for connection in connections:
            from_node = str(connection.get("from_node", ""))
            from_port = str(connection.get("from_port", "output"))
            to_node = str(connection.get("to_node", ""))
            to_port = str(connection.get("to_port", "input"))
            if (
                from_node in self.node_items
                and to_node in self.node_items
                and from_node != to_node
                and from_port == "output"
                and to_port == "input"
            ):
                self.connections.append(
                    {
                        "from_node": from_node,
                        "from_port": "output",
                        "to_node": to_node,
                        "to_port": "input",
                    }
                )

        self._rebuild_connection_items()

    def _create_node_item(self, node_id: str, node_type: str, x: float, y: float) -> None:
        item = NodeItem(
            node_id=node_id,
            node_type=node_type,
            x=x,
            y=y,
            on_position_changed=self.update_connection_positions,
            on_port_clicked=self.on_port_clicked,
        )
        self.scene.addItem(item)
        self.node_items[node_id] = item

    def add_test_node(self, node_type: str) -> None:
        node_id = str(uuid.uuid4())
        center_scene_pos = self.view.mapToScene(self.view.viewport().rect().center())
        x = float(center_scene_pos.x() - 90)
        y = float(center_scene_pos.y() - 35)
        self._create_node_item(node_id=node_id, node_type=node_type, x=x, y=y)

    def _rebuild_connection_items(self) -> None:
        for line_item in self.connection_items:
            self.scene.removeItem(line_item)
        self.connection_items = []

        for connection in self.connections:
            start_item = self.node_items.get(connection["from_node"])
            end_item = self.node_items.get(connection["to_node"])
            if start_item is None or end_item is None:
                continue

            line = QLineF(start_item.output_anchor(), end_item.input_anchor())
            line_item = self.scene.addLine(line, QPen(QColor("#53a7ff"), 2.0))
            line_item.setZValue(-1)
            self.connection_items.append(line_item)

    def update_connection_positions(self) -> None:
        self._rebuild_connection_items()

    def _input_is_available(self, to_node_id: str) -> bool:
        for connection in self.connections:
            if connection["to_node"] == to_node_id and connection["to_port"] == "input":
                return False
        return True

    def _add_connection(self, from_node_id: str, to_node_id: str) -> bool:
        if from_node_id == to_node_id:
            return False

        exists = any(
            connection
            for connection in self.connections
            if connection["from_node"] == from_node_id
            and connection["from_port"] == "output"
            and connection["to_node"] == to_node_id
            and connection["to_port"] == "input"
        )
        if exists:
            return False

        if not self._input_is_available(to_node_id):
            return False

        self.connections.append(
            {
                "from_node": from_node_id,
                "from_port": "output",
                "to_node": to_node_id,
                "to_port": "input",
            }
        )
        return True

    def on_port_clicked(self, node_id: str, port_kind: str) -> None:
        if port_kind == "output":
            self.pending_output_node_id = node_id
            node_type = self.node_items[node_id].node_type if node_id in self.node_items else "Node"
            self.statusBar().showMessage(f"Selected output: {node_type}. Click an input port to connect.", 4000)
            return

        if port_kind == "input":
            if self.pending_output_node_id is None:
                self.statusBar().showMessage("Select an output port first.", 3000)
                return

            from_node_id = self.pending_output_node_id
            to_node_id = node_id

            if not self._add_connection(from_node_id, to_node_id):
                self.statusBar().showMessage("Connection blocked: input already connected or invalid.", 4000)
                self.pending_output_node_id = None
                return

            self.pending_output_node_id = None
            self._rebuild_connection_items()
            self.statusBar().showMessage("Connection created.", 2500)

    def connect_selected_nodes(self) -> None:
        selected_nodes = [item for item in self.scene.selectedItems() if isinstance(item, NodeItem)]
        if len(selected_nodes) != 2:
            QMessageBox.warning(self, "Select Two Nodes", "Select exactly two nodes to connect.")
            return

        ordered = sorted(selected_nodes, key=lambda node: node.pos().x())
        from_id = ordered[0].node_id
        to_id = ordered[1].node_id

        if not self._add_connection(from_id, to_id):
            QMessageBox.warning(
                self,
                "Connection Blocked",
                "Target input already has a connection, or connection is invalid.",
            )
            return

        self._rebuild_connection_items()

    def add_test_lines(self) -> None:
        if len(self.node_items) < 2:
            return

        ordered_nodes = sorted(self.node_items.values(), key=lambda item: item.pos().x())
        for index in range(len(ordered_nodes) - 1):
            from_id = ordered_nodes[index].node_id
            to_id = ordered_nodes[index + 1].node_id
            self._add_connection(from_id, to_id)

        self._rebuild_connection_items()

    def collect_nodes(self) -> List[Dict[str, object]]:
        result: List[Dict[str, object]] = []
        for node_id, item in self.node_items.items():
            pos = item.pos()
            result.append(
                {
                    "id": node_id,
                    "type": item.node_type,
                    "x": float(pos.x()),
                    "y": float(pos.y()),
                }
            )
        return result

    def save_layout(self) -> None:
        nodes = self.collect_nodes()
        save_project_graph(self.project_path, nodes, self.connections)
        QMessageBox.information(self, "Saved", "Project node locations saved.")

    def closeEvent(self, event) -> None:
        try:
            save_project_graph(self.project_path, self.collect_nodes(), self.connections)
        except Exception:
            pass
        super().closeEvent(event)
