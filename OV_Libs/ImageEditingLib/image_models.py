"""
Image editing data models for Open Vision.

This module defines core data structures used throughout the image editing system.

Classes:
    ImageRecord: Container for an image's path and both original and modified versions
    
Type Aliases:
    RgbaColor: A tuple of 4 integers representing RGBA color values (0-255)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from OV_Libs.pillow_compat import Image

RgbaColor = Tuple[int, int, int, int]


@dataclass
class ImageRecord:
    path: Path
    original: 'Image.Image'
    modified: 'Image.Image'
