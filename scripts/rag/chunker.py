"""Two chunking strategies for RAG ingestion.

chunk_fixed:      overlapping fixed-size chunks with sentence-aware boundaries.
chunk_by_sections: split on markdown headings or double newlines.

CLI usage:
    python chunker.py <file> [--chunk-size N] [--overlap N] [--strategy fixed|sections]
"""
from __future__ import annotations

import argparse
import re
import sys

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
MIN_CHUNK_LEN = 50


def chunk_fixed(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping fixed-size chunks.

    Scans backward from each cut point for a sentence boundary so chunks
    don't end mid-sentence. Produces better embeddings than hard character splits.
    """
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if len(text) >= MIN_CHUNK_LEN else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Search only in the last half of the range so we don't snap back
            # to a boundary inside the overlap zone and get stuck creeping forward.
            search_from = max(start + 1, end - chunk_size // 2)
            for boundary in (". ", ".\n", "? ", "! ", "\n\n"):
                last_break = text.rfind(boundary, search_from, end)
                if last_break != -1:
                    end = last_break + len(boundary)
                    break
        chunk = text[start:end].strip()
        if len(chunk) >= MIN_CHUNK_LEN:
            chunks.append(chunk)
        start = len(text) if end >= len(text) else max(end - overlap, start + 1)
    return chunks


def chunk_by_sections(text: str) -> list[str]:
    """Split text on wikitext or markdown headings, or blank lines.

    Tries wikitext (==Section==) then markdown (# Section) then double newlines.
    Produces variable-size chunks that follow document structure.
    """
    text = text.strip()
    # Wikitext: == Heading == or === Sub ===
    sections = re.split(r"\n(?===+[^=])", text)
    if len(sections) <= 1:
        # Markdown: # Heading
        sections = re.split(r"\n(?=#{1,3}\s)", text)
    if len(sections) <= 1:
        sections = re.split(r"\n\n+", text)
    return [s.strip() for s in sections if len(s.strip()) >= MIN_CHUNK_LEN]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk a text file for RAG ingestion.")
    parser.add_argument("file", help="Path to the text file to chunk")
    parser.add_argument("--strategy", choices=["fixed", "sections"], default="fixed")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help=f"Characters per chunk (default: {CHUNK_SIZE}); only used with --strategy fixed")
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP, help=f"Overlap between chunks in characters (default: {CHUNK_OVERLAP}); only used with --strategy fixed")
    args = parser.parse_args()

    text = open(args.file).read()
    if args.strategy == "fixed":
        chunks = chunk_fixed(text, chunk_size=args.chunk_size, overlap=args.overlap)
    else:
        chunks = chunk_by_sections(text)

    for i, chunk in enumerate(chunks):
        print(f"--- chunk {i + 1} ({len(chunk)} chars) ---")
        print(chunk)
        print()
    print(f"{len(chunks)} chunks total", file=sys.stderr)
