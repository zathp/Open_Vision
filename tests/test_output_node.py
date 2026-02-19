"""
Tests for Output Node with Dynamic Filename Templating.

Tests cover:
- Output node configuration
- Tag replacement (date, time, version, counter)
- File saving and directory creation
- Executor function
- Error handling
- Node registration
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from OV_Libs.NodesLib.output_node import (
    OutputNodeConfig,
    OutputNodeHandler,
    execute_output_node,
    create_output_node,
)
from OV_Libs.ProjStoreLib.node_executors import get_default_registry


class TestOutputNodeConfig(unittest.TestCase):
    """Test OutputNodeConfig dataclass."""
    
    def test_config_creation_default(self):
        """Test creating config with defaults."""
        config = OutputNodeConfig()
        
        self.assertEqual(config.output_path, "output.png")
        self.assertEqual(config.save_format, "PNG")
        self.assertEqual(config.quality, 95)
        self.assertEqual(config.version, 1)
        self.assertFalse(config.auto_increment_counter)
        self.assertTrue(config.create_directories)
        self.assertFalse(config.overwrite)
    
    def test_config_creation_custom(self):
        """Test creating config with custom values."""
        config = OutputNodeConfig(
            output_path="/output/file_{DATE}.png",
            save_format="JPG",
            quality=80,
            version=2,
            auto_increment_counter=True,
            overwrite=True,
        )
        
        self.assertEqual(config.output_path, "/output/file_{DATE}.png")
        self.assertEqual(config.save_format, "JPG")
        self.assertEqual(config.quality, 80)
        self.assertEqual(config.version, 2)
        self.assertTrue(config.auto_increment_counter)
        self.assertTrue(config.overwrite)
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = OutputNodeConfig(
            output_path="test_{DATE}.png",
            version=3,
        )
        
        data = config.to_dict()
        
        self.assertEqual(data["output_path"], "test_{DATE}.png")
        self.assertEqual(data["version"], 3)
    
    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "output_path": "output_{VERSION:2}.png",
            "save_format": "JPG",
            "quality": 85,
            "version": 5,
        }
        
        config = OutputNodeConfig.from_dict(data)
        
        self.assertEqual(config.output_path, "output_{VERSION:2}.png")
        self.assertEqual(config.save_format, "JPG")
        self.assertEqual(config.quality, 85)
        self.assertEqual(config.version, 5)
    
    def test_get_save_kwargs_png(self):
        """Test save kwargs for PNG."""
        config = OutputNodeConfig(save_format="PNG")
        kwargs = config.get_save_kwargs()
        
        self.assertEqual(kwargs["format"], "PNG")
        # PNG doesn't use quality
        self.assertNotIn("quality", kwargs)
    
    def test_get_save_kwargs_jpg(self):
        """Test save kwargs for JPG."""
        config = OutputNodeConfig(save_format="JPG", quality=75)
        kwargs = config.get_save_kwargs()
        
        self.assertEqual(kwargs["format"], "JPEG")
        self.assertEqual(kwargs["quality"], 75)
    
    def test_quality_clamping(self):
        """Test that quality is clamped to 1-100."""
        config_low = OutputNodeConfig(save_format="JPG", quality=-10)
        config_high = OutputNodeConfig(save_format="JPG", quality=150)
        
        kwargs_low = config_low.get_save_kwargs()
        kwargs_high = config_high.get_save_kwargs()
        
        self.assertEqual(kwargs_low["quality"], 1)
        self.assertEqual(kwargs_high["quality"], 100)


class TestOutputNodeHandler(unittest.TestCase):
    """Test OutputNodeHandler tag replacement and file I/O."""
    
    def setUp(self):
        """Create temporary directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        self.test_image = Image.new("RGBA", (50, 50), color="blue")
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def test_date_tag_replacement(self):
        """Test {DATE} tag replacement."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{DATE}.png")
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        # Should contain today's date in YYYY-MM-DD format
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertIn(today, str(filename))
    
    def test_date_tag_custom_format(self):
        """Test {DATE} with custom format."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{DATE:%Y_%m_%d}.png")
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        # Should use custom format
        time_str = datetime.now().strftime("%Y_%m_%d")
        self.assertIn(time_str, str(filename))
    
    def test_time_tag_replacement(self):
        """Test {TIME} tag replacement."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{TIME}.png")
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        # Should contain time in HH-MM-SS format
        self.assertIn("-", str(filename))  # Time separators
    
    def test_datetime_tag_replacement(self):
        """Test {DATETIME} tag replacement."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{DATETIME}.png")
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        # Should contain date and time
        self.assertIn("_", str(filename))  # Separator between date and time
    
    def test_version_tag_replacement(self):
        """Test {VERSION} tag replacement."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{VERSION}.png"),
            version=5,
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        self.assertIn("5", str(filename))
    
    def test_version_tag_with_width(self):
        """Test {VERSION} with zero-padding width."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{VERSION:3}.png"),
            version=7,
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        # Should be zero-padded to width 3
        self.assertIn("007", str(filename))
    
    def test_counter_tag_replacement(self):
        """Test {COUNTER} tag replacement."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{COUNTER}.png")
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        self.assertIn("0", str(filename))
    
    def test_counter_tag_with_width(self):
        """Test {COUNTER} with zero-padding width."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{COUNTER:4}.png"),
            _counter=42,
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        
        # Should be zero-padded to width 4
        self.assertIn("0042", str(filename))
    
    def test_multiple_tags_replacement(self):
        """Test multiple tags in one filename."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_v{VERSION:2}_{DATE}_{COUNTER:3}.png"),
            version=3,
        )
        handler = OutputNodeHandler(config)
        
        filename = handler.resolve_filename()
        filename_str = str(filename)
        
        # Should contain all replaced tags
        self.assertIn("v03", filename_str)
        self.assertIn("000", filename_str)
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertIn(today, filename_str)
    
    def test_save_image_creates_file(self):
        """Test saving image creates file."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "test_output.png")
        )
        handler = OutputNodeHandler(config)
        
        output_path = handler.save_image(self.test_image)
        
        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.stat().st_size > 0, True)
    
    def test_save_image_creates_directories(self):
        """Test that directories are created."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "subdir" / "deep" / "output.png"),
            create_directories=True,
        )
        handler = OutputNodeHandler(config)
        
        output_path = handler.save_image(self.test_image)
        
        self.assertTrue(output_path.exists())
        self.assertTrue(output_path.parent.exists())
    
    def test_save_image_fails_without_create_directories(self):
        """Test that save fails if directory missing and create_directories=False."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "missing_dir" / "output.png"),
            create_directories=False,
        )
        handler = OutputNodeHandler(config)
        
        with self.assertRaises(OSError):
            handler.save_image(self.test_image)
    
    def test_save_image_respects_overwrite_false(self):
        """Test that overwrite=False prevents overwriting."""
        output_file = self.temp_path / "existing.png"
        self.test_image.save(output_file)
        
        config = OutputNodeConfig(
            output_path=str(output_file),
            overwrite=False,
        )
        handler = OutputNodeHandler(config)
        
        with self.assertRaises(ValueError):
            handler.save_image(self.test_image)
    
    def test_save_image_respects_overwrite_true(self):
        """Test that overwrite=True allows overwriting."""
        output_file = self.temp_path / "existing.png"
        self.test_image.save(output_file)
        
        config = OutputNodeConfig(
            output_path=str(output_file),
            overwrite=True,
        )
        handler = OutputNodeHandler(config)
        
        # Should not raise
        output_path = handler.save_image(self.test_image)
        self.assertTrue(output_path.exists())
    
    def test_counter_auto_increment(self):
        """Test auto-incrementing counter."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "output_{COUNTER:3}.png"),
            auto_increment_counter=True,
        )
        handler = OutputNodeHandler(config)
        
        # Save multiple times
        for i in range(3):
            filename = handler.resolve_filename()
            self.assertIn(f"{i:03d}", str(filename))
            handler.config._counter += 1
    
    def test_save_jpg_converts_rgba_to_rgb(self):
        """Test that RGBA images are converted to RGB for JPEG."""
        config = OutputNodeConfig(
            output_path=str(self.temp_path / "test_jpg.jpg"),
            save_format="JPG",
        )
        handler = OutputNodeHandler(config)
        
        # RGBA image
        output_path = handler.save_image(self.test_image)
        
        self.assertTrue(output_path.exists())
        # JPEG should save successfully
        saved = Image.open(output_path)
        self.assertEqual(saved.format, "JPEG")


class TestOutputNodeExecutor(unittest.TestCase):
    """Test output node executor."""
    
    def setUp(self):
        """Create test image and temporary directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.test_image = Image.new("RGBA", (50, 50), color="red")
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def test_execute_output_node(self):
        """Test executing output node."""
        node = {
            "id": "output-1",
            "type": "Output",
            "output_path": str(self.temp_path / "output.png"),
            "save_format": "PNG",
            "version": 1,
        }
        
        result = execute_output_node(node, [self.test_image])
        
        self.assertIsInstance(result, Path)
        self.assertTrue(result.exists())
    
    def test_execute_output_with_tags(self):
        """Test executing output node with tags."""
        node = {
            "id": "output-2",
            "output_path": str(self.temp_path / "output_{DATE}.png"),
            "version": 1,
        }
        
        result = execute_output_node(node, [self.test_image])
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertIn(today, str(result))
    
    def test_execute_missing_input_raises_error(self):
        """Test that missing input raises ValueError."""
        node = {"id": "output-bad"}
        
        with self.assertRaises(ValueError):
            execute_output_node(node, [])
    
    def test_execute_invalid_input_type_raises_error(self):
        """Test that invalid input type raises TypeError."""
        node = {"id": "output-bad"}
        
        with self.assertRaises(TypeError):
            execute_output_node(node, ["not an image"])


class TestOutputNodeFactory(unittest.TestCase):
    """Test create_output_node helper."""
    
    def test_create_simple_output_node(self):
        """Test creating simple output node."""
        node = create_output_node(
            node_id="out-1",
            output_path="output.png",
        )
        
        self.assertEqual(node["id"], "out-1")
        self.assertEqual(node["type"], "Output")
        self.assertEqual(node["output_path"], "output.png")
    
    def test_create_output_node_with_tags(self):
        """Test creating output node with tags."""
        node = create_output_node(
            node_id="out-2",
            output_path="output_v{VERSION:2}_{DATE}.png",
            version=3,
        )
        
        self.assertEqual(node["output_path"], "output_v{VERSION:2}_{DATE}.png")
        self.assertEqual(node["version"], 3)
    
    def test_create_output_node_with_counter(self):
        """Test creating output node with counter."""
        node = create_output_node(
            node_id="out-3",
            output_path="output_{COUNTER:4}.png",
            auto_increment_counter=True,
        )
        
        self.assertTrue(node["auto_increment_counter"])
        self.assertEqual(node["_counter"], 0)


class TestOutputNodeRegistry(unittest.TestCase):
    """Test Output node is registered in executor registry."""
    
    def test_output_registered(self):
        """Test that Output node is registered."""
        registry = get_default_registry()
        
        self.assertTrue(registry.has_executor("Output"))
    
    def test_output_metadata(self):
        """Test Output node metadata."""
        registry = get_default_registry()
        meta = registry.get_metadata("Output")
        
        self.assertEqual(meta["input_count"], 1)
        self.assertEqual(meta["output_count"], 0)
        self.assertIn("output", meta["tags"])
        self.assertIn("sink", meta["tags"])
    
    def test_execute_output_through_registry(self):
        """Test executing Output node through registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = get_default_registry()
            test_image = Image.new("RGBA", (50, 50), color="green")
            
            node = {
                "id": "output-registry",
                "output_path": str(temp_path / "test_output.png"),
            }
            
            result = registry.execute("Output", node, [test_image])
            
            self.assertIsInstance(result, Path)
            self.assertTrue(result.exists())


if __name__ == "__main__":
    unittest.main()
