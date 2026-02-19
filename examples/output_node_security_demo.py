"""
Output Node Path Security Examples

Demonstrates the path validation and security features that prevent
directory traversal attacks in the output node.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
from OV_Libs.NodesLib.output_node import OutputNodeConfig, OutputNodeHandler
import tempfile


def example_basic_security():
    """Example: Path traversal attempts are blocked."""
    print("=" * 60)
    print("Example 1: Path Traversal Protection")
    print("=" * 60)
    
    # Create a test image
    test_image = Image.new("RGBA", (100, 100), "blue")
    
    # Attempt 1: Try to use ../ to escape directory
    try:
        config = OutputNodeConfig(
            output_path="../../../etc/passwd"
        )
        handler = OutputNodeHandler(config)
        handler.resolve_filename()
        print("❌ FAILED: Path traversal was not blocked!")
    except ValueError as e:
        print("✓ Path traversal blocked:")
        print(f"  Error: {e}")
    
    # Attempt 2: Try relative path with ..
    try:
        config = OutputNodeConfig(
            output_path="output/../../secret.txt"
        )
        handler = OutputNodeHandler(config)
        handler.resolve_filename()
        print("❌ FAILED: Relative traversal was not blocked!")
    except ValueError as e:
        print("\n✓ Relative path traversal blocked:")
        print(f"  Error: {e}")
    
    print()


def example_base_directory_restriction():
    """Example: Using base_directory to restrict output location."""
    print("=" * 60)
    print("Example 2: Base Directory Restriction")
    print("=" * 60)
    
    # Create a temporary directory for safe outputs
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Safe directory: {temp_path}")
        
        test_image = Image.new("RGBA", (100, 100), "green")
        
        # Safe: Output within base directory
        try:
            config = OutputNodeConfig(
                output_path=str(temp_path / "safe_output.png"),
                base_directory=str(temp_path),
            )
            handler = OutputNodeHandler(config)
            result = handler.resolve_filename()
            print(f"\n✓ Safe path allowed: {result}")
        except ValueError as e:
            print(f"❌ Unexpected error: {e}")
        
        # Safe: Subdirectory within base
        try:
            config = OutputNodeConfig(
                output_path=str(temp_path / "subdir" / "output.png"),
                base_directory=str(temp_path),
            )
            handler = OutputNodeHandler(config)
            result = handler.resolve_filename()
            print(f"✓ Subdirectory allowed: {result}")
        except ValueError as e:
            print(f"❌ Unexpected error: {e}")
        
        # Unsafe: Try to write outside base directory
        try:
            outside_path = temp_path.parent / "outside" / "file.png"
            config = OutputNodeConfig(
                output_path=str(outside_path),
                base_directory=str(temp_path),
            )
            handler = OutputNodeHandler(config)
            handler.resolve_filename()
            print("❌ FAILED: Outside path was not blocked!")
        except ValueError as e:
            print(f"\n✓ Outside path blocked:")
            print(f"  Error: {str(e)[:100]}...")
    
    print()


def example_relative_paths_with_base():
    """Example: Relative paths work safely with base_directory."""
    print("=" * 60)
    print("Example 3: Relative Paths with Base Directory")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Base directory: {temp_path}")
        
        # Relative path is resolved relative to base directory
        config = OutputNodeConfig(
            output_path="outputs/image_{DATE}.png",
            base_directory=str(temp_path),
        )
        handler = OutputNodeHandler(config)
        result = handler.resolve_filename()
        
        print(f"\n✓ Relative path resolved safely:")
        print(f"  Input: outputs/image_{{DATE}}.png")
        print(f"  Resolved: {result}")
        print(f"  Within base: {str(result).startswith(str(temp_path))}")
    
    print()


def example_tags_with_security():
    """Example: Dynamic tags work with security validation."""
    print("=" * 60)
    print("Example 4: Tags with Security Validation")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = OutputNodeConfig(
            output_path=str(temp_path / "output_v{VERSION:2}_{DATE}_{COUNTER:3}.png"),
            version=5,
            base_directory=str(temp_path),
        )
        handler = OutputNodeHandler(config)
        result = handler.resolve_filename()
        
        print(f"✓ Template with tags validated:")
        print(f"  Template: output_v{{VERSION:2}}_{{DATE}}_{{COUNTER:3}}.png")
        print(f"  Resolved: {result.name}")
        print(f"  Full path: {result}")
    
    print()


def main():
    """Run all security examples."""
    print("\n" + "=" * 60)
    print("OUTPUT NODE PATH SECURITY DEMONSTRATION")
    print("=" * 60)
    print("\nThis demonstrates security features that prevent directory")
    print("traversal attacks and restrict outputs to safe locations.")
    print()
    
    example_basic_security()
    example_base_directory_restriction()
    example_relative_paths_with_base()
    example_tags_with_security()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\nSecurity Features:")
    print("  ✓ Path traversal detection (blocks .. sequences)")
    print("  ✓ Base directory restriction (optional)")
    print("  ✓ Absolute path validation")
    print("  ✓ Relative path safety")
    print("  ✓ Works with dynamic filename tags")
    print("\nBest Practices:")
    print("  • Always set base_directory when accepting user input")
    print("  • Use absolute paths for base_directory")
    print("  • Validate output_path comes from trusted sources")
    print("  • Check error messages for security violations")
    print()


if __name__ == "__main__":
    main()
