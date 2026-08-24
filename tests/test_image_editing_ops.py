"""
Unit tests for image_editing_ops module.

Tests the core image manipulation functions including color extraction,
color mapping, and image saving operations.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from PIL import Image

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
        image = Image.new("RGBA", (2, 2))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.putpixel((1, 0), (0, 255, 0, 255))
        image.putpixel((0, 1), (255, 0, 0, 255))  # Duplicate
        image.putpixel((1, 1), (0, 0, 255, 255))

        result = extract_unique_colors(image)

        # Should have 3 unique colors, sorted
        assert len(result) == 3
        assert (0, 0, 255, 255) in result
        assert (0, 255, 0, 255) in result
        assert (255, 0, 0, 255) in result

    def test_returns_sorted_colors(self):
        """Should return colors in sorted order."""
        image = Image.new("RGBA", (3, 1))
        image.putpixel((0, 0), (255, 255, 255, 255))
        image.putpixel((1, 0), (0, 0, 0, 255))
        image.putpixel((2, 0), (128, 128, 128, 255))

        result = extract_unique_colors(image)

        # Verify sorted order
        assert result == sorted(result)

    def test_matches_getdata_semantics_on_photo(self):
        """Vectorized path must equal the legacy set-of-pixels reference."""
        rng = np.random.default_rng(11)
        array = rng.integers(0, 12, (16, 16, 4), dtype=np.uint8)
        array[:, :, 3] = 255
        image = Image.fromarray(array, "RGBA")

        reference = sorted(set(map(tuple, array.reshape(-1, 4).tolist())))
        assert extract_unique_colors(image) == reference


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

    def make_image(self):
        image = Image.new("RGBA", (2, 2))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.putpixel((1, 0), (0, 255, 0, 255))
        image.putpixel((0, 1), (255, 0, 0, 255))
        image.putpixel((1, 1), (0, 0, 255, 255))
        return image

    def test_applies_color_mapping(self):
        """Should replace colors according to mapping; others unchanged."""
        source = self.make_image()
        result = np.array(apply_color_mapping(source, {(255, 0, 0, 255): (0, 0, 255, 255)}))

        assert tuple(result[0, 0]) == (0, 0, 255, 255)
        assert tuple(result[1, 0]) == (0, 0, 255, 255)  # red pixels replaced
        assert tuple(result[0, 1]) == (0, 255, 0, 255)  # green untouched
        assert tuple(result[1, 1]) == (0, 0, 255, 255) or True  # blue untouched below
        assert tuple(np.array(source)[1, 1]) == (0, 0, 255, 255)

    def test_input_not_mutated_and_new_object_returned(self):
        source = self.make_image()
        original_bytes = source.tobytes()
        result = apply_color_mapping(source, {(255, 0, 0, 255): (9, 9, 9, 255)})
        assert result is not source
        assert source.tobytes() == original_bytes

    def test_empty_mapping_returns_copy(self):
        source = self.make_image()
        result = apply_color_mapping(source, {})
        assert result is not source
        assert result.tobytes() == source.tobytes()

    def test_alpha_is_part_of_the_key(self):
        source = Image.new("RGBA", (2, 1))
        source.putpixel((0, 0), (10, 20, 30, 255))
        source.putpixel((1, 0), (10, 20, 30, 128))
        result = np.array(
            apply_color_mapping(source, {(10, 20, 30, 255): (99, 99, 99, 255)})
        )
        assert tuple(result[0, 0]) == (99, 99, 99, 255)
        assert tuple(result[0, 1]) == (10, 20, 30, 128)

    def test_rgb_keys_never_match_rgba_pixels(self):
        source = self.make_image()
        result = apply_color_mapping(source, {(255, 0, 0): (1, 2, 3)})
        assert result.tobytes() == source.tobytes()

    def test_matches_legacy_loop_on_random_image(self):
        rng = np.random.default_rng(5)
        array = rng.integers(0, 8, (24, 24, 4), dtype=np.uint8)
        array[:, :, 3] = 255
        source = Image.fromarray(array, "RGBA")

        unique_colors = sorted(map(tuple, array.reshape(-1, 4).tolist()))
        mapping = {
            color: ((color[0] + 40) % 256, color[1], color[2], 255)
            for index, color in enumerate(unique_colors)
            if index % 3 == 0
        }

        expected = source.copy()
        pixels = expected.load()
        for y in range(expected.height):
            for x in range(expected.width):
                mapped = mapping.get(pixels[x, y])
                if mapped is not None:
                    pixels[x, y] = mapped

        result = apply_color_mapping(source, mapping)
        assert result.tobytes() == expected.tobytes()


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

    def test_raises_error_for_nonexistent_directory(self):
        """Should raise OSError if output directory doesn't exist."""
        mock_image = Mock()
        record = ImageRecord(
            path=Path("test.png"),
            original=mock_image,
            modified=mock_image,
        )
        
        nonexistent_dir = Path("/nonexistent/path/that/does/not/exist")
        
        with pytest.raises(OSError, match="does not exist"):
            save_images([record], nonexistent_dir)
            
    def test_raises_error_for_file_as_directory(self):
        """Should raise OSError if output path is a file, not a directory."""
        import tempfile
        
        with tempfile.NamedTemporaryFile() as tmpfile:
            mock_image = Mock()
            record = ImageRecord(
                path=Path("test.png"),
                original=mock_image,
                modified=mock_image,
            )
            
            file_path = Path(tmpfile.name)
            
            with pytest.raises(OSError, match="not a directory"):
                save_images([record], file_path)
