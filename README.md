# Open Vision

A PyQt5-based image editing and processing application with node-based workflow capabilities.

## Overview

Open Vision is a desktop application for image manipulation featuring:
- **Node Graph Projects**: Advanced node-based visual filter chaining and compositing
- **Paint Projects** (planned): Direct image editing with a tool palette interface
- Project-based workflow with persistent `.ovproj` files
- Color replacement and manipulation tools
- Extensible filter system

## Features

- **Project Management**: Create and manage multiple image editing projects
- **Node-Based Editing**: Visual node graph for chaining image operations
- **Color Manipulation**: Extract unique colors and apply color mappings
- **Batch Processing**: Process multiple images with consistent settings
- **Filter Stacking**: Apply and manage multiple filters in sequence

## Installation

### Requirements

- Python 3.7 or higher
- PyQt5
- Pillow (PIL)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/zathp/Open_Vision.git
cd Open_Vision
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

Start the main application:
```bash
python open_vision.py
```

This launches the Project Menu where you can:
- Create new projects
- Open existing `.ovproj` files
- Launch the node editor for a selected project

### Project Types

#### Node Graph Projects (.ovproj)
Advanced workflow for complex image processing:
- Visual node-based filter chaining
- Filter stack management
- Support for complex compositing operations
- Export for Blender texture maps (planned)

#### Paint Projects (.ovpaint) - Coming Soon
Direct image editing interface:
- Tool palette with brushes and selection tools
- Integration with Initial_Forms tools (Downsampler, Mirror, Region Selector, Color Replace)
- Layer-based editing
- Quick transformations

## Project Structure

```
Open_Vision/
├── open_vision.py              # Main application entry point
├── node_editor_window.py       # Node graph editor window
├── OV_Libs/                    # Core library modules
│   ├── ImageEditingLib/        # Image editing operations
│   │   ├── image_models.py
│   │   ├── image_editing_ops.py
│   │   └── image_editor_window.py
│   ├── ProjStoreLib/           # Project file management
│   │   └── project_store.py
│   ├── Initial_Forms/          # Standalone tools (legacy)
│   │   ├── Downsampler.py
│   │   ├── Mirror.py
│   │   ├── RegionSelector.py
│   │   └── Greenscreen2.py
│   └── pillow_compat.py        # PIL/Pillow compatibility layer
├── Projects/                   # User project files (created on first run)
└── requirements.txt            # Python dependencies
```

## Development

### Code Organization

The codebase follows SOLID principles with clear separation of concerns:
- **OV_Libs/ImageEditingLib**: Core image processing logic
- **OV_Libs/ProjStoreLib**: Project persistence and file I/O
- **OV_Libs/Initial_Forms**: Legacy standalone tools being integrated

### Contributing

Contributions are welcome! Please ensure:
- Code follows existing style and conventions
- Functions include type hints
- New features include documentation
- Complex operations have docstrings

## Documentation

Additional documentation available:
- [Features Overview](Features.txt)
- [TODO Roadmap](OPEN_VISION_TODO.md)
- [Feature Specifications](OPEN_VISION_FEATURES.md)
- [Building New Filters](BUILDING_NEW_FILTERS.md)
- [Pipeline Design](PIPELINE_EXECUTION_DESIGN.md)
- [Paint Project Design](PAINT_PROJECT_DESIGN.md)

## License

See repository for license information.

## Acknowledgments

Part of the SOLID Codebase milestone for improving code quality and maintainability.
