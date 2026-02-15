"""
Quick test to demonstrate parallel execution functionality
"""
import time
from OV_Libs.ProjStoreLib.pipeline_builder import (
    build_pipeline_from_graph,
    execute_pipeline,
    get_pipeline_summary
)


def slow_input_executor(node, inputs):
    """Simulates slow input loading"""
    time.sleep(0.5)
    print(f"  Loading {node['id']}...")
    return f"data_from_{node['id']}"


def slow_filter_executor(node, inputs):
    """Simulates slow filter processing"""
    time.sleep(0.5)
    print(f"  Filtering {node['id']} with inputs: {inputs}")
    return f"filtered_{node['id']}"


def merge_executor(node, inputs):
    """Merges multiple inputs"""
    print(f"  Merging {node['id']} from: {inputs}")
    return f"merged_{'_'.join(inputs)}"


def output_executor(node, inputs):
    """Output node"""
    print(f"  Output {node['id']}: {inputs}")
    return f"output_{inputs[0]}"


# Create a diamond pattern node graph
nodes = [
    {"id": "input", "type": "Input", "x": 100, "y": 200},
    {"id": "filter_a", "type": "Filter", "x": 300, "y": 100},
    {"id": "filter_b", "type": "Filter", "x": 300, "y": 200},
    {"id": "filter_c", "type": "Filter", "x": 300, "y": 300},
    {"id": "merge", "type": "Merge", "x": 500, "y": 200},
    {"id": "output", "type": "Output", "x": 700, "y": 200}
]

connections = [
    {"from_node": "input", "to_node": "filter_a"},
    {"from_node": "input", "to_node": "filter_b"},
    {"from_node": "input", "to_node": "filter_c"},
    {"from_node": "filter_a", "to_node": "merge"},
    {"from_node": "filter_b", "to_node": "merge"},
    {"from_node": "filter_c", "to_node": "merge"},
    {"from_node": "merge", "to_node": "output"}
]

# Build pipeline
print("Building pipeline...")
pipeline, is_valid, errors = build_pipeline_from_graph(nodes, connections)

if not is_valid:
    print(f"Pipeline validation failed: {errors}")
    exit(1)

# Display pipeline summary
print("\n" + get_pipeline_summary(pipeline))
print("\n" + "="*60)

# Set up executors
node_executors = {
    "Input": slow_input_executor,
    "Filter": slow_filter_executor,
    "Merge": merge_executor,
    "Output": output_executor
}

# Execute with parallel threading
print("\nExecuting WITH parallel threading:")
print("-" * 60)
start_time = time.time()
results_parallel = execute_pipeline(pipeline, node_executors, use_threading=True)
parallel_time = time.time() - start_time
print(f"\nParallel execution time: {parallel_time:.2f} seconds")

print("\n" + "="*60)

# Execute without parallel threading (sequential)
print("\nExecuting WITHOUT parallel threading:")
print("-" * 60)
start_time = time.time()
results_sequential = execute_pipeline(pipeline, node_executors, use_threading=False)
sequential_time = time.time() - start_time
print(f"\nSequential execution time: {sequential_time:.2f} seconds")

print("\n" + "="*60)
print(f"\nSpeedup: {sequential_time/parallel_time:.2f}x")
print(f"Time saved: {sequential_time - parallel_time:.2f} seconds")

# Verify results are the same
assert results_parallel == results_sequential, "Results should be identical!"
print("\n✓ Results are identical - parallel execution works correctly!")
