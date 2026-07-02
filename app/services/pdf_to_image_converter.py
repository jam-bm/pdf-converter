import uuid
import zipfile
from pathlib import Path

import fitz  # PyMuPDF

from app.schemas.conversion import ConversionResult


def convert_pdf_to_image(pdf_path: Path, output_dir: Path, dpi: int = 150) -> ConversionResult:
    """Render every page of a PDF to a PNG image.

    - Single-page PDF  -> one .png file.
    - Multi-page PDF   -> a .zip archive containing page_1.png, page_2.png, ...

    The result is served through the existing GET /api/v1/convert/download/{filename}
    route (which handles .png and .zip media types).
    """
    doc = fitz.open(str(pdf_path))
    try:
        page_count = len(doc)
        if page_count == 0:
            raise ValueError("PDF has no pages")

        zoom = dpi / 72.0  # 72 is PDF's native DPI
        matrix = fitz.Matrix(zoom, zoom)

        if page_count == 1:
            output_name = f"{uuid.uuid4().hex}.png"
            output_path = output_dir / output_name
            pix = doc[0].get_pixmap(matrix=matrix)
            pix.save(str(output_path))
        else:
            output_name = f"{uuid.uuid4().hex}.zip"
            output_path = output_dir / output_name
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for page_num in range(page_count):
                    pix = doc[page_num].get_pixmap(matrix=matrix)
                    archive.writestr(f"page_{page_num + 1}.png", pix.tobytes("png"))
    finally:
        doc.close()

    return ConversionResult(
        filename=output_name,
        original_name=pdf_path.name,
        download_url=f"/api/v1/convert/download/{output_name}",
        total_pages=page_count,
        file_size_bytes=output_path.stat().st_size,
    )
