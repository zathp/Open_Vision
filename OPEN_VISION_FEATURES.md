# Open Vision (PyQt5) - Implemented Features

This document describes what is currently implemented in `open_vision.py`.

## Current Scope
- PyQt5 desktop app shell for image color-replacement workflow.
- Batch image loading and per-image selection.
- UI skeleton for color mapping, base color selection, range selection, apply, and save actions.

## Implemented UI Structure
- Main window class: `OpenVisionMainWindow`.
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

## Implemented Data Model
- `ImageRecord` dataclass:
  - `path: Path`
  - `original: Pillow Image`
  - `modified: Pillow Image`
- App state:
  - `images`
  - `current_image_index`
  - `unique_colors`
  - `color_mappings`
  - `base_color`

## Implemented Behaviors

### 1) App startup and window launch
- `main()` creates `QApplication`, opens `OpenVisionMainWindow`, and enters event loop.

### 2) Signal wiring
- Buttons/lists are connected to handler methods in `_connect_signals()`.
- Includes double-click handler for replacement color list.

### 3) Batch image loading
- `load_images()` uses a file picker for `png/jpg/jpeg/bmp`.
- Each loaded image is converted to `RGBA` with Pillow.
- Both original and initial modified images are stored.
- Loaded image names are added to the image list.
- First image is auto-selected after initial load.

### 4) Image selection workflow hook
- `on_image_selected()` validates index and updates current selection.
- Calls extraction/list/population/preview pipeline methods.

### 5) Base color picking
- `pick_base_color()` opens `QColorDialog`.
- Stores selected color as RGBA tuple (alpha fixed to 255).
- Updates base color label text.

### 6) Preview rendering
- `refresh_previews()` updates both original/modified preview panes.
- `_set_preview()` converts Pillow image to pixmap and scales to label size.
- `_to_png_bytes()` helper converts Pillow image to PNG bytes.

### 7) Information popup helper
- `_show_info()` displays user messages via `QMessageBox.information`.

## Partially Implemented / Placeholder Behavior
- `change_replacement_color()` currently opens color picker, but does not yet persist mapping updates.
- Several core processing methods intentionally raise `NotImplementedError` and are listed in the TODO document.

## Dependencies Used by Current Implementation
- `PyQt5`
- `Pillow`
- Python standard library (`dataclasses`, `pathlib`, `typing`, `sys`)