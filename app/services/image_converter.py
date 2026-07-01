import uuid
from pathlib import Path
from PIL import Image
from app.schemas.conversion import ConversionResult


def convert_image_to_pdf(image_path: Path, output_dir: Path) -> ConversionResult:
    output_name = f"{uuid.uuid4().hex}.pdf"
    output_path = output_dir / output_name

    with Image.open(image_path) as img:
        # PDF has no alpha channel; flatten RGBA/P onto white
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(str(output_path), "PDF", resolution=100.0)

    return ConversionResult(
        filename=output_name,
        original_name=image_path.name,
        download_url=f"/api/v1/convert/download/{output_name}",
        total_pages=1,
        file_size_bytes=output_path.stat().st_size,
    )
