"""
Unit tests for the Blender albedo export library.
"""

from pathlib import Path

import pytest
from PIL import Image

from OV_Libs.ExportLib.blender_export import (
    batch_export_albedo,
    CONFLICT_NUMERIC_SUFFIX,
    CONFLICT_OVERWRITE,
    CONFLICT_POLICIES,
    CONFLICT_PROMPT,
    ExportConflictError,
    export_albedo,
    render_filename,
    resolve_output_path,
)


def make_image(color=(10, 20, 30, 255)):
    return Image.new("RGBA", (4, 4), color)


class TestResolveOutputPath:

    def test_overwrite_returns_same_path_even_if_exists(self, tmp_path):
        existing = tmp_path / "a.png"
        existing.touch()
        assert resolve_output_path(tmp_path, "a.png", CONFLICT_OVERWRITE) == existing

    def test_fresh_file_never_conflicts(self, tmp_path):
        assert resolve_output_path(tmp_path, "new.png", CONFLICT_PROMPT) == tmp_path / "new.png"

    def test_numeric_suffix_chain(self, tmp_path):
        for name in ("a.png", "a_001.png", "a_002.png"):
            (tmp_path / name).touch()
        result = resolve_output_path(
            tmp_path, "a.png", CONFLICT_NUMERIC_SUFFIX, suffix_start=1, suffix_pad=3
        )
        assert result.name == "a_003.png"

    def test_suffix_custom_start_and_pad(self, tmp_path):
        (tmp_path / "a.png").touch()
        result = resolve_output_path(
            tmp_path, "a.png", CONFLICT_NUMERIC_SUFFIX, suffix_start=5, suffix_pad=2
        )
        assert result.name == "a_05.png"

    def test_prompt_accepts_candidate(self, tmp_path):
        existing = tmp_path / "a.png"
        existing.touch()
        result = resolve_output_path(
            tmp_path, "a.png", CONFLICT_PROMPT, prompt_callback=lambda p: p
        )
        assert result == existing

    def test_prompt_decline_raises(self, tmp_path):
        (tmp_path / "a.png").touch()
        with pytest.raises(ExportConflictError):
            resolve_output_path(tmp_path, "a.png", CONFLICT_PROMPT, prompt_callback=lambda p: None)

    def test_prompt_redirects_to_new_name(self, tmp_path):
        (tmp_path / "a.png").touch()
        redirected = tmp_path / "other.png"
        result = resolve_output_path(
            tmp_path, "a.png", CONFLICT_PROMPT, prompt_callback=lambda p: redirected
        )
        assert result == redirected

    def test_prompt_without_callback_raises_value_error(self, tmp_path):
        (tmp_path / "a.png").touch()
        with pytest.raises(ValueError):
            resolve_output_path(tmp_path, "a.png", CONFLICT_PROMPT)

    def test_unknown_policy_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            resolve_output_path(tmp_path, "a.png", "clobber")


class TestRenderFilename:

    def test_formats_context(self):
        assert render_filename("{p}_{i}", {"p": "x", "i": 2}, ".png") == "x_2.png"

    def test_normalizes_extension(self):
        assert render_filename("f{ }".replace("{ }", ""), {}, "JPG") == "f.jpg"
        assert render_filename("f", {}, "png") == "f.png"

    def test_missing_key_raises_keyerror(self):
        with pytest.raises(KeyError):
            render_filename("{missing_key}", {}, "png")


class TestExportAlbedo:

    def test_writes_png_and_creates_dirs(self, tmp_path):
        out_dir = tmp_path / "nested" / "albedo"
        result = export_albedo(make_image(), out_dir, context={"project_name": "P"})
        assert result == out_dir / "P_BaseColor.png"
        assert result.is_file()
        reopened = Image.open(result)
        assert reopened.size == (4, 4)

    def test_overwrite_policy_replaces_bytes(self, tmp_path):
        target_dir = tmp_path
        first = export_albedo(make_image((0, 0, 0, 255)), target_dir, context={"project_name": "P"})
        before = first.read_bytes()
        second = export_albedo(make_image((255, 255, 255, 255)), target_dir, context={"project_name": "P"})
        assert first == second
        assert second.read_bytes() != before

    def test_jpg_flattens_alpha_to_rgb(self, tmp_path):
        result = export_albedo(
            make_image(), tmp_path, context={"project_name": "P"},
            save_format="JPG", quality=90,
        )
        assert result.suffix == ".jpg"
        opened = Image.open(result)
        assert opened.mode == "RGB"

    def test_input_not_mutated(self, tmp_path):
        source = make_image()
        original = source.tobytes()
        export_albedo(source, tmp_path, context={"project_name": "P"}, save_format="JPG")
        assert source.tobytes() == original

    def test_bad_policy_rejected_before_write(self, tmp_path):
        with pytest.raises(ValueError):
            export_albedo(make_image(), tmp_path, conflict_policy="nuke")


class TestBatchExportAlbedo:

    def test_batch_writes_all_sorted(self, tmp_path):
        images = {"b": make_image(), "a": make_image()}
        written, errors = batch_export_albedo(
            images, tmp_path, context={"project_name": "Prj"}
        )
        assert errors == []
        assert list(written.keys()) == ["a", "b"]
        assert written["a"].name == "Prj_a_BaseColor.png"

    def test_batch_collects_errors_without_aborting(self, tmp_path):
        (tmp_path / "Prj_a_BaseColor.png").write_bytes(b"occupied")
        written, errors = batch_export_albedo(
            {"a": make_image(), "b": make_image()},
            tmp_path,
            context={"project_name": "Prj"},
            conflict_policy=CONFLICT_PROMPT,
        )
        assert len(errors) == 1 and "a" in errors[0]
        assert set(written.keys()) == {"b"}

    def test_policies_constant_complete(self):
        assert set(CONFLICT_POLICIES) == {
            CONFLICT_OVERWRITE, CONFLICT_NUMERIC_SUFFIX, CONFLICT_PROMPT,
        }
