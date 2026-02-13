from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys

from PIL import Image
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QImage
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
    QColorDialog,
    QAbstractItemView
)
import math

RgbaColor = Tuple[int, int, int, int]


@dataclass
class ImageRecord:
    path: Path
    original: 'Image.Image'
    modified: 'Image.Image'


class OpenVisionMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Open Vision (PyQt5) - Implemented")
        self.resize(1400, 850)

        self.images: List[ImageRecord] = []
        self.current_image_index: Optional[int] = None
        self.unique_colors: List[RgbaColor] = []
        self.color_mappings: Dict[RgbaColor, RgbaColor] = {}
        self.base_color: Optional[RgbaColor] = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)

        controls_col = QVBoxLayout()
        previews_col = QHBoxLayout()

        self.btn_load_images = QPushButton("Load Images")
        self.btn_apply_current = QPushButton("Apply to Current")
        self.btn_apply_all = QPushButton("Apply to All Images")
        self.btn_save_current = QPushButton("Save Current")
        self.btn_save_all = QPushButton("Save All")
        self.btn_pick_base = QPushButton("Pick Base Color")
        self.btn_select_range = QPushButton("Select Colors in Range")

        self.images_list = QListWidget()
        self.original_colors_list = QListWidget()
        self.original_colors_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.replacement_colors_list = QListWidget()

        self.label_base_color = QLabel("Base: not selected")
        self.label_original_preview = QLabel("Original Preview")
        self.label_modified_preview = QLabel("Modified Preview")

        self.label_original_preview.setAlignment(Qt.AlignCenter)
        self.label_modified_preview.setAlignment(Qt.AlignCenter)
        self.label_original_preview.setMinimumSize(450, 450)
        self.label_modified_preview.setMinimumSize(450, 450)
        self.label_original_preview.setStyleSheet("border: 1px solid #888;")
        self.label_modified_preview.setStyleSheet("border: 1px solid #888;")

        controls_col.addWidget(self.btn_load_images)
        controls_col.addWidget(QLabel("Loaded Images"))
        controls_col.addWidget(self.images_list)
        controls_col.addWidget(QLabel("Original Colors"))
        controls_col.addWidget(self.original_colors_list)
        controls_col.addWidget(QLabel("Replacement Colors"))
        controls_col.addWidget(self.replacement_colors_list)
        controls_col.addWidget(self.label_base_color)
        controls_col.addWidget(self.btn_pick_base)
        controls_col.addWidget(self.btn_select_range)
        controls_col.addWidget(self.btn_apply_current)
        controls_col.addWidget(self.btn_apply_all)
        controls_col.addWidget(self.btn_save_current)
        controls_col.addWidget(self.btn_save_all)

        previews_col.addWidget(self.label_original_preview)
        previews_col.addWidget(self.label_modified_preview)

        root.addLayout(controls_col, stretch=1)
        root.addLayout(previews_col, stretch=2)

    def _connect_signals(self) -> None:
        self.btn_load_images.clicked.connect(self.load_images)
        self.images_list.currentRowChanged.connect(self.on_image_selected)
        self.replacement_colors_list.itemDoubleClicked.connect(self.change_replacement_color)
        self.btn_pick_base.clicked.connect(self.pick_base_color)
        self.btn_select_range.clicked.connect(self.select_by_range)
        self.btn_apply_current.clicked.connect(self.apply_to_current)
        self.btn_apply_all.clicked.connect(self.apply_to_all)
        self.btn_save_current.clicked.connect(self.save_current)
        self.btn_save_all.clicked.connect(self.save_all)

    def load_images(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not file_paths:
            return

        for path_str in file_paths:
            image_path = Path(path_str)
            original = Image.open(image_path).convert("RGBA")
            self.images.append(
                ImageRecord(path=image_path, original=original, modified=original.copy())
            )
            self.images_list.addItem(image_path.name)

        if self.current_image_index is None and self.images:
            self.images_list.setCurrentRow(0)

    def on_image_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.images):
            self.current_image_index = None
            return

        self.current_image_index = index
        self.extract_unique_colors()
        self.populate_color_lists()
        self.refresh_previews()

    def extract_unique_colors(self) -> None:
        if self.current_image_index is None:
            return
        
        current = self.images[self.current_image_index]
        image = current.original
        
        import numpy as np
        img_array = np.array(image)
        pixels = img_array.reshape(-1, 4)
        
        unique = np.unique(pixels, axis=0)
        
        self.unique_colors = [tuple(color) for color in unique]
        
        self.color_mappings = {color: color for color in self.unique_colors}
        
        print("Extracted unique colors:", len(self.unique_colors))

    def populate_color_lists(self) -> None:
        self.original_colors_list.clear()
        self.replacement_colors_list.clear()

        for original_color in self.unique_colors:
            self.original_colors_list.addItem(f"RGBA: {original_color}")
            
            mapped_color = self.color_mappings.get(original_color, original_color)
            self.replacement_colors_list.addItem(f"RGBA: {mapped_color}")

    def change_replacement_color(self) -> None:
        selected_row = self.replacement_colors_list.currentRow()
        if selected_row < 0:
            return

        color = QColorDialog.getColor(parent=self, title="Pick replacement color")
        if not color.isValid():
            return
            
        # Get the new RGBA tuple
        new_color = (color.red(), color.green(), color.blue(), 255)
        
        # Find the original color this row corresponds to
        original_color = self.unique_colors[selected_row]
        
        # Update the mapping dictionary
        self.color_mappings[original_color] = new_color
        
        # Update the UI list item
        self.replacement_colors_list.item(selected_row).setText(f"RGBA: {new_color}")

    def pick_base_color(self) -> None:
        color = QColorDialog.getColor(parent=self, title="Pick base color")
        if not color.isValid():
            return

        self.base_color = (color.red(), color.green(), color.blue(), 255)
        self.label_base_color.setText(f"Base: {self.base_color}")

    def select_by_range(self) -> None:
        if self.base_color is None:
            QMessageBox.warning(self, "No Base Color", "Pick a base color first.")
            return

        tolerance = 30  # You can later make this user-adjustable
        r0, g0, b0, _ = self.base_color

        selected_colors = []

        for color in self.unique_colors:
            r, g, b, a = color
            distance = math.sqrt((r-r0)**2 + (g-g0)**2 + (b-b0)**2)
            if distance <= tolerance:
                selected_colors.append(color)

        # Highlight selected colors in original list
        self.original_colors_list.clearSelection()
        for i, color in enumerate(self.unique_colors):
            if color in selected_colors:
                item = self.original_colors_list.item(i)
                if item is not None:
                    item.setSelected(True)
        print("Base color:", self.base_color)
        print("Total unique colors:", len(self.unique_colors))
        print("Matched:", color)

    def apply_hsv_to_selected(self) -> None:
        raise NotImplementedError("Implement HSV mass-edit for selected colors")

    def apply_hsv_to_all(self) -> None:
        raise NotImplementedError("Implement HSV mass-edit for all replacement mappings")

    def apply_to_current(self) -> None:
        if self.current_image_index is None:
            return
            
        current = self.images[self.current_image_index]
        img = current.original.copy()
        pixels = img.load()
        
        for y in range(img.height):
            for x in range(img.width):
                orig_color = pixels[x, y]
                if orig_color in self.color_mappings:
                    pixels[x, y] = self.color_mappings[orig_color]
                    
        current.modified = img
        self.refresh_previews()

    def apply_to_all(self) -> None:
        if not self.images:
            return
            
        for record in self.images:
            img = record.original.copy()
            pixels = img.load()
            
            for y in range(img.height):
                for x in range(img.width):
                    orig_color = pixels[x, y]
                    if orig_color in self.color_mappings:
                        pixels[x, y] = self.color_mappings[orig_color]
                        
            record.modified = img
            
        self.refresh_previews()
        self._show_info("Success", "Color mappings applied to all loaded images.")

    def save_current(self) -> None:
        if self.current_image_index is None:
            return
            
        current = self.images[self.current_image_index]
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Current Image", str(current.path), "PNG Images (*.png)"
        )
        
        if save_path:
            current.modified.save(save_path, format="PNG")
            self._show_info("Success", "Current image saved successfully.")

    def save_all(self) -> None:
        if not self.images:
            return
            
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if not folder:
            return
            
        out_dir = Path(folder)
        for record in self.images:
            save_path = out_dir / f"modified_{record.path.name}"
            record.modified.save(save_path, format="PNG")
            
        self._show_info("Success", f"All {len(self.images)} images saved to {folder}")

    def refresh_previews(self) -> None:
        if self.current_image_index is None:
            self.label_original_preview.setText("Original Preview")
            self.label_modified_preview.setText("Modified Preview")
            return

        current = self.images[self.current_image_index]
        self._set_preview(self.label_original_preview, current.original)
        self._set_preview(self.label_modified_preview, current.modified)

    def _set_preview(self, label: QLabel, image: 'Image.Image') -> None:
        image_rgb = image.convert("RGB")
        pixmap = QPixmap()
        if not pixmap.loadFromData(self._to_png_bytes(image_rgb), "PNG"):
            label.setText("Preview failed")
            return

        scaled = pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled)

    def _to_png_bytes(self, image: 'Image.Image') -> bytes:
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _show_info(self, title: str, message: str) -> None:
        QMessageBox.information(self, title, message)


def main() -> None:
    app = QApplication(sys.argv)
    window = OpenVisionMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()