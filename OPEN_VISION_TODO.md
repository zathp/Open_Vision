# Open Vision (PyQt5) - TODO Tasks

This TODO list tracks the remaining implementation work for `open_vision.py`.

## Priority 1 - Core Functionality (Make Tool Usable)

- [ ] Update to `Pillow` lib
  - Replace legacy PIL wording with Pillow package usage.
  - Use `pip install pillow` for dependency management.
  - Note: Pillow imports still use the `PIL` namespace (for example: `from PIL import Image`).

- [ ] Convert image-processing functions to Pillow APIs
  - Ensure all image open/convert/save and pixel-processing paths rely on Pillow.
  - Remove remaining references that describe the project as using legacy PIL.

- [ ] Implement `extract_unique_colors()`
  - Read current image pixels.
  - Build unique RGBA color list.
  - Initialize missing entries in `color_mappings`.

- [ ] Implement `populate_color_lists()`
  - Fill original/replacement list widgets from `unique_colors`.
  - Show color tuples and optional hex preview text.
  - Keep list index aligned with `unique_colors`.

- [ ] Complete `change_replacement_color()` mapping write-back
  - Resolve selected color index.
  - Keep original alpha channel or selected alpha rule.
  - Update `color_mappings` and refresh replacement list entry.

- [ ] Implement `apply_to_current()`
  - Apply `color_mappings` over current original image.
  - Write result into current image `modified`.
  - Refresh modified preview.

- [ ] Implement `save_current()`
  - Save dialog for single image output path.
  - Export current modified image.

## Priority 2 - Batch Workflow

- [ ] Implement `apply_to_all()`
  - Apply mappings to every loaded image.
  - Update each `modified` image in memory.

- [ ] Implement `save_all()`
  - Select output directory.
  - Save each modified image with safe naming strategy.
  - Report summary of saved files and failures.

## Priority 3 - Selection / Editing Tools

- [ ] Implement `select_by_range()`
  - Add RGB or HSV tolerance checks against `base_color`.
  - Select matching color entries in list widgets.

- [ ] Implement `apply_hsv_to_selected()`
  - Read selected replacement entries.
  - Apply HSV shift/scale rules.
  - Write updated colors to mapping/list.

- [ ] Implement `apply_hsv_to_all()`
  - Bulk HSV operation over all mapped replacement colors.

## Priority 4 - UX / Robustness

- [ ] Add input validation and user-safe error handling
  - Empty image list protection.
  - Missing selection handling.
  - Try/except around file IO and Pillow operations.

- [ ] Add status/progress feedback
  - Status bar text for long operations.
  - Success/failure counts for batch apply/save.

- [ ] Improve preview behavior
  - Re-render preview pixmaps on window resize.

- [ ] Clean up unused code paths in `_set_preview()`
  - Remove unused variables (`width`, `height`, `raw`) or use a direct conversion path.

## Optional Enhancements

- [ ] Support click-to-pick color directly from preview image.
- [ ] Persist/load mapping presets as JSON.
- [ ] Add undo/redo for mapping changes.
- [ ] Add alpha-aware editing options.
- [ ] Add drag-and-drop image loading.

## Definition of Done (MVP)

- [ ] User can load one or more images.
- [ ] User can edit replacement colors.
- [ ] User can apply replacements to current/all images.
- [ ] User can save current/all modified outputs.
- [ ] No `NotImplementedError` paths remain in normal UI flow.