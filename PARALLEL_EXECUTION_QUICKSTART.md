# Quick Start: Parallel Pipeline Execution

## Basic Usage

```python
from OV_Libs.ProjStoreLib.pipeline_builder import (
    build_pipeline_from_graph,
    execute_pipeline
)

# 1. Build the pipeline from your node graph
pipeline, is_valid, errors = build_pipeline_from_graph(nodes, connections)

if not is_valid:
    print(f"Pipeline errors: {errors}")
    return

# 2. Define executor functions for each node type
def load_image(node, inputs):
    """Load an image from disk"""
    return Image.open(node["image_path"])

def apply_filter(node, inputs):
    """Apply filter to input image"""
    image = inputs[0]  # First input
    return process_filter(image, node["filter_params"])

def save_output(node, inputs):
    """Save the output image"""
    image = inputs[0]
    image.save(node["output_path"])
    return image

# 3. Map node types to executors
executors = {
    "Image Input": load_image,
    "Color Filter": apply_filter,
    "Blur Filter": apply_filter,
    "Output": save_output
}

# 4. Execute the pipeline with parallel threading
results = execute_pipeline(pipeline, executors, use_threading=True)
```

## Understanding Parallel Stages

The pipeline automatically identifies which stages can run in parallel:

```
Stage 0: Input (can_parallelize=False)        # 1 node - sequential
    ↓
Stage 1: FilterA, FilterB, FilterC (can_parallelize=True)  # 3 nodes - PARALLEL!
    ↓
Stage 2: Merge (can_parallelize=False)        # 1 node - sequential
    ↓
Stage 3: Output (can_parallelize=False)       # 1 node - sequential
```

## Viewing Pipeline Structure

```python
from OV_Libs.ProjStoreLib.pipeline_builder import get_pipeline_summary

# Print detailed pipeline info
print(get_pipeline_summary(pipeline))
```

Output:
```
Pipeline Summary:
  Total Stages: 4
  Total Nodes: 6

Stage 0: (1 node)
  - Image Input (input) (source)

Stage 1 [PARALLEL]: (3 nodes)      ← Multiple nodes execute simultaneously
  - Color Filter (filter_a) <- [input]
  - Blur Filter (filter_b) <- [input]
  - Brightness Filter (filter_c) <- [input]

Stage 2: (1 node)
  - Merge (merge) <- [filter_a, filter_b, filter_c]

Stage 3: (1 node)
  - Output (output) <- [merge]

Execution Order: input -> filter_a -> filter_b -> filter_c -> merge -> output
```

## Advanced Options

### Disable Threading (for debugging)
```python
results = execute_pipeline(pipeline, executors, use_threading=False)
```

### Limit Thread Count
```python
# Limit to 4 threads
results = execute_pipeline(pipeline, executors, use_threading=True, max_workers=4)
```

### Error Handling
```python
try:
    results = execute_pipeline(pipeline, executors)
except KeyError as e:
    print(f"Missing executor: {e}")
except Exception as e:
    print(f"Execution failed: {e}")
```

## Executor Function Template

```python
def your_executor(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Args:
        node: Node data dictionary containing:
              - "id": unique node identifier
              - "type": node type name
              - "inputs": list of dependency node IDs
              - ... any custom properties from your node graph
              
        inputs: List of results from dependency nodes
                Order matches the "inputs" list in the node data
    
    Returns:
        Any value to pass to downstream nodes
    """
    # Access node properties
    node_id = node["id"]
    custom_param = node.get("my_parameter", default_value)
    
    # Process inputs (if any)
    if inputs:
        input_data = inputs[0]  # First input
        # Process...
    
    # Return result for downstream nodes
    return result
```

## Performance Tips

### When Parallel Execution Helps
- ✓ Multiple nodes in a stage (2+)
- ✓ I/O-bound operations (file loading, API calls)
- ✓ Nodes with significant processing time (>100ms)
- ✓ Multi-core CPU available

### When to Use Sequential
- ✗ Very fast operations (<10ms)
- ✗ Debugging complex issues
- ✗ Memory-constrained systems
- ✗ Single-node stages (automatic)

## Common Patterns

### Pattern 1: Load Multiple Images in Parallel
```python
# These 3 image loads happen simultaneously
Input1 (image1.jpg) ─┐
Input2 (image2.jpg) ─┼─→ Merge
Input3 (image3.jpg) ─┘
```

### Pattern 2: Apply Multiple Filters in Parallel
```python
              ┌─→ Blur Filter    ─┐
Input Image ──┼─→ Color Filter   ─┼─→ Merge → Output
              └─→ Sharpen Filter ─┘
```

### Pattern 3: Process Multiple Branches
```python
Input1 ─→ ProcessA ─┐
                     ├─→ Combine → Output
Input2 ─→ ProcessB ─┘
```

## Example: Image Processing Pipeline

```python
from PIL import Image
from OV_Libs.ProjStoreLib.pipeline_builder import *

# Define node graph
nodes = [
    {"id": "img1", "type": "ImageInput", "x": 0, "path": "input1.jpg"},
    {"id": "blur", "type": "BlurFilter", "x": 200, "radius": 5},
    {"id": "color", "type": "ColorFilter", "x": 200, "hue_shift": 30},
    {"id": "merge", "type": "Merge", "x": 400},
    {"id": "out", "type": "Output", "x": 600, "path": "output.jpg"}
]

connections = [
    {"from_node": "img1", "to_node": "blur"},
    {"from_node": "img1", "to_node": "color"},
    {"from_node": "blur", "to_node": "merge"},
    {"from_node": "color", "to_node": "merge"},
    {"from_node": "merge", "to_node": "out"}
]

# Build pipeline
pipeline, valid, errors = build_pipeline_from_graph(nodes, connections)

# Define executors
def load_image(node, inputs):
    return Image.open(node["path"])

def blur_filter(node, inputs):
    from PIL import ImageFilter
    return inputs[0].filter(ImageFilter.GaussianBlur(radius=node["radius"]))

def color_filter(node, inputs):
    from PIL import ImageEnhance
    return ImageEnhance.Color(inputs[0]).enhance(1 + node["hue_shift"]/100)

def merge_images(node, inputs):
    from PIL import Image
    return Image.blend(inputs[0], inputs[1], alpha=0.5)

def save_output(node, inputs):
    inputs[0].save(node["path"])
    return inputs[0]

executors = {
    "ImageInput": load_image,
    "BlurFilter": blur_filter,
    "ColorFilter": color_filter,
    "Merge": merge_images,
    "Output": save_output
}

# Execute with parallel threading
results = execute_pipeline(pipeline, executors)
print(f"Pipeline complete! Output: {results['out']}")
```

## Summary

1. Build pipeline: `build_pipeline_from_graph(nodes, connections)`
2. Define executors: `{node_type: executor_function}`
3. Execute: `execute_pipeline(pipeline, executors)`
4. Profit from automatic parallelization! 🚀
