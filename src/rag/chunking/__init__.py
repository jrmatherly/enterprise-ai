"""Document chunking strategies.

Provides different methods for splitting documents into chunks
suitable for embedding and retrieval.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Chunk:
    """A document chunk ready for embedding."""

    index: int
    text: str
    start_char: int
    end_char: int
    metadata: dict


class ChunkingStrategy(ABC):
    """Base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into chunks."""


class FixedSizeChunker(ChunkingStrategy):
    """Fixed-size chunking with overlap.

    Simple but effective strategy that splits text into
    fixed-size chunks with configurable overlap.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into fixed-size overlapping chunks."""
        if not text.strip():
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Don't cut in the middle of a word
            if end < len(text):
                # Find the last space before end
                space_pos = text.rfind(" ", start, end)
                if space_pos > start + self.min_chunk_size:
                    end = space_pos

            chunk_text = text[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    Chunk(
                        index=index,
                        text=chunk_text,
                        start_char=start,
                        end_char=end,
                        metadata=metadata or {},
                    )
                )
                index += 1

            # Move start with overlap
            start = end - self.overlap
            if start < 0:
                start = end

        return chunks


class ParagraphChunker(ChunkingStrategy):
    """Paragraph-based chunking.

    Splits text by paragraph boundaries, combining small
    paragraphs and splitting large ones.
    """

    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 100,
        paragraph_separator: str = "\n\n",
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.paragraph_separator = paragraph_separator
        self.fallback_chunker = FixedSizeChunker(
            chunk_size=max_chunk_size,
            overlap=200,
            min_chunk_size=min_chunk_size,
        )

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text by paragraphs."""
        if not text.strip():
            return []

        # Split into paragraphs
        paragraphs = text.split(self.paragraph_separator)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return []

        chunks = []
        current_text = ""
        current_start = 0
        index = 0
        char_pos = 0

        for para in paragraphs:
            # If paragraph is too large, use fixed-size chunking
            if len(para) > self.max_chunk_size:
                # Flush current buffer first
                if current_text:
                    chunks.append(
                        Chunk(
                            index=index,
                            text=current_text,
                            start_char=current_start,
                            end_char=char_pos,
                            metadata=metadata or {},
                        )
                    )
                    index += 1
                    current_text = ""

                # Chunk the large paragraph
                sub_chunks = self.fallback_chunker.chunk(para, metadata)
                for sub in sub_chunks:
                    sub.index = index
                    sub.start_char += char_pos
                    sub.end_char += char_pos
                    chunks.append(sub)
                    index += 1

                char_pos += len(para) + len(self.paragraph_separator)
                current_start = char_pos
                continue

            # Would adding this paragraph exceed max size?
            combined = current_text + self.paragraph_separator + para if current_text else para

            if len(combined) > self.max_chunk_size:
                # Flush current buffer
                if current_text:
                    chunks.append(
                        Chunk(
                            index=index,
                            text=current_text,
                            start_char=current_start,
                            end_char=char_pos - len(self.paragraph_separator),
                            metadata=metadata or {},
                        )
                    )
                    index += 1

                current_text = para
                current_start = char_pos
            else:
                current_text = combined

            char_pos += len(para) + len(self.paragraph_separator)

        # Don't forget the last chunk
        if current_text and len(current_text) >= self.min_chunk_size:
            chunks.append(
                Chunk(
                    index=index,
                    text=current_text,
                    start_char=current_start,
                    end_char=len(text),
                    metadata=metadata or {},
                )
            )

        return chunks


def get_chunker(strategy: str = "paragraph", **kwargs) -> ChunkingStrategy:
    """Get a chunking strategy by name.

    Args:
        strategy: "fixed" or "paragraph"
        **kwargs: Strategy-specific parameters

    Returns:
        Configured chunking strategy
    """
    if strategy == "fixed":
        return FixedSizeChunker(**kwargs)
    if strategy == "paragraph":
        return ParagraphChunker(**kwargs)
    raise ValueError(f"Unknown chunking strategy: {strategy}")


__all__ = [
    "Chunk",
    "ChunkingStrategy",
    "FixedSizeChunker",
    "ParagraphChunker",
    "get_chunker",
]
