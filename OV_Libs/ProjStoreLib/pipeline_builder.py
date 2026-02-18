"""
Pipeline Builder for Node Graph Execution

This module builds an actionable task pipeline from a connected node graph,
determining execution stages based on dependency analysis. Each node is assigned
to a pipeline stage that is one more than the highest stage of its input nodes.

Inspired by the Teensy Audio Library's approach to node-based processing.
"""

from typing import Dict, List, Set, Tuple, Any, Iterable


def build_dependency_map(nodes: List[Dict[str, Any]], connections: List[Dict[str, str]]) -> Dict[str, List[str]]:
    """
    Build a mapping of each node to its input dependencies.
    
    Args:
        nodes: List of node dictionaries with 'id' keys
        connections: List of connection dictionaries with 'from_node' and 'to_node' keys
    
    Returns:
        Dictionary mapping node_id -> list of input node_ids
        
    Example:
        >>> nodes = [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}]
        >>> connections = [{"from_node": "n1", "to_node": "n2"}, {"from_node": "n2", "to_node": "n3"}]
        >>> build_dependency_map(nodes, connections)
        {'n1': [], 'n2': ['n1'], 'n3': ['n2']}
    """
    # Initialize all nodes with empty dependency lists
    dependencies: Dict[str, List[str]] = {}
    for node in nodes:
        node_id = str(node.get("id", ""))
        if node_id:
            dependencies[node_id] = []
    
    # Build dependency map from connections
    for connection in connections:
        from_node = str(connection.get("from_node", ""))
        to_node = str(connection.get("to_node", ""))
        
        # Only add valid connections between known nodes
        if from_node and to_node and to_node in dependencies:
            if from_node not in dependencies[to_node]:
                dependencies[to_node].append(from_node)
    
    return dependencies


def calculate_pipeline_stages(
    nodes: List[Dict[str, Any]], 
    dependencies: Dict[str, List[str]]
) -> Dict[str, int]:
    """
    Assign pipeline stage number to each node using topological sorting.
    
    Source nodes (no dependencies) are assigned stage 0.
    Each subsequent node is assigned: max(input_stages) + 1
    
    Args:
        nodes: List of node dictionaries with 'id' and optional 'x', 'y' keys
        dependencies: Dependency map from build_dependency_map()
    
    Returns:
        Dictionary mapping node_id -> stage_number
        
    Raises:
        ValueError: If circular dependency detected
        
    Example:
        >>> nodes = [{"id": "n1", "x": 100}, {"id": "n2", "x": 300}, {"id": "n3", "x": 500}]
        >>> deps = {"n1": [], "n2": ["n1"], "n3": ["n2"]}
        >>> calculate_pipeline_stages(nodes, deps)
        {'n1': 0, 'n2': 1, 'n3': 2}
    """
    node_stages: Dict[str, int] = {}
    unassigned: Set[str] = set(dependencies.keys())
    
    # Create node lookup for position-based tie-breaking
    node_lookup = {str(node.get("id", "")): node for node in nodes if node.get("id")}
    
    # Iteratively assign stages
    max_iterations = len(unassigned) + 1  # Prevent infinite loops
    iteration = 0
    
    while unassigned and iteration < max_iterations:
        progress_made = False
        
        # Process nodes in horizontal order (left to right)
        # Sort by x position, with y as tie-breaker (like Teensy Audio)
        nodes_to_process = sorted(
            unassigned,
            key=lambda nid: (
                node_lookup.get(nid, {}).get("x", 0),
                node_lookup.get(nid, {}).get("y", 0) / 250.0
            )
        )
        
        for node_id in nodes_to_process:
            node_deps = dependencies.get(node_id, [])
            
            # Source node (no dependencies)
            if not node_deps:
                node_stages[node_id] = 0
                unassigned.remove(node_id)
                progress_made = True
                continue
            
            # Check if all dependencies have assigned stages
            all_deps_assigned = all(dep_id in node_stages for dep_id in node_deps)
            
            if all_deps_assigned:
                # Calculate stage as max of input stages + 1
                input_stages = [node_stages[dep_id] for dep_id in node_deps]
                node_stages[node_id] = max(input_stages) + 1
                unassigned.remove(node_id)
                progress_made = True
        
        if not progress_made:
            # No progress means circular dependency
            cycle_nodes = ", ".join(sorted(unassigned))
            raise ValueError(
                f"Circular dependency detected: cannot assign stages to nodes: {cycle_nodes}"
            )
        
        iteration += 1
    
    return node_stages


def build_execution_pipeline(
    nodes: List[Dict[str, Any]],
    node_stages: Dict[str, int],
    dependencies: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Group nodes by stage and create execution plan.
    
    Args:
        nodes: List of node dictionaries
        node_stages: Stage assignments from calculate_pipeline_stages()
        dependencies: Dependency map from build_dependency_map()
    
    Returns:
        Dictionary with pipeline structure:
        {
            "stages": [
                {"stage_number": 0, "can_parallelize": bool, "nodes": [...]},
                {"stage_number": 1, "can_parallelize": bool, "nodes": [...]},
                ...
            ],
            "max_stage": int,
            "execution_order": ["node-id-1", "node-id-2", ...]
        }
        
        The 'can_parallelize' flag is True when a stage has 2+ nodes that can
        execute independently (no inter-dependencies within the stage).
        
    Example:
        >>> nodes = [{"id": "n1", "type": "Input"}, {"id": "n2", "type": "Filter"}]
        >>> stages = {"n1": 0, "n2": 1}
        >>> deps = {"n1": [], "n2": ["n1"]}
        >>> pipeline = build_execution_pipeline(nodes, stages, deps)
        >>> pipeline["max_stage"]
        1
    """
    if not node_stages:
        return {
            "stages": [],
            "max_stage": -1,
            "execution_order": []
        }
    
    # Find maximum stage
    max_stage = max(node_stages.values())
    
    # Create stage buckets
    stage_buckets: Dict[int, List[Dict[str, Any]]] = {}
    for stage_num in range(max_stage + 1):
        stage_buckets[stage_num] = []
    
    # Create node lookup
    node_lookup = {str(node.get("id", "")): node for node in nodes if node.get("id")}
    
    # Assign nodes to stages
    for node_id, stage_num in node_stages.items():
        if node_id in node_lookup:
            node_data = node_lookup[node_id].copy()
            # Add dependency information
            node_data["inputs"] = dependencies.get(node_id, [])
            stage_buckets[stage_num].append(node_data)
    
    # Sort nodes within each stage by horizontal position
    for stage_num in stage_buckets:
        stage_buckets[stage_num].sort(
            key=lambda n: (n.get("x", 0), n.get("y", 0) / 250.0)
        )
    
    # Build stage list with parallelization metadata
    stages = []
    for stage_num in range(max_stage + 1):
        stage_nodes = stage_buckets[stage_num]
        # A stage can parallelize if it has 2+ nodes with no inter-dependencies
        can_parallelize = len(stage_nodes) >= 2
        
        stages.append({
            "stage_number": stage_num,
            "can_parallelize": can_parallelize,
            "nodes": stage_nodes
        })
    
    # Build execution order (flattened list)
    execution_order = []
    for stage in stages:
        for node in stage["nodes"]:
            execution_order.append(str(node.get("id", "")))
    
    return {
        "stages": stages,
        "max_stage": max_stage,
        "execution_order": execution_order
    }


def validate_pipeline(
    pipeline: Dict[str, Any],
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, str]]
) -> Tuple[bool, List[str]]:
    """
    Validate pipeline integrity and structure.
    
    Performs the following checks:
    - All nodes are included in pipeline
    - Each node appears exactly once
    - No orphaned nodes (disconnected from graph)
    - Pipeline has at least one input node (stage 0)
    - Connections reference valid nodes
    
    Args:
        pipeline: Pipeline structure from build_execution_pipeline()
        nodes: List of node dictionaries
        connections: List of connection dictionaries
    
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
        
    Example:
        >>> pipeline = {"stages": [...], "max_stage": 2, "execution_order": ["n1", "n2", "n3"]}
        >>> nodes = [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}]
        >>> connections = [{"from_node": "n1", "to_node": "n2"}]
        >>> is_valid, errors = validate_pipeline(pipeline, nodes, connections)
        >>> is_valid
        True
    """
    errors: List[str] = []
    
    # Get all node IDs
    all_node_ids = {str(node.get("id", "")) for node in nodes if node.get("id")}
    pipeline_node_ids = set(pipeline.get("execution_order", []))
    
    # Check: All nodes included in pipeline
    missing_nodes = all_node_ids - pipeline_node_ids
    if missing_nodes:
        errors.append(f"Nodes missing from pipeline: {', '.join(sorted(missing_nodes))}")
    
    # Check: No extra nodes in pipeline
    extra_nodes = pipeline_node_ids - all_node_ids
    if extra_nodes:
        errors.append(f"Unknown nodes in pipeline: {', '.join(sorted(extra_nodes))}")
    
    # Check: Each node appears exactly once
    execution_order = pipeline.get("execution_order", [])
    if len(execution_order) != len(set(execution_order)):
        duplicates = [nid for nid in execution_order if execution_order.count(nid) > 1]
        errors.append(f"Nodes appear multiple times in pipeline: {', '.join(set(duplicates))}")
    
    # Check: Pipeline has input nodes (stage 0)
    stages = pipeline.get("stages", [])
    if stages and stages[0].get("stage_number") == 0:
        stage_0_nodes = stages[0].get("nodes", [])
        if not stage_0_nodes:
            errors.append("Pipeline has no input nodes (stage 0 is empty)")
    elif not stages:
        errors.append("Pipeline has no stages")
    
    # Check: Connections reference valid nodes
    for idx, connection in enumerate(connections):
        from_node = str(connection.get("from_node", ""))
        to_node = str(connection.get("to_node", ""))
        
        if from_node and from_node not in all_node_ids:
            errors.append(f"Connection {idx}: from_node '{from_node}' does not exist")
        
        if to_node and to_node not in all_node_ids:
            errors.append(f"Connection {idx}: to_node '{to_node}' does not exist")
    
    # Warning: Check for disconnected nodes (optional - may be intentional)
    connected_nodes = set()
    for connection in connections:
        from_node = str(connection.get("from_node", ""))
        to_node = str(connection.get("to_node", ""))
        if from_node:
            connected_nodes.add(from_node)
        if to_node:
            connected_nodes.add(to_node)
    
    disconnected = all_node_ids - connected_nodes
    if disconnected:
        node_types = []
        for node in nodes:
            if str(node.get("id", "")) in disconnected:
                node_types.append(f"{node.get('type', 'Unknown')} ({node.get('id', '')})")
        errors.append(f"Warning: Disconnected nodes detected: {', '.join(node_types)}")
    
    # Pipeline is valid if no critical errors (warnings are OK)
    critical_errors = [e for e in errors if not e.startswith("Warning:")]
    is_valid = len(critical_errors) == 0
    
    return is_valid, errors


def build_pipeline_from_graph(
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, str]]
) -> Tuple[Dict[str, Any], bool, List[str]]:
    """
    Convenience function to build complete pipeline from node graph.
    
    This is the main entry point for pipeline construction.
    Combines all pipeline building steps into a single call.
    
    Args:
        nodes: List of node dictionaries with 'id', 'type', 'x', 'y' keys
        connections: List of connection dictionaries with 'from_node', 'to_node' keys
    
    Returns:
        Tuple of (pipeline: Dict, is_valid: bool, errors: List[str])
        
    Example:
        >>> nodes = [{"id": "n1", "type": "Input", "x": 100, "y": 100}]
        >>> connections = []
        >>> pipeline, is_valid, errors = build_pipeline_from_graph(nodes, connections)
        >>> is_valid
        True
    """
    try:
        # Step 1: Build dependency map
        dependencies = build_dependency_map(nodes, connections)
        
        # Step 2: Calculate pipeline stages
        node_stages = calculate_pipeline_stages(nodes, dependencies)
        
        # Step 3: Build execution pipeline
        pipeline = build_execution_pipeline(nodes, node_stages, dependencies)
        
        # Step 4: Validate pipeline
        is_valid, errors = validate_pipeline(pipeline, nodes, connections)
        
        return pipeline, is_valid, errors
        
    except ValueError as e:
        # Circular dependency or other structural error
        empty_pipeline = {
            "stages": [],
            "max_stage": -1,
            "execution_order": []
        }
        return empty_pipeline, False, [str(e)]
    except Exception as e:
        # Unexpected error
        empty_pipeline = {
            "stages": [],
            "max_stage": -1,
            "execution_order": []
        }
        return empty_pipeline, False, [f"Unexpected error building pipeline: {str(e)}"]


def _normalize_updated_nodes(updated_node_ids: Iterable[str]) -> Set[str]:
    normalized: Set[str] = set()
    for node_id in updated_node_ids:
        node_str = str(node_id).strip()
        if node_str:
            normalized.add(node_str)
    return normalized


def _build_downstream_map(connections: List[Dict[str, str]]) -> Dict[str, List[str]]:
    downstream: Dict[str, List[str]] = {}
    for connection in connections:
        from_node = str(connection.get("from_node", "")).strip()
        to_node = str(connection.get("to_node", "")).strip()
        if not from_node or not to_node:
            continue
        if from_node not in downstream:
            downstream[from_node] = []
        if to_node not in downstream[from_node]:
            downstream[from_node].append(to_node)
    return downstream


def build_update_pipeline(
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, str]],
    updated_node_ids: Iterable[str]
) -> Tuple[Dict[str, Any], bool, List[str]]:
    """
    Build a partial pipeline starting from recently updated node(s).

    This reduces execution to only the updated node(s) and their downstream
    dependents, allowing cached upstream results to be reused.

    Args:
        nodes: List of node dictionaries with 'id', 'type', 'x', 'y' keys
        connections: List of connection dictionaries with 'from_node', 'to_node' keys
        updated_node_ids: Iterable of node ids that were updated

    Returns:
        Tuple of (pipeline: Dict, is_valid: bool, errors: List[str])
    """
    try:
        if not nodes:
            return {"stages": [], "max_stage": -1, "execution_order": []}, False, ["No nodes provided"]

        all_node_ids = {str(node.get("id", "")) for node in nodes if node.get("id")}
        normalized_updated = _normalize_updated_nodes(updated_node_ids)
        valid_updated = {nid for nid in normalized_updated if nid in all_node_ids}

        if not valid_updated:
            return {"stages": [], "max_stage": -1, "execution_order": []}, False, [
                "No valid updated nodes provided"
            ]

        downstream_map = _build_downstream_map(connections)

        # Collect all downstream nodes reachable from updated nodes
        affected: Set[str] = set(valid_updated)
        queue = list(valid_updated)
        while queue:
            current = queue.pop(0)
            for next_node in downstream_map.get(current, []):
                if next_node not in affected:
                    affected.add(next_node)
                    queue.append(next_node)

        # Filter nodes and connections to affected subgraph
        affected_nodes = [node for node in nodes if str(node.get("id", "")) in affected]
        affected_connections = [
            c for c in connections
            if str(c.get("from_node", "")) in affected and str(c.get("to_node", "")) in affected
        ]

        # Build full dependency map (used for inputs) and filtered for staging
        full_dependencies = build_dependency_map(nodes, connections)
        filtered_dependencies: Dict[str, List[str]] = {}
        for node_id in affected:
            deps = full_dependencies.get(node_id, [])
            filtered_dependencies[node_id] = [d for d in deps if d in affected]

        # Calculate stages within affected subgraph
        node_stages = calculate_pipeline_stages(affected_nodes, filtered_dependencies)

        # Build pipeline; keep full inputs so cached upstream data can be used
        pipeline = build_execution_pipeline(affected_nodes, node_stages, full_dependencies)

        # Validate only within affected subgraph
        is_valid, errors = validate_pipeline(pipeline, affected_nodes, affected_connections)

        return pipeline, is_valid, errors

    except ValueError as e:
        empty_pipeline = {"stages": [], "max_stage": -1, "execution_order": []}
        return empty_pipeline, False, [str(e)]
    except Exception as e:
        empty_pipeline = {"stages": [], "max_stage": -1, "execution_order": []}
        return empty_pipeline, False, [f"Unexpected error building update pipeline: {str(e)}"]


def get_pipeline_summary(pipeline: Dict[str, Any]) -> str:
    """
    Generate human-readable summary of pipeline structure.
    
    Args:
        pipeline: Pipeline structure from build_execution_pipeline()
    
    Returns:
        Multi-line string describing the pipeline
        
    Example:
        >>> pipeline = {"stages": [...], "max_stage": 2, "execution_order": ["n1", "n2"]}
        >>> print(get_pipeline_summary(pipeline))
        Pipeline Summary:
        Total Stages: 3
        Total Nodes: 2
        ...
    """
    stages = pipeline.get("stages", [])
    max_stage = pipeline.get("max_stage", -1)
    execution_order = pipeline.get("execution_order", [])
    
    lines = [
        "Pipeline Summary:",
        f"  Total Stages: {max_stage + 1}",
        f"  Total Nodes: {len(execution_order)}",
        ""
    ]
    
    for stage in stages:
        stage_num = stage.get("stage_number", 0)
        nodes = stage.get("nodes", [])
        can_parallelize = stage.get("can_parallelize", False)
        parallel_marker = " [PARALLEL]" if can_parallelize else ""
        
        lines.append(f"Stage {stage_num}{parallel_marker}: ({len(nodes)} node{'s' if len(nodes) != 1 else ''})")
        
        for node in nodes:
            node_id = node.get("id", "unknown")
            node_type = node.get("type", "Unknown")
            inputs = node.get("inputs", [])
            
            if inputs:
                input_str = f" <- [{', '.join(inputs)}]"
            else:
                input_str = " (source)"
            
            lines.append(f"  - {node_type} ({node_id}){input_str}")
        
        lines.append("")
    
    lines.append(f"Execution Order: {' -> '.join(execution_order)}")
    
    return "\n".join(lines)


def execute_pipeline(
    pipeline: Dict[str, Any],
    node_executors: Dict[str, Any],
    use_threading: bool = True,
    max_workers: int = None
) -> Dict[str, Any]:
    """
    Execute nodes in pipeline order with optional parallel execution.
    
    Stages marked with can_parallelize=True will execute nodes in parallel
    using ThreadPoolExecutor when use_threading is enabled.
    
    Args:
        pipeline: Pipeline structure from build_execution_pipeline()
        node_executors: Dict mapping node types to executor functions
                       Each executor should accept (node_data: Dict, inputs: List) -> result
        use_threading: Enable parallel execution for parallelizable stages (default: True)
        max_workers: Maximum number of threads (default: None = CPU count)
    
    Returns:
        Dictionary mapping node_id -> execution result
        
    Raises:
        KeyError: If a node type has no registered executor
        Exception: Any exception raised by node executors
        
    Example:
        >>> def input_executor(node, inputs):
        ...     return load_image(node["path"])
        >>> 
        >>> executors = {"Image Input": input_executor, "Filter": filter_executor}
        >>> results = execute_pipeline(pipeline, executors, use_threading=True)
        >>> output_image = results["output-node-1"]
    """
    import concurrent.futures
    
    results: Dict[str, Any] = {}
    
    for stage in pipeline.get("stages", []):
        stage_results: Dict[str, Any] = {}
        stage_nodes = stage.get("nodes", [])
        can_parallelize = stage.get("can_parallelize", False)
        
        # Execute nodes in parallel if stage allows it and threading is enabled
        if can_parallelize and use_threading and len(stage_nodes) > 1:
            # Parallel execution using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures: Dict[concurrent.futures.Future, str] = {}
                
                for node in stage_nodes:
                    node_type = node.get("type", "")
                    node_id = str(node.get("id", ""))
                    
                    if node_type not in node_executors:
                        raise KeyError(f"No executor registered for node type: {node_type}")
                    
                    node_executor = node_executors[node_type]
                    inputs = [results[dep_id] for dep_id in node.get("inputs", [])]
                    
                    # Submit task to thread pool
                    future = executor.submit(node_executor, node, inputs)
                    futures[future] = node_id
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(futures):
                    node_id = futures[future]
                    try:
                        stage_results[node_id] = future.result()
                    except Exception as e:
                        # Re-raise with node context
                        raise Exception(f"Error executing node {node_id}: {str(e)}") from e
        else:
            # Sequential execution for single-node stages or when threading disabled
            for node in stage_nodes:
                node_type = node.get("type", "")
                node_id = str(node.get("id", ""))
                
                if node_type not in node_executors:
                    raise KeyError(f"No executor registered for node type: {node_type}")
                
                executor_fn = node_executors[node_type]
                inputs = [results[dep_id] for dep_id in node.get("inputs", [])]
                
                try:
                    output = executor_fn(node, inputs)
                    stage_results[node_id] = output
                except Exception as e:
                    # Re-raise with node context
                    raise Exception(f"Error executing node {node_id}: {str(e)}") from e
        
        # Store results for next stage
        results.update(stage_results)
    
    return results
