"""
Tests for Image Layer Compositor Node.

Tests cover:
- Layer configuration
- Single and multi-layer compositing
- Mask application
- Alpha and blend amount application
- Image loading from paths
- Error handling
- Node registration
"""

import tempfile
import unittest
from pathlib import Path
from PIL import Image

from OV_Libs.NodesLib.image_layer_node import (
    LayerInfo,
    ImageLayerNodeConfig,
    ImageLayerCompositor,
    execute_image_layer_node,
    create_image_layer_node,
)
from OV_Libs.ProjStoreLib.node_executors import get_default_registry


class TestLayerInfo(unittest.TestCase):
    """Test LayerInfo configuration."""
    
    def test_create_with_image(self):
        """Test creating layer with PIL Image."""
        img = Image.new("RGBA", (50, 50), "blue")
        layer = LayerInfo(image=img, alpha=200)
        
        self.assertEqual(layer.image, img)
        self.assertEqual(layer.alpha, 200)
        self.assertEqual(layer.blend_amount, 1.0)
    
    def test_create_with_path(self):
        """Test creating layer with image path."""
        layer = LayerInfo(image_path="/path/to/image.png")
        
        self.assertIsNone(layer.image)
        self.assertEqual(layer.image_path, "/path/to/image.png")
    
    def test_requires_image_or_path(self):
        """Test that layer requires image or path."""
        with self.assertRaises(ValueError):
            LayerInfo()
    
    def test_validate_alpha_range(self):
        """Test alpha validation."""
        with self.assertRaises(ValueError):
            LayerInfo(image=Image.new("RGBA", (10, 10)), alpha=256)
        
        with self.assertRaises(ValueError):
            LayerInfo(image=Image.new("RGBA", (10, 10)), alpha=-1)
    
    def test_validate_blend_range(self):
        """Test blend_amount validation."""
        with self.assertRaises(ValueError):
            LayerInfo(image=Image.new("RGBA", (10, 10)), blend_amount=1.5)
        
        with self.assertRaises(ValueError):
            LayerInfo(image=Image.new("RGBA", (10, 10)), blend_amount=-0.1)
    
    def test_to_dict(self):
        """Test converting layer to dict."""
        img = Image.new("RGBA", (50, 50), "red")
        layer = LayerInfo(image=img, alpha=150, blend_amount=0.7)
        
        data = layer.to_dict()
        
        self.assertIsNone(data["image"])
        self.assertIsNone(data["mask"])
        self.assertEqual(data["alpha"], 150)
        self.assertEqual(data["blend_amount"], 0.7)
    
    def test_from_dict(self):
        """Test creating layer from dict."""
        data = {
            "image": None,
            "image_path": "/path/image.png",
            "alpha": 180,
            "blend_amount": 0.9,
        }
        
        layer = LayerInfo.from_dict(data)
        
        self.assertEqual(layer.image_path, "/path/image.png")
        self.assertEqual(layer.alpha, 180)
        self.assertEqual(layer.blend_amount, 0.9)


class TestImageLayerNodeConfig(unittest.TestCase):
    """Test ImageLayerNodeConfig."""
    
    def test_config_creation_default(self):
        """Test creating config with defaults."""
        config = ImageLayerNodeConfig()
        
        self.assertEqual(len(config.layers), 0)
        self.assertEqual(config.blend_mode, "alpha")
        self.assertEqual(config.output_mode, "RGBA")
    
    def test_config_with_layers(self):
        """Test creating config with layers."""
        layer1 = LayerInfo(image=Image.new("RGBA", (100, 100)))
        layer2 = LayerInfo(image=Image.new("RGBA", (100, 100)), alpha=150)
        
        config = ImageLayerNodeConfig(layers=[layer1, layer2])
        
        self.assertEqual(len(config.layers), 2)
        self.assertEqual(config.layers[1].alpha, 150)
    
    def test_config_to_dict(self):
        """Test converting config to dict."""
        layer = LayerInfo(image=Image.new("RGBA", (50, 50)), alpha=200)
        config = ImageLayerNodeConfig(layers=[layer])
        
        data = config.to_dict()
        
        self.assertIsNone(data["base_image"])
        self.assertEqual(len(data["layers"]), 1)
        self.assertEqual(data["blend_mode"], "alpha")
    
    def test_config_from_dict(self):
        """Test creating config from dict."""
        data = {
            "layers": [
                {"image_path": "/img1.png", "alpha": 200},
            ],
            "blend_mode": "alpha",
            "output_mode": "RGBA",
        }
        
        config = ImageLayerNodeConfig.from_dict(data)
        
        self.assertEqual(len(config.layers), 1)
        self.assertEqual(config.layers[0].alpha, 200)


class TestImageLayerCompositor(unittest.TestCase):
    """Test image layer compositing."""
    
    def setUp(self):
        """Create test images."""
        self.base = Image.new("RGBA", (100, 100), "red")
        self.overlay = Image.new("RGBA", (100, 100), "blue")
        self.overlay_semi = Image.new("RGBA", (100, 100), (0, 0, 255, 128))
    
    def test_composite_no_layers(self):
        """Test compositing with no layers."""
        result = ImageLayerCompositor.composite_layers(self.base, [])
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.base.size)
    
    def test_composite_single_layer(self):
        """Test compositing single layer."""
        layer = LayerInfo(image=self.overlay)
        result = ImageLayerCompositor.composite_layers(self.base, [layer])
        
        self.assertEqual(result.mode, "RGBA")
        # Result should be predominantly blue (overlay on top)
        pixel = result.getpixel((50, 50))
        self.assertGreater(pixel[2], pixel[0])  # Blue > Red
    
    def test_composite_multiple_layers(self):
        """Test compositing multiple layers."""
        layer1 = LayerInfo(image=self.overlay)
        layer2 = LayerInfo(image=self.overlay_semi)
        
        result = ImageLayerCompositor.composite_layers(
            self.base, [layer1, layer2]
        )
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.base.size)
    
    def test_composite_with_alpha(self):
        """Test alpha application."""
        layer = LayerInfo(image=self.overlay, alpha=128)
        result = ImageLayerCompositor.composite_layers(self.base, [layer])
        
        # Result should be a blend of red and blue
        pixel = result.getpixel((50, 50))
        # Should have both red and blue components (blend)
        self.assertGreater(pixel[0], 0)  # Some red
        self.assertGreater(pixel[2], 0)  # Some blue
    
    def test_composite_with_blend_amount(self):
        """Test blend_amount application."""
        layer = LayerInfo(image=self.overlay, blend_amount=0.5)
        result = ImageLayerCompositor.composite_layers(self.base, [layer])
        
        self.assertEqual(result.mode, "RGBA")
        # Result should be blend of red and blue
        pixel = result.getpixel((50, 50))
        self.assertGreater(pixel[0], 0)
        self.assertGreater(pixel[2], 0)
    
    def test_composite_with_mask(self):
        """Test mask application."""
        # Create half-opaque mask (left half opaque, right half transparent)
        mask = Image.new("L", (100, 100), 0)
        mask.paste(255, (0, 0, 50, 100))
        
        layer = LayerInfo(image=self.overlay, mask=mask)
        result = ImageLayerCompositor.composite_layers(self.base, [layer])
        
        # Left side should be more blue, right side should be more red
        pixel_left = result.getpixel((25, 50))
        pixel_right = result.getpixel((75, 50))
        
        # Left should be bluer
        self.assertGreater(pixel_left[2], pixel_left[0])
        # Right should be redder
        self.assertGreater(pixel_right[0], pixel_right[2])
    
    def test_composite_resizes_mismatched_overlay(self):
        """Test that mismatched overlay sizes are handled."""
        small_overlay = Image.new("RGBA", (50, 50), "green")
        layer = LayerInfo(image=small_overlay)
        
        result = ImageLayerCompositor.composite_layers(self.base, [layer])
        
        self.assertEqual(result.size, self.base.size)
    
    def test_composite_resizes_mismatched_mask(self):
        """Test that mismatched mask sizes are handled."""
        small_mask = Image.new("L", (50, 50), 200)
        layer = LayerInfo(image=self.overlay, mask=small_mask)
        
        result = ImageLayerCompositor.composite_layers(self.base, [layer])
        
        self.assertEqual(result.size, self.base.size)
    
    def test_composite_invalid_base_type(self):
        """Test error on invalid base type."""
        with self.assertRaises(TypeError):
            ImageLayerCompositor.composite_layers("not_an_image", [])
    
    def test_composite_invalid_blend_mode(self):
        """Test error on unsupported blend mode."""
        with self.assertRaises(ValueError):
            ImageLayerCompositor.composite_layers(self.base, [], "multiply")
    
    def test_composite_invalid_layer_image_type(self):
        """Test error on invalid layer image type."""
        layer = LayerInfo(image="not_an_image")
        
        with self.assertRaises(TypeError):
            ImageLayerCompositor.composite_layers(self.base, [layer])


class TestImageLayerNodeExecutor(unittest.TestCase):
    """Test image layer node executor."""
    
    def setUp(self):
        """Create test images."""
        self.base = Image.new("RGBA", (100, 100), "red")
        self.overlay = Image.new("RGBA", (100, 100), "blue")
    
    def test_execute_no_layers(self):
        """Test execution with no layers."""
        node = {"id": "layer-1", "layers": []}
        result = execute_image_layer_node(node, [self.base])
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.base.size)
    
    def test_execute_with_layers(self):
        """Test execution with layers."""
        node = {
            "id": "layer-1",
            "layers": [
                {"image": self.overlay, "alpha": 200, "blend_amount": 1.0}
            ],
        }
        
        result = execute_image_layer_node(node, [self.base])
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.base.size)
    
    def test_execute_missing_base(self):
        """Test error on missing base image."""
        node = {"id": "layer-1"}
        
        with self.assertRaises(ValueError):
            execute_image_layer_node(node, [])
    
    def test_execute_invalid_base_type(self):
        """Test error on invalid base type."""
        node = {"id": "layer-1"}
        
        with self.assertRaises(TypeError):
            execute_image_layer_node(node, ["not_an_image"])
    
    def test_execute_with_dict_layers(self):
        """Test execution with layer dicts."""
        node = {
            "id": "layer-1",
            "layers": [
                {"image": self.overlay, "alpha": 150},
            ],
        }
        
        result = execute_image_layer_node(node, [self.base])
        
        self.assertIsNotNone(result)
        self.assertEqual(result.mode, "RGBA")
    
    def test_execute_converts_rgb_base_to_rgba(self):
        """Test that RGB base is converted to RGBA."""
        rgb_base = Image.new("RGB", (100, 100), "red")
        node = {"id": "layer-1", "layers": []}
        
        result = execute_image_layer_node(node, [rgb_base])
        
        self.assertEqual(result.mode, "RGBA")


class TestImageLayerFactory(unittest.TestCase):
    """Test create_image_layer_node helper."""
    
    def test_create_simple_node(self):
        """Test creating simple layer node."""
        node = create_image_layer_node("layer-1")
        
        self.assertEqual(node["id"], "layer-1")
        self.assertEqual(node["type"], "Image Layer")
        self.assertEqual(len(node["layers"]), 0)
    
    def test_create_with_layers(self):
        """Test creating node with layers."""
        img = Image.new("RGBA", (50, 50), "blue")
        node = create_image_layer_node(
            "layer-1",
            layers=[{"image": img, "alpha": 200}],
        )
        
        self.assertEqual(len(node["layers"]), 1)
        self.assertEqual(node["layers"][0]["alpha"], 200)
    
    def test_create_with_custom_modes(self):
        """Test creating node with custom modes."""
        node = create_image_layer_node(
            "layer-1",
            blend_mode="alpha",
            output_mode="RGB",
        )
        
        self.assertEqual(node["blend_mode"], "alpha")
        self.assertEqual(node["output_mode"], "RGB")


class TestImageLayerRegistry(unittest.TestCase):
    """Test Image Layer node is registered."""
    
    def test_layer_registered(self):
        """Test that Image Layer node is registered."""
        registry = get_default_registry()
        
        self.assertTrue(registry.has_executor("Image Layer"))
    
    def test_layer_metadata(self):
        """Test Image Layer node metadata."""
        registry = get_default_registry()
        meta = registry.get_metadata("Image Layer")
        
        self.assertEqual(meta["input_count"], 1)
        self.assertEqual(meta["output_count"], 1)
        self.assertIn("composition", meta["tags"])
    
    def test_execute_through_registry(self):
        """Test executing Image Layer node through registry."""
        registry = get_default_registry()
        base = Image.new("RGBA", (100, 100), "red")
        overlay = Image.new("RGBA", (100, 100), "blue")
        
        node = {
            "id": "layer-registry",
            "layers": [{"image": overlay, "alpha": 200}],
        }
        
        result = registry.execute("Image Layer", node, [base])
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, base.size)


class TestImageLayerIntegration(unittest.TestCase):
    """Integration tests for multi-layer compositing."""
    
    def test_three_layer_composition(self):
        """Test compositing three layers."""
        base = Image.new("RGBA", (100, 100), "red")
        layer1 = Image.new("RGBA", (100, 100), (0, 255, 0, 150))
        layer2 = Image.new("RGBA", (100, 100), (0, 0, 255, 100))
        
        node = {
            "id": "multilayer",
            "layers": [
                {"image": layer1, "alpha": 200, "blend_amount": 0.8},
                {"image": layer2, "alpha": 150, "blend_amount": 0.6},
            ],
        }
        
        result = execute_image_layer_node(node, [base])
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, base.size)
        # Should have all three colors blended
        pixel = result.getpixel((50, 50))
        self.assertGreater(pixel[0], 0)  # Red from base
        self.assertGreater(pixel[1], 0)  # Green from layer1
        self.assertGreater(pixel[2], 0)  # Blue from layer2
    
    def test_masking_layers(self):
        """Test compositing with masks on multiple layers."""
        base = Image.new("RGBA", (100, 100), "white")
        overlay1 = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        overlay2 = Image.new("RGBA", (100, 100), (0, 255, 0, 255))
        
        # Masks to create regions
        mask1 = Image.new("L", (100, 100), 0)
        mask1_pixels = [255 if i % 100 < 50 else 0 for i in range(10000)]
        mask1.putdata(mask1_pixels)
        
        mask2 = Image.new("L", (100, 100), 0)
        mask2_pixels = [255 if i % 100 >= 50 else 0 for i in range(10000)]
        mask2.putdata(mask2_pixels)
        
        node = {
            "id": "masked-layers",
            "layers": [
                {"image": overlay1, "mask": mask1},
                {"image": overlay2, "mask": mask2},
            ],
        }
        
        result = execute_image_layer_node(node, [base])
        
        self.assertEqual(result.mode, "RGBA")
        # Left side should be red, right side should be green
        pixel_left = result.getpixel((25, 50))
        pixel_right = result.getpixel((75, 50))
        
        self.assertGreater(pixel_left[0], pixel_left[1])  # Red > Green
        self.assertGreater(pixel_right[1], pixel_right[0])  # Green > Red


if __name__ == "__main__":
    unittest.main()
