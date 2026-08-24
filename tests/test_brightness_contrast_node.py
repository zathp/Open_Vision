"""
Unit tests for the Brightness/Contrast filter and node executor.
"""

import numpy as np
from PIL import Image

import pytest

from OV_Libs.ImageEditingLib.brightness_contrast_filter import (
    apply_brightness,
    apply_brightness_contrast,
    apply_contrast,
)
from OV_Libs.NodesLib.brightness_contrast_node import (
    BrightnessContrastNodeConfig,
    execute_brightness_contrast_node,
)


def grey_image(value=128, size=(4, 4)):
    return Image.new("RGBA", size, (value, value, value, 255))


class TestFilter:

    def test_identity_factors_return_same_pixels(self):
        source = grey_image(100)
        result = np.array(apply_brightness_contrast(source))
        assert np.array_equal(result, np.array(source.convert("RGBA")))

    def test_brightness_zero_makes_black(self):
        result = np.array(apply_brightness(grey_image(200), 0.0))
        assert result[:, :, :3].max() == 0
        assert (result[:, :, 3] == 255).all()

    def test_negative_factor_raises(self):
        with pytest.raises(ValueError):
            apply_brightness(grey_image(), -1.0)
        with pytest.raises(ValueError):
            apply_contrast(grey_image(), -1.0)

    def test_input_not_mutated(self):
        source = grey_image(90)
        original = source.tobytes()
        apply_brightness_contrast(source, brightness=2.0, contrast=2.0)
        assert source.tobytes() == original

    def test_contrast_one_is_identity(self):
        source = grey_image(60)
        assert np.array_equal(np.array(apply_contrast(source)), np.array(source.convert("RGBA")))


class TestNodeExecutor:

    def test_requires_input(self):
        with pytest.raises(ValueError):
            execute_brightness_contrast_node({"brightness": 1.0}, [])

    def test_rejects_non_image(self):
        with pytest.raises(TypeError):
            execute_brightness_contrast_node({}, ["not-an-image"])

    def test_applies_parameters(self):
        source = grey_image(100)
        result = execute_brightness_contrast_node(
            {"brightness": 1.5, "contrast": 1.0}, [source]
        )
        center = int(np.array(result)[0, 0][0])
        assert abs(center - 150) <= 3

    def test_config_roundtrip(self):
        config = BrightnessContrastNodeConfig(node_id="bc-9", brightness=0.5, contrast=1.4)
        restored = BrightnessContrastNodeConfig.from_dict(config.to_dict())
        assert restored == config


class TestRegistryIntegration:

    def test_registered_in_default_registry(self):
        from OV_Libs.ProjStoreLib.node_executors import get_default_registry

        registry = get_default_registry()
        assert registry.has_executor("Brightness Contrast")
        metadata = registry.get_metadata("Brightness Contrast")
        assert metadata["input_count"] == 1
        assert metadata["output_count"] == 1

    def test_executes_via_registry(self):
        from OV_Libs.ProjStoreLib.node_executors import get_default_registry

        result = get_default_registry().execute(
            "Brightness Contrast",
            {"brightness": 1.0, "contrast": 1.0},
            [grey_image(50)],
        )
        assert np.array_equal(np.array(result), np.array(grey_image(50)))
