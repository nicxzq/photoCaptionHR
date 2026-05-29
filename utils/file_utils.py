from __future__ import annotations

import re
from pathlib import Path


INVALID_FILENAME = re.compile(r'[\\/:*?"<>|]')
MAX_FILENAME_STEM = 120


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def iter_images(input_dir: str | Path, extensions: set[str]) -> list[Path]:
    directory = Path(input_dir)
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower().lstrip(".") in extensions
    )


def safe_filename(filename: str) -> str:
    stem = INVALID_FILENAME.sub("_", filename)
    stem = re.sub(r"[\r\n\t]+", "", stem).strip(" ._")
    return (stem[:MAX_FILENAME_STEM].rstrip(" ._") or "unknown")


def resolve_output_path(output_dir: str | Path, filename: str) -> Path:
    directory = ensure_dir(output_dir)
    raw = Path(filename)
    stem = safe_filename(raw.stem)
    suffix = ".jpg"
    candidate = directory / f"{stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = directory / f"{stem}_{index}{suffix}"
        index += 1
    return candidate


def output_filename(
    name: str,
    title: str,
    rule: str = "name-title",
    sequence: str = "",
    level: str = "",
) -> str:
    if rule == "title-name":
        stem = f"{title}-{name}"
    elif rule == "name":
        stem = name
    elif rule == "seq-name-title":
        stem = f"{sequence}-{name}-{title}"
    elif rule == "name-title-level":
        stem = f"{name}-{title}-{level}"
    else:
        stem = f"{name}-{title}"
    return f"{stem}.jpg"
