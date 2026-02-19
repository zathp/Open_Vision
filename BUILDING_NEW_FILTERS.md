# Building New Filters in Open Vision

This guide explains the current Open Vision pattern for adding a new filter end-to-end.

You will typically touch four areas:

1. `OV_Libs/ImageEditingLib/` (filter logic)
2. `OV_Libs/NodesLib/` (node executor + node factory)
3. `OV_Libs/ProjStoreLib/node_executors.py` (registry wiring)
4. `tests/` (unit tests for filter + node + registry)

---

## Quick Checklist

- Add a focused filter module with typed public functions/classes.
- Add a node module with:
  - `execute_<name>_node(node, inputs)`
  - `create_<name>_node(...)`
- Register node type in `register_default_executors(...)`.
- Export from `OV_Libs/NodesLib/__init__.py`.
- Add tests for normal cases and validation/error cases.

---

## 1) Create the Filter Logic

Create a new file under `OV_Libs/ImageEditingLib/`, for example:

- `OV_Libs/ImageEditingLib/edge_enhance_filter.py`

Keep this layer focused on image operations only (no graph concerns).

### Pattern to Follow

- Validate input image shape/type early.
- Validate parameter ranges early.
- Return a PIL image object.
- Use clear errors (`TypeError` for bad image type, `ValueError` for bad parameters).
- Keep functions deterministic and side-effect free.

### Minimal Example

```python
from typing import Any

from PIL import ImageFilter


def apply_edge_enhance(image: Any, strength: float = 1.0) -> Any:
    """
    Apply edge enhancement to an image.

    Args:
        image: PIL Image
        strength: Blend factor (0.0-5.0)

    Returns:
        Processed PIL Image

    Raises:
        TypeError: If image is not a PIL Image-like object
        ValueError: If strength is out of range
    """
    if not hasattr(image, "filter"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")

    if not (0.0 <= strength <= 5.0):
        raise ValueError(f"strength must be between 0.0 and 5.0, got {strength}")

    # Simple version: run built-in filter once.
    # You can replace with stronger custom behavior later.
    return image.filter(ImageFilter.EDGE_ENHANCE)
```

---

## 2) Add a Node Wrapper

Create `OV_Libs/NodesLib/edge_enhance_node.py`.

This layer translates node dictionaries into calls to your filter function.

### Required Functions

- `execute_edge_enhance_node(node: Dict[str, Any], inputs: List[Any]) -> Any`
- `create_edge_enhance_node(node_id: str, ...) -> Dict[str, Any]`

### Minimal Example

```python
from typing import Any, Dict, List

from OV_Libs.ImageEditingLib.edge_enhance_filter import apply_edge_enhance


def execute_edge_enhance_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    if not inputs or len(inputs) < 1:
        raise ValueError("Edge Enhance node requires image input")

    image = inputs[0]
    if not hasattr(image, "filter") and not hasattr(image, "tobytes"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")

    strength = float(node.get("strength", 1.0))
    return apply_edge_enhance(image, strength)


def create_edge_enhance_node(node_id: str, strength: float = 1.0) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "Edge Enhance",
        "strength": strength,
    }
```

---

## 3) Register the Node Type

Update `OV_Libs/ProjStoreLib/node_executors.py` inside `register_default_executors(...)`.

### Add Import

```python
from OV_Libs.NodesLib.edge_enhance_node import execute_edge_enhance_node
```

### Add Registry Entry

```python
registry.register(
    node_type="Edge Enhance",
    executor=execute_edge_enhance_node,
    description="Enhance image edges",
    input_count=1,
    output_count=1,
    tags=["processing", "filter", "image"],
)
```

---

## 4) Export in Nodes Package

Update `OV_Libs/NodesLib/__init__.py`:

1. Import your new node symbols.
2. Add them to `__all__`.

Example:

```python
from OV_Libs.NodesLib.edge_enhance_node import (
    execute_edge_enhance_node,
    create_edge_enhance_node,
)
```

and add to `__all__`:

```python
"execute_edge_enhance_node",
"create_edge_enhance_node",
```

---

## 5) Add Tests

Create tests in `tests/`:

- `tests/test_edge_enhance_filter.py` (filter-level behavior)
- `tests/test_edge_enhance_node.py` (node execution/factory)

Recommended coverage:

- Valid default execution.
- Custom parameter execution.
- Invalid parameter range raises `ValueError`.
- Invalid input type raises `TypeError`.
- Node input missing raises `ValueError`.
- Registry contains your new node type (via `get_default_registry()`).

---

## 6) Run Validation

Run targeted tests first:

```bash
pytest tests/test_edge_enhance_filter.py tests/test_edge_enhance_node.py
```

Then run full test suite:

```bash
pytest
```

---

## Common Pitfalls

- **Mismatched `node["type"]` string** vs registered `node_type`.
- Forgetting to register in `register_default_executors(...)`.
- Forgetting to export in `OV_Libs/NodesLib/__init__.py`.
- Returning inconsistent output shape (single image vs tuple).
- Skipping parameter validation (causes hard-to-debug runtime errors).

---

## Design Notes for This Codebase

- Keep image math in `ImageEditingLib`; keep graph plumbing in `NodesLib`.
- Prefer explicit defaults in node dictionaries.
- Follow existing exception style and docstring style.
- Use Pillow-compatible image checks like current nodes (`hasattr(image, "filter")`, etc.).

If you follow the pattern above, your filter will integrate cleanly with the pipeline registry and test suite.
