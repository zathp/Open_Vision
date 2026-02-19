"""
Constants and configuration values for Open Vision.

This module centralizes all constant values, magic numbers, and
configuration settings used throughout the application.
"""

# Project file constants
PROJECTS_DIR_NAME = "Projects"
PROJECT_EXTENSION = ".ovproj"
PAINT_PROJECT_EXTENSION = ".ovpaint"
SCHEMA_VERSION = 1

# Node graph constants
DEFAULT_NODE_WIDTH = 180
DEFAULT_NODE_HEIGHT = 70
DEFAULT_PORT_SIZE = 12
DEFAULT_PORT_OFFSET = 6

# UI constants
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 850
DEFAULT_PROJECT_WINDOW_WIDTH = 900
DEFAULT_PROJECT_WINDOW_HEIGHT = 580

# Node colors (Qt color strings)
NODE_BACKGROUND_COLOR = "#2d2d30"
NODE_BORDER_COLOR = "#8a8a8a"
NODE_TEXT_COLOR = "#f0f0f0"
INPUT_PORT_COLOR = "#9cdcfe"
INPUT_PORT_BORDER_COLOR = "#d0ebff"
OUTPUT_PORT_COLOR = "#6aeb8f"
OUTPUT_PORT_BORDER_COLOR = "#c8ffd8"

# Default node positions
DEFAULT_INPUT_NODE_X = 80.0
DEFAULT_INPUT_NODE_Y = 100.0
DEFAULT_PROCESS_NODE_X = 340.0
DEFAULT_PROCESS_NODE_Y = 240.0
DEFAULT_OUTPUT_NODE_X = 620.0
DEFAULT_OUTPUT_NODE_Y = 100.0

# File naming
OUTPUT_FILE_PREFIX = "modified_"
DEFAULT_OUTPUT_FORMAT = "PNG"

# Safe filename characters
SAFE_FILENAME_CHARS = "-_"
FILENAME_REPLACEMENT_CHAR = "_"

# Project field names
FIELD_SCHEMA_VERSION = "schema_version"
FIELD_NAME = "name"
FIELD_CREATED_AT = "created_at"
FIELD_IMAGE_PATHS = "image_paths"
FIELD_FILTER_STACKS = "filter_stacks"
FIELD_NODE_GRAPH = "node_graph"
FIELD_OUTPUT_PRESETS = "output_presets"
FIELD_NODES = "nodes"
FIELD_CONNECTIONS = "connections"

# Node/Connection field names
FIELD_NODE_ID = "id"
FIELD_NODE_TYPE = "type"
FIELD_NODE_X = "x"
FIELD_NODE_Y = "y"
FIELD_FROM_NODE = "from_node"
FIELD_FROM_PORT = "from_port"
FIELD_TO_NODE = "to_node"
FIELD_TO_PORT = "to_port"

# Port names
PORT_INPUT = "input"
PORT_OUTPUT = "output"

# Default node types
NODE_TYPE_INPUT = "Test Input"
NODE_TYPE_PROCESS = "Test Process"
NODE_TYPE_OUTPUT = "Test Output"
NODE_TYPE_DEFAULT = "Test Node"

# Image import node type
NODE_TYPE_IMAGE_IMPORT = "Image Import"

# Supported file formats
SUPPORTED_STANDARD_IMAGES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
SUPPORTED_MOVIES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
SUPPORTED_GIF = {".gif"}
