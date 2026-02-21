"""
Output Node for Open Vision.

This node saves images to disk with support for dynamic filenames using
delimited tags for date, version, and numbering.

Supported tags (case-insensitive):
- {DATE} or {DATE:format} - Current date (default: YYYY-MM-DD)
- {TIME} or {TIME:format} - Current time (default: HH-MM-SS)
- {VERSION} or {VERSION:width} - Version number (default: 1, width: 0-pad width)
- {COUNTER} or {COUNTER:width} - Auto-incrementing counter (default: 0, width: 0-pad width)
- {DATETIME} - Combined date and time

Classes:
    OutputNodeConfig: Configuration for output node
    OutputNodeHandler: Handles file operations and tag substitution
    
Functions:
    execute_output_node: Pipeline executor for output nodes
    create_output_node: Helper to create output node dictionary
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import os

from OV_Libs.pillow_compat import Image


@dataclass
class OutputNodeConfig:
    """Configuration for output node execution.
    
    Attributes:
        output_path: Base output path or filename with optional tags
        save_format: Image format to save as (PNG, JPG, etc., default: PNG)
        quality: JPEG quality 1-100 (default: 95, only for JPG)
        version: Current version number (default: 1)
        auto_increment_counter: Auto-increment counter on each save (default: False)
        create_directories: Create output directories if they don't exist (default: True)
        overwrite: Overwrite existing files (default: False)
        base_directory: Optional base directory to restrict outputs (None = no restriction)
                       If set, validated paths must be within this directory tree
    """
    output_path: str = "output.png"
    save_format: str = "PNG"
    quality: int = 95
    version: int = 1
    auto_increment_counter: bool = False
    create_directories: bool = True
    overwrite: bool = False
    base_directory: Optional[str] = None
    _counter: int = 0  # Internal counter state
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutputNodeConfig":
        """Create from dictionary."""
        # Filter out most internal fields, but allow known persisted state
        filtered = {
            k: v
            for k, v in data.items()
            if k in cls.__dataclass_fields__
            and (not k.startswith('_') or k == "_counter")
        }
        return cls(**filtered)
    
    def get_save_kwargs(self) -> Dict[str, Any]:
        """Get PIL Image.save() kwargs based on format."""
        # PIL uses "JPEG" not "JPG"
        save_format = self.save_format.upper()
        if save_format == "JPG":
            save_format = "JPEG"
        
        kwargs = {"format": save_format}
        
        if save_format in ("JPG", "JPEG"):
            kwargs["quality"] = max(1, min(100, self.quality))
        
        return kwargs


class OutputNodeHandler:
    """Handles dynamic filename generation and file I/O for output nodes."""
    
    # Regex patterns for tag detection
    DATE_PATTERN = r'\{DATE(?::([^\}]*))?\}'
    TIME_PATTERN = r'\{TIME(?::([^\}]*))?\}'
    DATETIME_PATTERN = r'\{DATETIME(?::([^\}]*))?\}'
    VERSION_PATTERN = r'\{VERSION(?::([^\}]*))?\}'
    COUNTER_PATTERN = r'\{COUNTER(?::([^\}]*))?\}'
    
    # Default format strings
    DEFAULT_DATE_FORMAT = "%Y-%m-%d"
    DEFAULT_TIME_FORMAT = "%H-%M-%S"
    DEFAULT_DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
    
    def __init__(self, config: OutputNodeConfig):
        """Initialize handler with configuration."""
        self.config = config
        # Resolve and validate base directory if provided
        self._base_dir = None
        if config.base_directory:
            base_path = Path(config.base_directory)
            if not base_path.is_absolute():
                raise ValueError(f"base_directory must be an absolute path: {config.base_directory}")
            self._base_dir = base_path.resolve()
    
    def resolve_filename(self) -> Path:
        """
        Resolve the output filename with tag substitution and path validation.
        
        Returns:
            Path to the resolved output file
            
        Raises:
            ValueError: If path contains traversal sequences or is outside base_directory
        """
        filename = self.config.output_path
        
        # Replace tags in order
        filename = self._replace_datetime(filename)
        filename = self._replace_date(filename)
        filename = self._replace_time(filename)
        filename = self._replace_version(filename)
        filename = self._replace_counter(filename)
        
        # Validate and sanitize the path
        validated_path = self._validate_output_path(filename)
        
        return validated_path
    
    def _validate_output_path(self, path_str: str) -> Path:
        """
        Validate output path to prevent directory traversal attacks.
        
        Args:
            path_str: Path string to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValueError: If path contains dangerous sequences or is outside base_directory
        """
        # Create Path object  
        path = Path(path_str)
        
        # Check for potentially dangerous path components
        parts = path.parts
        for part in parts:
            # Check for parent directory references
            if part == "..":
                raise ValueError(
                    f"Path traversal detected: output_path contains '..': {path_str}"
                )
        
        # Resolve the path
        if path.is_absolute():
            resolved_path = path.resolve()
        else:
            # For relative paths with base_directory, resolve relative to base
            if self._base_dir:
                resolved_path = (self._base_dir / path).resolve()
            else:
                # Otherwise resolve relative to current directory
                resolved_path = path.resolve()
        
        # If base_directory is set, ensure the resolved path is within it
        if self._base_dir:
            try:
                # Check if resolved path is relative to base directory
                resolved_path.relative_to(self._base_dir)
            except ValueError:
                raise ValueError(
                    f"Security: output_path '{path_str}' resolves to '{resolved_path}' "
                    f"which is outside the allowed base directory '{self._base_dir}'"
                )
        
        return resolved_path
    
    def save_image(self, image: Any) -> Path:
        """
        Save image to disk with resolved filename.
        
        Args:
            image: PIL Image to save
            
        Returns:
            Path where image was saved
            
        Raises:
            ValueError: If file exists and overwrite=False
            OSError: If file cannot be written
        """
        # Ensure image is valid
        if not hasattr(image, "save"):
            raise TypeError(f"Expected PIL Image, got {type(image)}")
        
        output_file = self.resolve_filename()
        
        # Create directories if needed
        if self.config.create_directories:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check overwrite
        if output_file.exists() and not self.config.overwrite:
            raise ValueError(
                f"Output file already exists: {output_file}. "
                f"Set overwrite=True to replace."
            )
        
        # Save image
        try:
            kwargs = self.config.get_save_kwargs()
            # Convert RGBA to RGB for JPEG format
            if image.mode == "RGBA" and kwargs["format"] == "JPEG":
                image = image.convert("RGB")
            
            image.save(output_file, **kwargs)
        except Exception as e:
            raise OSError(f"Failed to save image to {output_file}: {str(e)}")
        
        # Auto-increment counter if enabled
        if self.config.auto_increment_counter:
            self.config._counter += 1
        
        return output_file
    
    def _replace_datetime(self, text: str) -> str:
        """Replace {DATETIME} tags."""
        def replacer(match):
            fmt = match.group(1) or self.DEFAULT_DATETIME_FORMAT
            try:
                return datetime.now().strftime(fmt)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid datetime format string '{fmt}' in {{DATETIME}} tag: {str(e)}"
                )
        
        return re.sub(self.DATETIME_PATTERN, replacer, text, flags=re.IGNORECASE)
    
    def _replace_date(self, text: str) -> str:
        """Replace {DATE} tags."""
        def replacer(match):
            fmt = match.group(1) or self.DEFAULT_DATE_FORMAT
            try:
                return datetime.now().strftime(fmt)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid date format string '{fmt}' in {{DATE}} tag: {str(e)}"
                )
        
        return re.sub(self.DATE_PATTERN, replacer, text, flags=re.IGNORECASE)
    
    def _replace_time(self, text: str) -> str:
        """Replace {TIME} tags."""
        def replacer(match):
            fmt = match.group(1) or self.DEFAULT_TIME_FORMAT
            try:
                return datetime.now().strftime(fmt)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid time format string '{fmt}' in {{TIME}} tag: {str(e)}"
                )
        
        return re.sub(self.TIME_PATTERN, replacer, text, flags=re.IGNORECASE)
    
    def _replace_version(self, text: str) -> str:
        """Replace {VERSION} tags."""
        def replacer(match):
            width_str = match.group(1) or "0"
            try:
                width = int(width_str)
            except ValueError:
                width = 0
            
            return str(self.config.version).zfill(width)
        
        return re.sub(self.VERSION_PATTERN, replacer, text, flags=re.IGNORECASE)
    
    def _replace_counter(self, text: str) -> str:
        """Replace {COUNTER} tags."""
        def replacer(match):
            width_str = match.group(1) or "0"
            try:
                width = int(width_str)
            except ValueError:
                width = 0
            
            return str(self.config._counter).zfill(width)
        
        return re.sub(self.COUNTER_PATTERN, replacer, text, flags=re.IGNORECASE)


def execute_output_node(node: Dict[str, Any], inputs: List[Any]) -> Path:
    """
    Pipeline executor for output nodes.
    
    Saves an image to disk with dynamic filename templating.
    
    Args:
        node: Node dictionary containing:
            - All OutputNodeConfig fields as node properties
            - 'output_path': Path/filename with optional tags (required)
        inputs: Should contain exactly one element: the input PIL Image
        
    Returns:
        Path where image was saved
        
    Raises:
        ValueError: If inputs empty, invalid config, or file already exists
        TypeError: If input is not a PIL Image
        OSError: If file cannot be written
    """
    if not inputs or len(inputs) == 0:
        raise ValueError("Output node requires 1 input image")
    
    image = inputs[0]
    if isinstance(image, (list, tuple)) and image:
        image = image[0]
    
    if not hasattr(image, "save") or not hasattr(image, "mode"):
        raise TypeError(f"Expected PIL Image, got {type(image)}")
    
    # Parse configuration
    config_dict = {
        k: v for k, v in node.items()
        if k in OutputNodeConfig.__dataclass_fields__ or k.startswith("_")
    }
    config = OutputNodeConfig.from_dict(config_dict)
    
    # Preserve internal counter state if present
    if "_counter" in node:
        config._counter = node.get("_counter", 0)
    
    # Create handler and save
    handler = OutputNodeHandler(config)
    output_path = handler.save_image(image)
    
    # Store updated counter back in node if auto-incrementing
    if config.auto_increment_counter:
        node["_counter"] = config._counter
    
    return output_path


def create_output_node(
    node_id: str,
    output_path: str = "output.png",
    save_format: str = "PNG",
    quality: int = 95,
    version: int = 1,
    auto_increment_counter: bool = False,
    create_directories: bool = True,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Helper to create an output node dictionary for graph building.
    
    Args:
        node_id: Unique node identifier
        output_path: Output path/filename with optional tags
        save_format: Image format (PNG, JPG, BMP, etc.)
        quality: JPEG quality 1-100
        version: Version number (can be used with {VERSION} tag)
        auto_increment_counter: Auto-increment counter on each save
        create_directories: Create output directories if missing
        overwrite: Overwrite existing files
        
    Returns:
        Node dictionary ready for graph serialization
        
    Examples:
        >>> # Simple output
        >>> create_output_node("out-1", "output.png")
        
        >>> # With date tag
        >>> create_output_node("out-2", "output_{DATE}.png")
        
        >>> # With version and counter
        >>> create_output_node("out-3", "output_v{VERSION:2}_{COUNTER:3}.png", 
        ...                   version=1, auto_increment_counter=True)
        
        >>> # With custom time format
        >>> create_output_node("out-4", "output_{TIME:%H_%M_%S}.png")
    """
    return {
        "id": node_id,
        "type": "Output",
        "output_path": output_path,
        "save_format": save_format,
        "quality": quality,
        "version": version,
        "auto_increment_counter": auto_increment_counter,
        "create_directories": create_directories,
        "overwrite": overwrite,
        "_counter": 0,
    }
