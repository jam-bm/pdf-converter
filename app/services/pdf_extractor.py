import base64
import fitz  # PyMuPDF
from pathlib import Path
from app.schemas.conversion import ExtractionResult, ExtractedPage, ExtractedImage


def extract_pdf_content(pdf_path: Path) -> ExtractionResult:
    doc = fitz.open(str(pdf_path))
    pages: list[ExtractedPage] = []
    images: list[ExtractedImage] = []
    full_text_parts: list[str] = []
    image_index = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        text = page.get_text("text").strip()
        if not text:
            tp = page.get_textpage_ocr(flags=0, dpi=300, full=True)
            text = page.get_text("text", textpage=tp).strip()
        full_text_parts.append(text)

        page_images = _extract_images_from_page(doc, page, page_num + 1, image_index)
        images.extend(page_images)
        image_index += len(page_images)

        pages.append(ExtractedPage(
            page_number=page_num + 1,
            text=text,
            image_count=len(page_images),
        ))

    doc.close()

    return ExtractionResult(
        filename=pdf_path.name,
        total_pages=len(pages),
        pages=pages,
        images=images,
        full_text="\n\n".join(full_text_parts),
    )


def _extract_images_from_page(
    doc: fitz.Document,
    page: fitz.Page,
    page_number: int,
    start_index: int,
) -> list[ExtractedImage]:
    extracted: list[ExtractedImage] = []

    for img_index, img_ref in enumerate(page.get_images(full=True)):
        xref = img_ref[0]
        try:
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            width = base_image["width"]
            height = base_image["height"]

            b64 = base64.b64encode(image_bytes).decode("utf-8")

            extracted.append(ExtractedImage(
                index=start_index + img_index,
                page=page_number,
                width=width,
                height=height,
                format=image_ext.upper(),
                base64_data=f"data:image/{image_ext};base64,{b64}",
            ))
        except Exception:
            continue

    return extracted
