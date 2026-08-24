"""Paint project layer system.

Pure PIL data structures and compositing for .ovpaint projects.
No Qt imports - UI layers consume this module.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from OV_Libs.ProjStoreLib.project_store import (
    get_paint_layers_dir,
    load_paint_project_data,
    save_paint_project_data,
)


class PaintLayerStackError(RuntimeError):
    """Raised for invalid layer operations (unknown ids, empty stacks)."""


def _scale_alpha(image: Image.Image, opacity: int) -> Image.Image:
    if opacity >= 255:
        return image
    r, g, b, a = image.split()
    lut = [int(value * (opacity / 255.0)) for value in range(256)]
    return Image.merge("RGBA", (r, g, b, a.point(lut)))


class PaintLayer:
    """A single RGBA layer with display metadata."""

    def __init__(
        self,
        name: str,
        image: Optional[Image.Image] = None,
        visible: bool = True,
        opacity: int = 255,
        layer_id: Optional[str] = None,
        canvas_size: Optional[tuple] = None,
    ) -> None:
        self.id = layer_id or str(uuid.uuid4())
        self.name = name
        self.visible = visible
        self.opacity = max(0, min(255, int(opacity)))
        if image is not None:
            self.image = image.convert("RGBA")
            if canvas_size is not None and self.image.size != tuple(canvas_size):
                canvas = Image.new("RGBA", tuple(canvas_size), (0, 0, 0, 0))
                canvas.paste(self.image, (0, 0))
                self.image = canvas
        elif canvas_size is not None:
            self.image = Image.new("RGBA", tuple(canvas_size), (0, 0, 0, 0))
        else:
            raise ValueError("PaintLayer needs an image or a canvas_size")

    @property
    def effective_opacity(self) -> int:
        return self.opacity if self.visible else 0


class PaintLayerStack:
    """Ordered layer collection with compositing and canvas management."""

    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError(f"Canvas must be positive, got {width}x{height}")
        self.canvas_width = int(width)
        self.canvas_height = int(height)
        self.layers: List[PaintLayer] = []
        self.active_id: Optional[str] = None

    # -- queries ------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        return not self.layers

    def get_layer(self, layer_id: Optional[str]) -> Optional[PaintLayer]:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def require_layer(self, layer_id: Optional[str]) -> PaintLayer:
        layer = self.get_layer(layer_id)
        if layer is None:
            raise PaintLayerStackError(f"Unknown layer id: {layer_id}")
        return layer

    def get_active(self) -> Optional[PaintLayer]:
        return self.get_layer(self.active_id)

    def index_of(self, layer_id: str) -> int:
        for index, layer in enumerate(self.layers):
            if layer.id == layer_id:
                return index
        raise PaintLayerStackError(f"Unknown layer id: {layer_id}")

    def composite(self) -> Image.Image:
        """Composite visible layers bottom-to-top honoring opacity."""
        result = Image.new("RGBA", (self.canvas_width, self.canvas_height), (0, 0, 0, 0))
        for layer in self.layers:
            if not layer.visible or layer.opacity <= 0:
                continue
            result = Image.alpha_composite(result, _scale_alpha(layer.image, layer.opacity))
        return result

    # -- mutations ----------------------------------------------------------

    def _fit_to_canvas(self, image: Image.Image) -> Image.Image:
        if image.size == (self.canvas_width, self.canvas_height):
            return image.convert("RGBA")
        canvas = Image.new("RGBA", (self.canvas_width, self.canvas_height), (0, 0, 0, 0))
        canvas.paste(image.convert("RGBA"), (0, 0))
        return canvas

    def add_blank_layer(self, name: Optional[str] = None) -> PaintLayer:
        layer = PaintLayer(
            name=name or f"Layer {len(self.layers) + 1}",
            canvas_size=(self.canvas_width, self.canvas_height),
        )
        return self._append(layer)

    def add_image_layer(self, image: Image.Image, name: str = "Image") -> PaintLayer:
        layer = PaintLayer(
            name=name,
            image=self._fit_to_canvas(image),
            canvas_size=(self.canvas_width, self.canvas_height),
        )
        return self._append(layer)

    def _append(self, layer: PaintLayer) -> PaintLayer:
        self.layers.append(layer)
        self.active_id = layer.id
        return layer

    def duplicate_layer(self, layer_id: str) -> PaintLayer:
        source = self.require_layer(layer_id)
        copy = PaintLayer(
            name=f"{source.name} copy",
            image=source.image.copy(),
            visible=source.visible,
            opacity=source.opacity,
        )
        self.layers.insert(self.index_of(layer_id) + 1, copy)
        self.active_id = copy.id
        return copy

    def delete_layer(self, layer_id: str) -> None:
        index = self.index_of(layer_id)
        del self.layers[index]
        if self.active_id == layer_id:
            neighbor = self.layers[min(index, len(self.layers) - 1)] if self.layers else None
            self.active_id = neighbor.id if neighbor else None

    def merge_down(self, layer_id: str) -> PaintLayer:
        index = self.index_of(layer_id)
        if index == 0:
            raise PaintLayerStackError("Cannot merge bottom layer down")
        upper = self.layers[index]
        lower = self.layers[index - 1]
        merged_rgb = Image.alpha_composite(
            _scale_alpha(lower.image, lower.effective_opacity),
            _scale_alpha(upper.image, upper.effective_opacity),
        )
        merged = PaintLayer(
            name=lower.name,
            image=merged_rgb,
            visible=True,
            opacity=255,
            canvas_size=(self.canvas_width, self.canvas_height),
        )
        self.layers[index - 1] = merged
        del self.layers[index]
        self.active_id = merged.id
        return merged

    def flatten_visible(self) -> PaintLayer:
        flattened = PaintLayer(
            name="Flattened",
            image=self.composite(),
            canvas_size=(self.canvas_width, self.canvas_height),
        )
        self.layers = [flattened]
        self.active_id = flattened.id
        return flattened

    def move_layer(self, layer_id: str, offset: int) -> None:
        index = self.index_of(layer_id)
        target = max(0, min(len(self.layers) - 1, index + int(offset)))
        if target == index:
            return
        self.layers[index], self.layers[target] = self.layers[target], self.layers[index]

    def set_active(self, layer_id: str) -> None:
        self.require_layer(layer_id)
        self.active_id = layer_id

    def replace_layer_image(self, layer_id: str, image: Image.Image) -> None:
        self.require_layer(layer_id).image = self._fit_to_canvas(image)

    def resize_canvas(self, width: int, height: int, anchor: str = "top_left") -> None:
        """Resize the canvas, keeping layer content anchored per ``anchor``."""
        width, height = int(width), int(height)
        if width < 1 or height < 1:
            raise ValueError(f"Canvas must be positive, got {width}x{height}")
        if anchor not in ("top_left", "center"):
            raise ValueError(f"Unsupported anchor: {anchor}")

        resized: List[PaintLayer] = []
        for layer in self.layers:
            canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            paste_x = paste_y = 0
            if anchor == "center":
                paste_x = max(0, (width - layer.image.width) // 2)
                paste_y = max(0, (height - layer.image.height) // 2)
            canvas.paste(layer.image, (paste_x, paste_y))
            resized.append(canvas)

        self.canvas_width, self.canvas_height = width, height
        for layer, canvas in zip(self.layers, resized):
            layer.image = canvas

    # -- persistence ----------------------------------------------------------

    def save_to_project(self, project_path: Path, tool_preferences: Dict[str, Any],
                        export_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Write layer PNGs to the sidecar dir and persist metadata."""
        layers_dir = get_paint_layers_dir(project_path)
        metadata: List[Dict[str, Any]] = []
        keep_names = set()
        for layer in self.layers:
            filename = f"{layer.id}.png"
            keep_names.add(filename)
            layer.image.save(layers_dir / filename)
            metadata.append({
                "id": layer.id,
                "name": layer.name,
                "visible": layer.visible,
                "opacity": layer.opacity,
                "image_file": f"{project_path.stem}_layers/{filename}",
            })

        stale = {p.name for p in layers_dir.glob("*.png")} - keep_names
        for name in stale:
            (layers_dir / name).unlink()

        payload = load_paint_project_data(project_path)
        payload["canvas_width"] = self.canvas_width
        payload["canvas_height"] = self.canvas_height
        payload["layers"] = metadata
        payload["tool_preferences"] = tool_preferences
        payload["export_settings"] = export_settings
        save_paint_project_data(project_path, payload)
        return payload

    @classmethod
    def load_from_project(cls, project_path: Path) -> "PaintLayerStack":
        """Rebuild a stack from a .ovpaint file, skipping missing layer files."""
        payload = load_paint_project_data(project_path)
        stack = cls(payload["canvas_width"], payload["canvas_height"])
        layers_dir = project_path.parent / f"{project_path.stem}_layers"

        for meta in payload.get("layers", []):
            image_path = layers_dir / Path(meta["image_file"]).name
            if not image_path.is_file():
                continue
            try:
                image = Image.open(image_path).convert("RGBA")
            except OSError:
                continue
            layer = PaintLayer(
                name=meta["name"],
                image=image,
                visible=meta["visible"],
                opacity=meta["opacity"],
                layer_id=meta["id"],
            )
            stack.layers.append(layer)

        stack.active_id = stack.layers[-1].id if stack.layers else None
        stack._loaded_preferences = {
            "tool_preferences": payload.get("tool_preferences", {}),
            "export_settings": payload.get("export_settings", {}),
        }
        return stack
