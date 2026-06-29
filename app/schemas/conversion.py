from pydantic import BaseModel
from typing import Optional


class ExtractedImage(BaseModel):
    index: int
    page: int
    width: int
    height: int
    format: str
    base64_data: str


class ExtractedPage(BaseModel):
    page_number: int
    text: str
    image_count: int


class ExtractionResult(BaseModel):
    filename: str
    total_pages: int
    pages: list[ExtractedPage]
    images: list[ExtractedImage]
    full_text: str


class ConversionResult(BaseModel):
    filename: str
    original_name: str
    download_url: str
    total_pages: int
    file_size_bytes: int


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
