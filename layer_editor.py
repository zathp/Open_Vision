"""
Multi-layer parameter editor for Image Layer node.

Provides an intuitive UI for editing layers with:
- Visual layer stack display
- Per-layer controls (alpha, blend_amount, file selection)
- Layer reordering and management
- Preview support
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
import json

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class LayerListWidget(QWidget):
    """Visual layer stack editor with controls."""

    def __init__(self, layers_data: List[Dict[str, Any]], parent=None) -> None:
        """
        Initialize layer list editor.

        Args:
            layers_data: List of layer dictionaries with keys:
                - image_path: str (file path to layer image)
                - mask: Optional (mask path, not yet implemented)
                - alpha: int (0-255, opacity)
                - blend_amount: float (0.0-1.0, contribution)
        """
        super().__init__(parent)
        self.layers = [dict(layer) for layer in layers_data]  # Deep copy
        self._init_ui()

    def _init_ui(self) -> None:
        """Build the layer editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header / info
        info = QLabel("Layers (drag to reorder, edit properties below):")
        info.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(info)

        # Layer list table
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["#", "Image Path", "Alpha", "Blend", "Actions"]
        )
        self.table.setMaximumHeight(200)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, header.ResizeToContents)  # #
        header.setSectionResizeMode(1, header.Stretch)  # Image Path
        header.setSectionResizeMode(2, header.ResizeToContents)  # Alpha
        header.setSectionResizeMode(3, header.ResizeToContents)  # Blend
        header.setSectionResizeMode(4, header.ResizeToContents)  # Actions

        self._populate_table()
        layout.addWidget(self.table)

        # Action buttons
        button_row = QHBoxLayout()
        self.btn_add = QPushButton("Add Layer", self)
        self.btn_add.clicked.connect(self._add_layer)
        self.btn_remove = QPushButton("Remove Layer", self)
        self.btn_remove.clicked.connect(self._remove_layer)
        self.btn_move_up = QPushButton("Move Up", self)
        self.btn_move_up.clicked.connect(self._move_layer_up)
        self.btn_move_down = QPushButton("Move Down", self)
        self.btn_move_down.clicked.connect(self._move_layer_down)

        button_row.addWidget(self.btn_add)
        button_row.addWidget(self.btn_remove)
        button_row.addWidget(self.btn_move_up)
        button_row.addWidget(self.btn_move_down)
        button_row.addStretch()
        layout.addLayout(button_row)

        # Properties panel for selected layer
        props_label = QLabel("Layer Properties:")
        props_label.setStyleSheet("font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        layout.addWidget(props_label)

        self.props_widget = self._create_properties_panel()
        layout.addWidget(self.props_widget)

        layout.addStretch()

        # Connect table selection to update properties panel
        self.table.itemSelectionChanged.connect(self._on_layer_selected)

    def _populate_table(self) -> None:
        """Populate table with current layers."""
        self.table.setRowCount(0)

        for idx, layer in enumerate(self.layers):
            self.table.insertRow(idx)

            # Column 0: Index
            index_item = QTableWidgetItem(str(idx + 1))
            index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(idx, 0, index_item)

            # Column 1: Image Path
            path = layer.get("image_path", "")
            path_item = QTableWidgetItem(path)
            path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(idx, 1, path_item)

            # Column 2: Alpha (display only, edited in props)
            alpha = layer.get("alpha", 255)
            alpha_item = QTableWidgetItem(str(alpha))
            alpha_item.setFlags(alpha_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(idx, 2, alpha_item)

            # Column 3: Blend Amount (display only, edited in props)
            blend = layer.get("blend_amount", 1.0)
            blend_item = QTableWidgetItem(f"{blend:.2f}")
            blend_item.setFlags(blend_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(idx, 3, blend_item)

            # Column 4: Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(2)

            browse_btn = QPushButton("Browse", self)
            browse_btn.setMaximumWidth(60)
            browse_btn.clicked.connect(lambda checked=False, i=idx: self._browse_image(i))
            actions_layout.addWidget(browse_btn)

            actions_layout.addStretch()
            self.table.setCellWidget(idx, 4, actions_widget)

    def _create_properties_panel(self) -> QWidget:
        """Create properties editor for selected layer."""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Image path input with browse
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Image Path:"))
        self.prop_path = QLineEdit(self)
        self.prop_path.setReadOnly(True)
        path_layout.addWidget(self.prop_path, stretch=1)
        path_browse = QPushButton("Browse...", self)
        path_browse.setMaximumWidth(80)
        path_browse.clicked.connect(self._browse_current_layer_image)
        path_layout.addWidget(path_browse)
        layout.addLayout(path_layout)

        # Alpha slider + spinbox
        alpha_layout = QHBoxLayout()
        alpha_layout.addWidget(QLabel("Alpha (Opacity):"))
        self.prop_alpha_slider = QSlider(Qt.Horizontal, self)
        self.prop_alpha_slider.setMinimum(0)
        self.prop_alpha_slider.setMaximum(255)
        self.prop_alpha_slider.setValue(255)
        self.prop_alpha_slider.valueChanged.connect(self._on_alpha_changed)
        alpha_layout.addWidget(self.prop_alpha_slider, stretch=1)

        self.prop_alpha_spin = QSpinBox(self)
        self.prop_alpha_spin.setMinimum(0)
        self.prop_alpha_spin.setMaximum(255)
        self.prop_alpha_spin.setValue(255)
        self.prop_alpha_spin.setMaximumWidth(60)
        self.prop_alpha_spin.valueChanged.connect(self._on_alpha_spin_changed)
        alpha_layout.addWidget(self.prop_alpha_spin)
        alpha_layout.addWidget(QLabel("/ 255"))
        layout.addLayout(alpha_layout)

        # Blend amount slider + spinbox
        blend_layout = QHBoxLayout()
        blend_layout.addWidget(QLabel("Blend Amount:"))
        self.prop_blend_slider = QSlider(Qt.Horizontal, self)
        self.prop_blend_slider.setMinimum(0)
        self.prop_blend_slider.setMaximum(100)
        self.prop_blend_slider.setValue(100)
        self.prop_blend_slider.valueChanged.connect(self._on_blend_changed)
        blend_layout.addWidget(self.prop_blend_slider, stretch=1)

        self.prop_blend_spin = QDoubleSpinBox(self)
        self.prop_blend_spin.setMinimum(0.0)
        self.prop_blend_spin.setMaximum(1.0)
        self.prop_blend_spin.setSingleStep(0.05)
        self.prop_blend_spin.setDecimals(2)
        self.prop_blend_spin.setValue(1.0)
        self.prop_blend_spin.setMaximumWidth(70)
        self.prop_blend_spin.valueChanged.connect(self._on_blend_spin_changed)
        blend_layout.addWidget(self.prop_blend_spin)
        layout.addLayout(blend_layout)

        layout.addStretch()
        return panel

    def _on_layer_selected(self) -> None:
        """Update properties panel when layer is selected."""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            self.props_widget.setEnabled(False)
            return

        self.props_widget.setEnabled(True)
        row = selected_rows[0].row()
        layer = self.layers[row]

        # Block signals to avoid circular updates
        self.prop_path.blockSignals(True)
        self.prop_alpha_slider.blockSignals(True)
        self.prop_alpha_spin.blockSignals(True)
        self.prop_blend_slider.blockSignals(True)
        self.prop_blend_spin.blockSignals(True)

        self.prop_path.setText(layer.get("image_path", ""))
        alpha = int(layer.get("alpha", 255))
        self.prop_alpha_slider.setValue(alpha)
        self.prop_alpha_spin.setValue(alpha)

        blend = float(layer.get("blend_amount", 1.0))
        self.prop_blend_slider.setValue(int(round(blend * 100)))
        self.prop_blend_spin.setValue(blend)

        self.prop_path.blockSignals(False)
        self.prop_alpha_slider.blockSignals(False)
        self.prop_alpha_spin.blockSignals(False)
        self.prop_blend_slider.blockSignals(False)
        self.prop_blend_spin.blockSignals(False)

    def _on_alpha_changed(self, value: int) -> None:
        """Update alpha when slider changes."""
        self.prop_alpha_spin.blockSignals(True)
        self.prop_alpha_spin.setValue(value)
        self.prop_alpha_spin.blockSignals(False)
        self._update_selected_layer()

    def _on_alpha_spin_changed(self, value: int) -> None:
        """Update alpha when spinbox changes."""
        self.prop_alpha_slider.blockSignals(True)
        self.prop_alpha_slider.setValue(value)
        self.prop_alpha_slider.blockSignals(False)
        self._update_selected_layer()

    def _on_blend_changed(self, value: int) -> None:
        """Update blend when slider changes."""
        blend_value = float(value) / 100.0
        self.prop_blend_spin.blockSignals(True)
        self.prop_blend_spin.setValue(blend_value)
        self.prop_blend_spin.blockSignals(False)
        self._update_selected_layer()

    def _on_blend_spin_changed(self, value: float) -> None:
        """Update blend when spinbox changes."""
        self.prop_blend_slider.blockSignals(True)
        self.prop_blend_slider.setValue(int(round(value * 100)))
        self.prop_blend_slider.blockSignals(False)
        self._update_selected_layer()

    def _update_selected_layer(self) -> None:
        """Save properties back to selected layer."""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        self.layers[row]["alpha"] = self.prop_alpha_spin.value()
        self.layers[row]["blend_amount"] = self.prop_blend_spin.value()
        self.layers[row]["image_path"] = self.prop_path.text()

        # Update table display
        self.table.item(row, 2).setText(str(self.layers[row]["alpha"]))
        self.table.item(row, 3).setText(f"{self.layers[row]['blend_amount']:.2f}")
        self.table.item(row, 1).setText(self.layers[row]["image_path"])

    def _browse_image(self, row: int) -> None:
        """Browse for image file and update layer."""
        current_path = self.layers[row].get("image_path", "")
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Layer Image",
            current_path,
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.gif);;All Files (*)",
        )

        if selected_file:
            self.layers[row]["image_path"] = selected_file
            # Update UI
            self.table.item(row, 1).setText(selected_file)
            # If this row is selected, update properties panel too
            selected_rows = self.table.selectedIndexes()
            if selected_rows and selected_rows[0].row() == row:
                self.prop_path.setText(selected_file)

    def _browse_current_layer_image(self) -> None:
        """Browse for image of currently selected layer."""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a layer first.")
            return

        row = selected_rows[0].row()
        self._browse_image(row)

    def _add_layer(self) -> None:
        """Add a new empty layer."""
        new_layer = {
            "image_path": "",
            "image": None,
            "mask": None,
            "alpha": 255,
            "blend_amount": 1.0,
        }
        self.layers.append(new_layer)
        self._populate_table()
        # Select the new layer
        self.table.selectRow(len(self.layers) - 1)

    def _remove_layer(self) -> None:
        """Remove selected layer."""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a layer to remove.")
            return

        row = selected_rows[0].row()
        if len(self.layers) == 1:
            QMessageBox.warning(self, "Last Layer", "Cannot remove the last layer.")
            return

        self.layers.pop(row)
        self._populate_table()

    def _move_layer_up(self) -> None:
        """Move selected layer up in stack."""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row == 0:
            return

        self.layers[row], self.layers[row - 1] = (
            self.layers[row - 1],
            self.layers[row],
        )
        self._populate_table()
        self.table.selectRow(row - 1)

    def _move_layer_down(self) -> None:
        """Move selected layer down in stack."""
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row >= len(self.layers) - 1:
            return

        self.layers[row], self.layers[row + 1] = (
            self.layers[row + 1],
            self.layers[row],
        )
        self._populate_table()
        self.table.selectRow(row + 1)

    def get_layers_data(self) -> List[Dict[str, Any]]:
        """Return edited layers data."""
        return self.layers
