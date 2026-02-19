"""
Blur Node for Open Vision Pipeline.

Wraps the blur filter operations for use in the node graph system.
Supports Gaussian, Box, Motion, and Radial blur algorithms.

Example:
    Creating a blur node:
    
    >>> from PIL import Image
    >>> from OV_Libs.NodesLib.blur_node import create_blur_node
    >>> from OV_Libs.ProjStoreLib.node_executors import get_default_registry
    >>> 
    >>> # Create Gaussian blur node
    >>> blur_node = create_blur_node(
    ...     "blur-1",
    ...     blur_type="gaussian",
    ...     gaussian_radius=10
    ... )
    >>> 
    >>> # Execute through registry
    >>> registry = get_default_registry()
    >>> image = Image.open("photo.jpg")
    >>> result = registry.execute("Blur", blur_node, [image])
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from OV_Libs.ImageEditingLib.blur_filter import (
    apply_gaussian_blur,
    apply_box_blur,
    apply_motion_blur,
    apply_radial_blur,
    BlurNodeConfig,
)


def execute_blur_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Execute blur node in pipeline.
    
    Node dict should contain:
        - 'blur_type': Type of blur ('gaussian', 'box', 'motion', 'radial')
        - Blur-specific parameters (e.g., gaussian_radius, motion_angle, etc.)
        
    Inputs:
        - [0]: Image to blur (PIL Image)
        
    Returns:
        Blurred PIL Image
        
    Raises:
        ValueError: If no input or invalid blur type
        TypeError: If input not PIL Image
    """
    if not inputs or len(inputs) < 1:
        raise ValueError("BlurNode requires image input")
    
    image = inputs[0]
    if not hasattr(image, "filter") and not hasattr(image, "tobytes"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    blur_type = node.get("blur_type", "gaussian").lower()
    
    try:
        if blur_type == "gaussian":
            radius = float(node.get("gaussian_radius", 5.0))
            return apply_gaussian_blur(image, radius)
        
        elif blur_type == "box":
            kernel = int(node.get("box_kernel", 3))
            return apply_box_blur(image, kernel)
        
        elif blur_type == "motion":
            angle = float(node.get("motion_angle", 0.0))
            distance = int(node.get("motion_distance", 10))
            return apply_motion_blur(image, angle, distance)
        
        elif blur_type == "radial":
            center_x = node.get("radial_center_x")
            center_y = node.get("radial_center_y")
            strength = float(node.get("radial_strength", 5.0))
            return apply_radial_blur(image, center_x, center_y, strength)
        
        else:
            raise ValueError(
                f"Unknown blur_type: {blur_type}. "
                f"Valid types: gaussian, box, motion, radial"
            )
    except (ValueError, TypeError) as e:
        raise type(e)(f"Blur node error: {str(e)}")


def create_blur_node(
    node_id: str,
    blur_type: str = "gaussian",
    **blur_params: Any,
) -> Dict[str, Any]:
    """
    Create blur node for graph.
    
    Args:
        node_id: Unique node identifier
        blur_type: Type of blur ('gaussian', 'box', 'motion', 'radial')
        **blur_params: Blur-specific parameters
        
    Returns:
        Node dict for graph
        
    Blur Parameters by Type:
    
        **Gaussian Blur:**
        - gaussian_radius (float): 0-100, typical 1-50
          * 1-5: light blur
          * 5-15: moderate blur
          * 15+: strong blur
        
        **Box Blur:**
        - box_kernel (int): 1-101 (must be odd)
          * 1: no blur
          * 3: very light
          * 5-11: light to moderate
          * 15+: moderate to strong
        
        **Motion Blur:**
        - motion_angle (float): 0-360 degrees
          * 0: horizontal right
          * 45: diagonal
          * 90: vertical down
          * 180: horizontal left
          * 270: vertical up
        - motion_distance (int): 1-100 pixels
        
        **Radial/Zoom Blur:**
        - radial_center_x (int): X coordinate (None = auto center)
        - radial_center_y (int): Y coordinate (None = auto center)
        - radial_strength (float): 1-50 (higher = stronger blur)
        
    Examples:
        >>> # Light Gaussian blur
        >>> node1 = create_blur_node("blur-1", "gaussian", gaussian_radius=5)
        >>> 
        >>> # Strong motion blur at 45 degrees
        >>> node2 = create_blur_node(
        ...     "blur-2",
        ...     "motion",
        ...     motion_angle=45,
        ...     motion_distance=50,
        ... )
        >>> 
        >>> # Box blur (light)
        >>> node3 = create_blur_node("blur-3", "box", box_kernel=5)
        >>> 
        >>> # Radial blur from center
        >>> node4 = create_blur_node("blur-4", "radial", radial_strength=15)
    """
    node = {
        "id": node_id,
        "type": "Blur",
        "blur_type": blur_type,
    }
    
    # Add blur-specific parameters
    node.update(blur_params)
    
    return node
