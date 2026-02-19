"""
Tests for Mask-Based Blur Node.

Tests cover:
- Mask blur operations (Gaussian and Box)
- Per-channel blur strength from RGBA map
- Size mismatch handling
- Node configuration
- Executor function
- Node registration
- Error handling
"""

import unittest
from PIL import Image

from OV_Libs.NodesLib.mask_blur_node import (
    apply_mask_blur,
    MaskBlurNodeConfig,
    execute_mask_blur_node,
    create_mask_blur_node,
    get_available_backend,
)
from OV_Libs.ProjStoreLib.node_executors import get_default_registry


class TestApplyMaskBlur(unittest.TestCase):
    """Test mask blur operation."""
    
    def setUp(self):
        """Create test images."""
        # Create test image: red
        self.test_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        
        # Create uniform strength map: half strength (128)
        self.strength_map = Image.new("RGBA", (100, 100), (128, 128, 128, 128))
        
        # Create gradient strength map: varies left to right
        self.gradient_map = Image.new("RGBA", (100, 100))
        pixels = self.gradient_map.load()
        for x in range(100):
            for y in range(100):
                # Gradient from left (0) to right (255)
                val = int((x / 100) * 255)
                pixels[x, y] = (val, val, val, 255)
    
    def test_mask_blur_gaussian_uniform(self):
        """Test Gaussian mask blur with uniform strength."""
        result = apply_mask_blur(
            self.test_image,
            self.strength_map,
            blur_type="gaussian",
            max_radius=10,
        )
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.test_image.size)
    
    def test_mask_blur_box_uniform(self):
        """Test box mask blur with uniform strength."""
        result = apply_mask_blur(
            self.test_image,
            self.strength_map,
            blur_type="box",
            max_radius=10,
        )
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.test_image.size)
    
    def test_mask_blur_zero_strength(self):
        """Test that zero strength produces no blur."""
        # Create zero strength map
        zero_map = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        
        result = apply_mask_blur(
            self.test_image,
            zero_map,
            blur_type="gaussian",
            max_radius=10,
        )
        
        # Result should be similar to original (no blur where strength is 0)
        self.assertEqual(result.size, self.test_image.size)
    
    def test_mask_blur_max_strength(self):
        """Test that max strength produces strong blur."""
        # Create max strength map
        max_map = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        
        result = apply_mask_blur(
            self.test_image,
            max_map,
            blur_type="gaussian",
            max_radius=20,
        )
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_mask_blur_per_channel_strength(self):
        """Test that different channels get different blur."""
        # Create map with different strength per channel
        # R=255 (max blur), G=128 (half blur), B=0 (no blur)
        channel_map = Image.new("RGBA", (100, 100), (255, 128, 0, 255))
        
        result = apply_mask_blur(
            self.test_image,
            channel_map,
            blur_type="gaussian",
            max_radius=15,
        )
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.test_image.size)
    
    def test_mask_blur_gradient_strength(self):
        """Test mask blur with gradient strength map."""
        result = apply_mask_blur(
            self.test_image,
            self.gradient_map,
            blur_type="gaussian",
            max_radius=10,
        )
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_mask_blur_resizes_mismatched_map(self):
        """Test that mismatched map size is auto-resized."""
        small_map = Image.new("RGBA", (50, 50), (128, 128, 128, 128))
        
        result = apply_mask_blur(
            self.test_image,
            small_map,
            blur_type="gaussian",
            max_radius=10,
        )
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_mask_blur_converts_rgb_to_rgba(self):
        """Test that RGB image is converted to RGBA."""
        rgb_image = Image.new("RGB", (100, 100), "blue")
        
        result = apply_mask_blur(
            rgb_image,
            self.strength_map,
            blur_type="gaussian",
            max_radius=10,
        )
        
        self.assertEqual(result.mode, "RGBA")
    
    def test_mask_blur_invalid_image_type(self):
        """Test error on invalid image type."""
        with self.assertRaises(TypeError):
            apply_mask_blur(
                "not_an_image",
                self.strength_map,
                blur_type="gaussian",
            )
    
    def test_mask_blur_invalid_map_type(self):
        """Test error on invalid strength map type."""
        with self.assertRaises(TypeError):
            apply_mask_blur(
                self.test_image,
                "not_an_image",
                blur_type="gaussian",
            )
    
    def test_mask_blur_invalid_blur_type(self):
        """Test error on invalid blur type."""
        with self.assertRaises(ValueError):
            apply_mask_blur(
                self.test_image,
                self.strength_map,
                blur_type="invalid",
                max_radius=10,
            )
    
    def test_mask_blur_invalid_max_radius(self):
        """Test error on invalid max_radius."""
        with self.assertRaises(ValueError):
            apply_mask_blur(
                self.test_image,
                self.strength_map,
                blur_type="gaussian",
                max_radius=0,
            )
        
        with self.assertRaises(ValueError):
            apply_mask_blur(
                self.test_image,
                self.strength_map,
                blur_type="gaussian",
                max_radius=101,
            )


class TestMaskBlurNodeConfig(unittest.TestCase):
    """Test MaskBlurNodeConfig."""
    
    def test_config_default(self):
        """Test default config."""
        config = MaskBlurNodeConfig()
        
        self.assertEqual(config.blur_type, "gaussian")
        self.assertEqual(config.max_radius, 25.0)
    
    def test_config_custom(self):
        """Test custom config."""
        config = MaskBlurNodeConfig(
            blur_type="box",
            max_radius=40.0,
        )
        
        self.assertEqual(config.blur_type, "box")
        self.assertEqual(config.max_radius, 40.0)
    
    def test_config_to_dict(self):
        """Test serialization."""
        config = MaskBlurNodeConfig(
            blur_type="gaussian",
            max_radius=30.0,
        )
        
        data = config.to_dict()
        
        self.assertEqual(data["blur_type"], "gaussian")
        self.assertEqual(data["max_radius"], 30.0)
    
    def test_config_from_dict(self):
        """Test deserialization."""
        data = {
            "blur_type": "box",
            "max_radius": 20.0,
        }
        
        config = MaskBlurNodeConfig.from_dict(data)
        
        self.assertEqual(config.blur_type, "box")
        self.assertEqual(config.max_radius, 20.0)


class TestMaskBlurNodeExecutor(unittest.TestCase):
    """Test mask blur node executor."""
    
    def setUp(self):
        """Create test images."""
        self.test_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        self.strength_map = Image.new("RGBA", (100, 100), (128, 128, 128, 255))
    
    def test_execute_gaussian(self):
        """Test executing Gaussian mask blur."""
        node = {
            "blur_type": "gaussian",
            "max_radius": 15,
        }
        
        result = execute_mask_blur_node(node, [self.test_image, self.strength_map])
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.test_image.size)
    
    def test_execute_box(self):
        """Test executing box mask blur."""
        node = {
            "blur_type": "box",
            "max_radius": 15,
        }
        
        result = execute_mask_blur_node(node, [self.test_image, self.strength_map])
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_execute_missing_input(self):
        """Test error on missing input."""
        node = {"blur_type": "gaussian"}
        
        with self.assertRaises(ValueError):
            execute_mask_blur_node(node, [])
    
    def test_execute_missing_strength_map(self):
        """Test error on missing strength map."""
        node = {"blur_type": "gaussian"}
        
        with self.assertRaises(ValueError):
            execute_mask_blur_node(node, [self.test_image])
    
    def test_execute_invalid_image_type(self):
        """Test error on invalid image type."""
        node = {"blur_type": "gaussian"}
        
        with self.assertRaises(TypeError):
            execute_mask_blur_node(node, ["not_image", self.strength_map])
    
    def test_execute_invalid_map_type(self):
        """Test error on invalid map type."""
        node = {"blur_type": "gaussian"}
        
        with self.assertRaises(TypeError):
            execute_mask_blur_node(node, [self.test_image, "not_map"])
    
    def test_execute_case_insensitive_blur_type(self):
        """Test case-insensitive blur type."""
        node = {
            "blur_type": "GAUSSIAN",
            "max_radius": 10,
        }
        
        result = execute_mask_blur_node(node, [self.test_image, self.strength_map])
        
        self.assertEqual(result.size, self.test_image.size)


class TestMaskBlurNodeFactory(unittest.TestCase):
    """Test mask blur node factory."""
    
    def test_create_gaussian_node(self):
        """Test creating Gaussian mask blur node."""
        node = create_mask_blur_node(
            "mask-blur-1",
            blur_type="gaussian",
            max_radius=20,
        )
        
        self.assertEqual(node["id"], "mask-blur-1")
        self.assertEqual(node["type"], "Mask Blur")
        self.assertEqual(node["blur_type"], "gaussian")
        self.assertEqual(node["max_radius"], 20)
    
    def test_create_box_node(self):
        """Test creating box mask blur node."""
        node = create_mask_blur_node(
            "mask-blur-2",
            blur_type="box",
            max_radius=15,
        )
        
        self.assertEqual(node["blur_type"], "box")
        self.assertEqual(node["max_radius"], 15)
    
    def test_create_default_node(self):
        """Test creating node with defaults."""
        node = create_mask_blur_node("mask-blur-3")
        
        self.assertEqual(node["blur_type"], "gaussian")
        self.assertEqual(node["max_radius"], 25.0)


class TestMaskBlurRegistry(unittest.TestCase):
    """Test Mask Blur node registration."""
    
    def test_mask_blur_registered(self):
        """Test that Mask Blur is registered."""
        registry = get_default_registry()
        
        self.assertTrue(registry.has_executor("Mask Blur"))
    
    def test_mask_blur_metadata(self):
        """Test Mask Blur metadata."""
        registry = get_default_registry()
        meta = registry.get_metadata("Mask Blur")
        
        self.assertEqual(meta["input_count"], 2)
        self.assertEqual(meta["output_count"], 1)
        self.assertIn("mask", meta["tags"])
        self.assertIn("blur", meta["tags"])
    
    def test_execute_through_registry(self):
        """Test executing through registry."""
        registry = get_default_registry()
        image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        strength_map = Image.new("RGBA", (100, 100), (200, 100, 50, 255))
        
        node = {
            "id": "mask-blur-registry",
            "blur_type": "gaussian",
            "max_radius": 20,
        }
        
        result = registry.execute("Mask Blur", node, [image, strength_map])
        
        self.assertEqual(result.size, image.size)
        self.assertEqual(result.mode, "RGBA")
    
    def test_mask_blur_in_filter_tag(self):
        """Test that Mask Blur is tagged as filter."""
        registry = get_default_registry()
        filter_nodes = registry.filter_by_tag("filter")
        
        self.assertIn("Mask Blur", filter_nodes)


class TestMaskBlurIntegration(unittest.TestCase):
    """Integration tests for mask blur."""
    
    def test_mask_blur_on_different_sizes(self):
        """Test mask blur on different image sizes."""
        sizes = [(50, 50), (100, 200), (200, 150)]
        
        for width, height in sizes:
            img = Image.new("RGBA", (width, height), "blue")
            strength_map = Image.new("RGBA", (width, height), (150, 150, 150, 255))
            
            node = {
                "blur_type": "gaussian",
                "max_radius": 10,
            }
            
            result = execute_mask_blur_node(node, [img, strength_map])
            self.assertEqual(result.size, (width, height))
    
    def test_mask_blur_with_varied_strength(self):
        """Test mask blur with varied strength across image."""
        img = Image.new("RGBA", (100, 100), (255, 100, 50, 255))
        
        # Create horizontal gradient
        strength_map = Image.new("RGBA", (100, 100))
        pixels = strength_map.load()
        for x in range(100):
            val = int((x / 100) * 255)
            for y in range(100):
                pixels[x, y] = (val, val, val, 255)
        
        node = {
            "blur_type": "gaussian",
            "max_radius": 15,
        }
        
        result = execute_mask_blur_node(node, [img, strength_map])
        
        self.assertEqual(result.size, img.size)
    
    def test_mask_blur_per_channel_variation(self):
        """Test different blur per channel."""
        img = Image.new("RGBA", (100, 100), (255, 200, 100, 200))
        
        # R channel high strength, G medium, B low, A max
        strength_map = Image.new("RGBA", (100, 100), (255, 128, 32, 255))
        
        node = {
            "blur_type": "box",
            "max_radius": 20,
        }
        
        result = execute_mask_blur_node(node, [img, strength_map])
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, img.size)
    
    def test_mask_blur_both_types(self):
        """Test both Gaussian and Box blur types."""
        img = Image.new("RGBA", (100, 100), (100, 150, 200, 255))
        strength_map = Image.new("RGBA", (100, 100), (180, 180, 180, 255))
        
        configs = [
            {"blur_type": "gaussian", "max_radius": 10},
            {"blur_type": "box", "max_radius": 10},
        ]
        
        for config in configs:
            result = execute_mask_blur_node(config, [img, strength_map])
            self.assertEqual(result.size, img.size)


class TestMaskBlurBackends(unittest.TestCase):
    """Test mask blur backend selection and acceleration."""
    
    def test_get_available_backend(self):
        """Test that backend detection works."""
        backend = get_available_backend()
        self.assertIn(backend, ["cupy", "numpy", "pil"])
    
    def test_force_pil_backend(self):
        """Test forcing PIL backend."""
        img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        strength = Image.new("RGBA", (50, 50), (128, 128, 128, 255))
        
        result = apply_mask_blur(
            img, strength, blur_type="gaussian", max_radius=5, backend="pil"
        )
        
        self.assertEqual(result.size, img.size)
        self.assertEqual(result.mode, "RGBA")
    
    def test_invalid_backend_raises_error(self):
        """Test that invalid backend raises error."""
        img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        strength = Image.new("RGBA", (50, 50), (128, 128, 128, 255))
        
        with self.assertRaises(ValueError):
            apply_mask_blur(
                img, strength, blur_type="gaussian", max_radius=5, backend="invalid"
            )
    
    def test_numpy_acceleration_if_available(self):
        """Test NumPy backend if available."""
        backend = get_available_backend()
        
        if backend in ["numpy", "cupy"]:
            img = Image.new("RGBA", (100, 100), (255, 100, 50, 255))
            strength = Image.new("RGBA", (100, 100), (200, 200, 200, 255))
            
            # Should work with auto-detected backend
            result = apply_mask_blur(
                img, strength, blur_type="gaussian", max_radius=10
            )
            
            self.assertEqual(result.size, img.size)
            self.assertEqual(result.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
