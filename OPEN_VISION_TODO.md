# Open Vision - Prioritized TODO Roadmap

This TODO tracks implementation after the refactor where `open_vision.py` is a project menu with support for two project types:
- **Node Graph Projects (.ovproj)**: Advanced filter stacking and node-based compositing
- **Paint Projects (.ovpaint)**: MS Paint-style direct image editing with Initial_Forms tools

## Implementation Notes (2026-08)

1. **Linear filter stack vs. node graph**: The node graph pipeline (schema, executors,
   validation, incremental threaded execution, previews) fully supersedes the planned
   per-image linear filter-stack UI. The `filter_stacks` field stays in the `.ovproj`
   schema for backward compatibility, but no parallel linear-stack UI is built. A new
   **Brightness Contrast** node fills the "simple utility stackable filter" slot.
2. **Paint undo/redo** uses bounded snapshot stacks (configurable depth, default 30)
   covering every destructive edit operation. A formal command-pattern refactor and the
   optional history browser are deferred.
3. **Output naming robustness**: `strftime` directives in Output-node name templates are
   validated explicitly (`_validate_strftime_format`) because glibc silently passes
   invalid directives through while Windows raises.
4. Still open (tracked below): ellipse selection, layer-list thumbnails and drag-drop
   reorder, rulers/guides, custom tool cursors, export quality/resolution presets,
   and the Priority 5+ enhancement backlog.

## Priority 0 - Baseline Cleanup (Current State)

- [x] Move image-editing logic out of `open_vision.py` into dedicated files.
- [x] Keep `open_vision.py` focused on project selection/creation and editor launch.
- [x] Add basic `.ovproj` project file creation and listing.
- [x] Add project type selector to creation dialog (Node Graph vs Paint)
- [x] Create basic `.ovpaint` project file format and storage
- [x] Implement `PaintEditorWindow` skeleton class

## Priority 1 - Project Persistence MVP

### Node Graph Projects (.ovproj)

- [x] Add `.ovproj` schema versioning
  - Add `schema_version` field.
  - Add loader compatibility check for older/newer versions (`check_schema_version`,
    editor surfaces upgrade/unsupported warnings).

- [x] Persist loaded image paths per project
  - Save image path list whenever project data changes (Image Import node properties
    are part of the graph payload saved on close/save).
  - Restore image list on project open.
  - Handle missing/moved files with a clear warning and skip behavior
    (`filter_missing_image_paths` + load-time dialog).

- [ ] Persist filter stack per image *(superseded by node graph pipeline - see Notes)*
  - Store ordered filter list and parameters for each image.
  - Restore stack into editor state at load time.

- [x] Persist output presets
  - Save output directory, naming template, and selected format.
    (`_persist_output_presets` captures Output node settings on save.)
  - Restore export defaults when reopening project (new Output nodes are seeded
    from stored presets).

### Paint Projects (.ovpaint)

- [x] Implement `.ovpaint` file format schema
  - Store canvas dimensions
  - Store layer stack with names, visibility, opacity
  - Store tool settings (last used tool, colors, brush size)
  - Store undo/redo history (optional, may be memory-intensive) - *not stored;
    snapshots are session-scoped*

- [x] Persist canvas and layer data
  - Save each layer as embedded PNG or separate file reference (sidecar
    `<project>_layers/<layer_id>.png`)
  - Restore full layer stack on project open
  - Handle missing layer images gracefully (skipped with metadata intact)

- [x] Persist tool preferences
  - Save last-used tool and its parameters
  - Save color palette (foreground/background colors)
  - Restore tool state when reopening project

## Priority 2 - Core Editing Features

### Node Graph Projects - Filter Stack MVP (Linear)

- [ ] Implement linear stack model *(superseded - see Notes)*
  - Top-to-bottom execution order only.
  - No branching in MVP.

- [ ] Add stack UI in editor *(superseded - see Notes)*
  - Show current filter order.
  - Add/reorder/remove filter entries.
  - Show active parameters for selected filter.

- [ ] Implement filter runner for stack *(superseded by pipeline runner)*
  - Execute each filter in order against working image.
  - Recompute preview after stack edits.

- [x] Implement first stackable filters *(as graph nodes)*
  - Include existing Color Replace behavior as stack filter (existing Color Shift node).
  - Add at least one simple utility filter for stack validation
    (**Brightness Contrast** node + filter library).

### Paint Projects - Tool Palette MVP

- [x] Integrate Initial_Forms tools
  - **Downsampler**: tool panel with width/height inputs, applied to active layer
    (`OV_Libs/Initial_Forms/integration.py: downsample_image`, parity-tested against
    the legacy function).
  - **Mirror**: four flip operations (H, V, both diagonals) on active layer.
  - **Region Selector**: crop tool with drag-selection, crop-to-selection,
    new-layer-from-selection, out-of-bounds transparency support.
  - **Color Replace**: panel with base color picking, distance/range/HSV modes,
    tolerance, affected-pixel preview count, replace with color or transparency.

- [x] Implement basic paint tools *(rectangle selection; ellipse pending)*
  - Brush tool with size and opacity
  - Pencil tool (hard-edge, 100% opacity)
  - Fill bucket with tolerance
  - Eyedropper for color sampling
  - Rectangle/Ellipse selection tools *(rectangle done; ellipse pending)*

- [x] Add tool parameter panel
  - Dynamic parameter UI based on active tool
  - Color picker (foreground/background, alpha-aware foreground)
  - Brush size slider
  - Opacity slider
  - Tool-specific options (fill tolerance)

## Priority 3 - Advanced Features

### Node Graph Projects - Node Graph MVP (Minimal)

- [x] Define graph data schema
  - Node IDs, typed ports, connections, and parameters.
  - Graph serialization inside `.ovproj`.

- [x] Implement required nodes
  - Image Input node (Image Import).
  - Color Replace node (Color Shift).
  - Output node.

- [x] Implement graph execution pipeline
  - Validate graph connectivity before run.
  - Execute graph to produce output image (threaded, incremental updates).

- [x] Add minimal graph UI
  - Create nodes, connect ports, and run graph.
  - Keep UI minimal (no advanced graph editing tools in MVP).

### Paint Projects - Layer System MVP

- [x] Implement layer data structure
  - Layer list with PIL Images
  - Layer metadata (name, visibility, opacity)
  - Active layer tracking

- [x] Add layer management UI *(thumbnails and drag-drop pending; up/down reorder done)*
  - Layer list widget with thumbnails *(pending)*
  - Visibility toggle checkboxes
  - Add/Delete layer buttons
  - Layer reordering (drag-drop or up/down buttons) *(up/down buttons)*
  - Rename layer functionality

- [x] Implement layer operations
  - Create new blank layer
  - Create layer from image file
  - Duplicate layer
  - Merge layer down
  - Flatten all visible layers
  - Delete layer with confirmation

- [x] Add layer compositing
  - Render composite preview from layer stack
  - Apply layer opacity during compositing
  - Update preview on any layer change

- [x] Implement canvas rendering
  - Composite all visible layers for display
  - Support zoom levels (25%, 50%, 100%, 200%, 400%)
  - Pan controls for scrolling large canvases (scrollbars + middle-mouse drag)
  - Grid overlay toggle
  - Transparent background checkerboard pattern

## Priority 4 - Export and Output

### Node Graph Projects - Blender Export MVP

- [x] Implement Base Color (Albedo) export path
  - Export from stack or graph output (runs pipeline, exports each Output node
    result via "Export Base Color Maps...").
  - Use predictable naming preset (`{project_name}_BaseColor` template).

- [x] Add export conflict policy
  - Choose and implement one behavior: overwrite, numeric suffix, or prompt.
    (All three implemented in `OV_Libs/ExportLib/blender_export.py`; editor uses
    prompt policy, batch layer export uses numeric suffix.)
  - Keep policy consistent between single and batch export.

### Paint Projects - Export Options

- [x] Implement single-layer export
  - Export active layer only
  - Export specific layer by selection
  - Preserve transparency

- [x] Implement composite export
  - Flatten and export all visible layers
  - Option to export at different resolutions *(pending)*
  - Support PNG (with alpha), JPG, BMP formats

- [ ] Add export presets
  - Save export settings (format, quality, path) *(path remembered; format/quality pending)*
  - Quick export to last location
  - Batch export all layers as separate files

## Priority 5 - Reliability and UX

### Both Project Types

- [x] Replace remaining `NotImplementedError` paths used in flow.
- [x] Add try/except around file IO and processing with user-facing messages
  (editor-facing IO paths wrapped; deeper hardening continues opportunistically).
- [x] Add status/progress feedback for long operations (status bar messages).
- [x] Re-render previews on resize events (Qt repaint handles this; previews derive
  from live composited state).
- [x] Add keyboard shortcuts for common actions
  (paint: B/P/E/F/I/S tools, `[`/`]` size, +/- zoom, Ctrl+S/Z/Y; node editor retains its own set).
- [x] Implement comprehensive error handling and user feedback.

### Paint Editor Specific

- [x] Implement undo/redo system
  - Command pattern for all edit operations *(bounded snapshot stacks - see Notes)*
  - Configurable undo stack depth (`UNDO_DEPTH`)
  - Visual undo history browser (optional) - *deferred*

- [ ] Add canvas interaction improvements
  - Smooth zoom (mousewheel done via Ctrl+wheel, pinch gesture pending)
  - Pan with middle mouse or spacebar+drag (middle mouse done; spacebar pending)
  - Fit to window / Actual size shortcuts
  - Rulers and guides *(pending)*

- [ ] Tool feedback and cursors
  - Custom cursors for each tool showing size/shape *(pending)*
  - Live preview of brush strokes before committing (strokes commit incrementally)
  - Visual feedback for selection areas (dashed overlay)

## Deferred / Later Enhancements

### Node Graph Projects

- [ ] Filter enable/disable toggles.
- [ ] Per-filter masks.
- [ ] Additional Blender maps (Normal, Roughness, Metallic, Height, ORM packing).
- [ ] Undo/redo for stack and graph edits. *(graph edits already have undo/redo)*
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
  - Color adjustments (hue/saturation, brightness/contrast) *(available via tools/nodes)*
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

- [x] Opening a `.ovproj` restores image paths, per-image filter stacks, graph data, and output presets. *(image paths, graph data, and presets restored; legacy `filter_stacks` field preserved but unused - see Notes)*
- [x] Minimal node graph (Input -> Color Replace -> Output) runs and exports.
- [x] Base Color (Albedo) export works with configured naming/conflict policy.
- [ ] Linear filter stack can be edited and executed end-to-end. *(superseded by node graph - see Notes)*

### Paint Projects (.ovpaint)

- [x] Opening a `.ovpaint` restores canvas, all layers, and tool settings.
- [x] All four Initial_Forms tools (Downsampler, Mirror, Region Selector, Color Replace) are integrated and functional.
- [x] Basic paint tools (brush, pencil, fill, eyedropper) work on active layer.
- [x] Layer system supports create, delete, reorder, visibility, and opacity.
- [x] Undo/redo works for all edit operations.
- [x] Export supports single layer, composite, and batch layer export.
- [x] Canvas zoom and pan work smoothly with visual feedback.
