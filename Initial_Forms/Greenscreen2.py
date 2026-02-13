import tkinter as tk
from tkinter import filedialog, colorchooser
from PIL import Image, ImageTk
import numpy as np
import colorsys

class ColorReplacerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Color Replacer")
        
        self.original_image = None
        self.modified_image = None
        self.color_mappings = {}
        self.unique_colors = []
        self.base_color = None  # For range selection
        
        # Store canvas image position and scale info
        self.original_img_offset = (0, 0)
        self.original_img_scale = 1.0
        self.modified_img_offset = (0, 0)
        self.modified_img_scale = 1.0
        
        # Create main frames
        # Left frame with scrollbar
        left_container = tk.Frame(root)
        left_container.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH)
        
        left_canvas = tk.Canvas(left_container, width=350)
        scrollbar = tk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        self.left_frame = tk.Frame(left_canvas)
        
        self.left_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=self.left_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=scrollbar.set)
        
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        middle_frame = tk.Frame(root)
        middle_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Load button
        tk.Button(self.left_frame, text="Load Image", command=self.load_image).pack(pady=5)
        
        # Original colors list
        tk.Label(self.left_frame, text="Original Colors:").pack()
        self.original_listbox = tk.Listbox(self.left_frame, width=30, height=20)
        self.original_listbox.pack(pady=5)
        
        # Replacement colors list
        tk.Label(self.left_frame, text="Replacement Colors (click to change):").pack()
        self.replacement_listbox = tk.Listbox(self.left_frame, width=30, height=20)
        self.replacement_listbox.pack(pady=5)
        self.replacement_listbox.bind('<Double-Button-1>', self.change_color)
        
        # HSV Mass Edit Section
        tk.Label(self.left_frame, text="--- HSV Mass Edit ---", font='bold').pack(pady=(10, 2))
        
        # Hue adjustment
        hsv_frame = tk.Frame(self.left_frame)
        hsv_frame.pack(pady=2, fill=tk.X)
        tk.Label(hsv_frame, text="Hue:", width=8).pack(side=tk.LEFT)
        self.hue_var = tk.StringVar(value="0")
        tk.Entry(hsv_frame, textvariable=self.hue_var, width=8).pack(side=tk.LEFT, padx=2)
        tk.Label(hsv_frame, text="(-180 to 180)").pack(side=tk.LEFT)
        
        # Saturation adjustment
        sat_frame = tk.Frame(self.left_frame)
        sat_frame.pack(pady=2, fill=tk.X)
        tk.Label(sat_frame, text="Sat:", width=8).pack(side=tk.LEFT)
        self.sat_var = tk.StringVar(value="0")
        tk.Entry(sat_frame, textvariable=self.sat_var, width=8).pack(side=tk.LEFT, padx=2)
        tk.Label(sat_frame, text="(-100 to 100)").pack(side=tk.LEFT)
        
        # Value adjustment
        val_frame = tk.Frame(self.left_frame)
        val_frame.pack(pady=2, fill=tk.X)
        tk.Label(val_frame, text="Value:", width=8).pack(side=tk.LEFT)
        self.val_var = tk.StringVar(value="0")
        tk.Entry(val_frame, textvariable=self.val_var, width=8).pack(side=tk.LEFT, padx=2)
        tk.Label(val_frame, text="(-100 to 100)").pack(side=tk.LEFT)
        
        # Apply HSV buttons
        hsv_btn_frame = tk.Frame(self.left_frame)
        hsv_btn_frame.pack(pady=5)
        tk.Button(hsv_btn_frame, text="Apply to Selected", command=self.apply_hsv_to_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(hsv_btn_frame, text="Apply to All", command=self.apply_hsv_to_all).pack(side=tk.LEFT, padx=2)
        
        # Color Range Selection Section
        tk.Label(self.left_frame, text="--- Select by Color Range ---", font='bold').pack(pady=(10, 2))
        
        # Base color display
        base_color_frame = tk.Frame(self.left_frame)
        base_color_frame.pack(pady=2, fill=tk.X)
        tk.Label(base_color_frame, text="Base:", width=8).pack(side=tk.LEFT)
        self.base_color_display = tk.Label(base_color_frame, text="Click pixel or Pick", bg='lightgray', relief=tk.SUNKEN, width=20)
        self.base_color_display.pack(side=tk.LEFT, padx=2)
        tk.Button(base_color_frame, text="Pick", command=self.pick_base_color, width=5).pack(side=tk.LEFT)
        
        # Tolerance mode selector
        mode_frame = tk.Frame(self.left_frame)
        mode_frame.pack(pady=2, fill=tk.X)
        tk.Label(mode_frame, text="Mode:", width=8).pack(side=tk.LEFT)
        self.tolerance_mode = tk.StringVar(value="RGB")
        tk.Radiobutton(mode_frame, text="RGB", variable=self.tolerance_mode, value="RGB", command=self.update_tolerance_labels).pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="HSV", variable=self.tolerance_mode, value="HSV", command=self.update_tolerance_labels).pack(side=tk.LEFT)
        
        # Channel 1 tolerance (R or H)
        tol1_frame = tk.Frame(self.left_frame)
        tol1_frame.pack(pady=2, fill=tk.X)
        self.tol1_label = tk.Label(tol1_frame, text="R Tol:", width=8)
        self.tol1_label.pack(side=tk.LEFT)
        self.tol1_var = tk.StringVar(value="10")
        tk.Entry(tol1_frame, textvariable=self.tol1_var, width=8).pack(side=tk.LEFT, padx=2)
        self.tol1_range = tk.Label(tol1_frame, text="(0-255)")
        self.tol1_range.pack(side=tk.LEFT)
        
        # Channel 2 tolerance (G or S)
        tol2_frame = tk.Frame(self.left_frame)
        tol2_frame.pack(pady=2, fill=tk.X)
        self.tol2_label = tk.Label(tol2_frame, text="G Tol:", width=8)
        self.tol2_label.pack(side=tk.LEFT)
        self.tol2_var = tk.StringVar(value="10")
        tk.Entry(tol2_frame, textvariable=self.tol2_var, width=8).pack(side=tk.LEFT, padx=2)
        self.tol2_range = tk.Label(tol2_frame, text="(0-255)")
        self.tol2_range.pack(side=tk.LEFT)
        
        # Channel 3 tolerance (B or V)
        tol3_frame = tk.Frame(self.left_frame)
        tol3_frame.pack(pady=2, fill=tk.X)
        self.tol3_label = tk.Label(tol3_frame, text="B Tol:", width=8)
        self.tol3_label.pack(side=tk.LEFT)
        self.tol3_var = tk.StringVar(value="10")
        tk.Entry(tol3_frame, textvariable=self.tol3_var, width=8).pack(side=tk.LEFT, padx=2)
        self.tol3_range = tk.Label(tol3_frame, text="(0-255)")
        self.tol3_range.pack(side=tk.LEFT)
        
        # Select by range button
        tk.Button(self.left_frame, text="Select Colors in Range", command=self.select_by_range).pack(pady=5)
        
        # Apply button
        tk.Button(self.left_frame, text="Apply Changes", command=self.apply_changes).pack(pady=5)
        
        # Image displays
        tk.Label(middle_frame, text="Original Image").pack()
        self.original_canvas = tk.Canvas(middle_frame, bg='gray')
        self.original_canvas.pack(fill=tk.BOTH, expand=True)
        self.original_color_label = tk.Label(middle_frame, text="Hover over image", bg='white', relief=tk.SUNKEN)
        self.original_color_label.pack(fill=tk.X, pady=2)
        
        tk.Label(right_frame, text="Modified Image").pack()
        self.modified_canvas = tk.Canvas(right_frame, bg='gray')
        self.modified_canvas.pack(fill=tk.BOTH, expand=True)
        self.modified_color_label = tk.Label(right_frame, text="Hover over image", bg='white', relief=tk.SUNKEN)
        self.modified_color_label.pack(fill=tk.X, pady=2)
        
        # Bind resize events
        self.original_canvas.bind('<Configure>', lambda e: self.on_resize())
        self.modified_canvas.bind('<Configure>', lambda e: self.on_resize())
        
        # Bind mouse motion events
        self.original_canvas.bind('<Motion>', lambda e: self.on_mouse_move(e, self.original_image, self.original_color_label, 'original'))
        self.modified_canvas.bind('<Motion>', lambda e: self.on_mouse_move(e, self.modified_image, self.modified_color_label, 'modified'))
        
        # Bind click events
        self.original_canvas.bind('<Button-1>', lambda e: self.on_canvas_click(e, self.original_image, 'original'))
        self.modified_canvas.bind('<Button-1>', lambda e: self.on_canvas_click(e, self.modified_image, 'modified'))
        
    def load_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if not filepath:
            return
            
        self.original_image = Image.open(filepath).convert('RGBA')
        self.modified_image = self.original_image.copy()
        
        # Display original image
        self.display_image(self.original_image, self.original_canvas)
        self.display_image(self.modified_image, self.modified_canvas)
        
        # Extract unique colors
        img_array = np.array(self.original_image)
        pixels = img_array.reshape(-1, 4)
        self.unique_colors = np.unique(pixels, axis=0)
        
        # Populate listboxes
        self.original_listbox.delete(0, tk.END)
        self.replacement_listbox.delete(0, tk.END)
        self.color_mappings = {}
        
        for color in self.unique_colors:
            color_tuple = tuple(color)
            self.color_mappings[color_tuple] = color_tuple
            color_hex = '#{:02x}{:02x}{:02x}'.format(*color[:3])
            self.original_listbox.insert(tk.END, f"RGBA{color_tuple} - {color_hex}")
            self.replacement_listbox.insert(tk.END, f"RGBA{color_tuple} - {color_hex}")
            
    def change_color(self, event):
        selection = self.replacement_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        original_color = tuple(self.unique_colors[index])
        
        color = colorchooser.askcolor(title="Choose replacement color")
        if color[0]:
            # Get RGB from color picker, keep original alpha
            new_color = tuple(int(c) for c in color[0]) + (original_color[3],)
            self.color_mappings[original_color] = new_color
            
            # Update listbox display
            color_hex = '#{:02x}{:02x}{:02x}'.format(*new_color[:3])
            self.replacement_listbox.delete(index)
            self.replacement_listbox.insert(index, f"RGBA{new_color} - {color_hex}")
            
    def apply_changes(self):
        if self.original_image is None:
            return
            
        img_array = np.array(self.original_image)
        modified_array = img_array.copy()
        
        for original_color, new_color in self.color_mappings.items():
            mask = np.all(img_array == original_color, axis=-1)
            modified_array[mask] = new_color
            
        self.modified_image = Image.fromarray(modified_array, 'RGBA')
        self.display_image(self.modified_image, self.modified_canvas)
    
    def on_resize(self):
        """Handle window resize events."""
        if self.original_image:
            self.display_image(self.original_image, self.original_canvas)
        if self.modified_image:
            self.display_image(self.modified_image, self.modified_canvas)
    
    def on_mouse_move(self, event, image, label, canvas_type):
        """Display the color under the mouse cursor."""
        if image is None:
            return
        
        # Get the appropriate offset and scale
        if canvas_type == 'original':
            offset_x, offset_y = self.original_img_offset
            scale = self.original_img_scale
        else:
            offset_x, offset_y = self.modified_img_offset
            scale = self.modified_img_scale
        
        # Convert canvas coordinates to image coordinates
        img_x = int((event.x - offset_x) / scale)
        img_y = int((event.y - offset_y) / scale)
        
        # Check if coordinates are within image bounds
        if 0 <= img_x < image.width and 0 <= img_y < image.height:
            # Get pixel color
            pixel = image.getpixel((img_x, img_y))
            color_hex = '#{:02x}{:02x}{:02x}'.format(*pixel[:3])
            
            # Update label with color info
            label.config(
                text=f"Pos: ({img_x}, {img_y}) | RGBA{pixel} | {color_hex}",
                bg=color_hex,
                fg='white' if sum(pixel[:3]) < 384 else 'black'
            )
        else:
            label.config(text="Outside image bounds", bg='white', fg='black')
    
    def on_canvas_click(self, event, image, canvas_type):
        """Handle clicks on canvas to open color picker for clicked pixel."""
        if image is None or self.original_image is None:
            return
        
        # Get the appropriate offset and scale
        if canvas_type == 'original':
            offset_x, offset_y = self.original_img_offset
            scale = self.original_img_scale
        else:
            offset_x, offset_y = self.modified_img_offset
            scale = self.modified_img_scale
        
        # Convert canvas coordinates to image coordinates
        img_x = int((event.x - offset_x) / scale)
        img_y = int((event.y - offset_y) / scale)
        
        # Check if coordinates are within image bounds
        if 0 <= img_x < image.width and 0 <= img_y < image.height:
            # Get pixel color from the original image (to find it in the unique colors list)
            pixel = self.original_image.getpixel((img_x, img_y))
            original_color = tuple(pixel)
            
            # If Ctrl is held, set as base color for range selection
            if event.state & 0x0004:  # Ctrl key
                self.base_color = original_color
                color_hex = '#{:02x}{:02x}{:02x}'.format(*original_color[:3])
                self.base_color_display.config(
                    text=f"RGBA{original_color}",
                    bg=color_hex,
                    fg='white' if sum(original_color[:3]) < 384 else 'black'
                )
                print(f"Base color set to RGBA{original_color}")
                return
            
            # Find the index of this color in unique_colors
            try:
                color_array = np.array(original_color)
                matches = np.where(np.all(self.unique_colors == color_array, axis=1))[0]
                if len(matches) > 0:
                    index = matches[0]
                    
                    # Select it in the listbox
                    self.replacement_listbox.selection_clear(0, tk.END)
                    self.replacement_listbox.selection_set(index)
                    self.replacement_listbox.see(index)
                    
                    # Open color picker
                    color = colorchooser.askcolor(
                        title=f"Replace RGBA{original_color}",
                        initialcolor='#{:02x}{:02x}{:02x}'.format(*original_color[:3])
                    )
                    if color[0]:
                        # Get RGB from picker, keep original alpha
                        new_color = tuple(int(c) for c in color[0]) + (original_color[3],)
                        self.color_mappings[original_color] = new_color
                        
                        # Update listbox display
                        color_hex = '#{:02x}{:02x}{:02x}'.format(*new_color[:3])
                        self.replacement_listbox.delete(index)
                        self.replacement_listbox.insert(index, f"RGBA{new_color} - {color_hex}")
                        self.replacement_listbox.selection_set(index)
            except Exception as e:
                print(f"Error finding color: {e}")
    
    def display_image(self, image, canvas):
        # Get canvas dimensions
        canvas.update_idletasks()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        # Calculate scaling to fit canvas while maintaining aspect ratio
        img_width, img_height = image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize image
        display_image = image.resize((new_width, new_height), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(display_image)
        
        # Clear canvas and center image
        canvas.delete('all')
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        canvas.create_image(x, y, anchor=tk.NW, image=photo)
        canvas.image = photo
        
        # Store offset and scale for mouse coordinate conversion
        if canvas == self.original_canvas:
            self.original_img_offset = (x, y)
            self.original_img_scale = scale
        elif canvas == self.modified_canvas:
            self.modified_img_offset = (x, y)
            self.modified_img_scale = scale
    
    def adjust_color_hsv(self, rgba_color, hue_shift, sat_shift, val_shift):
        """
        Adjust a color by adding/subtracting HSV values.
        
        Args:
            rgba_color: Tuple of (R, G, B, A) values (0-255)
            hue_shift: Hue adjustment in degrees (-180 to 180)
            sat_shift: Saturation adjustment in percent (-100 to 100)
            val_shift: Value adjustment in percent (-100 to 100)
        
        Returns:
            Tuple of adjusted (R, G, B, A) values
        """
        # Convert RGB to HSV (0-1 range)
        r, g, b = rgba_color[0] / 255.0, rgba_color[1] / 255.0, rgba_color[2] / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        
        # Adjust hue (wrap around 0-1)
        h = (h + hue_shift / 360.0) % 1.0
        
        # Adjust saturation (clamp 0-1)
        s = max(0.0, min(1.0, s + sat_shift / 100.0))
        
        # Adjust value (clamp 0-1)
        v = max(0.0, min(1.0, v + val_shift / 100.0))
        
        # Convert back to RGB and preserve alpha
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        
        return (int(r * 255), int(g * 255), int(b * 255), rgba_color[3])
    
    def apply_hsv_to_selected(self):
        """Apply HSV adjustments to selected colors in the listbox."""
        if not self.unique_colors.size:
            return
        
        try:
            hue_shift = float(self.hue_var.get())
            sat_shift = float(self.sat_var.get())
            val_shift = float(self.val_var.get())
        except ValueError:
            print("Invalid HSV values. Please enter numbers.")
            return
        
        # Get selected indices
        selected_indices = self.replacement_listbox.curselection()
        if not selected_indices:
            print("No colors selected. Select colors in the list first.")
            return
        
        # Apply adjustments to selected colors
        for index in selected_indices:
            original_color = tuple(self.unique_colors[index])
            new_color = self.adjust_color_hsv(original_color, hue_shift, sat_shift, val_shift)
            self.color_mappings[original_color] = new_color
            
            # Update listbox display
            color_hex = '#{:02x}{:02x}{:02x}'.format(*new_color[:3])
            self.replacement_listbox.delete(index)
            self.replacement_listbox.insert(index, f"RGBA{new_color} - {color_hex}")
        
        print(f"Applied HSV adjustments to {len(selected_indices)} color(s)")
    
    def apply_hsv_to_all(self):
        """Apply HSV adjustments to all colors."""
        if not self.unique_colors.size:
            return
        
        try:
            hue_shift = float(self.hue_var.get())
            sat_shift = float(self.sat_var.get())
            val_shift = float(self.val_var.get())
        except ValueError:
            print("Invalid HSV values. Please enter numbers.")
            return
        
        # Apply adjustments to all colors
        for index, color in enumerate(self.unique_colors):
            original_color = tuple(color)
            new_color = self.adjust_color_hsv(original_color, hue_shift, sat_shift, val_shift)
            self.color_mappings[original_color] = new_color
            
            # Update listbox display
            color_hex = '#{:02x}{:02x}{:02x}'.format(*new_color[:3])
            self.replacement_listbox.delete(index)
            self.replacement_listbox.insert(index, f"RGBA{new_color} - {color_hex}")
        
        print(f"Applied HSV adjustments to all {len(self.unique_colors)} colors")
    
    def pick_base_color(self):
        """Pick a base color using color picker."""
        color = colorchooser.askcolor(title="Choose Base Color")
        if color[0]:
            self.base_color = tuple(int(c) for c in color[0]) + (255,)  # Default alpha to 255
            color_hex = '#{:02x}{:02x}{:02x}'.format(*self.base_color[:3])
            self.base_color_display.config(
                text=f"RGBA{self.base_color}",
                bg=color_hex,
                fg='white' if sum(self.base_color[:3]) < 384 else 'black'
            )
            print(f"Base color set to RGBA{self.base_color}")
    
    def update_tolerance_labels(self):
        """Update tolerance labels based on selected mode."""
        mode = self.tolerance_mode.get()
        if mode == "RGB":
            self.tol1_label.config(text="R Tol:")
            self.tol2_label.config(text="G Tol:")
            self.tol3_label.config(text="B Tol:")
            self.tol1_range.config(text="(0-255)")
            self.tol2_range.config(text="(0-255)")
            self.tol3_range.config(text="(0-255)")
        else:  # HSV
            self.tol1_label.config(text="H Tol:")
            self.tol2_label.config(text="S Tol:")
            self.tol3_label.config(text="V Tol:")
            self.tol1_range.config(text="(0-180)")
            self.tol2_range.config(text="(0-100)")
            self.tol3_range.config(text="(0-100)")
    
    def select_by_range(self):
        """Select all colors within tolerance of base color (RGB or HSV mode)."""
        if self.base_color is None:
            print("No base color set. Ctrl+Click on a pixel or use Pick button.")
            return
        
        if not self.unique_colors.size:
            return
        
        try:
            tol1 = float(self.tol1_var.get())
            tol2 = float(self.tol2_var.get())
            tol3 = float(self.tol3_var.get())
        except ValueError:
            print("Invalid tolerance values. Please enter numbers.")
            return
        
        mode = self.tolerance_mode.get()
        
        # Clear current selection
        self.replacement_listbox.selection_clear(0, tk.END)
        
        # Select colors within range
        selected_count = 0
        
        if mode == "RGB":
            # RGB mode - direct channel comparison (ignore alpha)
            base_array = np.array(self.base_color[:3])
            tolerances = np.array([tol1, tol2, tol3])
            
            for index, color in enumerate(self.unique_colors):
                color_array = np.array(color[:3])
                # Check if all RGB channels are within their respective tolerances
                if np.all(np.abs(color_array - base_array) <= tolerances):
                    self.replacement_listbox.selection_set(index)
                    selected_count += 1
        
        else:  # HSV mode
            # Convert base color to HSV
            r, g, b = self.base_color[0] / 255.0, self.base_color[1] / 255.0, self.base_color[2] / 255.0
            base_h, base_s, base_v = colorsys.rgb_to_hsv(r, g, b)
            base_h_deg = base_h * 360  # Convert to degrees
            base_s_pct = base_s * 100  # Convert to percentage
            base_v_pct = base_v * 100  # Convert to percentage
            
            for index, color in enumerate(self.unique_colors):
                # Convert color to HSV
                r, g, b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                h_deg = h * 360
                s_pct = s * 100
                v_pct = v * 100
                
                # Check hue (handle circular nature - 0 and 360 are the same)
                h_diff = abs(h_deg - base_h_deg)
                if h_diff > 180:
                    h_diff = 360 - h_diff
                
                # Check if all HSV channels are within tolerance
                if (h_diff <= tol1 and 
                    abs(s_pct - base_s_pct) <= tol2 and 
                    abs(v_pct - base_v_pct) <= tol3):
                    self.replacement_listbox.selection_set(index)
                    selected_count += 1
        
        print(f"Selected {selected_count} colors in {mode} mode (Tol: {tol1}, {tol2}, {tol3})")
        
        # Scroll to first selected item
        if selected_count > 0:
            first_selected = self.replacement_listbox.curselection()[0]
            self.replacement_listbox.see(first_selected)
    
    def save_image(self):
        if self.modified_image is None:
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")])
        if filepath:
            self.modified_image.save(filepath)

if __name__ == "__main__":
    root = tk.Tk()
    app = ColorReplacerApp(root)
    # Save button
    tk.Button(app.left_frame, text="Save Modified Image", command=app.save_image).pack(pady=5)
    
    root.mainloop()