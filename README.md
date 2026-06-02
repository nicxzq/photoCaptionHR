# photoCaptionHR

photoCaptionHR is a Windows desktop and command-line OCR utility for batch photo processing. It can mark table-list images and rename certificate images using PaddleOCR results.

The project was extracted from the private PhotoSign codebase for open source release. Private sample images, generated output, virtual environments, executable build output, and local model caches are intentionally excluded.

## Requirements

- Windows 10 or later
- Python 3.9-3.11
- Network access for first-time PaddleOCR model download, unless you provide a prepared model cache

PaddlePaddle may not provide wheels for every new Python version, so Python 3.9-3.11 is recommended.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For editable development installs:

```powershell
python -m pip install -e .
```

## GUI

Run the GUI with:

```powershell
python main.py
```

Or build the executable and run `release\photosign.exe`. Select the task, naming attributes, separator, input folder, output folder, and model cache folder, then click Start.

## Commands

```powershell
python main.py --task excel --input .\input\excelFile --output .\output\excelFile --model-dir C:\PhotoSign\models
python main.py --task cert --input .\input\zhengjian --output .\output\zhengjian --model-dir C:\PhotoSign\models
```

The packaged command-line entry point is `release\photosign-cli.exe`.

Optional naming rules:

```powershell
python main.py --task excel --input .\input\excelFile --output .\output\excelFile --name-rule name-title
python main.py --task excel --input .\input\excelFile --output .\output\excelFile --name-rule title-name
python main.py --task excel --input .\input\excelFile --output .\output\excelFile --name-rule name
```

`--model-dir` is optional. Resolution order:

1. `--model-dir`
2. `PHOTOSIGN_MODEL_DIR`
3. `%LOCALAPPDATA%\PhotoSign\models`
4. `models` beside `main.py` when `%LOCALAPPDATA%` is unavailable

For the packaged executable, the prepared `det`, `rec`, and `cls` model folders are bundled inside `photosign.exe` and extracted to PyInstaller's runtime directory automatically. Development runs still use an external cache. If the external cache is missing, PaddleOCR tries to download models into that directory.

On Windows, prefer an ASCII-only model path, for example `C:\PhotoSign\models`. Some PaddlePaddle builds cannot open model files from paths containing Chinese characters.

## Build

```powershell
.\build.ps1
```

Output:

```text
release/
  photosign.exe
  photosign-cli.exe
  input/
  output/
  README.md
```

`build/`, `dist/`, and `release/` are generated directories and are ignored by Git.

## Project Layout

```text
core/              OCR engine and task runners
utils/             image, file, and table helpers
main.py            CLI entry point and GUI launcher
gui.py             Tkinter GUI
photosign.spec     PyInstaller configuration
build.ps1          Windows release build script
```

## Open Source Notes

- Do not commit real input photos, generated output, credentials, local databases, or model cache binaries.
- Keep sample data synthetic or explicitly redistributable.
- Review third-party dependency licenses before redistributing packaged builds.

## License

MIT License. See [LICENSE](LICENSE).
