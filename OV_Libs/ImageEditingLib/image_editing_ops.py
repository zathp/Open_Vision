"""
Core image editing operations for Open Vision.

This module provides low-level image manipulation functions including
color extraction, color mapping, and batch image saving.

Functions:
    extract_unique_colors: Extract all unique colors from an image
    build_identity_mapping: Create a color-to-color identity mapping
    apply_color_mapping: Apply color replacements to an image
    save_images: Batch save multiple ImageRecords to disk
"""

from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np

from OV_Libs.ImageEditingLib.image_models import RgbaColor
from OV_Libs.constants import OUTPUT_FILE_PREFIX, DEFAULT_OUTPUT_FORMAT


def _as_channel_array(image: Any) -> np.ndarray:
    return np.asarray(image)


def _pack_channels(flat: np.ndarray) -> np.ndarray:
    """Pack an (N, C) uint8 array into one big-endian uint32 value per row."""
    channels = flat.shape[1]
    shifts = (np.arange(channels - 1, -1, -1, dtype=np.uint32) * 8)
    shifted = flat.astype(np.uint32) << shifts[None, :]
    return shifted.sum(axis=1, dtype=np.uint32)


def _unpack_channels(packed: np.ndarray, channels: int) -> np.ndarray:
    """Inverse of _pack_channels: (N,) uint -> (N, C) uint8."""
    shifts = np.arange(channels - 1, -1, -1, dtype=np.uint32) * 8
    bits = ((packed[:, None] >> shifts[None, :]) & np.uint32(255)).astype(np.uint8)
    return bits


def _unique_sorted(values: np.ndarray) -> np.ndarray:
    """Sorted unique values of a 1-D array; far cheaper than np.unique here."""
    ordered = np.sort(values)
    if ordered.size == 0:
        return ordered
    keep = np.empty(ordered.shape, dtype=bool)
    keep[0] = True
    keep[1:] = ordered[1:] != ordered[:-1]
    return ordered[keep]


def extract_unique_colors(image: Any) -> List[RgbaColor]:
    """
    Extract all unique colors from an image.

    Vectorized via packed 1-D unique sort; returns colors ordered
    lexicographically by channel (identical ordering to sorting Python
    tuples), matching the original implementation's contract for both
    multi-channel and palette-mode images.

    Args:
        image: A PIL Image object to extract colors from

    Returns:
        A sorted list of unique colors found in the image
    """
    array = _as_channel_array(image)

    if array.ndim == 2:
        unique_values = np.unique(array)
        return [int(value) for value in unique_values.tolist()]

    packed = _pack_channels(array.reshape(-1, array.shape[-1]))
    unique_packed = _unique_sorted(packed)
    return [tuple(row) for row in _unpack_channels(unique_packed, array.shape[-1]).tolist()]


def build_identity_mapping(colors: Sequence[RgbaColor]) -> Dict[RgbaColor, RgbaColor]:
    """
    Create an identity mapping where each color maps to itself.

    Args:
        colors: A sequence of RGBA color tuples

    Returns:
        A dictionary mapping each color to itself
    """
    return {color: color for color in colors}


def apply_color_mapping(image: Any, color_mappings: Dict[RgbaColor, RgbaColor]) -> Any:
    """
    Apply color replacements to an image based on a mapping dictionary.

    Vectorized replacement of the original pixel-by-pixel loop. Only pixels
    whose full channel tuple exactly equals a mapping key are changed; all
    other pixels are byte-identical to the input. Works for any PIL mode:
    keys whose length differs from the image's channel count simply never
    match (same semantics as tuple comparison in the original loop).

    Args:
        image: A PIL Image object to process
        color_mappings: Dictionary mapping source colors to replacement colors

    Returns:
        A new PIL Image with color replacements applied
    """
    if not color_mappings:
        return image.copy()

    array = _as_channel_array(image).copy()
    if array.ndim != 3:
        raise ValueError(
            f"apply_color_mapping expects a multi-channel image, got array shape {array.shape}"
        )

    channels = array.shape[-1]
    flat = array.reshape(-1, channels)

    source_keys = []
    replacement_values = []
    for source_color, replacement_color in color_mappings.items():
        if len(source_color) != channels or len(replacement_color) != channels:
            continue
        source_keys.append(list(source_color))
        replacement_values.append(list(replacement_color))

    if not source_keys:
        return _array_to_image(array, image)

    packed_pixels = _pack_channels(flat)
    unique_packed = _unique_sorted(packed_pixels)
    inverse = np.searchsorted(unique_packed, packed_pixels)

    packed_keys = _pack_channels(np.array(source_keys, dtype=np.uint8))
    key_positions = np.searchsorted(unique_packed, packed_keys)
    valid = key_positions < unique_packed.size
    matched = np.zeros(packed_keys.size, dtype=bool)
    matched[valid] = unique_packed[key_positions[valid]] == packed_keys[valid]

    if not matched.any():
        return _array_to_image(array, image)

    remap_lut = unique_packed.copy()
    remap_lut[key_positions[matched]] = _pack_channels(
        np.array([replacement_values[i] for i in np.nonzero(matched)[0]], dtype=np.uint8)
    )

    output_flat = _unpack_channels(remap_lut[inverse], channels)
    output = output_flat.reshape(array.shape).astype(np.uint8, copy=False)
    return _array_to_image(output, image)


def _array_to_image(array: np.ndarray, reference_image: Any) -> Any:
    """Rebuild a PIL image from an array using the reference image's mode."""
    from OV_Libs.pillow_compat import Image

    try:
        return Image.fromarray(array, mode=getattr(reference_image, "mode", None))
    except (TypeError, ValueError):
        return Image.fromarray(array)


def save_images(records, output_dir: Path) -> int:
    """
    Save multiple ImageRecords to disk in PNG format.
    
    Each image is saved with a 'modified_' prefix added to the original filename.
    
    Args:
        records: A sequence of ImageRecord objects to save
        output_dir: Directory path where images should be saved
        
    Returns:
        The number of images successfully saved
        
    Raises:
        OSError: If directory cannot be accessed or files cannot be written
    """
    if not output_dir.exists():
        raise OSError(f"Output directory does not exist: {output_dir}")
    
    if not output_dir.is_dir():
        raise OSError(f"Output path is not a directory: {output_dir}")
    
    saved_count = 0
    for record in records:
        save_path = output_dir / f"{OUTPUT_FILE_PREFIX}{record.path.name}"
        record.modified.save(save_path, format=DEFAULT_OUTPUT_FORMAT)
        saved_count += 1
    return saved_count
