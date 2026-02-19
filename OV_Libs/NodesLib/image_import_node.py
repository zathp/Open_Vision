"""
Image Import Node for Open Vision.

This module provides the ImageImportNode class that handles importing images
from the file system. It supports standard image formats (PNG, JPG, BMP, etc.)
and is designed for easy extension to support movies and GIFs.

Classes:
    ImageImportNode: Data model for image import node
    
Functions:
    execute_import_image_node: Pipeline executor for image import nodes
    get_supported_image_formats: Get list of supported image formats
    get_supported_movie_formats: Get list of supported movie formats (future)
    get_supported_formats: Get all supported formats
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from OV_Libs.pillow_compat import Image


# Supported file extensions
STANDARD_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
MOVIE_FORMATS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}  # For future implementation
GIF_FORMAT = {".gif"}  # Can be static image or animated sequence

# File filter patterns for QFileDialog
STANDARD_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
MOVIE_FILTER = "Movies (*.mp4 *.avi *.mov *.mkv *.webm)"
GIF_FILTER = "GIF Files (*.gif)"
ALL_SUPPORTED_FILTER = "All Supported Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.mp4 *.avi *.mov *.mkv *.webm)"


def get_supported_image_formats() -> List[str]:
    """
    Get list of supported standard image formats.
    
    Returns:
        List of file extensions (e.g., ['.png', '.jpg', ...])
    """
    return sorted(list(STANDARD_IMAGE_FORMATS))


def get_supported_movie_formats() -> List[str]:
    """
    Get list of supported movie formats (future implementation).
    
    Returns:
        List of file extensions (e.g., ['.mp4', '.avi', ...])
    """
    return sorted(list(MOVIE_FORMATS))


def get_supported_gif_formats() -> List[str]:
    """
    Get list of GIF format extensions.
    
    Returns:
        List containing ['.gif']
    """
    return sorted(list(GIF_FORMAT))


def get_supported_formats(include_movies: bool = False, include_gifs: bool = True) -> List[str]:
    """
    Get all supported formats.
    
    Args:
        include_movies: Include movie formats (default False)
        include_gifs: Include GIF format (default True)
        
    Returns:
        Combined list of supported extensions
    """
    formats = set(STANDARD_IMAGE_FORMATS)
    
    if include_gifs:
        formats.update(GIF_FORMAT)
    
    if include_movies:
        formats.update(MOVIE_FORMATS)
    
    return sorted(list(formats))


def is_supported_format(file_path: Path, include_movies: bool = False, include_gifs: bool = True) -> bool:
    """
    Check if a file path has a supported format.
    
    Args:
        file_path: Path to the file
        include_movies: Check movie formats (default False)
        include_gifs: Check GIF format (default True)
        
    Returns:
        True if file extension is supported
    """
    ext = file_path.suffix.lower()
    supported = get_supported_formats(include_movies=include_movies, include_gifs=include_gifs)
    return ext in supported


@dataclass
class ImageImportNode:
    """Data model for an image import node.
    
    An image import node loads an image file from disk and provides it as
    output to downstream nodes. Supports standard image formats with
    extensibility for movies and GIFs.
    
    Attributes:
        node_id: Unique identifier for this node
        file_path: Path to the image file to import
        format_type: Type of format ('image' default, 'movie' future, 'gif' future)
        cache_image: Whether to cache the loaded image (default True)
        frame_index: For GIFs/movies, which frame to use (default 0, future)
        cached_image: Cached PIL Image object
    """
    
    node_id: str
    file_path: Path
    format_type: str = "image"  # 'image', 'movie', 'gif'
    cache_image: bool = True
    frame_index: int = 0  # For animated formats
    cached_image: Optional[Any] = field(default=None, init=False)
    
    def __post_init__(self):
        """Validate input parameters."""
        self.file_path = Path(self.file_path)
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Image file not found: {self.file_path}")
        
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")
        
        if self.format_type not in ("image", "movie", "gif"):
            raise ValueError(f"Unsupported format_type: {self.format_type}")
        
        if self.frame_index < 0:
            raise ValueError(f"frame_index must be >= 0, got {self.frame_index}")
    
    def load_image(self) -> Any:
        """
        Load the image from disk.
        
        Returns:
            PIL Image object
            
        Raises:
            IOError: If image cannot be loaded
            NotImplementedError: If format is not yet supported
        """
        if self.cached_image is not None and self.cache_image:
            return self.cached_image
        
        if self.format_type == "image":
            image = self._load_standard_image()
        elif self.format_type == "gif":
            image = self._load_gif_frame()
        elif self.format_type == "movie":
            raise NotImplementedError("Movie import not yet implemented")
        else:
            raise ValueError(f"Unknown format_type: {self.format_type}")
        
        if self.cache_image:
            self.cached_image = image
        
        return image
    
    def _load_standard_image(self) -> Any:
        """Load a standard image file (PNG, JPG, BMP, etc.)."""
        try:
            img = Image.open(self.file_path)
            # Convert to RGBA for consistency
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            return img
        except Exception as e:
            raise IOError(f"Failed to load image from {self.file_path}: {str(e)}")
    
    def _load_gif_frame(self) -> Any:
        """Load a specific frame from a GIF file."""
        try:
            img = Image.open(self.file_path)
            
            # Check if it's an animated GIF
            try:
                img.seek(self.frame_index)
            except EOFError:
                # Frame index out of range, load first frame
                img.seek(0)
            
            # Convert to RGBA for consistency
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            return img
        except Exception as e:
            raise IOError(f"Failed to load GIF frame {self.frame_index} from {self.file_path}: {str(e)}")
    
    def get_num_frames(self) -> int:
        """
        Get the number of frames (for animated formats).
        
        Returns:
            1 for static images, number of frames for animated GIFs
        """
        if self.format_type != "gif":
            return 1
        
        try:
            img = Image.open(self.file_path)
            return getattr(img, "n_frames", 1)
        except Exception:
            return 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation for serialization."""
        return {
            "node_id": self.node_id,
            "file_path": str(self.file_path),
            "format_type": self.format_type,
            "cache_image": self.cache_image,
            "frame_index": self.frame_index,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageImportNode":
        """Create from dictionary representation."""
        return cls(
            node_id=data.get("node_id", ""),
            file_path=Path(data.get("file_path", "")),
            format_type=data.get("format_type", "image"),
            cache_image=data.get("cache_image", True),
            frame_index=data.get("frame_index", 0),
        )


def execute_import_image_node(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Pipeline executor for image import nodes.
    
    This function is called during pipeline execution to load and return
    the image specified by the node's configuration.
    
    Args:
        node: Node dictionary containing:
            - 'file_path': Path to image file (required)
            - 'format_type': Type of format - 'image', 'gif', 'movie' (default 'image')
            - 'frame_index': Frame index for animated formats (default 0)
            - 'cache_image': Whether to cache the loaded image (default True)
        inputs: Should be empty list (import nodes have no inputs)
    
    Returns:
        PIL Image object
        
    Raises:
        KeyError: If required fields are missing
        FileNotFoundError: If image file not found
        IOError: If image cannot be loaded
    """
    file_path = node.get("file_path")
    if not file_path:
        raise KeyError("Image import node missing required 'file_path' field")
    
    node_id = node.get("id", node.get("node_id", "unknown"))
    
    import_node = ImageImportNode(
        node_id=node_id,
        file_path=Path(file_path),
        format_type=node.get("format_type", "image"),
        cache_image=node.get("cache_image", True),
        frame_index=node.get("frame_index", 0),
    )
    
    return import_node.load_image()
