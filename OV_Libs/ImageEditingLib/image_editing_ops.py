from pathlib import Path
from typing import Any, Dict, List, Sequence

from image_models import RgbaColor


def extract_unique_colors(image: Any) -> List[RgbaColor]:
    unique_colors = set(image.getdata())
    return sorted(unique_colors)


def build_identity_mapping(colors: Sequence[RgbaColor]) -> Dict[RgbaColor, RgbaColor]:
    return {color: color for color in colors}


def apply_color_mapping(image: Any, color_mappings: Dict[RgbaColor, RgbaColor]) -> Any:
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
    saved_count = 0
    for record in records:
        save_path = output_dir / f"modified_{record.path.name}"
        record.modified.save(save_path, format="PNG")
        saved_count += 1
    return saved_count
