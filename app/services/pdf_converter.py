from pathlib import Path
from pdf2docx import Converter
from app.schemas.conversion import ConversionResult


def convert_pdf_to_docx(pdf_path: Path, output_dir: Path) -> ConversionResult:
    output_name = pdf_path.stem + ".docx"
    output_path = output_dir / output_name

    cv = Converter(str(pdf_path))
    cv.convert(str(output_path), start=0, end=None)
    cv.close()

    import fitz
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    doc.close()

    return ConversionResult(
        filename=output_name,
        original_name=pdf_path.name,
        download_url=f"/api/v1/convert/download/{output_name}",
        total_pages=total_pages,
        file_size_bytes=output_path.stat().st_size,
    )
