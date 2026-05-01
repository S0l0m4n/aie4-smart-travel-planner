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
            SELECT destination_name, content, source,
                   embedding <=> CAST(:embedding AS vector) AS distance
            FROM documents
            ORDER BY distance
            LIMIT :k
        """),
        {"embedding": str(embedding), "k": k},
    )
    return [
        {
            "destination_name": row[0],
            "content": row[1],
            "source": row[2],
            "distance": float(row[3]),
        }
        for row in result.fetchall()
    ]
