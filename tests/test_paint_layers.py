"""
Unit tests for the paint layer system.

Tests PaintLayerStack operations: add/delete/reorder/merge/flatten,
compositing with visibility and opacity, canvas resize, and
.ovpaint round-trip persistence.
"""

import json

import numpy as np
from PIL import Image

from OV_Libs.PaintLib.paint_layers import (
    PaintLayer,
    PaintLayerStack,
    PaintLayerStackError,
)


def solid(size, color):
    return Image.new("RGBA", size, color)


class TestStackBasics:

    def test_rejects_invalid_canvas(self):
        for w, h in ((0, 10), (10, 0), (-1, -1)):
            try:
                PaintLayerStack(w, h)
            except ValueError:
                pass
            else:
                raise AssertionError("expected ValueError")

    def test_add_blank_layer_tracks_active(self):
        stack = PaintLayerStack(16, 16)
        assert stack.is_empty
        layer = stack.add_blank_layer()
        assert len(stack.layers) == 1
        assert stack.active_id == layer.id
        assert np.array(layer.image)[8, 8][3] == 0

    def test_default_names_increment(self):
        stack = PaintLayerStack(8, 8)
        first = stack.add_blank_layer()
        second = stack.add_blank_layer()
        assert (first.name, second.name) == ("Layer 1", "Layer 2")

    def test_unknown_id_raises(self):
        stack = PaintLayerStack(8, 8)
        try:
            stack.require_layer("nope")
        except PaintLayerStackError:
            pass
        else:
            raise AssertionError("expected PaintLayerStackError")


class TestCompositing:

    def test_visibility_and_opacity(self):
        stack = PaintLayerStack(2, 1)
        red = stack.layers[0] if stack.layers else None
        base = stack.add_image_layer(solid((2, 1), (255, 0, 0, 255)), "base")
        top = stack.add_image_layer(solid((2, 1), (0, 0, 255, 255)), "top")

        composite = np.array(stack.composite())
        assert tuple(composite[0, 0]) == (0, 0, 255, 255)

        top.visible = False
        composite = np.array(stack.composite())
        assert tuple(composite[0, 0]) == (255, 0, 0, 255)
        assert base.id != red

        top.opacity = 128
        top.visible = True
        composite = np.array(stack.composite())
        r, g, b, a = (int(v) for v in composite[0, 0])
        assert abs(r - 127) <= 1 and abs(b - 128) <= 1 and a == 255

    def test_invisible_layer_excluded_from_flatten_source(self):
        stack = PaintLayerStack(2, 2)
        stack.add_image_layer(solid((2, 2), (255, 0, 0, 255)))
        hidden = stack.add_image_layer(solid((2, 2), (0, 255, 0, 255)))
        hidden.visible = False
        flattened = np.array(stack.flatten_visible().image)
        assert tuple(flattened[0, 0]) == (255, 0, 0, 255)


class TestLayerOperations:

    def make_stack(self) -> tuple:
        stack = PaintLayerStack(4, 4)
        bottom = stack.add_image_layer(solid((4, 4), (255, 0, 0, 255)), "bottom")
        top = stack.add_image_layer(solid((4, 4), (0, 0, 255, 255)), "top")
        return stack, bottom, top

    def test_duplicate_inserts_above(self):
        stack, bottom, _ = self.make_stack()
        copy = stack.duplicate_layer(bottom.id)
        assert [l.name for l in stack.layers] == ["bottom", "bottom copy", "top"]
        assert stack.active_id == copy.id

    def test_delete_updates_active_to_neighbor(self):
        stack, _, top = self.make_stack()
        stack.set_active(top.id)
        stack.delete_layer(top.id)
        assert stack.get_active() is not None
        stack.delete_layer(stack.get_active().id)
        assert stack.is_empty and stack.active_id is None

    def test_merge_down_composites(self):
        stack, bottom, top = self.make_stack()
        merged = stack.merge_down(top.id)
        assert len(stack.layers) == 1
        assert merged.id == bottom.id or merged.name == "bottom"
        pixel = tuple(int(v) for v in np.array(merged.image)[0, 0])
        assert pixel == (0, 0, 255, 255)

    def test_merge_bottom_raises(self):
        stack, bottom, _ = self.make_stack()
        try:
            stack.merge_down(bottom.id)
        except PaintLayerStackError:
            pass
        else:
            raise AssertionError("expected PaintLayerStackError")

    def test_move_up_down(self):
        stack, bottom, top = self.make_stack()
        stack.move_layer(top.id, +1)
        assert stack.layers[-1].name == "top"
        stack.move_layer(top.id, -1)
        assert stack.layers[-1].name == "bottom"
        stack.move_layer(bottom.id, +5)
        assert stack.layers[-1].name == "bottom"
        stack.move_layer(bottom.id, -5)
        assert stack.layers[0].name == "bottom"

    def test_replace_layer_image_fits_canvas(self):
        stack, bottom, _ = self.make_stack()
        stack.replace_layer_image(bottom.id, solid((2, 2), (0, 255, 0, 255)))
        assert bottom.image.size == (4, 4)

    def test_resize_canvas_top_left(self):
        stack, _, _ = self.make_stack()
        stack.resize_canvas(6, 6)
        assert stack.canvas_width == 6
        for layer in stack.layers:
            assert layer.image.size == (6, 6)

    def test_resize_rejects_bad_anchor(self):
        stack, _, _ = self.make_stack()
        try:
            stack.resize_canvas(6, 6, anchor="bottom")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


class TestPersistence:

    def test_save_load_roundtrip(self, tmp_path):
        from OV_Libs.ProjStoreLib.project_store import create_paint_project_file

        project_path = create_paint_project_file(tmp_path, "RoundTrip")
        stack = PaintLayerStack(8, 8)
        kept = stack.add_image_layer(solid((8, 8), (1, 2, 3, 255)), "Kept")
        stack.duplicate_layer(kept.id)
        stack.layers[1].opacity = 100
        stack.layers[1].visible = False

        stack.save_to_project(
            project_path,
            tool_preferences={"last_tool": "brush"},
            export_settings={"format": "PNG"},
        )
        payload = json.loads(project_path.read_text(encoding="utf-8"))
        assert payload["layers"][0]["name"] == "Kept"
        assert payload["tool_preferences"]["last_tool"] == "brush"

        loaded = PaintLayerStack.load_from_project(project_path)
        assert loaded.canvas_width == 8
        assert [l.name for l in loaded.layers] == ["Kept", "Kept copy"]
        assert loaded.layers[1].opacity == 100
        assert loaded.layers[1].visible is False
        assert loaded._loaded_preferences["export_settings"]["format"] == "PNG"

    def test_load_skips_missing_layer_files(self, tmp_path):
        from OV_Libs.ProjStoreLib.project_store import create_paint_project_file

        project_path = create_paint_project_file(tmp_path, "Gappy")
        payload = json.loads(project_path.read_text(encoding="utf-8"))
        payload["layers"] = [
            {"id": "a", "name": "Ghost", "visible": True, "opacity": 255,
             "image_file": "Gappy_layers/a.png"},
        ]
        project_path.write_text(json.dumps(payload), encoding="utf-8")

        loaded = PaintLayerStack.load_from_project(project_path)
        assert loaded.is_empty


class TestPaintLayerUnit:

    def test_opacity_clamped(self):
        layer = PaintLayer("x", image=solid((2, 2), (0, 0, 0, 255)), opacity=999)
        assert layer.opacity == 255
        layer = PaintLayer("x", image=solid((2, 2), (0, 0, 0, 255)), opacity=-5)
        assert layer.opacity == 0

    def test_requires_image_or_canvas_size(self):
        try:
            PaintLayer("x")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")
