import io
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtCore import QPoint, QRectF, Qt, QSize, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap, QCursor
from PyQt5.QtWidgets import (
    QAction,
    QColorDialog,
    QFileDialog,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QToolButton,
    QButtonGroup,
    QInputDialog
)

from OV_Libs.ProjStoreLib.project_store import load_project_data, save_project_data
from OV_Libs.pillow_compat import qimage_to_pil, pil_to_qimage, Image
from OV_Libs.Initial_Forms.Downsampler import downsample_image_hsv
from OV_Libs.Initial_Forms.Mirror import mirror_image

class CanvasView(QGraphicsView):
    drawing = pyqtSignal(QPoint)
    started = pyqtSignal(QPoint)
    finished = pyqtSignal()

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setMouseTracking(True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.viewport().setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos()).toPoint()
            self.started.emit(pos)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            pos = self.mapToScene(event.pos()).toPoint()
            self.drawing.emit(pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.finished.emit()

class PaintEditorWindow(QMainWindow):
    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self.project_path = project_path
        self.setWindowTitle(f"Open Vision Paint Editor - {project_path.stem}")
        self.resize(1400, 900)

        # State
        self.project_data = load_project_data(project_path)
        canvas_size = self.project_data.get("canvas_size", [1280, 720])
        self.image = QImage(canvas_size[0], canvas_size[1], QImage.Format_ARGB32)
        self.image.fill(Qt.white)

        self.current_tool = "brush"
        self.brush_color = QColor(Qt.black)
        self.brush_size = 5
        self.last_point = QPoint()
        self.undo_stack: List[QImage] = []
        self.redo_stack: List[QImage] = []
        
        self._build_ui()
        self._setup_canvas()
        self.push_undo()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # 1. Tool Palette Sidebar
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(10, 10, 10, 10)
        sidebar.setSpacing(8)

        # File Operations
        sidebar.addWidget(QLabel("Project"))
        btn_import = QPushButton("Import Image")
        btn_import.clicked.connect(self.import_image)
        sidebar.addWidget(btn_import)
        
        btn_export = QPushButton("Export Image")
        btn_export.clicked.connect(self.export_image)
        sidebar.addWidget(btn_export)
        
        sidebar.addSpacing(10)
        sidebar.addWidget(QLabel("Tools"))
        
        self.tool_group = QButtonGroup(self)
        
        tools = [
            ("Brush", "brush"),
            ("Pencil", "pencil"),
            ("Eraser", "eraser"),
            ("Fill", "fill"),
            ("Eyedropper", "eyedropper")
        ]

        for name, key in tools:
            btn = QPushButton(name)
            btn.setCheckable(True)
            if key == "brush": btn.setChecked(True)
            self.tool_group.addButton(btn)
            sidebar.addWidget(btn)
            btn.clicked.connect(lambda checked, k=key: self.set_tool(k))

        sidebar.addSpacing(15)
        
        # Color & Size
        sidebar.addWidget(QLabel("Brush Color"))
        self.btn_color = QPushButton()
        self.btn_color.setFixedHeight(30)
        self._update_color_button()
        self.btn_color.clicked.connect(self.pick_color)
        sidebar.addWidget(self.btn_color)

        sidebar.addWidget(QLabel(f"Size: {self.brush_size}px"))
        self.size_label = sidebar.itemAt(sidebar.count()-1).widget()
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(self.brush_size)
        self.size_slider.valueChanged.connect(self.set_brush_size)
        sidebar.addWidget(self.size_slider)

        sidebar.addSpacing(20)
        sidebar.addWidget(QLabel("History"))
        btn_undo = QPushButton("Undo")
        btn_undo.clicked.connect(self.undo)
        sidebar.addWidget(btn_undo)
        
        btn_redo = QPushButton("Redo")
        btn_redo.clicked.connect(self.redo)
        sidebar.addWidget(btn_redo)

        sidebar.addStretch(1)

        # Initial_Forms Tools Section
        sidebar.addWidget(QLabel("Initial_Forms Tools"))
        btn_downsample = QPushButton("Downsample")
        btn_downsample.clicked.connect(self.run_downsampler)
        sidebar.addWidget(btn_downsample)

        btn_mirror = QPushButton("Mirror Flip")
        btn_mirror.clicked.connect(self.run_mirror)
        sidebar.addWidget(btn_mirror)

        root.addLayout(sidebar, stretch=1)

        # 2. Main Canvas Area
        self.scene = QGraphicsScene(self)
        self.view = CanvasView(self.scene)
        self.view.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        self.view.started.connect(self.on_draw_start)
        self.view.drawing.connect(self.on_drawing)
        self.view.finished.connect(self.on_draw_finish)
        
        root.addWidget(self.view, stretch=6)

    def _setup_canvas(self) -> None:
        self.update_pixmap()
        self.scene.setSceneRect(QRectF(self.image.rect()))

    def update_pixmap(self) -> None:
        self.pixmap_item.setPixmap(QPixmap.fromImage(self.image))

    def set_tool(self, tool_name: str) -> None:
        self.current_tool = tool_name
        self.statusBar().showMessage(f"Active Tool: {tool_name.capitalize()}")

    def pick_color(self) -> None:
        color = QColorDialog.getColor(self.brush_color, self, "Select Color")
        if color.isValid():
            self.brush_color = color
            self._update_color_button()

    def _update_color_button(self) -> None:
        self.btn_color.setStyleSheet(f"background-color: {self.brush_color.name()}; border: 1px solid #555;")

    def set_brush_size(self, size: int) -> None:
        self.brush_size = size
        self.size_label.setText(f"Size: {size}px")

    def push_undo(self) -> None:
        if len(self.undo_stack) >= 50:
            self.undo_stack.pop(0)
        self.undo_stack.append(self.image.copy())
        self.redo_stack.clear()

    def undo(self) -> None:
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.image = self.undo_stack[-1].copy()
            self.update_pixmap()

    def redo(self) -> None:
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self.image = state.copy()
            self.update_pixmap()

    def on_draw_start(self, pos: QPoint) -> None:
        if not self.image.rect().contains(pos): return
        self.last_point = pos
        if self.current_tool == "fill":
            self.flood_fill(pos, self.brush_color)
        elif self.current_tool == "eyedropper":
            self.sample_color(pos)

    def on_drawing(self, pos: QPoint) -> None:
        if self.current_tool in ["brush", "pencil", "eraser"]:
            self.draw_line_to(pos)

    def on_draw_finish(self) -> None:
        if self.current_tool in ["brush", "pencil", "eraser"]:
            self.push_undo()

    def draw_line_to(self, end_point: QPoint) -> None:
        painter = QPainter(self.image)
        
        # Determine color for the tool
        draw_color = self.brush_color
        if self.current_tool == "eraser":
            draw_color = Qt.white  # Erase to background color
            
        pen = QPen(draw_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        
        if self.current_tool == "pencil":
            pen.setCapStyle(Qt.SquareCap)
            painter.setRenderHint(QPainter.Antialiasing, False)
        else:
            painter.setRenderHint(QPainter.Antialiasing, True)
            
        painter.setPen(pen)
        painter.drawLine(self.last_point, end_point)
        painter.end()
        self.last_point = end_point
        self.update_pixmap()

    def flood_fill(self, pos: QPoint, color: QColor) -> None:
        # Simple recursive fill (not for production with large areas, but okay for MVP)
        # Using a QPainter fill for now as a simpler alternative for 'fill all'
        self.push_undo()
        painter = QPainter(self.image)
        painter.fillRect(self.image.rect(), color)
        self.update_pixmap()

    def sample_color(self, pos: QPoint) -> None:
        if not self.image.rect().contains(pos): return
        color = QColor(self.image.pixel(pos))
        self.brush_color = color
        self._update_color_button()

    # --- Initial_Forms Integration ---

    def run_downsampler(self) -> None:
        val, ok = QInputDialog.getInt(self, "Downsample", "Output size (e.g. 32):", 32, 8, 512)
        if not ok: return
        
        self.push_undo()
        pil_img = qimage_to_pil(self.image)
        result_pil = downsample_image_hsv(pil_img, (val, val))
        
        # Scaling back up for display if small
        final_pil = result_pil.resize(pil_img.size, Image.NEAREST)
        self.image = pil_to_qimage(final_pil)
        self.update_pixmap()
        QMessageBox.information(self, "Done", f"Pixelated to {val}x{val}")

    def run_mirror(self) -> None:
        axes = ["horizontal", "vertical", "diagonal_tl_br", "diagonal_tr_bl"]
        axis, ok = QInputDialog.getItem(self, "Mirror", "Select axis:", axes, 0, False)
        if not ok: return
        
        self.push_undo()
        pil_img = qimage_to_pil(self.image)
        result_pil = mirror_image(pil_img, axis)
        self.image = pil_to_qimage(result_pil)
        self.update_pixmap()

    def import_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not file_path:
            return

        new_img = QImage(file_path)
        if new_img.isNull():
            QMessageBox.critical(self, "Error", "Could not load image.")
            return

        # Ask to resize canvas or scale image
        msg = QMessageBox()
        msg.setWindowTitle("Import Options")
        msg.setText("How would you like to import this image?")
        btn_resize = msg.addButton("Resize Canvas to Fit", QMessageBox.ActionRole)
        btn_scale = msg.addButton("Scale Image to Canvas", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Cancel)
        
        msg.exec_()
        
        self.push_undo()
        if msg.clickedButton() == btn_resize:
            self.image = new_img.convertToFormat(QImage.Format_ARGB32)
            self._setup_canvas()
        elif msg.clickedButton() == btn_scale:
            self.image = new_img.scaled(self.image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_ARGB32)
            self.update_pixmap()
        else:
            return

    def export_image(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", "untitled.png", "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
        )
        if file_path:
            if self.image.save(file_path):
                self.statusBar().showMessage(f"Successfully exported to {file_path}", 3000)
            else:
                QMessageBox.critical(self, "Error", "Failed to save image.")

    def closeEvent(self, event) -> None:
        # Save project data
        save_project_data(self.project_path, self.project_data)
        super().closeEvent(event)
