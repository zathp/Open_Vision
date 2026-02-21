"""
Color Shift Node for Open Vision.

This node applies color shifting operations to images and generates masks
showing which pixels were changed. Supports various color selection and
shift methods.

Classes:
    ColorShiftNodeConfig: Configuration for color shift node
    
Functions:
    execute_color_shift_node: Pipeline executor for color shift nodes
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from OV_Libs.pillow_compat import Image
from OV_Libs.ImageEditingLib.color_shift_filter import (
    ColorShiftFilter,
    ColorShiftFilterOptions,
    RgbaColor,
    SelectionType,
    ShiftType,
    DistanceType,
)


@dataclass
class ColorShiftNodeConfig:
    """Configuration for color shift node execution.
    
    Attributes:
        base_color_r: Red component of base color (0-255)
        base_color_g: Green component of base color (0-255)
        base_color_b: Blue component of base color (0-255)
        base_color_a: Alpha component of base color (0-255, default 255)
        selection_type: How to select colors - 'hsv_range', 'rgb_range', 'rgb_distance'
        shift_type: How to shift colors - 'percentile_rgb', 'percentile_hsv', 
               'absolute_rgb', 'absolute_hsv', 'match_distance_rgb'
        tolerance: Tolerance for color selection. Can be a scalar or HSV triplet (H, S, V)
        distance_type: Distance metric for 'rgb_distance' - 'euclidean', 'manhattan', 'chebyshev'
        shift_amount: Amount to shift (can be float or tuple of 3 floats for RGB/HSV)
        output_color_r/g/b/a: Output base color used by 'match_distance_rgb'
        output_mask: If True, return (image, mask) tuple; else just image
    """
    base_color_r: int = 0
    base_color_g: int = 0
    base_color_b: int = 0
    base_color_a: int = 255
    selection_type: SelectionType = "rgb_distance"
    shift_type: ShiftType = "absolute_rgb"
    tolerance: float | Tuple[float, float, float] = 30.0
    distance_type: DistanceType = "euclidean"
    shift_amount: float | Tuple[float, float, float] = 50.0
    output_color_r: int = 0
    output_color_g: int = 0
    output_color_b: int = 0
    output_color_a: int = 255
    output_mask: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColorShiftNodeConfig":
        """Create from dictionary."""
        normalized = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        shift_amount = normalized.get("shift_amount")
        if isinstance(shift_amount, list):
            normalized["shift_amount"] = tuple(shift_amount[:3])
        return cls(**normalized)
    
    def get_base_color(self) -> RgbaColor:
        """Get the base color as RGBA tuple."""
        return (
            int(max(0, min(255, self.base_color_r))),
            int(max(0, min(255, self.base_color_g))),
            int(max(0, min(255, self.base_color_b))),
            int(max(0, min(255, self.base_color_a))),
        )
    
    def get_filter_options(self) -> ColorShiftFilterOptions:
        """Get ColorShiftFilterOptions from this config."""
        return ColorShiftFilterOptions(
            selection_type=self.selection_type,
            shift_type=self.shift_type,
            tolerance=self.tolerance,
            distance_type=self.distance_type,
            output_base_color=(
                int(max(0, min(255, self.output_color_r))),
                int(max(0, min(255, self.output_color_g))),
                int(max(0, min(255, self.output_color_b))),
                int(max(0, min(255, self.output_color_a))),
            ),
        )


def execute_color_shift_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Pipeline executor for color shift nodes.
    
    Applies color shifting to an input image and optionally returns a mask
    showing which pixels were changed.
    
    Args:
        node: Node dictionary containing:
            - All ColorShiftNodeConfig fields as node properties
            - 'output_mask': Whether to return mask (default True)
        inputs: Should contain exactly one element: the input PIL Image
        
    Returns:
        - If output_mask=True: Tuple of (shifted_image, change_mask)
        - If output_mask=False: Just shifted_image
        
    Raises:
        ValueError: If inputs list is empty or wrong size
        TypeError: If input is not a PIL Image
    """
    if not inputs or len(inputs) == 0:
        raise ValueError("Color shift node requires 1 input image")
    
    image = inputs[0]
    
    if not hasattr(image, "size") or not hasattr(image, "getpixel"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    # Parse configuration
    config_dict = {
        k: v for k, v in node.items()
        if k in ColorShiftNodeConfig.__dataclass_fields__
    }
    config = ColorShiftNodeConfig.from_dict(config_dict)
    
    # Create filter and apply
    filter_obj = ColorShiftFilter()
    base_color = config.get_base_color()
    options = config.get_filter_options()
    
    modified_image, mask = filter_obj.apply_color_shift_to_image(
        image,
        base_color,
        options,
        config.shift_amount,
    )
    
    if config.output_mask or node.get("output_mask", True):
        return (modified_image, mask)
    else:
        return modified_image


def create_color_shift_node(
    node_id: str,
    base_color: RgbaColor,
    shift_amount: float | Tuple[float, float, float],
    selection_type: SelectionType = "rgb_distance",
    shift_type: ShiftType = "absolute_rgb",
    tolerance: float = 30.0,
    distance_type: DistanceType = "euclidean",
    output_base_color: Optional[RgbaColor] = None,
    output_mask: bool = True,
) -> Dict[str, Any]:
    """
    Helper to create a color shift node dictionary for graph building.
    
    Args:
        node_id: Unique node identifier
        base_color: RGBA tuple for base color selection
        shift_amount: Amount to shift colors
        selection_type: Color selection method
        shift_type: Shift method
        tolerance: Tolerance for selection
        distance_type: Distance metric
        output_mask: Whether to output mask
        
    Returns:
        Node dictionary ready for graph serialization
    """
    r, g, b, a = base_color
    out_r, out_g, out_b, out_a = output_base_color if output_base_color is not None else base_color
    
    return {
        "id": node_id,
        "type": "Color Shift",
        "output_ports": ["image", "mask"],
        "base_color_r": r,
        "base_color_g": g,
        "base_color_b": b,
        "base_color_a": a,
        "selection_type": selection_type,
        "shift_type": shift_type,
        "tolerance": tolerance,
        "distance_type": distance_type,
        "shift_amount": shift_amount,
        "output_color_r": out_r,
        "output_color_g": out_g,
        "output_color_b": out_b,
        "output_color_a": out_a,
        "output_mask": output_mask,
    }
