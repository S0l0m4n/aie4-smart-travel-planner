from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def retrieve_chunks(
    query: str,
    embed_model,
    session: AsyncSession,
    k: int = 5,
) -> list[dict]:
    embedding = embed_model.encode(query).tolist()
    result = await session.execute(
        text("""
            SELECT destination_name, content, source
            FROM documents
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :k
        """),
        {"embedding": str(embedding), "k": k},
    )
    return [
        {"destination_name": row[0], "content": row[1], "source": row[2]}
        for row in result.fetchall()
    ]