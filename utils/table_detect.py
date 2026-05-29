from __future__ import annotations

from pathlib import Path


def detect_table_rows(image_path: str | Path) -> list[tuple[int, int]]:
    try:
        import cv2
        import numpy as np
    except ImportError:
        return []

    img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    kernel_width = max(30, width // 3)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    ys = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w >= width * 0.45 and h <= max(10, height * 0.02):
            ys.append(y + h // 2)
    ys = merge_close_values(sorted(ys), tolerance=6)
    return [(ys[index], ys[index + 1]) for index in range(len(ys) - 1) if ys[index + 1] - ys[index] > 10]


def estimate_rows_from_ocr(blocks: list[dict]) -> list[tuple[int, int]]:
    if not blocks:
        return []
    centers = sorted((block["bbox"][1] + block["bbox"][3]) / 2 for block in blocks)
    heights = sorted(max(8, block["bbox"][3] - block["bbox"][1]) for block in blocks)
    tolerance = max(10, int(heights[len(heights) // 2] * 0.8))
    clusters: list[list[float]] = []
    for center in centers:
        if not clusters or center - clusters[-1][-1] > tolerance:
            clusters.append([center])
        else:
            clusters[-1].append(center)
    row_centers = [sum(cluster) / len(cluster) for cluster in clusters]
    if len(row_centers) < 2:
        return []
    rows = []
    for index, center in enumerate(row_centers):
        if index == 0:
            top = int(center - tolerance)
        else:
            top = int((row_centers[index - 1] + center) / 2)
        if index == len(row_centers) - 1:
            bottom = int(center + tolerance)
        else:
            bottom = int((center + row_centers[index + 1]) / 2)
        rows.append((top, bottom))
    return rows


def merge_close_values(values: list[int], tolerance: int) -> list[int]:
    merged: list[list[int]] = []
    for value in values:
        if not merged or value - merged[-1][-1] > tolerance:
            merged.append([value])
        else:
            merged[-1].append(value)
    return [int(sum(group) / len(group)) for group in merged]
