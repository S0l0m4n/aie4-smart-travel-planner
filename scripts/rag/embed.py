"""Chunk and embed Wikivoyage text files, then insert into the documents table.

Place plain-text files in data/wikivoyage/<DestinationName>.txt, then run:
    python scripts/embed.py

Each filename (minus .txt) becomes the destination_name in the DB.
Run once to populate the database; it is safe to re-run (inserts are cumulative).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings
from app.database import Base
from app.logging_config import configure_logging, get_logger
import app.models  # noqa: F401

WIKIVOYAGE_DIR = Path(__file__).resolve().parents[1] / "data" / "wikivoyage"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def _chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) >= 50]


async def main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_output=False)
    log = get_logger(__name__)

    if not WIKIVOYAGE_DIR.exists():
        log.error("wikivoyage_dir.missing", path=str(WIKIVOYAGE_DIR))
        log.info("hint", message="Create data/wikivoyage/ and add <DestinationName>.txt files")
        return

    txt_files = sorted(WIKIVOYAGE_DIR.glob("*.txt"))
    if not txt_files:
        log.warning("no_files_found", path=str(WIKIVOYAGE_DIR))
        return

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    total = 0
    async with session_factory() as session:
        for txt_file in txt_files:
            destination_name = txt_file.stem
            chunks = _chunk_text(txt_file.read_text(encoding="utf-8"))
            embeddings = embed_model.encode(chunks, batch_size=32, show_progress_bar=False)
            log.info("embedding", destination=destination_name, chunks=len(chunks))
            for chunk, embedding in zip(chunks, embeddings):
                await session.execute(
                    text("""
                        INSERT INTO documents (destination_name, content, source, embedding)
                        VALUES (:name, :content, :source, CAST(:embedding AS vector))
                    """),
                    {
                        "name": destination_name,
                        "content": chunk,
                        "source": f"Wikivoyage: {destination_name}",
                        "embedding": str(embedding.tolist()),
                    },
                )
            total += len(chunks)
        await session.commit()

    await engine.dispose()
    log.info("embed.complete", total_chunks=total, destinations=len(txt_files))


if __name__ == "__main__":
    asyncio.run(main())