from io import BytesIO


class PdfExtractionService:
    def extract_text(self, content: bytes) -> str:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def chunk_text(text: str, *, max_chars: int = 1200) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    return [
        normalized[index : index + max_chars]
        for index in range(0, len(normalized), max_chars)
    ]

