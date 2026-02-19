"""
Node Executors Registry and Manager.

This module provides a centralized registry for node type executors. It enables
easy registration, lookup, and execution of different node types in the pipeline.

Classes:
    NodeExecutorRegistry: Registry for node executors
    
Functions:
    get_default_registry: Get the global default registry (singleton)
    register_default_executors: Register all built-in node executors
"""

from typing import Any, Callable, Dict, List, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Type alias for executor function
ExecutorFunction = Callable[[Dict[str, Any], List[Any]], Any]


class NodeExecutorRegistry:
    """
    Registry for node type executors.
    
    Provides centralized management of node executors, allowing registration,
    lookup, and validation of executor functions for different node types.
    
    Example:
        >>> registry = NodeExecutorRegistry()
        >>> registry.register("Image Import", image_import_executor)
        >>> registry.register("Color Replace", color_replace_executor)
        >>> executor = registry.get_executor("Image Import")
        >>> result = executor(node_dict, input_list)
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._executors: Dict[str, ExecutorFunction] = {}
        self._node_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register(
        self,
        node_type: str,
        executor: ExecutorFunction,
        description: str = "",
        input_count: int = 0,
        output_count: int = 1,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Register a node executor.
        
        Args:
            node_type: Unique identifier for the node type (e.g., "Image Import")
            executor: Callable that executes the node. Must accept (node_dict, inputs)
            description: Human-readable description of the node
            input_count: Expected number of inputs (0 for source nodes)
            output_count: Expected number of outputs (usually 1)
            tags: Optional list of tags for categorization (e.g., ["input", "image"])
            
        Raises:
            ValueError: If node_type is empty or executor is not callable
            RuntimeError: If node_type is already registered
        """
        node_type = str(node_type).strip()
        
        if not node_type:
            raise ValueError("node_type cannot be empty")
        
        if not callable(executor):
            raise ValueError(f"executor must be callable, got {type(executor)}")
        
        if node_type in self._executors:
            raise RuntimeError(
                f"Node type '{node_type}' is already registered. "
                f"Use unregister() first to replace it."
            )
        
        self._executors[node_type] = executor
        self._node_metadata[node_type] = {
            "description": str(description),
            "input_count": int(input_count),
            "output_count": int(output_count),
            "tags": list(tags) if tags else [],
        }
        
        logger.debug(f"Registered executor for node type: {node_type}")
    
    def unregister(self, node_type: str) -> bool:
        """
        Unregister a node executor.
        
        Args:
            node_type: The node type to unregister
            
        Returns:
            True if unregistered, False if node_type was not registered
        """
        node_type = str(node_type).strip()
        
        if node_type in self._executors:
            del self._executors[node_type]
            del self._node_metadata[node_type]
            logger.debug(f"Unregistered executor for node type: {node_type}")
            return True
        
        return False
    
    def get_executor(self, node_type: str) -> ExecutorFunction:
        """
        Get an executor for a node type.
        
        Args:
            node_type: The node type to get executor for
            
        Returns:
            The executor function
            
        Raises:
            KeyError: If node_type is not registered
        """
        node_type = str(node_type).strip()
        
        if node_type not in self._executors:
            available = ", ".join(self.list_node_types())
            raise KeyError(
                f"No executor registered for node type '{node_type}'. "
                f"Available types: {available}"
            )
        
        return self._executors[node_type]
    
    def has_executor(self, node_type: str) -> bool:
        """
        Check if an executor is registered for a node type.
        
        Args:
            node_type: The node type to check
            
        Returns:
            True if executor is registered, False otherwise
        """
        return str(node_type).strip() in self._executors
    
    def execute(
        self,
        node_type: str,
        node_dict: Dict[str, Any],
        inputs: List[Any],
    ) -> Any:
        """
        Execute a node by looking up its executor.
        
        Args:
            node_type: The node type to execute
            node_dict: Node configuration dictionary
            inputs: List of results from input nodes
            
        Returns:
            Result from the executor
            
        Raises:
            KeyError: If node_type is not registered
            Exception: Any exception raised by the executor
        """
        executor = self.get_executor(node_type)
        return executor(node_dict, inputs)
    
    def list_node_types(self) -> List[str]:
        """
        Get list of all registered node types.
        
        Returns:
            Sorted list of node type names
        """
        return sorted(list(self._executors.keys()))
    
    def get_metadata(self, node_type: str) -> Dict[str, Any]:
        """
        Get metadata for a node type.
        
        Args:
            node_type: The node type
            
        Returns:
            Dictionary with description, input_count, output_count, tags
            
        Raises:
            KeyError: If node_type is not registered
        """
        node_type = str(node_type).strip()
        
        if node_type not in self._node_metadata:
            raise KeyError(f"No metadata for node type: {node_type}")
        
        return dict(self._node_metadata[node_type])
    
    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all registered node types.
        
        Returns:
            Dictionary mapping node_type -> metadata
        """
        return {
            node_type: dict(meta)
            for node_type, meta in self._node_metadata.items()
        }
    
    def filter_by_tag(self, tag: str) -> List[str]:
        """
        Get all node types with a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            Sorted list of node type names with the tag
        """
        tag = str(tag).strip().lower()
        return sorted([
            node_type
            for node_type, meta in self._node_metadata.items()
            if tag in [t.lower() for t in meta.get("tags", [])]
        ])
    
    def get_nodes_by_category(self, category: str) -> Dict[str, Any]:
        """
        Get all node types in a category (based on tags).
        
        Common categories: "input", "processing", "output"
        
        Args:
            category: The category to filter by
            
        Returns:
            Dictionary mapping node_type -> metadata for nodes in category
        """
        nodes = {}
        category_lower = str(category).strip().lower()
        
        for node_type, meta in self._node_metadata.items():
            if category_lower in [t.lower() for t in meta.get("tags", [])]:
                nodes[node_type] = dict(meta)
        
        return nodes
    
    def clear(self) -> None:
        """Clear all registered executors. Use with caution."""
        self._executors.clear()
        self._node_metadata.clear()
        logger.warning("Node executor registry cleared")


# Global singleton registry
_default_registry: Optional[NodeExecutorRegistry] = None


def get_default_registry() -> NodeExecutorRegistry:
    """
    Get the global default registry (singleton).
    
    Creates the registry on first call and registers default executors.
    
    Returns:
        The global NodeExecutorRegistry instance
    """
    global _default_registry
    
    if _default_registry is None:
        _default_registry = NodeExecutorRegistry()
        register_default_executors(_default_registry)
    
    return _default_registry


def register_default_executors(registry: NodeExecutorRegistry) -> None:
    """
    Register all built-in node executors.
    
    This function registers:
    - Image Import node
    - Color Shift node
    - Output node
    - Image Layer node (compositor)
    - Additional built-in nodes as they're implemented
    
    Args:
        registry: The registry to register executors with
    """
    from OV_Libs.NodesLib.image_import_node import execute_import_image_node
    from OV_Libs.NodesLib.color_shift_node import execute_color_shift_node
    from OV_Libs.NodesLib.output_node import execute_output_node
    from OV_Libs.NodesLib.image_layer_node import execute_image_layer_node
    from OV_Libs.NodesLib.blur_node import execute_blur_node
    from OV_Libs.NodesLib.mask_blur_node import execute_mask_blur_node
    
    registry.register(
        node_type="Image Import",
        executor=execute_import_image_node,
        description="Import an image from disk (PNG, JPG, BMP, GIF, etc.)",
        input_count=0,
        output_count=1,
        tags=["input", "image", "source"],
    )
    
    registry.register(
        node_type="Color Shift",
        executor=execute_color_shift_node,
        description="Apply color shifting with mask generation",
        input_count=1,
        output_count=2,
        tags=["processing", "color", "filter"],
    )
    
    registry.register(
        node_type="Output",
        executor=execute_output_node,
        description="Save image to disk with dynamic filename templating",
        input_count=1,
        output_count=0,
        tags=["output", "image", "sink"],
    )
    
    registry.register(
        node_type="Image Layer",
        executor=execute_image_layer_node,
        description="Composite multiple layers with masks, alphas, and blend amounts",
        input_count=1,
        output_count=1,
        tags=["processing", "composition", "layer"],
    )
    
    registry.register(
        node_type="Blur",
        executor=execute_blur_node,
        description="Apply blur effects (Gaussian, Motion, Radial, Box)",
        input_count=1,
        output_count=1,
        tags=["processing", "blur", "filter"],
    )
    
    registry.register(
        node_type="Mask Blur",
        executor=execute_mask_blur_node,
        description="Apply spatially-varying blur based on RGBA strength map",
        input_count=2,
        output_count=1,
        tags=["processing", "blur", "filter", "mask"],
    )
    
    logger.info("Registered default node executors")


def executor_wrapper(
    node_type: str,
    description: str = "",
    input_count: int = 0,
    output_count: int = 1,
    tags: Optional[List[str]] = None,
) -> Callable:
    """
    Decorator to automatically register an executor function.
    
    Usage:
        >>> @executor_wrapper("My Node", description="Does something", tags=["custom"])
        >>> def my_node_executor(node, inputs):
        ...     return process(inputs)
    
    Args:
        node_type: Node type name
        description: Human-readable description
        input_count: Expected number of inputs
        output_count: Expected number of outputs
        tags: Optional categorization tags
        
    Returns:
        Decorator function
    """
    def decorator(func: ExecutorFunction) -> ExecutorFunction:
        registry = get_default_registry()
        
        try:
            registry.register(
                node_type=node_type,
                executor=func,
                description=description,
                input_count=input_count,
                output_count=output_count,
                tags=tags or [],
            )
        except RuntimeError:
            # Node type already registered, just use the function
            logger.debug(f"Node type '{node_type}' already registered, skipping")
        
        @wraps(func)
        def wrapper(node: Dict[str, Any], inputs: List[Any]) -> Any:
            return func(node, inputs)
        
        return wrapper
    
    return decorator
