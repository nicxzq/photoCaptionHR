from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable


INVALID_FILENAME = re.compile(r'[\\/:*?"<>|]')
MAX_FILENAME_STEM = 120
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
NAMING_ATTRIBUTES = {
    "excel": ("sequence", "name", "title"),
    "cert": ("name", "title", "level"),
}


def safe_print(message: str, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    if stream is not None:
        print(message, file=stream)


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
    stem = stem[:MAX_FILENAME_STEM].rstrip(" ._") or "unknown"
    return f"_{stem}" if stem.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES else stem


def resolve_output_path(output_dir: str | Path, filename: str) -> Path:
    directory = ensure_dir(output_dir)
    raw_stem = filename[:-4] if filename.lower().endswith(".jpg") else filename
    stem = safe_filename(raw_stem)
    suffix = ".jpg"
    candidate = directory / f"{stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = directory / f"{stem}_{index}{suffix}"
        index += 1
    return candidate


def normalize_naming_attributes(task: str, attributes: Iterable[str]) -> tuple[str, ...]:
    allowed = NAMING_ATTRIBUTES.get(task)
    if not allowed:
        raise ValueError(f"unsupported task: {task}")
    requested = {attribute.strip().lower() for attribute in attributes if attribute.strip()}
    invalid = requested.difference(allowed)
    if invalid:
        raise ValueError(f"unsupported {task} naming attributes: {', '.join(sorted(invalid))}")
    selected = tuple(attribute for attribute in allowed if attribute in requested)
    if not selected:
        raise ValueError("at least one naming attribute must be selected")
    return selected


def output_filename(
    name: str,
    title: str,
    rule: str = "name-title",
    *,
    task: str | None = None,
    attributes: tuple[str, ...] | None = None,
    separator: str = "-",
    sequence: str = "",
    level: str = "",
) -> str:
    if attributes is not None:
        selected = normalize_naming_attributes(task or "", attributes)
        values = {"name": name, "title": title, "sequence": sequence, "level": level}
        stem = separator.join(values[attribute] for attribute in selected if values[attribute])
        return f"{stem}.jpg"
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
