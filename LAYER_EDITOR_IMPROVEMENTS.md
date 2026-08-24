# Multi-Layer Parameter Editor - Improvements Guide

## Overview

The multi-layer parameter editor has been enhanced to provide a more intuitive and user-friendly interface for editing Image Layer node parameters. Previously, layers were edited as raw JSON text through a plain text editor, which was error-prone and not user-friendly.

## New Features

### 1. **Visual Layer Stack Widget**
The new `LayerListWidget` (in `layer_editor.py`) provides a comprehensive visual representation of all layers with:
- Clear table display showing layer index, image path, alpha, and blend amount
- Easy at-a-glance view of all layer properties
- Organized scrollable list for projects with many layers

### 2. **Intuitive Layer Controls**

#### Add Layers
- **"Add Layer" button** - Creates a new layer with default properties:
  - `alpha`: 255 (fully opaque)
  - `blend_amount`: 1.0 (full contribution)
  - `image_path`: empty (awaiting user selection)

#### Remove Layers
- **"Remove Layer" button** - Removes selected layer
- Safety check prevents removing the last layer

#### Reorder Layers
- **"Move Up" button** - Moves selected layer up in the stack
- **"Move Down" button** - Moves selected layer down in the stack
- Immediate visual feedback with table updates

### 3. **Per-Layer Properties Panel**

When a layer is selected, a dedicated properties panel appears showing:

#### Image Path
- Read-only display of current layer image path
- **"Browse..." button** - Opens file picker to select/change the layer image
- Inline editing with automatic table update

#### Alpha (Opacity)
- **Synchronized slider** (0-255) and spinbox controls
- Real-time bidirectional sync - changing one updates the other
- Visual feedback with percentage/255 display
- Values: 0 = fully transparent, 255 = fully opaque

#### Blend Amount  
- **Synchronized slider** (0-100%) and double spinbox (0.0-1.0) controls
- Real-time bidirectional sync
- Controls layer contribution: 0.0 = invisible, 1.0 = full contribution
- More intuitive than raw decimal values

### 4. **Image File Selection**

Two ways to select layer images:

1. **Browse column in table** - Small "Browse" button next to each layer
2. **Browse in properties** - "Browse..." button when layer is selected

Both use the same file picker dialog with image format filtering:
- Supports: PNG, JPG, JPEG, BMP, TIFF, WEBP, GIF
- File paths are validated on selection

### 5. **Layer State Persistence**

All edits are preserved in the layer widget's internal state:
- Selecting different layers saves previous edits automatically
- Reordering preserves all layer properties
- Adding/removing updates the affected rows
- Final state is only committed when "OK" is clicked in the main dialog

## Usage Workflow

### Adding Layers
1. Click "Add Layer" button
2. Select the new layer (last in list)
3. Click "Browse..." to choose an image
4. Adjust Alpha and Blend Amount as needed
5. Repeat for additional layers

### Editing Existing Layers
1. Click on layer row in the table to select it
2. Properties panel updates with selected layer's values
3. Modify image path, alpha, or blend amount
4. Changes are immediately reflected in the table
5. Click "OK" to save changes

### Reordering Layers
1. Select layer to move
2. Click "Move Up" or "Move Down"
3. Layer order updates in the table
4. Affects compositing order (top of list = topmost in composition)

### Removing Layers
1. Select layer to remove
2. Click "Remove Layer"
3. Cannot remove if it's the only layer (safety check)

## Technical Implementation

### File: `layer_editor.py`

**Main Class: `LayerListWidget`**

Provides the complete layer editing UI:
- `__init__(layers_data, parent)` - Initialize with layer list
- `_init_ui()` - Build the UI components
- `_populate_table()` - Display layers in table
- `_create_properties_panel()` - Build editable properties widget
- `_on_layer_selected()` - Update panel when row selected
- `_on_alpha_changed()`, `_on_blend_changed()` - Handle slider updates
- `_on_alpha_spin_changed()`, `_on_blend_spin_changed()` - Handle spinbox updates
- `_update_selected_layer()` - Save edits back to internal state
- `_browse_image()`, `_browse_current_layer_image()` - File selection
- `_add_layer()`, `_remove_layer()` - Layer management
- `_move_layer_up()`, `_move_layer_down()` - Reordering
- `get_layers_data()` - Return edited layer list

### File: `node_editor_window.py` (Modified)

**Changes to `NodeParameterEditorDialog`:**

1. **Import statement** (line ~52):
   ```python
   from layer_editor import LayerListWidget
   ```

2. **New method** `_create_layer_list_editor()` (adds specialized editor):
   - Detects "layers" parameter in Image Layer node
   - Creates LayerListWidget instance
   - Returns widget + getter function for parameter collection
   - Getter converts internal state back to Image Layer node format

3. **Updated** `_create_editor_widget()` method (line ~250):
   - Added check for Image Layer node's "layers" parameter
   - Routes to new `_create_layer_list_editor()` before generic JSON handler

## Data Format

Internal layer format preserved for compatibility:
```python
{
    "image_path": "/path/to/layer.png",
    "mask": None,  # Future use
    "alpha": 255,  # 0-255 opacity
    "blend_amount": 1.0  # 0.0-1.0 contribution
}
```

The editor normalizes values:
- Ensures `alpha` is int (0-255)
- Ensures `blend_amount` is float (0.0-1.0)
- Handles missing fields with sensible defaults

## UX Improvements Over Previous Implementation

| Aspect | Before | After |
|--------|--------|-------|
| **Viewing layers** | Raw JSON text only | Visual table with summaries |
| **Adding layers** | Manual JSON syntax error-prone | Single button click |
| **Adjusting opacity** | Edit numeric value in JSON | Slider + spinbox with validation |
| **Setting blend** | Edit decimal in JSON | Percentage slider or 0.0-1.0 spinbox |
| **Reordering** | Manual array index manipulation | Up/Down buttons |
| **File selection** | Copy/paste path as string | File picker dialog |
| **Error feedback** | JSON parse errors | Inline validation |
| **Layer count** | Hard to see at a glance | Clear row numbering |

## Future Enhancement Opportunities

1. **Mask Support** - Add UI for selecting mask images per layer
2. **Alpha Preview** - Show semi-transparent preview in table
3. **Drag-Drop Reordering** - Allow dragging rows to reorder
4. **Blend Mode Selection** - Add dropdown for future blend modes
5. **Layer Naming** - Allow custom layer names for clarity
6. **Thumbnail Previews** - Display mini image thumbnails in table
7. **Layer Visibility Toggle** - Eye icon to temporarily hide layers
8. **Default Values** - Quick set buttons for common alpha/blend values
9. **Copy/Duplicate** - Duplicate layer with all properties
10. **Import from Clipboard** - Paste layer data from other sources

## Testing

To test the new layer editor:

1. Open a project with Image Layer node or create one
2. Edit the Image Layer node's parameters
3. The "Layers" field will now show the new widget instead of JSON
4. Add, remove, and reorder layers
5. Verify edits are saved on dialog close
6. Check that final node properties contain correct layer data

## Backward Compatibility

✅ **Fully backward compatible** - Existing projects with layer data will work seamlessly:
- Import old JSON layer format
- Convert to internal state
- Export back to same format
- No data loss or migration needed
