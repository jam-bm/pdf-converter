import subprocess
from pathlib import Path
from app.schemas.conversion import ConversionResult


def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> ConversionResult:
    # LibreOffice writes <input-stem>.pdf into --outdir; it cannot rename output.
    result = subprocess.run(
        [
            "libreoffice", "--headless", "--convert-to", "pdf",
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
