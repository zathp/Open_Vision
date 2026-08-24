"""
Unit tests for Initial_Forms headless integrations.

Tests the pure-image wrappers for Downsampler, Mirror, RegionSelector,
and Greenscreen2 functionality.
"""

import colorsys

import numpy as np
from PIL import Image

from OV_Libs.Initial_Forms.integration import (
    adjust_color_hsv,
    build_color_mask,
    crop_with_transparency,
    downsample_image,
    mirror_image,
    replace_color_range,
    SELECTION_MODES,
    shift_image_hsv,
)


def make_image(size, fill=(255, 0, 0, 255)):
    return Image.new("RGBA", size, fill)


class TestDownsampleImage:

    def test_output_size_and_mode(self):
        result = downsample_image(make_image((64, 64)), (8, 8))
        assert result.size == (8, 8)
        assert result.mode == "RGBA"

    def test_solid_color_stays_solid(self):
        result = downsample_image(make_image((40, 40), (10, 200, 30, 255)), (4, 4))
        result_rgb = [int(v) for v in np.array(result)[2, 2][:3]]
        assert all(abs(a - b) <= 1 for a, b in zip(result_rgb, [10, 200, 30]))

    def test_transparent_blocks_stay_transparent(self):
        source = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        result = downsample_image(source, (5, 5))
        assert tuple(np.array(result)[1, 1]) == (0, 0, 0, 0)

    def test_rejects_invalid_size(self):
        try:
            downsample_image(make_image((4, 4)), (0, 4))
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")

    def test_matches_legacy_function(self, tmp_path):
        from OV_Libs.Initial_Forms.Downsampler import downsample_image_hsv

        source = Image.new("RGBA", (32, 32), (50, 100, 150, 255))
        path = tmp_path / "src.png"
        source.save(path)

        legacy = downsample_image_hsv(str(path), (4, 4))
        local = downsample_image(source, (4, 4))
        assert np.array_equal(np.array(legacy), np.array(local))

    def test_matches_legacy_function_on_gradient(self, tmp_path):
        """Vectorized result stays within 1/255 of the scalar original.

        Floating-point summation order differs (np.add.reduceat vs
        sequential np.mean over a Python-built list), so per-channel
        values may round to adjacent integers after int() truncation.
        """
        from OV_Libs.Initial_Forms.Downsampler import downsample_image_hsv

        gradient = np.zeros((48, 64, 4), dtype=np.uint8)
        gradient[..., 0] = np.linspace(0, 255, 64, dtype=np.uint8)[None, :]
        gradient[..., 1] = np.linspace(0, 255, 48, dtype=np.uint8)[:, None]
        gradient[..., 2] = 128
        gradient[..., 3] = 255
        gradient[10:20, 20:30, 3] = 0

        path = tmp_path / "grad.png"
        Image.fromarray(gradient, "RGBA").save(path)
        source = Image.fromarray(gradient, "RGBA")

        legacy = np.array(downsample_image_hsv(str(path), (12, 9)))
        local = np.array(downsample_image(source, (12, 9)))

        assert legacy.shape == local.shape
        assert np.all(legacy[:, :, 3] == local[:, :, 3])
        assert np.max(np.abs(legacy[:, :, :3].astype(int) - local[:, :, :3].astype(int))) <= 1


class TestMirrorImage:

    def test_horizontal_flip(self):
        array = np.zeros((2, 2, 4), dtype=np.uint8)
        array[0, 0] = (255, 0, 0, 255)
        source = Image.fromarray(array, "RGBA")
        flipped = np.array(mirror_image(source, "horizontal"))
        assert tuple(flipped[0, 0]) == (0, 0, 0, 0)
        assert tuple(flipped[1, 0]) == (255, 0, 0, 255)

    def test_vertical_flip_swaps_columns(self):
        array = np.zeros((1, 2, 4), dtype=np.uint8)
        array[0, 0] = (0, 255, 0, 255)
        flipped = np.array(mirror_image(Image.fromarray(array, "RGBA"), "vertical"))
        assert tuple(flipped[0, 0]) == (0, 0, 0, 0)
        assert tuple(flipped[0, 1]) == (0, 255, 0, 255)

    def test_diagonal_transpose_swaps_shape(self):
        source = make_image((3, 7))
        assert mirror_image(source, "diagonal_tl_br").size == (7, 3)

    def test_all_axes_valid_and_invalid_rejected(self):
        source = make_image((4, 4))
        for axis in ("horizontal", "vertical", "diagonal_tl_br", "diagonal_tr_bl"):
            mirror_image(source, axis)
        try:
            mirror_image(source, "sideways")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


class TestCropWithTransparency:

    def test_in_bounds_crop(self):
        cropped = crop_with_transparency(make_image((10, 10)), 2, 2, 6, 6)
        assert cropped.size == (4, 4)
        assert cropped.mode == "RGBA"

    def test_out_of_bounds_pads_transparent(self):
        cropped = crop_with_transparency(make_image((10, 10)), -4, -4, 6, 6)
        assert cropped.size == (10, 10)
        assert tuple(cropped.getpixel((0, 0))) == (0, 0, 0, 0)
        assert tuple(cropped.getpixel((9, 9)))[:3] == (255, 0, 0)

    def test_corner_order_irrelevant(self):
        a = crop_with_transparency(make_image((10, 10)), 1, 1, 5, 5)
        b = crop_with_transparency(make_image((10, 10)), 5, 5, 1, 1)
        assert np.array_equal(np.array(a), np.array(b))

    def test_zero_size_raises(self):
        try:
            crop_with_transparency(make_image((10, 10)), 5, 5, 5, 5)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


class TestBuildColorMask:

    def make_two_color_image(self):
        array = np.zeros((2, 2, 4), dtype=np.uint8)
        array[:, 0] = (255, 0, 0, 255)
        array[:, 1] = (0, 0, 255, 255)
        return Image.fromarray(array, "RGBA")

    def test_rgb_distance(self):
        mask = build_color_mask(
            self.make_two_color_image(), (250, 5, 5), (10,), "rgb_distance"
        )
        assert mask[:, 0].all() and not mask[:, 1].any()

    def test_rgb_range_per_channel(self):
        mask = build_color_mask(
            self.make_two_color_image(), (255, 0, 0), (5, 5, 5), "rgb_range"
        )
        assert mask[:, 0].all() and not mask[:, 1].any()

    def test_hsv_range_with_circular_hue(self):
        image = self.make_two_color_image()
        near = build_color_mask(image, (5, 5, 250), (20, 20, 20), "hsv_range")
        assert near[:, 1].all() and not near[:, 0].any()
        wrapped = build_color_mask(image, (245, 5, 5), (20, 20, 20), "hsv_range")
        assert wrapped[:, 0].all()

    def test_alpha_ignored_for_matching(self):
        array = np.zeros((1, 2, 4), dtype=np.uint8)
        array[0, 0] = (10, 20, 30, 255)
        array[0, 1] = (10, 20, 30, 128)
        mask = build_color_mask(Image.fromarray(array, "RGBA"), (10, 20, 30), (0, 0, 0), "rgb_range")
        assert mask.all()

    def test_unknown_mode_raises(self):
        try:
            build_color_mask(make_image((2, 2)), (0, 0, 0), (1,), "lab_space")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


class TestReplaceColorRange:

    def test_replace_keeps_other_pixels(self):
        source = make_image((2, 1), (0, 255, 0, 255))
        source.putpixel((1, 0), (0, 255, 0, 255))
        replaced, mask = replace_color_range(
            source, (0, 255, 0), (0, 0, 0), (255, 0, 0, 255), "rgb_range"
        )
        assert mask.all()
        assert tuple(replaced.getpixel((0, 0))) == (255, 0, 0, 255)

    def test_make_transparent_erases_match(self):
        source = make_image((2, 1), (9, 9, 9, 255))
        erased, _ = replace_color_range(
            source, (9, 9, 9), (2,), None, "rgb_distance", make_transparent=True
        )
        assert tuple(erased.getpixel((0, 0))) == (0, 0, 0, 0)

    def test_missing_replacement_raises(self):
        try:
            replace_color_range(make_image((2, 2)), (0, 0, 0), (1,))
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")


class TestHsvShift:

    def test_adjust_single_color_preserves_alpha(self):
        r, g, b, a = adjust_color_hsv((255, 0, 0, 200), 120, 0, 0)
        expected_hue = colorsys.rgb_to_hsv(0, 1, 0)[0]
        actual_hue = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)[0]
        assert abs(actual_hue - expected_hue) < 0.02
        assert a == 200

    def test_zero_shift_is_identity(self):
        source = make_image((3, 3), (12, 34, 56, 78))
        assert np.array_equal(np.array(shift_image_hsv(source)), np.array(source))

    def test_only_colors_restricts_scope(self):
        array = np.zeros((1, 2, 4), dtype=np.uint8)
        array[0, 0] = (255, 0, 0, 255)
        array[0, 1] = (0, 255, 0, 255)
        source = Image.fromarray(array, "RGBA")
        shifted = shift_image_hsv(source, hue_shift=180, only_colors=[(255, 0, 0, 255)])
        assert tuple(shifted.getpixel((0, 0))) != (255, 0, 0, 255)
        assert tuple(shifted.getpixel((1, 0))) == (0, 255, 0, 255)

    def test_selection_modes_constant(self):
        assert set(SELECTION_MODES) == {"rgb_distance", "rgb_range", "hsv_range"}


class TestVectorizedParity:
    """Cross-checks vectorized paths against scalar colorsys references."""

    @staticmethod
    def _random_image(seed=3, size=(24, 20)):
        rng = np.random.default_rng(seed)
        array = rng.integers(0, 256, (size[1], size[0], 4), dtype=np.uint8)
        return Image.fromarray(array, "RGBA")

    @staticmethod
    def _scalar_shift_reference(image, hue, sat, val, restrict):
        from OV_Libs.Initial_Forms.integration import adjust_color_hsv

        array = np.array(image.convert("RGBA"))
        out = array.copy()
        for y in range(array.shape[0]):
            for x in range(array.shape[1]):
                original = tuple(int(c) for c in array[y, x][:4])
                if restrict is not None and original not in {
                    tuple(int(c) for c in color[:4]) for color in restrict
                }:
                    continue
                out[y, x] = adjust_color_hsv(original, hue, sat, val)
        return out

    def test_shift_matches_scalar_reference(self):
        image = self._random_image()
        got = np.array(shift_image_hsv(image, hue_shift=70, sat_shift=-15, val_shift=10))
        expected = self._scalar_shift_reference(image, 70, -15, 10, None)
        assert np.max(np.abs(got.astype(int) - expected.astype(int))) <= 1
        assert np.array_equal(got[:, :, 3], expected[:, :, 3])

    def test_restricted_shift_matches_scalar_reference(self):
        image = self._random_image(seed=9)
        restrict = [(12, 34, 56, 255), (200, 100, 50, 78)]
        array = np.array(image)
        array[2, 2] = restrict[0]
        array[5, 7] = restrict[1]
        array[8, 3] = restrict[0]
        image = Image.fromarray(array, "RGBA")

        got = np.array(shift_image_hsv(image, 120, 25, -5, only_colors=restrict))
        expected = self._scalar_shift_reference(image, 120, 25, -5, restrict)

        changed_pixels = np.any(got != np.array(image), axis=-1)
        assert changed_pixels.sum() == 3
        assert np.max(np.abs(got.astype(int) - expected.astype(int))) <= 1

    def test_hsv_range_mask_matches_scalar_reference(self):
        import colorsys as cs

        image = self._random_image(seed=17, size=(16, 16))
        base = (128, 64, 200)
        tolerances = (40.0, 30.0, 35.0)

        r, g, b = base[0] / 255, base[1] / 255, base[2] / 255
        bh, bs, bv = cs.rgb_to_hsv(r, g, b)

        array = np.array(image.convert("RGBA"))
        expected = np.zeros((16, 16), dtype=bool)
        for y in range(16):
            for x in range(16):
                pr, pg, pb = (c / 255.0 for c in array[y, x, :3])
                h, s, v = cs.rgb_to_hsv(pr, pg, pb)
                hd = abs(h * 360 - bh * 360)
                if hd > 180:
                    hd = 360 - hd
                expected[y, x] = (
                    hd <= tolerances[0]
                    and abs(s * 100 - bs * 100) <= tolerances[1]
                    and abs(v * 100 - bv * 100) <= tolerances[2]
                )

        mask = build_color_mask(image, base, tolerances, "hsv_range")
        assert np.array_equal(mask, expected)
