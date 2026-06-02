from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.ocr_engine import OCREngineError
from core.runner import run_batch
from utils.file_utils import safe_print
from utils.splash import close_splash


def parse_exts(raw: str) -> set[str]:
    return {item.strip().lower().lstrip(".") for item in raw.split(",") if item.strip()}


def parse_name_attributes(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PhotoSign batch OCR tool")
    parser.add_argument("--task", required=True, choices=("excel", "cert"))
    parser.add_argument("--input", required=True, help="Input image directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--ext", default="jpg,jpeg,png", help="Comma-separated image extensions")
    parser.add_argument(
        "--name-rule",
        default="name-title",
        choices=("name-title", "title-name", "name", "seq-name-title", "name-title-level"),
    )
    parser.add_argument(
        "--model-dir",
        default=None,
        help="External PaddleOCR model cache directory. Defaults to PHOTOSIGN_MODEL_DIR or %%LOCALAPPDATA%%\\PhotoSign\\models.",
    )
    parser.add_argument(
        "--name-attributes",
        type=parse_name_attributes,
        default=None,
        help="Comma-separated attributes. Excel: name,title,sequence. Cert: name,title,level.",
    )
    parser.add_argument("--separator", default="-", help="Filename separator. Empty text is allowed.")
    return parser


def run(args: argparse.Namespace) -> int:
    try:
        result = run_batch(
            args.task,
            args.input,
            args.output,
            args.model_dir,
            parse_exts(args.ext),
            args.name_rule,
            name_attributes=args.name_attributes,
            separator=args.separator,
        )
    except (ImportError, OCREngineError, ValueError) as exc:
        safe_print(f"ERROR: {exc}", error=True)
        return 2
    safe_print(
        f"Done. input={result['input']}, success={result['success']}, "
        f"failed={result['failed']}, output={result['output']}"
    )
    return 1 if result["failed"] and not result["success"] else 0


def main() -> int:
    if len(sys.argv) == 1:
        if getattr(sys, "frozen", False) and Path(sys.executable).stem.lower() == "photosign-cli":
            return run(build_parser().parse_args())
        from gui import main as gui_main

        gui_main()
        return 0
    close_splash()
    if getattr(sys, "frozen", False) and sys.stdout is None:
        return 2
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
