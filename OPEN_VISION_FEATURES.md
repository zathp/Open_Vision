# Open Vision (PyQt5) - Implemented Features

This document describes what is currently implemented in the Open Vision application.

## Project Architecture

Open Vision supports two distinct project types:

### 1. Node Graph Projects (.ovproj)
- Advanced node-based workflow for complex image processing
- Filter stacking and visual node chaining
- Multi-image batch processing
- Blender texture export pipeline

### 2. Paint Projects (.ovpaint) 
- MS Paint-style direct image editing
- Tool palette with Initial_Forms integrations
- Layer-based editing
- Quick transformations and touch-ups

## Current Scope - Main Application
- PyQt5 desktop app with project menu launcher
- Create and open both .ovproj and .ovpaint project types
- Project listing and selection interface
- Separate editor windows launched per project type

## Implemented UI Structure - Main Menu (open_vision.py)
- Main window class: `OpenVisionMainWindow`
- Project menu interface with:
  - Create Project button (with type selector)
  - Open Project File button
  - Refresh Projects button
  - Launch Selected Project button
  - Available Projects list
  - Selected project display

## Implemented UI Structure - Node Graph Editor (node_editor_window.py)
- Window class: `NodeEditorWindow`
- Left control column contains:
  - Load Images button
  - Loaded Images list
  - Original Colors list
  - Replacement Colors list
  - Base color label
  - Pick Base Color button
  - Select Colors in Range button
  - Apply to Current button
  - Apply to All Images button
  - Save Current button
  - Save All button
- Right section contains side-by-side preview labels:
  - Original Preview
  - Modified Preview

## Planned UI Structure - Paint Editor (paint_editor_window.py)
- Window class: `PaintEditorWindow`
- Tool palette sidebar:
  - Brush/Pencil tools
  - Fill bucket
  - Eyedropper
  - Selection tools
  - Initial_Forms tools section:
    - Downsampler (pixelation effect)
    - Mirror (flip transformations)
    - Region Selector (crop tool)
    - Color Replace (greenscreen)
- Layer panel:
  - Layer list with visibility toggles
  - Add/Delete/Merge layer buttons
  - Layer opacity controls
- Main canvas area:
  - Scrollable/zoomable image canvas
  - Tool cursor feedback
  - Grid overlay toggle
- Bottom toolbar:
  - Zoom controls
  - Undo/Redo buttons
  - Color picker (foreground/background)
  - Tool parameters panel

## Implemented Data Model

### Project Store (project_store.py)
- `.ovproj` format for node graph projects
- `.ovpaint` format for paint projects (to be implemented)
- Project creation, loading, and saving
- Schema versioning system

### Node Graph Projects
- `ImageRecord` dataclass:
  - `path: Path`
  - `original: Pillow Image`
  - `modified: Pillow Image`
- Project state:
  - `images`
  - `current_image_index`
  - `unique_colors`
  - `color_mappings`
  - `base_color`
  - `node_graph` (nodes and connections)
  - `filter_stacks`
  - `output_presets`

### Paint Projects (Planned)
- `PaintProject` dataclass:
  - `canvas_size: tuple[int, int]`
  - `layers: list[Layer]`
  - `active_layer_index: int`
  - `tool_settings: dict`
- `Layer` dataclass:
  - `name: str`
  - `image: Pillow Image`
  - `visible: bool`
  - `opacity: float`
- Paint state:
  - `current_tool`
  - `foreground_color`
  - `background_color`
  - `brush_size`
  - `undo_stack`
  - `redo_stack`

## Implemented Behaviors

### 1) App startup and project selection
- `main()` creates `QApplication`, opens `OpenVisionMainWindow`, and enters event loop.
- Main menu displays available projects from Projects directory.
- User can create new project (choosing type) or open existing project.
- Appropriate editor window launches based on project type.

### 2) Node Graph Editor - Signal wiring
- Buttons/lists are connected to handler methods in `_connect_signals()`.
- Includes double-click handler for replacement color list.

### 3) Node Graph Editor - Batch image loading
- `load_images()` uses a file picker for `png/jpg/jpeg/bmp`.
- Each loaded image is converted to `RGBA` with Pillow.
- Both original and initial modified images are stored.
- Loaded image names are added to the image list.
- First image is auto-selected after initial load.

### 4) Node Graph Editor - Image selection workflow hook
- `on_image_selected()` validates index and updates current selection.
- Calls extraction/list/population/preview pipeline methods.

### 5) Node Graph Editor - Base color picking
- `pick_base_color()` opens `QColorDialog`.
- Stores selected color as RGBA tuple (alpha fixed to 255).
- Updates base color label text.

### 6) Node Graph Editor - Preview rendering
- `refresh_previews()` updates both original/modified preview panes.
- `_set_preview()` converts Pillow image to pixmap and scales to label size.
- `_to_png_bytes()` helper converts Pillow image to PNG bytes.

### 7) Paint Editor - Initial_Forms Tool Integration (Planned)
- **Downsampler Tool**: Apply HSV-based pixelation effects to active layer
  - Parameter controls: output size (width x height)
  - Preserves transparency, averages opaque pixels only
  
- **Mirror Tool**: Flip image transformations
  - Options: horizontal, vertical, diagonal (TL-BR), diagonal (TR-BL)
  - Applies to active layer or selection
  
- **Region Selector Tool**: Interactive crop with transparency
  - Click-drag selection rectangle
  - Supports out-of-bounds selection with transparent fill
  - Zoom controls for precision
  
- **Color Replace Tool**: Greenscreen/chroma key functionality
  - Pick base color from canvas
  - Adjustable color range tolerance
  - Replace matched colors with transparency or chosen color
  - Visual feedback of affected pixels

### 8) Paint Editor - Layer Management (Planned)
- Create new layer (blank or from image)
- Delete selected layer
- Reorder layers via drag-drop
- Toggle layer visibility
- Adjust layer opacity
- Flatten visible layers
- Merge down to layer below

### 9) Paint Editor - Direct Painting (Planned)
- Brush tool with size and opacity controls
- Pencil tool for hard-edge pixel editing
- Fill bucket with tolerance setting
- Eyedropper to sample colors from canvas
- Undo/redo for all paint operations

### 10) Information popup helper
- `_show_info()` displays user messages via `QMessageBox.information`.

## Partially Implemented / Placeholder Behavior
- Node Graph Editor: `change_replacement_color()` currently opens color picker, but does not yet persist mapping updates.
- Paint Editor: Full implementation pending - see TODO roadmap.
- Several core processing methods intentionally raise `NotImplementedError` and are listed in the TODO document.

## Available Initial_Forms Tools

The following standalone tools from `Initial_Forms/` are available for integration into Paint Editor:

### Downsampler.py
- Function: `downsample_image_hsv(input_path, output_size=(32, 32))`
- HSV-based image downsampling with transparency preservation
- Averages only fully opaque pixels (alpha = 255)
- Returns PIL Image object
- Useful for pixel art effects and texture reduction

### Mirror.py  
- Function: `mirror_image(input_path, axis='horizontal', output_path=None)`
- Flip transformations along multiple axes
- Axes: 'horizontal', 'vertical', 'diagonal_tl_br', 'diagonal_tr_bl'
- Returns PIL Image object
- Useful for symmetry creation and texture tiling

### RegionSelector.py
- Interactive GUI tool for region selection and cropping
- Supports out-of-bounds selection with transparent RGBA areas
- Features zoom controls for precise selection
- Both GUI and programmatic `crop_with_coordinates()` function
- Useful for extracting image portions and creating transparent margins

### Greenscreen2.py / Greenscreen2_Batch.py
- Interactive color replacement tool (Tkinter GUI)
- Pick base color and select similar colors in range
- Replace selected colors with transparency or alternate colors
- Batch processing support in Greenscreen2_Batch.py
- Useful for background removal and color substitution

## Dependencies Used by Current Implementation
- `PyQt5`
- `Pillow`
- `numpy` (for Initial_Forms tools)
- Python standard library (`dataclasses`, `pathlib`, `typing`, `sys`, `json`, `uuid`, `datetime`)