"""
Brightness/Contrast filter operations.

Simple utility adjustment filter used to validate stackable filters
in the pipeline (per OPEN_VISION_TODO Priority 2).
"""

from typing import Any

from PIL import Image, ImageEnhance


def apply_brightness(image: Image.Image, factor: float = 1.0) -> Image.Image:
    """
    Adjust image brightness.

    Args:
        image: Input PIL image.
        factor: 0.0 = black, 1.0 = unchanged, > 1.0 = brighter.

    Returns:
        New adjusted PIL image.

    Raises:
        ValueError: If factor is negative.
    """
    if factor < 0:
        raise ValueError(f"brightness factor must be >= 0, got {factor}")
    enhanced = ImageEnhance.Brightness(image.convert("RGBA"))
    return enhanced.enhance(float(factor))


def apply_contrast(image: Image.Image, factor: float = 1.0) -> Image.Image:
    """
    Adjust image contrast.

    Args:
        image: Input PIL image.
        factor: 0.0 = flat grey, 1.0 = unchanged, > 1.0 = more contrast.

    Returns:
        New adjusted PIL image.

    Raises:
        ValueError: If factor is negative.
    """
    if factor < 0:
        raise ValueError(f"contrast factor must be >= 0, got {factor}")
    enhanced = ImageEnhance.Contrast(image.convert("RGBA"))
    return enhanced.enhance(float(factor))


def apply_brightness_contrast(
    image: Image.Image,
    brightness: float = 1.0,
    contrast: float = 1.0,
) -> Any:
    """
    Apply brightness then contrast adjustments.

    Args:
        image: Input PIL image.
        brightness: Brightness factor (see apply_brightness).
        contrast: Contrast factor (see apply_contrast).

    Returns:
        New adjusted RGBA PIL image.
    """
    result = apply_brightness(image, brightness)
    return apply_contrast(result, contrast)
