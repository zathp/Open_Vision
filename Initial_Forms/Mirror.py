from PIL import Image
import os
import sys


def mirror_image(input_path, axis='horizontal', output_path=None):
    """
    Mirror an image along a specified axis.
    
    Args:
        input_path: Path to the input image
        axis: One of 'horizontal', 'vertical', 'diagonal_tl_br', 'diagonal_tr_bl'
              - 'horizontal': flip top-bottom
              - 'vertical': flip left-right
              - 'diagonal_tl_br': flip along diagonal from top-left to bottom-right
              - 'diagonal_tr_bl': flip along diagonal from top-right to bottom-left
        output_path: Path to save the mirrored image (optional)
    
    Returns:
        PIL Image object of the mirrored image
    """
    # Load the image
    img = Image.open(input_path)
    
    if axis == 'horizontal':
        # Flip top to bottom
        mirrored_img = img.transpose(Image.FLIP_TOP_BOTTOM)
    elif axis == 'vertical':
        # Flip left to right
        mirrored_img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif axis == 'diagonal_tl_br':
        # Transpose (flip along top-left to bottom-right diagonal)
        mirrored_img = img.transpose(Image.TRANSPOSE)
    elif axis == 'diagonal_tr_bl':
        # Transverse (flip along top-right to bottom-left diagonal)
        mirrored_img = img.transpose(Image.TRANSVERSE)
    else:
        raise ValueError(f"Invalid axis: {axis}. Must be 'horizontal', 'vertical', 'diagonal_tl_br', or 'diagonal_tr_bl'")
    
    # Save if output path is provided
    if output_path:
        mirrored_img.save(output_path)
        print(f"Saved mirrored image to {output_path}")
    
    return mirrored_img


def main():
    """Main function to run the mirror tool."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python Mirror.py <input_image> [axis] [output_image]")
        print("\nAxis options:")
        print("  horizontal     - Flip top to bottom (default)")
        print("  vertical       - Flip left to right")
        print("  diagonal_tl_br - Flip along top-left to bottom-right diagonal")
        print("  diagonal_tr_bl - Flip along top-right to bottom-left diagonal")
        print("\nExamples:")
        print("  python Mirror.py input.png")
        print("  python Mirror.py input.png vertical")
        print("  python Mirror.py input.png diagonal_tl_br output.png")
        return
    
    input_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.isfile(input_path):
        print(f"Error: {input_path} is not a valid file")
        return
    
    # Default axis
    axis = 'horizontal'
    if len(sys.argv) >= 3:
        axis = sys.argv[2].lower()
    
    # Determine output path
    if len(sys.argv) >= 4:
        output_path = sys.argv[3]
    else:
        # Generate output filename based on axis
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_{axis}{ext}"
    
    # Validate axis
    valid_axes = ['horizontal', 'vertical', 'diagonal_tl_br', 'diagonal_tr_bl']
    if axis not in valid_axes:
        print(f"Error: Invalid axis '{axis}'")
        print(f"Valid options: {', '.join(valid_axes)}")
        return
    
    # Mirror the image
    print(f"Mirroring {input_path} along {axis} axis...")
    try:
        mirror_image(input_path, axis, output_path)
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
