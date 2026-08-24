"""
Unit tests for paint project storage and schema version helpers.

Tests .ovpaint project creation/loading, schema version compatibility
checks, and missing image path filtering.
"""

import json
import tempfile
from pathlib import Path

from OV_Libs.ProjStoreLib.project_store import (
    check_schema_version,
    create_paint_project_file,
    filter_missing_image_paths,
    get_paint_layers_dir,
    list_paint_project_files,
    load_paint_project_data,
    load_project_name,
    save_paint_project_data,
    SCHEMA_VERSION,
)


class TestCheckSchemaVersion:

    def test_matching_version_is_ok(self):
        status, message = check_schema_version({"schema_version": SCHEMA_VERSION})
        assert status == "ok"
        assert message == ""

    def test_missing_version_defaults_to_ok(self):
        status, _ = check_schema_version({})
        assert status == "ok"

    def test_older_version_reports_upgrade(self):
        status, message = check_schema_version({"schema_version": SCHEMA_VERSION - 1})
        assert status == "upgrade"
        assert str(SCHEMA_VERSION - 1) in message

    def test_newer_version_unsupported(self):
        status, message = check_schema_version({"schema_version": SCHEMA_VERSION + 5})
        assert status == "unsupported"
        assert "newer" in message

    def test_invalid_version_treated_as_upgrade(self):
        status, _ = check_schema_version({"schema_version": "abc"})
        assert status == "upgrade"


class TestFilterMissingImagePaths:

    def test_splits_existing_and_missing(self, tmp_path):
        existing_file = tmp_path / "present.png"
        existing_file.touch()

        existing, missing = filter_missing_image_paths(
            [str(existing_file), str(tmp_path / "gone.png")]
        )
        assert existing == [str(existing_file)]
        assert missing == [str(tmp_path / "gone.png")]

    def test_empty_input(self):
        assert filter_missing_image_paths([]) == ([], [])
        assert filter_missing_image_paths(None) == ([], [])

    def test_preserves_order(self, tmp_path):
        first = tmp_path / "a.png"
        second = tmp_path / "b.png"
        first.touch()
        second.touch()
        existing, _ = filter_missing_image_paths([str(second), str(first)])
        assert existing == [str(second), str(first)]


class TestCreatePaintProjectFile:

    def test_creates_ovpaint_file_with_defaults(self, tmp_path):
        project_path = create_paint_project_file(tmp_path, "My Paint")

        assert project_path.exists()
        assert project_path.suffix == ".ovpaint"
        assert project_path.parent.name == "Projects"

        payload = json.loads(project_path.read_text(encoding="utf-8"))
        assert payload["name"] == "My Paint"
        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["canvas_width"] > 0
        assert payload["canvas_height"] > 0
        assert payload["layers"] == []
        assert payload["tool_preferences"] == {}
        assert payload["export_settings"] == {}

    def test_blank_name_falls_back_to_new_project(self, tmp_path):
        project_path = create_paint_project_file(tmp_path, "///")
        assert project_path.stem.startswith("new_project")

    def test_avoids_filename_collision(self, tmp_path):
        first = create_paint_project_file(tmp_path, "Sketch")
        second = create_paint_project_file(tmp_path, "Sketch")
        assert first != second
        assert both_exist(first, second)


def both_exist(*paths):
    return all(p.exists() for p in paths)


class TestListPaintProjectFiles:

    def test_lists_only_ovpaint_files(self, tmp_path):
        create_paint_project_file(tmp_path, "Paint A")
        create_paint_project_file(tmp_path, "Paint B")
        (tmp_path / "Projects" / "ignored.ovproj").touch()

        files = list_paint_project_files(tmp_path)
        names = {f.suffix for f in files}
        assert names == {".ovpaint"}
        assert len(files) == 2


class TestLoadSavePaintProjectData:

    def test_load_fills_defaults_on_corrupt_file(self, tmp_path):
        project_path = tmp_path / "broken.ovpaint"
        project_path.write_text("not json at all", encoding="utf-8")

        payload = load_paint_project_data(project_path)
        assert payload["name"] == "broken"
        assert payload["layers"] == []
        assert payload["canvas_width"] > 0

    def test_roundtrip_preserves_data(self, tmp_path):
        project_path = tmp_path / "round.ovpaint"
        create_payload = load_paint_project_data(create_paint_project_file(tmp_path.parent, "x"))

        create_payload["canvas_width"] = 320
        create_payload["layers"] = [
            {"id": "l1", "name": "Base", "visible": True, "opacity": 200,
             "image_file": "round_layers/l1.png"}
        ]
        save_paint_project_data(project_path, create_payload)

        loaded = load_paint_project_data(project_path)
        assert loaded["canvas_width"] == 320
        assert loaded["layers"][0]["name"] == "Base"
        assert loaded["layers"][0]["opacity"] == 200

    def test_layer_normalization(self, tmp_path):
        project_path = tmp_path / "norm.ovpaint"
        project_path.write_text(json.dumps({
            "layers": [
                {"name": "NoId"},
                {"id": "keep", "name": "Kept", "visible": False, "opacity": 999},
                "not-a-dict",
            ]
        }), encoding="utf-8")

        layers = load_paint_project_data(project_path)["layers"]
        assert len(layers) == 2
        assert len(layers[0]["id"]) > 0
        assert layers[0]["opacity"] == 255
        assert layers[1]["visible"] is False
        assert layers[1]["opacity"] == 255

    def test_save_stamps_schema_version(self, tmp_path):
        project_path = tmp_path / "stamp.ovpaint"
        save_paint_project_data(project_path, {"name": "Stamp"})
        payload = json.loads(project_path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == SCHEMA_VERSION


class TestPaintLayersDir:

    def test_creates_sidecar_directory(self, tmp_path):
        project_path = tmp_path / "proj.ovpaint"
        project_path.touch()

        layers_dir = get_paint_layers_dir(project_path)
        assert layers_dir == tmp_path / "proj_layers"
        assert layers_dir.is_dir()


class TestLoadProjectNameGeneric:

    def test_reads_name_from_ovpaint(self, tmp_path):
        project_path = create_paint_project_file(tmp_path, "Named Paint")
        assert load_project_name(project_path) == "Named Paint"

    def test_falls_back_to_stem(self, tmp_path):
        project_path = tmp_path / "Fallback.ovpaint"
        project_path.write_text("{ invalid", encoding="utf-8")
        assert load_project_name(project_path) == "Fallback"
