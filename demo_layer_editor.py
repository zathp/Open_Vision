#!/usr/bin/env python
"""
Demo of the improved multi-layer parameter editor.

This script demonstrates the new LayerListWidget in action.
Run it to see the enhanced UI for editing Image Layer parameters.

Usage:
    python demo_layer_editor.py
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from layer_editor import LayerListWidget


def main() -> None:
    """Run the layer editor demo."""
    app = QApplication(sys.argv)

    # Create demo layer data
    demo_layers = [
        {
            "image_path": "/path/to/background.png",
            "mask": None,
            "alpha": 255,
            "blend_amount": 1.0,
        },
        {
            "image_path": "/path/to/overlay.png",
            "mask": None,
            "alpha": 200,
            "blend_amount": 0.8,
        },
        {
            "image_path": "/path/to/detail.png",
            "mask": None,
            "alpha": 128,
            "blend_amount": 0.5,
        },
    ]

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Layer Editor Demo")
    window.resize(800, 600)

    # Create central widget with layer editor
    central = QWidget()
    layout = QVBoxLayout(central)

    # Add layer editor
    layer_widget = LayerListWidget(demo_layers, window)
    layout.addWidget(layer_widget)

    # Add print button to show current state
    def print_layers() -> None:
        """Print current layer state to console."""
        import json
        layers = layer_widget.get_layers_data()
        print("\n=== Current Layer Configuration ===")
        print(json.dumps(layers, indent=2))
        print("==================================\n")

    print_btn = QPushButton("Print Current Layers")
    print_btn.clicked.connect(print_layers)
    layout.addWidget(print_btn)

    window.setCentralWidget(central)
    window.show()

    # Print initial state
    print("Starting Layer Editor Demo...")
    print(f"Initial layers: {len(demo_layers)}")
    print("\nInstructions:")
    print("1. Add/remove layers using the buttons")
    print("2. Select layers and edit properties")
    print("3. Use Browse to select image files")
    print("4. Reorder layers with Move Up/Down")
    print("5. Click 'Print Current Layers' to see the data")
    print()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
