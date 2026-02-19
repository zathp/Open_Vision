"""
Tests for Image Import Node functionality.

Tests cover:
- ImageImportNode creation and validation
- Standard image format loading
- GIF frame loading
- Caching behavior
- Executor function
- Error handling
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

from OV_Libs.NodesLib.image_import_node import (
    ImageImportNode,
    execute_import_image_node,
    get_supported_image_formats,
    get_supported_movie_formats,
    get_supported_gif_formats,
    get_supported_formats,
    is_supported_format,
    STANDARD_IMAGE_FORMATS,
    MOVIE_FORMATS,
)


class TestImageImportNodeCreation(unittest.TestCase):
    """Test ImageImportNode creation and validation."""
    
    def setUp(self):
        """Create temporary directory and test images."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create a test image
        self.test_image_path = self.temp_path / "test_image.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(self.test_image_path)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_valid_node_creation(self):
        """Test creating a valid ImageImportNode."""
        node = ImageImportNode(
            node_id="test-node-1",
            file_path=self.test_image_path
        )
        
        self.assertEqual(node.node_id, "test-node-1")
        self.assertEqual(node.file_path, self.test_image_path)
        self.assertEqual(node.format_type, "image")
        self.assertTrue(node.cache_image)
        self.assertEqual(node.frame_index, 0)
        self.assertIsNone(node.cached_image)
    
    def test_node_creation_with_all_fields(self):
        """Test creating node with all fields specified."""
        node = ImageImportNode(
            node_id="test-node-2",
            file_path=self.test_image_path,
            format_type="gif",
            cache_image=False,
            frame_index=2
        )
        
        self.assertEqual(node.format_type, "gif")
        self.assertFalse(node.cache_image)
        self.assertEqual(node.frame_index, 2)
    
    def test_node_creation_nonexistent_file(self):
        """Test that creation fails with nonexistent file."""
        nonexistent = self.temp_path / "does_not_exist.png"
        
        with self.assertRaises(FileNotFoundError):
            ImageImportNode(
                node_id="test-bad",
                file_path=nonexistent
            )
    
    def test_node_creation_nonfile_path(self):
        """Test that creation fails when path is a directory."""
        with self.assertRaises(ValueError):
            ImageImportNode(
                node_id="test-bad",
                file_path=self.temp_path
            )
    
    def test_node_creation_invalid_format_type(self):
        """Test that creation fails with invalid format_type."""
        with self.assertRaises(ValueError):
            ImageImportNode(
                node_id="test-bad",
                file_path=self.test_image_path,
                format_type="invalid_format"
            )
    
    def test_node_creation_negative_frame_index(self):
        """Test that creation fails with negative frame_index."""
        with self.assertRaises(ValueError):
            ImageImportNode(
                node_id="test-bad",
                file_path=self.test_image_path,
                frame_index=-1
            )


class TestImageLoading(unittest.TestCase):
    """Test image loading functionality."""
    
    def setUp(self):
        """Create temporary directory and test images."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create standard image
        self.png_image = self.temp_path / "test.png"
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(self.png_image)
        
        # Create JPEG image
        self.jpg_image = self.temp_path / "test.jpg"
        img.save(self.jpg_image)
        
        # Create simple GIF
        self.gif_image = self.temp_path / "test.gif"
        img.save(self.gif_image)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_load_png_image(self):
        """Test loading a PNG image."""
        node = ImageImportNode(
            node_id="png-test",
            file_path=self.png_image
        )
        
        image = node.load_image()
        
        self.assertIsNotNone(image)
        self.assertEqual(image.size, (50, 50))
        self.assertEqual(image.mode, "RGBA")
    
    def test_load_jpg_image(self):
        """Test loading a JPG image."""
        node = ImageImportNode(
            node_id="jpg-test",
            file_path=self.jpg_image
        )
        
        image = node.load_image()
        
        self.assertIsNotNone(image)
        self.assertEqual(image.size, (50, 50))
        self.assertEqual(image.mode, "RGBA")
    
    def test_load_gif_image(self):
        """Test loading a GIF image."""
        node = ImageImportNode(
            node_id="gif-test",
            file_path=self.gif_image,
            format_type="gif"
        )
        
        image = node.load_image()
        
        self.assertIsNotNone(image)
        self.assertEqual(image.mode, "RGBA")
    
    def test_load_image_converts_to_rgba(self):
        """Test that loaded images are converted to RGBA mode."""
        node = ImageImportNode(
            node_id="rgb-test",
            file_path=self.png_image
        )
        
        image = node.load_image()
        
        self.assertEqual(image.mode, "RGBA")
    
    def test_image_caching(self):
        """Test that images are cached when cache_image=True."""
        node = ImageImportNode(
            node_id="cache-test",
            file_path=self.png_image,
            cache_image=True
        )
        
        image1 = node.load_image()
        image2 = node.load_image()
        
        # Should be the same object (cached)
        self.assertIs(image1, image2)
    
    def test_image_not_cached(self):
        """Test that new images are loaded when cache_image=False."""
        node = ImageImportNode(
            node_id="no-cache-test",
            file_path=self.png_image,
            cache_image=False
        )
        
        image1 = node.load_image()
        image2 = node.load_image()
        
        # Should be different objects (not cached)
        self.assertIsNot(image1, image2)
        # But same content
        self.assertEqual(image1.tobytes(), image2.tobytes())


class TestImageImportNodeSerialization(unittest.TestCase):
    """Test ImageImportNode serialization."""
    
    def setUp(self):
        """Create temporary directory and test images."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        self.test_image = self.temp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="green")
        img.save(self.test_image)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_to_dict(self):
        """Test converting node to dictionary."""
        node = ImageImportNode(
            node_id="dict-test",
            file_path=self.test_image,
            format_type="gif",
            cache_image=False,
            frame_index=3
        )
        
        data = node.to_dict()
        
        self.assertEqual(data["node_id"], "dict-test")
        self.assertEqual(data["file_path"], str(self.test_image))
        self.assertEqual(data["format_type"], "gif")
        self.assertFalse(data["cache_image"])
        self.assertEqual(data["frame_index"], 3)
    
    def test_from_dict(self):
        """Test creating node from dictionary."""
        data = {
            "node_id": "restored-node",
            "file_path": str(self.test_image),
            "format_type": "image",
            "cache_image": True,
            "frame_index": 0
        }
        
        node = ImageImportNode.from_dict(data)
        
        self.assertEqual(node.node_id, "restored-node")
        self.assertEqual(node.file_path, self.test_image)
        self.assertEqual(node.format_type, "image")
        self.assertTrue(node.cache_image)
        self.assertEqual(node.frame_index, 0)
    
    def test_roundtrip_serialization(self):
        """Test serialization and deserialization roundtrip."""
        original = ImageImportNode(
            node_id="roundtrip-test",
            file_path=self.test_image,
            format_type="gif",
            cache_image=False,
            frame_index=5
        )
        
        data = original.to_dict()
        restored = ImageImportNode.from_dict(data)
        
        self.assertEqual(original.node_id, restored.node_id)
        self.assertEqual(original.file_path, restored.file_path)
        self.assertEqual(original.format_type, restored.format_type)
        self.assertEqual(original.cache_image, restored.cache_image)
        self.assertEqual(original.frame_index, restored.frame_index)


class TestImageImportExecutor(unittest.TestCase):
    """Test the pipeline executor function."""
    
    def setUp(self):
        """Create temporary directory and test images."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        self.test_image = self.temp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="yellow")
        img.save(self.test_image)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_executor_basic(self):
        """Test executor function with basic node."""
        node = {
            "id": "exec-test",
            "file_path": str(self.test_image),
            "format_type": "image",
            "cache_image": True
        }
        
        result = execute_import_image_node(node, [])
        
        self.assertIsNotNone(result)
        self.assertEqual(result.size, (100, 100))
        self.assertEqual(result.mode, "RGBA")
    
    def test_executor_missing_file_path(self):
        """Test executor raises KeyError when file_path missing."""
        node = {
            "id": "bad-exec",
            "format_type": "image"
        }
        
        with self.assertRaises(KeyError):
            execute_import_image_node(node, [])
    
    def test_executor_with_alternative_id_field(self):
        """Test executor works with 'node_id' field as fallback."""
        node = {
            "node_id": "alt-id-test",
            "file_path": str(self.test_image)
        }
        
        result = execute_import_image_node(node, [])
        
        self.assertIsNotNone(result)
    
    def test_executor_default_format_type(self):
        """Test executor uses default format_type when not specified."""
        node = {
            "id": "default-test",
            "file_path": str(self.test_image)
        }
        
        result = execute_import_image_node(node, [])
        
        self.assertIsNotNone(result)
        self.assertEqual(result.mode, "RGBA")


class TestFormatSupport(unittest.TestCase):
    """Test format support functions."""
    
    def test_standard_image_formats(self):
        """Test standard image format list."""
        formats = get_supported_image_formats()
        
        self.assertIn(".png", formats)
        self.assertIn(".jpg", formats)
        self.assertIn(".jpeg", formats)
        self.assertIn(".bmp", formats)
    
    def test_movie_formats(self):
        """Test movie format list."""
        formats = get_supported_movie_formats()
        
        self.assertIn(".mp4", formats)
        self.assertIn(".avi", formats)
        self.assertIn(".mov", formats)
    
    def test_gif_formats(self):
        """Test GIF format list."""
        formats = get_supported_gif_formats()
        
        self.assertEqual(formats, [".gif"])
    
    def test_get_all_formats_without_movies(self):
        """Test getting all formats without movies."""
        formats = get_supported_formats(include_movies=False)
        
        self.assertIn(".png", formats)
        self.assertNotIn(".mp4", formats)
    
    def test_get_all_formats_with_movies(self):
        """Test getting all formats with movies."""
        formats = get_supported_formats(include_movies=True)
        
        self.assertIn(".png", formats)
        self.assertIn(".mp4", formats)
    
    def test_is_supported_format_png(self):
        """Test is_supported_format for PNG."""
        path = Path("test.png")
        
        self.assertTrue(is_supported_format(path))
    
    def test_is_supported_format_unsupported(self):
        """Test is_supported_format for unsupported format."""
        path = Path("test.xyz")
        
        self.assertFalse(is_supported_format(path))
    
    def test_is_supported_format_case_insensitive(self):
        """Test is_supported_format is case insensitive."""
        path_upper = Path("test.PNG")
        path_lower = Path("test.png")
        
        self.assertTrue(is_supported_format(path_upper))
        self.assertTrue(is_supported_format(path_lower))


class TestFrameHandling(unittest.TestCase):
    """Test frame handling for animated formats."""
    
    def setUp(self):
        """Create temporary directory and test GIF."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        self.static_gif = self.temp_path / "static.gif"
        img = Image.new("RGB", (50, 50), color="purple")
        img.save(self.static_gif)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_get_num_frames_static_image(self):
        """Test get_num_frames for static image."""
        node = ImageImportNode(
            node_id="static-frames",
            file_path=self.static_gif,
            format_type="image"
        )
        
        num_frames = node.get_num_frames()
        
        self.assertEqual(num_frames, 1)
    
    def test_get_num_frames_gif(self):
        """Test get_num_frames for GIF."""
        node = ImageImportNode(
            node_id="gif-frames",
            file_path=self.static_gif,
            format_type="gif"
        )
        
        num_frames = node.get_num_frames()
        
        self.assertGreaterEqual(num_frames, 1)
    
    def test_load_gif_with_frame_index_out_of_range(self):
        """Test loading GIF with frame index beyond available frames."""
        node = ImageImportNode(
            node_id="out-of-range",
            file_path=self.static_gif,
            format_type="gif",
            frame_index=999
        )
        
        # Should fall back to frame 0
        image = node.load_image()
        
        self.assertIsNotNone(image)


if __name__ == "__main__":
    unittest.main()
