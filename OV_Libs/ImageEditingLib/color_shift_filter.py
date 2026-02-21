from dataclasses import dataclass
from colorsys import rgb_to_hsv, hsv_to_rgb
from typing import Any, Iterable, List, Literal, Optional, Sequence, Tuple

from OV_Libs.pillow_compat import Image

RgbaColor = Tuple[int, int, int, int]
DistanceType = Literal["euclidean", "manhattan", "chebyshev"]
SelectionType = Literal["hsv_range", "rgb_range", "rgb_distance"]
ShiftType = Literal["percentile_rgb", "percentile_hsv", "absolute_rgb", "absolute_hsv", "match_distance_rgb"]


@dataclass(frozen=True)
class ColorShiftFilterOptions:
    selection_type: SelectionType
    shift_type: ShiftType
    tolerance: float | Tuple[float, float, float] = 30.0
    distance_type: DistanceType = "euclidean"
    output_base_color: Optional[RgbaColor] = None


class ColorShiftFilter:
    def __init__(self) -> None:
        pass

    def select_indices(
        self,
        colors: Sequence[RgbaColor],
        base_color: RgbaColor,
        options: ColorShiftFilterOptions,
    ) -> List[int]:
        if options.selection_type == "hsv_range":
            selected = self.select_by_hsv_range(colors, base_color, options.tolerance)
        elif options.selection_type == "rgb_range":
            selected = self.select_by_rgb_range(colors, base_color, int(self._scalar_tolerance(options.tolerance)))
        elif options.selection_type == "rgb_distance":
            selected = self.select_by_rgb_distance(
                colors,
                base_color,
                self._scalar_tolerance(options.tolerance),
                options.distance_type,
            )
        else:
            raise ValueError(f"Unsupported selection type: {options.selection_type}")

        selected_set = set(selected)
        return [index for index, color in enumerate(colors) if color in selected_set]

    def apply_shift(
        self,
        color: RgbaColor,
        options: ColorShiftFilterOptions,
        shift_value: float | Sequence[float],
    ) -> RgbaColor:
        if options.shift_type == "percentile_rgb":
            shift_tuple = self._triplet_shift_value(shift_value, scalar_default="rgb")
            return self.apply_percentile_shift_rgb(color, shift_tuple)

        if options.shift_type == "percentile_hsv":
            shift_tuple = self._triplet_shift_value(shift_value, scalar_default="hsv")
            return self.apply_percentile_shift_hsv(color, shift_tuple)

        if options.shift_type == "absolute_rgb":
            shift_tuple = self._triplet_shift_value(shift_value, scalar_default="rgb")
            return self.apply_absolute_shift_rgb(color, shift_tuple)

        if options.shift_type == "absolute_hsv":
            shift_tuple = self._triplet_shift_value(shift_value, scalar_default="hsv")
            return self.apply_absolute_shift_hsv(color, shift_tuple)

        if options.shift_type == "match_distance_rgb":
            if options.output_base_color is None:
                return color
            return color

        raise ValueError(f"Unsupported shift type: {options.shift_type}")

    def _triplet_shift_value(
        self,
        shift_value: float | Sequence[float],
        scalar_default: Literal["rgb", "hsv"] = "rgb",
    ) -> Tuple[float, float, float]:
        if isinstance(shift_value, Sequence) and not isinstance(shift_value, (str, bytes)):
            values = [float(value) for value in shift_value]
            if not values:
                return 0.0, 0.0, 0.0
            if len(values) == 1:
                value = values[0]
                return value, value, value
            if len(values) == 2:
                return values[0], values[1], values[1]
            return values[0], values[1], values[2]

        value = float(shift_value)
        if scalar_default == "hsv":
            return 0.0, value, value
        return value, value, value

    def shift_selected_colors(
        self,
        colors: Sequence[RgbaColor],
        selected_indices: Iterable[int],
        options: ColorShiftFilterOptions,
        shift_value: float | Tuple[float, float, float],
    ) -> List[RgbaColor]:
        output = list(colors)
        for index in selected_indices:
            if 0 <= index < len(output):
                output[index] = self.apply_shift(output[index], options, shift_value)
        return output

    def apply_color_shift_to_image(
        self,
        image: Any,
        base_color: RgbaColor,
        options: ColorShiftFilterOptions,
        shift_value: float | Tuple[float, float, float],
    ) -> Tuple[Any, Any]:
        """
        Apply color shift to an image and generate a change mask.
        
        Args:
            image: PIL Image to process
            base_color: Base color for selection
            options: Filter options for selection and shift type
            shift_value: The shift amount to apply
            
        Returns:
            Tuple of (modified_image, change_mask):
            - modified_image: PIL Image with colors shifted
            - change_mask: PIL Image (RGBA) where white pixels indicate changes
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        modified = image.copy()
        source_pixels = image.load()
        modified_pixels = modified.load()
        
        width, height = image.size
        mask = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        mask_pixels = mask.load()
        
        # Process each pixel
        for y in range(height):
            for x in range(width):
                original_pixel = source_pixels[x, y]
                
                # Check if this pixel's color is in the selection
                if self._is_color_selected(
                    original_pixel, base_color, options
                ):
                    # Apply the shift
                    if options.shift_type == "match_distance_rgb":
                        output_base = options.output_base_color if options.output_base_color is not None else base_color
                        shifted_pixel = self.apply_match_distance_rgb(
                            original_pixel,
                            base_color,
                            output_base,
                        )
                    else:
                        shifted_pixel = self.apply_shift(
                            original_pixel, options, shift_value
                        )
                    modified_pixels[x, y] = shifted_pixel
                    # Mark as changed (white in mask)
                    mask_pixels[x, y] = (255, 255, 255, 255)
        
        return modified, mask

    def apply_color_shift_to_image_with_palette(
        self,
        image: Any,
        palette: Sequence[RgbaColor],
        mapping: Sequence[RgbaColor],
    ) -> Tuple[Any, Any]:
        """
        Apply color shift using a palette mapping and generate a change mask.
        
        Args:
            image: PIL Image to process
            palette: Sequence of colors from the image
            mapping: Mapped colors (same length as palette)
            
        Returns:
            Tuple of (modified_image, change_mask):
            - modified_image: PIL Image with colors replaced
            - change_mask: PIL Image (RGBA) where white pixels show changes
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        if len(palette) != len(mapping):
            raise ValueError(
                f"Palette and mapping must have same length: "
                f"{len(palette)} vs {len(mapping)}"
            )
        
        # Build color lookup dictionary
        color_map = dict(zip(palette, mapping))
        
        modified = image.copy()
        source_pixels = image.load()
        modified_pixels = modified.load()
        
        width, height = image.size
        mask = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        mask_pixels = mask.load()
        
        # Process each pixel
        for y in range(height):
            for x in range(width):
                original_color = source_pixels[x, y]
                
                if original_color in color_map:
                    new_color = color_map[original_color]
                    modified_pixels[x, y] = new_color
                    # Mark as changed (white in mask)
                    mask_pixels[x, y] = (255, 255, 255, 255)
        
        return modified, mask

    def generate_change_mask(
        self,
        original_image: Any,
        modified_image: Any,
        alpha_channel: bool = True,
    ) -> Any:
        """
        Generate a mask showing differences between two images.
        
        Args:
            original_image: Original PIL Image
            modified_image: Modified PIL Image
            alpha_channel: If True, return RGBA mask; else return L (grayscale)
            
        Returns:
            PIL Image mask where pixels are white where images differ
        """
        if original_image.size != modified_image.size:
            raise ValueError("Images must have the same size")
        
        mask_pixels = []
        width, height = original_image.size
        
        # Ensure both images are RGBA for comparison
        orig = original_image.convert("RGBA") if original_image.mode != "RGBA" else original_image
        modified = modified_image.convert("RGBA") if modified_image.mode != "RGBA" else modified_image
        
        orig_data = orig.load()
        mod_data = modified.load()
        
        for y in range(height):
            for x in range(width):
                if orig_data[x, y] != mod_data[x, y]:
                    # Pixels differ - white in mask
                    mask_pixels.append((255, 255, 255, 255) if alpha_channel else 255)
                else:
                    # Pixels same - black in mask
                    mask_pixels.append((0, 0, 0, 255) if alpha_channel else 0)
        
        if alpha_channel:
            mask = Image.new("RGBA", (width, height))
        else:
            mask = Image.new("L", (width, height))
        
        mask.putdata(mask_pixels)
        return mask

    def _is_color_selected(
        self,
        color: RgbaColor,
        base_color: RgbaColor,
        options: ColorShiftFilterOptions,
    ) -> bool:
        """
        Check if a color should be selected based on options.
        
        Args:
            color: Color to check
            base_color: Base color for comparison
            options: Selection options
            
        Returns:
            True if color matches selection criteria
        """
        if options.selection_type == "hsv_range":
            selected = self.select_by_hsv_range([color], base_color, options.tolerance)
        elif options.selection_type == "rgb_range":
            selected = self.select_by_rgb_range(
                [color], base_color, int(self._scalar_tolerance(options.tolerance))
            )
        elif options.selection_type == "rgb_distance":
            selected = self.select_by_rgb_distance(
                [color], base_color, self._scalar_tolerance(options.tolerance), options.distance_type
            )
        else:
            return False
        
        return len(selected) > 0

    def select_by_hsv_range(
        self,
        colors: Sequence[RgbaColor],
        base_color: RgbaColor,
        tolerance: float | Sequence[float],
    ) -> List[RgbaColor]:
        base_h, base_s, base_v = self._rgb_to_hsv_255(base_color)
        hue_raw, sat_raw, val_raw = self._triplet_tolerance(tolerance)

        hue_tolerance = max(0.0, min(180.0, hue_raw)) / 360.0
        sat_tolerance = max(0.0, min(255.0, sat_raw)) / 255.0
        val_tolerance = max(0.0, min(255.0, val_raw)) / 255.0

        selected: List[RgbaColor] = []
        for color in colors:
            hue, sat, value = self._rgb_to_hsv_255(color)
            hue_distance = min(abs(hue - base_h), 1.0 - abs(hue - base_h))
            if (
                hue_distance <= hue_tolerance
                and abs(sat - base_s) <= sat_tolerance
                and abs(value - base_v) <= val_tolerance
            ):
                selected.append(color)
        return selected

    def _triplet_tolerance(self, tolerance: float | Sequence[float]) -> Tuple[float, float, float]:
        if isinstance(tolerance, Sequence) and not isinstance(tolerance, (str, bytes)):
            raw_values = [float(value) for value in tolerance]
            if not raw_values:
                return 0.0, 0.0, 0.0
            if len(raw_values) == 1:
                value = raw_values[0]
                return value, value, value
            if len(raw_values) == 2:
                return raw_values[0], raw_values[1], raw_values[1]
            return raw_values[0], raw_values[1], raw_values[2]

        value = float(tolerance)
        return value, value, value

    def _scalar_tolerance(self, tolerance: float | Sequence[float]) -> float:
        triplet = self._triplet_tolerance(tolerance)
        return max(triplet)

    def select_by_rgb_range(
        self,
        colors: Sequence[RgbaColor],
        base_color: RgbaColor,
        tolerance: int,
    ) -> List[RgbaColor]:
        r0, g0, b0, _ = base_color
        t = max(0, tolerance)

        selected: List[RgbaColor] = []
        for color in colors:
            r, g, b, _ = color
            if abs(r - r0) <= t and abs(g - g0) <= t and abs(b - b0) <= t:
                selected.append(color)
        return selected

    def select_by_rgb_distance(
        self,
        colors: Sequence[RgbaColor],
        base_color: RgbaColor,
        tolerance: float,
        distance_type: DistanceType = "euclidean",
    ) -> List[RgbaColor]:
        selected: List[RgbaColor] = []
        for color in colors:
            distance = self._rgb_distance(base_color, color, distance_type)
            if distance <= tolerance:
                selected.append(color)
        return selected

    def apply_percentile_shift_rgb(
        self,
        color: RgbaColor,
        shift_percent: Tuple[float, float, float],
    ) -> RgbaColor:
        r, g, b, a = color
        pr, pg, pb = shift_percent

        return (
            self._percentile_shift_channel(r, pr),
            self._percentile_shift_channel(g, pg),
            self._percentile_shift_channel(b, pb),
            a,
        )

    def apply_percentile_shift_hsv(
        self,
        color: RgbaColor,
        shift_percent: Tuple[float, float, float],
    ) -> RgbaColor:
        hue_p, sat_p, val_p = shift_percent
        r, g, b, a = color
        h, s, v = self._rgb_to_hsv_255(color)

        h = (h + (hue_p / 100.0)) % 1.0
        s = self._percentile_shift_unit(s, sat_p)
        v = self._percentile_shift_unit(v, val_p)

        rr, gg, bb = hsv_to_rgb(h, s, v)
        return (int(round(rr * 255)), int(round(gg * 255)), int(round(bb * 255)), a)

    def apply_absolute_shift_rgb(
        self,
        color: RgbaColor,
        shift: Tuple[float, float, float],
    ) -> RgbaColor:
        r, g, b, a = color
        dr, dg, db = shift
        return (
            self._clamp_byte(r + dr),
            self._clamp_byte(g + dg),
            self._clamp_byte(b + db),
            a,
        )

    def apply_absolute_shift_hsv(
        self,
        color: RgbaColor,
        shift: Tuple[float, float, float],
    ) -> RgbaColor:
        hue_delta_deg, sat_delta, val_delta = shift
        r, g, b, a = color
        h, s, v = self._rgb_to_hsv_255(color)

        h = (h + (hue_delta_deg / 360.0)) % 1.0
        s = max(0.0, min(1.0, s + (sat_delta / 255.0)))
        v = max(0.0, min(1.0, v + (val_delta / 255.0)))

        rr, gg, bb = hsv_to_rgb(h, s, v)
        return (int(round(rr * 255)), int(round(gg * 255)), int(round(bb * 255)), a)

    def apply_match_distance_rgb(
        self,
        color: RgbaColor,
        source_base_color: RgbaColor,
        output_base_color: RgbaColor,
    ) -> RgbaColor:
        sr, sg, sb, sa = source_base_color
        tr, tg, tb, ta = output_base_color
        r, g, b, a = color

        return (
            self._clamp_byte(tr + (r - sr)),
            self._clamp_byte(tg + (g - sg)),
            self._clamp_byte(tb + (b - sb)),
            self._clamp_byte(ta + (a - sa)),
        )

    def _rgb_distance(self, a: RgbaColor, b: RgbaColor, distance_type: DistanceType) -> float:
        ar, ag, ab, _ = a
        br, bg, bb, _ = b
        dr = abs(ar - br)
        dg = abs(ag - bg)
        db = abs(ab - bb)

        if distance_type == "euclidean":
            return (dr * dr + dg * dg + db * db) ** 0.5
        if distance_type == "manhattan":
            return float(dr + dg + db)
        if distance_type == "chebyshev":
            return float(max(dr, dg, db))

        raise ValueError(f"Unsupported distance type: {distance_type}")

    def _rgb_to_hsv_255(self, color: RgbaColor) -> Tuple[float, float, float]:
        r, g, b, _ = color
        return rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

    def _percentile_shift_channel(self, value: int, shift_percent: float) -> int:
        normalized = max(-100.0, min(100.0, shift_percent)) / 100.0
        if normalized >= 0:
            shifted = value + (255 - value) * normalized
        else:
            shifted = value * (1.0 + normalized)
        return self._clamp_byte(shifted)

    def _percentile_shift_unit(self, value: float, shift_percent: float) -> float:
        normalized = max(-100.0, min(100.0, shift_percent)) / 100.0
        if normalized >= 0:
            shifted = value + (1.0 - value) * normalized
        else:
            shifted = value * (1.0 + normalized)
        return max(0.0, min(1.0, shifted))

    def _clamp_byte(self, value: float) -> int:
        return int(max(0, min(255, round(value))))