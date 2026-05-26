"""
Text chunking service for resume documents.
Cleans, normalizes, and chunks text into ~800 token segments for embedding.
"""

import re
from typing import Optional

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("chunking")


class TextChunk:
    """Represents a chunk of text with metadata."""

    def __init__(
        self,
        text: str,
        chunk_index: int,
        total_chunks: int,
        candidate_name: str = "",
        section: str = "",
        token_count: int = 0,
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
        self.candidate_name = candidate_name
        self.section = section
        self.token_count = token_count


class ChunkingService:
    """Service for cleaning and chunking resume text."""

    def __init__(self):
        self.settings = get_settings()
        self._encoding = None

    @property
    def encoding(self):
        """Lazy-load tiktoken encoding."""
        if self._encoding is None:
            import tiktoken
            self._encoding = tiktoken.get_encoding("cl100k_base")
        return self._encoding

    def clean_text(self, text: str) -> str:
        """Clean and normalize resume text."""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive whitespace
        text = re.sub(r" {3,}", "  ", text)

        # Remove excessive blank lines (keep max 2)
        text = re.sub(r"\n{4,}", "\n\n\n", text)

        # Remove common header/footer artifacts
        text = re.sub(r"(?i)page \d+ of \d+", "", text)
        text = re.sub(r"(?i)confidential", "", text)

        # Normalize unicode characters
        text = text.replace("\u2019", "'")
        text = text.replace("\u2018", "'")
        text = text.replace("\u201c", '"')
        text = text.replace("\u201d", '"')
        text = text.replace("\u2013", "-")
        text = text.replace("\u2014", "-")
        text = text.replace("\u2022", "•")

        return text.strip()

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        return len(self.encoding.encode(text))

    def chunk_text(
        self,
        text: str,
        candidate_name: str = "",
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
    ) -> list[TextChunk]:
        """
        Chunk text into segments of approximately chunk_size tokens
        with overlap tokens of overlap between chunks.
        """
        chunk_size = chunk_size or self.settings.CHUNK_SIZE_TOKENS
        overlap = overlap or self.settings.CHUNK_OVERLAP_TOKENS

        cleaned = self.clean_text(text)

        # If text is short enough, return as single chunk
        total_tokens = self.count_tokens(cleaned)
        if total_tokens <= chunk_size:
            return [
                TextChunk(
                    text=cleaned,
                    chunk_index=0,
                    total_chunks=1,
                    candidate_name=candidate_name,
                    token_count=total_tokens,
                )
            ]

        # Split by sections first for better semantic boundaries
        sections = self._split_by_sections(cleaned)

        chunks: list[TextChunk] = []
        current_text = ""
        current_tokens = 0

        for section_name, section_text in sections:
            section_tokens = self.count_tokens(section_text)

            if current_tokens + section_tokens <= chunk_size:
                current_text += section_text + "\n\n"
                current_tokens += section_tokens
            else:
                # Save current chunk if it has content
                if current_text.strip():
                    chunks.append(TextChunk(
                        text=current_text.strip(),
                        chunk_index=len(chunks),
                        total_chunks=0,  # Will be updated
                        candidate_name=candidate_name,
                        section=section_name,
                        token_count=current_tokens,
                    ))

                # If section itself is too large, split it further
                if section_tokens > chunk_size:
                    sub_chunks = self._split_large_section(
                        section_text, section_name, candidate_name, chunk_size, overlap
                    )
                    for sc in sub_chunks:
                        sc.chunk_index = len(chunks)
                        chunks.append(sc)
                    current_text = ""
                    current_tokens = 0
                else:
                    # Start new chunk with overlap from previous
                    if chunks:
                        overlap_text = self._get_overlap_text(chunks[-1].text, overlap)
                        current_text = overlap_text + "\n\n" + section_text + "\n\n"
                        current_tokens = self.count_tokens(current_text)
                    else:
                        current_text = section_text + "\n\n"
                        current_tokens = section_tokens

        # Don't forget the last chunk
        if current_text.strip():
            chunks.append(TextChunk(
                text=current_text.strip(),
                chunk_index=len(chunks),
                total_chunks=0,
                candidate_name=candidate_name,
                token_count=self.count_tokens(current_text),
            ))

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        logger.info(
            f"Chunked resume for '{candidate_name}': {total_tokens} tokens → {len(chunks)} chunks"
        )
        return chunks

    def _split_by_sections(self, text: str) -> list[tuple[str, str]]:
        """Split text into labeled sections based on common resume headers."""
        section_patterns = [
            r"(?i)^(PROFESSIONAL\s+SUMMARY|SUMMARY|PROFILE|OBJECTIVE|ABOUT)",
            r"(?i)^(TECHNICAL\s+SKILLS|SKILLS|CORE\s+COMPETENCIES|TECHNOLOGIES)",
            r"(?i)^(WORK\s+EXPERIENCE|EXPERIENCE|EMPLOYMENT|CAREER)",
            r"(?i)^(EDUCATION|ACADEMIC)",
            r"(?i)^(CERTIFICATIONS?|LICENSES?)",
            r"(?i)^(PROJECTS?|PORTFOLIO)",
            r"(?i)^(PUBLICATIONS?|PAPERS?)",
            r"(?i)^(AWARDS?|HONORS?|ACHIEVEMENTS?)",
        ]

        combined_pattern = "|".join(f"({p})" for p in section_patterns)
        lines = text.split("\n")

        sections: list[tuple[str, str]] = []
        current_section = "Header"
        current_lines: list[str] = []

        for line in lines:
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    # Save previous section
                    if current_lines:
                        sections.append((current_section, "\n".join(current_lines)))
                    current_section = line.strip()
                    current_lines = [line]
                    is_header = True
                    break

            if not is_header:
                current_lines.append(line)

        if current_lines:
            sections.append((current_section, "\n".join(current_lines)))

        return sections if sections else [("Full", text)]

    def _split_large_section(
        self,
        text: str,
        section_name: str,
        candidate_name: str,
        chunk_size: int,
        overlap: int,
    ) -> list[TextChunk]:
        """Split a large section into smaller chunks by sentences/paragraphs."""
        sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
        chunks: list[TextChunk] = []
        current_text = ""
        current_tokens = 0

        for sentence in sentences:
            sent_tokens = self.count_tokens(sentence)
            if current_tokens + sent_tokens > chunk_size and current_text:
                chunks.append(TextChunk(
                    text=current_text.strip(),
                    chunk_index=0,
                    total_chunks=0,
                    candidate_name=candidate_name,
                    section=section_name,
                    token_count=current_tokens,
                ))
                # Add overlap
                overlap_text = self._get_overlap_text(current_text, overlap)
                current_text = overlap_text + " " + sentence
                current_tokens = self.count_tokens(current_text)
            else:
                current_text += " " + sentence
                current_tokens += sent_tokens

        if current_text.strip():
            chunks.append(TextChunk(
                text=current_text.strip(),
                chunk_index=0,
                total_chunks=0,
                candidate_name=candidate_name,
                section=section_name,
                token_count=self.count_tokens(current_text),
            ))

        return chunks

    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Get the last N tokens of text for overlap."""
        tokens = self.encoding.encode(text)
        if len(tokens) <= overlap_tokens:
            return text
        overlap = tokens[-overlap_tokens:]
        return self.encoding.decode(overlap)


def get_chunking_service() -> ChunkingService:
    """Factory for chunking service."""
    return ChunkingService()
