"""
Blur Filter Operations and Blur Node.

Provides multiple blur algorithms:
- Gaussian blur: Natural smooth blur with circular falloff
- Motion blur: Directional blur with angle and distance
- Radial blur: Zoom blur from center point
- Box blur: Simple averaging blur

Example:
    >>> from PIL import Image
    >>> img = Image.open("photo.jpg")
    >>> 
    >>> # Gaussian blur
    >>> blurred = apply_gaussian_blur(img, radius=10)
    >>> 
    >>> # Motion blur with angle
    >>> motion = apply_motion_blur(img, angle=45, distance=20)
    >>> 
    >>> # Radial blur from center
    >>> radial = apply_radial_blur(img, center_x=400, center_y=300, strength=10)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageFilter
import math


# ============================================================================
# Gaussian Blur
# ============================================================================

def apply_gaussian_blur(
    image: Any,
    radius: float = 5.0,
) -> Any:
    """
    Apply Gaussian blur to image.
    
    Args:
        image: PIL Image
        radius: Blur radius in pixels (1-100, typical 1-50)
                Higher values = stronger blur
                
    Returns:
        Blurred PIL Image (same mode as input)
        
    Raises:
        ValueError: If radius <= 0 or > 100
        TypeError: If image not PIL Image
    """
    if not hasattr(image, "filter"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    if not (0 < radius <= 100):
        raise ValueError(f"radius must be 0 < r <= 100, got {radius}")
    
    # Convert to RGB/RGBA if needed (Gaussian blur works best with color)
    original_mode = image.mode
    if original_mode == "P":
        image = image.convert("RGB")
    
    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    return blurred


# ============================================================================
# Box Blur
# ============================================================================

def apply_box_blur(
    image: Any,
    kernel_size: int = 3,
) -> Any:
    """
    Apply box blur (averaging) to image.
    
    Args:
        image: PIL Image
        kernel_size: Size of blur kernel (must be odd, 1-101)
                    1 = no blur, 3 = light, 5-11 = moderate, 15+ = heavy
                    
    Returns:
        Blurred PIL Image (same mode as input)
        
    Raises:
        ValueError: If kernel_size invalid or > 101
        TypeError: If image not PIL Image
    """
    if not hasattr(image, "filter"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    # Ensure odd kernel size
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    if kernel_size < 1 or kernel_size > 101:
        raise ValueError(f"kernel_size must be 1-101 and odd, got {kernel_size}")
    
    original_mode = image.mode
    if original_mode == "P":
        image = image.convert("RGB")
    
    blurred = image.filter(ImageFilter.BoxBlur(kernel_size // 2))  # PIL uses radius
    return blurred


# ============================================================================
# Motion Blur
# ============================================================================

def apply_motion_blur(
    image: Any,
    angle: float = 0.0,
    distance: int = 10,
) -> Any:
    """
    Apply motion blur to image in specified direction.
    
    Args:
        image: PIL Image
        angle: Direction of blur in degrees (0-360)
               0 = horizontal right, 90 = vertical down, 180 = left, 270 = up
        distance: Length of motion blur in pixels (1-100)
        
    Returns:
        Motion blurred PIL Image (RGBA)
        
    Raises:
        ValueError: If distance invalid or > 100
        TypeError: If image not PIL Image
    """
    if not hasattr(image, "filter"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    if distance < 1 or distance > 100:
        raise ValueError(f"distance must be 1-100, got {distance}")
    
    # Ensure angle in 0-360 range
    angle = float(angle) % 360
    
    # Convert to RGBA for processing
    original_mode = image.mode
    if original_mode == "P":
        img = image.convert("RGBA")
    else:
        img = image.convert("RGBA")
    
    width, height = img.size
    
    # Create output image
    result = Image.new("RGBA", img.size)
    pixels_result = result.load()
    pixels_original = img.load()
    
    # Calculate motion vector components
    angle_rad = math.radians(angle)
    dx = math.cos(angle_rad)
    dy = math.sin(angle_rad)
    
    # For each output pixel, average pixels along motion direction
    for y in range(height):
        for x in range(width):
            r_sum = [0, 0, 0, 0]
            
            # Sample pixels along motion direction
            for step in range(distance):
                # Position along motion line
                sample_x = int(x + dx * (step - distance / 2))
                sample_y = int(y + dy * (step - distance / 2))
                
                # Bounds check
                if 0 <= sample_x < width and 0 <= sample_y < height:
                    pixel = pixels_original[sample_x, sample_y]
                    for i in range(4):
                        r_sum[i] += pixel[i]
                else:
                    # Use current pixel for out-of-bounds
                    pixel = pixels_original[x, y]
                    for i in range(4):
                        r_sum[i] += pixel[i]
            
            # Average samples
            avg_pixel = tuple(
                int(r_sum[i] / distance) for i in range(4)
            )
            pixels_result[x, y] = avg_pixel
    
    return result


# ============================================================================
# Radial/Zoom Blur
# ============================================================================

def apply_radial_blur(
    image: Any,
    center_x: Optional[int] = None,
    center_y: Optional[int] = None,
    strength: float = 5.0,
) -> Any:
    """
    Apply radial (zoom) blur emanating from center point.
    
    Creates zoom blur effect where pixels blur outward from a center.
    
    Args:
        image: PIL Image
        center_x: X coordinate of blur center (default: image width/2)
        center_y: Y coordinate of blur center (default: image height/2)
        strength: Blur strength (1-50, higher = stronger blur)
        
    Returns:
        Radial blurred PIL Image (RGBA)
        
    Raises:
        ValueError: If strength invalid
        TypeError: If image not PIL Image
    """
    if not hasattr(image, "tobytes"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    if strength < 1 or strength > 50:
        raise ValueError(f"strength must be 1-50, got {strength}")
    
    width, height = image.size
    
    # Default to center
    if center_x is None:
        center_x = width // 2
    if center_y is None:
        center_y = height // 2
    
    # Convert to RGBA for processing
    if image.mode != "RGBA":
        img_rgb = image.convert("RGBA")
    else:
        img_rgb = image.copy()
    
    # Create output image
    result = Image.new("RGBA", image.size)
    pixels_result = result.load()
    
    # Load pixels
    pixels_original = img_rgb.load()
    
    # For each output pixel, sample from multiple radii
    num_samples = int(strength)
    
    for y in range(height):
        for x in range(width):
            # Calculate distance and angle from center
            dx = x - center_x
            dy = y - center_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance < 0.1:
                # At center, just use original pixel
                pixels_result[x, y] = pixels_original[x, y]
                continue
            
            # Calculate angle
            angle = math.atan2(dy, dx)
            
            # Sample pixels along radii from center to edge
            r_sum = [0, 0, 0, 0]
            
            for sample_idx in range(num_samples):
                # Sample at different radii
                sample_distance = distance * (1.0 - (sample_idx / num_samples) * 0.5)
                
                # Convert back to coordinates
                sample_x = int(center_x + sample_distance * math.cos(angle))
                sample_y = int(center_y + sample_distance * math.sin(angle))
                
                # Bounds check
                if 0 <= sample_x < width and 0 <= sample_y < height:
                    pixel = pixels_original[sample_x, sample_y]
                    for i in range(4):
                        r_sum[i] += pixel[i]
            
            # Average samples
            avg_pixel = tuple(
                int(r_sum[i] / num_samples) for i in range(4)
            )
            pixels_result[x, y] = avg_pixel
    
    return result


# ============================================================================
# Blur Node Configuration
# ============================================================================

@dataclass
class BlurNodeConfig:
    """Configuration for blur node.
    
    Attributes:
        blur_type: Type of blur ('gaussian', 'box', 'motion', 'radial')
        gaussian_radius: Radius for Gaussian blur (0-100)
        box_kernel: Kernel size for box blur (1-101, must be odd)
        motion_angle: Angle for motion blur (0-360 degrees)
        motion_distance: Distance for motion blur (1-100 pixels)
        radial_center_x: X coordinate for radial blur center (or None for auto)
        radial_center_y: Y coordinate for radial blur center (or None for auto)
        radial_strength: Strength of radial blur (1-50)
    """
    blur_type: str = "gaussian"
    gaussian_radius: float = 5.0
    box_kernel: int = 3
    motion_angle: float = 0.0
    motion_distance: int = 10
    radial_center_x: Optional[int] = None
    radial_center_y: Optional[int] = None
    radial_strength: float = 5.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "blur_type": self.blur_type,
            "gaussian_radius": self.gaussian_radius,
            "box_kernel": self.box_kernel,
            "motion_angle": self.motion_angle,
            "motion_distance": self.motion_distance,
            "radial_center_x": self.radial_center_x,
            "radial_center_y": self.radial_center_y,
            "radial_strength": self.radial_strength,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlurNodeConfig":
        """Create from dictionary."""
        filtered = {k: v for k, v in data.items() 
                   if k in cls.__dataclass_fields__}
        return cls(**filtered)


def execute_blur_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Execute blur node.
    
    Node dict should contain:
        - 'blur_type': Type of blur ('gaussian', 'box', 'motion', 'radial')
        - Appropriate parameters for chosen blur type
        
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
    if not hasattr(image, "filter"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    blur_type = node.get("blur_type", "gaussian").lower()
    
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
        **blur_params: Blur-specific parameters:
                      - Gaussian: gaussian_radius (0-100)
                      - Box: box_kernel (1-101, odd)
                      - Motion: motion_angle (0-360), motion_distance (1-100)
                      - Radial: radial_center_x, radial_center_y, radial_strength (1-50)
        
    Returns:
        Node dict for graph
        
    Example:
        >>> # Gaussian blur
        >>> node1 = create_blur_node("blur-1", "gaussian", gaussian_radius=15)
        >>> 
        >>> # Motion blur
        >>> node2 = create_blur_node(
        ...     "blur-2",
        ...     "motion",
        ...     motion_angle=45,
        ...     motion_distance=30,
        ... )
        >>> 
        >>> # Radial blur
        >>> node3 = create_blur_node("blur-3", "radial", radial_strength=10)
    """
    node = {
        "id": node_id,
        "type": "Blur",
        "blur_type": blur_type,
    }
    
    # Add blur-specific parameters
    node.update(blur_params)
    return node
