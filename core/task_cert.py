from __future__ import annotations

import re
import shutil
from pathlib import Path

from PIL import Image

from core.ocr_engine import OCREngine
from utils.file_utils import output_filename, resolve_output_path


NAME_RE = re.compile(r"\u59d3\s*\u540d\s*[\uff1a:]?\s*(?P<name>[\u4e00-\u9fff]{2,4})?")
NAME_LABEL = "\u59d3\u540d"
SURNAME_LABEL = "\u59d3"
GIVEN_LABEL = "\u540d"


def process_cert_image(input_path: str | Path, output_dir: str | Path, name_rule: str = "name-title") -> int:
    path = Path(input_path)
    with Image.open(path) as image:
        height = image.height
    blocks = OCREngine.ocr_image(path)
    title = extract_cert_title(blocks, height) or path.stem
    name = extract_cert_name(blocks)
    if not name:
        raise ValueError("name was not detected")
    level = ""
    if name_rule == "name-title-level":
        level = extract_cert_level(blocks)
        if not level:
            raise ValueError("certificate level was not detected")
    output_path = resolve_output_path(output_dir, output_filename(name, title, name_rule, level=level))
    save_as_jpg(path, output_path)
    return 1


def extract_cert_title(blocks: list[dict], image_height: int) -> str:
    candidates = []
    for block in blocks:
        text = clean_text(block["text"])
        if not text or text.isascii():
            continue
        y1, y2 = block["bbox"][1], block["bbox"][3]
        if (y1 + y2) / 2 <= image_height * 0.35 and len(text) >= 4:
            candidates.append(text)
    return max(candidates, key=len, default="")


def extract_cert_name(blocks: list[dict]) -> str:
    ordered = sorted(blocks, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    for block in ordered:
        text = clean_text(block["text"])
        match = NAME_RE.search(text)
        if not match:
            continue
        inline = match.group("name")
        if inline:
            return inline
        name = first_name_text(_right_blocks(block, ordered))
        if name:
            return name

    split_label = find_split_name_label(ordered)
    if split_label:
        name = first_name_text(_right_blocks(split_label, ordered))
        if name:
            return name

    for index, block in enumerate(ordered):
        if NAME_LABEL in clean_text(block["text"]):
            for next_block in ordered[index + 1 : index + 4]:
                name = clean_name(next_block["text"])
                if name:
                    return name
    return ""


def extract_cert_level(blocks: list[dict]) -> str:
    lines = group_text_lines(blocks)
    return lines[4] if len(lines) >= 5 else ""


def group_text_lines(blocks: list[dict]) -> list[str]:
    if not blocks:
        return []
    ordered = sorted(blocks, key=lambda item: ((item["bbox"][1] + item["bbox"][3]) / 2, item["bbox"][0]))
    heights = sorted(max(8, item["bbox"][3] - item["bbox"][1]) for item in ordered)
    tolerance = max(10, int(heights[len(heights) // 2] * 0.8))
    rows: list[list[dict]] = []
    centers: list[float] = []
    for block in ordered:
        center = (block["bbox"][1] + block["bbox"][3]) / 2
        if rows and abs(center - centers[-1]) <= tolerance:
            rows[-1].append(block)
            centers[-1] = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in rows[-1]) / len(rows[-1])
        else:
            rows.append([block])
            centers.append(center)
    return [
        clean_text("".join(item["text"] for item in sorted(row, key=lambda item: item["bbox"][0])))
        for row in rows
    ]


def _right_blocks(label: dict, blocks: list[dict]) -> list[dict]:
    _x1, y1, x2, y2 = label["bbox"]
    line_height = max(12, y2 - y1)
    center_y = (y1 + y2) / 2
    return [
        block
        for block in blocks
        if block is not label
        and block["bbox"][0] >= x2
        and abs(((block["bbox"][1] + block["bbox"][3]) / 2) - center_y) <= line_height * 1.5
    ]


def find_split_name_label(blocks: list[dict]) -> dict | None:
    for block in blocks:
        if clean_text(block["text"]) != SURNAME_LABEL:
            continue
        for candidate in blocks:
            if candidate["bbox"][0] <= block["bbox"][0]:
                continue
            if GIVEN_LABEL in clean_text(candidate["text"]) and _same_line(block, candidate):
                return candidate
    return None


def _same_line(left: dict, right: dict) -> bool:
    y1, y2 = left["bbox"][1], left["bbox"][3]
    line_height = max(12, y2 - y1)
    return abs(((right["bbox"][1] + right["bbox"][3]) / 2) - ((y1 + y2) / 2)) <= line_height * 1.5


def first_name_text(blocks: list[dict]) -> str:
    labels = {GIVEN_LABEL, f"{GIVEN_LABEL}:", f"{GIVEN_LABEL}\uff1a", NAME_LABEL, f"{NAME_LABEL}:", f"{NAME_LABEL}\uff1a"}
    for block in blocks:
        text = clean_text(block["text"])
        if text in labels:
            continue
        name = clean_name(text)
        if name:
            return name
    return ""


def clean_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def clean_name(text: str) -> str:
    match = re.search(r"[\u4e00-\u9fff]{2,4}", clean_text(text))
    return match.group(0) if match else ""


def save_as_jpg(source: Path, target: Path) -> None:
    if source.suffix.lower() in {".jpg", ".jpeg"}:
        shutil.copy2(source, target)
        return
    with Image.open(source) as image:
        image.convert("RGB").save(target, "JPEG", quality=95)
