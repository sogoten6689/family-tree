from __future__ import annotations

import io

import pypdfium2 as pdfium

MAX_PDF_PAGES_DEFAULT = 8


def render_pdf_pages_to_png(
    pdf_bytes: bytes,
    *,
    dpi: int = 200,
    max_pages: int = MAX_PDF_PAGES_DEFAULT,
) -> list[bytes]:
    """Render each PDF page to a PNG image (bytes) for OCR.

    Giới hạn `max_pages` để tránh gọi quá nhiều lần API OCR trả phí/rate-limited
    (Kim Hán Nôm, 40 request/phút) từ một lần upload nhanh trong Document Reader.
    Tài liệu dài hơn nên dùng luồng Admin (upload nhiều file + pipeline 7 bước).
    """
    if not pdf_bytes:
        raise ValueError("File PDF rỗng.")

    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        page_count = min(len(pdf), max_pages)
        scale = dpi / 72
        pages: list[bytes] = []
        for index in range(page_count):
            page = pdf[index]
            try:
                bitmap = page.render(scale=scale)
                pil_image = bitmap.to_pil()
                buffer = io.BytesIO()
                pil_image.save(buffer, format="PNG")
                pages.append(buffer.getvalue())
            finally:
                page.close()
        return pages
    finally:
        pdf.close()
