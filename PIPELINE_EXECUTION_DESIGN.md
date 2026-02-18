# Node Graph Pipeline Execution Design

## Overview

This document describes the algorithm for building an actionable task pipeline from a connected node graph. The pipeline stages are determined by dependency analysis: each filter or merge node is assigned to a pipeline stage that is one more than the highest pipeline stage of its input nodes.

## Core Concept

**Pipeline Stage Assignment Rule:**
- Input nodes (no dependencies): Stage 0
- Processing nodes: Stage = max(all input node stages) + 1
- Output nodes: Stage = max(all input node stages) + 1

This ensures that all dependencies are resolved before a node executes.

## Data Structures

### Input: Node Graph
```json
{
  "nodes": [
    {"id": "node-1", "type": "Image Input", "x": 100, "y": 200},
    {"id": "node-2", "type": "Color Replace", "x": 300, "y": 200},
    {"id": "node-3", "type": "Output", "x": 500, "y": 200}
  ],
  "connections": [
    {"from_node": "node-1", "from_port": "output", "to_node": "node-2", "to_port": "input"},
    {"from_node": "node-2", "from_port": "output", "to_node": "node-3", "to_port": "input"}
  ]
}
```

### Output: Execution Pipeline
```python
{
  "stages": [
    {
      "stage_number": 0,
      "can_parallelize": False,
      "nodes": [
        {"id": "node-1", "type": "Image Input", "inputs": []}
      ]
    },
    {
      "stage_number": 1,
      "can_parallelize": False,
      "nodes": [
        {"id": "node-2", "type": "Color Replace", "inputs": ["node-1"]}
      ]
    },
    {
      "stage_number": 2,
      "can_parallelize": False,
      "nodes": [
        {"id": "node-3", "type": "Output", "inputs": ["node-2"]}
      ]
    }
  ],
  "max_stage": 2,
  "execution_order": ["node-1", "node-2", "node-3"]
}
```

## Algorithm Steps

### Step 1: Build Dependency Map
Create a mapping of each node to its input dependencies.

```python
dependencies = {
    "node-1": [],           # No inputs (source node)
    "node-2": ["node-1"],   # Depends on node-1
    "node-3": ["node-2"]    # Depends on node-2
}
```

### Step 2: Assign Pipeline Stages
Use topological sorting with stage calculation:

1. **Initialize**: All nodes start unassigned
2. **Find Source Nodes**: Nodes with no dependencies → Stage 0
3. **Iteratively Assign Stages**:
   - For each unassigned node:
     - Check if all input nodes have assigned stages
     - If yes: `node_stage = max(input_stages) + 1`
     - If no: Skip and try next iteration
4. **Repeat** until all nodes are assigned or cycle detected

### Step 3: Group by Stage
Organize nodes into stage groups for execution:

```python
stage_0 = [nodes with stage 0]  # Execute first
stage_1 = [nodes with stage 1]  # Execute after stage 0
stage_2 = [nodes with stage 2]  # Execute after stage 1
...
```

### Step 4: Validate Pipeline
- **Cycle Detection**: If any nodes remain unassigned, there's a cycle
- **Disconnected Nodes**: Warn about nodes with no connections
- **Multiple Outputs**: Check if graph has proper output nodes

## Example Scenarios

### Example 1: Linear Pipeline
```
Input → Process → Output

Stages:
- Stage 0: Input
- Stage 1: Process
- Stage 2: Output
```

### Example 2: Parallel Processing
```
Input 1 →\
           → Merge → Output
Input 2 →/

Stages:
- Stage 0: Input 1, Input 2 (can_parallelize=True, 2 nodes)
- Stage 1: Merge (can_parallelize=False, 1 node)
- Stage 2: Output (can_parallelize=False, 1 node)
```

### Example 3: Complex Multi-Path
```
Input 1 → Filter A →\
                      → Merge 1 → Filter C → Output
Input 2 → Filter B →/

Stages:
- Stage 0: Input 1, Input 2 (can_parallelize=True, 2 nodes)
- Stage 1: Filter A, Filter B (can_parallelize=True, 2 nodes)
- Stage 2: Merge 1 (can_parallelize=False, 1 node)
- Stage 3: Filter C (can_parallelize=False, 1 node)
- Stage 4: Output (can_parallelize=False, 1 node)
```

### Example 4: Diamond Pattern
```
        → Filter A →\
Input →             → Merge → Output
        → Filter B →/

Stages:
- Stage 0: Input (can_parallelize=False, 1 node)
- Stage 1: Filter A, Filter B (can_parallelize=True, 2 nodes)
- Stage 2: Merge (can_parallelize=False, 1 node)
- Stage 3: Output (can_parallelize=False, 1 node)
```

## Implementation Functions

### Function 1: `build_dependency_map(nodes, connections)`
**Purpose**: Create node-to-inputs mapping

**Input**: 
- `nodes`: List of node dictionaries
- `connections`: List of connection dictionaries

**Output**:
```python
{
  "node-id": ["input-id-1", "input-id-2", ...]
}
```

**Logic**:
- Initialize all nodes with empty lists
- For each connection, add from_node to to_node's dependency list

---

### Function 2: `calculate_pipeline_stages(nodes, dependencies)`
**Purpose**: Assign stage number to each node

**Input**:
- `nodes`: List of node dictionaries
- `dependencies`: Dependency map from Function 1

**Output**:
```python
{
  "node-id": stage_number
}
```

**Algorithm**:
```
1. node_stages = {}
2. unassigned = set(all node ids)

3. While unassigned is not empty:
   a. progress_made = False
   
   b. For each node_id in unassigned:
      i. Get node's input dependencies
      
      ii. If no dependencies:
          - node_stages[node_id] = 0
          - Remove from unassigned
          - progress_made = True
      
      iii. Else if all dependencies have assigned stages:
          - input_stages = [node_stages[dep] for dep in dependencies]
          - node_stages[node_id] = max(input_stages) + 1
          - Remove from unassigned
          - progress_made = True
   
   c. If NOT progress_made:
      - CYCLE DETECTED: raise error
      
4. Return node_stages
```

---

### Function 3: `build_execution_pipeline(nodes, node_stages)`
**Purpose**: Group nodes by stage and create execution plan

**Input**:
- `nodes`: List of node dictionaries
- `node_stages`: Stage assignments from Function 2

**Output**:
```python
{
  "stages": [
    {"stage_number": 0, "can_parallelize": bool, "nodes": [...]},
    {"stage_number": 1, "can_parallelize": bool, "nodes": [...]},
    ...
  ],
  "max_stage": int,
  "execution_order": ["node-id-1", "node-id-2", ...]
}
```

**Logic**:
1. Find max_stage = max(node_stages.values())
2. Create stage buckets: stages[0] through stages[max_stage]
3. For each node, add to appropriate stage bucket
4. Sort nodes within each stage (optional, for consistency)
5. Flatten to execution_order list
6. Return structured pipeline

---

### Function 4: `validate_pipeline(pipeline, nodes, connections)`
**Purpose**: Validate pipeline integrity

**Checks**:
- All nodes are included in pipeline
- No circular dependencies
- Each node appears in exactly one stage
- Input nodes have no dependencies
- Output nodes exist and are reachable
- All connections reference valid nodes

**Returns**: `(is_valid: bool, errors: List[str])`

---

### Function 5: `execute_pipeline(pipeline, node_executors, use_threading=True)`
**Purpose**: Execute nodes in pipeline order with optional parallel execution

**Input**:
- `pipeline`: Execution pipeline from Function 3
- `node_executors`: Dict mapping node types to executor functions
- `use_threading`: Enable parallel execution for stages with multiple nodes (default: True)

**Logic**:
```python
import concurrent.futures

results = {}

for stage in pipeline["stages"]:
    stage_results = {}
    
    # Execute nodes in parallel if stage allows it
    if stage["can_parallelize"] and use_threading and len(stage["nodes"]) > 1:
        # Parallel execution using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            for node in stage["nodes"]:
                node_executor = node_executors[node["type"]]
                inputs = [results[dep_id] for dep_id in node["inputs"]]
                future = executor.submit(node_executor, node, inputs)
                futures[future] = node["id"]
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                node_id = futures[future]
                stage_results[node_id] = future.result()
    else:
        # Sequential execution for single-node stages or when threading disabled
        for node in stage["nodes"]:
            executor_fn = node_executors[node["type"]]
            inputs = [results[dep_id] for dep_id in node["inputs"]]
            output = executor_fn(node, inputs)
            stage_results[node["id"]] = output
    
    # Store results for next stage
    results.update(stage_results)

return results
```

---

### Function 6: `build_update_pipeline(nodes, connections, updated_node_ids)`
**Purpose**: Build a partial pipeline starting from recently updated node(s)

**Input**:
- `nodes`: List of node dictionaries
- `connections`: List of connection dictionaries
- `updated_node_ids`: Iterable of node IDs that changed

**Output**:
```python
(
  {
    "stages": [
      {"stage_number": 0, "nodes": [...]},
      {"stage_number": 1, "nodes": [...]},
      ...
    ],
    "max_stage": int,
    "execution_order": ["node-id-1", "node-id-2", ...]
  },
  is_valid: bool,
  errors: List[str]
)
```

**Logic**:
1. Normalize and validate `updated_node_ids`
2. Traverse downstream connections to collect affected nodes
3. Build stages from the affected subgraph
4. Preserve full dependency inputs so cached upstream results can be reused
5. Validate the affected subgraph only

## Error Handling

### Cycle Detection
**Problem**: Node A depends on Node B, Node B depends on Node A
**Detection**: No progress made in assignment iteration
**Error Message**: "Circular dependency detected: cannot build execution pipeline"

### Disconnected Nodes
**Problem**: Nodes with no connections
**Detection**: Node has no inputs and no outputs
**Warning**: "Node {id} ({type}) is disconnected from the graph"

### Missing Input Nodes
**Problem**: All processing starts from somewhere
**Detection**: No nodes with stage 0
**Error**: "Graph has no input nodes"

### Multiple Output Paths
**Problem**: Unclear which output to use
**Detection**: Multiple nodes with no outputs
**Warning**: "Multiple output nodes detected: {node_ids}"

## Integration Points

### Where to Add This

**File**: `ProjStoreLib/pipeline_builder.py` (new file)

**Functions to Implement**:
- `build_dependency_map(nodes, connections) -> Dict[str, List[str]]`
- `calculate_pipeline_stages(nodes, dependencies) -> Dict[str, int]`
- `build_execution_pipeline(nodes, node_stages, dependencies) -> Dict`
- `validate_pipeline(pipeline, nodes, connections) -> Tuple[bool, List[str]]`

**Usage in Node Editor**:
```python
from ProjStoreLib.pipeline_builder import (
    build_dependency_map,
    calculate_pipeline_stages,
    build_execution_pipeline,
    validate_pipeline
)

# In NodeEditorWindow, add "Build Pipeline" button
def build_pipeline(self):
    nodes = self.collect_nodes()
    connections = self.connections
    
    deps = build_dependency_map(nodes, connections)
    stages = calculate_pipeline_stages(nodes, deps)
    pipeline = build_execution_pipeline(nodes, stages, deps)
    
    is_valid, errors = validate_pipeline(pipeline, nodes, connections)
    
    if not is_valid:
        show_errors(errors)
    else:
        self.current_pipeline = pipeline
        show_pipeline_viewer(pipeline)
```

## Inspiration: Teensy Audio Library Approach

The Teensy Audio Library (https://github.com/PaulStoffregen/Audio) provides an excellent reference implementation for node-based audio processing with similar requirements:

### Key Insights from Teensy Audio

1. **Separation of Visual Layout and Execution Graph**
   - Visual layout stored in GUI tool (x, y coordinates)
   - Execution order determined by signal flow analysis
   - Nodes sorted by horizontal position for predictable updates

2. **Connection-Based Execution**
   - Each `AudioConnection` object represents a link between nodes
   - Connections are created at compile time (static) or runtime (dynamic)
   - Connection format: `AudioConnection(sourceNode, sourcePort, destNode, destPort)`

3. **Update-Based Processing**
   - Every node has an `update()` method called periodically
   - Nodes use `receiveReadOnly()` to get input from connected nodes
   - Nodes use `transmit()` to send output to connected nodes
   - Framework automatically handles buffer management

4. **Topological Execution Order**
   - GUI tool sorts nodes: `nns.sort(function(a,b){ return (a.x + a.y/250) - (b.x + b.y/250); })`
   - Left-to-right processing follows natural signal flow
   - Slight vertical component (`y/250`) provides tie-breaking for same x-position

5. **Generated Code Pattern**
   ```cpp
   // Node declarations
   AudioInputI2S            audioInput;
   AudioFilterBiquad        filter;
   AudioOutputI2S           audioOutput;
   
   // Connection declarations (defines the graph)
   AudioConnection          patchCord1(audioInput, 0, filter, 0);
   AudioConnection          patchCord2(filter, 0, audioOutput, 0);
   ```

6. **Dynamic Connection Management**
   - Connections can be created/deleted at runtime
   - `connect()` and `disconnect()` methods
   - Each input port accepts only one connection
   - Output ports can connect to multiple inputs

### Adaptation to Open Vision

**Similarities to Apply**:
- Store visual layout (x, y) separately from execution logic
- Use horizontal position as primary sorting key for execution order
- Build dependency graph from connection list
- Maintain separation between visual editing and graph execution

**Key Difference**:
- Teensy uses periodic `update()` callbacks driven by hardware timer
- Open Vision uses on-demand execution triggered by user action
- Our pipeline stages allow explicit parallelization within each stage

**Recommended Approach**:
1. Keep visual coordinates in project file (already doing this)
2. Build execution pipeline from connections (this design)
3. Use horizontal position as hint for stage assignment tie-breaking
4. Support dynamic connection changes (reconnect, add, remove nodes)

## Parallel Execution

### Overview
The pipeline automatically identifies stages where nodes can execute in parallel. A stage is marked as parallelizable (`can_parallelize=True`) when it contains 2 or more nodes that have no inter-dependencies within that stage.

### Parallelization Rules

**Stage is Parallelizable when:**
- Stage contains 2 or more nodes
- Nodes in the stage do not depend on each other
- All nodes' dependencies are satisfied from previous stages

**Stage is NOT Parallelizable when:**
- Stage contains only 1 node
- (Future: user disables parallel execution for specific node types)

### Threading Model

**ThreadPoolExecutor** (Default):
- Suitable for I/O-bound operations (file loading, API calls)
- Lower overhead than multiprocessing
- Shares memory space (efficient for image data)
- Limited by Python GIL for CPU-bound operations

**Future Enhancement - ProcessPoolExecutor**:
- For CPU-intensive filters (blur, transforms, complex algorithms)
- Bypasses GIL limitations
- Higher overhead for data serialization
- Configurable per-node or per-stage

### Performance Considerations

1. **Threading Overhead**: Only beneficial when nodes have significant work
2. **Memory Usage**: Parallel execution may increase peak memory
3. **GIL Impact**: CPU-bound nodes may not benefit from threading
4. **Resource Contention**: Too many threads can degrade performance

### Configuration Options (Future)

```python
execution_config = {
    "enable_parallel": True,
    "max_workers": None,  # None = CPU count, or specify max threads
    "threading_model": "thread",  # "thread" or "process"
    "force_sequential_nodes": ["Output", "Video Writer"]  # Always run sequential
}
```

### Example Parallel Execution

```python
# Stage 1 has 3 independent filter nodes - all execute in parallel
Stage 1: [Blur Filter, Color Shift, Brightness Adjust]
         can_parallelize=True
         
# These 3 filters run simultaneously on different threads
# Results are collected before proceeding to Stage 2
```

## Future Enhancements

### Caching

### Caching
Cache node outputs to avoid recomputation when upstream doesn't change

### Conditional Execution
Add conditional nodes that can skip stages based on conditions

### Progress Tracking
Report progress as stages complete

### Partial Re-execution
Only re-execute nodes affected by changes

**Update Pipeline (Implemented)**:
- `build_update_pipeline()` produces the minimal downstream pipeline from a changed node
- Intended for image changes or parameter updates to reduce execution cost

## Testing Strategy

### Test Case 1: Linear Graph
```
Input → Process → Output
Expected: 3 stages
```

### Test Case 2: Parallel Inputs
```
Input1 → Merge → Output
Input2 →/
Expected: 3 stages, Input1 and Input2 in stage 0
```

### Test Case 3: Cycle Detection
```
A → B → C → A (cycle)
Expected: Error raised
```

### Test Case 4: Diamond Pattern
```
Input → A → Merge → Output
     → B →/
Expected: 4 stages
```

### Test Case 5: Disconnected Node
```
Input → Output
ProcessNode (isolated)
Expected: Warning for ProcessNode
```

## Summary

This pipeline execution design provides:
1. **Deterministic execution order** based on dependencies
2. **Parallelization opportunities** within stages
3. **Cycle detection** to prevent infinite loops
4. **Validation** to catch graph errors
5. **Clear execution model** for complex node graphs

The implementation will enable the node editor to execute arbitrary node graphs correctly while maintaining data flow integrity.
