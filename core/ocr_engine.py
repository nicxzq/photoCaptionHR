from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from shutil import copy2
from typing import Any


class OCREngineError(RuntimeError):
    pass


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def configure_frozen_paddleocr_path() -> None:
    if not getattr(sys, "frozen", False):
        return
    meipass = Path(getattr(sys, "_MEIPASS", ""))
    paddleocr_root = meipass / "paddleocr"
    if paddleocr_root.is_dir():
        root = str(paddleocr_root)
        if root not in sys.path:
            sys.path.insert(0, root)


def default_model_dir() -> Path:
    env_value = os.environ.get("PHOTOSIGN_MODEL_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", app_base_dir())) / "models"
        if bundled.exists():
            return bundled
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        return Path(local_app) / "PhotoSign" / "models"
    return app_base_dir() / "models"


def model_cache_ready(model_dir: Path) -> bool:
    required = ("det", "rec", "cls")
    return all((model_dir / name).is_dir() and any((model_dir / name).iterdir()) for name in required)


def windows_short_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name != "nt":
        return str(resolved)
    try:
        import ctypes
        from ctypes import wintypes

        buffer = ctypes.create_unicode_buffer(32768)
        result = ctypes.windll.kernel32.GetShortPathNameW(str(resolved), buffer, len(buffer))
        if result:
            return buffer.value
    except Exception:
        pass
    return str(resolved)


def ensure_windows_model_path(path: Path) -> None:
    if os.name != "nt":
        return
    resolved = str(path.resolve())
    if resolved.isascii() or windows_short_path(path) != resolved:
        return
    raise OCREngineError(
        f"Model path is not ASCII and Windows short paths are unavailable: {path}. "
        "Use an ASCII-only model cache path, for example C:\\PhotoSign\\models."
    )


class OCREngine:
    _instance: Any = None
    _model_dir: Path | None = None

    @classmethod
    def configure(cls, model_dir: str | Path | None) -> None:
        cls._model_dir = Path(model_dir).expanduser().resolve() if model_dir else default_model_dir()
        cls._instance = None

    @classmethod
    def get(cls) -> Any:
        if cls._instance is None:
            cls._instance = cls._create()
        return cls._instance

    @classmethod
    def ocr_image(cls, image_path: str | Path) -> list[dict[str, Any]]:
        path = Path(image_path)
        safe_path, temp_path = ocr_safe_image_path(path)
        try:
            raw = cls.get().ocr(safe_path, cls=True)
        except Exception as exc:
            raise OCREngineError(f"OCR failed for {image_path}: {exc}") from exc
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
        return normalize_paddle_result(raw)

    @classmethod
    def _create(cls) -> Any:
        model_dir = cls._model_dir or default_model_dir()
        model_dir.mkdir(parents=True, exist_ok=True)
        had_cache = model_cache_ready(model_dir)
        for name in ("det", "rec", "cls"):
            (model_dir / name).mkdir(parents=True, exist_ok=True)
        ensure_windows_model_path(model_dir)
        try:
            configure_frozen_paddleocr_path()
            from paddleocr import PaddleOCR

            return PaddleOCR(
                use_angle_cls=True,
                lang="ch",
                show_log=False,
                det_model_dir=windows_short_path(model_dir / "det"),
                rec_model_dir=windows_short_path(model_dir / "rec"),
                cls_model_dir=windows_short_path(model_dir / "cls"),
            )
        except TypeError:
            try:
                configure_frozen_paddleocr_path()
                from paddleocr import PaddleOCR

                return PaddleOCR(
                    use_angle_cls=True,
                    lang="ch",
                    det_model_dir=windows_short_path(model_dir / "det"),
                    rec_model_dir=windows_short_path(model_dir / "rec"),
                    cls_model_dir=windows_short_path(model_dir / "cls"),
                )
            except Exception as exc:
                raise _model_error(model_dir, had_cache, exc) from exc
        except ImportError as exc:
            raise OCREngineError(f"PaddleOCR import failed: {exc}. Run: pip install -r requirements.txt") from exc
        except Exception as exc:
            raise _model_error(model_dir, had_cache, exc) from exc


def _model_error(model_dir: Path, had_cache: bool, exc: Exception) -> OCREngineError:
    state = "existing cache may be invalid" if had_cache else "model cache is missing"
    return OCREngineError(
        f"Failed to initialize PaddleOCR: {exc}. The configured model directory is {model_dir} ({state}). "
        "Run this tool once with network access so PaddleOCR can download models into that directory, "
        "or copy a prepared det/rec/cls model cache there. You can also set --model-dir or PHOTOSIGN_MODEL_DIR. "
        "On Windows, prefer an ASCII-only model path such as C:\\PhotoSign\\models if initialization fails."
    )


def ocr_safe_image_path(path: Path) -> tuple[str, Path | None]:
    short = windows_short_path(path)
    if short and short != str(path.resolve()):
        return short, None
    if os.name != "nt" or str(path).isascii():
        return str(path), None
    suffix = path.suffix or ".jpg"
    temp_dir = Path(tempfile.gettempdir()) / "photosign_ocr"
    temp_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="ocr_input_", suffix=suffix, dir=temp_dir, delete=False) as handle:
        target = Path(handle.name)
    copy2(path, target)
    return str(target), target


def normalize_paddle_result(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    lines = raw[0] if len(raw) == 1 and isinstance(raw[0], list) else raw
    blocks: list[dict[str, Any]] = []
    for item in lines or []:
        if not item or len(item) < 2:
            continue
        points, text_score = item[0], item[1]
        if not points or not text_score:
            continue
        text = str(text_score[0]).strip()
        score = float(text_score[1]) if len(text_score) > 1 else 0.0
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        blocks.append(
            {
                "text": text,
                "bbox": (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
                "score": score,
            }
        )
    return blocks
