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

from OV_Libs.ImageEditingLib.image_models import RgbaColor
from OV_Libs.constants import OUTPUT_FILE_PREFIX, DEFAULT_OUTPUT_FORMAT


def extract_unique_colors(image: Any) -> List[RgbaColor]:
    """
    Extract all unique colors from an image.
    
    Args:
        image: A PIL Image object to extract colors from
        
    Returns:
        A sorted list of unique RGBA color tuples found in the image
    """
    unique_colors = set(image.getdata())
    return sorted(unique_colors)


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
    
    Creates a copy of the image and replaces colors pixel-by-pixel according
    to the provided mapping. Only colors present in the mapping are changed.
    
    Args:
        image: A PIL Image object to process
        color_mappings: Dictionary mapping source colors to replacement colors
        
    Returns:
        A new PIL Image with color replacements applied
    """
    img = image.copy()
    pixels = img.load()

    for y in range(img.height):
        for x in range(img.width):
            original_color = pixels[x, y]
            mapped_color = color_mappings.get(original_color)
            if mapped_color is not None:
                pixels[x, y] = mapped_color

    return img


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
