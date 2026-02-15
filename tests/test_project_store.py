"""
Unit tests for project_store module.

Tests project file creation, loading, and saving operations.
"""

import json
import tempfile
from pathlib import Path

import pytest

from OV_Libs.ProjStoreLib.project_store import (
    create_project_file,
    list_project_files,
    load_project_name,
    load_project_data,
    save_project_data,
    get_projects_dir,
    SCHEMA_VERSION,
)


class TestGetProjectsDir:
    """Tests for get_projects_dir function."""
    
    def test_creates_projects_directory(self):
        """Should create Projects directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            projects_dir = get_projects_dir(base_dir)
            
            assert projects_dir.exists()
            assert projects_dir.is_dir()
            assert projects_dir.name == "Projects"
            
    def test_returns_existing_directory(self):
        """Should return existing Projects directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            # Create directory first
            expected = base_dir / "Projects"
            expected.mkdir()
            
            projects_dir = get_projects_dir(base_dir)
            
            assert projects_dir == expected


class TestListProjectFiles:
    """Tests for list_project_files function."""
    
    def test_lists_ovproj_files(self):
        """Should list all .ovproj files in Projects directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            projects_dir = get_projects_dir(base_dir)
            
            # Create test files
            (projects_dir / "project1.ovproj").touch()
            (projects_dir / "project2.ovproj").touch()
            (projects_dir / "not_a_project.txt").touch()
            
            files = list_project_files(base_dir)
            
            assert len(files) == 2
            assert all(f.suffix == ".ovproj" for f in files)
            
    def test_returns_sorted_list(self):
        """Should return files in sorted order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            projects_dir = get_projects_dir(base_dir)
            
            # Create files in non-alphabetical order
            (projects_dir / "zebra.ovproj").touch()
            (projects_dir / "alpha.ovproj").touch()
            (projects_dir / "beta.ovproj").touch()
            
            files = list_project_files(base_dir)
            
            names = [f.name for f in files]
            assert names == sorted(names)


class TestCreateProjectFile:
    """Tests for create_project_file function."""
    
    def test_creates_valid_project_file(self):
        """Should create a valid project file with proper structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            project_name = "Test Project"
            
            project_path = create_project_file(base_dir, project_name)
            
            assert project_path.exists()
            assert project_path.suffix == ".ovproj"
            
            # Verify JSON structure
            data = json.loads(project_path.read_text())
            assert data["schema_version"] == SCHEMA_VERSION
            assert data["name"] == project_name
            assert "created_at" in data
            assert "image_paths" in data
            assert "filter_stacks" in data
            assert "node_graph" in data
            assert "output_presets" in data
            
    def test_sanitizes_filename(self):
        """Should sanitize special characters in project name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            project_name = "Test/Project*Name?"
            
            project_path = create_project_file(base_dir, project_name)
            
            # Filename should not contain special characters
            assert "/" not in project_path.name
            assert "*" not in project_path.name
            assert "?" not in project_path.name
            
    def test_handles_duplicate_names(self):
        """Should add numeric suffix for duplicate names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            project_name = "Duplicate"
            
            path1 = create_project_file(base_dir, project_name)
            path2 = create_project_file(base_dir, project_name)
            path3 = create_project_file(base_dir, project_name)
            
            assert path1.name == "Duplicate.ovproj"
            assert path2.name == "Duplicate_1.ovproj"
            assert path3.name == "Duplicate_2.ovproj"


class TestLoadProjectName:
    """Tests for load_project_name function."""
    
    def test_loads_project_name(self):
        """Should load project name from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            expected_name = "My Project"
            
            project_path = create_project_file(base_dir, expected_name)
            loaded_name = load_project_name(project_path)
            
            assert loaded_name == expected_name
            
    def test_returns_stem_for_invalid_file(self):
        """Should return filename stem if file is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_file = Path(tmpdir) / "invalid.ovproj"
            invalid_file.write_text("not valid json")
            
            name = load_project_name(invalid_file)
            
            assert name == "invalid"


class TestLoadProjectData:
    """Tests for load_project_data function."""
    
    def test_loads_valid_project_data(self):
        """Should load and validate project data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            project_path = create_project_file(base_dir, "Test")
            
            data = load_project_data(project_path)
            
            assert isinstance(data, dict)
            assert data["schema_version"] == SCHEMA_VERSION
            assert "name" in data
            assert "node_graph" in data
            assert "nodes" in data["node_graph"]
            assert "connections" in data["node_graph"]
            
    def test_provides_defaults_for_invalid_file(self):
        """Should provide default values for invalid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_file = Path(tmpdir) / "invalid.ovproj"
            invalid_file.write_text("{}")
            
            data = load_project_data(invalid_file)
            
            # Should have default values
            assert "schema_version" in data
            assert "name" in data
            assert "node_graph" in data
            assert "nodes" in data["node_graph"]
            

class TestSaveProjectData:
    """Tests for save_project_data function."""
    
    def test_saves_project_data(self):
        """Should save project data to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_file = Path(tmpdir) / "test.ovproj"
            
            test_data = {
                "name": "Test Project",
                "custom_field": "value",
            }
            
            save_project_data(project_file, test_data)
            
            assert project_file.exists()
            
            # Verify data was saved
            loaded_data = json.loads(project_file.read_text())
            assert loaded_data["name"] == "Test Project"
            assert loaded_data["custom_field"] == "value"
            assert loaded_data["schema_version"] == SCHEMA_VERSION
