"""
Brightness/Contrast Node for Open Vision Pipeline.

Wraps the brightness/contrast filter for use in the node graph system.

Example:
    >>> from OV_Libs.NodesLib.brightness_contrast_node import create_brightness_contrast_node
    >>> node = create_brightness_contrast_node("bc-1", brightness=1.2, contrast=0.9)
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from OV_Libs.ImageEditingLib.brightness_contrast_filter import apply_brightness_contrast


@dataclass
class BrightnessContrastNodeConfig:
    """Configuration for a brightness/contrast adjustment node."""

    node_id: str
    brightness: float = 1.0
    contrast: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "brightness": self.brightness,
            "contrast": self.contrast,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrightnessContrastNodeConfig":
        return cls(
            node_id=data.get("node_id", ""),
            brightness=float(data.get("brightness", 1.0)),
            contrast=float(data.get("contrast", 1.0)),
        )


def execute_brightness_contrast_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Execute brightness/contrast node in pipeline.

    Node dict fields:
        - 'brightness': Brightness factor (default 1.0)
        - 'contrast': Contrast factor (default 1.0)

    Inputs:
        - [0]: Input image (PIL Image)

    Returns:
        Adjusted PIL Image (RGBA)

    Raises:
        ValueError: If no input provided or invalid factors
        TypeError: If input is not a PIL Image
    """
    if not inputs or len(inputs) < 1:
        raise ValueError("BrightnessContrastNode requires image input")

    image = inputs[0]
    if not hasattr(image, "convert"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")

    brightness = float(node.get("brightness", 1.0))
    contrast = float(node.get("contrast", 1.0))

    return apply_brightness_contrast(image, brightness=brightness, contrast=contrast)


def create_brightness_contrast_node(
    node_id: str,
    brightness: float = 1.0,
    contrast: float = 1.0,
) -> Dict[str, Any]:
    """
    Create a brightness/contrast node dictionary ready for serialization.
    """
    return BrightnessContrastNodeConfig(
        node_id=node_id, brightness=brightness, contrast=contrast
    ).to_dict()
