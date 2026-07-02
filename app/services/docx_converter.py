import os
import shutil
import subprocess
from pathlib import Path
from app.schemas.conversion import ConversionResult

# Common install locations for the LibreOffice CLI. On Linux/Docker it's `libreoffice`
# (or `soffice`) on PATH; on Windows/macOS it's `soffice` at a fixed path. Override with
# the LIBREOFFICE_BIN env var if installed somewhere else.
_LIBREOFFICE_CANDIDATES = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)


def _find_libreoffice() -> str:
    override = os.getenv("LIBREOFFICE_BIN")
    if override and Path(override).exists():
        return override
    for name in ("libreoffice", "soffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in _LIBREOFFICE_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "LibreOffice not found. Install it and/or set the LIBREOFFICE_BIN env var to the "
        "soffice executable."
    )


def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> ConversionResult:
    # LibreOffice writes <input-stem>.pdf into --outdir; it cannot rename output.
    result = subprocess.run(
        [
            _find_libreoffice(), "--headless", "--convert-to", "pdf",
            "--outdir", str(output_dir), str(docx_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    output_path = output_dir / (docx_path.stem + ".pdf")
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(
            f"LibreOffice conversion failed: {result.stderr.strip() or result.stdout.strip()}"
        )

    return ConversionResult(
        filename=output_path.name,
        original_name=docx_path.name,
        download_url=f"/api/v1/convert/download/{output_path.name}",
        total_pages=0,  # page count not readily available without reopening the PDF
        file_size_bytes=output_path.stat().st_size,
    )
