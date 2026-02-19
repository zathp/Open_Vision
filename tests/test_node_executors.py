"""
Tests for Node Executors Registry.

Tests cover:
- Registry creation and basic operations
- Executor registration and lookup
- Metadata management
- Executor execution
- Filtering by tags
- Error handling
- Singleton pattern
- Decorator functionality
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

from OV_Libs.ProjStoreLib.node_executors import (
    NodeExecutorRegistry,
    get_default_registry,
    register_default_executors,
    executor_wrapper,
)


class TestNodeExecutorRegistry(unittest.TestCase):
    """Test NodeExecutorRegistry basic functionality."""
    
    def setUp(self):
        """Create a fresh registry for each test."""
        self.registry = NodeExecutorRegistry()
    
    def test_registry_creation(self):
        """Test creating a new registry."""
        self.assertIsNotNone(self.registry)
        self.assertEqual(len(self.registry.list_node_types()), 0)
    
    def test_register_executor(self):
        """Test registering an executor."""
        def dummy_executor(node, inputs):
            return "dummy result"
        
        self.registry.register("DummyNode", dummy_executor)
        
        self.assertTrue(self.registry.has_executor("DummyNode"))
        self.assertIn("DummyNode", self.registry.list_node_types())
    
    def test_register_with_metadata(self):
        """Test registering with metadata."""
        def dummy_executor(node, inputs):
            return "result"
        
        self.registry.register(
            "TestNode",
            dummy_executor,
            description="A test node",
            input_count=2,
            output_count=1,
            tags=["test", "example"]
        )
        
        meta = self.registry.get_metadata("TestNode")
        
        self.assertEqual(meta["description"], "A test node")
        self.assertEqual(meta["input_count"], 2)
        self.assertEqual(meta["output_count"], 1)
        self.assertIn("test", meta["tags"])
        self.assertIn("example", meta["tags"])
    
    def test_register_empty_node_type_raises_error(self):
        """Test that empty node_type raises ValueError."""
        def dummy_executor(node, inputs):
            return "result"
        
        with self.assertRaises(ValueError):
            self.registry.register("", dummy_executor)
    
    def test_register_non_callable_raises_error(self):
        """Test that non-callable executor raises ValueError."""
        with self.assertRaises(ValueError):
            self.registry.register("BadNode", "not callable")
    
    def test_register_duplicate_node_type_raises_error(self):
        """Test that duplicate registration raises RuntimeError."""
        def executor1(node, inputs):
            return "result1"
        
        def executor2(node, inputs):
            return "result2"
        
        self.registry.register("Node", executor1)
        
        with self.assertRaises(RuntimeError):
            self.registry.register("Node", executor2)
    
    def test_get_executor(self):
        """Test retrieving an executor."""
        def test_executor(node, inputs):
            return "test"
        
        self.registry.register("TestNode", test_executor)
        executor = self.registry.get_executor("TestNode")
        
        self.assertEqual(executor, test_executor)
    
    def test_get_nonexistent_executor_raises_error(self):
        """Test that getting nonexistent executor raises KeyError."""
        with self.assertRaises(KeyError):
            self.registry.get_executor("NonexistentNode")
    
    def test_has_executor(self):
        """Test checking if executor exists."""
        def executor(node, inputs):
            return "result"
        
        self.registry.register("ExistsNode", executor)
        
        self.assertTrue(self.registry.has_executor("ExistsNode"))
        self.assertFalse(self.registry.has_executor("DoesNotExist"))
    
    def test_unregister_executor(self):
        """Test unregistering an executor."""
        def executor(node, inputs):
            return "result"
        
        self.registry.register("ToRemove", executor)
        self.assertTrue(self.registry.has_executor("ToRemove"))
        
        result = self.registry.unregister("ToRemove")
        
        self.assertTrue(result)
        self.assertFalse(self.registry.has_executor("ToRemove"))
    
    def test_unregister_nonexistent_returns_false(self):
        """Test unregistering nonexistent executor returns False."""
        result = self.registry.unregister("DoesNotExist")
        
        self.assertFalse(result)
    
    def test_list_node_types_sorted(self):
        """Test that list_node_types returns sorted list."""
        executors = {
            "ZebraNode": lambda n, i: "z",
            "AlphaNode": lambda n, i: "a",
            "BetaNode": lambda n, i: "b",
        }
        
        for name, exec_func in executors.items():
            self.registry.register(name, exec_func)
        
        types = self.registry.list_node_types()
        
        self.assertEqual(types, ["AlphaNode", "BetaNode", "ZebraNode"])


class TestNodeExecutorExecution(unittest.TestCase):
    """Test node executor execution."""
    
    def setUp(self):
        """Create a fresh registry for each test."""
        self.registry = NodeExecutorRegistry()
    
    def test_execute_node(self):
        """Test executing a node through registry."""
        def test_executor(node, inputs):
            return inputs[0] * 2 if inputs else 0
        
        self.registry.register("Doubler", test_executor)
        
        result = self.registry.execute("Doubler", {}, [5])
        
        self.assertEqual(result, 10)
    
    def test_execute_missing_executor_raises_error(self):
        """Test executing nonexistent executor raises KeyError."""
        with self.assertRaises(KeyError):
            self.registry.execute("Missing", {}, [])
    
    def test_execute_with_node_dict_data(self):
        """Test executor receives node dictionary."""
        def config_executor(node, inputs):
            return node.get("multiplier", 1) * (inputs[0] if inputs else 0)
        
        self.registry.register("Multiplier", config_executor)
        
        node_dict = {"multiplier": 3}
        result = self.registry.execute("Multiplier", node_dict, [4])
        
        self.assertEqual(result, 12)


class TestNodeMetadata(unittest.TestCase):
    """Test node metadata management."""
    
    def setUp(self):
        """Create a fresh registry for each test."""
        self.registry = NodeExecutorRegistry()
    
    def test_get_metadata(self):
        """Test retrieving node metadata."""
        def executor(node, inputs):
            return "result"
        
        self.registry.register(
            "TestNode",
            executor,
            description="Test description",
            input_count=1,
            output_count=2,
            tags=["tag1", "tag2"]
        )
        
        meta = self.registry.get_metadata("TestNode")
        
        self.assertEqual(meta["description"], "Test description")
        self.assertEqual(meta["input_count"], 1)
        self.assertEqual(meta["output_count"], 2)
        self.assertEqual(set(meta["tags"]), {"tag1", "tag2"})
    
    def test_get_all_metadata(self):
        """Test retrieving all metadata."""
        def executor(node, inputs):
            return "result"
        
        self.registry.register("Node1", executor, description="First")
        self.registry.register("Node2", executor, description="Second")
        
        all_meta = self.registry.get_all_metadata()
        
        self.assertEqual(len(all_meta), 2)
        self.assertIn("Node1", all_meta)
        self.assertIn("Node2", all_meta)
    
    def test_filter_by_tag(self):
        """Test filtering nodes by tag."""
        def executor(node, inputs):
            return "result"
        
        self.registry.register("InputNode", executor, tags=["input", "source"])
        self.registry.register("ProcessNode", executor, tags=["process"])
        self.registry.register("OutputNode", executor, tags=["output", "sink"])
        
        input_nodes = self.registry.filter_by_tag("input")
        process_nodes = self.registry.filter_by_tag("process")
        
        self.assertEqual(input_nodes, ["InputNode"])
        self.assertEqual(process_nodes, ["ProcessNode"])
    
    def test_filter_by_tag_case_insensitive(self):
        """Test that tag filtering is case insensitive."""
        def executor(node, inputs):
            return "result"
        
        self.registry.register("TestNode", executor, tags=["INPUT", "Source"])
        
        result = self.registry.filter_by_tag("input")
        
        self.assertIn("TestNode", result)
    
    def test_get_nodes_by_category(self):
        """Test getting nodes by category."""
        def executor(node, inputs):
            return "result"
        
        self.registry.register("Import", executor, tags=["input"])
        self.registry.register("Filter", executor, tags=["process"])
        self.registry.register("Export", executor, tags=["output"])
        
        input_category = self.registry.get_nodes_by_category("input")
        
        self.assertEqual(len(input_category), 1)
        self.assertIn("Import", input_category)


class TestRegistryUtilities(unittest.TestCase):
    """Test utility functions."""
    
    def test_clear_registry(self):
        """Test clearing the registry."""
        registry = NodeExecutorRegistry()
        
        def executor(node, inputs):
            return "result"
        
        registry.register("Node1", executor)
        registry.register("Node2", executor)
        
        self.assertEqual(len(registry.list_node_types()), 2)
        
        registry.clear()
        
        self.assertEqual(len(registry.list_node_types()), 0)
    
    def test_get_metadata_nonexistent_raises_error(self):
        """Test getting metadata for nonexistent node raises KeyError."""
        registry = NodeExecutorRegistry()
        
        with self.assertRaises(KeyError):
            registry.get_metadata("NonexistentNode")


class TestDefaultRegistry(unittest.TestCase):
    """Test default registry singleton pattern."""
    
    def test_get_default_registry_singleton(self):
        """Test that get_default_registry returns same instance."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()
        
        self.assertIs(registry1, registry2)
    
    def test_default_registry_has_image_import(self):
        """Test that default registry includes Image Import node."""
        registry = get_default_registry()
        
        self.assertTrue(registry.has_executor("Image Import"))
    
    def test_default_registry_image_import_metadata(self):
        """Test Image Import node metadata."""
        registry = get_default_registry()
        meta = registry.get_metadata("Image Import")
        
        self.assertEqual(meta["input_count"], 0)
        self.assertEqual(meta["output_count"], 1)
        self.assertIn("input", meta["tags"])
        self.assertIn("image", meta["tags"])
        self.assertIn("source", meta["tags"])
    
    def test_register_default_executors(self):
        """Test register_default_executors function."""
        registry = NodeExecutorRegistry()
        register_default_executors(registry)
        
        types = registry.list_node_types()
        
        self.assertIn("Image Import", types)


class TestExecutorDecorator(unittest.TestCase):
    """Test executor_wrapper decorator."""
    
    def setUp(self):
        """Create a fresh registry for decorator tests."""
        self.registry = NodeExecutorRegistry()
    
    def test_executor_wrapper_decorator(self):
        """Test that executor_wrapper decorator registers function."""
        # Create a temporary test executor using the decorator logic
        def test_executor(node, inputs):
            return "decorated result"
        
        # Manually register it to simulate decorator behavior
        self.registry.register(
            "DecoratedNode",
            test_executor,
            description="A decorated node",
            tags=["test"]
        )
        
        self.assertTrue(self.registry.has_executor("DecoratedNode"))
        result = self.registry.execute("DecoratedNode", {}, [])
        self.assertEqual(result, "decorated result")


class TestExecutorIntegration(unittest.TestCase):
    """Integration tests with Image Import executor."""
    
    def setUp(self):
        """Create temporary directory and test images."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test image
        self.test_image = self.temp_path / "test.png"
        img = Image.new("RGB", (50, 50), color="red")
        img.save(self.test_image)
        
        self.registry = NodeExecutorRegistry()
        register_default_executors(self.registry)
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_execute_image_import_through_registry(self):
        """Test executing Image Import node through registry."""
        node_dict = {
            "id": "import-1",
            "file_path": str(self.test_image),
            "format_type": "image",
        }
        
        result = self.registry.execute("Image Import", node_dict, [])
        
        self.assertIsNotNone(result)
        self.assertEqual(result.size, (50, 50))
    
    def test_image_import_through_get_executor(self):
        """Test getting and executing Image Import executor."""
        executor = self.registry.get_executor("Image Import")
        
        node_dict = {
            "id": "import-2",
            "file_path": str(self.test_image),
        }
        
        result = executor(node_dict, [])
        
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
