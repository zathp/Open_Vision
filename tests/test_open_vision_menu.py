"""
Unit tests for the Open Vision project menu dual-type flow.

These tests require PyQt5; they are skipped automatically when the
Qt stack is unavailable (e.g. headless environments).
"""

import json
import sys
import types
import builtins

import pytest

qt = pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QInputDialog  # noqa: E402

import open_vision  # noqa: E402
from OV_Libs.ProjStoreLib.project_store import (  # noqa: E402
    create_paint_project_file,
    create_project_file,
)


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


class FakeEditor:
    instances = []

    def __init__(self, project_path=None):
        self.project_path = project_path
        FakeEditor.instances.append(self)

    def show(self):
        pass


@pytest.fixture
def fake_editor(monkeypatch):
    FakeEditor.instances = []
    module = types.ModuleType("paint_editor_window")
    module.PaintEditorWindow = FakeEditor
    monkeypatch.setitem(sys.modules, "paint_editor_window", module)
    monkeypatch.setattr(open_vision, "NodeEditorWindow", FakeEditor)
    return FakeEditor


def make_window(qapp, tmp_path):
    window = open_vision.OpenVisionMainWindow()
    window.base_dir = tmp_path
    return window


def patch_create_dialogs(monkeypatch, name="Proj", type_index=0):
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: (name, True))
    )
    items = ["Node Graph (.ovproj)", "Paint (.ovpaint)"]
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda *a, **k: (items[type_index], True)),
    )


def create_dialog_driven(qapp, tmp_path):
    window = make_window(qapp, tmp_path)
    try:
        window.create_project()
    finally:
        window.close()


class TestCreateProjectTypeSelector:

    def test_node_graph_choice_creates_ovproj(self, monkeypatch, qapp, tmp_path):
        patch_create_dialogs(monkeypatch, "NodeProj", type_index=0)
        create_dialog_driven(qapp, tmp_path)
        created = list((tmp_path / "Projects").glob("*.ovproj"))
        assert len(created) == 1
        payload = json.loads(created[0].read_text(encoding="utf-8"))
        assert payload["name"] == "NodeProj"

    def test_paint_choice_creates_ovpaint(self, monkeypatch, qapp, tmp_path):
        patch_create_dialogs(monkeypatch, "PaintProj", type_index=1)
        create_dialog_driven(qapp, tmp_path)
        created = list((tmp_path / "Projects").glob("*.ovpaint"))
        assert len(created) == 1

    def test_cancel_type_aborts(self, monkeypatch, qapp, tmp_path):
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("X", True)))
        monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("", False)))
        create_dialog_driven(qapp, tmp_path)
        projects_dir = tmp_path / "Projects"
        assert not projects_dir.exists() or not any(projects_dir.iterdir())


class TestListingAndLaunch:

    def test_listing_merges_both_types_with_labels(self, qapp, tmp_path):
        create_project_file(tmp_path, "GraphOne")
        create_paint_project_file(tmp_path, "PaintOne")
        window = make_window(qapp, tmp_path)
        try:
            window.refresh_projects()
            labels = [
                window.projects_list.item(i).text()
                for i in range(window.projects_list.count())
            ]
            paint_label = next(text for text in labels if "PaintOne" in text)
            graph_label = next(text for text in labels if "GraphOne" in text)
            assert "· Paint" in paint_label
            assert "· Node Graph" in graph_label
        finally:
            window.close()

    def test_launch_routes_by_suffix(self, qapp, tmp_path, fake_editor):
        window = make_window(qapp, tmp_path)
        try:
            paint_path = create_paint_project_file(tmp_path, "Routed")
            window.launch_project(paint_path)
            assert fake_editor.instances[-1].project_path == paint_path

            graph_path = create_project_file(tmp_path, "G")
            window.launch_project(graph_path)
            assert fake_editor.instances[-1].project_path == graph_path
        finally:
            window.close()

    def test_launch_shows_warning_when_paint_module_missing(
        self, qapp, tmp_path, monkeypatch
    ):
        warnings = []
        monkeypatch.setattr(
            open_vision.QMessageBox, "warning", staticmethod(lambda *a: warnings.append(a))
        )

        real_import = builtins.__import__

        def blocking_import(name, *args, **kwargs):
            if name == "paint_editor_window":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        saved_module = sys.modules.pop("paint_editor_window", None)
        monkeypatch.setattr(builtins, "__import__", blocking_import)
        try:
            window = make_window(qapp, tmp_path)
            paint_path = create_paint_project_file(tmp_path, "NoEditor")
            window.launch_project(paint_path)
            window.close()
        finally:
            if saved_module is not None:
                sys.modules["paint_editor_window"] = saved_module

        assert len(warnings) == 1
