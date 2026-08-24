"""
Multi-Layer Image Compositor Node.

Composites a base image with multiple overlay layers, each with optional masks,
alpha (transparency), and blend amounts. Uses standard alpha compositing.

Example:
    Creating a layer node at runtime:
    
    >>> base = Image.new("RGBA", (100, 100), "red")
    >>> overlay = Image.new("RGBA", (100, 100), "blue")
    >>> mask = Image.new("L", (100, 100), 128)  # semitransparent mask
    >>> layer_config = {
    ...     "base_image": base,
    ...     "layers": [
    ...         {
    ...             "image": overlay,
    ...             "mask": mask,
    ...             "alpha": 200,
    ...             "blend_amount": 0.8,
    ...         }
    ...     ]
    ... }
    >>> result = execute_image_layer_node(layer_config, [base])
"""

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from PIL import Image, ImageChops


@dataclass
class LayerInfo:
    """Configuration for a single layer in composition.
    
    Attributes:
        image: PIL Image for this layer (None if loading from path)
        image_path: Path to image file (used if image is None)
        mask: Optional PIL Image mask (L mode, 8-bit grayscale)
                8-bit values: 0=transparent, 255=opaque
        alpha: Layer opacity (0-255, where 255 is fully opaque)
        blend_amount: How much this layer contributes (0.0-1.0)
    """
    image: Optional[Any] = None
    image_path: Optional[str] = None
    mask: Optional[Any] = None
    alpha: int = 255
    blend_amount: float = 1.0
    
    def __post_init__(self):
        """Validate layer parameters."""
        if self.image is None and self.image_path is None:
            raise ValueError("LayerInfo must have either image or image_path")
        
        if not (0 <= self.alpha <= 255):
            raise ValueError(f"alpha must be 0-255, got {self.alpha}")
        
        if not (0.0 <= self.blend_amount <= 1.0):
            raise ValueError(f"blend_amount must be 0.0-1.0, got {self.blend_amount}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes image objects)."""
        data = asdict(self)
        # Remove actual image objects, keep paths
        data["image"] = None
        data["mask"] = None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayerInfo":
        """Create from dictionary."""
        # Filter out None image/mask
        filtered = {k: v for k, v in data.items() 
                   if k in cls.__dataclass_fields__}
        return cls(**filtered)


@dataclass
class ImageLayerNodeConfig:
    """Configuration for multi-layer image compositor node.
    
    Attributes:
        base_image: Base PIL Image to composite onto (can come from input)
        layers: List of LayerInfo objects for overlay layers
        blend_mode: Blending mode ('alpha' is only supported currently)
        output_mode: Output color mode ('RGBA' or 'RGB')
    """
    base_image: Optional[Any] = None
    layers: List[LayerInfo] = field(default_factory=list)
    blend_mode: str = "alpha"
    output_mode: str = "RGBA"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes image objects)."""
        return {
            "base_image": None,
            "layers": [layer.to_dict() for layer in self.layers],
            "blend_mode": self.blend_mode,
            "output_mode": self.output_mode,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageLayerNodeConfig":
        """Create from dictionary."""
        layers = [LayerInfo.from_dict(l) for l in data.get("layers", [])]
        return cls(
            base_image=None,
            layers=layers,
            blend_mode=data.get("blend_mode", "alpha"),
            output_mode=data.get("output_mode", "RGBA"),
        )


class ImageLayerCompositor:
    """Handles multi-layer image composition."""
    
    @staticmethod
    def composite_layers(
        base_image: Any,
        layers: List[LayerInfo],
        blend_mode: str = "alpha",
    ) -> Any:
        """
        Composite multiple layers onto base image.
        
        Args:
            base_image: PIL Image to use as base (converted to RGBA)
            layers: List of LayerInfo objects to composite
            blend_mode: Blending algorithm ('alpha' only currently)
            
        Returns:
            Composited PIL Image in RGBA mode
            
        Raises:
            ValueError: If blend_mode unsupported or layer invalid
            TypeError: If inputs are not PIL Images
        """
        if not hasattr(base_image, "mode"):
            raise TypeError(f"Expected PIL Image for base, got {type(base_image)}")
        
        if blend_mode != "alpha":
            raise ValueError(f"Unsupported blend_mode: {blend_mode}")
        
        # Ensure base is RGBA
        result = base_image.convert("RGBA")
        
        # Composite each layer
        for layer_idx, layer in enumerate(layers):
            result = ImageLayerCompositor._composite_single_layer(
                result, layer, layer_idx
            )
        
        return result
    
    @staticmethod
    def _composite_single_layer(
        base: Any,
        layer: LayerInfo,
        layer_idx: int,
    ) -> Any:
        """
        Composite a single layer onto base image.
        
        Args:
            base: Current composite (RGBA PIL Image)
            layer: LayerInfo for this layer
            layer_idx: Index of layer (for error messages)
            
        Returns:
            Updated composite (RGBA PIL Image)
        """
        # Get layer image
        if layer.image is not None:
            overlay = layer.image
        elif layer.image_path is not None:
            from OV_Libs.NodesLib.image_import_node import execute_import_image_node
            # Create minimal node config for importing
            import_node = {
                "id": f"layer-{layer_idx}-import",
                "image_path": layer.image_path,
            }
            try:
                overlay = execute_import_image_node(import_node, [])
            except Exception as e:
                raise ValueError(
                    f"Failed to load layer {layer_idx} image from "
                    f"{layer.image_path}: {str(e)}"
                )
        else:
            raise ValueError(f"Layer {layer_idx} has no image or image_path")
        
        # Validate overlay is PIL Image
        if not hasattr(overlay, "convert"):
            raise TypeError(
                f"Layer {layer_idx} image is not PIL Image, got {type(overlay)}"
            )
        
        # Ensure overlay is RGBA
        overlay = overlay.convert("RGBA")
        
        # Ensure base and overlay same size
        if base.size != overlay.size:
            overlay = overlay.resize(base.size, Image.Resampling.LANCZOS)
        
        # Apply mask if provided
        if layer.mask is not None:
            if not hasattr(layer.mask, "mode"):
                raise TypeError(f"Layer {layer_idx} mask is not PIL Image")
            
            mask = layer.mask.convert("L")
            if mask.size != overlay.size:
                mask = mask.resize(overlay.size, Image.Resampling.LANCZOS)
            
            # Apply mask to overlay alpha channel
            overlay = ImageLayerCompositor._apply_mask_to_alpha(overlay, mask)
        
        # Apply alpha (transparency)
        if layer.alpha < 255:
            overlay = ImageLayerCompositor._apply_alpha_to_image(overlay, layer.alpha)
        
        # Apply blend amount (0.0-1.0 controls opacity contribution)
        if layer.blend_amount < 1.0:
            overlay = ImageLayerCompositor._apply_blend_amount(
                overlay, layer.blend_amount
            )
        
        # Alpha composite: overlay onto base
        result = Image.alpha_composite(base, overlay)
        return result
    
    @staticmethod
    def _apply_mask_to_alpha(image: Any, mask: Any) -> Any:
        """
        Apply grayscale mask to image's alpha channel.
        
        Args:
            image: RGBA PIL Image
            mask: L (grayscale) PIL Image where 255=opaque, 0=transparent
            
        Returns:
            RGBA PIL Image with mask applied to alpha
        """
        # Get current RGBA bands
        r, g, b, a = image.split()

        # Combine current alpha with mask using native image multiplication
        # new_alpha ≈ current_alpha * (mask / 255.0)
        mask_scaled = mask.convert("L")
        new_alpha = ImageChops.multiply(a, mask_scaled)

        # Reconstruct image
        return Image.merge("RGBA", (r, g, b, new_alpha))
    
    @staticmethod
    def _apply_alpha_to_image(image: Any, alpha: int) -> Any:
        """
        Apply uniform alpha (opacity) to entire image.
        
        Args:
            image: RGBA PIL Image
            alpha: Opacity value (0-255)
            
        Returns:
            RGBA PIL Image with alpha applied
        """
        r, g, b, a = image.split()

        # Scale existing alpha by new alpha with a lookup table
        # new_a = a * (alpha / 255.0)
        alpha_scale = alpha / 255.0
        lut = [int(value * alpha_scale) for value in range(256)]
        new_alpha = a.point(lut)

        return Image.merge("RGBA", (r, g, b, new_alpha))
    
    @staticmethod
    def _apply_blend_amount(image: Any, blend_amount: float) -> Any:
        """
        Apply blend amount (0.0-1.0) to control layer opacity contribution.
        
        Args:
            image: RGBA PIL Image
            blend_amount: Blending factor (0.0=invisible, 1.0=full opacity)
            
        Returns:
            RGBA PIL Image with blend amount applied to alpha
        """
        r, g, b, a = image.split()

        # Scale alpha by blend amount with a lookup table: new_a = a * blend_amount
        lut = [int(value * blend_amount) for value in range(256)]
        new_alpha = a.point(lut)

        return Image.merge("RGBA", (r, g, b, new_alpha))


def execute_image_layer_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Execute image layer composition node.
    
    Inputs:
        - [0]: Base image (PIL Image from previous node)
        - [1..n]: Layer images (PIL Images, optional - only connected layers are used)
        
    Returns:
        Composited PIL Image (RGBA mode)
        
    Raises:
        ValueError: If no base image or invalid layer configuration
        TypeError: If base image not PIL Image
    """
    if not inputs or len(inputs) < 1:
        raise ValueError("ImageLayerNode requires base image as first input")
    
    base_image = inputs[0]
    if not hasattr(base_image, "mode"):
        raise TypeError(f"Expected PIL Image for base, got {type(base_image)}")
    
    # If no layer inputs connected, just return the base image
    if len(inputs) < 2:
        return base_image.convert("RGBA")
    
    # Convert input images to LayerInfo objects
    # Each connected input port (after base) becomes a layer with default settings
    layers = []
    for layer_idx, layer_image in enumerate(inputs[1:], start=1):
        if layer_image is None:
            # Skip unconnected ports
            continue
        
        if not hasattr(layer_image, "mode"):
            raise TypeError(
                f"Layer {layer_idx} input is not a PIL Image, got {type(layer_image)}"
            )
        
        # Create LayerInfo with connected image
        # Use defaults: alpha=255 (fully opaque), blend_amount=1.0 (full contribution)
        layer_info = LayerInfo(
            image=layer_image,
            alpha=255,
            blend_amount=1.0,
        )
        layers.append(layer_info)
    
    blend_mode = node.get("blend_mode", "alpha")
    
    # Composite all layers onto base
    result = ImageLayerCompositor.composite_layers(
        base_image, layers, blend_mode
    )
    
    return result


def create_image_layer_node(
    node_id: str,
    blend_mode: str = "alpha",
    output_mode: str = "RGBA",
) -> Dict[str, Any]:
    """
    Create image layer composition node for graph.
    
    Args:
        node_id: Unique node identifier
        blend_mode: Blending algorithm ('alpha' only currently)
        output_mode: Output image mode ('RGBA' or 'RGB')
        
    Returns:
        Node dict for graph
        
    Note:
        Layers are provided via input ports (inputs[1:]), not parameters.
        - inputs[0] = base image
        - inputs[1..8] = layer images from ports
        
    Example:
        >>> # Create layer composition node
        >>> node = create_image_layer_node("compositor-1")
        >>> # In the graph, connect:
        >>> # - Base image output → base_image input port
        >>> # - Layer 1 output → layer_1 input port
        >>> # - Layer 2 output → layer_2 input port
        >>> # etc
    """
    return {
        "id": node_id,
        "type": "Image Layer",
        "blend_mode": blend_mode,
        "output_mode": output_mode,
    }
