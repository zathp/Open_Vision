"""
Tests for Color Shift Node with Mask Generation.

Tests cover:
- Color shift node execution
- Mask generation
- Color shift filter enhancements
- Various selection and shift types
- Error handling
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

from OV_Libs.ImageEditingLib.color_shift_filter import (
    ColorShiftFilter,
    ColorShiftFilterOptions,
)
from OV_Libs.NodesLib.color_shift_node import (
    ColorShiftNodeConfig,
    execute_color_shift_node,
    create_color_shift_node,
)
from OV_Libs.ProjStoreLib.node_executors import get_default_registry


class TestColorShiftFilterEnhancements(unittest.TestCase):
    """Test color shift filter mask generation methods."""
    
    def setUp(self):
        """Create test images and filter."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.filter = ColorShiftFilter()
        
        # Create test image with red and blue regions
        self.test_image = Image.new("RGBA", (100, 100), color=(0, 0, 0, 255))
        pixels = self.test_image.load()
        
        # Red region (top half)
        for y in range(50):
            for x in range(100):
                pixels[x, y] = (255, 0, 0, 255)
        
        # Blue region (bottom half)
        for y in range(50, 100):
            for x in range(100):
                pixels[x, y] = (0, 0, 255, 255)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_apply_color_shift_to_image_with_mask(self):
        """Test applying color shift and generating mask."""
        base_color = (255, 0, 0, 255)  # Red
        options = ColorShiftFilterOptions(
            selection_type="rgb_range",
            shift_type="absolute_rgb",
            tolerance=30
        )
        shift_value = (50, 0, 0)  # Shift red channel up
        
        modified, mask = self.filter.apply_color_shift_to_image(
            self.test_image,
            base_color,
            options,
            shift_value,
        )
        
        # Modified image should have different color in red region
        self.assertIsNotNone(modified)
        self.assertEqual(modified.size, (100, 100))
        self.assertEqual(modified.mode, "RGBA")
        
        # Mask should be RGBA
        self.assertIsNotNone(mask)
        self.assertEqual(mask.size, (100, 100))
        self.assertEqual(mask.mode, "RGBA")
        
        # Check that mask has white pixels in red region
        mask_pixels = mask.load()
        # Top-left pixel should be white (was red, so changed)
        pixel = mask_pixels[0, 0]
        self.assertEqual(pixel[:3], (255, 255, 255))
    
    def test_apply_color_shift_with_palette_mapping(self):
        """Test color shift using palette mapping."""
        palette = [(255, 0, 0, 255), (0, 0, 255, 255)]
        mapping = [(255, 100, 0, 255), (100, 100, 255, 255)]
        
        modified, mask = self.filter.apply_color_shift_to_image_with_palette(
            self.test_image,
            palette,
            mapping,
        )
        
        # Should successfully apply mapping
        self.assertIsNotNone(modified)
        self.assertIsNotNone(mask)
        self.assertEqual(modified.size, (100, 100))
        self.assertEqual(mask.size, (100, 100))
    
    def test_palette_mapping_size_mismatch_raises_error(self):
        """Test that palette/mapping size mismatch raises error."""
        palette = [(255, 0, 0, 255)]
        mapping = [(255, 100, 0, 255), (100, 100, 255, 255)]
        
        with self.assertRaises(ValueError):
            self.filter.apply_color_shift_to_image_with_palette(
                self.test_image,
                palette,
                mapping,
            )
    
    def test_generate_change_mask_with_rgba(self):
        """Test generating mask from two images (RGBA)."""
        original = self.test_image.copy()
        modified = self.test_image.copy()
        
        # Modify a region
        pixels = modified.load()
        pixels[0, 0] = (255, 255, 255, 255)
        
        mask = self.filter.generate_change_mask(original, modified, alpha_channel=True)
        
        self.assertEqual(mask.mode, "RGBA")
        self.assertEqual(mask.size, (100, 100))
        
        # First pixel should be white (changed)
        mask_pixels = mask.load()
        self.assertEqual(mask_pixels[0, 0][:3], (255, 255, 255))
        
        # Other pixels in red region should be black (unchanged)
        self.assertEqual(mask_pixels[10, 10][:3], (0, 0, 0))
    
    def test_generate_change_mask_grayscale(self):
        """Test generating grayscale mask."""
        original = self.test_image.copy()
        modified = self.test_image.copy()
        
        pixels = modified.load()
        pixels[0, 0] = (255, 255, 255, 255)
        
        mask = self.filter.generate_change_mask(original, modified, alpha_channel=False)
        
        self.assertEqual(mask.mode, "L")
        self.assertEqual(mask.size, (100, 100))
    
    def test_generate_change_mask_size_mismatch_raises_error(self):
        """Test that different sized images raise error."""
        small = Image.new("RGBA", (50, 50))
        large = Image.new("RGBA", (100, 100))
        
        with self.assertRaises(ValueError):
            self.filter.generate_change_mask(small, large)
    
    def test_is_color_selected_hsv_range(self):
        """Test color selection via HSV range."""
        red = (255, 0, 0, 255)
        options = ColorShiftFilterOptions(
            selection_type="hsv_range",
            shift_type="absolute_rgb",
            tolerance=60  # Increased tolerance for HSV range
        )
        
        # Red-ish color should be selected
        bright_red = (255, 50, 50, 255)
        is_selected = self.filter._is_color_selected(bright_red, red, options)
        
        self.assertTrue(is_selected)
    
    def test_is_color_selected_rgb_range(self):
        """Test color selection via RGB range."""
        red = (255, 0, 0, 255)
        options = ColorShiftFilterOptions(
            selection_type="rgb_range",
            shift_type="absolute_rgb",
            tolerance=40
        )
        
        # Close red should be selected
        close_red = (250, 10, 5, 255)
        is_selected = self.filter._is_color_selected(close_red, red, options)
        
        self.assertTrue(is_selected)
        
        # Far red should not be selected
        far_color = (100, 100, 100, 255)
        not_selected = self.filter._is_color_selected(far_color, red, options)
        
        self.assertFalse(not_selected)
    
    def test_is_color_selected_rgb_distance(self):
        """Test color selection via RGB distance."""
        red = (255, 0, 0, 255)
        options = ColorShiftFilterOptions(
            selection_type="rgb_distance",
            shift_type="absolute_rgb",
            tolerance=50,
            distance_type="euclidean"
        )
        
        close_red = (250, 10, 5, 255)
        is_selected = self.filter._is_color_selected(close_red, red, options)
        
        self.assertTrue(is_selected)


class TestColorShiftNodeConfig(unittest.TestCase):
    """Test ColorShiftNodeConfig dataclass."""
    
    def test_config_creation_default(self):
        """Test creating config with defaults."""
        config = ColorShiftNodeConfig()
        
        self.assertEqual(config.base_color_r, 0)
        self.assertEqual(config.base_color_g, 0)
        self.assertEqual(config.base_color_b, 0)
        self.assertEqual(config.base_color_a, 255)
        self.assertEqual(config.selection_type, "rgb_distance")
        self.assertTrue(config.output_mask)
    
    def test_config_creation_custom(self):
        """Test creating config with custom values."""
        config = ColorShiftNodeConfig(
            base_color_r=255,
            base_color_g=100,
            base_color_b=50,
            shift_amount=75.0,
            output_mask=False,
        )
        
        self.assertEqual(config.base_color_r, 255)
        self.assertEqual(config.base_color_g, 100)
        self.assertEqual(config.shift_amount, 75.0)
        self.assertFalse(config.output_mask)
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = ColorShiftNodeConfig(
            base_color_r=200,
            base_color_g=50,
            base_color_b=100,
            shift_amount=40.0,
        )
        
        data = config.to_dict()
        
        self.assertEqual(data["base_color_r"], 200)
        self.assertEqual(data["base_color_g"], 50)
        self.assertEqual(data["shift_amount"], 40.0)
    
    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "base_color_r": 180,
            "base_color_g": 60,
            "base_color_b": 120,
            "shift_amount": 55.0,
            "output_mask": False,
        }
        
        config = ColorShiftNodeConfig.from_dict(data)
        
        self.assertEqual(config.base_color_r, 180)
        self.assertEqual(config.base_color_g, 60)
        self.assertFalse(config.output_mask)
    
    def test_config_get_base_color(self):
        """Test getting base color as RGBA tuple."""
        config = ColorShiftNodeConfig(
            base_color_r=255,
            base_color_g=128,
            base_color_b=64,
            base_color_a=200,
        )
        
        color = config.get_base_color()
        
        self.assertEqual(color, (255, 128, 64, 200))
    
    def test_config_get_filter_options(self):
        """Test getting filter options from config."""
        config = ColorShiftNodeConfig(
            selection_type="hsv_range",
            shift_type="percentile_rgb",
            tolerance=50.0,
            distance_type="manhattan",
        )
        
        options = config.get_filter_options()
        
        self.assertEqual(options.selection_type, "hsv_range")
        self.assertEqual(options.shift_type, "percentile_rgb")
        self.assertEqual(options.tolerance, 50.0)
        self.assertEqual(options.distance_type, "manhattan")


class TestColorShiftNodeExecutor(unittest.TestCase):
    """Test color shift node executor."""
    
    def setUp(self):
        """Create test images."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_image = Image.new("RGBA", (50, 50), color=(255, 0, 0, 255))
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def test_execute_color_shift_with_mask(self):
        """Test executing color shift node with mask output."""
        node = {
            "id": "shift-1",
            "type": "Color Shift",
            "base_color_r": 255,
            "base_color_g": 0,
            "base_color_b": 0,
            "base_color_a": 255,
            "selection_type": "rgb_range",
            "shift_type": "absolute_rgb",
            "tolerance": 50,
            "shift_amount": (50, 0, 0),
            "output_mask": True,
        }
        
        result = execute_color_shift_node(node, [self.test_image])
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        
        modified, mask = result
        self.assertIsNotNone(modified)
        self.assertIsNotNone(mask)
        self.assertEqual(mask.mode, "RGBA")
    
    def test_execute_color_shift_without_mask(self):
        """Test executing color shift node without mask output."""
        node = {
            "id": "shift-2",
            "base_color_r": 255,
            "base_color_g": 0,
            "base_color_b": 0,
            "selection_type": "rgb_range",
            "shift_type": "absolute_rgb",
            "tolerance": 50,
            "shift_amount": 50,
            "output_mask": False,
        }
        
        result = execute_color_shift_node(node, [self.test_image])
        
        # Should return just the image, not a tuple
        self.assertNotIsInstance(result, tuple)
        self.assertEqual(result.size, (50, 50))
    
    def test_execute_missing_input_raises_error(self):
        """Test that missing input raises ValueError."""
        node = {"id": "shift-bad"}
        
        with self.assertRaises(ValueError):
            execute_color_shift_node(node, [])
    
    def test_execute_invalid_input_type_raises_error(self):
        """Test that invalid input type raises TypeError."""
        node = {"id": "shift-bad"}
        
        with self.assertRaises(TypeError):
            execute_color_shift_node(node, ["not an image"])


class TestColorShiftNodeFactory(unittest.TestCase):
    """Test color shift node creation helper."""
    
    def test_create_color_shift_node(self):
        """Test creating a color shift node dictionary."""
        node = create_color_shift_node(
            node_id="shift-test",
            base_color=(255, 100, 50, 255),
            shift_amount=75.0,
            selection_type="hsv_range",
            shift_type="percentile_rgb",
            tolerance=40.0,
        )
        
        self.assertEqual(node["id"], "shift-test")
        self.assertEqual(node["type"], "Color Shift")
        self.assertEqual(node["base_color_r"], 255)
        self.assertEqual(node["base_color_g"], 100)
        self.assertEqual(node["base_color_b"], 50)
        self.assertEqual(node["base_color_a"], 255)
        self.assertEqual(node["shift_amount"], 75.0)
        self.assertEqual(node["selection_type"], "hsv_range")
    
    def test_create_node_defaults(self):
        """Test creating node with default values."""
        node = create_color_shift_node(
            node_id="shift-defaults",
            base_color=(200, 50, 100, 255),
            shift_amount=60.0,
        )
        
        self.assertTrue(node["output_mask"])
        self.assertEqual(node["selection_type"], "rgb_distance")
        self.assertEqual(node["shift_type"], "absolute_rgb")


class TestColorShiftNodeRegistry(unittest.TestCase):
    """Test Color Shift node is registered in executor registry."""
    
    def test_color_shift_registered(self):
        """Test that Color Shift node is registered."""
        registry = get_default_registry()
        
        self.assertTrue(registry.has_executor("Color Shift"))
    
    def test_color_shift_metadata(self):
        """Test Color Shift node metadata."""
        registry = get_default_registry()
        meta = registry.get_metadata("Color Shift")
        
        self.assertEqual(meta["input_count"], 1)
        self.assertEqual(meta["output_count"], 2)
        self.assertIn("processing", meta["tags"])
        self.assertIn("color", meta["tags"])
    
    def test_execute_color_shift_through_registry(self):
        """Test executing Color Shift node through registry."""
        registry = get_default_registry()
        test_image = Image.new("RGBA", (50, 50), color=(255, 0, 0, 255))
        
        node = {
            "id": "shift-registry",
            "base_color_r": 255,
            "base_color_g": 0,
            "base_color_b": 0,
            "selection_type": "rgb_range",
            "shift_type": "absolute_rgb",
            "tolerance": 50,
            "shift_amount": 50,
            "output_mask": True,
        }
        
        result = registry.execute("Color Shift", node, [test_image])
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
