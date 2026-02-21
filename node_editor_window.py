import json
import io
import math
import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QLineF, QPoint, QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QImage, QKeySequence, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from OV_Libs.ProjStoreLib.node_executors import get_default_registry
from OV_Libs.ProjStoreLib.pipeline_builder import (
    build_pipeline_from_graph,
    build_update_pipeline,
    execute_pipeline,
    get_pipeline_summary,
)
from OV_Libs.ProjStoreLib.project_store import load_project_graph, save_project_graph


class NodeParameterEditorDialog(QDialog):
    IMAGE_FILE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.gif);;All Files (*)"
    ALL_FILE_FILTER = "All Files (*)"
    ENUM_OPTIONS: Dict[str, List[str]] = {
        "selection_type": ["rgb_distance", "rgb_range", "hsv_range"],
        "shift_type": ["absolute_rgb", "absolute_hsv", "percentile_rgb", "percentile_hsv", "match_distance_rgb"],
        "distance_type": ["euclidean", "manhattan", "chebyshev"],
        "blur_type": ["gaussian", "box", "motion", "radial"],
        "format_type": ["image", "gif", "movie"],
        "save_format": ["PNG", "JPG", "JPEG", "BMP", "WEBP", "TIFF", "GIF"],
        "blend_mode": ["alpha", "normal", "multiply", "screen", "overlay"],
        "output_mode": ["RGBA", "RGB", "L"],
    }
    NUMERIC_SPECS: Dict[str, Tuple[float, float, int, float]] = {
        "base_color_r": (0.0, 255.0, 0, 1.0),
        "base_color_g": (0.0, 255.0, 0, 1.0),
        "base_color_b": (0.0, 255.0, 0, 1.0),
        "base_color_a": (0.0, 255.0, 0, 1.0),
        "output_color_r": (0.0, 255.0, 0, 1.0),
        "output_color_g": (0.0, 255.0, 0, 1.0),
        "output_color_b": (0.0, 255.0, 0, 1.0),
        "output_color_a": (0.0, 255.0, 0, 1.0),
        "tolerance": (0.0, 255.0, 0, 1.0),
        "shift_amount": (-255.0, 255.0, 1, 1.0),
        "gaussian_radius": (0.0, 100.0, 1, 0.5),
        "box_kernel": (1.0, 101.0, 0, 2.0),
        "motion_angle": (0.0, 360.0, 1, 1.0),
        "motion_distance": (1.0, 100.0, 0, 1.0),
        "radial_strength": (1.0, 50.0, 1, 0.5),
        "max_radius": (1.0, 100.0, 1, 0.5),
        "quality": (1.0, 100.0, 0, 1.0),
        "version": (1.0, 100000.0, 0, 1.0),
        "frame_index": (0.0, 100000.0, 0, 1.0),
    }
    BLUR_PARAM_KEYS_BY_TYPE: Dict[str, List[str]] = {
        "gaussian": ["gaussian_radius"],
        "box": ["box_kernel"],
        "motion": ["motion_angle", "motion_distance"],
        "radial": ["radial_strength", "radial_center_x", "radial_center_y"],
    }

    def __init__(self, node_type: str, properties: Dict[str, object], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit {node_type} Parameters")
        self.resize(860, 600)

        self.node_type = str(node_type)
        self._properties: Dict[str, object] = {}
        self._value_getters: Dict[str, Callable[[], object]] = {}
        self._selection_type_combo: Optional[QComboBox] = None
        self._tolerance_mode_updater: Optional[Callable[[], None]] = None
        self._shift_type_combo: Optional[QComboBox] = None
        self._shift_amount_mode_updater: Optional[Callable[[], None]] = None
        self._blur_type_combo: Optional[QComboBox] = None
        self._field_labels: Dict[str, QLabel] = {}
        self._field_editors: Dict[str, QWidget] = {}
        self._color_shift_preview_before: Optional[QLabel] = None
        self._color_shift_preview_mask: Optional[QLabel] = None
        self._color_shift_preview_after: Optional[QLabel] = None
        self._color_shift_target_chip: Optional[QLabel] = None
        self._color_shift_output_chip: Optional[QLabel] = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Use labeled controls for each parameter. "
                "For advanced edits, use Advanced JSON."
            )
        )

        self.form_widget = QWidget(self)
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.form_layout.setLabelAlignment(Qt.AlignTop)
        layout.addWidget(self.form_widget)

        if self.node_type == "Color Shift":
            preview_container = QWidget(self)
            preview_layout = QHBoxLayout(preview_container)
            preview_layout.setContentsMargins(0, 0, 0, 0)

            def build_preview_column(title: str) -> QLabel:
                column = QWidget(self)
                column_layout = QVBoxLayout(column)
                column_layout.setContentsMargins(0, 0, 0, 0)
                column_layout.addWidget(QLabel(title, self))

                image_label = QLabel("Preparing preview...", self)
                image_label.setFixedSize(190, 90)
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setStyleSheet("border: 1px solid #5a5a5a; background: #202020; color: #a8a8a8;")
                column_layout.addWidget(image_label)
                preview_layout.addWidget(column)
                return image_label

            self._color_shift_preview_before = build_preview_column("Before")
            self._color_shift_preview_mask = build_preview_column("Mask")
            self._color_shift_preview_after = build_preview_column("After")
            layout.addWidget(preview_container)

        self.btn_advanced_json = QPushButton("Advanced JSON...")
        layout.addWidget(self.btn_advanced_json)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)
        self.btn_advanced_json.clicked.connect(self.open_advanced_json_editor)
        self.button_box.accepted.connect(self._try_accept)
        self.button_box.rejected.connect(self.reject)

        self._build_form(properties)

    def _ordered_keys(self, properties: Dict[str, object]) -> List[str]:
        preferred_order = [
            "file_path",
            "format_type",
            "frame_index",
            "cache_image",
            "base_color_r",
            "base_color_g",
            "base_color_b",
            "base_color_a",
            "output_color_r",
            "output_color_g",
            "output_color_b",
            "output_color_a",
            "selection_type",
            "tolerance",
            "distance_type",
            "shift_type",
            "shift_amount",
            "output_mask",
            "blur_type",
            "gaussian_radius",
            "box_kernel",
            "motion_angle",
            "motion_distance",
            "radial_strength",
            "max_radius",
            "output_path",
            "save_format",
            "quality",
            "version",
            "auto_increment_counter",
            "create_directories",
            "overwrite",
        ]
        index_map = {key: index for index, key in enumerate(preferred_order)}
        return sorted(properties.keys(), key=lambda key: (index_map.get(key, 999), key.lower()))

    def _build_form(self, properties: Dict[str, object]) -> None:
        self._value_getters = {}
        self._selection_type_combo = None
        self._tolerance_mode_updater = None
        self._shift_type_combo = None
        self._shift_amount_mode_updater = None
        self._blur_type_combo = None
        self._field_labels = {}
        self._field_editors = {}
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)

        if not properties:
            label = QLabel("No editable parameters for this node.")
            self.form_layout.addRow(label)
            return

        for key in self._ordered_keys(properties):
            label_text = self._label_for_key(key)
            editor_widget, getter = self._create_editor_widget(key, properties[key])
            self._value_getters[key] = getter
            label_widget = QLabel(label_text)
            self._field_labels[key] = label_widget
            self._field_editors[key] = editor_widget
            self.form_layout.addRow(label_widget, editor_widget)

        if self.node_type == "Color Shift":
            self._add_color_shift_palette_selector()

        self._update_blur_field_visibility()
        self._update_color_shift_field_visibility()

        if self.node_type == "Color Shift":
            self._connect_color_shift_preview_updates()
            self._update_color_shift_preview()

    @staticmethod
    def _label_for_key(key: str) -> str:
        return key.replace("_", " ").title()

    def _create_editor_widget(self, key: str, value: object) -> Tuple[QWidget, Callable[[], object]]:
        if self.node_type == "Color Shift" and key == "tolerance":
            return self._create_color_shift_tolerance_editor(value)

        if self.node_type == "Color Shift" and key == "shift_amount":
            return self._create_color_shift_shift_amount_editor(value)

        if key in self.ENUM_OPTIONS:
            combo = QComboBox(self)
            options = self.ENUM_OPTIONS[key]
            combo.addItems(options)
            current_value = str(value)
            if current_value and combo.findText(current_value) == -1:
                combo.addItem(current_value)
            combo.setCurrentText(current_value if current_value else options[0])

            if self.node_type == "Color Shift" and key == "selection_type":
                self._selection_type_combo = combo
                if self._tolerance_mode_updater is not None:
                    combo.currentTextChanged.connect(lambda _value: self._tolerance_mode_updater())
                    self._tolerance_mode_updater()

            if self.node_type == "Blur" and key == "blur_type":
                self._blur_type_combo = combo
                combo.currentTextChanged.connect(lambda _value: self._update_blur_field_visibility())

            if self.node_type == "Color Shift" and key == "shift_type":
                self._shift_type_combo = combo
                if self._shift_amount_mode_updater is not None:
                    combo.currentTextChanged.connect(lambda _value: self._shift_amount_mode_updater())
                    self._shift_amount_mode_updater()
                combo.currentTextChanged.connect(lambda _value: self._update_color_shift_field_visibility())

            return combo, combo.currentText

        if isinstance(value, bool):
            checkbox = QCheckBox(self)
            checkbox.setChecked(bool(value))
            return checkbox, checkbox.isChecked

        if isinstance(value, int) and not isinstance(value, bool):
            return self._create_numeric_editor(key, float(value), is_integer=True)

        if isinstance(value, float):
            return self._create_numeric_editor(key, value, is_integer=False)

        if isinstance(value, (list, tuple, dict)):
            text = QPlainTextEdit(self)
            text.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
            text.setFixedHeight(90)
            return text, lambda: self._parse_json_text(text.toPlainText())

        if key.endswith("_path"):
            return self._create_path_editor(key, str(value) if value is not None else "")

        line_edit = QLineEdit(self)
        line_edit.setText("" if value is None else str(value))
        return line_edit, line_edit.text

    def _create_numeric_editor(self, key: str, value: float, is_integer: bool) -> Tuple[QWidget, Callable[[], object]]:
        spec = self.NUMERIC_SPECS.get(key)
        container = QWidget(self)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)

        if spec is None:
            if is_integer:
                spin = QSpinBox(self)
                spin.setMinimum(-1_000_000)
                spin.setMaximum(1_000_000)
                spin.setValue(int(value))
                row.addWidget(spin)
                return container, spin.value

            spinf = QDoubleSpinBox(self)
            spinf.setDecimals(4)
            spinf.setMinimum(-1_000_000.0)
            spinf.setMaximum(1_000_000.0)
            spinf.setSingleStep(0.1)
            spinf.setValue(float(value))
            row.addWidget(spinf)
            return container, spinf.value

        min_value, max_value, decimals, step = spec

        scale = 10 ** decimals
        slider = QSlider(Qt.Horizontal, self)
        slider.setMinimum(int(round(min_value * scale)))
        slider.setMaximum(int(round(max_value * scale)))
        row.addWidget(slider, stretch=3)

        if is_integer and decimals == 0:
            spin = QSpinBox(self)
            spin.setMinimum(int(min_value))
            spin.setMaximum(int(max_value))
            spin.setSingleStep(max(1, int(step)))
            spin.setValue(int(round(value)))

            def on_slider_change(raw: int) -> None:
                spin.blockSignals(True)
                spin.setValue(raw)
                spin.blockSignals(False)

            def on_spin_change(new_value: int) -> None:
                slider.blockSignals(True)
                slider.setValue(new_value)
                slider.blockSignals(False)

            slider.valueChanged.connect(on_slider_change)
            spin.valueChanged.connect(on_spin_change)
            slider.setValue(spin.value())
            row.addWidget(spin, stretch=1)
            return container, spin.value

        spinf = QDoubleSpinBox(self)
        spinf.setDecimals(decimals)
        spinf.setMinimum(min_value)
        spinf.setMaximum(max_value)
        spinf.setSingleStep(step)
        spinf.setValue(float(value))

        def on_slider_change(raw: int) -> None:
            mapped = float(raw) / scale
            spinf.blockSignals(True)
            spinf.setValue(mapped)
            spinf.blockSignals(False)

        def on_spinf_change(new_value: float) -> None:
            slider.blockSignals(True)
            slider.setValue(int(round(new_value * scale)))
            slider.blockSignals(False)

        slider.valueChanged.connect(on_slider_change)
        spinf.valueChanged.connect(on_spinf_change)
        slider.setValue(int(round(spinf.value() * scale)))
        row.addWidget(spinf, stretch=1)

        if is_integer:
            return container, lambda: int(round(spinf.value()))
        return container, spinf.value

    def _create_path_editor(self, key_name: str, value: str) -> Tuple[QWidget, Callable[[], object]]:
        container = QWidget(self)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)

        line_edit = QLineEdit(self)
        line_edit.setText(value)
        browse = QPushButton("Browse...", self)

        def choose_file() -> None:
            dialog_filter = self._file_filter_for_key(key_name)
            if self.node_type == "Output" and key_name in {"output_path", "file_path"}:
                selected_file, _ = QFileDialog.getSaveFileName(self, "Select Output File", line_edit.text(), dialog_filter)
            else:
                selected_file, _ = QFileDialog.getOpenFileName(self, "Select File", line_edit.text(), dialog_filter)

            if selected_file:
                line_edit.setText(selected_file)

        browse.clicked.connect(choose_file)
        row.addWidget(line_edit, stretch=1)
        row.addWidget(browse)
        return container, line_edit.text

    def _create_color_shift_tolerance_editor(self, value: object) -> Tuple[QWidget, Callable[[], object]]:
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            h_value = int(float(value[0]))
            s_value = int(float(value[1]))
            v_value = int(float(value[2]))
            scalar_value = max(h_value, s_value, v_value)
        else:
            scalar = int(float(value)) if isinstance(value, (int, float)) else 30
            h_value = scalar
            s_value = scalar
            v_value = scalar
            scalar_value = scalar

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        scalar_group = QWidget(self)
        scalar_layout = QVBoxLayout(scalar_group)
        scalar_layout.setContentsMargins(0, 0, 0, 0)
        scalar_layout.addWidget(QLabel("Tolerance"))
        scalar_widget, scalar_getter = self._create_channel_slider("Value", scalar_value, 0, 255)
        scalar_layout.addWidget(scalar_widget)

        hsv_group = QWidget(self)
        hsv_layout = QVBoxLayout(hsv_group)
        hsv_layout.setContentsMargins(0, 0, 0, 0)
        hsv_layout.addWidget(QLabel("HSV Tolerance"))

        h_widget, h_getter = self._create_channel_slider("H", h_value, 0, 180)
        s_widget, s_getter = self._create_channel_slider("S", s_value, 0, 255)
        v_widget, v_getter = self._create_channel_slider("V", v_value, 0, 255)
        hsv_layout.addWidget(h_widget)
        hsv_layout.addWidget(s_widget)
        hsv_layout.addWidget(v_widget)

        layout.addWidget(scalar_group)
        layout.addWidget(hsv_group)

        def update_mode() -> None:
            selection_mode = ""
            if self._selection_type_combo is not None:
                selection_mode = self._selection_type_combo.currentText().strip().lower()

            use_hsv = selection_mode == "hsv_range"
            if not selection_mode:
                use_hsv = isinstance(value, (list, tuple))

            hsv_group.setVisible(use_hsv)
            scalar_group.setVisible(not use_hsv)

        self._tolerance_mode_updater = update_mode
        if self._selection_type_combo is not None:
            self._selection_type_combo.currentTextChanged.connect(lambda _value: update_mode())
        update_mode()

        def read_tolerance() -> object:
            if hsv_group.isVisible():
                return [h_getter(), s_getter(), v_getter()]
            return float(scalar_getter())

        return container, read_tolerance

    def _create_signed_channel_slider(
        self,
        channel_name: str,
        initial: int,
        min_value: int,
        max_value: int,
    ) -> Tuple[QWidget, Callable[[], int]]:
        row_widget = QWidget(self)
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"{channel_name}:")
        slider = QSlider(Qt.Horizontal, self)
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        spin = QSpinBox(self)
        spin.setMinimum(min_value)
        spin.setMaximum(max_value)

        clamped_initial = max(min_value, min(max_value, int(initial)))
        slider.setValue(clamped_initial)
        spin.setValue(clamped_initial)

        def on_slider_change(raw: int) -> None:
            spin.blockSignals(True)
            spin.setValue(raw)
            spin.blockSignals(False)

        def on_spin_change(new_value: int) -> None:
            slider.blockSignals(True)
            slider.setValue(new_value)
            slider.blockSignals(False)

        slider.valueChanged.connect(on_slider_change)
        spin.valueChanged.connect(on_spin_change)

        row.addWidget(label)
        row.addWidget(slider, stretch=1)
        row.addWidget(spin)
        return row_widget, spin.value

    def _create_color_shift_shift_amount_editor(self, value: object) -> Tuple[QWidget, Callable[[], object]]:
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            channel_1 = int(float(value[0]))
            channel_2 = int(float(value[1]))
            channel_3 = int(float(value[2]))
            scalar_value = channel_1
        else:
            scalar = int(float(value)) if isinstance(value, (int, float)) else 50
            channel_1 = scalar
            channel_2 = scalar
            channel_3 = scalar
            scalar_value = scalar

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        scalar_group = QWidget(self)
        scalar_layout = QVBoxLayout(scalar_group)
        scalar_layout.setContentsMargins(0, 0, 0, 0)
        scalar_layout.addWidget(QLabel("Shift Amount"))
        scalar_widget, scalar_getter = self._create_signed_channel_slider("Value", scalar_value, -255, 255)
        scalar_layout.addWidget(scalar_widget)

        component_group = QWidget(self)
        component_layout = QVBoxLayout(component_group)
        component_layout.setContentsMargins(0, 0, 0, 0)
        component_header = QLabel("Channel Shift")
        component_layout.addWidget(component_header)

        channel_a_widget, channel_a_getter = self._create_signed_channel_slider("R", channel_1, -255, 255)
        channel_b_widget, channel_b_getter = self._create_signed_channel_slider("G", channel_2, -255, 255)
        channel_c_widget, channel_c_getter = self._create_signed_channel_slider("B", channel_3, -255, 255)

        component_layout.addWidget(channel_a_widget)
        component_layout.addWidget(channel_b_widget)
        component_layout.addWidget(channel_c_widget)

        layout.addWidget(scalar_group)
        layout.addWidget(component_group)

        def update_mode() -> None:
            shift_mode = ""
            if self._shift_type_combo is not None:
                shift_mode = self._shift_type_combo.currentText().strip().lower()

            if not shift_mode and isinstance(value, (list, tuple)):
                shift_mode = "absolute_rgb"

            use_components = shift_mode in {
                "absolute_rgb",
                "absolute_hsv",
                "percentile_rgb",
                "percentile_hsv",
            }

            component_group.setVisible(use_components)
            scalar_group.setVisible(not use_components)

            if shift_mode.endswith("hsv"):
                component_header.setText("HSV Shift")
                channel_a_widget.findChildren(QLabel)[0].setText("H:")
                channel_b_widget.findChildren(QLabel)[0].setText("S:")
                channel_c_widget.findChildren(QLabel)[0].setText("V:")
            else:
                component_header.setText("RGB Shift")
                channel_a_widget.findChildren(QLabel)[0].setText("R:")
                channel_b_widget.findChildren(QLabel)[0].setText("G:")
                channel_c_widget.findChildren(QLabel)[0].setText("B:")

        self._shift_amount_mode_updater = update_mode
        if self._shift_type_combo is not None:
            self._shift_type_combo.currentTextChanged.connect(lambda _value: update_mode())
        update_mode()

        def read_shift_amount() -> object:
            if component_group.isVisible():
                return (
                    float(channel_a_getter()),
                    float(channel_b_getter()),
                    float(channel_c_getter()),
                )
            return float(scalar_getter())

        return container, read_shift_amount

    def _create_channel_slider(self, channel_name: str, initial: int, min_value: int, max_value: int) -> Tuple[QWidget, Callable[[], int]]:
        row_widget = QWidget(self)
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"{channel_name}:")
        slider = QSlider(Qt.Horizontal, self)
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        spin = QSpinBox(self)
        spin.setMinimum(min_value)
        spin.setMaximum(max_value)

        clamped_initial = max(min_value, min(max_value, int(initial)))
        slider.setValue(clamped_initial)
        spin.setValue(clamped_initial)

        def on_slider_change(raw: int) -> None:
            spin.blockSignals(True)
            spin.setValue(raw)
            spin.blockSignals(False)

        def on_spin_change(new_value: int) -> None:
            slider.blockSignals(True)
            slider.setValue(new_value)
            slider.blockSignals(False)

        slider.valueChanged.connect(on_slider_change)
        spin.valueChanged.connect(on_spin_change)

        row.addWidget(label)
        row.addWidget(slider, stretch=1)
        row.addWidget(spin)
        return row_widget, spin.value

    def _update_blur_field_visibility(self) -> None:
        if self.node_type != "Blur":
            return

        all_blur_keys = {
            key
            for keys in self.BLUR_PARAM_KEYS_BY_TYPE.values()
            for key in keys
        }
        existing_blur_keys = [key for key in all_blur_keys if key in self._field_labels]
        if not existing_blur_keys:
            return

        blur_type = ""
        if self._blur_type_combo is not None:
            blur_type = self._blur_type_combo.currentText().strip().lower()

        visible_keys = set(self.BLUR_PARAM_KEYS_BY_TYPE.get(blur_type, existing_blur_keys))
        for key in existing_blur_keys:
            visible = key in visible_keys
            label = self._field_labels.get(key)
            editor = self._field_editors.get(key)
            if label is not None:
                label.setVisible(visible)
            if editor is not None:
                editor.setVisible(visible)

    def _update_color_shift_field_visibility(self) -> None:
        if self.node_type != "Color Shift":
            return

        shift_mode = ""
        if self._shift_type_combo is not None:
            shift_mode = self._shift_type_combo.currentText().strip().lower()

        show_output_base = shift_mode == "match_distance_rgb"
        output_keys = ["output_color_r", "output_color_g", "output_color_b", "output_color_a"]
        for key in output_keys:
            label = self._field_labels.get(key)
            editor = self._field_editors.get(key)
            if label is not None:
                label.setVisible(show_output_base)
            if editor is not None:
                editor.setVisible(show_output_base)

        shift_label = self._field_labels.get("shift_amount")
        shift_editor = self._field_editors.get("shift_amount")
        show_shift_amount = shift_mode != "match_distance_rgb"
        if shift_label is not None:
            shift_label.setVisible(show_shift_amount)
        if shift_editor is not None:
            shift_editor.setVisible(show_shift_amount)

    def _add_color_shift_palette_selector(self) -> None:
        required_keys = {
            "base_color_r",
            "base_color_g",
            "base_color_b",
            "base_color_a",
            "output_color_r",
            "output_color_g",
            "output_color_b",
            "output_color_a",
        }
        if not required_keys.issubset(set(self._field_editors.keys())):
            return

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        top_row = QWidget(self)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self._color_shift_target_chip = QLabel(self)
        self._color_shift_target_chip.setFixedSize(46, 24)
        self._color_shift_target_chip.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self._color_shift_target_chip)

        pick_button = QPushButton("Pick Input Base Color...", self)
        pick_button.clicked.connect(self._open_color_shift_target_color_picker)
        top_layout.addWidget(pick_button)
        top_layout.addStretch(1)

        layout.addWidget(top_row)

        swatch_row = QWidget(self)
        swatch_layout = QHBoxLayout(swatch_row)
        swatch_layout.setContentsMargins(0, 0, 0, 0)
        swatch_layout.setSpacing(6)

        swatches = [
            (255, 0, 0),
            (255, 128, 0),
            (255, 255, 0),
            (0, 255, 0),
            (0, 255, 255),
            (0, 0, 255),
            (255, 0, 255),
            (255, 255, 255),
            (192, 192, 192),
            (128, 128, 128),
            (64, 64, 64),
            (0, 0, 0),
        ]
        for red, green, blue in swatches:
            swatch_button = QPushButton("", self)
            swatch_button.setFixedSize(22, 22)
            swatch_button.setToolTip(f"R:{red} G:{green} B:{blue}")
            swatch_button.setStyleSheet(
                f"background-color: rgb({red}, {green}, {blue}); border: 1px solid #777777;"
            )
            swatch_button.clicked.connect(
                lambda _checked=False, r=red, g=green, b=blue: self._set_color_shift_target_color(r, g, b)
            )
            swatch_layout.addWidget(swatch_button)

        swatch_layout.addStretch(1)
        layout.addWidget(swatch_row)
        self.form_layout.insertRow(0, "Input Base Color", container)

        output_container = QWidget(self)
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)

        output_top_row = QWidget(self)
        output_top_layout = QHBoxLayout(output_top_row)
        output_top_layout.setContentsMargins(0, 0, 0, 0)

        self._color_shift_output_chip = QLabel(self)
        self._color_shift_output_chip.setFixedSize(46, 24)
        self._color_shift_output_chip.setAlignment(Qt.AlignCenter)
        output_top_layout.addWidget(self._color_shift_output_chip)

        output_pick_button = QPushButton("Pick Output Base Color...", self)
        output_pick_button.clicked.connect(self._open_color_shift_output_color_picker)
        output_top_layout.addWidget(output_pick_button)
        output_top_layout.addStretch(1)
        output_layout.addWidget(output_top_row)

        output_swatch_row = QWidget(self)
        output_swatch_layout = QHBoxLayout(output_swatch_row)
        output_swatch_layout.setContentsMargins(0, 0, 0, 0)
        output_swatch_layout.setSpacing(6)
        for red, green, blue in swatches:
            swatch_button = QPushButton("", self)
            swatch_button.setFixedSize(22, 22)
            swatch_button.setToolTip(f"R:{red} G:{green} B:{blue}")
            swatch_button.setStyleSheet(
                f"background-color: rgb({red}, {green}, {blue}); border: 1px solid #777777;"
            )
            swatch_button.clicked.connect(
                lambda _checked=False, r=red, g=green, b=blue: self._set_color_shift_output_color(r, g, b)
            )
            output_swatch_layout.addWidget(swatch_button)
        output_swatch_layout.addStretch(1)
        output_layout.addWidget(output_swatch_row)
        self.form_layout.addRow("Output Base Color", output_container)

        self._connect_widget_change_signal(self._field_editors.get("base_color_r"), self._update_color_shift_target_chip)
        self._connect_widget_change_signal(self._field_editors.get("base_color_g"), self._update_color_shift_target_chip)
        self._connect_widget_change_signal(self._field_editors.get("base_color_b"), self._update_color_shift_target_chip)
        self._connect_widget_change_signal(self._field_editors.get("base_color_a"), self._update_color_shift_target_chip)
        self._connect_widget_change_signal(self._field_editors.get("output_color_r"), self._update_color_shift_output_chip)
        self._connect_widget_change_signal(self._field_editors.get("output_color_g"), self._update_color_shift_output_chip)
        self._connect_widget_change_signal(self._field_editors.get("output_color_b"), self._update_color_shift_output_chip)
        self._connect_widget_change_signal(self._field_editors.get("output_color_a"), self._update_color_shift_output_chip)
        self._update_color_shift_target_chip()
        self._update_color_shift_output_chip()

    def _get_color_shift_base_color(self) -> Tuple[int, int, int, int]:
        red = self._clamp_byte(self._value_getters.get("base_color_r", lambda: 0)(), 0)
        green = self._clamp_byte(self._value_getters.get("base_color_g", lambda: 0)(), 0)
        blue = self._clamp_byte(self._value_getters.get("base_color_b", lambda: 0)(), 0)
        alpha = self._clamp_byte(self._value_getters.get("base_color_a", lambda: 255)(), 255)
        return red, green, blue, alpha

    def _set_numeric_editor_value(self, key: str, value: int) -> None:
        editor = self._field_editors.get(key)
        if editor is None:
            return

        spin_boxes = editor.findChildren(QSpinBox)
        if spin_boxes:
            spin_boxes[0].setValue(int(value))
            return

        double_spin_boxes = editor.findChildren(QDoubleSpinBox)
        if double_spin_boxes:
            double_spin_boxes[0].setValue(float(value))

    def _set_color_shift_target_color(self, red: int, green: int, blue: int) -> None:
        _r, _g, _b, alpha = self._get_color_shift_base_color()
        self._set_numeric_editor_value("base_color_r", self._clamp_byte(red, 0))
        self._set_numeric_editor_value("base_color_g", self._clamp_byte(green, 0))
        self._set_numeric_editor_value("base_color_b", self._clamp_byte(blue, 0))
        self._set_numeric_editor_value("base_color_a", alpha)
        self._update_color_shift_target_chip()

    def _open_color_shift_target_color_picker(self) -> None:
        red, green, blue, _alpha = self._get_color_shift_base_color()
        chosen = QColorDialog.getColor(QColor(red, green, blue), self, "Select Target Color")
        if not chosen.isValid():
            return
        self._set_color_shift_target_color(chosen.red(), chosen.green(), chosen.blue())

    def _get_color_shift_output_color(self) -> Tuple[int, int, int, int]:
        red = self._clamp_byte(self._value_getters.get("output_color_r", lambda: 0)(), 0)
        green = self._clamp_byte(self._value_getters.get("output_color_g", lambda: 0)(), 0)
        blue = self._clamp_byte(self._value_getters.get("output_color_b", lambda: 0)(), 0)
        alpha = self._clamp_byte(self._value_getters.get("output_color_a", lambda: 255)(), 255)
        return red, green, blue, alpha

    def _set_color_shift_output_color(self, red: int, green: int, blue: int) -> None:
        _r, _g, _b, alpha = self._get_color_shift_output_color()
        self._set_numeric_editor_value("output_color_r", self._clamp_byte(red, 0))
        self._set_numeric_editor_value("output_color_g", self._clamp_byte(green, 0))
        self._set_numeric_editor_value("output_color_b", self._clamp_byte(blue, 0))
        self._set_numeric_editor_value("output_color_a", alpha)
        self._update_color_shift_output_chip()

    def _open_color_shift_output_color_picker(self) -> None:
        red, green, blue, _alpha = self._get_color_shift_output_color()
        chosen = QColorDialog.getColor(QColor(red, green, blue), self, "Select Output Base Color")
        if not chosen.isValid():
            return
        self._set_color_shift_output_color(chosen.red(), chosen.green(), chosen.blue())

    def _update_color_shift_target_chip(self) -> None:
        if self._color_shift_target_chip is None:
            return

        red, green, blue, alpha = self._get_color_shift_base_color()
        text_color = "#000000" if (red + green + blue) > 380 else "#ffffff"
        self._color_shift_target_chip.setText("")
        self._color_shift_target_chip.setToolTip(f"R:{red} G:{green} B:{blue} A:{alpha}")
        self._color_shift_target_chip.setStyleSheet(
            f"background-color: rgba({red}, {green}, {blue}, {alpha});"
            f"color: {text_color}; border: 2px solid #8a8a8a;"
        )

    def _update_color_shift_output_chip(self) -> None:
        if self._color_shift_output_chip is None:
            return

        red, green, blue, alpha = self._get_color_shift_output_color()
        text_color = "#000000" if (red + green + blue) > 380 else "#ffffff"
        self._color_shift_output_chip.setText("●")
        self._color_shift_output_chip.setToolTip(f"R:{red} G:{green} B:{blue} A:{alpha}")
        self._color_shift_output_chip.setStyleSheet(
            f"background-color: rgba({red}, {green}, {blue}, {alpha});"
            f"color: {text_color}; border: 1px solid #6a6a6a;"
        )

    def _connect_widget_change_signal(self, widget: Optional[QWidget], callback: Callable[[], None]) -> None:
        if widget is None:
            return

        def bind_single(target: QWidget) -> None:
            if isinstance(target, QSpinBox):
                target.valueChanged.connect(lambda _value: callback())
            elif isinstance(target, QDoubleSpinBox):
                target.valueChanged.connect(lambda _value: callback())
            elif isinstance(target, QSlider):
                target.valueChanged.connect(lambda _value: callback())
            elif isinstance(target, QLineEdit):
                target.textChanged.connect(lambda _value: callback())
            elif isinstance(target, QComboBox):
                target.currentTextChanged.connect(lambda _value: callback())
            elif isinstance(target, QCheckBox):
                target.stateChanged.connect(lambda _value: callback())
            elif isinstance(target, QPlainTextEdit):
                target.textChanged.connect(callback)

        bind_single(widget)
        for child in widget.findChildren(QWidget):
            bind_single(child)

    def _connect_color_shift_preview_updates(self) -> None:
        if self.node_type != "Color Shift":
            return

        preview_keys = [
            "base_color_r",
            "base_color_g",
            "base_color_b",
            "base_color_a",
            "output_color_r",
            "output_color_g",
            "output_color_b",
            "output_color_a",
            "selection_type",
            "tolerance",
            "distance_type",
            "shift_type",
            "shift_amount",
        ]
        for key in preview_keys:
            self._connect_widget_change_signal(self._field_editors.get(key), self._update_color_shift_preview)

    @staticmethod
    def _clamp_byte(value: object, fallback: int) -> int:
        try:
            return int(max(0, min(255, int(round(float(value))))))
        except (TypeError, ValueError):
            return fallback

    def _set_preview_label_pixmap(self, label: Optional[QLabel], image_obj: object) -> None:
        if label is None:
            return

        try:
            from PIL.ImageQt import ImageQt

            qimage = QImage(ImageQt(image_obj.convert("RGBA")))
            pixmap = QPixmap.fromImage(qimage)
            if not pixmap.isNull():
                scaled = pixmap.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(scaled)
                label.setText("")
                return
        except Exception:
            pass

        label.setPixmap(QPixmap())
        label.setText("Preview unavailable")

    def _update_color_shift_preview(self) -> None:
        if self.node_type != "Color Shift":
            return

        if (
            self._color_shift_preview_before is None
            or self._color_shift_preview_mask is None
            or self._color_shift_preview_after is None
        ):
            return

        try:
            from OV_Libs.ImageEditingLib.color_shift_filter import ColorShiftFilter, ColorShiftFilterOptions
            from OV_Libs.pillow_compat import Image

            props = self._collect_form_properties()

            base_color = (
                self._clamp_byte(props.get("base_color_r", 0), 0),
                self._clamp_byte(props.get("base_color_g", 0), 0),
                self._clamp_byte(props.get("base_color_b", 0), 0),
                self._clamp_byte(props.get("base_color_a", 255), 255),
            )

            selection_type = str(props.get("selection_type", "rgb_distance")).strip().lower() or "rgb_distance"
            if selection_type not in {"rgb_distance", "rgb_range", "hsv_range"}:
                selection_type = "rgb_distance"

            shift_type = str(props.get("shift_type", "absolute_rgb")).strip().lower() or "absolute_rgb"
            if shift_type not in {"absolute_rgb", "absolute_hsv", "percentile_rgb", "percentile_hsv", "match_distance_rgb"}:
                shift_type = "absolute_rgb"

            output_base_color = (
                self._clamp_byte(props.get("output_color_r", 0), 0),
                self._clamp_byte(props.get("output_color_g", 0), 0),
                self._clamp_byte(props.get("output_color_b", 0), 0),
                self._clamp_byte(props.get("output_color_a", 255), 255),
            )

            distance_type = str(props.get("distance_type", "euclidean")).strip().lower() or "euclidean"
            if distance_type not in {"euclidean", "manhattan", "chebyshev"}:
                distance_type = "euclidean"

            tolerance_raw = props.get("tolerance", 30.0)
            tolerance: object
            if isinstance(tolerance_raw, (list, tuple)):
                tolerance_values = []
                for value in list(tolerance_raw)[:3]:
                    try:
                        tolerance_values.append(float(value))
                    except (TypeError, ValueError):
                        tolerance_values.append(30.0)
                while len(tolerance_values) < 3:
                    tolerance_values.append(tolerance_values[-1] if tolerance_values else 30.0)
                tolerance = tuple(tolerance_values[:3])
            else:
                try:
                    tolerance = float(tolerance_raw)
                except (TypeError, ValueError):
                    tolerance = 30.0

            shift_amount_raw = props.get("shift_amount", 50.0)
            if isinstance(shift_amount_raw, (list, tuple)):
                shift_values = []
                for value in list(shift_amount_raw)[:3]:
                    try:
                        shift_values.append(float(value))
                    except (TypeError, ValueError):
                        shift_values.append(50.0)
                while len(shift_values) < 3:
                    shift_values.append(shift_values[-1] if shift_values else 50.0)
                shift_value: object = tuple(shift_values[:3])
            else:
                try:
                    shift_value = float(shift_amount_raw)
                except (TypeError, ValueError):
                    shift_value = 50.0

            width = 240
            height = 90
            sample = Image.new("RGBA", (width, height), (0, 0, 0, 255))
            pixels = sample.load()

            sample_palette = [
                base_color,
                (self._clamp_byte(base_color[0] + 20, 0), self._clamp_byte(base_color[1], 0), self._clamp_byte(base_color[2], 0), 255),
                (self._clamp_byte(base_color[0], 0), self._clamp_byte(base_color[1] + 20, 0), self._clamp_byte(base_color[2], 0), 255),
                (self._clamp_byte(base_color[0], 0), self._clamp_byte(base_color[1], 0), self._clamp_byte(base_color[2] + 20, 0), 255),
                (self._clamp_byte(base_color[0] + 40, 0), self._clamp_byte(base_color[1] + 40, 0), self._clamp_byte(base_color[2] + 40, 0), 255),
                (255, 0, 0, 255),
                (0, 255, 0, 255),
                (0, 0, 255, 255),
                (255, 255, 0, 255),
                (255, 0, 255, 255),
                (0, 255, 255, 255),
                (40, 40, 40, 255),
            ]

            stripe_width = max(1, width // len(sample_palette))
            for index, color in enumerate(sample_palette):
                x_start = index * stripe_width
                x_end = width if index == len(sample_palette) - 1 else min(width, x_start + stripe_width)
                for y in range(height):
                    for x in range(x_start, x_end):
                        pixels[x, y] = color

            filter_options = ColorShiftFilterOptions(
                selection_type=selection_type,
                shift_type=shift_type,
                tolerance=tolerance,
                distance_type=distance_type,
                output_base_color=output_base_color,
            )
            shifted, mask = ColorShiftFilter().apply_color_shift_to_image(
                sample,
                base_color,
                filter_options,
                shift_value,
            )

            self._set_preview_label_pixmap(self._color_shift_preview_before, sample)
            self._set_preview_label_pixmap(self._color_shift_preview_mask, mask)
            self._set_preview_label_pixmap(self._color_shift_preview_after, shifted)
        except Exception:
            self._set_preview_label_pixmap(self._color_shift_preview_before, None)
            self._set_preview_label_pixmap(self._color_shift_preview_mask, None)
            self._set_preview_label_pixmap(self._color_shift_preview_after, None)

    @staticmethod
    def _parse_json_text(raw_text: str) -> object:
        text = raw_text.strip()
        if not text:
            return ""
        return json.loads(text)

    def _collect_form_properties(self) -> Dict[str, object]:
        collected: Dict[str, object] = {}
        for key, getter in self._value_getters.items():
            collected[key] = getter()
        return collected

    def open_advanced_json_editor(self) -> None:
        current = self._collect_form_properties()

        dialog = QDialog(self)
        dialog.setWindowTitle("Advanced JSON Parameter Editor")
        dialog.resize(780, 520)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Edit full node parameters as a JSON object."))

        text = QPlainTextEdit(dialog)
        text.setPlainText(json.dumps(current, ensure_ascii=False, indent=2))
        layout.addWidget(text)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec_() != QDialog.Accepted:
            return

        try:
            parsed = json.loads(text.toPlainText())
        except json.JSONDecodeError as error:
            QMessageBox.warning(self, "Invalid JSON", f"Could not parse JSON:\n{error}")
            return

        if not isinstance(parsed, dict):
            QMessageBox.warning(self, "Invalid JSON", "Advanced JSON must be an object with key/value pairs.")
            return

        self._properties = {str(key): value for key, value in parsed.items()}
        self.accept()

    def _file_filter_for_key(self, key_name: str) -> str:
        normalized_key = key_name.strip().lower()

        if self.node_type == "Image Import":
            return self.IMAGE_FILE_FILTER

        if self.node_type == "Output":
            if normalized_key in {"output_path", "file_path"}:
                return self.IMAGE_FILE_FILTER
            return self.ALL_FILE_FILTER

        if normalized_key.endswith("_path"):
            return self.ALL_FILE_FILTER

        return self.ALL_FILE_FILTER

    def _try_accept(self) -> None:
        if self._properties:
            self.accept()
            return

        try:
            self._properties = self._collect_form_properties()
        except json.JSONDecodeError as error:
            QMessageBox.warning(self, "Invalid JSON", f"Could not parse one of the JSON fields:\n{error}")
            return
        self.accept()

    def properties(self) -> Dict[str, object]:
        return dict(self._properties)


class PortItem(QGraphicsEllipseItem):
    DRAG_THRESHOLD = 8.0

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        node_id: str,
        port_kind: str,
        port_name: str,
        on_port_clicked: Callable[[str, str, str], None],
        on_port_drag_started: Optional[Callable[[str, str, str, QPointF], None]],
        on_port_drag_moved: Optional[Callable[[QPointF], None]],
        on_port_drag_finished: Optional[Callable[[str, str, str, QPointF], None]],
        parent=None,
    ) -> None:
        super().__init__(x, y, width, height, parent)
        self.node_id = node_id
        self.port_kind = port_kind
        self.port_name = port_name
        self.on_port_clicked = on_port_clicked
        self.on_port_drag_started = on_port_drag_started
        self.on_port_drag_moved = on_port_drag_moved
        self.on_port_drag_finished = on_port_drag_finished
        self._press_scene_pos: Optional[QPointF] = None
        self._drag_started = False
        self.setAcceptedMouseButtons(Qt.LeftButton)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._press_scene_pos = event.scenePos()
            self._drag_started = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._press_scene_pos is None or not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return

        if not self._drag_started:
            delta = event.scenePos() - self._press_scene_pos
            if delta.manhattanLength() >= self.DRAG_THRESHOLD:
                self._drag_started = True
                if self.on_port_drag_started is not None:
                    self.on_port_drag_started(
                        self.node_id,
                        self.port_kind,
                        self.port_name,
                        self._press_scene_pos,
                    )

        if self._drag_started and self.on_port_drag_moved is not None:
            self.on_port_drag_moved(event.scenePos())

        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._drag_started:
                if self.on_port_drag_finished is not None:
                    self.on_port_drag_finished(
                        self.node_id,
                        self.port_kind,
                        self.port_name,
                        event.scenePos(),
                    )
            elif self.on_port_clicked is not None:
                self.on_port_clicked(self.node_id, self.port_kind, self.port_name)

            self._press_scene_pos = None
            self._drag_started = False
            event.accept()
            return

        super().mouseReleaseEvent(event)


class NodeItem(QGraphicsRectItem):
    PORT_SIZE = 12.0
    HEADER_HEIGHT = 28.0
    MIN_WIDTH = 280.0
    MIN_HEIGHT = 190.0
    PORT_PADDING = 12.0
    RESIZE_HANDLE_SIZE = 12.0
    PORT_LABEL_COLOR = "#cfcfcf"
    PREVIEW_MAX_SIZE = 170.0

    def __init__(
        self,
        node_id: str,
        node_type: str,
        x: float,
        y: float,
        input_port_names: List[str],
        output_port_names: List[str],
        width: float,
        height: float,
        node_properties: Optional[Dict[str, object]],
        on_position_changed,
        on_interaction_finished: Optional[Callable[[], None]],
        on_port_clicked: Callable[[str, str, str], None],
        on_port_drag_started: Optional[Callable[[str, str, str, QPointF], None]],
        on_port_drag_moved: Optional[Callable[[QPointF], None]],
        on_port_drag_finished: Optional[Callable[[str, str, str, QPointF], None]],
        on_context_menu_requested: Callable[[str, object], None],
    ) -> None:
        super().__init__(0, 0, 180, 70)
        self.node_id = node_id
        self.node_type = node_type
        self.on_position_changed = on_position_changed
        self.input_port_names = list(input_port_names)
        self.output_port_names = list(output_port_names)
        self.input_ports: Dict[str, PortItem] = {}
        self.output_ports: Dict[str, PortItem] = {}
        self.input_port_labels: Dict[str, QGraphicsSimpleTextItem] = {}
        self.output_port_labels: Dict[str, QGraphicsSimpleTextItem] = {}
        self._is_resizing = False
        self._resize_start_scene_pos = None
        self._resize_start_rect = None
        self._press_start_item_pos: Optional[Tuple[float, float]] = None
        self._press_start_size: Optional[Tuple[float, float]] = None
        self.node_properties: Dict[str, object] = dict(node_properties or {})
        self.on_context_menu_requested = on_context_menu_requested
        self.on_interaction_finished = on_interaction_finished
        self.setPos(x, y)

        self._preview_pixmap: Optional[QPixmap] = None

        self.setBrush(QBrush(QColor("#2d2d30")))
        self.setPen(QPen(QColor("#8a8a8a"), 1.5))

        self.setFlags(
            QGraphicsRectItem.ItemIsMovable
            | QGraphicsRectItem.ItemIsSelectable
            | QGraphicsRectItem.ItemSendsGeometryChanges
        )

        self.label = QGraphicsSimpleTextItem(node_type, self)
        self.label.setBrush(QBrush(QColor("#f0f0f0")))

        self.resize_handle = QGraphicsRectItem(self)
        self.resize_handle.setBrush(QBrush(QColor("#5a5a5a")))
        self.resize_handle.setPen(QPen(QColor("#9a9a9a"), 1.0))
        self.resize_handle.setZValue(3)

        self.preview_frame = QGraphicsRectItem(self)
        self.preview_frame.setBrush(QBrush(QColor("#1b1b1b")))
        self.preview_frame.setPen(QPen(QColor("#5a5a5a"), 1.0))
        self.preview_frame.setZValue(2)
        self.preview_frame.setVisible(False)

        self.preview_item = QGraphicsPixmapItem(self)
        self.preview_item.setZValue(2)
        self.preview_item.setVisible(False)

        for port_name in self.input_port_names:
            port_item = PortItem(
                0,
                0,
                self.PORT_SIZE,
                self.PORT_SIZE,
                node_id,
                "input",
                port_name,
                on_port_clicked,
                on_port_drag_started,
                on_port_drag_moved,
                on_port_drag_finished,
                self,
            )
            port_item.setBrush(QBrush(QColor("#9cdcfe")))
            port_item.setPen(QPen(QColor("#d0ebff"), 1.0))
            self.input_ports[port_name] = port_item

            port_label = QGraphicsSimpleTextItem(port_name, self)
            port_label.setBrush(QBrush(QColor(self.PORT_LABEL_COLOR)))
            self.input_port_labels[port_name] = port_label

        for port_name in self.output_port_names:
            port_item = PortItem(
                0,
                0,
                self.PORT_SIZE,
                self.PORT_SIZE,
                node_id,
                "output",
                port_name,
                on_port_clicked,
                on_port_drag_started,
                on_port_drag_moved,
                on_port_drag_finished,
                self,
            )
            port_item.setBrush(QBrush(QColor("#6aeb8f")))
            port_item.setPen(QPen(QColor("#c8ffd8"), 1.0))
            self.output_ports[port_name] = port_item

            port_label = QGraphicsSimpleTextItem(port_name, self)
            port_label.setBrush(QBrush(QColor(self.PORT_LABEL_COLOR)))
            self.output_port_labels[port_name] = port_label

        self.set_size(width, height)

    def _minimum_size(self) -> Tuple[float, float]:
        max_ports = max(len(self.input_port_names), len(self.output_port_names), 1)
        min_height = self.HEADER_HEIGHT + (max_ports * 20.0) + self.PORT_PADDING

        left_label_width = max(
            (label.boundingRect().width() for label in self.input_port_labels.values()),
            default=0.0,
        )
        right_label_width = max(
            (label.boundingRect().width() for label in self.output_port_labels.values()),
            default=0.0,
        )
        min_width = max(
            self.MIN_WIDTH,
            36.0 + left_label_width + right_label_width + 70.0,
        )

        return min_width, max(self.MIN_HEIGHT, min_height)

    def _layout_contents(self) -> None:
        rect = self.rect()
        width = rect.width()
        height = rect.height()

        self.label.setPos(12, 8)

        input_positions = self._port_positions(len(self.input_port_names), height)
        output_positions = self._port_positions(len(self.output_port_names), height)

        for index, port_name in enumerate(self.input_port_names):
            if port_name in self.input_ports:
                center_y = input_positions[index]
                y = center_y - (self.PORT_SIZE / 2.0)
                self.input_ports[port_name].setRect(-self.PORT_SIZE / 2.0, y, self.PORT_SIZE, self.PORT_SIZE)

                label_item = self.input_port_labels.get(port_name)
                if label_item is not None:
                    label_height = label_item.boundingRect().height()
                    label_item.setPos(10.0, center_y - (label_height / 2.0))

        for index, port_name in enumerate(self.output_port_names):
            if port_name in self.output_ports:
                center_y = output_positions[index]
                y = center_y - (self.PORT_SIZE / 2.0)
                self.output_ports[port_name].setRect(
                    width - (self.PORT_SIZE / 2.0),
                    y,
                    self.PORT_SIZE,
                    self.PORT_SIZE,
                )

                label_item = self.output_port_labels.get(port_name)
                if label_item is not None:
                    label_rect = label_item.boundingRect()
                    label_x = width - 10.0 - self.PORT_SIZE - label_rect.width()
                    label_item.setPos(label_x, center_y - (label_rect.height() / 2.0))

        handle_size = self.RESIZE_HANDLE_SIZE
        self.resize_handle.setRect(width - handle_size, height - handle_size, handle_size, handle_size)

        self._layout_preview(width, height)

    def _layout_preview(self, width: float, height: float) -> None:
        if self._preview_pixmap is None:
            self.preview_frame.setVisible(False)
            self.preview_item.setVisible(False)
            return

        content_top = self.HEADER_HEIGHT + 8.0
        content_bottom = max(content_top, height - 8.0)
        available_width = max(0.0, width - 16.0)
        available_height = max(0.0, content_bottom - content_top)
        max_size = min(self.PREVIEW_MAX_SIZE, available_width, available_height)
        if max_size <= 0:
            self.preview_frame.setVisible(False)
            self.preview_item.setVisible(False)
            return

        scaled = self._preview_pixmap.scaled(
            int(max_size),
            int(max_size),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_item.setPixmap(scaled)
        preview_x = (width - scaled.width()) / 2.0
        preview_y = content_top + ((available_height - scaled.height()) / 2.0)
        self.preview_item.setPos(preview_x, preview_y)

        frame_padding = 2.0
        self.preview_frame.setRect(
            preview_x - frame_padding,
            preview_y - frame_padding,
            scaled.width() + (frame_padding * 2),
            scaled.height() + (frame_padding * 2),
        )
        self.preview_frame.setVisible(True)
        self.preview_item.setVisible(True)

    def set_preview_image(self, image: Optional[QImage]) -> None:
        if image is None or image.isNull():
            self._preview_pixmap = None
            self._layout_preview(self.rect().width(), self.rect().height())
            return

        self._preview_pixmap = QPixmap.fromImage(image)
        self._layout_preview(self.rect().width(), self.rect().height())

    def get_preview_pixmap(self) -> Optional[QPixmap]:
        if self._preview_pixmap is None:
            return None
        return QPixmap(self._preview_pixmap)

    def _port_positions(self, count: int, height: float) -> List[float]:
        if count <= 0:
            return []

        top = self.HEADER_HEIGHT + 8.0
        bottom = max(top + 1.0, height - 10.0)

        if count == 1:
            return [(top + bottom) / 2.0]

        step = (bottom - top) / (count - 1)
        return [top + (step * index) for index in range(count)]

    def set_size(self, width: float, height: float) -> None:
        min_width, min_height = self._minimum_size()
        clamped_width = max(float(width), min_width)
        clamped_height = max(float(height), min_height)
        self.setRect(0, 0, clamped_width, clamped_height)
        self._layout_contents()

    def get_port_anchor(self, port_kind: str, port_name: str):
        if port_kind == "input":
            port_item = self.input_ports.get(port_name)
        else:
            port_item = self.output_ports.get(port_name)

        if port_item is None:
            return self.mapToScene(self.rect().center())

        center = port_item.rect().center()
        return port_item.mapToScene(center)

    def _is_on_resize_handle(self, item_pos) -> bool:
        rect = self.rect()
        return (
            item_pos.x() >= rect.width() - self.RESIZE_HANDLE_SIZE
            and item_pos.y() >= rect.height() - self.RESIZE_HANDLE_SIZE
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._press_start_item_pos = (float(self.pos().x()), float(self.pos().y()))
            self._press_start_size = (float(self.rect().width()), float(self.rect().height()))

        if event.button() == Qt.LeftButton and self._is_on_resize_handle(event.pos()):
            self._is_resizing = True
            self._resize_start_scene_pos = event.scenePos()
            self._resize_start_rect = QRectF(self.rect())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._is_resizing and self._resize_start_scene_pos is not None and self._resize_start_rect is not None:
            delta = event.scenePos() - self._resize_start_scene_pos
            new_width = self._resize_start_rect.width() + delta.x()
            new_height = self._resize_start_rect.height() + delta.y()
            self.set_size(new_width, new_height)
            if self.on_position_changed is not None:
                self.on_position_changed()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        start_pos = self._press_start_item_pos
        start_size = self._press_start_size

        self._is_resizing = False
        self._resize_start_scene_pos = None
        self._resize_start_rect = None
        super().mouseReleaseEvent(event)

        self._press_start_item_pos = None
        self._press_start_size = None

        if (
            event.button() == Qt.LeftButton
            and start_pos is not None
            and start_size is not None
            and self.on_interaction_finished is not None
        ):
            current_pos = (float(self.pos().x()), float(self.pos().y()))
            current_size = (float(self.rect().width()), float(self.rect().height()))
            moved = (
                abs(current_pos[0] - start_pos[0]) > 0.01
                or abs(current_pos[1] - start_pos[1]) > 0.01
            )
            resized = (
                abs(current_size[0] - start_size[0]) > 0.01
                or abs(current_size[1] - start_size[1]) > 0.01
            )
            if moved or resized:
                self.on_interaction_finished()

    def contextMenuEvent(self, event) -> None:
        if self.on_context_menu_requested is not None:
            self.on_context_menu_requested(self.node_id, event.screenPos())
        event.accept()

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionHasChanged and self.on_position_changed is not None:
            self.on_position_changed()
        return super().itemChange(change, value)


class ConnectionLineItem(QGraphicsLineItem):
    def __init__(self, connection: Dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.connection = dict(connection)


class NodeCanvasView(QGraphicsView):
    MIN_ZOOM = 0.25
    MAX_ZOOM = 3.5
    ZOOM_STEP = 1.15

    def __init__(self, scene: QGraphicsScene, parent=None) -> None:
        super().__init__(scene, parent)
        self._zoom_level = 1.0
        self._is_panning = False
        self._pan_start = None
        self._on_hover_scene_pos: Optional[Callable[[QPointF], None]] = None
        self._on_hover_leave: Optional[Callable[[], None]] = None

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def set_hover_handlers(
        self,
        on_hover_scene_pos: Optional[Callable[[QPointF], None]],
        on_hover_leave: Optional[Callable[[], None]],
    ) -> None:
        self._on_hover_scene_pos = on_hover_scene_pos
        self._on_hover_leave = on_hover_leave

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            step = self.ZOOM_STEP if event.angleDelta().y() > 0 else (1.0 / self.ZOOM_STEP)
            next_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom_level * step))
            scale_factor = next_zoom / self._zoom_level
            if abs(scale_factor - 1.0) > 1e-6:
                self.scale(scale_factor, scale_factor)
                self._zoom_level = next_zoom
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self.setDragMode(QGraphicsView.NoDrag)
            if self._on_hover_leave is not None:
                self._on_hover_leave()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._is_panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            if self._on_hover_leave is not None:
                self._on_hover_leave()
            event.accept()
            return

        if self._on_hover_scene_pos is not None:
            self._on_hover_scene_pos(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._is_panning = False
            self._pan_start = None
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.RubberBandDrag)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        if self._on_hover_leave is not None:
            self._on_hover_leave()
        super().leaveEvent(event)

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom_level = 1.0

    def fit_scene(self) -> None:
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self._zoom_level = 1.0


class NodeEditorWindow(QMainWindow):
    NODE_CORE_FIELDS = {
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
    HISTORY_LIMIT = 100

    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self.project_path = project_path
        self.setWindowTitle(f"Open Vision Node Canvas - {project_path.stem}")
        self.resize(1300, 800)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 3000, 3000))

        self.view = NodeCanvasView(self.scene)
        self.view.setRenderHints(self.view.renderHints())
        self.view.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        self.view.set_hover_handlers(self.on_canvas_hover_moved, self.on_canvas_hover_left)

        self.node_items: Dict[str, NodeItem] = {}
        self.node_registry = get_default_registry()
        self.node_metadata = self.node_registry.get_all_metadata()
        self.node_add_order = self._build_node_add_order()
        self.connections: List[Dict[str, str]] = []
        self.connection_items: List[QGraphicsLineItem] = []
        self.pending_output: Optional[Tuple[str, str]] = None
        self.pending_connection_drag: Optional[Tuple[str, str, str]] = None
        self.pending_connection_line: Optional[QGraphicsLineItem] = None
        self.copied_node_properties: Optional[Dict[str, object]] = None
        self.output_cache: Dict[str, object] = {}
        self.updated_node_ids: Set[str] = set()
        self.undo_stack: List[Dict[str, object]] = []
        self.redo_stack: List[Dict[str, object]] = []
        self._last_committed_state: Optional[Dict[str, object]] = None
        self._is_restoring_history = False
        self._hover_preview_popup: Optional[QLabel] = None

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._load_nodes_from_project()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        controls = QVBoxLayout()

        self.label_info = QLabel(
            "Click output port (right) then input port (left), or drag port-to-port to connect. "
            "Each input accepts one connection; outputs can connect to many inputs."
        )
        self.label_info.setWordWrap(True)
        self.input_node_filter = QLineEdit()
        self.input_node_filter.setPlaceholderText("Filter node types...")

        self.label_graph_stats = QLabel("Nodes: 0 | Connections: 0")
        self.label_graph_stats.setStyleSheet("color: #d0d0d0;")

        self.node_buttons: Dict[str, QPushButton] = {}
        for node_type in self.node_add_order:
            button = QPushButton(f"Add {node_type} Node")
            controls.addWidget(button)
            self.node_buttons[node_type] = button

        self.btn_connect_selected = QPushButton("Connect Selected (Left -> Right)")
        self.btn_add_test_lines = QPushButton("Add Test Lines")
        self.btn_undo = QPushButton("Undo")
        self.btn_redo = QPushButton("Redo")
        self.btn_run_outputs = QPushButton("Run Outputs")
        self.btn_fit_view = QPushButton("Fit Canvas")
        self.btn_reset_zoom = QPushButton("Reset Zoom")
        self.btn_save_layout = QPushButton("Save Node Layout")

        controls.addWidget(self.label_info)
        controls.addWidget(self.label_graph_stats)
        controls.addWidget(self.input_node_filter)
        controls.addWidget(self.btn_connect_selected)
        controls.addWidget(self.btn_add_test_lines)
        controls.addWidget(self.btn_undo)
        controls.addWidget(self.btn_redo)
        controls.addWidget(self.btn_run_outputs)
        controls.addWidget(self.btn_fit_view)
        controls.addWidget(self.btn_reset_zoom)
        controls.addWidget(self.btn_save_layout)
        controls.addStretch(1)

        root.addLayout(controls, stretch=1)
        root.addWidget(self.view, stretch=4)

    def _connect_signals(self) -> None:
        for node_type, button in self.node_buttons.items():
            button.clicked.connect(lambda _checked=False, t=node_type: self.add_node(t))

        self.btn_connect_selected.clicked.connect(self.connect_selected_nodes)
        self.btn_add_test_lines.clicked.connect(self.add_test_lines)
        self.btn_undo.clicked.connect(self.undo_graph_edit)
        self.btn_redo.clicked.connect(self.redo_graph_edit)
        self.btn_run_outputs.clicked.connect(self.run_outputs)
        self.btn_fit_view.clicked.connect(self.fit_canvas_to_scene)
        self.btn_reset_zoom.clicked.connect(self.reset_canvas_zoom)
        self.btn_save_layout.clicked.connect(self.save_layout)
        self.input_node_filter.textChanged.connect(self.apply_node_filter)

    def _setup_shortcuts(self) -> None:
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_layout)

        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.shortcut_delete.activated.connect(self.delete_selected_items)

        self.shortcut_backspace = QShortcut(QKeySequence(Qt.Key_Backspace), self)
        self.shortcut_backspace.activated.connect(self.delete_selected_items)

        self.shortcut_fit = QShortcut(QKeySequence("F"), self)
        self.shortcut_fit.activated.connect(self.fit_canvas_to_scene)

        self.shortcut_reset_zoom = QShortcut(QKeySequence("Ctrl+0"), self)
        self.shortcut_reset_zoom.activated.connect(self.reset_canvas_zoom)

        self.shortcut_cancel_connection = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_cancel_connection.activated.connect(self.cancel_pending_connection)

        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo_graph_edit)

        self.shortcut_redo = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.shortcut_redo.activated.connect(self.redo_graph_edit)

        self.shortcut_redo_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.shortcut_redo_alt.activated.connect(self.redo_graph_edit)

    def apply_node_filter(self) -> None:
        filter_text = self.input_node_filter.text().strip().lower()
        visible_count = 0

        for node_type, button in self.node_buttons.items():
            visible = (not filter_text) or (filter_text in node_type.lower())
            button.setVisible(visible)
            if visible:
                visible_count += 1

        if filter_text:
            self.statusBar().showMessage(f"Showing {visible_count} matching node types.", 2000)

    def _update_graph_stats(self) -> None:
        pending = " | Pending: yes" if self.pending_output is not None else ""
        self.label_graph_stats.setText(
            f"Nodes: {len(self.node_items)} | Connections: {len(self.connections)}{pending}"
        )

    def _trim_history(self) -> None:
        if len(self.undo_stack) > self.HISTORY_LIMIT:
            self.undo_stack = self.undo_stack[-self.HISTORY_LIMIT :]
        if len(self.redo_stack) > self.HISTORY_LIMIT:
            self.redo_stack = self.redo_stack[-self.HISTORY_LIMIT :]

    def _update_undo_redo_actions(self) -> None:
        self.btn_undo.setEnabled(bool(self.undo_stack))
        self.btn_redo.setEnabled(bool(self.redo_stack))

    def _capture_graph_state(self) -> Dict[str, object]:
        return {
            "nodes": self.collect_nodes(),
            "connections": deepcopy(self.connections),
        }

    def _record_graph_change(self) -> None:
        if self._is_restoring_history:
            return

        current_state = self._capture_graph_state()
        if self._last_committed_state is None:
            self._last_committed_state = deepcopy(current_state)
            self._update_undo_redo_actions()
            return

        if current_state == self._last_committed_state:
            self._update_undo_redo_actions()
            return

        self.undo_stack.append(deepcopy(self._last_committed_state))
        self.redo_stack.clear()
        self._trim_history()
        self._last_committed_state = deepcopy(current_state)
        self._update_undo_redo_actions()

    def _set_graph_state(self, state: Dict[str, object]) -> None:
        self._is_restoring_history = True
        try:
            self._hide_hover_preview_popup()
            for line_item in self.connection_items:
                self.scene.removeItem(line_item)
            self.connection_items = []

            for node_item in list(self.node_items.values()):
                self.scene.removeItem(node_item)
            self.node_items = {}

            self.pending_output = None
            self._clear_pending_connection_drag()
            self.connections = []

            nodes = state.get("nodes", []) if isinstance(state, dict) else []
            connections = state.get("connections", []) if isinstance(state, dict) else []

            if isinstance(nodes, list):
                for node in nodes:
                    if not isinstance(node, dict):
                        continue

                    node_type = str(node.get("type", "Node"))
                    input_ports, output_ports = self._node_port_names(node_type, node)
                    node_properties = self._extract_node_properties(node)
                    self._create_node_item(
                        node_id=str(node.get("id", uuid.uuid4())),
                        node_type=node_type,
                        x=float(node.get("x", 120.0)),
                        y=float(node.get("y", 120.0)),
                        input_port_names=input_ports,
                        output_port_names=output_ports,
                        width=float(node.get("width", 180.0)),
                        height=float(node.get("height", 70.0)),
                        node_properties=node_properties,
                    )

            if isinstance(connections, list):
                for connection in connections:
                    if not isinstance(connection, dict):
                        continue

                    from_node = str(connection.get("from_node", ""))
                    from_port = str(connection.get("from_port", "output"))
                    to_node = str(connection.get("to_node", ""))
                    to_port = str(connection.get("to_port", "input"))
                    if (
                        from_node in self.node_items
                        and to_node in self.node_items
                        and from_node != to_node
                        and self._is_valid_port(from_node, "output", from_port)
                        and self._is_valid_port(to_node, "input", to_port)
                    ):
                        self.connections.append(
                            {
                                "from_node": from_node,
                                "from_port": from_port,
                                "to_node": to_node,
                                "to_port": to_port,
                            }
                        )

            self._rebuild_connection_items()
            self._update_graph_stats()
            self.updated_node_ids = set()
            self._update_node_previews()
        finally:
            self._is_restoring_history = False

    def _initialize_history(self) -> None:
        self.undo_stack = []
        self.redo_stack = []
        self._last_committed_state = deepcopy(self._capture_graph_state())
        self._update_undo_redo_actions()

    def _build_node_add_order(self) -> List[str]:
        ordered: List[str] = []
        categories = ["input", "processing", "output"]

        for category in categories:
            typed_nodes = sorted(self.node_registry.get_nodes_by_category(category).keys())
            for node_type in typed_nodes:
                if node_type not in ordered:
                    ordered.append(node_type)

        for node_type in sorted(self.node_metadata.keys()):
            if node_type not in ordered:
                ordered.append(node_type)

        return ordered

    @staticmethod
    def _make_port_names(prefix: str, count: int) -> List[str]:
        if count <= 0:
            return []
        if count == 1:
            return [prefix]
        return [f"{prefix}_{index}" for index in range(count)]

    def _node_port_names(self, node_type: str, node_data: Optional[Dict[str, object]] = None) -> Tuple[List[str], List[str]]:
        metadata = self.node_metadata.get(node_type, {})

        input_count = int(metadata.get("input_count", 1))
        output_count = int(metadata.get("output_count", 1))

        if node_data is not None:
            input_count = int(node_data.get("input_count", input_count))
            output_count = int(node_data.get("output_count", output_count))

        input_count = max(0, input_count)
        output_count = max(0, output_count)

        input_ports_raw = node_data.get("input_ports") if node_data is not None else None
        output_ports_raw = node_data.get("output_ports") if node_data is not None else None

        if isinstance(input_ports_raw, list):
            input_ports = [str(value) for value in input_ports_raw if str(value).strip()]
        else:
            input_ports = []

        if isinstance(output_ports_raw, list):
            output_ports = [str(value) for value in output_ports_raw if str(value).strip()]
        else:
            output_ports = []

        metadata_input_ports_raw = metadata.get("input_ports")
        metadata_output_ports_raw = metadata.get("output_ports")
        metadata_input_ports = (
            [str(value) for value in metadata_input_ports_raw if str(value).strip()]
            if isinstance(metadata_input_ports_raw, list)
            else []
        )
        metadata_output_ports = (
            [str(value) for value in metadata_output_ports_raw if str(value).strip()]
            if isinstance(metadata_output_ports_raw, list)
            else []
        )

        if len(input_ports) != input_count:
            if len(metadata_input_ports) == input_count:
                input_ports = metadata_input_ports
            else:
                input_ports = self._make_port_names("input", input_count)

        if len(output_ports) != output_count:
            if len(metadata_output_ports) == output_count:
                output_ports = metadata_output_ports
            else:
                output_ports = self._make_port_names("output", output_count)

        return input_ports, output_ports

    def _extract_node_properties(self, node_data: Dict[str, object]) -> Dict[str, object]:
        return {
            key: deepcopy(value)
            for key, value in node_data.items()
            if key not in self.NODE_CORE_FIELDS
        }

    def _default_node_properties(self, node_type: str) -> Dict[str, object]:
        templates: Dict[str, Dict[str, object]] = {
            "Image Import": {
                "file_path": "",
                "format_type": "image",
                "cache_image": True,
                "frame_index": 0,
            },
            "Color Shift": {
                "base_color_r": 0,
                "base_color_g": 0,
                "base_color_b": 0,
                "base_color_a": 255,
                "output_color_r": 0,
                "output_color_g": 0,
                "output_color_b": 0,
                "output_color_a": 255,
                "selection_type": "rgb_distance",
                "shift_type": "absolute_rgb",
                "tolerance": 30.0,
                "distance_type": "euclidean",
                "shift_amount": 50.0,
                "output_mask": True,
            },
            "Blur": {
                "blur_type": "gaussian",
                "gaussian_radius": 5.0,
            },
            "Mask Blur": {
                "blur_type": "gaussian",
                "max_radius": 25.0,
            },
            "Image Layer": {
                "layers": [],
                "blend_mode": "alpha",
                "output_mode": "RGBA",
            },
            "Output": {
                "output_path": "output.png",
                "save_format": "PNG",
                "quality": 95,
                "version": 1,
                "auto_increment_counter": False,
                "create_directories": True,
                "overwrite": False,
            },
        }
        return deepcopy(templates.get(node_type, {}))

    def _load_nodes_from_project(self) -> None:
        graph = load_project_graph(self.project_path)
        self._set_graph_state(
            {
                "nodes": graph.get("nodes", []),
                "connections": graph.get("connections", []),
            }
        )
        self._initialize_history()

    def _create_node_item(
        self,
        node_id: str,
        node_type: str,
        x: float,
        y: float,
        input_port_names: List[str],
        output_port_names: List[str],
        width: float,
        height: float,
        node_properties: Optional[Dict[str, object]] = None,
    ) -> None:
        item = NodeItem(
            node_id=node_id,
            node_type=node_type,
            x=x,
            y=y,
            input_port_names=input_port_names,
            output_port_names=output_port_names,
            width=width,
            height=height,
            node_properties=node_properties,
            on_position_changed=self.update_connection_positions,
            on_interaction_finished=self.on_node_interaction_finished,
            on_port_clicked=self.on_port_clicked,
            on_port_drag_started=self.on_port_drag_started,
            on_port_drag_moved=self.on_port_drag_moved,
            on_port_drag_finished=self.on_port_drag_finished,
            on_context_menu_requested=self.show_node_context_menu,
        )
        self.scene.addItem(item)
        self.node_items[node_id] = item
        self._update_graph_stats()

    def _mark_nodes_updated(self, node_ids: List[str]) -> None:
        for node_id in node_ids:
            if node_id:
                self.updated_node_ids.add(node_id)

    def add_node(self, node_type: str) -> None:
        node_id = str(uuid.uuid4())
        input_ports, output_ports = self._node_port_names(node_type)
        node_properties = self._default_node_properties(node_type)

        max_ports = max(len(input_ports), len(output_ports), 1)
        default_width = 320.0
        default_height = max(190.0, 36.0 + (max_ports * 24.0) + 20.0)

        center_scene_pos = self.view.mapToScene(self.view.viewport().rect().center())
        x = float(center_scene_pos.x() - (default_width / 2.0))
        y = float(center_scene_pos.y() - (default_height / 2.0))
        self._create_node_item(
            node_id=node_id,
            node_type=node_type,
            x=x,
            y=y,
            input_port_names=input_ports,
            output_port_names=output_ports,
            width=default_width,
            height=default_height,
            node_properties=node_properties,
        )
        self._mark_nodes_updated([node_id])
        self._record_graph_change()
        self.statusBar().showMessage(f"Added {node_type} node.", 2000)

    def on_node_interaction_finished(self) -> None:
        node_ids = [item.node_id for item in self.scene.selectedItems() if isinstance(item, NodeItem)]
        if node_ids:
            self._mark_nodes_updated(node_ids)
        self._record_graph_change()

    def show_node_context_menu(self, node_id: str, screen_pos) -> None:
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return

        menu = QMenu(self)
        menu.addAction("Edit Parameters...", lambda: self.edit_node_parameters(node_id))
        menu.addAction("Set/Update Parameter...", lambda: self.set_node_parameter(node_id))
        menu.addAction("Remove Parameter...", lambda: self.remove_node_parameter(node_id))
        menu.addAction("Reset to Node Defaults", lambda: self.reset_node_to_defaults(node_id))
        menu.addSeparator()
        menu.addAction("Copy Properties", lambda: self.copy_node_properties(node_id))

        paste_action = menu.addAction("Paste Properties")
        can_paste = bool(self.copied_node_properties)
        paste_action.setEnabled(can_paste)
        if can_paste:
            paste_action.triggered.connect(lambda: self.paste_node_properties(node_id))

        menu.exec_(screen_pos)

    def _editable_node_properties(self, node_id: str) -> Dict[str, object]:
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return {}
        return dict(node_item.node_properties)

    def _set_node_properties(self, node_id: str, properties: Dict[str, object]) -> None:
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return
        node_item.node_properties = dict(properties)
        self._update_node_previews()

    def edit_node_parameters(self, node_id: str) -> None:
        current_props = self._editable_node_properties(node_id)
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return

        dialog = NodeParameterEditorDialog(node_item.node_type, current_props, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        self._set_node_properties(node_id, dialog.properties())
        self._mark_nodes_updated([node_id])
        self._record_graph_change()
        self.statusBar().showMessage("Node properties updated.", 2500)

    def set_node_parameter(self, node_id: str) -> None:
        key, ok = QInputDialog.getText(self, "Set Parameter", "Parameter key:")
        if not ok:
            return

        key = key.strip()
        if not key:
            QMessageBox.warning(self, "Invalid Key", "Parameter key cannot be empty.")
            return

        value_text, ok = QInputDialog.getMultiLineText(
            self,
            "Set Parameter",
            f"JSON value for '{key}' (examples: 5, true, \"text\", [1,2]):",
            "",
        )
        if not ok:
            return

        value_text = value_text.strip()
        if not value_text:
            QMessageBox.warning(self, "Invalid Value", "Parameter value cannot be empty.")
            return

        try:
            value = json.loads(value_text)
        except json.JSONDecodeError as error:
            QMessageBox.warning(self, "Invalid Value", f"Could not parse JSON value:\n{error}")
            return

        props = self._editable_node_properties(node_id)
        props[key] = value
        self._set_node_properties(node_id, props)
        self._mark_nodes_updated([node_id])
        self._record_graph_change()
        self.statusBar().showMessage(f"Set parameter '{key}'.", 2500)

    def remove_node_parameter(self, node_id: str) -> None:
        props = self._editable_node_properties(node_id)
        if not props:
            self.statusBar().showMessage("Node has no editable properties.", 2500)
            return

        keys = sorted(props.keys())
        key, ok = QInputDialog.getItem(
            self,
            "Remove Parameter",
            "Select parameter to remove:",
            keys,
            0,
            False,
        )
        if not ok:
            return

        if key in props:
            del props[key]
            self._set_node_properties(node_id, props)
            self._mark_nodes_updated([node_id])
            self._record_graph_change()
            self.statusBar().showMessage(f"Removed parameter '{key}'.", 2500)

    def copy_node_properties(self, node_id: str) -> None:
        props = self._editable_node_properties(node_id)
        self.copied_node_properties = deepcopy(props)
        self.statusBar().showMessage("Node properties copied.", 2500)

    def paste_node_properties(self, node_id: str) -> None:
        if not self.copied_node_properties:
            self.statusBar().showMessage("No copied properties available.", 2500)
            return

        self._set_node_properties(node_id, deepcopy(self.copied_node_properties))
        self._mark_nodes_updated([node_id])
        self._record_graph_change()
        self.statusBar().showMessage("Node properties pasted.", 2500)

    def reset_node_to_defaults(self, node_id: str) -> None:
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return

        default_properties = self._default_node_properties(node_item.node_type)
        self._set_node_properties(node_id, default_properties)
        self._mark_nodes_updated([node_id])
        self._record_graph_change()
        self.statusBar().showMessage("Node properties reset to defaults.", 2500)

    def _is_valid_port(self, node_id: str, port_kind: str, port_name: str) -> bool:
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return False

        if port_kind == "input":
            return port_name in node_item.input_ports
        return port_name in node_item.output_ports

    def _first_port_name(self, node_id: str, port_kind: str) -> Optional[str]:
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return None

        if port_kind == "input" and node_item.input_port_names:
            return node_item.input_port_names[0]
        if port_kind == "output" and node_item.output_port_names:
            return node_item.output_port_names[0]
        return None

    def _rebuild_connection_items(self) -> None:
        self._hide_hover_preview_popup()
        for line_item in self.connection_items:
            self.scene.removeItem(line_item)
        self.connection_items = []

        for connection in self.connections:
            start_item = self.node_items.get(connection["from_node"])
            end_item = self.node_items.get(connection["to_node"])
            if start_item is None or end_item is None:
                continue

            from_port = str(connection.get("from_port", "output"))
            to_port = str(connection.get("to_port", "input"))
            line = QLineF(
                start_item.get_port_anchor("output", from_port),
                end_item.get_port_anchor("input", to_port),
            )
            line_item = ConnectionLineItem(connection)
            line_item.setLine(line)
            line_item.setPen(QPen(QColor("#53a7ff"), 2.0))
            line_item.setFlag(QGraphicsLineItem.ItemIsSelectable, True)
            line_item.setZValue(-1)
            self.scene.addItem(line_item)
            self.connection_items.append(line_item)
        self._update_graph_stats()

    @staticmethod
    def _resolve_connection_from_ports(
        first_node_id: str,
        first_port_kind: str,
        first_port_name: str,
        second_node_id: str,
        second_port_kind: str,
        second_port_name: str,
    ) -> Optional[Tuple[str, str, str, str]]:
        if first_port_kind == second_port_kind:
            return None

        if first_port_kind == "output":
            return first_node_id, first_port_name, second_node_id, second_port_name

        return second_node_id, second_port_name, first_node_id, first_port_name

    def _find_port_item_at(
        self,
        scene_pos: QPointF,
        exclude: Optional[Tuple[str, str, str]] = None,
    ) -> Optional[PortItem]:
        for item in self.scene.items(scene_pos):
            if not isinstance(item, PortItem):
                continue

            if exclude is not None:
                node_id, port_kind, port_name = exclude
                if (
                    item.node_id == node_id
                    and item.port_kind == port_kind
                    and item.port_name == port_name
                ):
                    continue
            return item
        return None

    def _clear_pending_connection_drag(self) -> None:
        self.pending_connection_drag = None
        if self.pending_connection_line is not None:
            self.scene.removeItem(self.pending_connection_line)
            self.pending_connection_line = None

    def on_port_drag_started(self, node_id: str, port_kind: str, port_name: str, scene_pos: QPointF) -> None:
        self.pending_output = None
        self.pending_connection_drag = (node_id, port_kind, port_name)

        if self.pending_connection_line is None:
            self.pending_connection_line = QGraphicsLineItem()
            self.pending_connection_line.setPen(QPen(QColor("#53a7ff"), 2.0, Qt.DashLine))
            self.pending_connection_line.setZValue(1)
            self.scene.addItem(self.pending_connection_line)

        self.on_port_drag_moved(scene_pos)
        self._update_graph_stats()

    def on_port_drag_moved(self, scene_pos: QPointF) -> None:
        if self.pending_connection_drag is None or self.pending_connection_line is None:
            return

        node_id, port_kind, port_name = self.pending_connection_drag
        node_item = self.node_items.get(node_id)
        if node_item is None:
            return

        line = QLineF(node_item.get_port_anchor(port_kind, port_name), scene_pos)
        self.pending_connection_line.setLine(line)

    def on_port_drag_finished(self, node_id: str, port_kind: str, port_name: str, scene_pos: QPointF) -> None:
        start_drag = self.pending_connection_drag
        self._clear_pending_connection_drag()
        self._update_graph_stats()

        if start_drag is None:
            return

        source_node_id, source_port_kind, source_port_name = start_drag
        target_port = self._find_port_item_at(
            scene_pos,
            exclude=(node_id, port_kind, port_name),
        )
        if target_port is None:
            self.statusBar().showMessage("Drag canceled: drop on another port to connect.", 2000)
            return

        resolved = self._resolve_connection_from_ports(
            source_node_id,
            source_port_kind,
            source_port_name,
            target_port.node_id,
            target_port.port_kind,
            target_port.port_name,
        )
        if resolved is None:
            self.statusBar().showMessage("Connection blocked: drag between output and input ports.", 3000)
            return

        from_node_id, from_port, to_node_id, to_port = resolved
        if not self._add_connection(from_node_id, to_node_id, from_port, to_port):
            self.statusBar().showMessage("Connection blocked: input already connected or invalid.", 4000)
            return

        self._rebuild_connection_items()
        self._mark_nodes_updated([from_node_id, to_node_id])
        self._record_graph_change()
        self.statusBar().showMessage("Connection created.", 2500)

    def update_connection_positions(self) -> None:
        self._rebuild_connection_items()

    def _input_is_available(self, to_node_id: str, to_port: str) -> bool:
        for connection in self.connections:
            if connection["to_node"] == to_node_id and connection["to_port"] == to_port:
                return False
        return True

    def _add_connection(self, from_node_id: str, to_node_id: str, from_port: str, to_port: str) -> bool:
        if from_node_id == to_node_id:
            return False

        if not self._is_valid_port(from_node_id, "output", from_port):
            return False
        if not self._is_valid_port(to_node_id, "input", to_port):
            return False

        exists = any(
            connection
            for connection in self.connections
            if connection["from_node"] == from_node_id
            and connection["from_port"] == from_port
            and connection["to_node"] == to_node_id
            and connection["to_port"] == to_port
        )
        if exists:
            return False

        if not self._input_is_available(to_node_id, to_port):
            return False

        self.connections.append(
            {
                "from_node": from_node_id,
                "from_port": from_port,
                "to_node": to_node_id,
                "to_port": to_port,
            }
        )
        return True

    def on_port_clicked(self, node_id: str, port_kind: str, port_name: str) -> None:
        if port_kind == "output":
            self.pending_output = (node_id, port_name)
            node_type = self.node_items[node_id].node_type if node_id in self.node_items else "Node"
            self.statusBar().showMessage(
                f"Selected output: {node_type}.{port_name}. Click an input port to connect.",
                4000,
            )
            self._update_graph_stats()
            return

        if port_kind == "input":
            if self.pending_output is None:
                self.statusBar().showMessage("Select an output port first.", 3000)
                return

            from_node_id, from_port = self.pending_output
            to_node_id = node_id
            to_port = port_name

            if not self._add_connection(from_node_id, to_node_id, from_port, to_port):
                self.statusBar().showMessage("Connection blocked: input already connected or invalid.", 4000)
                self.pending_output = None
                self._update_graph_stats()
                return

            self.pending_output = None
            self._rebuild_connection_items()
            self._mark_nodes_updated([from_node_id, to_node_id])
            self._record_graph_change()
            self.statusBar().showMessage("Connection created.", 2500)

    def connect_selected_nodes(self) -> None:
        selected_nodes = [item for item in self.scene.selectedItems() if isinstance(item, NodeItem)]
        if len(selected_nodes) != 2:
            QMessageBox.warning(self, "Select Two Nodes", "Select exactly two nodes to connect.")
            return

        ordered = sorted(selected_nodes, key=lambda node: node.pos().x())
        from_id = ordered[0].node_id
        to_id = ordered[1].node_id
        from_port = self._first_port_name(from_id, "output")
        if from_port is None:
            QMessageBox.warning(self, "Connection Blocked", "Left node has no output ports.")
            return

        to_port = None
        target_node = self.node_items.get(to_id)
        if target_node is not None:
            for candidate_port in target_node.input_port_names:
                if self._input_is_available(to_id, candidate_port):
                    to_port = candidate_port
                    break

        if to_port is None:
            QMessageBox.warning(self, "Connection Blocked", "Right node has no available input ports.")
            return

        if not self._add_connection(from_id, to_id, from_port, to_port):
            QMessageBox.warning(
                self,
                "Connection Blocked",
                "Target input already has a connection, or connection is invalid.",
            )
            return

        self._rebuild_connection_items()
        self._mark_nodes_updated([from_id, to_id])
        self._record_graph_change()
        self.statusBar().showMessage("Connected selected nodes.", 2000)

    def add_test_lines(self) -> None:
        if len(self.node_items) < 2:
            return

        ordered_nodes = sorted(self.node_items.values(), key=lambda item: item.pos().x())
        for index in range(len(ordered_nodes) - 1):
            from_id = ordered_nodes[index].node_id
            to_id = ordered_nodes[index + 1].node_id

            from_port = self._first_port_name(from_id, "output")
            target_node = self.node_items.get(to_id)
            to_port = None
            if target_node is not None:
                for candidate_port in target_node.input_port_names:
                    if self._input_is_available(to_id, candidate_port):
                        to_port = candidate_port
                        break

            if from_port is not None and to_port is not None:
                self._add_connection(from_id, to_id, from_port, to_port)

        self._rebuild_connection_items()
        self._mark_nodes_updated([item.node_id for item in self.node_items.values()])
        self._record_graph_change()
        self.statusBar().showMessage("Added test chain connections.", 2000)

    @staticmethod
    def _connection_key(connection: Dict[str, str]) -> Tuple[str, str, str, str]:
        return (
            connection.get("from_node", ""),
            connection.get("from_port", ""),
            connection.get("to_node", ""),
            connection.get("to_port", ""),
        )

    @staticmethod
    def _distance_to_line_segment(point: QPointF, line: QLineF) -> float:
        x1 = float(line.p1().x())
        y1 = float(line.p1().y())
        x2 = float(line.p2().x())
        y2 = float(line.p2().y())
        px = float(point.x())
        py = float(point.y())

        dx = x2 - x1
        dy = y2 - y1
        length_sq = (dx * dx) + (dy * dy)
        if length_sq <= 1e-9:
            return math.hypot(px - x1, py - y1)

        projection = ((px - x1) * dx + (py - y1) * dy) / length_sq
        t = max(0.0, min(1.0, projection))
        closest_x = x1 + (t * dx)
        closest_y = y1 + (t * dy)
        return math.hypot(px - closest_x, py - closest_y)

    def _preview_node_id_near_scene_pos(self, scene_pos: QPointF) -> Optional[str]:
        for item in self.scene.items(scene_pos):
            if isinstance(item, PortItem):
                return item.node_id
            if isinstance(item, ConnectionLineItem):
                return str(item.connection.get("from_node", "")) or None

        zoom = max(0.1, float(self.view.transform().m11()))
        line_threshold = 12.0 / zoom
        nearest_node_id: Optional[str] = None
        nearest_distance = float("inf")

        for line_item in self.connection_items:
            if not isinstance(line_item, ConnectionLineItem):
                continue
            distance = self._distance_to_line_segment(scene_pos, line_item.line())
            if distance <= line_threshold and distance < nearest_distance:
                nearest_distance = distance
                nearest_node_id = str(line_item.connection.get("from_node", ""))

        if nearest_node_id:
            return nearest_node_id

        port_threshold = 14.0 / zoom
        port_threshold_sq = port_threshold * port_threshold
        nearest_port_node: Optional[str] = None
        nearest_port_dist_sq = float("inf")
        for node_item in self.node_items.values():
            for port_name in node_item.input_port_names:
                anchor = node_item.get_port_anchor("input", port_name)
                dx = float(anchor.x() - scene_pos.x())
                dy = float(anchor.y() - scene_pos.y())
                dist_sq = (dx * dx) + (dy * dy)
                if dist_sq <= port_threshold_sq and dist_sq < nearest_port_dist_sq:
                    nearest_port_dist_sq = dist_sq
                    nearest_port_node = node_item.node_id

            for port_name in node_item.output_port_names:
                anchor = node_item.get_port_anchor("output", port_name)
                dx = float(anchor.x() - scene_pos.x())
                dy = float(anchor.y() - scene_pos.y())
                dist_sq = (dx * dx) + (dy * dy)
                if dist_sq <= port_threshold_sq and dist_sq < nearest_port_dist_sq:
                    nearest_port_dist_sq = dist_sq
                    nearest_port_node = node_item.node_id

        return nearest_port_node

    def _ensure_hover_preview_popup(self) -> QLabel:
        if self._hover_preview_popup is None:
            popup = QLabel(None)
            popup.setWindowFlags(Qt.ToolTip)
            popup.setStyleSheet("border: 1px solid #5a5a5a; background: #1b1b1b; padding: 2px;")
            popup.setAlignment(Qt.AlignCenter)
            popup.setMinimumSize(64, 40)
            self._hover_preview_popup = popup
        return self._hover_preview_popup

    def _hide_hover_preview_popup(self) -> None:
        if self._hover_preview_popup is not None:
            self._hover_preview_popup.hide()

    def on_canvas_hover_left(self) -> None:
        self._hide_hover_preview_popup()

    def on_canvas_hover_moved(self, scene_pos: QPointF) -> None:
        if self.pending_connection_drag is not None:
            self._hide_hover_preview_popup()
            return

        node_id = self._preview_node_id_near_scene_pos(scene_pos)
        if not node_id:
            self._hide_hover_preview_popup()
            return

        node_item = self.node_items.get(node_id)
        if node_item is None:
            self._hide_hover_preview_popup()
            return

        pixmap = node_item.get_preview_pixmap()
        if pixmap is None or pixmap.isNull():
            self._hide_hover_preview_popup()
            return

        popup = self._ensure_hover_preview_popup()
        scaled = pixmap.scaled(220, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        popup.setPixmap(scaled)
        popup.resize(scaled.width() + 6, scaled.height() + 6)

        view_pos = self.view.mapFromScene(scene_pos)
        global_pos = self.view.viewport().mapToGlobal(view_pos + QPoint(18, 18))
        popup.move(global_pos)
        popup.show()

    def _delete_nodes(self, node_ids: List[str]) -> None:
        for node_id in node_ids:
            node_item = self.node_items.pop(node_id, None)
            if node_item is not None:
                self.scene.removeItem(node_item)
            if node_id in self.output_cache:
                del self.output_cache[node_id]
            if node_id in self.updated_node_ids:
                self.updated_node_ids.discard(node_id)

        self.connections = [
            connection
            for connection in self.connections
            if connection["from_node"] not in node_ids and connection["to_node"] not in node_ids
        ]

        if self.pending_output is not None and self.pending_output[0] in node_ids:
            self.pending_output = None

        if self.pending_connection_drag is not None and self.pending_connection_drag[0] in node_ids:
            self._clear_pending_connection_drag()

    def _delete_connections(self, connection_keys: List[Tuple[str, str, str, str]]) -> None:
        key_set = set(connection_keys)
        affected_nodes = []
        for from_node, _from_port, to_node, _to_port in key_set:
            affected_nodes.append(from_node)
            affected_nodes.append(to_node)
        self.connections = [
            connection
            for connection in self.connections
            if self._connection_key(connection) not in key_set
        ]
        self._mark_nodes_updated([node_id for node_id in affected_nodes if node_id])

    def delete_selected_items(self) -> None:
        selected_items = self.scene.selectedItems()
        if not selected_items:
            self.statusBar().showMessage("Nothing selected to delete.", 1500)
            return

        node_ids = [item.node_id for item in selected_items if isinstance(item, NodeItem)]
        selected_connection_keys = [
            self._connection_key(item.connection)
            for item in selected_items
            if isinstance(item, ConnectionLineItem)
        ]

        if node_ids:
            self._delete_nodes(node_ids)

        if selected_connection_keys:
            self._delete_connections(selected_connection_keys)

        self._rebuild_connection_items()
        self._record_graph_change()
        self.statusBar().showMessage(
            f"Deleted {len(node_ids)} node(s) and {len(selected_connection_keys)} connection(s).",
            2500,
        )

    def undo_graph_edit(self) -> None:
        if not self.undo_stack:
            self.statusBar().showMessage("Nothing to undo.", 1500)
            self._update_undo_redo_actions()
            return

        current_state = self._capture_graph_state()
        previous_state = self.undo_stack.pop()
        self.redo_stack.append(deepcopy(current_state))
        self._trim_history()

        self._set_graph_state(previous_state)
        self._last_committed_state = deepcopy(self._capture_graph_state())
        self._update_undo_redo_actions()
        self.statusBar().showMessage("Undo complete.", 1500)

    def redo_graph_edit(self) -> None:
        if not self.redo_stack:
            self.statusBar().showMessage("Nothing to redo.", 1500)
            self._update_undo_redo_actions()
            return

        current_state = self._capture_graph_state()
        next_state = self.redo_stack.pop()
        self.undo_stack.append(deepcopy(current_state))
        self._trim_history()

        self._set_graph_state(next_state)
        self._last_committed_state = deepcopy(self._capture_graph_state())
        self._update_undo_redo_actions()
        self.statusBar().showMessage("Redo complete.", 1500)

    def cancel_pending_connection(self) -> None:
        if self.pending_output is None and self.pending_connection_drag is None:
            return
        self.pending_output = None
        self._clear_pending_connection_drag()
        self._update_graph_stats()
        self.statusBar().showMessage("Canceled pending connection.", 2000)

    def fit_canvas_to_scene(self) -> None:
        self.view.fit_scene()
        self.statusBar().showMessage("Fit canvas to scene.", 1500)

    def reset_canvas_zoom(self) -> None:
        self.view.reset_zoom()
        self.statusBar().showMessage("Canvas zoom reset.", 1500)

    def run_outputs(self) -> None:
        nodes = self.collect_nodes()
        if not nodes:
            QMessageBox.information(self, "Run Outputs", "No nodes available to run.")
            return

        updated_ids = sorted(self.updated_node_ids)
        if updated_ids:
            pipeline, is_valid, errors = build_update_pipeline(nodes, self.connections, updated_ids)
        else:
            pipeline, is_valid, errors = build_pipeline_from_graph(nodes, self.connections)
        if errors:
            summary = "\n".join(errors)
            if not is_valid:
                QMessageBox.warning(self, "Pipeline Invalid", summary)
                return
            QMessageBox.information(self, "Pipeline Warnings", summary)

        node_executors: Dict[str, Callable[[Dict[str, object], List[object]], object]] = {}
        for node in nodes:
            node_type = str(node.get("type", "")).strip()
            if not node_type or node_type in node_executors:
                continue
            try:
                node_executors[node_type] = self.node_registry.get_executor(node_type)
            except KeyError as error:
                QMessageBox.warning(self, "Missing Executor", str(error))
                return

        results: Optional[Dict[str, object]] = None
        try:
            results = execute_pipeline(
                pipeline,
                node_executors,
                use_threading=True,
                initial_results=self.output_cache,
            )
        except Exception as error:
            if updated_ids:
                full_pipeline, full_valid, full_errors = build_pipeline_from_graph(nodes, self.connections)
                if full_errors and not full_valid:
                    QMessageBox.warning(self, "Execution Failed", "\n".join(full_errors))
                    return

                try:
                    results = execute_pipeline(
                        full_pipeline,
                        node_executors,
                        use_threading=True,
                        initial_results=None,
                    )
                    pipeline = full_pipeline
                    self.statusBar().showMessage("Incremental run failed; full run succeeded.", 3000)
                except Exception as full_error:
                    message = self._format_execution_error(str(full_error), nodes)
                    QMessageBox.warning(self, "Execution Failed", message)
                    return
            else:
                message = self._format_execution_error(str(error), nodes)
                QMessageBox.warning(self, "Execution Failed", message)
                return

        if results is None:
            QMessageBox.warning(self, "Execution Failed", "No results returned from execution.")
            return

        self.output_cache.update(results)
        self._update_node_previews()

        executed_ids = pipeline.get("execution_order", [])
        if updated_ids:
            self.updated_node_ids.difference_update(executed_ids)
        else:
            self.updated_node_ids = set()

        output_items: List[str] = []
        for node in nodes:
            if str(node.get("type", "")) != "Output":
                continue
            node_id = str(node.get("id", ""))
            if node_id and node_id in results:
                output_items.append(f"{node_id}: {results[node_id]}")

        if not output_items:
            summary = get_pipeline_summary(pipeline)
            QMessageBox.information(self, "Run Complete", f"Pipeline executed.\n\n{summary}")
            return

        QMessageBox.information(self, "Run Outputs", "\n".join(output_items))

    @staticmethod
    def _format_execution_error(message: str, nodes: List[Dict[str, object]]) -> str:
        match = re.search(r"Error executing node ([^:]+):", message)
        if not match:
            return message

        node_id = match.group(1).strip()
        node_type = "Unknown"
        for node in nodes:
            if str(node.get("id", "")) == node_id:
                node_type = str(node.get("type", "Unknown"))
                break

        return f"{message}\n\nNode: {node_type} ({node_id})"

    def _extract_preview_image(self, result: object) -> Optional[object]:
        if result is None:
            return None

        def is_image_candidate(value: object) -> bool:
            return (
                hasattr(value, "size")
                and hasattr(value, "mode")
                and hasattr(value, "getbands")
            )

        pending: List[object] = [result]
        visited_ids: Set[int] = set()

        while pending:
            candidate = pending.pop(0)
            candidate_id = id(candidate)
            if candidate_id in visited_ids:
                continue
            visited_ids.add(candidate_id)

            if is_image_candidate(candidate):
                return candidate

            if isinstance(candidate, (list, tuple)):
                pending.extend(candidate)
                continue

            if isinstance(candidate, dict):
                preferred_keys = (
                    "image",
                    "preview",
                    "output",
                    "result",
                    "value",
                    "data",
                    "modified_image",
                    "base_image",
                )
                for key in preferred_keys:
                    if key in candidate:
                        pending.append(candidate[key])
                for value in candidate.values():
                    pending.append(value)

        return None

    def _pil_to_qimage(self, image_obj: object) -> Optional[QImage]:
        if image_obj is None:
            return None

        try:
            if hasattr(image_obj, "convert"):
                image_obj = image_obj.convert("RGBA")
        except Exception:
            return None

        try:
            from PIL.ImageQt import ImageQt

            qimage = QImage(ImageQt(image_obj))
            if not qimage.isNull():
                return qimage
        except Exception:
            pass

        try:
            png_buffer = io.BytesIO()
            image_obj.save(png_buffer, format="PNG")
            qimage = QImage.fromData(png_buffer.getvalue(), "PNG")
            if not qimage.isNull():
                return qimage
        except Exception:
            return None

        return None

    def _preview_from_node_properties(self, node_item: NodeItem) -> Optional[object]:
        if node_item.node_type != "Image Import":
            return None

        file_path_value = node_item.node_properties.get("file_path", "")
        file_path = str(file_path_value).strip()
        if not file_path:
            return None

        try:
            from OV_Libs.pillow_compat import Image

            image = Image.open(file_path)
            return image.convert("RGBA") if hasattr(image, "convert") else image
        except Exception:
            return None

    def _update_node_previews(self) -> None:
        for node_id, node_item in self.node_items.items():
            result = self.output_cache.get(node_id)
            preview = self._extract_preview_image(result)
            if preview is None:
                preview = self._preview_from_node_properties(node_item)
            qimage = self._pil_to_qimage(preview)
            node_item.set_preview_image(qimage)

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
                    "width": float(item.rect().width()),
                    "height": float(item.rect().height()),
                    "input_count": len(item.input_port_names),
                    "output_count": len(item.output_port_names),
                    "input_ports": list(item.input_port_names),
                    "output_ports": list(item.output_port_names),
                    **item.node_properties,
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
