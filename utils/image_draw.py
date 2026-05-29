from __future__ import annotations

from PIL import Image, ImageDraw


def draw_checkmark(img: Image.Image, y_top: int, y_bottom: int, left_margin: int) -> Image.Image:
    if left_margin < 40:
        img = expand_left_canvas(img, 60)
        left_margin += 60
    draw = ImageDraw.Draw(img)
    row_height = max(10, y_bottom - y_top)
    cx = max(12, left_margin // 2)
    cy = int((y_top + y_bottom) / 2)
    radius = max(6, int(min(row_height * 0.4, left_margin * 0.4)))

    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill="#E53935")
    points = [
        (cx - int(radius * 0.45), cy + int(radius * 0.05)),
        (cx - int(radius * 0.12), cy + int(radius * 0.35)),
        (cx + int(radius * 0.45), cy - int(radius * 0.28)),
    ]
    draw.line(points, fill="white", width=max(2, int(radius * 0.18)), joint="curve")
    return img


def expand_left_canvas(img: Image.Image, width: int) -> Image.Image:
    expanded = Image.new("RGB", (img.width + width, img.height), "white")
    expanded.paste(img, (width, 0))
    return expanded
