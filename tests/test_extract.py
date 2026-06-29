import io
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_extract_rejects_non_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/extract/text-only",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_convert_rejects_non_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/convert/to-docx",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
    assert response.status_code == 400
