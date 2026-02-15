"""
Region Selector - Select and crop a region from an image
Allows interactive selection or coordinates-based cropping
Supports out-of-bounds selection with transparent RGBA areas
Features GUI with zoom controls for precise selection
"""

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import sys
import os

def crop_with_coordinates(image_path, x1, y1, x2, y2, output_path=None):
    """
    Crop image using specified coordinates
    Supports out-of-bounds coordinates with transparent areas
    
    Args:
        image_path: Path to input image
        x1, y1: Top-left corner coordinates
        x2, y2: Bottom-right corner coordinates
        output_path: Path to save cropped image (optional)
    """
    try:
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        # Convert to RGBA if not already (to support transparency)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Ensure coordinates are in correct order
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        
        crop_width = right - left
        crop_height = bottom - top
        
        # Check if crop region extends outside image bounds
        out_of_bounds = (left < 0 or top < 0 or 
                        right > img_width or bottom > img_height)
        
        if out_of_bounds:
            # Create new transparent image for the full crop region
            cropped = Image.new('RGBA', (crop_width, crop_height), (0, 0, 0, 0))
            
            # Calculate overlap region
            src_left = max(0, left)
            src_top = max(0, top)
            src_right = min(img_width, right)
            src_bottom = min(img_height, bottom)
            
            # Calculate paste position in the new image
            paste_x = src_left - left
            paste_y = src_top - top
            
            # Extract and paste the overlapping portion
            if src_right > src_left and src_bottom > src_top:
                img_section = img.crop((src_left, src_top, src_right, src_bottom))
                cropped.paste(img_section, (paste_x, paste_y))
            
            print(f"Note: Crop region extends outside image bounds")
            print(f"      Out-of-bounds areas will be transparent")
        else:
            # Standard crop - fully within bounds
            cropped = img.crop((left, top, right, bottom))
        
        # Generate output filename if not provided
        if output_path is None:
            base, ext = os.path.splitext(image_path)
            # Force PNG for transparency support
            if out_of_bounds and ext.lower() != '.png':
                ext = '.png'
            output_path = f"{base}_cropped_{left}_{top}_{right}_{bottom}{ext}"
        
        # Ensure PNG format if we have transparency
        if out_of_bounds and not output_path.lower().endswith('.png'):
            print("Note: Saving as PNG to preserve transparency")
            output_path = os.path.splitext(output_path)[0] + '.png'
        
        cropped.save(output_path)
        print(f"Cropped image saved to: {output_path}")
        print(f"Crop region: ({left}, {top}) to ({right}, {bottom})")
        print(f"Output size: {cropped.width}x{cropped.height}")
        
        return output_path
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def interactive_select(image_path, output_path=None):
    """
    Interactive selection using matplotlib
    Click two points to define the crop region
    
    Args:
        image_path: Path to input image
        output_path: Path to save cropped image (optional)
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        img = Image.open(image_path)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.imshow(img)
        ax.set_title("Click two points to define crop region (can extend outside image)")
        
        points = []
        rect = None
        
        def onclick(event):
            nonlocal rect
            if event.xdata is not None and event.ydata is not None:
                points.append((int(event.xdata), int(event.ydata)))
                ax.plot(event.xdata, event.ydata, 'ro', markersize=8)
                
                if len(points) == 1:
                    print(f"First point selected: ({points[0][0]}, {points[0][1]})")
                elif len(points) == 2:
                    x1, y1 = points[0]
                    x2, y2 = points[1]
                    
                    left = min(x1, x2)
                    right = max(x1, x2)
                    top = min(y1, y2)
                    bottom = max(y1, y2)
                    
                    width = right - left
                    height = bottom - top
                    
                    # Draw rectangle
                    if rect:
                        rect.remove()
                    rect = patches.Rectangle((left, top), width, height, 
                                            linewidth=2, edgecolor='red', 
                                            facecolor='none')
                    ax.add_patch(rect)
                    
                    print(f"Second point selected: ({x2}, {y2})")
                    print(f"Crop region: ({left}, {top}) to ({right}, {bottom})")
                    print(f"Size: {width}x{height}")
                    print("Close the window to save the cropped image")
                    
                fig.canvas.draw()
        
        cid = fig.canvas.mpl_connect('button_press_event', onclick)
        plt.show()
        
        if len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]
            return crop_with_coordinates(image_path, x1, y1, x2, y2, output_path)
        else:
            print("Cancelled: Two points not selected")
            return None
            
    except ImportError:
        print("Error: matplotlib is required for interactive selection")
        print("Install it with: pip install matplotlib")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def fixed_size_select(image_path, width, height, anchor='center', output_path=None):
    """
    Interactive selection with fixed size
    Click a point to define the anchor position for a fixed-size crop
    
    Args:
        image_path: Path to input image
        width: Width of the crop region
        height: Height of the crop region
        anchor: Anchor point type - 'center', 'tl', 'tr', 'bl', 'br'
        output_path: Path to save cropped image (optional)
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        anchor_names = {
            'center': 'center',
            'tl': 'top-left corner',
            'tr': 'top-right corner',
            'bl': 'bottom-left corner',
            'br': 'bottom-right corner'
        }
        
        anchor_name = anchor_names.get(anchor, anchor)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.imshow(img)
        ax.set_title(f"Click to select {anchor_name} for {width}x{height} crop (can extend outside)")
        
        point = []
        rect = None
        
        def calculate_crop_box(x, y):
            """Calculate crop box coordinates based on anchor point"""
            if anchor == 'center':
                left = x - width // 2
                top = y - height // 2
            elif anchor == 'tl':
                left = x
                top = y
            elif anchor == 'tr':
                left = x - width
                top = y
            elif anchor == 'bl':
                left = x
                top = y - height
            elif anchor == 'br':
                left = x - width
                top = y - height
            else:
                left = x - width // 2
                top = y - height // 2
            
            right = left + width
            bottom = top + height
            
            # No clamping - allow out-of-bounds selection
            return left, top, right, bottom
        
        def onclick(event):
            nonlocal rect
            if event.xdata is not None and event.ydata is not None:
                x = int(event.xdata)
                y = int(event.ydata)
                
                point.clear()
                point.append((x, y))
                
                left, top, right, bottom = calculate_crop_box(x, y)
                
                # Clear previous plot points
                ax.clear()
                ax.imshow(img)
                ax.set_title(f"Click to select {anchor_name} for {width}x{height} crop (can extend outside)")
                
                # Plot anchor point
                ax.plot(x, y, 'ro', markersize=8)
                
                # Draw rectangle
                rect = patches.Rectangle((left, top), width, height, 
                                        linewidth=2, edgecolor='red', 
                                        facecolor='none')
                ax.add_patch(rect)
                
                print(f"Anchor point selected: ({x}, {y})")
                print(f"Crop region: ({left}, {top}) to ({right}, {bottom})")
                print(f"Size: {width}x{height}")
                print("Close the window to save the cropped image")
                
                fig.canvas.draw()
        
        cid = fig.canvas.mpl_connect('button_press_event', onclick)
        plt.show()
        
        if len(point) == 1:
            x, y = point[0]
            left, top, right, bottom = calculate_crop_box(x, y)
            return crop_with_coordinates(image_path, left, top, right, bottom, output_path)
        else:
            print("Cancelled: No point selected")
            return None
            
    except ImportError:
        print("Error: matplotlib is required for interactive selection")
        print("Install it with: pip install matplotlib")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


class RegionSelectorGUI:
    """Tkinter GUI for interactive region selection"""
    
    def __init__(self, root, image_path=None):
        self.root = root
        self.root.title("Region Selector")
        self.root.geometry("1200x800")
        
        self.image_path = None
        self.original_image = None
        self.display_image = None
        self.photo = None
        self.scale = 1.0
        
        # Selection state
        self.selection_mode = tk.StringVar(value="free")
        self.anchor_mode = tk.StringVar(value="center")
        self.fixed_width = tk.IntVar(value=64)
        self.fixed_height = tk.IntVar(value=64)
        
        self.click_points = []
        self.rect_id = None
        self.point_ids = []
        
        self.setup_ui()
        
        if image_path and os.path.exists(image_path):
            self.load_image(image_path)
    
    def setup_ui(self):
        """Setup the user interface"""
        # Top toolbar
        toolbar = tk.Frame(self.root, relief=tk.RAISED, borderwidth=2)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="Open Image", command=self.open_image).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Clear Selection", command=self.clear_selection).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Save Crop", command=self.save_crop).pack(side=tk.LEFT, padx=5)
        
        # Zoom controls
        tk.Label(toolbar, text=" | ").pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Zoom In (+)", command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Zoom Out (-)", command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Reset Zoom (1:1)", command=self.zoom_reset).pack(side=tk.LEFT, padx=2)
        self.zoom_label = tk.Label(toolbar, text="Zoom: 100%", font=('Arial', 9, 'bold'))
        self.zoom_label.pack(side=tk.LEFT, padx=10)
        
        # Manual zoom entry
        tk.Label(toolbar, text="Set:").pack(side=tk.LEFT, padx=2)
        self.zoom_entry = tk.Entry(toolbar, width=6)
        self.zoom_entry.pack(side=tk.LEFT, padx=2)
        self.zoom_entry.insert(0, "100")
        self.zoom_entry.bind("<Return>", lambda e: self.set_zoom_from_entry())
        tk.Label(toolbar, text="%").pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Apply", command=self.set_zoom_from_entry, width=5).pack(side=tk.LEFT, padx=2)
        
        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - controls
        left_panel = tk.Frame(main_container, width=250, relief=tk.SUNKEN, borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        # Mode selection
        tk.Label(left_panel, text="Selection Mode:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        tk.Radiobutton(left_panel, text="Free Selection (2 clicks)", 
                      variable=self.selection_mode, value="free",
                      command=self.on_mode_change).pack(anchor=tk.W, padx=20)
        
        tk.Radiobutton(left_panel, text="Fixed Size (1 click)", 
                      variable=self.selection_mode, value="fixed",
                      command=self.on_mode_change).pack(anchor=tk.W, padx=20)
        
        # Fixed size options
        self.fixed_frame = tk.LabelFrame(left_panel, text="Fixed Size Options", padx=10, pady=10)
        self.fixed_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(self.fixed_frame, text="Width:").grid(row=0, column=0, sticky=tk.W, pady=2)
        tk.Spinbox(self.fixed_frame, from_=1, to=2000, textvariable=self.fixed_width, 
                  width=10).grid(row=0, column=1, pady=2)
        
        tk.Label(self.fixed_frame, text="Height:").grid(row=1, column=0, sticky=tk.W, pady=2)
        tk.Spinbox(self.fixed_frame, from_=1, to=2000, textvariable=self.fixed_height, 
                  width=10).grid(row=1, column=1, pady=2)
        
        tk.Label(self.fixed_frame, text="Anchor:", font=("Arial", 9, "bold")).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        tk.Radiobutton(self.fixed_frame, text="Center", variable=self.anchor_mode, 
                      value="center").grid(row=3, column=0, columnspan=2, sticky=tk.W)
        tk.Radiobutton(self.fixed_frame, text="Top-Left", variable=self.anchor_mode, 
                      value="tl").grid(row=4, column=0, columnspan=2, sticky=tk.W)
        tk.Radiobutton(self.fixed_frame, text="Top-Right", variable=self.anchor_mode, 
                      value="tr").grid(row=5, column=0, columnspan=2, sticky=tk.W)
        tk.Radiobutton(self.fixed_frame, text="Bottom-Left", variable=self.anchor_mode, 
                      value="bl").grid(row=6, column=0, columnspan=2, sticky=tk.W)
        tk.Radiobutton(self.fixed_frame, text="Bottom-Right", variable=self.anchor_mode, 
                      value="br").grid(row=7, column=0, columnspan=2, sticky=tk.W)
        
        # Info panel
        info_frame = tk.LabelFrame(left_panel, text="Selection Info", padx=10, pady=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.info_label = tk.Label(info_frame, text="No selection", justify=tk.LEFT, anchor=tk.W)
        self.info_label.pack(fill=tk.X)
        
        # Instructions
        instructions_frame = tk.LabelFrame(left_panel, text="Instructions", padx=10, pady=10)
        instructions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.instructions_text = tk.Text(instructions_frame, wrap=tk.WORD, height=10, width=30)
        self.instructions_text.pack(fill=tk.BOTH, expand=True)
        self.update_instructions()
        self.instructions_text.config(state=tk.DISABLED)
        
        # Right panel - canvas
        right_panel = tk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas with scrollbars
        canvas_frame = tk.Frame(right_panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = tk.Canvas(canvas_frame, bg="gray", 
                               xscrollcommand=self.h_scroll.set,
                               yscrollcommand=self.v_scroll.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # Keyboard shortcuts for zoom
        self.root.bind("<plus>", lambda e: self.zoom_in())
        self.root.bind("<equal>", lambda e: self.zoom_in())  # + without shift
        self.root.bind("<minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.zoom_reset())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        
        self.on_mode_change()
    
    def on_mode_change(self):
        """Update UI when mode changes"""
        if self.selection_mode.get() == "fixed":
            for child in self.fixed_frame.winfo_children():
                child.config(state=tk.NORMAL)
        else:
            for child in self.fixed_frame.winfo_children():
                if isinstance(child, (tk.Radiobutton, tk.Spinbox)):
                    child.config(state=tk.NORMAL)
        
        self.clear_selection()
        self.update_instructions()
    
    def update_instructions(self):
        """Update instruction text"""
        self.instructions_text.config(state=tk.NORMAL)
        self.instructions_text.delete(1.0, tk.END)
        
        if self.selection_mode.get() == "free":
            text = """Free Selection Mode:

1. Click two points on the image
2. First click: one corner
3. Second click: opposite corner
4. A red rectangle shows your selection
5. Click 'Save Crop' to export

You can click outside the image bounds - those areas will be transparent.

Zoom Controls:
• Mouse wheel
• +/- keys or Ctrl+Plus/Minus
• Toolbar buttons
• Manual percentage entry
• Reset: Ctrl+0"""
        else:
            text = """Fixed Size Mode:

1. Set width and height
2. Choose anchor point type
3. Click once on the image
4. The fixed-size region appears
5. Click 'Save Crop' to export

The anchor determines which part of the box you're clicking.

Zoom Controls:
• Mouse wheel
• +/- keys or Ctrl+Plus/Minus
• Toolbar buttons
• Manual percentage entry
• Reset: Ctrl+0"""
        
        self.instructions_text.insert(1.0, text)
        self.instructions_text.config(state=tk.DISABLED)
    
    def open_image(self):
        """Open file dialog and load image"""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, path):
        """Load and display an image"""
        try:
            self.image_path = path
            self.original_image = Image.open(path)
            
            if self.original_image.mode != 'RGBA':
                self.original_image = self.original_image.convert('RGBA')
            
            self.scale = 1.0
            self.update_display()
            self.clear_selection()
            self.root.title(f"Region Selector - {os.path.basename(path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{e}")
    
    def update_display(self):
        """Update the displayed image based on current zoom level"""
        if not self.original_image:
            return
        
        # Calculate new size
        new_width = int(self.original_image.width * self.scale)
        new_height = int(self.original_image.height * self.scale)
        
        # Resize image
        if self.scale == 1.0:
            self.display_image = self.original_image.copy()
        else:
            self.display_image = self.original_image.resize(
                (new_width, new_height), 
                Image.Resampling.NEAREST if self.scale > 1 else Image.Resampling.LANCZOS
            )
        
        self.photo = ImageTk.PhotoImage(self.display_image)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo, tags="image")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # Update zoom label
        zoom_percent = int(self.scale * 100)
        self.zoom_label.config(text=f"Zoom: {zoom_percent}%")
        self.zoom_entry.delete(0, tk.END)
        self.zoom_entry.insert(0, str(zoom_percent))
        
        # Redraw selection if it exists
        if self.click_points:
            self.redraw_selection()
    
    def zoom_in(self):
        """Zoom in on the image"""
        if not self.original_image:
            messagebox.showwarning("No Image", "Please open an image first")
            return
        
        self.scale *= 1.25
        if self.scale > 10.0:  # Max 1000% zoom
            self.scale = 10.0
        self.update_display()
    
    def zoom_out(self):
        """Zoom out on the image"""
        if not self.original_image:
            messagebox.showwarning("No Image", "Please open an image first")
            return
        
        self.scale /= 1.25
        if self.scale < 0.1:  # Min 10% zoom
            self.scale = 0.1
        self.update_display()
    
    def zoom_reset(self):
        """Reset zoom to 100%"""
        if not self.original_image:
            messagebox.showwarning("No Image", "Please open an image first")
            return
        
        self.scale = 1.0
        self.update_display()
    
    def set_zoom_from_entry(self):
        """Set zoom level from manual entry"""
        if not self.original_image:
            messagebox.showwarning("No Image", "Please open an image first")
            return
        
        try:
            zoom_percent = float(self.zoom_entry.get())
            if zoom_percent < 10:
                zoom_percent = 10
            elif zoom_percent > 1000:
                zoom_percent = 1000
            
            self.scale = zoom_percent / 100.0
            self.update_display()
        except ValueError:
            messagebox.showerror("Invalid Zoom", "Please enter a valid number for zoom percentage")
            # Reset to current zoom
            self.zoom_entry.delete(0, tk.END)
            self.zoom_entry.insert(0, str(int(self.scale * 100)))
    
    def on_mousewheel(self, event):
        """Handle mouse wheel zoom"""
        if not self.original_image:
            return
        
        # Mouse wheel up = zoom in, down = zoom out
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def on_canvas_click(self, event):
        """Handle canvas click events"""
        if not self.original_image:
            messagebox.showwarning("No Image", "Please open an image first")
            return
        
        # Convert canvas coordinates to image coordinates (accounting for zoom)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert display coordinates to original image coordinates
        x = canvas_x / self.scale
        y = canvas_y / self.scale
        
        if self.selection_mode.get() == "free":
            self.handle_free_selection(x, y)
        else:
            self.handle_fixed_selection(x, y)
    
    def handle_free_selection(self, x, y):
        """Handle free selection mode clicks"""
        self.click_points.append((int(x), int(y)))
        
        # Draw point at display coordinates
        display_x = x * self.scale
        display_y = y * self.scale
        point_id = self.canvas.create_oval(display_x-3, display_y-3, display_x+3, display_y+3, 
                                          fill="red", outline="white")
        self.point_ids.append(point_id)
        
        if len(self.click_points) == 1:
            self.update_info(f"Point 1: ({int(x)}, {int(y)})\nClick second point...")
        elif len(self.click_points) == 2:
            self.draw_rectangle()
    
    def handle_fixed_selection(self, x, y):
        """Handle fixed size selection mode clicks"""
        self.click_points = [(int(x), int(y))]
        
        # Clear previous
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        for point_id in self.point_ids:
            self.canvas.delete(point_id)
        self.point_ids = []
        
        # Draw anchor point at display coordinates
        display_x = x * self.scale
        display_y = y * self.scale
        point_id = self.canvas.create_oval(display_x-3, display_y-3, display_x+3, display_y+3, 
                                          fill="red", outline="white")
        self.point_ids.append(point_id)
        
        self.draw_rectangle()
    
    def draw_rectangle(self):
        """Draw selection rectangle"""
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        if self.selection_mode.get() == "free" and len(self.click_points) == 2:
            x1, y1 = self.click_points[0]
            x2, y2 = self.click_points[1]
            
            left = min(x1, x2)
            right = max(x1, x2)
            top = min(y1, y2)
            bottom = max(y1, y2)
            
        elif self.selection_mode.get() == "fixed" and len(self.click_points) == 1:
            x, y = self.click_points[0]
            width = self.fixed_width.get()
            height = self.fixed_height.get()
            anchor = self.anchor_mode.get()
            
            if anchor == 'center':
                left = x - width // 2
                top = y - height // 2
            elif anchor == 'tl':
                left = x
                top = y
            elif anchor == 'tr':
                left = x - width
                top = y
            elif anchor == 'bl':
                left = x
                top = y - height
            elif anchor == 'br':
                left = x - width
                top = y - height
            
            right = left + width
            bottom = top + height
        else:
            return
        
        # Convert to display coordinates for drawing
        display_left = left * self.scale
        display_top = top * self.scale
        display_right = right * self.scale
        display_bottom = bottom * self.scale
        
        # Draw rectangle at display coordinates
        self.rect_id = self.canvas.create_rectangle(
            display_left, display_top, display_right, display_bottom,
            outline="red", width=2, tags="selection"
        )
        
        # Update info (use original image coordinates)
        width = right - left
        height = bottom - top
        
        img_width, img_height = self.original_image.size
        out_of_bounds = (left < 0 or top < 0 or right > img_width or bottom > img_height)
        oob_text = "\n⚠ Out of bounds!" if out_of_bounds else ""
        
        info = f"Region: ({left}, {top}) to ({right}, {bottom})\nSize: {width}x{height}{oob_text}"
        self.update_info(info)
    
    def redraw_selection(self):
        """Redraw the current selection after zoom change"""
        # Clear existing visual elements
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        
        for point_id in self.point_ids:
            self.canvas.delete(point_id)
        self.point_ids = []
        
        # Redraw points at new scale
        for px, py in self.click_points:
            display_x = px * self.scale
            display_y = py * self.scale
            point_id = self.canvas.create_oval(display_x-3, display_y-3, display_x+3, display_y+3,
                                              fill="red", outline="white")
            self.point_ids.append(point_id)
        
        # Redraw rectangle
        if len(self.click_points) >= 1:
            self.draw_rectangle()
    
    def update_info(self, text):
        """Update info label"""
        self.info_label.config(text=text)
    
    def clear_selection(self):
        """Clear current selection"""
        self.click_points = []
        
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        
        for point_id in self.point_ids:
            self.canvas.delete(point_id)
        self.point_ids = []
        
        self.update_info("No selection")
    
    def save_crop(self):
        """Save the cropped region"""
        if not self.original_image:
            messagebox.showwarning("No Image", "Please open an image first")
            return
        
        if not self.click_points:
            messagebox.showwarning("No Selection", "Please make a selection first")
            return
        
        # Calculate crop coordinates
        if self.selection_mode.get() == "free" and len(self.click_points) == 2:
            x1, y1 = self.click_points[0]
            x2, y2 = self.click_points[1]
        elif self.selection_mode.get() == "fixed" and len(self.click_points) == 1:
            x, y = self.click_points[0]
            width = self.fixed_width.get()
            height = self.fixed_height.get()
            anchor = self.anchor_mode.get()
            
            if anchor == 'center':
                x1 = x - width // 2
                y1 = y - height // 2
            elif anchor == 'tl':
                x1, y1 = x, y
            elif anchor == 'tr':
                x1 = x - width
                y1 = y
            elif anchor == 'bl':
                x1 = x
                y1 = y - height
            elif anchor == 'br':
                x1 = x - width
                y1 = y - height
            
            x2 = x1 + width
            y2 = y1 + height
        else:
            messagebox.showwarning("Incomplete Selection", "Please complete your selection")
            return
        
        # Ask for save location
        default_name = os.path.splitext(os.path.basename(self.image_path))[0] + "_cropped.png"
        output_path = filedialog.asksaveasfilename(
            title="Save Cropped Image",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        
        if output_path:
            result = crop_with_coordinates(self.image_path, x1, y1, x2, y2, output_path)
            if result:
                messagebox.showinfo("Success", f"Cropped image saved to:\n{result}")


def launch_gui(image_path=None):
    """Launch the GUI application"""
    root = tk.Tk()
    app = RegionSelectorGUI(root, image_path)
    root.mainloop()


def print_usage():
    """Print usage instructions"""
    print("Region Selector - Crop regions from images")
    print("\nUsage:")
    print("  GUI mode:")
    print("    python RegionSelector.py              # Launch GUI")
    print("    python RegionSelector.py --gui        # Launch GUI")
    print("    python RegionSelector.py <image> --gui  # Launch GUI with image")
    print("\n  Interactive mode (free selection):")
    print("    python RegionSelector.py <image_path> [-o output_path]")
    print("\n  Fixed-size mode (click anchor point):")
    print("    python RegionSelector.py <image_path> -s <width> <height> [-a anchor] [-o output_path]")
    print("\n  Coordinate mode:")
    print("    python RegionSelector.py <image_path> <x1> <y1> <x2> <y2> [-o output_path]")
    print("\nAnchor options for fixed-size mode:")
    print("  center  - Click the center of the region (default)")
    print("  tl      - Click the top-left corner")
    print("  tr      - Click the top-right corner")
    print("  bl      - Click the bottom-left corner")
    print("  br      - Click the bottom-right corner")
    print("\nExamples:")
    print("  # GUI mode (recommended)")
    print("  python RegionSelector.py")
    print("  python RegionSelector.py sprite.png --gui")
    print("\n  # Interactive free selection")
    print("  python RegionSelector.py sprite.png")
    print("  python RegionSelector.py sprite.png -o cropped.png")
    print("\n  # Fixed size (64x64) selecting center point")
    print("  python RegionSelector.py sprite.png -s 64 64")
    print("  python RegionSelector.py sprite.png -s 64 64 -a center -o region.png")
    print("\n  # Fixed size selecting top-left corner")
    print("  python RegionSelector.py sprite.png -s 32 32 -a tl")
    print("\n  # Direct coordinates (can be negative or outside bounds)")
    print("  python RegionSelector.py sprite.png 10 10 100 100")
    print("  python RegionSelector.py sprite.png -10 -10 50 50  # extends outside image")
    print("  python RegionSelector.py sprite.png 10 10 100 100 -o region.png")
    print("\nModes:")
    print("  GUI: Visual interface with point-and-click selection")
    print("  Interactive: Click two points on the image to define the crop region")
    print("  Fixed-size: Click one point as anchor for a preset-sized region")
    print("  Coordinate: Specify x1,y1 (top-left) and x2,y2 (bottom-right)")
    print("\nNote: Regions extending outside image bounds will have transparent (RGBA) areas")
    print("      Output will be saved as PNG to preserve transparency")


if __name__ == "__main__":
    # Check for GUI mode
    if len(sys.argv) == 1:
        # No arguments - launch GUI
        launch_gui()
        sys.exit(0)
    
    if "--gui" in sys.argv:
        # GUI flag present
        image_path = None
        if len(sys.argv) >= 2 and sys.argv[1] != "--gui":
            if os.path.exists(sys.argv[1]):
                image_path = sys.argv[1]
        launch_gui(image_path)
        sys.exit(0)
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)
    
    # Parse all flags
    output_path = None
    crop_width = None
    crop_height = None
    anchor = 'center'
    
    # Check for output path flag
    if "-o" in sys.argv:
        o_index = sys.argv.index("-o")
        if o_index + 1 < len(sys.argv):
            output_path = sys.argv[o_index + 1]
        else:
            print("Error: -o flag requires an output path")
            sys.exit(1)
    
    # Check for size flag
    if "-s" in sys.argv:
        s_index = sys.argv.index("-s")
        if s_index + 2 < len(sys.argv):
            try:
                crop_width = int(sys.argv[s_index + 1])
                crop_height = int(sys.argv[s_index + 2])
            except ValueError:
                print("Error: Size dimensions must be integers")
                sys.exit(1)
        else:
            print("Error: -s flag requires width and height")
            sys.exit(1)
    
    # Check for anchor flag
    if "-a" in sys.argv:
        a_index = sys.argv.index("-a")
        if a_index + 1 < len(sys.argv):
            anchor = sys.argv[a_index + 1]
            if anchor not in ['center', 'tl', 'tr', 'bl', 'br']:
                print(f"Error: Invalid anchor '{anchor}'. Use: center, tl, tr, bl, or br")
                sys.exit(1)
        else:
            print("Error: -a flag requires an anchor type")
            sys.exit(1)
    
    # Remove flags and their values for coordinate detection
    args_cleaned = [sys.argv[0], sys.argv[1]]
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] in ['-o', '-s', '-a']:
            # Skip flag and its value(s)
            if sys.argv[i] == '-s':
                i += 3  # -s width height
            elif sys.argv[i] == '-o':
                i += 2  # -o output_path
            elif sys.argv[i] == '-a':
                i += 2  # -a anchor
        else:
            args_cleaned.append(sys.argv[i])
            i += 1
    
    # Determine mode
    if crop_width is not None and crop_height is not None:
        # Fixed-size mode
        print(f"Opening {image_path} in fixed-size mode ({crop_width}x{crop_height}, anchor: {anchor})...")
        fixed_size_select(image_path, crop_width, crop_height, anchor, output_path)
    elif len(args_cleaned) == 2:
        # Interactive mode
        print(f"Opening {image_path} in interactive mode...")
        interactive_select(image_path, output_path)
    elif len(args_cleaned) >= 6:
        # Coordinate mode
        try:
            x1 = int(args_cleaned[2])
            y1 = int(args_cleaned[3])
            x2 = int(args_cleaned[4])
            y2 = int(args_cleaned[5])
            crop_with_coordinates(image_path, x1, y1, x2, y2, output_path)
        except ValueError:
            print("Error: Coordinates must be integers")
            print_usage()
            sys.exit(1)
    else:
        print("Error: Invalid arguments")
        print_usage()
        sys.exit(1)
