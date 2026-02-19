"""
Performance demonstration for mask blur acceleration.

Shows the speedup gained from using NumPy/CuPy backends compared to PIL fallback.
Run this script to see performance differences on your system.

Install acceleration dependencies:
    pip install numpy scipy      # For NumPy acceleration
    pip install cupy-cuda11x     # For GPU acceleration (optional)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from PIL import Image

from OV_Libs.NodesLib.mask_blur_node import (
    apply_mask_blur,
    get_available_backend,
)


def benchmark_mask_blur(size, radius, blur_type="gaussian", iterations=3):
    """Benchmark mask blur with different backends."""
    print(f"\nBenchmarking {size}x{size} image with radius={radius}, type={blur_type}")
    print(f"Current backend: {get_available_backend()}")
    print("-" * 60)
    
    # Create test images
    img = Image.new("RGBA", (size, size), (200, 100, 50, 255))
    strength = Image.new("RGBA", (size, size), (200, 200, 200, 255))
    
    # Test with current (auto-detected) backend
    times_auto = []
    for i in range(iterations):
        start = time.time()
        result = apply_mask_blur(img, strength, blur_type=blur_type, max_radius=radius)
        elapsed = time.time() - start
        times_auto.append(elapsed)
        if i == 0:  # First run might include warmup
            print(f"  Auto backend run {i+1}: {elapsed:.3f}s (warmup)")
        else:
            print(f"  Auto backend run {i+1}: {elapsed:.3f}s")
    
    avg_auto = sum(times_auto[1:]) / len(times_auto[1:])  # Exclude first run
    print(f"Average (excluding warmup): {avg_auto:.3f}s")
    
    # Test with PIL fallback for comparison
    print("\nForcing PIL backend for comparison...")
    times_pil = []
    for i in range(iterations):
        start = time.time()
        result = apply_mask_blur(img, strength, blur_type=blur_type, 
                                max_radius=radius, backend="pil")
        elapsed = time.time() - start
        times_pil.append(elapsed)
        if i == 0:
            print(f"  PIL backend run {i+1}: {elapsed:.3f}s (warmup)")
        else:
            print(f"  PIL backend run {i+1}: {elapsed:.3f}s")
    
    avg_pil = sum(times_pil[1:]) / len(times_pil[1:])
    print(f"Average (excluding warmup): {avg_pil:.3f}s")
    
    # Calculate speedup
    if avg_auto < avg_pil:
        speedup = avg_pil / avg_auto
        print(f"\n✓ Speedup: {speedup:.2f}x faster with {get_available_backend()} backend!")
    else:
        print(f"\n⚠ Using PIL backend (no acceleration)")
    
    return avg_auto, avg_pil


def main():
    """Run performance benchmarks."""
    print("=" * 60)
    print("Mask Blur Performance Demonstration")
    print("=" * 60)
    
    backend = get_available_backend()
    print(f"\nDetected backend: {backend.upper()}")
    
    if backend == "pil":
        print("\n⚠ NumPy/SciPy not installed - using PIL fallback")
        print("Install for better performance: pip install numpy scipy")
    elif backend == "numpy":
        print("\n✓ NumPy acceleration enabled!")
        print("For GPU acceleration, install: pip install cupy-cuda11x")
    elif backend == "cupy":
        print("\n✓✓ CuPy GPU acceleration enabled!")
    
    # Run benchmarks with increasing complexity
    test_cases = [
        (200, 10, "gaussian"),
        (500, 15, "gaussian"),
        (1000, 20, "gaussian"),
        (500, 15, "box"),
    ]
    
    results = []
    for size, radius, blur_type in test_cases:
        try:
            avg_auto, avg_pil = benchmark_mask_blur(size, radius, blur_type, iterations=3)
            results.append((size, radius, blur_type, avg_auto, avg_pil))
        except KeyboardInterrupt:
            print("\n\nBenchmark interrupted by user")
            break
        except Exception as e:
            print(f"\n⚠ Error: {e}")
            continue
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Backend: {backend.upper()}")
    print("\nSize    Radius  Type      Auto      PIL       Speedup")
    print("-" * 60)
    for size, radius, blur_type, avg_auto, avg_pil in results:
        speedup = avg_pil / avg_auto if avg_auto > 0 else 1.0
        print(f"{size:4d}x{size:<4d} {radius:3d}     {blur_type[:4]:4s}  "
              f"{avg_auto:6.3f}s  {avg_pil:6.3f}s  {speedup:5.2f}x")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
