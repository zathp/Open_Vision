"""
Pytest configuration and shared fixtures for Open Vision tests.

This module provides shared test fixtures and configuration
used across multiple test modules.
"""

import pytest
from pathlib import Path


@pytest.fixture
def temp_project_dir(tmp_path):
    """
    Provide a temporary directory for project files.
    
    Args:
        tmp_path: Pytest's built-in temporary directory fixture
        
    Returns:
        Path object pointing to a temporary directory
    """
    return tmp_path


@pytest.fixture
def sample_rgba_colors():
    """
    Provide a list of sample RGBA color tuples for testing.
    
    Returns:
        List of (R, G, B, A) tuples with common test colors
    """
    return [
        (255, 0, 0, 255),    # Red
        (0, 255, 0, 255),    # Green
        (0, 0, 255, 255),    # Blue
        (255, 255, 255, 255),  # White
        (0, 0, 0, 255),      # Black
        (128, 128, 128, 255),  # Gray
    ]
