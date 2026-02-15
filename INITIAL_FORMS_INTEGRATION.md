# Initial_Forms Integration Guide

This document provides technical guidance for integrating the standalone Initial_Forms tools into the Paint Editor.

## Overview

The Initial_Forms tools were originally created as standalone command-line and GUI applications. To integrate them into the Paint Editor, we need to:

1. Extract core image processing functions
2. Create PyQt5-compatible tool wrappers
3. Adapt parameters to work with layers and selections
4. Add undo/redo support
5. Integrate with the tool palette UI

## Tool-by-Tool Integration

### 1. Downsampler Integration

#### Source Code Analysis

**File**: `Initial_Forms/Downsampler.py`

**Key Function**:
```python
def downsample_image_hsv(input_path, output_size=(32, 32)):
    # Loads image, converts to RGBA
    # Calculates block sizes for downsampling
    # Averages HSV values from opaque pixels only
    # Returns PIL Image
```

#### Adaptation Strategy

**Create**: `paint_tools/downsampler_tool.py`

```python
from PIL import Image
import numpy as np
from .base_tool import PaintTool
from ..commands import DownsampleCommand

class DownsamplerTool(PaintTool):
    def __init__(self):
        super().__init__("Downsampler")
        self.parameters = {
            'width': 32,
            'height': 32,
            'lock_aspect': True
        }
    
    def apply_to_layer(self, layer_image: Image.Image) -> Image.Image:
        """
        Apply downsampling to a layer image
        Returns new PIL Image
        """
        # Import the core function
        from Initial_Forms.Downsampler import downsample_image_hsv
        
        # Since function expects file path, we need to adapt:
        # Option 1: Save temp file, process, load result
        # Option 2: Extract the processing logic into reusable function
        
        output_size = (self.parameters['width'], self.parameters['height'])
        
        # Extract processing logic here (see below)
        return downsample_image_in_memory(layer_image, output_size)
    
    def get_parameter_widget(self) -> QWidget:
        """Return UI for width/height parameters"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        width_spin = QSpinBox()
        width_spin.setRange(1, 1024)
        width_spin.setValue(self.parameters['width'])
        width_spin.valueChanged.connect(
            lambda v: self._update_param('width', v)
        )
        
        height_spin = QSpinBox()
        height_spin.setRange(1, 1024)
        height_spin.setValue(self.parameters['height'])
        height_spin.valueChanged.connect(
            lambda v: self._update_param('height', v)
        )
        
        lock_check = QCheckBox("Lock Aspect Ratio")
        lock_check.setChecked(self.parameters['lock_aspect'])
        lock_check.stateChanged.connect(
            lambda state: self._update_param('lock_aspect', state == Qt.Checked)
        )
        
        layout.addRow("Width:", width_spin)
        layout.addRow("Height:", height_spin)
        layout.addRow(lock_check)
        
        return widget
```

**Refactor Processing Logic**:

Extract the core algorithm from `downsample_image_hsv` into a function that works with PIL Images directly:

```python
def downsample_image_in_memory(img: Image.Image, output_size: tuple) -> Image.Image:
    """
    Downsample PIL Image using HSV averaging (opaque pixels only)
    
    Args:
        img: PIL Image in RGBA mode
        output_size: (width, height) tuple
    
    Returns:
        Downsampled PIL Image
    """
    # Ensure RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    original_size = img.size
    block_width = original_size[0] / output_size[0]
    block_height = original_size[1] / output_size[1]
    
    img_array = np.array(img)
    output_array = np.zeros((output_size[1], output_size[0], 4), dtype=np.uint8)
    
    # ... rest of processing logic from original function ...
    
    return Image.fromarray(output_array, 'RGBA')
```

#### Undo Command

```python
class DownsampleCommand(PaintCommand):
    def __init__(self, layer, original_image, downsampled_image):
        self.layer = layer
        self.original = original_image.copy()
        self.downsampled = downsampled_image.copy()
    
    def execute(self):
        self.layer.image = self.downsampled.copy()
    
    def undo(self):
        self.layer.image = self.original.copy()
```

---

### 2. Mirror Tool Integration

#### Source Code Analysis

**File**: `Initial_Forms/Mirror.py`

**Key Function**:
```python
def mirror_image(input_path, axis='horizontal', output_path=None):
    # Load image
    # Use PIL transpose methods
    # Returns mirrored PIL Image
```

#### Adaptation Strategy

**Create**: `paint_tools/mirror_tool.py`

```python
from PIL import Image
from .base_tool import PaintTool
from ..commands import MirrorCommand

class MirrorTool(PaintTool):
    def __init__(self):
        super().__init__("Mirror")
        self.axis = 'horizontal'  # Current flip axis
    
    def mirror_horizontal(self, layer_image: Image.Image) -> Image.Image:
        return layer_image.transpose(Image.FLIP_TOP_BOTTOM)
    
    def mirror_vertical(self, layer_image: Image.Image) -> Image.Image:
        return layer_image.transpose(Image.FLIP_LEFT_RIGHT)
    
    def mirror_diagonal_tl_br(self, layer_image: Image.Image) -> Image.Image:
        return layer_image.transpose(Image.TRANSPOSE)
    
    def mirror_diagonal_tr_bl(self, layer_image: Image.Image) -> Image.Image:
        return layer_image.transpose(Image.TRANSVERSE)
    
    def apply_to_layer(self, layer_image: Image.Image, axis: str) -> Image.Image:
        """Apply mirror transformation"""
        if axis == 'horizontal':
            return self.mirror_horizontal(layer_image)
        elif axis == 'vertical':
            return self.mirror_vertical(layer_image)
        elif axis == 'diagonal_tl_br':
            return self.mirror_diagonal_tl_br(layer_image)
        elif axis == 'diagonal_tr_bl':
            return self.mirror_diagonal_tr_bl(layer_image)
        else:
            raise ValueError(f"Invalid axis: {axis}")
```

**UI Integration**: Add toolbar buttons or menu items for each flip operation. No parameter widget needed since it's a single-click operation.

---

### 3. Region Selector (Crop Tool) Integration

#### Source Code Analysis

**File**: `Initial_Forms/RegionSelector.py`

**Key Function**:
```python
def crop_with_coordinates(image_path, x1, y1, x2, y2, output_path=None):
    # Supports out-of-bounds cropping
    # Creates transparent RGBA image
    # Returns cropped PIL Image
```

**GUI Features**:
- Tkinter canvas with selection rectangle
- Zoom controls
- Coordinate display

#### Adaptation Strategy

**Create**: `paint_tools/crop_tool.py`

```python
from PIL import Image
from PyQt5.QtCore import QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor
from .base_tool import PaintTool

class CropTool(PaintTool):
    def __init__(self):
        super().__init__("Crop")
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
    
    def on_mouse_press(self, event, canvas_pos):
        """Start selection rectangle"""
        self.selection_start = canvas_pos
        self.is_selecting = True
    
    def on_mouse_move(self, event, canvas_pos):
        """Update selection rectangle"""
        if self.is_selecting:
            self.selection_end = canvas_pos
            # Trigger canvas redraw to show selection
    
    def on_mouse_release(self, event, canvas_pos):
        """Finalize selection"""
        self.selection_end = canvas_pos
        self.is_selecting = False
        # Selection is complete, ready to crop
    
    def draw_selection_overlay(self, painter: QPainter):
        """Draw marching ants selection rectangle"""
        if self.selection_start and self.selection_end:
            rect = QRect(self.selection_start, self.selection_end)
            pen = QPen(QColor(0, 0, 0), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)
    
    def crop_with_transparency(self, img: Image.Image, 
                               x1: int, y1: int, 
                               x2: int, y2: int) -> Image.Image:
        """
        Crop with out-of-bounds support (transparent areas)
        Adapted from RegionSelector.py
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img_width, img_height = img.size
        
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        
        crop_width = right - left
        crop_height = bottom - top
        
        out_of_bounds = (left < 0 or top < 0 or 
                        right > img_width or bottom > img_height)
        
        if out_of_bounds:
            # Create transparent image for full crop region
            cropped = Image.new('RGBA', (crop_width, crop_height), (0, 0, 0, 0))
            
            # Calculate overlap region
            overlap_left = max(0, left)
            overlap_top = max(0, top)
            overlap_right = min(img_width, right)
            overlap_bottom = min(img_height, bottom)
            
            if overlap_right > overlap_left and overlap_bottom > overlap_top:
                # Extract overlapping portion
                img_portion = img.crop((overlap_left, overlap_top, 
                                       overlap_right, overlap_bottom))
                
                # Calculate paste position
                paste_x = overlap_left - left
                paste_y = overlap_top - top
                
                # Paste onto transparent canvas
                cropped.paste(img_portion, (paste_x, paste_y))
            
            return cropped
        else:
            # Simple crop, all within bounds
            return img.crop((left, top, right, bottom))
```

**UI Integration**:
- Add "Crop" and "Crop to New Layer" buttons when selection is active
- Display selection coordinates and dimensions
- Add to undo stack when crop is applied

---

### 4. Color Replace (Greenscreen) Integration

#### Source Code Analysis

**File**: `Initial_Forms/Greenscreen2.py`

**Key Features**:
- Extract unique colors from image (only opaque pixels)
- Pick base color
- Find colors within HSV range tolerance
- Replace matched colors with transparency or chosen color

**GUI**: Full Tkinter application with color lists and previews

#### Adaptation Strategy

**Create**: `paint_tools/color_replace_tool.py`

```python
from PIL import Image
import numpy as np
import colorsys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSlider, QListWidget
from .base_tool import PaintTool

class ColorReplaceTool(PaintTool):
    def __init__(self):
        super().__init__("Color Replace")
        self.base_color = None
        self.unique_colors = []
        self.color_mappings = {}
        self.range_tolerance = 10  # 0-100 scale
    
    def extract_unique_colors(self, img: Image.Image) -> list:
        """
        Extract unique opaque colors from image
        Adapted from Greenscreen2.py
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img_array = np.array(img)
        
        # Get fully opaque pixels only
        opaque_mask = img_array[:, :, 3] == 255
        opaque_pixels = img_array[opaque_mask][:, :3]  # RGB only
        
        # Find unique colors
        unique_colors = np.unique(opaque_pixels.reshape(-1, 3), axis=0)
        
        return [tuple(color) for color in unique_colors]
    
    def find_colors_in_range(self, base_color: tuple, 
                            all_colors: list, 
                            tolerance: float) -> list:
        """
        Find colors within HSV range of base color
        Adapted from Greenscreen2.py
        
        Args:
            base_color: RGB tuple (0-255)
            all_colors: List of RGB tuples
            tolerance: 0-100 range tolerance
        
        Returns:
            List of matching RGB tuples
        """
        base_hsv = colorsys.rgb_to_hsv(
            base_color[0]/255, 
            base_color[1]/255, 
            base_color[2]/255
        )
        
        # Convert tolerance to HSV ranges
        h_threshold = tolerance / 100.0 * 0.05  # Hue
        s_threshold = tolerance / 100.0 * 0.3   # Saturation
        v_threshold = tolerance / 100.0 * 0.3   # Value
        
        matching_colors = []
        
        for color in all_colors:
            color_hsv = colorsys.rgb_to_hsv(
                color[0]/255,
                color[1]/255,
                color[2]/255
            )
            
            h_diff = abs(color_hsv[0] - base_hsv[0])
            h_diff = min(h_diff, 1.0 - h_diff)  # Circular hue
            
            if (h_diff <= h_threshold and
                abs(color_hsv[1] - base_hsv[1]) <= s_threshold and
                abs(color_hsv[2] - base_hsv[2]) <= v_threshold):
                matching_colors.append(color)
        
        return matching_colors
    
    def replace_colors(self, img: Image.Image, 
                      color_map: dict, 
                      replace_with_transparency: bool = True) -> Image.Image:
        """
        Replace colors according to mapping
        
        Args:
            img: Source PIL Image
            color_map: Dict mapping old RGB tuple -> new RGB tuple
            replace_with_transparency: If True, set alpha to 0 instead of replacing color
        
        Returns:
            Modified PIL Image
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img_array = np.array(img)
        result_array = img_array.copy()
        
        for old_color, new_color in color_map.items():
            # Find all pixels matching old_color
            mask = ((img_array[:, :, 0] == old_color[0]) &
                   (img_array[:, :, 1] == old_color[1]) &
                   (img_array[:, :, 2] == old_color[2]) &
                   (img_array[:, :, 3] == 255))  # Only opaque pixels
            
            if replace_with_transparency:
                # Set alpha to 0
                result_array[mask, 3] = 0
            else:
                # Replace color
                result_array[mask, 0] = new_color[0]
                result_array[mask, 1] = new_color[1]
                result_array[mask, 2] = new_color[2]
        
        return Image.fromarray(result_array, 'RGBA')
    
    def get_parameter_widget(self) -> QWidget:
        """Return UI panel for color replacement"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Pick base color from canvas button
        pick_btn = QPushButton("Pick Color from Canvas")
        pick_btn.clicked.connect(self._activate_eyedropper)
        layout.addWidget(pick_btn)
        
        # Base color display
        self.base_color_label = QLabel("No color selected")
        layout.addWidget(self.base_color_label)
        
        # Range tolerance slider
        layout.addWidget(QLabel("Range Tolerance:"))
        tolerance_slider = QSlider(Qt.Horizontal)
        tolerance_slider.setRange(0, 100)
        tolerance_slider.setValue(self.range_tolerance)
        tolerance_slider.valueChanged.connect(self._update_tolerance)
        layout.addWidget(tolerance_slider)
        
        # Select colors in range button
        select_range_btn = QPushButton("Select Colors in Range")
        select_range_btn.clicked.connect(self._select_in_range)
        layout.addWidget(select_range_btn)
        
        # Unique colors list
        layout.addWidget(QLabel("Unique Colors:"))
        self.colors_list = QListWidget()
        layout.addWidget(self.colors_list)
        
        # Apply button
        apply_btn = QPushButton("Replace with Transparency")
        apply_btn.clicked.connect(self._apply_replacement)
        layout.addWidget(apply_btn)
        
        return widget
```

**Eyedropper Mode**: When "Pick Color from Canvas" is clicked, temporarily switch to eyedropper cursor. Click on canvas to sample color.

---

## Common Patterns

### Working with Layers

All tools should work on the active layer:

```python
def apply_tool_to_active_layer(self, editor_state):
    """Standard pattern for applying tool to layer"""
    active_layer = editor_state.get_active_layer()
    
    # Get original image
    original_image = active_layer.image.copy()
    
    # Apply tool processing
    modified_image = self.process_image(original_image)
    
    # Create undo command
    command = ToolCommand(active_layer, original_image, modified_image)
    
    # Execute and add to undo stack
    command.execute()
    editor_state.undo_stack.push(command)
```

### Handling Selections

If a selection is active, only process selected region:

```python
def apply_with_selection(self, layer_image, selection_mask):
    """Apply tool only to selected region"""
    # Copy original
    result = layer_image.copy()
    
    # Process entire image
    processed = self.process_image(layer_image)
    
    # Composite using selection mask
    result_array = np.array(result)
    processed_array = np.array(processed)
    mask_array = np.array(selection_mask)
    
    # Blend based on mask
    result_array[mask_array > 0] = processed_array[mask_array > 0]
    
    return Image.fromarray(result_array)
```

### Progress Feedback

For long-running operations:

```python
def apply_to_layer(self, layer_image, progress_callback=None):
    """Apply tool with optional progress reporting"""
    total_steps = 100
    
    for step in range(total_steps):
        # Do processing...
        
        if progress_callback:
            progress_callback(step / total_steps * 100)
    
    return processed_image
```

## Testing Strategy

### Unit Tests

Test each tool's core functionality independently:

```python
def test_downsampler():
    # Create test image
    test_img = Image.new('RGBA', (64, 64), (255, 0, 0, 255))
    
    # Apply downsampling
    result = downsample_image_in_memory(test_img, (16, 16))
    
    # Verify dimensions
    assert result.size == (16, 16)
    
    # Verify mode
    assert result.mode == 'RGBA'
```

### Integration Tests

Test tools within the Paint Editor context:

```python
def test_mirror_tool_integration():
    # Create mock editor state
    editor = MockPaintEditor()
    editor.create_layer("Test Layer")
    
    # Load test image to layer
    test_img = Image.open("test_data/test.png")
    editor.active_layer.image = test_img
    
    # Apply mirror tool
    mirror_tool = MirrorTool()
    mirror_tool.apply_to_layer(editor.active_layer.image, 'horizontal')
    
    # Verify result
    assert editor.active_layer.image.size == test_img.size
    # More specific verification...
```

## Performance Considerations

### Image Copying

Always work on copies to enable undo:

```python
# Good: Non-destructive
original = layer.image.copy()
modified = self.process_image(original)

# Bad: Destructive
self.process_image(layer.image)  # Modifies in place
```

### NumPy Optimization

Use NumPy for pixel-level operations:

```python
# Slow: Python loops
for y in range(height):
    for x in range(width):
        pixel = img.getpixel((x, y))
        # Process...

# Fast: NumPy array operations
img_array = np.array(img)
# Vectorized operations...
result = Image.fromarray(img_array)
```

### Preview Generation

Generate low-res previews for real-time feedback:

```python
def generate_preview(self, full_image, max_size=256):
    """Create smaller preview for UI"""
    full_image.thumbnail((max_size, max_size), Image.LANCZOS)
    return full_image
```

## Conclusion

The Initial_Forms tools provide proven image processing algorithms that can be adapted to work within the Paint Editor's tool system. Key adaptation points:

1. **Extract core logic** from file I/O wrappers
2. **Work with PIL Images** directly instead of file paths
3. **Create PyQt5 parameter widgets** instead of Tkinter GUIs
4. **Add undo/redo support** via command pattern
5. **Integrate with layer system** and selections

This approach preserves the valuable processing code while making it fit naturally into the Paint Editor's architecture.
