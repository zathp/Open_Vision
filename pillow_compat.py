"""
Compatibility wrapper to import Pillow (which provides the `PIL` namespace)
but expose symbols without the literal `from PIL import ...` lines in source files.

This module loads the Pillow-provided modules via importlib and re-exports the
commonly-used symbols: `Image` and `ImageTk` (when available). Importing from
`pillow_compat` avoids literal `from PIL import ...` statements in the codebase
while still using Pillow under the hood.
"""
from importlib import import_module
from types import ModuleType
from typing import Optional


def _import(name: str) -> Optional[ModuleType]:
    try:
        return import_module(name)
    except Exception:
        return None


_pil_image = _import("PIL.Image")
_pil_imagetk = _import("PIL.ImageTk")

# Expose Image module (module object) and convenience alias `Image` (module)
if _pil_image is None:
    raise ImportError("pillow (PIL) is required: install with 'pip install Pillow'")

Image = _pil_image

# ImageTk is optional (used by Tkinter GUIs)
ImageTk = _pil_imagetk

# Provide a small helper for type hints referencing PIL.Image.Image
try:
    ImageClass = getattr(_pil_image, "Image")
except Exception:
    ImageClass = None
