from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Optional

from core.ocr_engine import OCREngine, OCREngineError, default_model_dir
from utils.file_utils import ensure_dir, iter_images, normalize_naming_attributes, safe_filename, safe_print


ProgressCallback = Callable[[str, Optional[Path], int, int, object], None]


def run_batch(
    task: str,
    input_dir: str | Path,
    output_dir: str | Path,
    model_dir: str | Path | None = None,
    extensions: set[str] | None = None,
    name_rule: str = "name-title",
    progress: ProgressCallback | None = None,
    name_attributes: tuple[str, ...] | None = None,
    separator: str = "-",
) -> dict[str, int]:
    source_dir = Path(input_dir)
    target_dir = ensure_dir(output_dir)
    selected_attributes = (
        normalize_naming_attributes(task, name_attributes) if name_attributes is not None else None
    )
    if not source_dir.is_dir():
        raise ValueError(f"input directory does not exist: {source_dir}")

    files = list(iter_images(source_dir, extensions or {"jpg", "jpeg", "png"}))
    if not files and progress:
        progress("empty", None, 0, 0, 0)

    OCREngine.configure(Path(model_dir) if model_dir else default_model_dir())
    try:
        from core.task_cert import process_cert_image
        from core.task_excel import process_excel_image
    except ImportError as exc:
        raise ImportError(f"missing dependency: {exc}. Run: pip install -r requirements.txt") from exc

    if files:
        if progress:
            progress("initializing", None, 0, len(files), "正在加载 OCR 模型...")
        OCREngine.preload()
        if progress:
            progress("ready", None, 0, len(files), "模型加载完成")

    success = 0
    failed = 0
    outputs = 0
    for index, image_path in enumerate(files, start=1):
        try:
            if progress:
                progress("start", image_path, index, len(files), outputs)
            safe_print(f"PROCESSING: {image_path.name}")
            if task == "excel":
                count = process_excel_image(
                    image_path,
                    target_dir,
                    name_rule,
                    name_attributes=selected_attributes,
                    separator=separator,
                )
            else:
                count = process_cert_image(
                    image_path,
                    target_dir,
                    name_rule,
                    name_attributes=selected_attributes,
                    separator=separator,
                )
            success += 1
            outputs += count
            if progress:
                progress("ok", image_path, index, len(files), count)
            safe_print(f"OK: {image_path.name} -> {count} file(s)")
        except (OCREngineError, RuntimeError, ValueError) as exc:
            failed += 1
            message = failure_message(image_path, target_dir, str(exc))
            if progress:
                progress("failed", image_path, index, len(files), message)
            safe_print(f"FAILED: {image_path.name}: {message}", error=True)
        except Exception as exc:
            failed += 1
            message = failure_message(image_path, target_dir, f"unexpected error: {exc}")
            if progress:
                progress("failed", image_path, index, len(files), message)
            safe_print(f"FAILED: {image_path.name}: {message}", error=True)

    return {"input": len(files), "success": success, "failed": failed, "output": outputs}


def failure_message(source: Path, output_dir: Path, reason: str) -> str:
    try:
        failed_path = copy_failed_image(source, output_dir)
    except Exception as exc:
        return f"{reason}; failed image copy failed: {exc}"
    return f"{reason}; copied to {failed_path}"


def copy_failed_image(source: Path, output_dir: Path) -> Path:
    failed_dir = ensure_dir(output_dir / "failed")
    suffix = source.suffix or ".jpg"
    target = failed_dir / f"{safe_filename(source.stem)}{suffix}"
    index = 2
    while target.exists():
        target = failed_dir / f"{safe_filename(source.stem)}_{index}{suffix}"
        index += 1
    shutil.copy2(source, target)
    return target
