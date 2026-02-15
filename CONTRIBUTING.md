# Contributing to Open Vision

Thank you for your interest in contributing to Open Vision! This document provides guidelines and best practices for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Create a feature branch
5. Make your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.7 or higher
- Git
- A code editor with Python support (VS Code, PyCharm, etc.)

### Initial Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Open_Vision.git
cd Open_Vision

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run the application to verify setup
python open_vision.py
```

## Code Standards

### Style Guide

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Maximum line length: 120 characters
- Use descriptive variable names
- Write docstrings for all public functions and classes

### Code Formatting

We use Black for automatic code formatting:

```bash
# Format all Python files
black .

# Check formatting without making changes
black --check .
```

### Linting

Run linters before committing:

```bash
# Pylint
pylint OV_Libs/

# Flake8
flake8 OV_Libs/

# Type checking with mypy
mypy OV_Libs/
```

### Import Organization

Imports should be organized in the following order:
1. Standard library imports
2. Third-party library imports (PyQt5, PIL, etc.)
3. Local application imports (from OV_Libs)

Example:
```python
import json
from pathlib import Path
from typing import List

from PyQt5.QtWidgets import QWidget

from OV_Libs.ImageEditingLib import ImageRecord
```

## Project Structure

### Module Organization

```
OV_Libs/
├── ImageEditingLib/     # Core image editing functionality
├── ProjStoreLib/        # Project file persistence
├── Initial_Forms/       # Legacy tools being integrated
└── pillow_compat.py     # PIL compatibility layer
```

### Adding New Features

When adding new features:
1. Place code in the appropriate module
2. Follow the existing architectural patterns
3. Maintain separation of concerns (SOLID principles)
4. Add docstrings and type hints
5. Update relevant documentation

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def function_name(arg1: str, arg2: int) -> bool:
    """
    Brief description of the function.
    
    More detailed explanation if needed, describing what the
    function does and any important details.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When and why this is raised
    """
    pass
```

### Module Docstrings

Every Python module should have a docstring explaining its purpose:

```python
"""
Module name - Brief description

Detailed explanation of the module's purpose and contents.

Classes:
    ClassName: Brief description
    
Functions:
    function_name: Brief description
"""
```

## Testing

### Writing Tests

- Place tests in a `tests/` directory (when created)
- Name test files with `test_` prefix
- Use pytest for testing
- Aim for good test coverage of new code

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=OV_Libs --cov-report=html
```

## Commit Guidelines

### Commit Messages

Write clear, descriptive commit messages:

- Use present tense ("Add feature" not "Added feature")
- First line: brief summary (50 chars or less)
- Blank line, then detailed explanation if needed
- Reference issues/PRs when relevant

Good examples:
```
Add color mapping validation to image_editing_ops

- Validate color tuples are RGBA format
- Add error handling for invalid colors
- Update docstrings with validation info

Fixes #123
```

### Commit Scope

- Keep commits focused on a single change
- Don't mix refactoring with new features
- Commit working code (tests should pass)

## Pull Request Process

1. **Branch Naming**: Use descriptive branch names
   - `feature/description` for new features
   - `fix/description` for bug fixes
   - `refactor/description` for refactoring

2. **Before Submitting**:
   - Run linters and fix any issues
   - Ensure tests pass
   - Update documentation if needed
   - Verify the application runs correctly

3. **PR Description**:
   - Describe what changes were made and why
   - Reference any related issues
   - Include screenshots for UI changes
   - List any breaking changes

4. **Review Process**:
   - Address review feedback promptly
   - Keep the PR focused and reasonably sized
   - Be open to suggestions and discussion

## Code Review Checklist

When reviewing PRs, check for:

- [ ] Code follows style guidelines
- [ ] Type hints are present
- [ ] Docstrings are complete and accurate
- [ ] No unnecessary code changes
- [ ] Imports are properly organized
- [ ] Error handling is appropriate
- [ ] No hardcoded values (use constants)
- [ ] Code is maintainable and readable

## Project Roadmap

See [OPEN_VISION_TODO.md](OPEN_VISION_TODO.md) for the current roadmap and priorities.

Current focus areas:
- **Priority 0**: Baseline cleanup and project type support
- **Priority 1**: Project persistence MVP
- **Priority 2**: Core editing features

## Communication

- Use GitHub Issues for bug reports and feature requests
- Use PR comments for code-specific discussions
- Be respectful and constructive in all interactions

## Questions?

If you have questions about contributing:
1. Check existing documentation
2. Search closed issues/PRs for similar discussions
3. Open a new issue with your question

Thank you for contributing to Open Vision! 🎨
