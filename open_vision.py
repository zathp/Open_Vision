from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys

from PIL import Image
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap
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
)

RgbaColor = Tuple[int, int, int, int]


@dataclass
class ImageRecord:
    path: Path
    original: Image.Image
    modified: Image.Image


class OpenVisionMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Open Vision (PyQt5) - Skeleton")
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
        raise NotImplementedError("Implement extraction of unique RGBA values from current image")

    def populate_color_lists(self) -> None:
        raise NotImplementedError("Implement syncing original/replacement list widgets")

    def change_replacement_color(self) -> None:
        selected = self.replacement_colors_list.currentItem()
        if selected is None:
            return

        color = QColorDialog.getColor(parent=self, title="Pick replacement color")
        if not color.isValid():
            return

        self._show_info("TODO", "Wire selected replacement color into color_mappings")

    def pick_base_color(self) -> None:
        color = QColorDialog.getColor(parent=self, title="Pick base color")
        if not color.isValid():
            return

        self.base_color = (color.red(), color.green(), color.blue(), 255)
        self.label_base_color.setText(f"Base: {self.base_color}")

    def select_by_range(self) -> None:
        raise NotImplementedError("Implement RGB/HSV tolerance matching for color selection")

    def apply_hsv_to_selected(self) -> None:
        raise NotImplementedError("Implement HSV mass-edit for selected colors")

    def apply_hsv_to_all(self) -> None:
        raise NotImplementedError("Implement HSV mass-edit for all replacement mappings")

    def apply_to_current(self) -> None:
        raise NotImplementedError("Implement applying color_mappings to current image")

    def apply_to_all(self) -> None:
        raise NotImplementedError("Implement applying color_mappings to all loaded images")

    def save_current(self) -> None:
        raise NotImplementedError("Implement save dialog and export for active modified image")

    def save_all(self) -> None:
        raise NotImplementedError("Implement batch output folder save for all modified images")

    def refresh_previews(self) -> None:
        if self.current_image_index is None:
            self.label_original_preview.setText("Original Preview")
            self.label_modified_preview.setText("Modified Preview")
            return

        current = self.images[self.current_image_index]
        self._set_preview(self.label_original_preview, current.original)
        self._set_preview(self.label_modified_preview, current.modified)

    def _set_preview(self, label: QLabel, image: Image.Image) -> None:
        image_rgb = image.convert("RGB")
        width, height = image_rgb.size
        raw = image_rgb.tobytes("raw", "RGB")
        pixmap = QPixmap()
        if not pixmap.loadFromData(self._to_png_bytes(image_rgb), "PNG"):
            label.setText("Preview failed")
            return

        scaled = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)

    def _to_png_bytes(self, image: Image.Image) -> bytes:
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
