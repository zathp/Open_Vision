"""
Headless tool integrations for Initial_Forms utilities.

Adapts the functional cores of the standalone tools (Downsampler, Mirror,
RegionSelector, Greenscreen2) into pure PIL-in/PIL-out operations so they
can be embedded in editors without file paths or GUI dependencies:

- downsample_image: HSV-averaging pixelation (from Downsampler)
- mirror_image: axis flips including diagonals (from Mirror)
- crop_with_transparency: out-of-bounds-safe cropping (from RegionSelector)
- replace_color_range: tolerance-based color replacement (from Greenscreen2)
- adjust_color_hsv / shift_image_hsv: HSV channel adjustments

All functions return NEW images and never mutate their inputs.
"""

import colorsys
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

MIRROR_AXES = (
    "horizontal",
    "vertical",
    "diagonal_tl_br",
    "diagonal_tr_bl",
)

SELECTION_MODES = ("rgb_distance", "rgb_range", "hsv_range")


def _to_rgba(image: Image.Image) -> Image.Image:
    return image if image.mode == "RGBA" else image.convert("RGBA")


def _pack_rgba(array: np.ndarray) -> np.ndarray:
    """Pack an (N, 4) uint8 channel array into one uint32 value per row."""
    channels = array.astype(np.uint64)
    return (
        (channels[:, 0] << 24)
        | (channels[:, 1] << 16)
        | (channels[:, 2] << 8)
        | channels[:, 3]
    )


def _rgb_to_hsv_arrays(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convert an (..., 3) float64 RGB array (0-1 range) to H, S, V arrays.

    Hue in turns [0, 1); mirrors colorsys.rgb_to_hsv semantics including
    exact-equality tie handling between channels.
    """
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]

    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    delta = maxc - minc

    value = maxc
    safe_max = np.where(maxc == 0, 1.0, maxc)
    saturation = np.where(maxc == 0, 0.0, delta / safe_max)

    safe_delta = np.where(delta == 0, 1.0, delta)
    hue_when_red = ((g - b) / safe_delta) % 6.0
    hue_when_green = (b - r) / safe_delta + 2.0
    hue_when_blue = (r - g) / safe_delta + 4.0

    hue = np.where(
        maxc == r,
        hue_when_red,
        np.where(maxc == g, hue_when_green, hue_when_blue),
    )
    hue = np.where(delta == 0, 0.0, hue / 6.0) % 1.0
    return hue, saturation, value


def _hsv_to_rgb_arrays(
    hue: np.ndarray, saturation: np.ndarray, value: np.ndarray
) -> np.ndarray:
    """
    Convert H (turns [0, 1)), S, V arrays to an (..., 3) float64 RGB array.

    Mirrors colorsys.hsv_to_rgb sector construction.
    """
    scaled = hue * 6.0
    sector = np.floor(scaled).astype(np.int64) % 6
    frac = scaled - np.floor(scaled)

    p = value * (1.0 - saturation)
    q = value * (1.0 - frac * saturation)
    t = value * (1.0 - (1.0 - frac) * saturation)

    red = np.choose(sector, [value, q, p, p, t, value])
    green = np.choose(sector, [t, value, value, q, p, p])
    blue = np.choose(sector, [p, p, t, value, value, q])
    return np.stack([red, green, blue], axis=-1)


def _shift_hsv_arrays(
    hue: np.ndarray, saturation: np.ndarray, value: np.ndarray,
    hue_shift: float, sat_shift: float, val_shift: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    shifted_h = np.mod(hue + hue_shift / 360.0, 1.0)
    shifted_s = np.clip(saturation + sat_shift / 100.0, 0.0, 1.0)
    shifted_v = np.clip(value + val_shift / 100.0, 0.0, 1.0)
    return shifted_h, shifted_s, shifted_v


def downsample_image(image: Image.Image, output_size: Tuple[int, int] = (32, 32)) -> Image.Image:
    """
    Downsample an image by HSV averaging fully opaque pixels per block.

    Adapted from Initial_Forms/Downsampler.downsample_image_hsv (vectorized:
    identical algorithm, numpy block reduction instead of per-pixel loops;
    results may differ from the scalar original by at most 1/255 per channel
    due to floating-point summation order).

    Args:
        image: Input PIL image.
        output_size: Target (width, height); both must be >= 1.

    Returns:
        New RGBA PIL image of ``output_size``.

    Raises:
        ValueError: If any output dimension is less than 1.
    """
    width, height = int(output_size[0]), int(output_size[1])
    if width < 1 or height < 1:
        raise ValueError(f"output_size must be >= (1, 1), got {output_size}")

    rgba = _to_rgba(image)
    source_w, source_h = rgba.size
    pixels = np.array(rgba).astype(np.float64)
    opaque = pixels[:, :, 3] == 255.0

    rgb = pixels[:, :, :3] / 255.0
    hue, saturation, value = _rgb_to_hsv_arrays(rgb)

    sin_h = np.sin(hue * 2.0 * np.pi) * opaque
    cos_h = np.cos(hue * 2.0 * np.pi) * opaque

    starts_x = np.clip((np.arange(width) * (source_w / width)).astype(np.int64), 0, source_w - 1)
    starts_y = np.clip((np.arange(height) * (source_h / height)).astype(np.int64), 0, source_h - 1)

    def block_reduce(array: np.ndarray) -> np.ndarray:
        reduced = np.add.reduceat(array, starts_y, axis=0)
        return np.add.reduceat(reduced, starts_x, axis=1)

    counts = block_reduce(opaque.astype(np.float64))
    sum_sin = block_reduce(sin_h)
    sum_cos = block_reduce(cos_h)
    sum_s = block_reduce(saturation * opaque)
    sum_v = block_reduce(value * opaque)

    valid = counts > 0
    safe_counts = np.where(valid, counts, 1.0)

    mean_sin = sum_sin / safe_counts
    mean_cos = sum_cos / safe_counts
    avg_h = np.arctan2(mean_sin, mean_cos) / (2.0 * np.pi)
    avg_h = np.where(avg_h < 0, avg_h + 1.0, avg_h)
    avg_s = sum_s / safe_counts
    avg_v = sum_v / safe_counts

    rgb_out = _hsv_to_rgb_arrays(avg_h, avg_s, avg_v)
    rgb_out = np.floor(np.clip(rgb_out, 0.0, 1.0) * 255.0)

    output_array = np.zeros((height, width, 4), dtype=np.uint8)
    output_array[:, :, :3] = np.where(valid[..., None], rgb_out, 0).astype(np.uint8)
    output_array[:, :, 3] = np.where(valid, 255, 0).astype(np.uint8)

    return Image.fromarray(output_array, "RGBA")


def mirror_image(image: Image.Image, axis: str = "horizontal") -> Image.Image:
    """
    Mirror an image along an axis.

    Args:
        image: Input PIL image.
        axis: One of MIRROR_AXES - 'horizontal' flips top-bottom,
            'vertical' flips left-right, 'diagonal_tl_br' transposes,
            'diagonal_tr_bl' anti-transposes.

    Returns:
        New mirrored PIL image (mode preserved).

    Raises:
        ValueError: If axis is not one of MIRROR_AXES.
    """
    if axis not in MIRROR_AXES:
        raise ValueError(f"Invalid axis: {axis}. Must be one of {MIRROR_AXES}")

    if axis == "horizontal":
        return image.transpose(Image.FLIP_TOP_BOTTOM)
    if axis == "vertical":
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    if axis == "diagonal_tl_br":
        return image.transpose(Image.TRANSPOSE)
    return image.transpose(Image.TRANSVERSE)


def crop_with_transparency(
    image: Image.Image,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> Image.Image:
    """
    Crop a region, filling out-of-bounds areas with transparency.

    Adapted from Initial_Forms/RegionSelector.crop_with_coordinates.

    Args:
        image: Input PIL image.
        x1, y1: First corner (any order relative to x2/y2).
        x2, y2: Opposite corner.

    Returns:
        New RGBA PIL image sized (|x2-x1|, |y2-y1|).

    Raises:
        ValueError: If the requested region has zero width or height.
    """
    rgba = _to_rgba(image)
    left, right = sorted((int(x1), int(x2)))
    top, bottom = sorted((int(y1), int(y2)))
    crop_w, crop_h = right - left, bottom - top
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError(f"Crop region must have positive size, got {crop_w}x{crop_h}")

    img_w, img_h = rgba.size
    out_of_bounds = left < 0 or top < 0 or right > img_w or bottom > img_h

    if not out_of_bounds:
        return rgba.crop((left, top, right, bottom))

    cropped = Image.new("RGBA", (crop_w, crop_h), (0, 0, 0, 0))
    src_left, src_top = max(0, left), max(0, top)
    src_right, src_bottom = min(img_w, right), min(img_h, bottom)
    if src_right > src_left and src_bottom > src_top:
        section = rgba.crop((src_left, src_top, src_right, src_bottom))
        cropped.paste(section, (src_left - left, src_top - top))
    return cropped


def build_color_mask(
    image: Image.Image,
    base_color: Sequence[int],
    tolerances: Sequence[float],
    selection_type: str = "rgb_distance",
) -> np.ndarray:
    """
    Build a boolean mask of pixels matching a base color within tolerance.

    Matching semantics follow Greenscreen2's range selection and the node
    editor's selection_type enum:

    - rgb_distance: Euclidean RGB distance <= single scalar tolerance[0].
      Extra tolerance entries are ignored.
    - rgb_range: per-channel |c - base| <= tolerance[channel].
    - hsv_range: per-channel difference in H(degrees)/S(%)/V(%) with
      circular hue handling.

    Args:
        image: Input PIL image (converted to RGBA internally).
        base_color: (r, g, b[, a]) reference color, 0-255 channels.
        tolerances: Tolerance values; interpretation depends on selection_type.
        selection_type: One of SELECTION_MODES.

    Returns:
        Boolean numpy array of shape (height, width); True where matched.
        Alpha is ignored for matching.

    Raises:
        ValueError: If selection_type unknown or tolerances missing.
    """
    if selection_type not in SELECTION_MODES:
        raise ValueError(f"Invalid selection_type: {selection_type}. Must be one of {SELECTION_MODES}")

    rgba = _to_rgba(image)
    rgb_array = np.array(rgba)[:, :, :3].astype(np.int16)
    base = [float(c) for c in base_color[:3]]

    if selection_type == "rgb_distance":
        if not tolerances:
            raise ValueError("rgb_distance requires one scalar tolerance")
        distance = np.sqrt(((rgb_array - np.array(base)) ** 2).sum(axis=-1))
        return distance <= float(tolerances[0])

    if selection_type == "rgb_range":
        if len(tolerances) < 3:
            raise ValueError("rgb_range requires three per-channel tolerances")
        deltas = np.abs(rgb_array - np.array(base))
        return (
            (deltas[:, :, 0] <= tolerances[0])
            & (deltas[:, :, 1] <= tolerances[1])
            & (deltas[:, :, 2] <= tolerances[2])
        )

    if len(tolerances) < 3:
        raise ValueError("hsv_range requires three tolerances (H degrees, S %, V %)")

    r, g, b = base[0] / 255.0, base[1] / 255.0, base[2] / 255.0
    base_h, base_s, base_v = colorsys.rgb_to_hsv(r, g, b)
    base_h_deg, base_s_pct, base_v_pct = base_h * 360.0, base_s * 100.0, base_v * 100.0

    height, width = rgba.size[1], rgba.size[0]
    normalized = rgb_array.astype(np.float64) / 255.0
    pixel_h, pixel_s, pixel_v = _rgb_to_hsv_arrays(normalized.reshape(-1, 3))

    h_deg = pixel_h * 360.0
    s_pct = pixel_s * 100.0
    v_pct = pixel_v * 100.0

    h_diff = np.abs(h_deg - base_h_deg)
    h_diff = np.where(h_diff > 180.0, 360.0 - h_diff, h_diff)

    matches = (
        (h_diff <= tolerances[0])
        & (np.abs(s_pct - base_s_pct) <= tolerances[1])
        & (np.abs(v_pct - base_v_pct) <= tolerances[2])
    )
    return matches.reshape(height, width)


def replace_color_range(
    image: Image.Image,
    base_color: Sequence[int],
    tolerances: Sequence[float],
    replacement_color: Optional[Sequence[int]] = None,
    selection_type: str = "rgb_distance",
    make_transparent: bool = False,
) -> Tuple[Image.Image, np.ndarray]:
    """
    Replace (or erase) all pixels matching a base color within tolerance.

    Args:
        image: Input PIL image.
        base_color: Reference (r, g, b[, a]) color, 0-255 channels.
        tolerances: Tolerance values interpreted per selection_type.
        replacement_color: (r, g, b[, a]) fill color; alpha defaults to 255.
            Ignored when make_transparent is True.
        selection_type: One of SELECTION_MODES.
        make_transparent: When True, matched pixels become fully transparent
            instead of being recolored.

    Returns:
        Tuple of (new RGBA image, boolean match mask ndarray).

    Raises:
        ValueError: Via build_color_mask for invalid selection_type/tolerances.
    """
    rgba = _to_rgba(image)
    mask = build_color_mask(rgba, base_color, tolerances, selection_type)

    result_array = np.array(rgba)
    if make_transparent:
        result_array[mask] = [0, 0, 0, 0]
    else:
        if replacement_color is None:
            raise ValueError("replacement_color is required when make_transparent is False")
        fill = list(replacement_color)
        while len(fill) < 4:
            fill.append(255)
        result_array[mask] = [
            int(fill[0]), int(fill[1]), int(fill[2]), int(fill[3]),
        ]

    return Image.fromarray(result_array, "RGBA"), mask


def adjust_color_hsv(
    rgba_color: Sequence[int],
    hue_shift: float,
    sat_shift: float,
    val_shift: float,
) -> Tuple[int, int, int, int]:
    """
    Shift a single RGBA color in HSV space.

    Hue shifts in degrees (-180..180, wrapped); saturation/value shifts are
    percentages clamped to 0-100 range after adjustment.

    Args:
        rgba_color: (r, g, b, a) color, 0-255 channels.
        hue_shift: Degrees to rotate hue.
        sat_shift: Percent change of saturation.
        val_shift: Percent change of value.

    Returns:
        Adjusted (r, g, b, a) integer tuple.
    """
    r, g, b = rgba_color[0] / 255.0, rgba_color[1] / 255.0, rgba_color[2] / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    h = (h + hue_shift / 360.0) % 1.0
    s = max(0.0, min(1.0, s + sat_shift / 100.0))
    v = max(0.0, min(1.0, v + val_shift / 100.0))

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255), int(rgba_color[3]))


def shift_image_hsv(
    image: Image.Image,
    hue_shift: float = 0.0,
    sat_shift: float = 0.0,
    val_shift: float = 0.0,
    only_colors: Optional[List[Sequence[int]]] = None,
) -> Image.Image:
    """
    Apply an HSV shift to every pixel, optionally restricted to exact colors.

    Backs the editor's HSV mass-edit actions (from Greenscreen2). Vectorized:
    zero shifts return an exact copy; nonzero shifts may differ from the
    legacy per-pixel implementation by at most 1/255 per channel due to
    floating-point rounding.

    Args:
        image: Input PIL image.
        hue_shift: Degrees (-180..180).
        sat_shift: Percent (-100..100).
        val_shift: Percent (-100..100).
        only_colors: When provided, only pixels whose RGBA tuple exactly
            equals one of these colors are shifted; None shifts everything.

    Returns:
        New shifted RGBA PIL image.
    """
    rgba = _to_rgba(image)
    array = np.array(rgba)

    if hue_shift == 0 and sat_shift == 0 and val_shift == 0:
        return Image.fromarray(array, "RGBA")

    height, width = array.shape[:2]
    flat = array.reshape(-1, 4)

    if only_colors is None:
        target_indices = np.arange(flat.shape[0])
    else:
        packed_pixels = _pack_rgba(flat)
        packed_targets = np.unique(
            np.array([_pack_rgba(np.array([[int(c) for c in color[:4]]]))[0] for color in only_colors],
                     dtype=np.uint64)
        )
        target_indices = np.nonzero(np.isin(packed_pixels, packed_targets))[0]

    if target_indices.size == 0:
        return Image.fromarray(array, "RGBA")

    subset_rgb = flat[target_indices, :3].astype(np.float64) / 255.0
    h, s, v = _rgb_to_hsv_arrays(subset_rgb)
    h, s, v = _shift_hsv_arrays(h, s, v, hue_shift, sat_shift, val_shift)
    shifted_rgb = _hsv_to_rgb_arrays(h, s, v)

    result = array.copy()
    result_flat = result.reshape(-1, 4)
    result_flat[target_indices, :3] = np.floor(
        np.clip(shifted_rgb, 0.0, 1.0) * 255.0
    ).astype(np.uint8)

    return Image.fromarray(result, "RGBA")
