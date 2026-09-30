from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.config import get_settings

settings = get_settings()
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@dataclass(frozen=True)
class ExtractedSegment:
    text: str
    metadata: dict


@dataclass(frozen=True)
class TextChunk:
    content: str
    metadata: dict


def extract_segments(filename: str, content: bytes) -> list[ExtractedSegment]:
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("unsupported document type")

    if suffix in {".txt", ".md"}:
        text = content.decode("utf-8", errors="replace").strip()
        return [ExtractedSegment(text=text, metadata={})] if text else []

    reader = PdfReader(BytesIO(content))
    segments: list[ExtractedSegment] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append(
                ExtractedSegment(
                    text=text,
                    metadata={"page": page_number},
                )
            )

    return segments


def chunk_segments(segments: list[ExtractedSegment]) -> list[TextChunk]:
    chunk_size = settings.chunk_size_words
    overlap = settings.chunk_overlap_words

    if chunk_size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    step = chunk_size - overlap
    chunks: list[TextChunk] = []

    for segment in segments:
        words = segment.text.split()

        for start in range(0, len(words), step):
            window = words[start : start + chunk_size]
            if not window:
                continue

            chunks.append(
                TextChunk(
                    content=" ".join(window),
                    metadata={
                        **segment.metadata,
                        "word_start": start,
                        "word_count": len(window),
                    },
                )
            )

            if start + chunk_size >= len(words):
                break

    return chunks
