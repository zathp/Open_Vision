"""Blender texture-map export utilities (Qt-free).

Implements the Base Color (Albedo) export path with a configurable
filename template and conflict policy, usable from both single-image
and batch export flows.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from PIL import Image

CONFLICT_OVERWRITE = "overwrite"
CONFLICT_NUMERIC_SUFFIX = "numeric_suffix"
CONFLICT_PROMPT = "prompt"
CONFLICT_POLICIES = (CONFLICT_OVERWRITE, CONFLICT_NUMERIC_SUFFIX, CONFLICT_PROMPT)

DEFAULT_NAME_TEMPLATE = "{project_name}_BaseColor"

PromptCallback = Callable[[Path], Optional[Path]]


class ExportConflictError(RuntimeError):
    """Raised when a prompt-policy export is declined by the callback."""


def _validate_policy(policy: str) -> None:
    if policy not in CONFLICT_POLICIES:
        raise ValueError(f"Unknown conflict policy: {policy}. Must be one of {CONFLICT_POLICIES}")


def resolve_output_path(
    directory: Path,
    filename: str,
    policy: str,
    prompt_callback: Optional[PromptCallback] = None,
    suffix_start: int = 1,
    suffix_pad: int = 3,
) -> Path:
    """
    Resolve the final write path for an export under the given conflict policy.

    Args:
        directory: Target directory.
        filename: Desired file name inside the directory.
        policy: One of CONFLICT_OVERWRITE, CONFLICT_NUMERIC_SUFFIX,
            CONFLICT_PROMPT.
        prompt_callback: Required for the prompt policy; receives the
            candidate path and returns the accepted path or None to cancel.
        suffix_start: First numeric suffix value for the suffix policy.
        suffix_pad: Zero-padding width of numeric suffixes.

    Returns:
        The resolved output path.

    Raises:
        ValueError: If policy unknown, or prompt policy lacks a callback.
        ExportConflictError: If the prompt callback declines (returns None).
    """
    _validate_policy(policy)
    candidate = Path(directory) / filename

    if policy == CONFLICT_OVERWRITE or not candidate.exists():
        return candidate

    if policy == CONFLICT_NUMERIC_SUFFIX:
        counter = suffix_start
        while True:
            suffixed = candidate.with_name(
                f"{candidate.stem}_{str(counter).zfill(suffix_pad)}{candidate.suffix}"
            )
            if not suffixed.exists():
                return suffixed
            counter += 1

    if prompt_callback is None:
        raise ValueError("prompt policy requires prompt_callback")
    decision = prompt_callback(candidate)
    if decision is None:
        raise ExportConflictError(f"Export cancelled for existing file: {candidate}")
    return Path(decision)


def render_filename(template: str, context: Dict[str, Any], extension: str) -> str:
    """
    Render an export filename from a format template.

    Args:
        template: str.format-style template, e.g. "{project_name}_BaseColor".
        context: Substitution values (project_name, image_name, index...).
        extension: File extension with or without leading dot.

    Returns:
        Rendered lowercase-extension filename string.

    Raises:
        KeyError: If the template references a missing context key.
    """
    rendered = template.format_map(context)
    normalized_ext = extension.lower()
    if not normalized_ext.startswith("."):
        normalized_ext = f".{normalized_ext}"
    return f"{rendered}{normalized_ext}"


def _normalize_pil_format(save_format: str) -> str:
    fmt = save_format.upper()
    return "JPEG" if fmt == "JPG" else fmt


def _flatten_for_format(image: Image.Image, save_format: str) -> Image.Image:
    fmt = _normalize_pil_format(save_format)
    if fmt == "JPEG" and image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.copy()


def export_albedo(
    image: Image.Image,
    output_directory: Path,
    template: str = DEFAULT_NAME_TEMPLATE,
    context: Optional[Dict[str, Any]] = None,
    conflict_policy: str = CONFLICT_OVERWRITE,
    prompt_callback: Optional[PromptCallback] = None,
    save_format: str = "PNG",
    quality: Optional[int] = None,
) -> Path:
    """
    Export an image as a Base Color map under the configured policy.

    Args:
        image: Source PIL image (never mutated; JPG gets a white background
            behind transparency).
        output_directory: Created (with parents) if missing.
        template: Filename template; see render_filename.
        context: Template substitution values.
        conflict_policy: See resolve_output_path.
        prompt_callback: Callback for the prompt policy.
        save_format: PIL-friendly format string (PNG default; JPG/BMP also
            sensible for albedo).
        quality: Passed to PIL only for quality-aware formats (JPG/WEBP).

    Returns:
        The path actually written.

    Raises:
        ValueError: Unknown policy / missing replacement requirements.
        ExportConflictError: Prompt declined.
        OSError/PIL exceptions: On save failure.
    """
    _validate_policy(conflict_policy)
    values = dict(context or {})
    filename = render_filename(template, values, save_format)
    target = resolve_output_path(output_directory, filename, conflict_policy, prompt_callback)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    to_save = _flatten_for_format(image, save_format)
    save_kwargs: Dict[str, Any] = {}
    normalized_format = _normalize_pil_format(save_format)
    if quality is not None and normalized_format in ("JPEG", "WEBP"):
        save_kwargs["quality"] = int(quality)
    to_save.save(target, format=normalized_format, **save_kwargs)
    return target


def batch_export_albedo(
    images: Mapping[str, Image.Image],
    output_directory: Path,
    template: str = "{project_name}_{image_name}_BaseColor",
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Tuple[Dict[str, Path], List[str]]:
    """
    Export multiple images with one consistent conflict policy.

    Args:
        images: Mapping of logical name -> PIL image (exported in sorted
            key order; each name is exposed to the template as image_name).
        output_directory: Target directory.
        template: Filename template including {image_name}.
        context: Shared template values (e.g. project_name).
        **kwargs: Forwarded to export_albedo (conflict_policy, save_format...).

    Returns:
        Tuple of (written mapping name->path, error message list). A failing
        export does not abort remaining exports.
    """
    written: Dict[str, Path] = {}
    errors: List[str] = []
    shared = dict(context or {})

    for name in sorted(images.keys()):
        values = dict(shared)
        values["image_name"] = name
        try:
            written[name] = export_albedo(
                images[name],
                output_directory,
                template=template,
                context=values,
                **kwargs,
            )
        except Exception as error:
            errors.append(f"{name}: {error}")

    return written, errors
