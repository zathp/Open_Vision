from PIL import Image
import numpy as np
import colorsys
import os
import sys


def downsample_image_hsv(input_path, output_size=(32, 32)):
    """
    Downsample an image to the specified size using HSV averaging
    from only fully opaque pixels (alpha = 255).
    
    Args:
        input_path: Path to the input image
        output_size: Tuple of (width, height) for output image
    
    Returns:
        PIL Image object of the downsampled image
    """
    # Load the image
    img = Image.open(input_path).convert('RGBA')
    original_size = img.size
    
    # Calculate block sizes
    block_width = original_size[0] / output_size[0]
    block_height = original_size[1] / output_size[1]
    
    # Convert to numpy array for easier processing
    img_array = np.array(img)
    
    # Create output array
    output_array = np.zeros((output_size[1], output_size[0], 4), dtype=np.uint8)
    
    # Process each output pixel
    for out_y in range(output_size[1]):
        for out_x in range(output_size[0]):
            # Calculate the corresponding region in the input image
            start_x = int(out_x * block_width)
            end_x = int((out_x + 1) * block_width)
            start_y = int(out_y * block_height)
            end_y = int((out_y + 1) * block_height)
            
            # Extract the block
            block = img_array[start_y:end_y, start_x:end_x]
            
            # Get fully opaque pixels (alpha = 255)
            opaque_mask = block[:, :, 3] == 255
            opaque_pixels = block[opaque_mask]
            
            if len(opaque_pixels) > 0:
                # Convert RGB to HSV for opaque pixels only
                hsv_values = []
                for pixel in opaque_pixels:
                    r, g, b = pixel[0] / 255.0, pixel[1] / 255.0, pixel[2] / 255.0
                    h, s, v = colorsys.rgb_to_hsv(r, g, b)
                    hsv_values.append([h, s, v])
                
                hsv_values = np.array(hsv_values)
                
                # Average HSV (with special handling for hue)
                # For hue, we need to handle the circular nature (0-360 degrees)
                avg_h = np.arctan2(np.mean(np.sin(hsv_values[:, 0] * 2 * np.pi)),
                                   np.mean(np.cos(hsv_values[:, 0] * 2 * np.pi))) / (2 * np.pi)
                if avg_h < 0:
                    avg_h += 1.0
                
                avg_s = np.mean(hsv_values[:, 1])
                avg_v = np.mean(hsv_values[:, 2])
                
                # Convert back to RGB
                r, g, b = colorsys.hsv_to_rgb(avg_h, avg_s, avg_v)
                
                # Set output pixel with full opacity
                output_array[out_y, out_x] = [
                    int(r * 255),
                    int(g * 255),
                    int(b * 255),
                    255
                ]
            else:
                # No opaque pixels in this block - set as transparent
                output_array[out_y, out_x] = [0, 0, 0, 0]
    
    # Convert back to PIL Image
    output_img = Image.fromarray(output_array, 'RGBA')
    return output_img


def process_directory(input_dir, output_dir, output_size=(32, 32)):
    """
    Process all PNG images in a directory.
    
    Args:
        input_dir: Directory containing input images
        output_dir: Directory to save downsampled images
        output_size: Tuple of (width, height) for output images
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each PNG file
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.png'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            
            print(f"Processing {filename}...")
            try:
                downsampled_img = downsample_image_hsv(input_path, output_size)
                downsampled_img.save(output_path)
                print(f"  Saved to {output_path}")
            except Exception as e:
                print(f"  Error processing {filename}: {e}")


def main():
    """Main function to run the downsampler."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single file: python Downsampler.py <input_image> [output_image]")
        print("  Directory:   python Downsampler.py <input_dir> <output_dir>")
        print("\nOptional: Add width and height (default 32x32)")
        print("  python Downsampler.py <input> <output> <width> <height>")
        return
    
    input_path = sys.argv[1]
    
    # Default output size
    width = 32
    height = 32
    
    # Check if width and height are provided
    if len(sys.argv) >= 5:
        width = int(sys.argv[3])
        height = int(sys.argv[4])
    
    output_size = (width, height)
    
    if os.path.isfile(input_path):
        # Single file processing
        output_path = sys.argv[2] if len(sys.argv) >= 3 else input_path.replace('.png', '_32x32.png')
        print(f"Downsampling {input_path} to {output_size[0]}x{output_size[1]}...")
        downsampled_img = downsample_image_hsv(input_path, output_size)
        downsampled_img.save(output_path)
        print(f"Saved to {output_path}")
    
    elif os.path.isdir(input_path):
        # Directory processing
        output_dir = sys.argv[2] if len(sys.argv) >= 3 else input_path + "_32x32"
        print(f"Processing directory {input_path}...")
        print(f"Output size: {output_size[0]}x{output_size[1]}")
        process_directory(input_path, output_dir, output_size)
        print("Done!")
    
    else:
        print(f"Error: {input_path} is not a valid file or directory")


if __name__ == "__main__":
    main()
