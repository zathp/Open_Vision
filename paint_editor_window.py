"""
Paint editor window for .ovpaint projects.

MS Paint-style direct editing with a layer system, tool palette,
Initial_Forms tool integration, and project persistence.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw
from PyQt5.QtCore import QSize, QPoint, Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
)
from PyQt5.QtWidgets import (
    QAction,
    QColorDialog,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPalette,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from OV_Libs.ExportLib.blender_export import (
    CONFLICT_NUMERIC_SUFFIX,
    CONFLICT_PROMPT,
    ExportConflictError,
    resolve_output_path,
)
from OV_Libs.Initial_Forms.integration import (
    MIRROR_AXES,
    SELECTION_MODES,
    crop_with_transparency,
    downsample_image,
    mirror_image,
    replace_color_range,
)
from OV_Libs.PaintLib.paint_layers import PaintLayerStack, PaintLayerStackError
from OV_Libs.ProjStoreLib.project_store import load_paint_project_data

CHECKER_SIZE = 8
CHECKER_LIGHT = "#ffffff"
CHECKER_DARK = "#c8c8c8"
UNDO_DEPTH = 30
ZOOM_LEVELS = (0.25, 0.5, 1.0, 2.0, 4.0)

TOOL_BRUSH = "brush"
TOOL_PENCIL = "pencil"
TOOL_ERASER = "eraser"
TOOL_FILL = "fill"
TOOL_EYEDROPPER = "eyedropper"
TOOL_SELECT = "select"

TOOL_LABELS = {
    TOOL_BRUSH: "Brush (B)",
    TOOL_PENCIL: "Pencil (P)",
    TOOL_ERASER: "Eraser (E)",
    TOOL_FILL: "Fill (F)",
    TOOL_EYEDROPPER: "Eyedropper (I)",
    TOOL_SELECT: "Rectangle Select (S)",
}


def qcolor_to_rgba(color: QColor) -> Tuple[int, int, int, int]:
    return color.red(), color.green(), color.blue(), color.alpha()


def pil_to_qimage(image: Image.Image) -> QImage:
    data = image.convert("RGBA").tobytes("raw", "RGBA")
    return QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888).copy()


class PaintCanvas(QWidget):
    """Canvas widget rendering the composited stack with zoom and overlays."""

    def __init__(self, get_composite, parent=None) -> None:
        super().__init__(parent)
        self._get_composite = get_composite
        self.zoom = 1.0
        self.show_grid = False
        self.setMouseTracking(True)

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(min(ZOOM_LEVELS), min(max(ZOOM_LEVELS), zoom))
        self.updateGeometry()
        self.update()

    def set_show_grid(self, enabled: bool) -> None:
        self.show_grid = enabled
        self.update()

    def refresh(self) -> None:
        self.update()

    def image_to_widget(self, pos: QPoint) -> Tuple[int, int]:
        return int(pos.x() / self.zoom), int(pos.y() / self.zoom)

    def sizeHint(self):
        image = self._get_composite()
        if image is None:
            return QSize(400, 300)
        return QSize(int(image.width * self.zoom), int(image.height * self.zoom))

    def minimumSizeHint(self):
        return self.sizeHint()

    def mousePressEvent(self, event):
        self.parent().on_canvas_press(event)

    def mouseMoveEvent(self, event):
        self.parent().on_canvas_move(event)

    def mouseReleaseEvent(self, event):
        self.parent().on_canvas_release(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.parent().adjust_zoom(1 if event.angleDelta().y() > 0 else -1)
        else:
            super().wheelEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        image = self._get_composite()
        if image is None:
            painter.end()
            return

        scaled_width = int(image.width * self.zoom)
        scaled_height = int(image.height * self.zoom)

        light, dark = QBrush(QColor(CHECKER_LIGHT)), QBrush(QColor(CHECKER_DARK))
        for y in range(0, scaled_height, CHECKER_SIZE):
            for x in range(0, scaled_width, CHECKER_SIZE):
                even = ((x // CHECKER_SIZE) + (y // CHECKER_SIZE)) % 2 == 0
                painter.fillRect(x, y, CHECKER_SIZE, CHECKER_SIZE, light if even else dark)

        qimage = pil_to_qimage(image).scaled(
            max(1, scaled_width),
            max(1, scaled_height),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation if self.zoom < 1.0 else Qt.FastTransformation,
        )
        painter.drawImage(0, 0, qimage)

        if self.show_grid:
            pen = QPen(QColor(0, 0, 0, 60))
            painter.setPen(pen)
            step = max(1, int(16 * self.zoom))
            for x in range(0, scaled_width, step):
                painter.drawLine(x, 0, x, scaled_height)
            for y in range(0, scaled_height, step):
                painter.drawLine(0, y, scaled_width, y)

        selection = self.parent().selection_rect
        if selection is not None:
            pen = QPen(QColor(0, 170, 255))
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(
                int(selection[0] * self.zoom),
                int(selection[1] * self.zoom),
                int((selection[2] - selection[0]) * self.zoom),
                int((selection[3] - selection[1]) * self.zoom),
            )
        painter.end()


class PaintEditorWindow(QMainWindow):
    """Main window for .ovpaint projects."""

    def __init__(self, project_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.project_path = Path(project_path)
        payload = load_paint_project_data(self.project_path)

        self.stack = PaintLayerStack.load_from_project(self.project_path)
        if self.stack.is_empty:
            self.stack = PaintLayerStack(payload["canvas_width"], payload["canvas_height"])
            base = self.stack.add_blank_layer("Background")
            ImageDraw.Draw(base.image).rectangle(
                [0, 0, self.stack.canvas_width - 1, self.stack.canvas_height - 1],
                fill=(255, 255, 255, 255),
            )

        preferences_bundle = getattr(self.stack, "_loaded_preferences", {})
        preferences = preferences_bundle.get("tool_preferences", {})
        self.export_settings: Dict[str, Any] = dict(preferences_bundle.get("export_settings", {}))

        self.foreground_color = self._load_color(preferences, "foreground_color", QColor(0, 0, 0))
        self.background_color = self._load_color(preferences, "background_color", QColor(255, 255, 255))
        self.brush_size = int(preferences.get("brush_size", 6) or 6)
        self.brush_opacity_pct = int(preferences.get("brush_opacity", 100) or 100)
        self.fill_tolerance = int(preferences.get("fill_tolerance", 32) or 32)
        self.active_tool = str(preferences.get("last_tool") or TOOL_BRUSH)

        self.selection_rect: Optional[Tuple[int, int, int, int]] = None
        self._stroke_last_point: Optional[Tuple[int, int]] = None
        self._drawing = False
        self._pan_origin: Optional[Tuple[int, int]] = None
        self._select_origin: Optional[Tuple[int, int]] = None
        self.undo_stack: List[Tuple[bytes, int, int]] = []
        self.redo_stack: List[Tuple[bytes, int, int]] = []

        self.setWindowTitle(f"Open Vision Paint - {payload['name']}")
        self.resize(1280, 800)
        self._build_ui()
        self._restore_tool_selection()
        self._refresh_layer_panel()
        self.statusBar().showMessage(f"Opened {self.project_path.name}", 3000)

    # -- UI construction -------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setBackgroundRole(QPalette.Dark)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidgetResizable(False)
        self.canvas = PaintCanvas(self.composite, self)
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll, stretch=1)
        self.scroll_area = scroll

        self.setCentralWidget(central)
        self._build_left_dock()
        self._build_right_dock()
        self._build_menus()
        self._connect_shortcuts()

    def _build_left_dock(self) -> None:
        dock = QDockWidget("Tools", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        panel = QWidget()
        column = QVBoxLayout(panel)

        tools_box = QGroupBox("Paint Tools")
        tools_grid = QGridLayout(tools_box)
        self.tool_buttons: Dict[str, QPushButton] = {}
        for index, (tool_key, label) in enumerate(TOOL_LABELS.items()):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, key=tool_key: self.select_tool(key))
            self.tool_buttons[tool_key] = button
            tools_grid.addWidget(button, index // 2, index % 2)
        column.addWidget(tools_box)

        params_box = QGroupBox("Tool Parameters")
        form = QFormLayout(params_box)

        colors_row = QHBoxLayout()
        colors_row.addWidget(QLabel("FG/BG:"))
        self.fg_button = self._make_color_button(self.foreground_color, self.pick_foreground)
        self.bg_button = self._make_color_button(self.background_color, self.pick_background)
        colors_row.addWidget(self.fg_button)
        colors_row.addWidget(self.bg_button)
        form.addRow(colors_row)

        self.size_slider, self.size_readout = self._add_slider(
            form, "Size:", 1, 200, self.brush_size, self.on_brush_size_changed
        )
        self.opacity_slider, self.opacity_readout = self._add_slider(
            form, "Opacity %:", 1, 100, self.brush_opacity_pct, self.on_brush_opacity_changed
        )

        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(0, 255)
        self.tolerance_spin.setValue(self.fill_tolerance)
        self.tolerance_spin.valueChanged.connect(self.on_fill_tolerance_changed)
        form.addRow("Fill tolerance:", self.tolerance_spin)
        column.addWidget(params_box)

        column.addWidget(self._build_downsampler_panel())
        column.addWidget(self._build_mirror_panel())
        column.addWidget(self._build_color_replace_panel())

        self.select_actions_label = QLabel("No selection")
        column.addWidget(self.select_actions_label)
        btn_crop = QPushButton("Crop Layer to Selection")
        btn_crop.clicked.connect(self.crop_to_selection)
        btn_new_from_sel = QPushButton("New Layer from Selection")
        btn_new_from_sel.clicked.connect(self.new_layer_from_selection)
        column.addWidget(btn_crop)
        column.addWidget(btn_new_from_sel)
        column.addStretch(1)

        dock.setWidget(panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def _build_downsampler_panel(self) -> QGroupBox:
        box = QGroupBox("Downsampler")
        form = QFormLayout(box)
        self.down_width_spin = QSpinBox()
        self.down_height_spin = QSpinBox()
        for spin in (self.down_width_spin, self.down_height_spin):
            spin.setRange(1, 1024)
            spin.setValue(32)
        form.addRow("Width:", self.down_width_spin)
        form.addRow("Height:", self.down_height_spin)
        apply_btn = QPushButton("Apply Downsampling")
        apply_btn.clicked.connect(self.apply_downsampler)
        form.addRow(apply_btn)
        return box

    def _build_mirror_panel(self) -> QGroupBox:
        box = QGroupBox("Mirror")
        grid = QGridLayout(box)
        labels = {
            "horizontal": "Flip H",
            "vertical": "Flip V",
            "diagonal_tl_br": "Flip TL-BR",
            "diagonal_tr_bl": "Flip TR-BL",
        }
        for index, axis in enumerate(MIRROR_AXES):
            button = QPushButton(labels[axis])
            button.clicked.connect(lambda _checked=False, a=axis: self.apply_mirror(a))
            grid.addWidget(button, index // 2, index % 2)
        return box

    def _build_color_replace_panel(self) -> QGroupBox:
        box = QGroupBox("Color Replace")
        form = QFormLayout(box)
        self.cr_base_color = QColor(0, 255, 0)
        self.cr_target_color = QColor(255, 0, 255)
        self.cr_base_button = self._make_color_button(
            self.cr_base_color, lambda: self._pick_cr_color("base")
        )
        form.addRow("Base:", self.cr_base_button)

        self.cr_mode_combo = QComboBox()
        self.cr_mode_combo.addItems(list(SELECTION_MODES))
        form.addRow("Mode:", self.cr_mode_combo)

        self.cr_tolerance_spin = QSpinBox()
        self.cr_tolerance_spin.setRange(0, 442)
        self.cr_tolerance_spin.setValue(40)
        form.addRow("Tolerance:", self.cr_tolerance_spin)

        self.cr_target_button = self._make_color_button(
            self.cr_target_color, lambda: self._pick_cr_color("target")
        )
        form.addRow("Replace with:", self.cr_target_button)

        self.cr_transparent_check = QCheckBox("Make transparent")
        form.addRow(self.cr_transparent_check)

        preview_btn = QPushButton("Preview affected count")
        preview_btn.clicked.connect(self.preview_color_replace)
        apply_btn = QPushButton("Apply Color Replace")
        apply_btn.clicked.connect(self.apply_color_replace)
        form.addRow(preview_btn)
        form.addRow(apply_btn)
        return box

    def _build_right_dock(self) -> QDockWidget:
        dock = QDockWidget("Layers", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        panel = QWidget()
        column = QVBoxLayout(panel)

        self.layer_list = QListWidget()
        self.layer_list.currentRowChanged.connect(self.on_layer_row_changed)
        column.addWidget(self.layer_list)

        controls = QGridLayout()
        specs = [
            ("Add Blank", lambda: self.layer_add_blank()),
            ("Add Image...", self.layer_add_image),
            ("Duplicate", self.layer_duplicate),
            ("Delete", self.layer_delete),
            ("Move Up", lambda: self.layer_move(-1)),
            ("Move Down", lambda: self.layer_move(1)),
            ("Merge Down", self.layer_merge_down),
            ("Flatten", self.layer_flatten),
        ]
        for index, (label, handler) in enumerate(specs):
            button = QPushButton(label)
            button.clicked.connect(handler)
            controls.addWidget(button, index // 2, index % 2)
        column.addLayout(controls)

        self.visibility_check = QCheckBox("Visible")
        self.visibility_check.stateChanged.connect(self.on_visibility_changed)
        column.addWidget(self.visibility_check)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Layer opacity (0-255):"))
        self.layer_opacity_spin = QSpinBox()
        self.layer_opacity_spin.setRange(0, 255)
        self.layer_opacity_spin.valueChanged.connect(self.on_layer_opacity_changed)
        opacity_row.addWidget(self.layer_opacity_spin)
        column.addLayout(opacity_row)

        rename_row = QHBoxLayout()
        rename_row.addWidget(QLabel("Name:"))
        self.rename_edit = QLineEdit()
        rename_row.addWidget(self.rename_edit)
        self.rename_edit.returnPressed.connect(self.on_rename_confirmed)
        column.addLayout(rename_row)

        dock.setWidget(panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        return dock

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self._action("Save Project", self.save_project))
        file_menu.addAction(self._action("Export Composite...", self.export_composite))
        file_menu.addAction(self._action("Export Active Layer...", self.export_active_layer))
        file_menu.addAction(self._action("Batch Export Layers...", self.batch_export_layers))

        edit_menu = menu_bar.addMenu("&Edit")
        self.undo_action = self._action("Undo", self.undo)
        self.redo_action = self._action("Redo", self.redo)
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self._action("Zoom In", lambda: self.adjust_zoom(1)))
        view_menu.addAction(self._action("Zoom Out", lambda: self.adjust_zoom(-1)))
        view_menu.addAction(self._action("Actual Size (100%)", self.reset_zoom))
        view_menu.addAction(self._action("Fit to Window", self.fit_to_window))
        grid_action = QAction("Show Grid", self, checkable=True)
        grid_action.toggled.connect(self.canvas.set_show_grid)
        view_menu.addAction(grid_action)

    # -- UI helpers ---------------------------------------------------------------

    @staticmethod
    def _load_color(preferences: Dict[str, Any], key: str, fallback: QColor) -> QColor:
        stored = preferences.get(key)
        if isinstance(stored, (list, tuple)) and len(stored) >= 3:
            return QColor(*[int(c) for c in stored[:4]])
        return QColor(fallback)

    @staticmethod
    def _action(text, handler, shortcut=None):
        action = QAction(text, None)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(handler)
        return action

    def _make_color_button(self, color: QColor, picker) -> QPushButton:
        button = QPushButton()
        button.setFixedSize(36, 20)
        self._style_color_button(button, color)
        button.clicked.connect(picker)
        return button

    @staticmethod
    def _style_color_button(button: QPushButton, color: QColor) -> None:
        button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")

    def _add_slider(self, form, label, low, high, value, handler):
        row = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(low, high)
        slider.setValue(value)
        readout = QLabel(str(value))
        slider.valueChanged.connect(handler)
        readout.setText(str(slider.value()))
        row.addWidget(slider)
        row.addWidget(readout)
        container = QWidget()
        container.setLayout(row)
        form.addRow(label, container)
        return slider, readout

    # -- tool state --------------------------------------------------------------

    def composite(self) -> Optional[Image.Image]:
        try:
            return self.stack.composite()
        except Exception:
            return None

    def select_tool(self, tool_key: str) -> None:
        self.active_tool = tool_key
        for key, button in self.tool_buttons.items():
            button.setChecked(key == tool_key)

    def _restore_tool_selection(self) -> None:
        if self.active_tool not in self.tool_buttons:
            self.active_tool = TOOL_BRUSH
        self.select_tool(self.active_tool)

    def pick_foreground(self):
        chosen = QColorDialog.getColor(
            self.foreground_color, self, "Foreground Color", QColorDialog.ShowAlphaChannel
        )
        if chosen.isValid():
            self.foreground_color = QColor(chosen)
            self._style_color_button(self.fg_button, self.foreground_color)

    def pick_background(self):
        chosen = QColorDialog.getColor(self.background_color, self, "Background Color")
        if chosen.isValid():
            self.background_color = QColor(chosen)
            self._style_color_button(self.bg_button, self.background_color)

    def on_brush_size_changed(self, value):
        self.brush_size = int(value)
        self.size_readout.setText(str(value))

    def on_brush_opacity_changed(self, value):
        self.brush_opacity_pct = int(value)
        self.opacity_readout.setText(str(value))

    def on_fill_tolerance_changed(self, value):
        self.fill_tolerance = int(value)

    # -- undo ---------------------------------------------------------------------

    def push_undo(self) -> None:
        active = self.stack.get_active()
        if active is None:
            return
        snapshot = (
            active.image.tobytes(),
            self.stack.canvas_width,
            self.stack.canvas_height,
        )
        self.undo_stack.append(snapshot)
        del self.undo_stack[:-UNDO_DEPTH]
        self.redo_stack.clear()

    def _pop_snapshot(self, source, target):
        if not source:
            return
        active = self.stack.get_active()
        if active is None:
            return
        target.append(
            (active.image.tobytes(), self.stack.canvas_width, self.stack.canvas_height)
        )
        blob, width, height = source.pop()
        if (width, height) != (self.stack.canvas_width, self.stack.canvas_height):
            self.stack.resize_canvas(width, height)
        active.image = Image.frombytes("RGBA", (width, height), blob)
        self.canvas.refresh()

    def undo(self):
        self._pop_snapshot(self.undo_stack, self.redo_stack)

    def redo(self):
        self._pop_snapshot(self.redo_stack, self.undo_stack)

    # -- canvas interaction ---------------------------------------------------------

    def _active_or_warn(self):
        active = self.stack.get_active()
        if active is None:
            self.statusBar().showMessage("No active layer.", 2500)
        return active

    def on_canvas_press(self, event):
        image_x, image_y = self.canvas.image_to_widget(event.pos())

        if event.button() == Qt.MiddleButton:
            self._pan_origin = (event.pos().x(), event.pos().y())
            return
        if event.button() != Qt.LeftButton:
            return

        if self.active_tool == TOOL_SELECT:
            self._select_origin = (image_x, image_y)
            return

        if self.active_tool == TOOL_EYEDROPPER:
            self._sample_color(image_x, image_y)
            return

        active = self._active_or_warn()
        if active is None or not (
            0 <= image_x < self.stack.canvas_width and 0 <= image_y < self.stack.canvas_height
        ):
            return

        if self.active_tool == TOOL_FILL:
            self.push_undo()
            try:
                ImageDraw.floodfill(
                    active.image,
                    (image_x, image_y),
                    qcolor_to_rgba(self.foreground_color),
                    thresh=self.fill_tolerance,
                )
            except Exception as error:
                QMessageBox.warning(self, "Fill Failed", str(error))
            self.canvas.refresh()
            return

        self.push_undo()
        self._drawing = True
        self._stroke_last_point = (image_x, image_y)
        self._stroke_segment(image_x, image_y, first=True)

    def _stroke_fill(self) -> Tuple[int, int, int, int]:
        color = self.foreground_color
        if self.active_tool == TOOL_ERASER:
            return (0, 0, 0, 0)
        alpha = 255 if self.active_tool == TOOL_PENCIL else max(
            1, int(color.alpha() * self.brush_opacity_pct / 100.0)
        )
        return (color.red(), color.green(), color.blue(), alpha)

    def _stroke_segment(self, image_x: int, image_y: int, first: bool = False) -> None:
        active = self.stack.get_active()
        if active is None or self._stroke_last_point is None:
            return
        fill = self._stroke_fill()
        width = 1 if self.active_tool == TOOL_PENCIL else max(1, self.brush_size)

        draw = ImageDraw.Draw(active.image)
        start = self._stroke_last_point
        draw.line([start, (image_x, image_y)], fill=fill, width=width, joint="curve")
        radius = (width - 1) // 2
        if radius > 0:
            for cx, cy in ((start,) if first else (start, (image_x, image_y))):
                draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill)
        self._stroke_last_point = (image_x, image_y)
        self.canvas.refresh()

    def on_canvas_move(self, event):
        pos = event.pos()

        if self._pan_origin is not None:
            horizontal = self.scroll_area.horizontalScrollBar()
            vertical = self.scroll_area.verticalScrollBar()
            horizontal.setValue(horizontal.value() + self._pan_origin[0] - pos.x())
            vertical.setValue(vertical.value() + self._pan_origin[1] - pos.y())
            self._pan_origin = (pos.x(), pos.y())
            return

        if self._select_origin is not None:
            image_x, image_y = self.canvas.image_to_widget(pos)
            self.selection_rect = (
                min(self._select_origin[0], image_x),
                min(self._select_origin[1], image_y),
                max(self._select_origin[0], image_x),
                max(self._select_origin[1], image_y),
            )
            self._update_selection_label()
            self.canvas.refresh()
            return

        if self._drawing:
            image_x, image_y = self.canvas.image_to_widget(pos)
            clamped_x = max(0, min(self.stack.canvas_width - 1, image_x))
            clamped_y = max(0, min(self.stack.canvas_height - 1, image_y))
            self._stroke_segment(clamped_x, clamped_y)

    def on_canvas_release(self, event):
        self._pan_origin = None
        if self._select_origin is not None:
            self._select_origin = None
            self._update_selection_label()
        if self._drawing:
            self._drawing = False
            self._stroke_last_point = None
            self.canvas.refresh()

    def _sample_color(self, image_x: int, image_y: int) -> None:
        composite = self.composite()
        if composite is None or not (
            0 <= image_x < composite.width and 0 <= image_y < composite.height
        ):
            return
        r, g, b, _ = composite.getpixel((image_x, image_y))
        self.foreground_color = QColor(r, g, b)
        self._style_color_button(self.fg_button, self.foreground_color)
        self.statusBar().showMessage(f"Picked #{r:02x}{g:02x}{b:02x}", 2000)

    def _update_selection_label(self):
        rect = self.selection_rect
        if rect is None:
            self.select_actions_label.setText("No selection")
        else:
            self.select_actions_label.setText(
                f"Selection ({rect[0]}, {rect[1]}) {rect[2] - rect[0]}x{rect[3] - rect[1]}"
            )

    # -- selection operations ----------------------------------------------------------

    def crop_to_selection(self):
        active = self._active_or_warn()
        if active is None or self.selection_rect is None:
            self.statusBar().showMessage("Select a region first.", 2500)
            return
        self.push_undo()
        active.image = crop_with_transparency(active.image, *self.selection_rect)
        self.canvas.refresh()
        self.statusBar().showMessage("Cropped active layer.", 2500)

    def new_layer_from_selection(self):
        if self.selection_rect is None:
            self.statusBar().showMessage("Select a region first.", 2500)
            return
        active = self.stack.get_active()
        if active is None:
            return
        cropped = crop_with_transparency(active.image, *self.selection_rect)
        layer = self.stack.add_image_layer(cropped, f"{active.name} cut")
        self._refresh_layer_panel(select_id=layer.id)

    # -- Initial_Forms tools ---------------------------------------------------------------

    def apply_downsampler(self):
        active = self._active_or_warn()
        if active is None:
            return
        target_size = (self.down_width_spin.value(), self.down_height_spin.value())
        self.push_undo()
        active.image = downsample_image(active.image, target_size)
        self.stack.resize_canvas(*target_size)
        self.canvas.refresh()
        self.statusBar().showMessage(f"Downsampled to {target_size[0]}x{target_size[1]}.", 3000)

    def apply_mirror(self, axis: str):
        active = self._active_or_warn()
        if active is None:
            return
        self.push_undo()
        active.image = mirror_image(active.image, axis)
        self.canvas.refresh()
        self.statusBar().showMessage(f"Mirror applied ({axis}).", 2500)

    def _pick_cr_color(self, which: str):
        current = getattr(self, f"cr_{which}_color")
        chosen = QColorDialog.getColor(current, self, "Color Replace Pick", QColorDialog.ShowAlphaChannel)
        if chosen.isValid():
            setattr(self, f"cr_{which}_color", QColor(chosen))
            button = getattr(self, f"cr_{which}_button")
            self._style_color_button(button, chosen)

    def _cr_params(self) -> Dict[str, Any]:
        mode = self.cr_mode_combo.currentText()
        tolerance = self.cr_tolerance_spin.value()
        tolerances = (tolerance,) if mode == "rgb_distance" else (tolerance, tolerance, tolerance)
        base = self.cr_base_color
        target = self.cr_target_color
        return {
            "base": (base.red(), base.green(), base.blue()),
            "tolerances": tolerances,
            "mode": mode,
            "target": (target.red(), target.green(), target.blue()),
        }

    def preview_color_replace(self):
        active = self.stack.get_active()
        if active is None:
            return
        params = self._cr_params()
        _, mask = replace_color_range(
            active.image, params["base"], params["tolerances"],
            selection_type=params["mode"], make_transparent=True,
        )
        self.statusBar().showMessage(f"{int(mask.sum())} pixels would be affected.", 4000)

    def apply_color_replace(self):
        active = self._active_or_warn()
        if active is None:
            return
        params = self._cr_params()
        self.push_undo()
        replaced, mask = replace_color_range(
            active.image,
            params["base"],
            params["tolerances"],
            replacement_color=params["target"],
            selection_type=params["mode"],
            make_transparent=self.cr_transparent_check.isChecked(),
        )
        active.image = replaced
        self.canvas.refresh()
        self.statusBar().showMessage(f"Replaced {int(mask.sum())} pixels.", 3000)

    # -- layers -----------------------------------------------------------------

    def _refresh_layer_panel(self, select_id: Optional[str] = None) -> None:
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for layer in reversed(self.stack.layers):
            state = "V" if layer.visible else "-"
            self.layer_list.addItem(QListWidgetItem(f"[{state}] {layer.name}"))
        ids = [layer.id for layer in reversed(self.stack.layers)]
        target_id = select_id or self.stack.active_id
        if target_id in ids:
            self.layer_list.setCurrentRow(ids.index(target_id))
        elif ids:
            self.layer_list.setCurrentRow(0)
        self.layer_list.blockSignals(False)
        self._sync_layer_controls()
        self.canvas.refresh()

    def _sync_layer_controls(self) -> None:
        active = self.stack.get_active()
        has_active = active is not None
        self.visibility_check.setEnabled(has_active)
        self.layer_opacity_spin.setEnabled(has_active)
        self.rename_edit.setEnabled(has_active)
        if has_active:
            self.visibility_check.blockSignals(True)
            self.visibility_check.setChecked(active.visible)
            self.visibility_check.blockSignals(False)
            self.layer_opacity_spin.blockSignals(True)
            self.layer_opacity_spin.setValue(active.opacity)
            self.layer_opacity_spin.blockSignals(False)
            self.rename_edit.setText(active.name)

    def on_layer_row_changed(self, row: int):
        ids = [layer.id for layer in reversed(self.stack.layers)]
        if 0 <= row < len(ids):
            self.stack.set_active(ids[row])
        self._sync_layer_controls()

    def on_visibility_changed(self, state):
        active = self.stack.get_active()
        if active is not None:
            active.visible = bool(state)
            self.canvas.refresh()

    def on_layer_opacity_changed(self, value):
        active = self.stack.get_active()
        if active is not None:
            active.opacity = int(value)
            self.canvas.refresh()

    def on_rename_confirmed(self):
        active = self.stack.get_active()
        name = self.rename_edit.text().strip()
        if active is not None and name:
            active.name = name
            self._refresh_layer_panel(select_id=active.id)

    def layer_add_blank(self):
        layer = self.stack.add_blank_layer()
        self._refresh_layer_panel(select_id=layer.id)

    def layer_add_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Image Layer", self.export_settings.get("last_directory", ""),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            return
        try:
            image = Image.open(path).convert("RGBA")
        except Exception as error:
            QMessageBox.warning(self, "Load Failed", str(error))
            return
        layer = self.stack.add_image_layer(image, Path(path).stem)
        self.export_settings["last_directory"] = str(Path(path).parent)
        self._refresh_layer_panel(select_id=layer.id)

    def layer_duplicate(self):
        if self.stack.active_id is None:
            return
        copy = self.stack.duplicate_layer(self.stack.active_id)
        self._refresh_layer_panel(select_id=copy.id)

    def layer_delete(self):
        active = self.stack.get_active()
        if active is None:
            return
        answer = QMessageBox.question(
            self, "Delete Layer", f"Delete layer '{active.name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.stack.delete_layer(self.stack.active_id)
        except PaintLayerStackError as error:
            QMessageBox.warning(self, "Delete Failed", str(error))
            return
        self._refresh_layer_panel()

    def layer_move(self, offset: int):
        if self.stack.active_id is None:
            return
        self.stack.move_layer(self.stack.active_id, offset)
        self._refresh_layer_panel(select_id=self.stack.active_id)

    def layer_merge_down(self):
        if self.stack.active_id is None:
            return
        try:
            merged = self.stack.merge_down(self.stack.active_id)
        except PaintLayerStackError as error:
            QMessageBox.information(self, "Merge Down", str(error))
            return
        self._refresh_layer_panel(select_id=merged.id)

    def layer_flatten(self):
        flattened = self.stack.flatten_visible()
        self._refresh_layer_panel(select_id=flattened.id)

    # -- zoom ------------------------------------------------------------

    def adjust_zoom(self, direction: int):
        current = self.canvas.zoom
        if direction > 0:
            candidates = [z for z in ZOOM_LEVELS if z > current + 1e-9]
            target = candidates[0] if candidates else max(ZOOM_LEVELS)
        else:
            candidates = [z for z in reversed(ZOOM_LEVELS) if z < current - 1e-9]
            target = candidates[0] if candidates else min(ZOOM_LEVELS)
        self.canvas.set_zoom(target)
        self.statusBar().showMessage(f"Zoom {int(target * 100)}%", 1500)

    def reset_zoom(self):
        self.canvas.set_zoom(1.0)
        self.statusBar().showMessage("Zoom 100%", 1500)

    def fit_to_window(self):
        composite = self.composite()
        if composite is None:
            return
        viewport = self.scroll_area.viewport().size()
        scale = min(viewport.width() / composite.width, viewport.height() / composite.height)
        closest = min(ZOOM_LEVELS, key=lambda z: abs(z - scale))
        self.canvas.set_zoom(closest)
        self.statusBar().showMessage(f"Fit to window: {int(closest * 100)}%", 2000)

    # -- persistence / export ---------------------------------------------

    def collect_tool_preferences(self) -> Dict[str, Any]:
        return {
            "last_tool": self.active_tool,
            "foreground_color": [
                self.foreground_color.red(), self.foreground_color.green(),
                self.foreground_color.blue(), self.foreground_color.alpha(),
            ],
            "background_color": [
                self.background_color.red(), self.background_color.green(),
                self.background_color.blue(), self.background_color.alpha(),
            ],
            "brush_size": self.brush_size,
            "brush_opacity": self.brush_opacity_pct,
            "fill_tolerance": self.fill_tolerance,
        }

    def save_project(self):
        try:
            self.stack.save_to_project(
                self.project_path,
                self.collect_tool_preferences(),
                self.export_settings,
            )
        except Exception as error:
            QMessageBox.critical(self, "Save Failed", str(error))
            return
        self.statusBar().showMessage(f"Saved {self.project_path.name}", 3000)

    def closeEvent(self, event):
        self.save_project()
        super().closeEvent(event)

    def _export_conflict_callback(self, candidate: Path) -> Optional[Path]:
        answer = QMessageBox.question(
            self, "File Exists",
            f"{candidate.name} already exists.\nOverwrite?",
            QMessageBox.Yes | QMessageBox.No,
        )
        return candidate if answer == QMessageBox.Yes else None

    def _save_pil_dialog(self, suggested_name: str):
        last_dir = self.export_settings.get("last_directory", str(Path.home()))
        target_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Image", str(Path(last_dir) / suggested_name),
            "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)",
        )
        if not target_path:
            return None
        save_format = Path(target_path).suffix.lstrip(".").upper() or "PNG"
        save_format = "JPEG" if save_format == "JPG" else save_format
        directory = Path(target_path).parent
        try:
            written = resolve_output_path(
                directory, Path(target_path).name, CONFLICT_PROMPT,
                prompt_callback=self._export_conflict_callback,
            )
        except ExportConflictError:
            return None
        self.export_settings["last_directory"] = str(directory)
        return written, save_format

    def export_composite(self):
        composite = self.composite()
        if composite is None:
            return
        plan = self._save_pil_dialog(f"{self.project_path.stem}.png")
        if plan is None:
            return
        path, save_format = plan
        try:
            image = composite
            if save_format == "JPEG":
                background = Image.new("RGBA", image.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, image.convert("RGBA")).convert("RGB")
            image.save(path, format=save_format)
        except Exception as error:
            QMessageBox.warning(self, "Export Failed", str(error))
            return
        self.statusBar().showMessage(f"Exported {Path(path).name}", 3000)

    def export_active_layer(self):
        active = self.stack.get_active()
        if active is None:
            self.statusBar().showMessage("No active layer.", 2500)
            return
        plan = self._save_pil_dialog(f"{self.project_path.stem}_{active.name}.png")
        if plan is None:
            return
        path, save_format = plan
        try:
            image = active.image
            if save_format == "JPEG":
                background = Image.new("RGBA", image.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, image.convert("RGBA")).convert("RGB")
            image.save(path, format=save_format)
        except Exception as error:
            QMessageBox.warning(self, "Export Failed", str(error))
            return
        self.statusBar().showMessage(f"Exported {Path(path).name}", 3000)

    def batch_export_layers(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Batch Export Layers", self.export_settings.get("last_directory", "")
        )
        if not directory:
            return
        errors: List[str] = []
        exported = 0
        for layer in self.stack.layers:
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in layer.name)
            try:
                path = resolve_output_path(
                    Path(directory),
                    f"{self.project_path.stem}_{safe_name}.png",
                    CONFLICT_NUMERIC_SUFFIX,
                )
                layer.image.save(path, format="PNG")
                exported += 1
            except Exception as error:
                errors.append(f"{layer.name}: {error}")
        self.export_settings["last_directory"] = directory
        if errors:
            QMessageBox.warning(self, "Batch Export Warnings", "\n".join(errors[:10]))
        self.statusBar().showMessage(
            f"Exported {exported}/{len(self.stack.layers)} layers to {directory}", 4000
        )

    # -- shortcuts -------------------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        tool_hotkeys = {
            Qt.Key_B: TOOL_BRUSH, Qt.Key_P: TOOL_PENCIL, Qt.Key_E: TOOL_ERASER,
            Qt.Key_F: TOOL_FILL, Qt.Key_I: TOOL_EYEDROPPER, Qt.Key_S: TOOL_SELECT,
        }
        if key in tool_hotkeys and not event.modifiers():
            self.select_tool(tool_hotkeys[key])
            return
        if key in (Qt.Key_BracketLeft, Qt.Key_BracketRight) and not event.modifiers():
            delta = -2 if key == Qt.Key_BracketLeft else 2
            self.size_slider.setValue(max(1, self.size_slider.value() + delta))
            return
        if key == Qt.Key_Plus:
            self.adjust_zoom(1)
            return
        if key == Qt.Key_Minus:
            self.adjust_zoom(-1)
            return
        super().keyPressEvent(event)

    def _connect_shortcuts(self):
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_project)
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo)
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.redo)
