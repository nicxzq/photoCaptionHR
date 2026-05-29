from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from core.ocr_engine import OCREngine
from utils.file_utils import output_filename, resolve_output_path
from utils.image_draw import draw_checkmark
from utils.table_detect import detect_table_rows, estimate_rows_from_ocr


HEADER_WORDS = (
    "\u5e8f\u53f7",
    "\u59d3\u540d",
    "\u5907\u6ce8",
    "\u804c\u52a1",
    "\u5355\u4f4d",
)


def process_excel_image(input_path: str | Path, output_dir: str | Path, name_rule: str = "name-title") -> int:
    path = Path(input_path)
    with Image.open(path) as original:
        image = original.convert("RGB")
    blocks = OCREngine.ocr_image(path)
    title = extract_excel_title(blocks, image.height) or path.stem
    rows = detect_table_rows(path) or estimate_rows_from_ocr(blocks)
    if len(rows) < 2:
        raise ValueError("table rows were not detected")

    header_idx = find_header_row(rows, blocks)
    if header_idx is None:
        raise ValueError("table header row was not detected")

    left_margin = estimate_left_margin(blocks, rows[header_idx])
    count = 0
    for row in rows[header_idx + 1 :]:
        name = extract_name_from_row(row, blocks)
        if not name:
            print(f"WARN: skipped row {row}: name was not detected")
            continue
        sequence = ""
        if name_rule == "seq-name-title":
            sequence = extract_sequence_from_row(row, blocks)
            if not sequence:
                raise ValueError(f"sequence number was not detected for {name}")
        marked = draw_checkmark(image.copy(), row[0], row[1], left_margin)
        output_path = resolve_output_path(output_dir, output_filename(name, title, name_rule, sequence=sequence))
        marked.save(output_path, "JPEG", quality=95)
        count += 1
    return count


def extract_excel_title(blocks: list[dict], image_height: int) -> str:
    candidates = []
    for block in blocks:
        text = clean_cell(block["text"])
        if len(text) < 6 or text in HEADER_WORDS or re.fullmatch(r"[\d*]+", text):
            continue
        y1, y2 = block["bbox"][1], block["bbox"][3]
        if (y1 + y2) / 2 < image_height * 0.28:
            candidates.append(text)
    return max(candidates, key=len, default="")


def find_header_row(rows: list[tuple[int, int]], blocks: list[dict]) -> int | None:
    for index, row in enumerate(rows):
        text = "".join(block["text"] for block in blocks_in_row(blocks, row))
        if "\u59d3\u540d" in text:
            return index
    return None


def extract_name_from_row(row: tuple[int, int], blocks: list[dict]) -> str:
    row_blocks = sorted(blocks_in_row(blocks, row), key=lambda item: item["bbox"][0])
    cells = [clean_cell(block["text"]) for block in row_blocks if clean_cell(block["text"])]
    cells = [cell for cell in cells if not re.fullmatch(r"\d+", cell)]
    if not cells:
        return ""
    for cell in cells:
        if is_chinese_name(cell):
            return cell
    return cells[0] if len(cells[0]) <= 4 else ""


def extract_sequence_from_row(row: tuple[int, int], blocks: list[dict]) -> str:
    row_blocks = sorted(blocks_in_row(blocks, row), key=lambda item: item["bbox"][0])
    for block in row_blocks:
        text = clean_cell(block["text"])
        if not text:
            continue
        match = re.match(r"[A-Za-z0-9]+", text)
        return match.group(0) if match else text
    return ""


def blocks_in_row(blocks: list[dict], row: tuple[int, int]) -> list[dict]:
    y_top, y_bottom = row
    margin = max(3, int((y_bottom - y_top) * 0.15))
    return [
        block
        for block in blocks
        if y_top - margin <= ((block["bbox"][1] + block["bbox"][3]) / 2) <= y_bottom + margin
    ]


def estimate_left_margin(blocks: list[dict], header_row: tuple[int, int]) -> int:
    row_blocks = blocks_in_row(blocks, header_row) or blocks
    left = min((block["bbox"][0] for block in row_blocks), default=60)
    return max(20, left - 10)


def clean_cell(text: str) -> str:
    return re.sub(r"\s+", "", text or "").strip()


def is_chinese_name(text: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fff]{2,4}", text))
