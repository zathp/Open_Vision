"""
Unit tests for image_editing_ops module.

Tests the core image manipulation functions including color extraction,
color mapping, and image saving operations.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from OV_Libs.ImageEditingLib.image_editing_ops import (
    extract_unique_colors,
    build_identity_mapping,
    apply_color_mapping,
    save_images,
)
from OV_Libs.ImageEditingLib.image_models import ImageRecord


class TestExtractUniqueColors:
    """Tests for extract_unique_colors function."""
    
    def test_extracts_unique_colors(self):
        """Should extract unique colors from image data."""
        # Mock PIL Image
        mock_image = Mock()
        mock_image.getdata.return_value = [
            (255, 0, 0, 255),
            (0, 255, 0, 255),
            (255, 0, 0, 255),  # Duplicate
            (0, 0, 255, 255),
        ]
        
        result = extract_unique_colors(mock_image)
        
        # Should have 3 unique colors, sorted
        assert len(result) == 3
        assert (0, 0, 255, 255) in result
        assert (0, 255, 0, 255) in result
        assert (255, 0, 0, 255) in result
        
    def test_returns_sorted_colors(self):
        """Should return colors in sorted order."""
        mock_image = Mock()
        mock_image.getdata.return_value = [
            (255, 255, 255, 255),
            (0, 0, 0, 255),
            (128, 128, 128, 255),
        ]
        
        result = extract_unique_colors(mock_image)
        
        # Verify sorted order
        assert result == sorted(result)


class TestBuildIdentityMapping:
    """Tests for build_identity_mapping function."""
    
    def test_creates_identity_mapping(self):
        """Should create a mapping where each color maps to itself."""
        colors = [
            (255, 0, 0, 255),
            (0, 255, 0, 255),
            (0, 0, 255, 255),
        ]
        
        result = build_identity_mapping(colors)
        
        assert len(result) == 3
        for color in colors:
            assert result[color] == color
            
    def test_empty_input(self):
        """Should handle empty color list."""
        result = build_identity_mapping([])
        assert result == {}


class TestApplyColorMapping:
    """Tests for apply_color_mapping function."""
    
    def test_applies_color_mapping(self):
        """Should replace colors according to mapping."""
        # Create mock image with pixel data
        mock_image = Mock()
        mock_copy = Mock()
        mock_image.copy.return_value = mock_copy
        mock_copy.width = 2
        mock_copy.height = 2
        
        # Mock pixel access
        pixels = {}
        pixels[(0, 0)] = (255, 0, 0, 255)
        pixels[(1, 0)] = (0, 255, 0, 255)
        pixels[(0, 1)] = (255, 0, 0, 255)
        pixels[(1, 1)] = (0, 0, 255, 255)
        
        def getitem(key):
            return pixels.get(key)
        
        def setitem(key, value):
            pixels[key] = value
        
        mock_pixels = Mock()
        mock_pixels.__getitem__ = Mock(side_effect=getitem)
        mock_pixels.__setitem__ = Mock(side_effect=setitem)
        mock_copy.load.return_value = mock_pixels
        
        # Define color mapping: red -> blue
        color_mapping = {
            (255, 0, 0, 255): (0, 0, 255, 255)
        }
        
        result = apply_color_mapping(mock_image, color_mapping)
        
        # Verify the copy was made
        mock_image.copy.assert_called_once()
        
        # Red pixels should be changed to blue
        assert pixels[(0, 0)] == (0, 0, 255, 255)
        assert pixels[(0, 1)] == (0, 0, 255, 255)
        
        # Other colors should remain unchanged
        assert pixels[(1, 0)] == (0, 255, 0, 255)


class TestSaveImages:
    """Tests for save_images function."""
    
    def test_saves_all_images(self):
        """Should save all image records to the output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Create mock image records
            mock_image = Mock()
            mock_image.save = Mock()
            
            records = [
                ImageRecord(
                    path=Path("test1.png"),
                    original=mock_image,
                    modified=mock_image,
                ),
                ImageRecord(
                    path=Path("test2.png"),
                    original=mock_image,
                    modified=mock_image,
                ),
            ]
            
            count = save_images(records, output_dir)
            
            assert count == 2
            # Verify save was called for each record
            assert mock_image.save.call_count == 2
            
    def test_adds_modified_prefix(self):
        """Should add 'modified_' prefix to saved filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            mock_image = Mock()
            saved_paths = []
            
            def capture_save(path, **kwargs):
                saved_paths.append(path)
            
            mock_image.save = Mock(side_effect=capture_save)
            
            record = ImageRecord(
                path=Path("original.png"),
                original=mock_image,
                modified=mock_image,
            )
            
            save_images([record], output_dir)
            
            # Check that the saved path has the prefix
            assert len(saved_paths) == 1
            assert saved_paths[0].name == "modified_original.png"
            
    def test_uses_png_format(self):
        """Should save images in PNG format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            mock_image = Mock()
            record = ImageRecord(
                path=Path("test.jpg"),
                original=mock_image,
                modified=mock_image,
            )
            
            save_images([record], output_dir)
            
            # Verify PNG format was specified
            mock_image.save.assert_called_once()
            call_kwargs = mock_image.save.call_args[1]
            assert call_kwargs.get('format') == 'PNG'
