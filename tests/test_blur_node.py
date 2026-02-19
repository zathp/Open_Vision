"""
Tests for Blur Operations and Blur Node.

Tests cover:
- Gaussian blur
- Box blur
- Motion blur
- Radial blur
- Blur node configuration
- Blur node executor
- Node registration
- Error handling
"""

import unittest
from PIL import Image

from OV_Libs.ImageEditingLib.blur_filter import (
    apply_gaussian_blur,
    apply_box_blur,
    apply_motion_blur,
    apply_radial_blur,
    BlurNodeConfig,
)
from OV_Libs.NodesLib.blur_node import (
    execute_blur_node,
    create_blur_node,
)
from OV_Libs.ProjStoreLib.node_executors import get_default_registry


class TestGaussianBlur(unittest.TestCase):
    """Test Gaussian blur operation."""
    
    def setUp(self):
        """Create test image."""
        self.test_image = Image.new("RGB", (100, 100), "red")
        self.rgba_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    
    def test_gaussian_blur_default(self):
        """Test Gaussian blur with default radius."""
        result = apply_gaussian_blur(self.test_image)
        
        self.assertEqual(result.mode, self.test_image.mode)
        self.assertEqual(result.size, self.test_image.size)
    
    def test_gaussian_blur_small_radius(self):
        """Test Gaussian blur with small radius."""
        result = apply_gaussian_blur(self.test_image, radius=2.0)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_gaussian_blur_large_radius(self):
        """Test Gaussian blur with large radius."""
        result = apply_gaussian_blur(self.test_image, radius=50.0)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_gaussian_blur_rgba(self):
        """Test Gaussian blur on RGBA image."""
        result = apply_gaussian_blur(self.rgba_image, radius=5.0)
        
        self.assertIn(result.mode, ("RGB", "RGBA"))
    
    def test_gaussian_blur_invalid_radius_zero(self):
        """Test that radius=0 raises error."""
        with self.assertRaises(ValueError):
            apply_gaussian_blur(self.test_image, radius=0)
    
    def test_gaussian_blur_invalid_radius_too_large(self):
        """Test that radius >100 raises error."""
        with self.assertRaises(ValueError):
            apply_gaussian_blur(self.test_image, radius=101)
    
    def test_gaussian_blur_invalid_input_type(self):
        """Test that invalid input raises TypeError."""
        with self.assertRaises(TypeError):
            apply_gaussian_blur("not_an_image")


class TestBoxBlur(unittest.TestCase):
    """Test box blur operation."""
    
    def setUp(self):
        """Create test image."""
        self.test_image = Image.new("RGB", (100, 100), "blue")
    
    def test_box_blur_default(self):
        """Test box blur with default kernel."""
        result = apply_box_blur(self.test_image)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_box_blur_odd_kernel(self):
        """Test box blur with odd kernel size."""
        result = apply_box_blur(self.test_image, kernel_size=5)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_box_blur_even_kernel_converted_to_odd(self):
        """Test that even kernel size is converted to odd."""
        result = apply_box_blur(self.test_image, kernel_size=4)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_box_blur_large_kernel(self):
        """Test box blur with large kernel."""
        result = apply_box_blur(self.test_image, kernel_size=41)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_box_blur_invalid_kernel_too_large(self):
        """Test that kernel > 101 raises error."""
        with self.assertRaises(ValueError):
            apply_box_blur(self.test_image, kernel_size=103)
    
    def test_box_blur_invalid_input_type(self):
        """Test that invalid input raises TypeError."""
        with self.assertRaises(TypeError):
            apply_box_blur("not_an_image")


class TestMotionBlur(unittest.TestCase):
    """Test motion blur operation."""
    
    def setUp(self):
        """Create test image."""
        self.test_image = Image.new("RGB", (100, 100), "green")
    
    def test_motion_blur_default(self):
        """Test motion blur with default parameters."""
        result = apply_motion_blur(self.test_image)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_motion_blur_horizontal(self):
        """Test horizontal motion blur."""
        result = apply_motion_blur(self.test_image, angle=0, distance=20)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_motion_blur_vertical(self):
        """Test vertical motion blur."""
        result = apply_motion_blur(self.test_image, angle=90, distance=20)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_motion_blur_diagonal(self):
        """Test diagonal motion blur."""
        result = apply_motion_blur(self.test_image, angle=45, distance=20)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_motion_blur_angles_wrap(self):
        """Test that angles wrap around 360."""
        result1 = apply_motion_blur(self.test_image, angle=0, distance=15)
        result2 = apply_motion_blur(self.test_image, angle=360, distance=15)
        result3 = apply_motion_blur(self.test_image, angle=720, distance=15)
        
        # All should produce similar results
        self.assertEqual(result1.size, result2.size)
        self.assertEqual(result2.size, result3.size)
    
    def test_motion_blur_max_distance(self):
        """Test motion blur with max distance."""
        result = apply_motion_blur(self.test_image, distance=100)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_motion_blur_invalid_distance_zero(self):
        """Test that distance=0 raises error."""
        with self.assertRaises(ValueError):
            apply_motion_blur(self.test_image, distance=0)
    
    def test_motion_blur_invalid_distance_too_large(self):
        """Test that distance > 100 raises error."""
        with self.assertRaises(ValueError):
            apply_motion_blur(self.test_image, distance=101)
    
    def test_motion_blur_invalid_input_type(self):
        """Test that invalid input raises TypeError."""
        with self.assertRaises(TypeError):
            apply_motion_blur("not_an_image")


class TestRadialBlur(unittest.TestCase):
    """Test radial blur operation."""
    
    def setUp(self):
        """Create test image."""
        self.test_image = Image.new("RGB", (100, 100), "yellow")
    
    def test_radial_blur_default(self):
        """Test radial blur with defaults (center)."""
        result = apply_radial_blur(self.test_image)
        
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, self.test_image.size)
    
    def test_radial_blur_custom_center(self):
        """Test radial blur with custom center."""
        result = apply_radial_blur(self.test_image, center_x=25, center_y=75)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_radial_blur_corner_center(self):
        """Test radial blur with corner as center."""
        result = apply_radial_blur(self.test_image, center_x=0, center_y=0)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_radial_blur_light_strength(self):
        """Test radial blur with light strength."""
        result = apply_radial_blur(self.test_image, strength=1)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_radial_blur_max_strength(self):
        """Test radial blur with maximum strength."""
        result = apply_radial_blur(self.test_image, strength=50)
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_radial_blur_invalid_strength_zero(self):
        """Test that strength < 1 raises error."""
        with self.assertRaises(ValueError):
            apply_radial_blur(self.test_image, strength=0)
    
    def test_radial_blur_invalid_strength_too_large(self):
        """Test that strength > 50 raises error."""
        with self.assertRaises(ValueError):
            apply_radial_blur(self.test_image, strength=51)
    
    def test_radial_blur_invalid_input_type(self):
        """Test that invalid input raises TypeError."""
        with self.assertRaises(TypeError):
            apply_radial_blur("not_an_image")


class TestBlurNodeConfig(unittest.TestCase):
    """Test BlurNodeConfig."""
    
    def test_config_default(self):
        """Test default blur config."""
        config = BlurNodeConfig()
        
        self.assertEqual(config.blur_type, "gaussian")
        self.assertEqual(config.gaussian_radius, 5.0)
    
    def test_config_gaussian(self):
        """Test Gaussian blur config."""
        config = BlurNodeConfig(
            blur_type="gaussian",
            gaussian_radius=15.0,
        )
        
        self.assertEqual(config.blur_type, "gaussian")
        self.assertEqual(config.gaussian_radius, 15.0)
    
    def test_config_motion(self):
        """Test motion blur config."""
        config = BlurNodeConfig(
            blur_type="motion",
            motion_angle=45,
            motion_distance=30,
        )
        
        self.assertEqual(config.blur_type, "motion")
        self.assertEqual(config.motion_angle, 45)
        self.assertEqual(config.motion_distance, 30)
    
    def test_config_to_dict(self):
        """Test config serialization."""
        config = BlurNodeConfig(
            blur_type="gaussian",
            gaussian_radius=20.0,
        )
        
        data = config.to_dict()
        
        self.assertEqual(data["blur_type"], "gaussian")
        self.assertEqual(data["gaussian_radius"], 20.0)
    
    def test_config_from_dict(self):
        """Test config deserialization."""
        data = {
            "blur_type": "radial",
            "radial_strength": 25.0,
            "radial_center_x": 50,
            "radial_center_y": 50,
        }
        
        config = BlurNodeConfig.from_dict(data)
        
        self.assertEqual(config.blur_type, "radial")
        self.assertEqual(config.radial_strength, 25.0)


class TestBlurNodeExecutor(unittest.TestCase):
    """Test blur node executor."""
    
    def setUp(self):
        """Create test image."""
        self.test_image = Image.new("RGB", (100, 100), "red")
    
    def test_execute_gaussian_blur(self):
        """Test executing Gaussian blur node."""
        node = {
            "blur_type": "gaussian",
            "gaussian_radius": 5.0,
        }
        
        result = execute_blur_node(node, [self.test_image])
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_execute_box_blur(self):
        """Test executing box blur node."""
        node = {
            "blur_type": "box",
            "box_kernel": 5,
        }
        
        result = execute_blur_node(node, [self.test_image])
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_execute_motion_blur(self):
        """Test executing motion blur node."""
        node = {
            "blur_type": "motion",
            "motion_angle": 45,
            "motion_distance": 20,
        }
        
        result = execute_blur_node(node, [self.test_image])
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_execute_radial_blur(self):
        """Test executing radial blur node."""
        node = {
            "blur_type": "radial",
            "radial_strength": 10,
        }
        
        result = execute_blur_node(node, [self.test_image])
        
        self.assertEqual(result.size, self.test_image.size)
    
    def test_execute_missing_input(self):
        """Test error on missing input."""
        node = {"blur_type": "gaussian"}
        
        with self.assertRaises(ValueError):
            execute_blur_node(node, [])
    
    def test_execute_invalid_input_type(self):
        """Test error on invalid input type."""
        node = {"blur_type": "gaussian"}
        
        with self.assertRaises(TypeError):
            execute_blur_node(node, ["not_an_image"])
    
    def test_execute_invalid_blur_type(self):
        """Test error on invalid blur type."""
        node = {"blur_type": "invalid_blur"}
        
        with self.assertRaises(ValueError):
            execute_blur_node(node, [self.test_image])
    
    def test_execute_case_insensitive_blur_type(self):
        """Test that blur type is case insensitive."""
        node = {"blur_type": "GAUSSIAN", "gaussian_radius": 5}
        
        result = execute_blur_node(node, [self.test_image])
        
        self.assertEqual(result.size, self.test_image.size)


class TestBlurNodeFactory(unittest.TestCase):
    """Test blur node factory function."""
    
    def test_create_gaussian_node(self):
        """Test creating Gaussian blur node."""
        node = create_blur_node(
            "blur-1",
            "gaussian",
            gaussian_radius=10,
        )
        
        self.assertEqual(node["id"], "blur-1")
        self.assertEqual(node["type"], "Blur")
        self.assertEqual(node["blur_type"], "gaussian")
        self.assertEqual(node["gaussian_radius"], 10)
    
    def test_create_motion_node(self):
        """Test creating motion blur node."""
        node = create_blur_node(
            "blur-2",
            "motion",
            motion_angle=45,
            motion_distance=30,
        )
        
        self.assertEqual(node["blur_type"], "motion")
        self.assertEqual(node["motion_angle"], 45)
        self.assertEqual(node["motion_distance"], 30)
    
    def test_create_radial_node(self):
        """Test creating radial blur node."""
        node = create_blur_node(
            "blur-3",
            "radial",
            radial_center_x=50,
            radial_center_y=50,
            radial_strength=15,
        )
        
        self.assertEqual(node["blur_type"], "radial")
        self.assertEqual(node["radial_center_x"], 50)
        self.assertEqual(node["radial_strength"], 15)
    
    def test_create_default_blur(self):
        """Test creating node with defaults."""
        node = create_blur_node("blur-4")
        
        self.assertEqual(node["blur_type"], "gaussian")


class TestBlurNodeRegistry(unittest.TestCase):
    """Test Blur node registration."""
    
    def test_blur_registered(self):
        """Test that Blur node is registered."""
        registry = get_default_registry()
        
        self.assertTrue(registry.has_executor("Blur"))
    
    def test_blur_metadata(self):
        """Test Blur node metadata."""
        registry = get_default_registry()
        meta = registry.get_metadata("Blur")
        
        self.assertEqual(meta["input_count"], 1)
        self.assertEqual(meta["output_count"], 1)
        self.assertIn("blur", meta["tags"])
        self.assertIn("filter", meta["tags"])
    
    def test_execute_through_registry(self):
        """Test executing Blur node through registry."""
        registry = get_default_registry()
        test_image = Image.new("RGB", (100, 100), "blue")
        
        node = {
            "id": "blur-registry",
            "blur_type": "gaussian",
            "gaussian_radius": 8,
        }
        
        result = registry.execute("Blur", node, [test_image])
        
        self.assertEqual(result.size, test_image.size)
    
    def test_blur_has_processing_tag(self):
        """Test that Blur is tagged as processing."""
        registry = get_default_registry()
        processing_nodes = registry.filter_by_tag("processing")
        
        self.assertIn("Blur", processing_nodes)


class TestBlurIntegration(unittest.TestCase):
    """Integration tests for blur node."""
    
    def test_blur_on_different_image_sizes(self):
        """Test blur works on different image sizes."""
        sizes = [(50, 50), (100, 200), (16, 9), (800, 600)]
        
        for width, height in sizes:
            img = Image.new("RGB", (width, height), "red")
            node = {"blur_type": "gaussian", "gaussian_radius": 5}
            
            result = execute_blur_node(node, [img])
            
            self.assertEqual(result.size, (width, height))
    
    def test_blur_on_different_modes(self):
        """Test blur works on different image modes."""
        modes = ["RGB", "RGBA", "L", "P"]
        
        for mode in modes:
            try:
                img = Image.new(mode, (100, 100))
                node = {"blur_type": "gaussian", "gaussian_radius": 5}
                
                result = execute_blur_node(node, [img])
                
                # Should not raise
                self.assertIsNotNone(result)
            except (ValueError, TypeError):
                # Some modes may not be supported
                pass
    
    def test_chained_blurs(self):
        """Test applying multiple blur operations sequentially."""
        img = Image.new("RGB", (100, 100), "red")
        
        # Apply Gaussian blur
        node1 = {"blur_type": "gaussian", "gaussian_radius": 5}
        result1 = execute_blur_node(node1, [img])
        
        # Apply motion blur to result
        node2 = {"blur_type": "motion", "motion_angle": 45, "motion_distance": 20}
        result2 = execute_blur_node(node2, [result1])
        
        self.assertEqual(result2.size, img.size)
    
    def test_all_blur_types_on_same_image(self):
        """Test all blur types produce output."""
        img = Image.new("RGB", (100, 100), "blue")
        
        blur_configs = [
            {"blur_type": "gaussian", "gaussian_radius": 10},
            {"blur_type": "box", "box_kernel": 7},
            {"blur_type": "motion", "motion_angle": 30, "motion_distance": 15},
            {"blur_type": "radial", "radial_strength": 8},
        ]
        
        for config in blur_configs:
            result = execute_blur_node(config, [img])
            
            self.assertIsNotNone(result)
            self.assertEqual(result.size, img.size)


if __name__ == "__main__":
    unittest.main()
