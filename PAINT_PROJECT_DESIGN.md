# Paint Project Design Document

## Overview

Paint Projects (.ovpaint) provide an MS Paint-style direct image editing experience within Open Vision. This project type focuses on intuitive, tool-based editing with layer support and integration of the specialized tools from the Initial_Forms collection.

## Project Type Comparison

| Feature | Node Graph (.ovproj) | Paint (.ovpaint) |
|---------|---------------------|------------------|
| **Workflow** | Node-based, batch processing | Direct editing, single canvas |
| **Primary Use** | Complex compositing, filter chains | Quick edits, painting, transformations |
| **Multi-image** | Yes, batch operations | Single image per project |
| **Layers** | No | Yes |
| **Export** | Blender texture maps | Standard image formats |
| **Complexity** | Advanced | Beginner-friendly |

## Paint Editor Architecture

### Core Components

1. **PaintEditorWindow** (paint_editor_window.py)
   - Main window class for paint projects
   - Manages UI layout and tool coordination
   - Handles project save/load operations

2. **Canvas Manager** (paint_canvas.py)
   - Handles image rendering and compositing
   - Zoom and pan controls
   - Grid and guide overlays
   - Mouse event routing to active tool

3. **Layer System** (paint_layers.py)
   - Layer data structures and management
   - Layer compositing and blending
   - Layer file persistence

4. **Tool Manager** (paint_tools.py)
   - Tool registration and switching
   - Tool parameter management
   - Undo/redo command pattern

5. **Initial_Forms Integration** (initial_forms_integration.py)
   - Wrapper classes for Initial_Forms utilities
   - Adapt functional code to tool-based interface
   - PyQt5 parameter dialogs for each tool

## Initial_Forms Tools Integration

### 1. Downsampler Tool

**Source**: `Initial_Forms/Downsampler.py`

**Core Function**: `downsample_image_hsv(input_path, output_size=(32, 32))`

**Integration Plan**:
- Create `DownsamplerTool` class wrapping the function
- UI Panel with:
  - Width input (spinbox, 1-1024 pixels)
  - Height input (spinbox, 1-1024 pixels)
  - Lock aspect ratio checkbox
  - Preview mode toggle
  - Apply button
- Apply to active layer or selection
- Add to undo stack

**Usage**: Pixelation effects, texture reduction, pixel art creation

---

### 2. Mirror Tool

**Source**: `Initial_Forms/Mirror.py`

**Core Function**: `mirror_image(input_path, axis='horizontal', output_path=None)`

**Integration Plan**:
- Create `MirrorTool` class with flip operations
- UI: Four toolbar buttons or dropdown menu
  - Flip Horizontal (↔)
  - Flip Vertical (↕)
  - Flip Diagonal TL-BR (⤢)
  - Flip Diagonal TR-BL (⤡)
- Single-click operation, no parameters
- Apply to active layer or selection
- Add to undo stack

**Usage**: Symmetry creation, texture tiling, mirroring artwork

---

### 3. Region Selector (Crop Tool)

**Source**: `Initial_Forms/RegionSelector.py`

**Core Function**: `crop_with_coordinates(image_path, x1, y1, x2, y2, output_path=None)`

**Integration Plan**:
- Create `CropTool` class with interactive selection
- Canvas interaction:
  - Click and drag to define crop rectangle
  - Show selection overlay with marching ants
  - Handles for resizing selection
  - Coordinate display (x, y, width, height)
- Support out-of-bounds selection with transparency
- Options:
  - Crop layer (destructive)
  - Copy to new layer (non-destructive)
  - Delete outside selection
- Zoom controls integrated into canvas

**Usage**: Extract image regions, remove edges, create transparent margins

---

### 4. Color Replace (Greenscreen Tool)

**Source**: `Initial_Forms/Greenscreen2.py`

**Core Functionality**: 
- Extract unique colors from image
- Select base color and range tolerance
- Replace matching colors with target color or transparency

**Integration Plan**:
- Create `ColorReplaceTool` class adapting the Tkinter logic to PyQt5
- UI Panel with:
  - "Pick Base Color from Canvas" button (eyedropper mode)
  - Base color display swatch
  - "Select in Range" button
  - Range tolerance slider (0-100)
  - Unique colors list (scrollable)
  - Target color picker
  - "Replace with Transparency" checkbox
  - "Apply to Layer" button
- Visual feedback:
  - Highlight affected pixels in preview
  - Before/after split view
- Apply to active layer
- Add to undo stack

**Usage**: Background removal, color correction, greenscreen keying

---

## Layer System Design

### Layer Data Structure

```python
@dataclass
class Layer:
    id: str                    # Unique identifier
    name: str                  # Display name
    image: Image.Image         # PIL Image (RGBA)
    visible: bool = True       # Visibility toggle
    opacity: float = 1.0       # 0.0 to 1.0
    blend_mode: str = "normal" # Future: multiply, screen, overlay, etc.
```

### Layer Operations

- **Create**: New blank layer with canvas size, filled with transparency
- **Duplicate**: Copy existing layer with all properties
- **Delete**: Remove layer with confirmation if only layer
- **Merge Down**: Flatten current layer onto layer below
- **Flatten All**: Composite all visible layers to single layer
- **Reorder**: Move layer up/down in stack
- **Rename**: Edit layer name

### Layer UI

- Thumbnail preview (64x64 pixels)
- Visibility eye icon toggle
- Opacity slider
- Lock icon (future: prevent editing)
- Active layer highlighted
- Right-click context menu for operations

## Tool System Design

### Tool Base Class

```python
class PaintTool(ABC):
    def __init__(self, name: str):
        self.name = name
        self.cursor = Qt.ArrowCursor
        self.parameters = {}
    
    @abstractmethod
    def on_mouse_press(self, event: QMouseEvent, canvas_pos: QPoint):
        pass
    
    @abstractmethod
    def on_mouse_move(self, event: QMouseEvent, canvas_pos: QPoint):
        pass
    
    @abstractmethod
    def on_mouse_release(self, event: QMouseEvent, canvas_pos: QPoint):
        pass
    
    def get_parameter_widget(self) -> QWidget:
        """Return widget for tool-specific parameters"""
        return None
```

### Standard Tools

1. **Brush Tool**: Freehand painting with size and opacity
2. **Pencil Tool**: Hard-edge pixel drawing
3. **Fill Bucket Tool**: Flood fill with tolerance
4. **Eyedropper Tool**: Sample color from canvas
5. **Rectangle Select**: Rectangular selection region
6. **Ellipse Select**: Elliptical selection region
7. **Lasso Select**: Freehand selection path

### Initial_Forms Tools

8. **Downsampler Tool**: Pixelation effect
9. **Mirror Tool**: Flip transformations
10. **Crop Tool**: Region selection and cropping
11. **Color Replace Tool**: Greenscreen/color substitution

## File Format: .ovpaint

### JSON Structure

```json
{
  "schema_version": 1,
  "name": "Project Name",
  "created_at": "2026-02-15T10:30:00",
  "modified_at": "2026-02-15T14:45:00",
  "canvas_width": 800,
  "canvas_height": 600,
  "layers": [
    {
      "id": "layer-uuid-1",
      "name": "Background",
      "image_ref": "layers/layer-uuid-1.png",
      "visible": true,
      "opacity": 1.0,
      "blend_mode": "normal"
    },
    {
      "id": "layer-uuid-2", 
      "name": "Sketch",
      "image_ref": "layers/layer-uuid-2.png",
      "visible": true,
      "opacity": 0.7,
      "blend_mode": "normal"
    }
  ],
  "tool_settings": {
    "last_tool": "brush",
    "foreground_color": [0, 0, 0, 255],
    "background_color": [255, 255, 255, 255],
    "brush_size": 10,
    "brush_opacity": 1.0,
    "fill_tolerance": 32
  },
  "view_settings": {
    "zoom_level": 1.0,
    "pan_offset": [0, 0],
    "show_grid": false,
    "grid_size": 16
  }
}
```

### Storage Structure

Projects are stored as directories with .ovpaint extension:

```
MyProject.ovpaint/
  project.json           # Main project file
  layers/
    layer-uuid-1.png     # Layer images
    layer-uuid-2.png
  thumbnails/
    project_thumb.png    # Project thumbnail for menu
```

## Canvas Rendering Pipeline

1. **Layer Compositing**:
   - Iterate layers bottom-to-top
   - Apply opacity to each layer
   - Composite using blend mode (alpha over for MVP)
   - Cache composited result

2. **Viewport Transform**:
   - Apply zoom scaling
   - Apply pan offset
   - Clip to visible region

3. **Overlay Drawing**:
   - Grid (if enabled)
   - Guides (if any)
   - Selection marching ants
   - Tool cursors and previews

4. **Performance**:
   - Only recomposite when layers change
   - Only redraw when viewport or overlays change
   - Use QPixmap cache for fast blitting

## Undo/Redo System

### Command Pattern

```python
class PaintCommand(ABC):
    @abstractmethod
    def execute(self):
        pass
    
    @abstractmethod
    def undo(self):
        pass
```

### Example Commands

- `BrushStrokeCommand`: Records pixel changes from brush
- `LayerCreateCommand`: Add new layer
- `LayerDeleteCommand`: Remove layer (stores copy for undo)
- `MirrorCommand`: Flip transformation
- `ColorReplaceCommand`: Color substitution operation

### Undo Stack

- Configurable depth (default 50 actions)
- Clear on project close
- Optional: Save to project file for persistent undo

## Initial Development Roadmap

### Phase 1: Basic Structure
1. Create `paint_editor_window.py` with skeleton UI
2. Implement basic canvas rendering
3. Add layer data structures and UI
4. Implement project save/load for .ovpaint format

### Phase 2: Initial_Forms Integration
1. Port Downsampler tool with UI
2. Port Mirror tool with UI
3. Port Region Selector as Crop tool
4. Port Color Replace tool (Greenscreen)

### Phase 3: Basic Paint Tools
1. Implement Brush tool
2. Implement Pencil tool
3. Implement Fill Bucket
4. Implement Eyedropper

### Phase 4: Undo/Redo
1. Create command pattern base classes
2. Add undo stack to editor
3. Implement undo for all tools
4. Add keyboard shortcuts (Ctrl+Z, Ctrl+Y)

### Phase 5: Polish
1. Add zoom and pan controls
2. Improve canvas rendering performance
3. Add tool parameter persistence
4. Add export functionality

## User Workflow Examples

### Example 1: Creating Pixel Art

1. Create new Paint Project (32x32 canvas)
2. Use Pencil tool to draw base shapes
3. Use Fill Bucket to add colors
4. Use Mirror tool to create symmetry
5. Use Downsampler to test different sizes
6. Export as PNG

### Example 2: Background Removal

1. Open existing image as new Paint Project
2. Select Color Replace tool
3. Pick background color from canvas
4. Adjust range tolerance slider
5. Preview affected pixels
6. Replace with transparency
7. Use Crop tool to trim transparent edges
8. Export as PNG with alpha

### Example 3: Multi-Layer Composition

1. Create new Paint Project
2. Load image as Background layer
3. Create new layer for edits
4. Use Brush to paint additions
5. Use Mirror to create symmetrical elements
6. Adjust layer opacity for blending
7. Flatten when satisfied
8. Export final composite

## Future Enhancements

- Blend modes (multiply, screen, overlay, etc.)
- Layer groups for organization
- Adjustment layers (non-destructive color correction)
- Filter layers (non-destructive effects)
- Animation timeline (frame-based editing)
- Pressure-sensitive tablet support
- Custom brush creation
- Scriptable actions
