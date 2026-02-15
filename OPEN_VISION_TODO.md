# Open Vision - Prioritized TODO Roadmap

This TODO tracks implementation after the refactor where `open_vision.py` is a project menu with support for two project types:
- **Node Graph Projects (.ovproj)**: Advanced filter stacking and node-based compositing
- **Paint Projects (.ovpaint)**: MS Paint-style direct image editing with Initial_Forms tools

## Priority 0 - Baseline Cleanup (Current State)

- [x] Move image-editing logic out of `open_vision.py` into dedicated files.
- [x] Keep `open_vision.py` focused on project selection/creation and editor launch.
- [x] Add basic `.ovproj` project file creation and listing.
- [ ] Add project type selector to creation dialog (Node Graph vs Paint)
- [ ] Create basic `.ovpaint` project file format and storage
- [ ] Implement `PaintEditorWindow` skeleton class

## Priority 1 - Project Persistence MVP

### Node Graph Projects (.ovproj)

- [ ] Add `.ovproj` schema versioning
  - Add `schema_version` field.
  - Add loader compatibility check for older/newer versions.

- [ ] Persist loaded image paths per project
  - Save image path list whenever project data changes.
  - Restore image list on project open.
  - Handle missing/moved files with a clear warning and skip behavior.

- [ ] Persist filter stack per image
  - Store ordered filter list and parameters for each image.
  - Restore stack into editor state at load time.

- [ ] Persist output presets
  - Save output directory, naming template, and selected format.
  - Restore export defaults when reopening project.

### Paint Projects (.ovpaint)

- [ ] Implement `.ovpaint` file format schema
  - Store canvas dimensions
  - Store layer stack with names, visibility, opacity
  - Store tool settings (last used tool, colors, brush size)
  - Store undo/redo history (optional, may be memory-intensive)

- [ ] Persist canvas and layer data
  - Save each layer as embedded PNG or separate file reference
  - Restore full layer stack on project open
  - Handle missing layer images gracefully

- [ ] Persist tool preferences
  - Save last-used tool and its parameters
  - Save color palette
  - Restore tool state when reopening project

## Priority 2 - Core Editing Features

### Node Graph Projects - Filter Stack MVP (Linear)

- [ ] Implement linear stack model
  - Top-to-bottom execution order only.
  - No branching in MVP.

- [ ] Add stack UI in editor
  - Show current filter order.
  - Add/reorder/remove filter entries.
  - Show active parameters for selected filter.

- [ ] Implement filter runner for stack
  - Execute each filter in order against working image.
  - Recompute preview after stack edits.

- [ ] Implement first stackable filters
  - Include existing Color Replace behavior as stack filter.
  - Add at least one simple utility filter (for example brightness/contrast) for stack validation.

### Paint Projects - Tool Palette MVP

- [ ] Integrate Initial_Forms tools
  - **Downsampler**: Add as tool with size parameter controls
    - Import `downsample_image_hsv()` function
    - Create UI panel with width/height inputs
    - Apply to active layer or selection
  
  - **Mirror**: Add flip transformation options
    - Import `mirror_image()` function
    - Create toolbar buttons for each axis option
    - Apply to active layer or selection
  
  - **Region Selector**: Implement as crop tool
    - Import or recreate selection rectangle logic
    - Add zoom controls to paint editor
    - Support out-of-bounds selection with transparency
    - Crop active layer or create new layer from selection
  
  - **Color Replace**: Add as tool panel
    - Import color matching and replacement logic from Greenscreen2.py
    - Create UI for base color picking and range tolerance
    - Visual preview of affected pixels
    - Replace with transparency or chosen color

- [ ] Implement basic paint tools
  - Brush tool with size and opacity
  - Pencil tool (hard-edge, 100% opacity)
  - Fill bucket with tolerance
  - Eyedropper for color sampling
  - Rectangle/Ellipse selection tools

- [ ] Add tool parameter panel
  - Dynamic parameter UI based on active tool
  - Color picker (foreground/background)
  - Brush size slider
  - Opacity slider
  - Tool-specific options

## Priority 3 - Advanced Features

### Node Graph Projects - Node Graph MVP (Minimal)

- [ ] Define graph data schema
  - Node IDs, typed ports, connections, and parameters.
  - Graph serialization inside `.ovproj`.

- [ ] Implement required nodes
  - Image Input node.
  - Color Replace node.
  - Output node.

- [ ] Implement graph execution pipeline
  - Validate graph connectivity before run.
  - Execute graph to produce output image.

- [ ] Add minimal graph UI
  - Create nodes, connect ports, and run graph.
  - Keep UI minimal (no advanced graph editing tools in MVP).

### Paint Projects - Layer System MVP

- [ ] Implement layer data structure
  - Layer list with PIL Images
  - Layer metadata (name, visibility, opacity)
  - Active layer tracking

- [ ] Add layer management UI
  - Layer list widget with thumbnails
  - Visibility toggle checkboxes
  - Add/Delete layer buttons
  - Layer reordering (drag-drop or up/down buttons)
  - Rename layer functionality

- [ ] Implement layer operations
  - Create new blank layer
  - Create layer from image file
  - Duplicate layer
  - Merge layer down
  - Flatten all visible layers
  - Delete layer with confirmation

- [ ] Add layer compositing
  - Render composite preview from layer stack
  - Apply layer opacity during compositing
  - Update preview on any layer change

- [ ] Implement canvas rendering
  - Composite all visible layers for display
  - Support zoom levels (25%, 50%, 100%, 200%, 400%)
  - Pan controls for scrolling large canvases
  - Grid overlay toggle
  - Transparent background checkerboard pattern

## Priority 4 - Export and Output

### Node Graph Projects - Blender Export MVP

- [ ] Implement Base Color (Albedo) export path
  - Export from stack or graph output.
  - Use predictable naming preset.

- [ ] Add export conflict policy
  - Choose and implement one behavior: overwrite, numeric suffix, or prompt.
  - Keep policy consistent between single and batch export.

### Paint Projects - Export Options

- [ ] Implement single-layer export
  - Export active layer only
  - Export specific layer by selection
  - Preserve transparency

- [ ] Implement composite export
  - Flatten and export all visible layers
  - Option to export at different resolutions
  - Support PNG (with alpha), JPG, BMP formats

- [ ] Add export presets
  - Save export settings (format, quality, path)
  - Quick export to last location
  - Batch export all layers as separate files

## Priority 5 - Reliability and UX

### Both Project Types

- [ ] Replace remaining `NotImplementedError` paths used in UI flow.
- [ ] Add try/except around file IO and image processing with user-facing messages.
- [ ] Add status/progress feedback for long operations.
- [ ] Re-render previews on resize events.
- [ ] Add keyboard shortcuts for common actions.
- [ ] Implement comprehensive error handling and user feedback.

### Paint Editor Specific

- [ ] Implement undo/redo system
  - Command pattern for all edit operations
  - Configurable undo stack depth
  - Visual undo history browser (optional)

- [ ] Add canvas interaction improvements
  - Smooth zoom (mousewheel, pinch gesture)
  - Pan with middle mouse or spacebar+drag
  - Fit to window / Actual size shortcuts
  - Rulers and guides

- [ ] Tool feedback and cursors
  - Custom cursors for each tool showing size/shape
  - Live preview of brush strokes before committing
  - Visual feedback for selection areas

## Deferred / Later Enhancements

### Node Graph Projects

- [ ] Filter enable/disable toggles.
- [ ] Per-filter masks.
- [ ] Additional Blender maps (Normal, Roughness, Metallic, Height, ORM packing).
- [ ] Undo/redo for stack and graph edits.
- [ ] Click-to-pick color directly from preview.

### Paint Projects

- [ ] Advanced brush engine
  - Pressure sensitivity (tablet support)
  - Custom brush shapes and textures
  - Blend modes for brushes
  - Airbrush and spray effects

- [ ] Advanced selection tools
  - Magic wand (color-based selection)
  - Lasso and polygon lasso
  - Selection modification (grow, shrink, feather, invert)
  - Save and load selections

- [ ] Filters and effects
  - Blur, sharpen, noise
  - Color adjustments (hue/saturation, brightness/contrast)
  - Transform tools (rotate, scale, skew)
  - Distortion effects

- [ ] Text tool
  - Add text layers
  - Font selection and sizing
  - Text effects and styling

- [ ] Custom color palette management
  - Save/load custom palettes
  - Recent colors history
  - Palette import/export

- [ ] Animation support
  - Frame-based layer timeline
  - Onion skinning
  - Export as GIF or sprite sheet

### Both Project Types

- [ ] Plugin system for custom tools/filters
- [ ] Scripting support (Python API)
- [ ] Batch processing automation
- [ ] Cloud project storage integration

## MVP Definition of Done

### Node Graph Projects (.ovproj)

- [ ] Opening a `.ovproj` restores image paths, per-image filter stacks, graph data, and output presets.
- [ ] Linear filter stack can be edited and executed end-to-end.
- [ ] Minimal node graph (Input -> Color Replace -> Output) runs and exports.
- [ ] Base Color (Albedo) export works with configured naming/conflict policy.

### Paint Projects (.ovpaint)

- [ ] Opening a `.ovpaint` restores canvas, all layers, and tool settings.
- [ ] All four Initial_Forms tools (Downsampler, Mirror, Region Selector, Color Replace) are integrated and functional.
- [ ] Basic paint tools (brush, pencil, fill, eyedropper) work on active layer.
- [ ] Layer system supports create, delete, reorder, visibility, and opacity.
- [ ] Undo/redo works for all edit operations.
- [ ] Export supports single layer, composite, and batch layer export.
- [ ] Canvas zoom and pan work smoothly with visual feedback.