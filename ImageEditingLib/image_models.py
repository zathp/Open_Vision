from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from pillow_compat import Image

RgbaColor = Tuple[int, int, int, int]


@dataclass
class ImageRecord:
    path: Path
    original: 'Image.Image'
    modified: 'Image.Image'
