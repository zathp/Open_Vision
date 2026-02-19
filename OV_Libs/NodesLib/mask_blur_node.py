"""
Mask-Based (Local) Blur Filter and Mask Blur Node.

Applies spatially-varying blur where each pixel's blur strength is determined
by an RGBA strength map image. Each channel of the strength map controls blur
for the corresponding image channel.

Example:
    >>> from PIL import Image
    >>> image = Image.open("photo.jpg").convert("RGBA")
    >>> strength_map = Image.open("blur_strength.png").convert("RGBA")
    >>> 
    >>> # Apply mask-based Gaussian blur
    >>> result = apply_mask_blur(
    ...     image,
    ...     strength_map,
    ...     blur_type="gaussian",
    ...     max_radius=25.0,
    ... )
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from PIL import Image, ImageFilter
import math


def apply_mask_blur(
    image: Any,
    strength_map: Any,
    blur_type: str = "gaussian",
    max_radius: float = 25.0,
) -> Any:
    """
    Apply spatially-varying blur based on strength map.
    
    Each channel of the strength_map image (0-255) determines how much blur
    is applied to that channel at each pixel. 0 = no blur, 255 = max blur.
    
    Args:
        image: PIL Image to blur (converted to RGBA)
        strength_map: PIL Image with blur strength for each channel (0-255)
                     Converted to RGBA. Same size as image or auto-resized.
        blur_type: Type of blur ("gaussian" or "box")
        max_radius: Maximum blur radius in pixels (1-100)
                   Actual radius = (channel_value / 255.0) * max_radius
                   
    Returns:
        Blurred PIL Image (RGBA mode)
        
    Raises:
        ValueError: If max_radius invalid
        TypeError: If inputs not PIL Images
    """
    if not hasattr(image, "mode"):
        raise TypeError(f"Expected PIL Image for image, got {type(image)}")
    
    if not hasattr(strength_map, "mode"):
        raise TypeError(f"Expected PIL Image for strength_map, got {type(strength_map)}")
    
    if max_radius < 1 or max_radius > 100:
        raise ValueError(f"max_radius must be 1-100, got {max_radius}")
    
    # Convert to RGBA
    img = image.convert("RGBA")
    strength = strength_map.convert("RGBA")
    
    # Ensure same size
    if strength.size != img.size:
        strength = strength.resize(img.size, Image.Resampling.LANCZOS)
    
    width, height = img.size
    
    # Get pixel data
    img_pixels = img.load()
    strength_pixels = strength.load()
    
    # For efficiency, pre-blur the image at different radii
    # Then blend based on strength map
    
    if blur_type.lower() == "gaussian":
        # Create output for Gaussian blur
        result = Image.new("RGBA", (width, height))
        result_pixels = result.load()
        
        for y in range(height):
            for x in range(width):
                strength_rgba = strength_pixels[x, y]
                radii = [
                    int((strength_rgba[i] / 255.0) * max_radius)
                    for i in range(4)
                ]
                
                blurred_channels = [0, 0, 0, 0]
                
                for channel_idx in range(4):
                    radius = radii[channel_idx]
                    
                    if radius == 0:
                        blurred_channels[channel_idx] = img_pixels[x, y][channel_idx]
                    else:
                        sample_sum = 0
                        sample_count = 0
                        
                        for dy in range(-radius, radius + 1):
                            for dx in range(-radius, radius + 1):
                                dist_sq = dx * dx + dy * dy
                                if dist_sq <= radius * radius:
                                    sample_x = x + dx
                                    sample_y = y + dy
                                    
                                    if 0 <= sample_x < width and 0 <= sample_y < height:
                                        pixel = img_pixels[sample_x, sample_y]
                                        sample_sum += pixel[channel_idx]
                                        sample_count += 1
                        
                        if sample_count > 0:
                            blurred_channels[channel_idx] = sample_sum // sample_count
                        else:
                            blurred_channels[channel_idx] = img_pixels[x, y][channel_idx]
                
                result_pixels[x, y] = tuple(blurred_channels)
        
        return result
    elif blur_type.lower() == "box":
        # Create output for box blur
        result = Image.new("RGBA", (width, height))
        result_pixels = result.load()
        
        for y in range(height):
            for x in range(width):
                strength_rgba = strength_pixels[x, y]
                radii = [
                    int((strength_rgba[i] / 255.0) * max_radius)
                    for i in range(4)
                ]
                
                blurred_channels = [0, 0, 0, 0]
                
                for channel_idx in range(4):
                    radius = radii[channel_idx]
                    
                    if radius == 0:
                        blurred_channels[channel_idx] = img_pixels[x, y][channel_idx]
                    else:
                        sample_sum = 0
                        sample_count = 0
                        
                        for dy in range(-radius, radius + 1):
                            for dx in range(-radius, radius + 1):
                                sample_x = x + dx
                                sample_y = y + dy
                                
                                if 0 <= sample_x < width and 0 <= sample_y < height:
                                    pixel = img_pixels[sample_x, sample_y]
                                    sample_sum += pixel[channel_idx]
                                    sample_count += 1
                        
                        if sample_count > 0:
                            blurred_channels[channel_idx] = sample_sum // sample_count
                        else:
                            blurred_channels[channel_idx] = img_pixels[x, y][channel_idx]
                
                result_pixels[x, y] = tuple(blurred_channels)
        
        return result
    else:
        raise ValueError(f"Unknown blur_type: {blur_type}")


@dataclass
class MaskBlurNodeConfig:
    """Configuration for mask-based blur node.
    
    Attributes:
        blur_type: Type of blur ('gaussian' or 'box')
        max_radius: Maximum blur radius in pixels (1-100)
    """
    blur_type: str = "gaussian"
    max_radius: float = 25.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "blur_type": self.blur_type,
            "max_radius": self.max_radius,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaskBlurNodeConfig":
        """Create from dictionary."""
        filtered = {k: v for k, v in data.items() 
                   if k in cls.__dataclass_fields__}
        return cls(**filtered)


def execute_mask_blur_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Execute mask blur node in pipeline.
    
    Node dict should contain:
        - 'blur_type': Type of blur ('gaussian' or 'box')
        - 'max_radius': Maximum blur radius (1-100)
        
    Inputs:
        - [0]: Image to blur (PIL Image)
        - [1]: Strength map image (PIL Image, RGBA)
        
    Returns:
        Blurred PIL Image (RGBA mode)
        
    Raises:
        ValueError: If invalid inputs or parameters
        TypeError: If inputs not PIL Images
    """
    if not inputs or len(inputs) < 2:
        raise ValueError(
            "MaskBlurNode requires 2 inputs: image and strength_map"
        )
    
    image = inputs[0]
    strength_map = inputs[1]
    
    if not hasattr(image, "mode"):
        raise TypeError(f"Expected PIL Image for image input, got {type(image)}")
    
    if not hasattr(strength_map, "mode"):
        raise TypeError(
            f"Expected PIL Image for strength_map input, got {type(strength_map)}"
        )
    
    blur_type = node.get("blur_type", "gaussian")
    max_radius = float(node.get("max_radius", 25.0))
    
    try:
        result = apply_mask_blur(
            image, strength_map, blur_type, max_radius
        )
        return result
    except (ValueError, TypeError) as e:
        raise type(e)(f"Mask blur node error: {str(e)}")


def create_mask_blur_node(
    node_id: str,
    blur_type: str = "gaussian",
    max_radius: float = 25.0,
) -> Dict[str, Any]:
    """
    Create mask-based blur node for graph.
    
    Args:
        node_id: Unique node identifier
        blur_type: Type of blur ('gaussian' or 'box')
        max_radius: Maximum blur radius in pixels (1-100)
        
    Returns:
        Node dict for graph
        
    Inputs:
        - [0]: Image to blur (PIL Image)
        - [1]: Strength map (RGBA image, 0-255 per channel)
        
    Example:
        >>> # Create mask blur node with Gaussian
        >>> node = create_mask_blur_node(
        ...     "mask-blur-1",
        ...     blur_type="gaussian",
        ...     max_radius=30
        ... )
        >>> 
        >>> # Use in pipeline
        >>> result = registry.execute("Mask Blur", node, [image, strength_map])
    """
    return {
        "id": node_id,
        "type": "Mask Blur",
        "blur_type": blur_type,
        "max_radius": max_radius,
    }
