# Open Vision - Prioritized TODO Roadmap

This TODO tracks implementation after the refactor where `open_vision.py` is a project menu and image-editing lives in separate modules.

## Priority 0 - Baseline Cleanup (Current State)

- [x] Move image-editing logic out of `open_vision.py` into dedicated files.
- [x] Keep `open_vision.py` focused on project selection/creation and editor launch.
- [x] Add basic `.ovproj` project file creation and listing.

## Priority 1 - Project Persistence MVP

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

## Priority 2 - Filter Stack MVP (Linear)

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

## Priority 3 - Node Graph MVP (Minimal)

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

## Priority 4 - Blender Export MVP

- [ ] Implement Base Color (Albedo) export path
  - Export from stack or graph output.
  - Use predictable naming preset.

- [ ] Add export conflict policy
  - Choose and implement one behavior: overwrite, numeric suffix, or prompt.
  - Keep policy consistent between single and batch export.

## Priority 5 - Reliability and UX

- [ ] Replace remaining `NotImplementedError` paths used in UI flow.
- [ ] Add try/except around file IO and image processing with user-facing messages.
- [ ] Add status/progress feedback for long operations.
- [ ] Re-render previews on resize events.

## Deferred / Later Enhancements

- [ ] Filter enable/disable toggles.
- [ ] Per-filter masks.
- [ ] Additional Blender maps (Normal, Roughness, Metallic, Height, ORM packing).
- [ ] Undo/redo for stack and graph edits.
- [ ] Click-to-pick color directly from preview.

## MVP Definition of Done

- [ ] Opening a `.ovproj` restores image paths, per-image filter stacks, graph data, and output presets.
- [ ] Linear filter stack can be edited and executed end-to-end.
- [ ] Minimal node graph (Input -> Color Replace -> Output) runs and exports.
- [ ] Base Color (Albedo) export works with configured naming/conflict policy.