# Parallel Execution Implementation Summary

## Overview
The pipeline execution system now supports **parallel execution** of independent nodes within the same stage, enabling multi-threading for actionable tasks. This provides significant performance improvements for node graphs with parallel processing paths.

## Key Features Added

### 1. Parallel Stage Detection
- Each pipeline stage is now marked with a `can_parallelize` flag
- A stage is parallelizable when it contains **2 or more nodes** with no inter-dependencies
- Example: In a diamond pattern, the two filter branches can execute simultaneously

### 2. Updated Pipeline Structure
The pipeline output now includes parallelization metadata:

```python
{
  "stages": [
    {
      "stage_number": 0,
      "can_parallelize": False,  # Single node
      "nodes": [...]
    },
    {
      "stage_number": 1,
      "can_parallelize": True,   # Multiple parallel nodes
      "nodes": [...]
    }
  ],
  "max_stage": int,
  "execution_order": [...]
}
```

### 3. New `execute_pipeline()` Function
A complete pipeline executor with optional parallel execution:

```python
results = execute_pipeline(
    pipeline,           # Pipeline from build_pipeline_from_graph()
    node_executors,     # Dict mapping node types to executor functions
    use_threading=True, # Enable parallel execution (default: True)
    max_workers=None    # Thread pool size (default: CPU count)
)
```

**Features:**
- Automatically uses `ThreadPoolExecutor` for parallelizable stages
- Falls back to sequential execution for single-node stages
- Maintains correct dependency order
- Provides detailed error messages with node context

## Performance Benefits

### Test Results (Diamond Pattern)
- **Sequential**: 2.00 seconds
- **Parallel**: 1.01 seconds
- **Speedup**: ~2x faster

The speedup is proportional to:
- Number of parallel nodes in a stage
- Processing time per node
- Available CPU cores

## Implementation Files Modified

### 1. [PIPELINE_EXECUTION_DESIGN.md](PIPELINE_EXECUTION_DESIGN.md)
**Changes:**
- Added comprehensive "Parallel Execution" section
- Updated all examples to show `can_parallelize` flag
- Updated `execute_pipeline()` function signature and implementation
- Added threading model discussion
- Added performance considerations

### 2. [OV_Libs/ProjStoreLib/pipeline_builder.py](OV_Libs/ProjStoreLib/pipeline_builder.py)
**Changes:**
- `build_execution_pipeline()`: Now sets `can_parallelize` flag on each stage
- `get_pipeline_summary()`: Shows `[PARALLEL]` marker for parallelizable stages
- `execute_pipeline()`: New function with full threading support
- Updated docstrings to reflect new structure

## Usage Examples

### Basic Execution
```python
from OV_Libs.ProjStoreLib.pipeline_builder import (
    build_pipeline_from_graph,
    execute_pipeline
)

# Build pipeline
pipeline, is_valid, errors = build_pipeline_from_graph(nodes, connections)

# Define executors
node_executors = {
    "Image Input": load_image_executor,
    "Color Filter": color_filter_executor,
    "Merge": merge_executor,
    "Output": save_image_executor
}

# Execute with parallel threading (recommended)
results = execute_pipeline(pipeline, node_executors, use_threading=True)
```

### Sequential Execution (for debugging)
```python
# Disable threading for easier debugging
results = execute_pipeline(pipeline, node_executors, use_threading=False)
```

### Custom Thread Pool Size
```python
# Limit to 4 threads
results = execute_pipeline(pipeline, node_executors, max_workers=4)
```

## Executor Function Signature

Each node executor must follow this signature:

```python
def executor_function(node: Dict[str, Any], inputs: List[Any]) -> Any:
    """
    Args:
        node: Full node dictionary with id, type, and any custom properties
        inputs: List of results from dependency nodes (in order)
    
    Returns:
        Result to be passed to downstream nodes
    """
    # Process node...
    return result
```

## Pipeline Summary Output

The `get_pipeline_summary()` function now shows parallel stages:

```
Pipeline Summary:
  Total Stages: 4
  Total Nodes: 6

Stage 0: (1 node)
  - Input (input) (source)

Stage 1 [PARALLEL]: (3 nodes)      # <-- Marked as parallel
  - Filter (filter_a) <- [input]
  - Filter (filter_b) <- [input]
  - Filter (filter_c) <- [input]

Stage 2: (1 node)
  - Merge (merge) <- [filter_a, filter_b, filter_c]

Stage 3: (1 node)
  - Output (output) <- [merge]

Execution Order: input -> filter_a -> filter_b -> filter_c -> merge -> output
```

## Threading Model

### Current: ThreadPoolExecutor
- **Best for**: I/O-bound operations (file loading, API calls, disk writes)
- **Pros**: Low overhead, shared memory space
- **Cons**: Limited by Python GIL for CPU-intensive tasks

### Future: ProcessPoolExecutor Option
- **Best for**: CPU-intensive filters (blur, transforms, complex algorithms)
- **Pros**: Bypasses GIL, true parallelism for CPU work
- **Cons**: Higher overhead for data serialization

## Testing

All existing tests pass with the new implementation:
```bash
python -m unittest tests.test_pipeline_builder -v
# 22 tests - All PASS
```

Demo script showing parallel execution benefits:
```bash
python test_parallel_execution.py
# Shows ~2x speedup for parallel stage
```

## Future Enhancements

### Planned Features
1. **ProcessPoolExecutor Support**: For CPU-intensive operations
2. **Per-Node Threading Config**: Disable threading for specific node types
3. **Adaptive Thread Pool**: Adjust worker count based on stage size
4. **Progress Callbacks**: Report progress as stages complete
5. **Result Caching**: Cache node outputs to skip recomputation

### Configuration (Future)
```python
execution_config = {
    "enable_parallel": True,
    "max_workers": None,
    "threading_model": "thread",  # or "process"
    "force_sequential_nodes": ["Output", "Video Writer"],
    "enable_caching": True
}
```

## Migration Notes

### Existing Code Compatibility
The changes are **backward compatible**:
- Existing pipeline building code works unchanged
- New `can_parallelize` field is added but optional to use
- `execute_pipeline()` is a new function (doesn't affect existing code)

### Recommended Updates
For projects wanting to use parallel execution:

1. Import the new executor:
   ```python
   from OV_Libs.ProjStoreLib.pipeline_builder import execute_pipeline
   ```

2. Define executor functions for each node type

3. Call `execute_pipeline()` instead of manual iteration

## Performance Considerations

### When Parallel Execution Helps
✓ Multiple independent nodes in a stage  
✓ Nodes with significant processing time (>100ms)  
✓ I/O-bound operations (file loading, network calls)  
✓ Available CPU cores > 1  

### When to Disable Parallel Execution
✗ Single-node stages (auto-detected)  
✗ Very fast operations (<10ms per node)  
✗ Memory-constrained environments  
✗ Debugging complex issues  

### Thread Pool Size Guidelines
- **Default (None)**: Uses CPU count - good for most cases
- **Low (2-4)**: For systems with limited resources
- **High (8+)**: Only if you have many parallel nodes AND sufficient CPU cores

## Summary

The pipeline now has full support for parallel execution:
- ✅ Automatic detection of parallelizable stages
- ✅ Thread-based parallel execution
- ✅ Sequential fallback for single nodes
- ✅ Comprehensive error handling
- ✅ Performance improvements demonstrated
- ✅ All tests passing
- ✅ Backward compatible

**Result**: Multi-threaded execution of independent nodes provides significant performance improvements for complex node graphs! 🚀
