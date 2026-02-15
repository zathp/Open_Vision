"""
Unit Tests for Pipeline Builder

Tests all core functionality of the pipeline builder module including:
- Dependency map construction
- Stage calculation with topological sorting
- Pipeline building
- Validation
- Edge cases and error handling
"""

import unittest
from OV_Libs.ProjStoreLib.pipeline_builder import (
    build_dependency_map,
    calculate_pipeline_stages,
    build_execution_pipeline,
    validate_pipeline,
    build_pipeline_from_graph,
    get_pipeline_summary,
    build_update_pipeline
)


class TestBuildDependencyMap(unittest.TestCase):
    """Test dependency map construction."""
    
    def test_simple_linear(self):
        """Test simple linear dependency chain."""
        nodes = [
            {"id": "n1"},
            {"id": "n2"},
            {"id": "n3"}
        ]
        connections = [
            {"from_node": "n1", "to_node": "n2"},
            {"from_node": "n2", "to_node": "n3"}
        ]
        
        deps = build_dependency_map(nodes, connections)
        
        self.assertEqual(deps["n1"], [])
        self.assertEqual(deps["n2"], ["n1"])
        self.assertEqual(deps["n3"], ["n2"])
    
    def test_parallel_inputs(self):
        """Test parallel input nodes merging."""
        nodes = [
            {"id": "input1"},
            {"id": "input2"},
            {"id": "merge"}
        ]
        connections = [
            {"from_node": "input1", "to_node": "merge"},
            {"from_node": "input2", "to_node": "merge"}
        ]
        
        deps = build_dependency_map(nodes, connections)
        
        self.assertEqual(deps["input1"], [])
        self.assertEqual(deps["input2"], [])
        self.assertIn("input1", deps["merge"])
        self.assertIn("input2", deps["merge"])
        self.assertEqual(len(deps["merge"]), 2)
    
    def test_no_connections(self):
        """Test graph with no connections."""
        nodes = [
            {"id": "n1"},
            {"id": "n2"}
        ]
        connections = []
        
        deps = build_dependency_map(nodes, connections)
        
        self.assertEqual(deps["n1"], [])
        self.assertEqual(deps["n2"], [])
    
    def test_invalid_connection(self):
        """Test connection referencing non-existent node."""
        nodes = [
            {"id": "n1"},
            {"id": "n2"}
        ]
        connections = [
            {"from_node": "n1", "to_node": "n_invalid"}
        ]
        
        deps = build_dependency_map(nodes, connections)
        
        # Invalid connection should be ignored
        self.assertEqual(deps["n1"], [])
        self.assertEqual(deps["n2"], [])


class TestCalculatePipelineStages(unittest.TestCase):
    """Test pipeline stage calculation."""
    
    def test_linear_chain(self):
        """Test linear dependency chain."""
        nodes = [
            {"id": "n1", "x": 100, "y": 100},
            {"id": "n2", "x": 300, "y": 100},
            {"id": "n3", "x": 500, "y": 100}
        ]
        deps = {
            "n1": [],
            "n2": ["n1"],
            "n3": ["n2"]
        }
        
        stages = calculate_pipeline_stages(nodes, deps)
        
        self.assertEqual(stages["n1"], 0)
        self.assertEqual(stages["n2"], 1)
        self.assertEqual(stages["n3"], 2)
    
    def test_parallel_paths(self):
        """Test diamond pattern with parallel paths."""
        nodes = [
            {"id": "input", "x": 100, "y": 200},
            {"id": "filterA", "x": 300, "y": 100},
            {"id": "filterB", "x": 300, "y": 300},
            {"id": "merge", "x": 500, "y": 200}
        ]
        deps = {
            "input": [],
            "filterA": ["input"],
            "filterB": ["input"],
            "merge": ["filterA", "filterB"]
        }
        
        stages = calculate_pipeline_stages(nodes, deps)
        
        self.assertEqual(stages["input"], 0)
        self.assertEqual(stages["filterA"], 1)
        self.assertEqual(stages["filterB"], 1)
        self.assertEqual(stages["merge"], 2)
    
    def test_multi_level_dependencies(self):
        """Test complex multi-level dependencies."""
        nodes = [
            {"id": "i1", "x": 100, "y": 100},
            {"id": "i2", "x": 100, "y": 300},
            {"id": "f1", "x": 300, "y": 100},
            {"id": "f2", "x": 300, "y": 300},
            {"id": "m1", "x": 500, "y": 200},
            {"id": "f3", "x": 700, "y": 200},
            {"id": "out", "x": 900, "y": 200}
        ]
        deps = {
            "i1": [],
            "i2": [],
            "f1": ["i1"],
            "f2": ["i2"],
            "m1": ["f1", "f2"],
            "f3": ["m1"],
            "out": ["f3"]
        }
        
        stages = calculate_pipeline_stages(nodes, deps)
        
        self.assertEqual(stages["i1"], 0)
        self.assertEqual(stages["i2"], 0)
        self.assertEqual(stages["f1"], 1)
        self.assertEqual(stages["f2"], 1)
        self.assertEqual(stages["m1"], 2)
        self.assertEqual(stages["f3"], 3)
        self.assertEqual(stages["out"], 4)
    
    def test_circular_dependency(self):
        """Test detection of circular dependencies."""
        nodes = [
            {"id": "n1", "x": 100, "y": 100},
            {"id": "n2", "x": 300, "y": 100},
            {"id": "n3", "x": 500, "y": 100}
        ]
        deps = {
            "n1": ["n3"],  # Circular: n1 -> n2 -> n3 -> n1
            "n2": ["n1"],
            "n3": ["n2"]
        }
        
        with self.assertRaises(ValueError) as context:
            calculate_pipeline_stages(nodes, deps)
        
        self.assertIn("Circular dependency", str(context.exception))
    
    def test_horizontal_sorting(self):
        """Test nodes sorted by horizontal position."""
        nodes = [
            {"id": "n3", "x": 500, "y": 100},
            {"id": "n1", "x": 100, "y": 100},
            {"id": "n2", "x": 300, "y": 100}
        ]
        deps = {
            "n1": [],
            "n2": [],
            "n3": []
        }
        
        stages = calculate_pipeline_stages(nodes, deps)
        
        # All should be stage 0 since no dependencies
        self.assertEqual(stages["n1"], 0)
        self.assertEqual(stages["n2"], 0)
        self.assertEqual(stages["n3"], 0)


class TestBuildExecutionPipeline(unittest.TestCase):
    """Test execution pipeline construction."""
    
    def test_simple_pipeline(self):
        """Test simple pipeline structure."""
        nodes = [
            {"id": "n1", "type": "Input", "x": 100, "y": 100},
            {"id": "n2", "type": "Filter", "x": 300, "y": 100},
            {"id": "n3", "type": "Output", "x": 500, "y": 100}
        ]
        stages = {"n1": 0, "n2": 1, "n3": 2}
        deps = {"n1": [], "n2": ["n1"], "n3": ["n2"]}
        
        pipeline = build_execution_pipeline(nodes, stages, deps)
        
        self.assertEqual(pipeline["max_stage"], 2)
        self.assertEqual(len(pipeline["stages"]), 3)
        self.assertEqual(pipeline["execution_order"], ["n1", "n2", "n3"])
        
        # Check stage 0
        stage0 = pipeline["stages"][0]
        self.assertEqual(stage0["stage_number"], 0)
        self.assertEqual(len(stage0["nodes"]), 1)
        self.assertEqual(stage0["nodes"][0]["id"], "n1")
        self.assertEqual(stage0["nodes"][0]["inputs"], [])
    
    def test_parallel_stage(self):
        """Test stage with multiple parallel nodes."""
        nodes = [
            {"id": "input", "type": "Input", "x": 100, "y": 200},
            {"id": "fA", "type": "FilterA", "x": 300, "y": 100},
            {"id": "fB", "type": "FilterB", "x": 300, "y": 300}
        ]
        stages = {"input": 0, "fA": 1, "fB": 1}
        deps = {"input": [], "fA": ["input"], "fB": ["input"]}
        
        pipeline = build_execution_pipeline(nodes, stages, deps)
        
        # Stage 0 should NOT be parallelizable (single node)
        stage0 = pipeline["stages"][0]
        self.assertEqual(stage0["can_parallelize"], False)
        
        # Stage 1 should have 2 nodes and be parallelizable
        stage1 = pipeline["stages"][1]
        self.assertEqual(len(stage1["nodes"]), 2)
        self.assertEqual(stage1["can_parallelize"], True)
        
        # Nodes should be sorted by x position
        self.assertEqual(stage1["nodes"][0]["id"], "fA")  # x=300, y=100
        self.assertEqual(stage1["nodes"][1]["id"], "fB")  # x=300, y=300
    
    def test_empty_pipeline(self):
        """Test empty pipeline."""
        pipeline = build_execution_pipeline([], {}, {})
        
        self.assertEqual(pipeline["max_stage"], -1)
        self.assertEqual(pipeline["stages"], [])
        self.assertEqual(pipeline["execution_order"], [])


class TestValidatePipeline(unittest.TestCase):
    """Test pipeline validation."""
    
    def test_valid_pipeline(self):
        """Test validation of valid pipeline."""
        nodes = [
            {"id": "n1", "type": "Input"},
            {"id": "n2", "type": "Output"}
        ]
        connections = [
            {"from_node": "n1", "to_node": "n2"}
        ]
        pipeline = {
            "stages": [
                {"stage_number": 0, "nodes": [{"id": "n1", "inputs": []}]},
                {"stage_number": 1, "nodes": [{"id": "n2", "inputs": ["n1"]}]}
            ],
            "max_stage": 1,
            "execution_order": ["n1", "n2"]
        }
        
        is_valid, errors = validate_pipeline(pipeline, nodes, connections)
        
        self.assertTrue(is_valid)
        # May have warnings, but no critical errors
    
    def test_missing_node(self):
        """Test detection of missing nodes."""
        nodes = [
            {"id": "n1"},
            {"id": "n2"}
        ]
        connections = []
        pipeline = {
            "stages": [
                {"stage_number": 0, "nodes": [{"id": "n1"}]}
            ],
            "max_stage": 0,
            "execution_order": ["n1"]  # n2 is missing
        }
        
        is_valid, errors = validate_pipeline(pipeline, nodes, connections)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("missing" in e.lower() for e in errors))
    
    def test_invalid_connection(self):
        """Test detection of invalid connections."""
        nodes = [
            {"id": "n1"}
        ]
        connections = [
            {"from_node": "n1", "to_node": "n_invalid"}
        ]
        pipeline = {
            "stages": [
                {"stage_number": 0, "nodes": [{"id": "n1"}]}
            ],
            "max_stage": 0,
            "execution_order": ["n1"]
        }
        
        is_valid, errors = validate_pipeline(pipeline, nodes, connections)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("does not exist" in e for e in errors))
    
    def test_no_input_nodes(self):
        """Test detection of missing input nodes."""
        nodes = [{"id": "n1"}]
        connections = []
        pipeline = {
            "stages": [
                {"stage_number": 0, "nodes": []}  # Empty stage 0
            ],
            "max_stage": 0,
            "execution_order": []
        }
        
        is_valid, errors = validate_pipeline(pipeline, nodes, connections)
        
        self.assertFalse(is_valid)
        # Should detect empty stage 0


class TestBuildPipelineFromGraph(unittest.TestCase):
    """Test complete pipeline building from graph."""
    
    def test_successful_build(self):
        """Test successful pipeline build."""
        nodes = [
            {"id": "i1", "type": "Input", "x": 100, "y": 100},
            {"id": "f1", "type": "Filter", "x": 300, "y": 100},
            {"id": "o1", "type": "Output", "x": 500, "y": 100}
        ]
        connections = [
            {"from_node": "i1", "to_node": "f1"},
            {"from_node": "f1", "to_node": "o1"}
        ]
        
        pipeline, is_valid, errors = build_pipeline_from_graph(nodes, connections)
        
        self.assertTrue(is_valid)
        self.assertEqual(pipeline["max_stage"], 2)
        self.assertEqual(len(pipeline["execution_order"]), 3)
    
    def test_circular_dependency_handling(self):
        """Test graceful handling of circular dependencies."""
        nodes = [
            {"id": "n1", "type": "Node1", "x": 100, "y": 100},
            {"id": "n2", "type": "Node2", "x": 300, "y": 100}
        ]
        connections = [
            {"from_node": "n1", "to_node": "n2"},
            {"from_node": "n2", "to_node": "n1"}  # Creates cycle
        ]
        
        pipeline, is_valid, errors = build_pipeline_from_graph(nodes, connections)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Circular dependency" in e for e in errors))
        self.assertEqual(pipeline["max_stage"], -1)


class TestGetPipelineSummary(unittest.TestCase):
    """Test pipeline summary generation."""
    
    def test_summary_format(self):
        """Test summary string formatting."""
        pipeline = {
            "stages": [
                {
                    "stage_number": 0,
                    "nodes": [
                        {"id": "n1", "type": "Input", "inputs": []}
                    ]
                },
                {
                    "stage_number": 1,
                    "nodes": [
                        {"id": "n2", "type": "Filter", "inputs": ["n1"]}
                    ]
                }
            ],
            "max_stage": 1,
            "execution_order": ["n1", "n2"]
        }
        
        summary = get_pipeline_summary(pipeline)
        
        self.assertIn("Pipeline Summary", summary)
        self.assertIn("Total Stages: 2", summary)
        self.assertIn("Total Nodes: 2", summary)
        self.assertIn("Stage 0", summary)
        self.assertIn("Stage 1", summary)
        self.assertIn("Execution Order: n1 -> n2", summary)


class TestBuildUpdatePipeline(unittest.TestCase):
    """Test update pipeline construction from an updated node."""

    def test_update_pipeline_downstream_chain(self):
        nodes = [
            {"id": "n1", "type": "Input", "x": 100, "y": 100},
            {"id": "n2", "type": "Filter", "x": 300, "y": 100},
            {"id": "n3", "type": "Output", "x": 500, "y": 100}
        ]
        connections = [
            {"from_node": "n1", "to_node": "n2"},
            {"from_node": "n2", "to_node": "n3"}
        ]

        pipeline, is_valid, errors = build_update_pipeline(nodes, connections, ["n2"])

        self.assertTrue(is_valid, msg=f"Errors: {errors}")
        self.assertEqual(pipeline["execution_order"], ["n2", "n3"])
        self.assertEqual(pipeline["max_stage"], 1)
        self.assertEqual(pipeline["stages"][0]["nodes"][0]["id"], "n2")
        self.assertIn("n1", pipeline["stages"][0]["nodes"][0]["inputs"])

    def test_update_pipeline_branch(self):
        nodes = [
            {"id": "n1", "type": "Input", "x": 100, "y": 100},
            {"id": "n2", "type": "FilterA", "x": 300, "y": 50},
            {"id": "n3", "type": "FilterB", "x": 300, "y": 150},
            {"id": "n4", "type": "Output", "x": 500, "y": 100}
        ]
        connections = [
            {"from_node": "n1", "to_node": "n2"},
            {"from_node": "n1", "to_node": "n3"},
            {"from_node": "n2", "to_node": "n4"},
            {"from_node": "n3", "to_node": "n4"}
        ]

        pipeline, is_valid, errors = build_update_pipeline(nodes, connections, ["n2"])

        self.assertTrue(is_valid, msg=f"Errors: {errors}")
        self.assertEqual(pipeline["execution_order"], ["n2", "n4"])
        self.assertEqual(pipeline["max_stage"], 1)

    def test_update_pipeline_invalid_node(self):
        nodes = [{"id": "n1", "type": "Input", "x": 100, "y": 100}]
        connections = []

        pipeline, is_valid, errors = build_update_pipeline(nodes, connections, ["missing"])

        self.assertFalse(is_valid)
        self.assertEqual(pipeline["max_stage"], -1)
        self.assertTrue(any("valid updated nodes" in e for e in errors))


if __name__ == "__main__":
    unittest.main()