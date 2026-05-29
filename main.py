from __future__ import annotations

import argparse
import sys

from core.runner import run_batch


def parse_exts(raw: str) -> set[str]:
    return {item.strip().lower().lstrip(".") for item in raw.split(",") if item.strip()}


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
        )
    except (ImportError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"Done. input={result['input']}, success={result['success']}, "
        f"failed={result['failed']}, output={result['output']}"
    )
    return 1 if result["failed"] and not result["success"] else 0


def main() -> int:
    if len(sys.argv) == 1:
        from gui import main as gui_main

        gui_main()
        return 0
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
