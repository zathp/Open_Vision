import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from PyQt5.QtCore import QLineF, QRectF, Qt, QSize
from PyQt5.QtGui import QBrush, QColor, QPen, QPixmap, QImage
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
    QFileDialog,
    QColorDialog,
    QInputDialog,
    QScrollArea
)

from OV_Libs.ProjStoreLib.project_store import load_project_graph, save_project_graph
from OV_Libs.ImageEditingLib.image_editing_ops import apply_color_mapping, extract_unique_colors, build_identity_mapping
from OV_Libs.pillow_compat import pil_to_qimage, qimage_to_pil, Image

# --- Node Components ---

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
        super().__init__(0, 0, 200, 100)
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

        self.label = QGraphicsSimpleTextItem(node_type, self)
        self.label.setBrush(QBrush(QColor("#f0f0f0")))
        self.label.setPos(12, 10)

        # Default ports (can be overridden)
        self.input_port = PortItem(-6, 44, 12, 12, node_id, "input", on_port_clicked, self)
        self.input_port.setBrush(QBrush(QColor("#9cdcfe")))
        
        self.output_port = PortItem(194, 44, 12, 12, node_id, "output", on_port_clicked, self)
        self.output_port.setBrush(QBrush(QColor("#6aeb8f")))

        self.node_data: Dict[str, Any] = {}

    def input_anchor(self):
        return self.mapToScene(0, 50)

    def output_anchor(self):
        return self.mapToScene(200, 50)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionHasChanged and self.on_position_changed is not None:
            self.on_position_changed()
        return super().itemChange(change, value)

    def get_params(self) -> Dict[str, Any]:
        return {}

    def set_params(self, params: Dict[str, Any]):
        pass

# --- Node Editor Window ---

class NodeEditorWindow(QMainWindow):
    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self.project_path = project_path
        self.setWindowTitle(f"Open Vision Node Canvas - {project_path.stem}")
        self.resize(1500, 900)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 5000, 5000))

        self.node_items: Dict[str, NodeItem] = {}
        self.connections: List[Dict[str, str]] = []
        self.connection_items: List[QGraphicsLineItem] = []
        self.pending_output_node_id: Optional[str] = None
        
        self.original_image: Optional[Image.Image] = None
        self.modified_image: Optional[Image.Image] = None

        self._build_ui()
        self._connect_signals()
        self._load_nodes_from_project()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # 1. Left Controls
        controls = QVBoxLayout()
        controls.setContentsMargins(10, 10, 10, 10)
        
        self.btn_add_import = QPushButton("Add Image Import")
        self.btn_add_replace = QPushButton("Add Color Replace")
        self.btn_add_export = QPushButton("Add Image Export")
        self.btn_run = QPushButton("Run Pipeline")
        self.btn_run.setStyleSheet("background-color: #0e639c; font-weight: bold;")
        
        controls.addWidget(QLabel("Nodes"))
        controls.addWidget(self.btn_add_import)
        controls.addWidget(self.btn_add_replace)
        controls.addWidget(self.btn_add_export)
        controls.addSpacing(20)
        controls.addWidget(self.btn_run)
        
        btn_save = QPushButton("Save Layout")
        btn_save.clicked.connect(self.save_layout)
        controls.addWidget(btn_save)
        
        controls.addStretch(1)
        root.addLayout(controls, stretch=1)

        # 2. Middle Canvas
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        self.view.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        root.addWidget(self.view, stretch=5)

        # 3. Right Previews
        previews = QVBoxLayout()
        previews.setContentsMargins(10, 10, 10, 10)
        
        self.label_orig = QLabel("Original")
        self.label_orig.setFixedSize(300, 300)
        self.label_orig.setStyleSheet("border: 1px solid #555; background: #000;")
        self.label_orig.setAlignment(Qt.AlignCenter)
        
        self.label_mod = QLabel("Result")
        self.label_mod.setFixedSize(300, 300)
        self.label_mod.setStyleSheet("border: 1px solid #555; background: #000;")
        self.label_mod.setAlignment(Qt.AlignCenter)
        
        previews.addWidget(QLabel("Original Preview"))
        previews.addWidget(self.label_orig)
        previews.addSpacing(20)
        previews.addWidget(QLabel("Modified Preview"))
        previews.addWidget(self.label_mod)
        previews.addStretch(1)
        
        root.addLayout(previews, stretch=2)

    def _connect_signals(self) -> None:
        self.btn_add_import.clicked.connect(lambda: self.add_node("Image Import"))
        self.btn_add_replace.clicked.connect(lambda: self.add_node("Color Replace"))
        self.btn_add_export.clicked.connect(lambda: self.add_node("Image Export"))
        self.btn_run.clicked.connect(self.run_pipeline)

    def add_node(self, node_type: str) -> None:
        node_id = str(uuid.uuid4())
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self._create_node_item(node_id, node_type, center.x() - 100, center.y() - 50)

    def _create_node_item(self, node_id: str, node_type: str, x: float, y: float) -> None:
        item = NodeItem(node_id, node_type, x, y, self.update_connection_positions, self.on_port_clicked)
        self.scene.addItem(item)
        self.node_items[node_id] = item

    def on_port_clicked(self, node_id: str, port_kind: str) -> None:
        if port_kind == "output":
            self.pending_output_node_id = node_id
            self.statusBar().showMessage(f"Selected output from {self.node_items[node_id].node_type}. Click an input.")
            return

        if port_kind == "input" and self.pending_output_node_id:
            from_node = self.pending_output_node_id
            to_node = node_id
            if from_node != to_node:
                self._add_connection(from_node, to_node)
            self.pending_output_node_id = None
            self._rebuild_connection_items()

    def _add_connection(self, from_id: str, to_id: str) -> None:
        # Check for existing connection to same input (one input per port)
        self.connections = [c for c in self.connections if c["to_node"] != to_id]
        self.connections.append({"from_node": from_id, "from_port": "output", "to_node": to_id, "to_port": "input"})
        self._rebuild_connection_items()

    def _rebuild_connection_items(self) -> None:
        for item in self.connection_items: self.scene.removeItem(item)
        self.connection_items.clear()
        
        for conn in self.connections:
            start = self.node_items.get(conn["from_node"])
            end = self.node_items.get(conn["to_node"])
            if start and end:
                line = self.scene.addLine(QLineF(start.output_anchor(), end.input_anchor()), QPen(QColor("#53a7ff"), 2.0))
                line.setZValue(-1)
                self.connection_items.append(line)

    def update_connection_positions(self) -> None:
        self._rebuild_connection_items()

    def run_pipeline(self) -> None:
        # 1. Find the Import Node
        import_node = next((n for n in self.node_items.values() if n.node_type == "Image Import"), None)
        if not import_node:
            QMessageBox.warning(self, "No Import", "Please add an Image Import node.")
            return

        # 2. Get image (simplified for MVP: just pick manually if not set)
        img_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if not img_path: return
        
        self.original_image = Image.open(img_path).convert("RGBA")
        self._update_preview(self.label_orig, self.original_image)
        
        # 3. Execute logic (Linear traversal for MVP)
        current_img = self.original_image
        
        # Find connection from import node
        curr_id = import_node.node_id
        while True:
            conn = next((c for c in self.connections if c["from_node"] == curr_id), None)
            if not conn: break
            
            curr_id = conn["to_node"]
            node = self.node_items[curr_id]
            
            if node.node_type == "Color Replace":
                # Manual color replace for now
                color = QColorDialog.getColor(Qt.black, self, "Pick color to replace")
                if color.isValid():
                    target = (color.red(), color.green(), color.blue(), 255)
                    repl = QColorDialog.getColor(Qt.white, self, "Pick replacement color")
                    if repl.isValid():
                        new_c = (repl.red(), repl.green(), repl.blue(), 255)
                        current_img = apply_color_mapping(current_img, {target: new_c})
            
            elif node.node_type == "Image Export":
                save_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "output.png", "PNG (*.png)")
                if save_path:
                    current_img.save(save_path)
                break
        
        self.modified_image = current_img
        self._update_preview(self.label_mod, self.modified_image)

    def _update_preview(self, label: QLabel, img: Image.Image) -> None:
        qimg = pil_to_qimage(img)
        pix = QPixmap.fromImage(qimg)
        label.setPixmap(pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _load_nodes_from_project(self) -> None:
        graph = load_project_graph(self.project_path)
        for node in graph.get("nodes", []):
            self._create_node_item(node["id"], node["type"], node["x"], node["y"])
        self.connections = graph.get("connections", [])
        self._rebuild_connection_items()

    def save_layout(self) -> None:
        nodes = []
        for nid, item in self.node_items.items():
            nodes.append({"id": nid, "type": item.node_type, "x": item.pos().x(), "y": item.pos().y()})
        save_project_graph(self.project_path, nodes, self.connections)
        QMessageBox.information(self, "Saved", "Layout saved.")

    def closeEvent(self, event) -> None:
        self.save_layout()
        super().closeEvent(event)
