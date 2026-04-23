# Multi-Layer Parameter Editor - Quick Reference

## What's New

The Image Layer node's "layers" parameter now uses a visual editor instead of raw JSON.

## Files Changed/Added

| File | Type | Purpose |
|------|------|---------|
| `layer_editor.py` | NEW | Main layer editor UI widget (292 lines) |
| `node_editor_window.py` | MODIFIED | Integrated layer editor (+30 lines) |
| `LAYER_EDITOR_IMPROVEMENTS.md` | DOC | Technical implementation guide |
| `LAYER_EDITOR_UX_DESIGN.md` | DOC | UX design and reasoning |
| `LAYER_EDITOR_VISUAL_GUIDE.md` | DOC | Visual before/after and workflows |
| `LAYER_EDITOR_IMPLEMENTATION.md` | DOC | Implementation summary |
| `demo_layer_editor.py` | DEMO | Standalone demo of the editor |

## Key Improvements

### Visual Layer Overview
- **Table view** shows all layers with index, image path, alpha, blend amount
- **Scrollable** for projects with many layers
- **Row highlighting** shows which layer is selected for editing

### Layer Management
- **[Add Layer]** - Create new layer with sensible defaults
- **[Remove]** - Delete selected layer (won't delete last layer)
- **[Move Up]** - Raise layer in rendering order
- **[Move Down]** - Lower layer in rendering order

### Properties Editor
- **Image Path** - Text display + [Browse...] button (no typing needed)
- **Alpha** - Slider (0-255) + Spinbox with validation
- **Blend Amount** - Slider (0-100%) + Spinbox (0.0-1.0)

### Quality Features
- ✓ Synchronized slider/spinbox controls (move one, updates the other)
- ✓ Live table updates when properties change
- ✓ File picker validation for image paths
- ✓ Range validation on numeric inputs
- ✓ Safety checks (can't remove last layer)

## How to Use

### Adding Layers
1. Click **[Add Layer]** button
2. New row appears in table (auto-selected)
3. Properties panel shows controls for new layer
4. Click **[Browse...]** to select image file
5. Adjust **Alpha** and **Blend** sliders as needed
6. Repeat for additional layers

### Editing Existing Layers
1. Click on layer row in table to select it
2. Edit properties in panel below:
   - Change image path: click **[Browse...]**
   - Adjust alpha: move slider or type value in spinbox
   - Adjust blend: move slider or type value in spinbox
3. Changes appear immediately in table

### Reordering Layers
1. Select layer by clicking its row
2. Click **[Move Up]** or **[Move Down]**
3. Layer position updates in table
4. All properties preserved during move

### Removing Layers
1. Select layer by clicking its row
2. Click **[Remove]** button
3. Layer deleted (button disabled if only one layer remains)

### Saving Changes
1. Make all edits using controls above
2. Click **[OK]** to save and close dialog
3. Node is updated with new layer configuration

## Data Format

Internal format compatible with Image Layer node:

```python
[
    {
        "image_path": "/path/to/layer1.png",
        "alpha": 255,           # 0-255 opacity
        "blend_amount": 1.0,    # 0.0-1.0 contribution
        "mask": None            # Reserved for future use
    },
    {
        "image_path": "/path/to/layer2.png",
        "alpha": 200,
        "blend_amount": 0.8,
        "mask": None
    }
]
```

## FAQ

**Q: Why two controls for alpha/blend?**  
A: Slider for intuitive visual adjustment, spinbox for precise numeric entry. They're synchronized—move either one and the other updates automatically.

**Q: What's the difference between alpha and blend?**  
A: Alpha = how transparent the layer is. Blend = how much it affects the final result. Usually used together.

**Q: Can I have just one layer?**  
A: Yes, and you can edit it. But you can't remove the last layer—at least one must exist.

**Q: What if I don't select an image path?**  
A: The layer will have an empty path, which will cause an error during execution. Always browse for an image file.

**Q: Can I drag layers to reorder?**  
A: Currently use [Move Up]/[Move Down] buttons. Drag-drop may be added in future version.

**Q: Does it save as JSON?**  
A: Yes! Data is saved in the same JSON format as before. The editor just provides a better UI for creating/editing the JSON.

**Q: What about masks?**  
A: Mask support will be added in a future update. Currently reserved but not editable.

**Q: Can I import/export layers?**  
A: Currently only through the projects file. Direct import/export may be added later.

**Q: Is this backward compatible?**  
A: 100% - existing projects with layer data load without any changes.

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Tab through controls | Tab / Shift+Tab |
| Move between table rows | Up / Down arrows |
| Activate button | Space / Enter |
| Open file picker | Alt+B (when Browse button focused) |

## Control Ranges

| Parameter | Min | Max | Unit | Default |
|-----------|-----|-----|------|---------|
| Alpha | 0 | 255 | 8-bit value | 255 |
| Blend | 0.0 | 1.0 | Decimal | 1.0 |
| Blend (slider) | 0 | 100 | Percent | 100 |

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Can't remove layer | Need at least one layer; can't delete the last one |
| Image path not showing | Click [Browse...] to select file |
| Slider and spinbox out of sync | They're synced; click OK to save and refresh |
| Changes disappeared | Click [OK] to save; Cancel discards edits |
| File picker not opening | Check file permissions; try different directory |
| Spinbox value rejected | Ensure value is within valid range |

## Performance Notes

- **Normal usage** (< 20 layers): No performance issues
- **Large projects** (> 100 layers): Table scrollable, no lag
- **Memory usage**: Minimal (one copy of layer data in widget)

## Future Enhancements

- Mask image selection UI
- Drag-drop layer reordering
- Inline image thumbnails
- Layer visibility toggles
- Blend mode selection
- Layer naming/annotations
- Duplicate layer shortcut

## Getting Help

Refer to:
1. **LAYER_EDITOR_IMPROVEMENTS.md** - Technical details
2. **LAYER_EDITOR_UX_DESIGN.md** - Design reasoning
3. **LAYER_EDITOR_VISUAL_GUIDE.md** - Visual examples and workflows
4. **demo_layer_editor.py** - Working example to study

## Demo

Run the standalone demo to explore the editor:

```bash
python demo_layer_editor.py
```

The demo:
- Shows a sample project with 3 layers
- Lets you add/remove/edit/reorder layers
- Has a "Print Layers" button to inspect data
- Works without needing a full project

## Support

For questions or issues:
1. Check the documentation files listed above
2. Review the code comments in `layer_editor.py`
3. Run the demo to see expected behavior
4. Check `test_*.py` files for usage examples (when available)
