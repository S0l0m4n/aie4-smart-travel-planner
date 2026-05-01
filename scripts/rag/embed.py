"""Chunk and embed Wikivoyage text files, insert into the documents table.

Place wikitext files in data/raw_wikivoyage/<DestinationName>.txt, then run:
    python scripts/rag/embed.py [--strategy fixed|sections]

Run once to populate; safe to re-run (inserts are cumulative, not deduplicated).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.config import get_settings
from app.database import Base
from app.logging_config import configure_logging, get_logger
import app.models  # noqa: F401 — registers ORM models with Base.metadata

from chunker import chunk_by_sections, chunk_fixed


async def main(strategy: str) -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_output=False)
    log = get_logger(__name__)

    wikivoyage_dir = settings.knowledge_data_path
    if not wikivoyage_dir.exists():
        log.error("wikivoyage_dir.missing", path=str(wikivoyage_dir))
        return

    txt_files = sorted(wikivoyage_dir.glob("*.txt"))
    if not txt_files:
        log.warning("no_files_found", path=str(wikivoyage_dir))
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
            raw_text = txt_file.read_text(encoding="utf-8")
            chunks = (
                chunk_by_sections(raw_text)
                if strategy == "sections"
                else chunk_fixed(raw_text)
            )
            if not chunks:
                log.warning("no_chunks", destination=destination_name)
                continue
            embeddings = embed_model.encode(chunks, batch_size=32, show_progress_bar=False)
            log.info("embedding", destination=destination_name, chunks=len(chunks), strategy=strategy)
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
    log.info("embed.complete", total_chunks=total, destinations=len(txt_files), strategy=strategy)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed Wikivoyage data into Postgres/pgvector.")
    parser.add_argument(
        "--strategy",
        choices=["fixed", "sections"],
        default="fixed",
        help="fixed: overlapping fixed-size chunks (default); sections: split on wikitext/markdown headings",
    )
    args = parser.parse_args()
    asyncio.run(main(args.strategy))
