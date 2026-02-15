"""
ImageEditingLib - Core image editing functionality

This module provides image editing operations, models, and windows
for the Open Vision project.
"""

from OV_Libs.ImageEditingLib.image_models import ImageRecord, RgbaColor
from OV_Libs.ImageEditingLib.image_editing_ops import (
    extract_unique_colors,
    build_identity_mapping,
    apply_color_mapping,
    save_images,
)

__all__ = [
    "ImageRecord",
    "RgbaColor",
    "extract_unique_colors",
    "build_identity_mapping",
    "apply_color_mapping",
    "save_images",
]
