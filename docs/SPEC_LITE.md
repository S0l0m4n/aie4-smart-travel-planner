# Smart Travel Planner — Demo Spec

## Scope

Get a working end-to-end demo: user sends a travel question via React UI, a LangChain agent decides which tools to call, synthesizes the results, and returns a coherent recommendation.

---

## Architecture

```
React Frontend (Vite)
    ↓ POST /api/chat  { "message": str }
FastAPI Backend (async)
    ↓
LangChain ReAct Agent (single LLM)
    ├── Tool 1: classify_trip
    │     Parse user preferences → extract features → run scikit-learn classifier
    │     Returns: travel style (Adventure, Relaxation, Culture, Budget, Luxury, Family)
    │
    └── Tool 2: search_destinations
          Embed query → pgvector cosine similarity → return top-k chunks
          Returns: relevant Wikivoyage passages with destination names
    ↓
Agent synthesizes tool results into one coherent recommendation
    ↓
Response: { "response": str, "tool_calls": list[dict] }
```

---

## What Exists

- ML classifier trained and saved as joblib
- `/parse` debug route for feature extraction (needs fixing — in progress)
- Dummy `/chat` endpoint (becomes the real one)
- Wikivoyage data downloaded for ~15 destinations

---

## Build Order

### 1. Fix classifier + parse (Claude Code — Sam)

Feature extraction from natural language → classifier prediction. Already in progress.

### 2. Postgres + pgvector

- Docker container: `pgvector/pgvector:pg16`
- Named volume for persistence
- Expose port 5432
- One database, one table for embeddings:

```sql
documents (
    id            SERIAL PRIMARY KEY,
    destination   TEXT NOT NULL,
    content       TEXT NOT NULL,
    source        TEXT,
    embedding     VECTOR(384),
    created_at    TIMESTAMPTZ DEFAULT NOW()
)
```

### 3. RAG pipeline script — `scripts/embed.py`

- Read Wikivoyage text files from `data/wikivoyage/`
- Chunk: ~400 tokens per chunk, ~50 token overlap (start here, adjust if retrieval is poor)
- Embed with SentenceTransformers `all-MiniLM-L6-v2` (384 dims, runs locally)
- Insert chunks + embeddings into the `documents` table
- Run once to populate, not on every startup

### 4. RAG tool function

- Input: query string (Pydantic-validated)
- Embed the query with the same SentenceTransformers model
- Cosine similarity search via pgvector, return top 5 chunks
- Output: list of `{ destination, content, source, score }`
- Embedding model loaded once at startup (lifespan handler)

### 5. LangChain ReAct agent on `/chat`

- Single LLM (Groq or OpenAI — whatever is already configured)
- Two tools registered: `classify_trip`, `search_destinations`
- Agent decides tool order based on the query:
  - "I want a budget hiking trip" → classifier first, then RAG informed by the result
  - "Tell me about Tbilisi" → RAG directly
  - Agent may call both, one, or neither — it reasons about what it needs
- The agent **synthesizes** across tool results — one coherent answer, not tool outputs glued together
- Tool call metadata returned alongside the response for the frontend

### 6. React frontend

- Vite + React, minimal
- Single chat view: input box, send button, message history
- POSTs to `/api/chat`, displays the response
- Collapsible panel under each response showing tool calls (which tools fired, what they returned)
- No auth, no routing, no polish — functional demo only

---

## Deferred (post-demo)

- Two-model routing (cheap LLM for parse/rewrite, strong for synthesis)
- Explicit RAG query rewriting step
- Auth (signup, login, JWT, user-scoped runs)
- Persistence tables (agent_runs, tool_calls, webhook_logs)
- Webhook delivery (Discord)
- Dockerized backend + frontend
- Tests
- Streaming responses
- LangSmith tracing

---

## Key Decisions

**Why one LLM for now?** Two-model routing is an optimization. The agent works identically with one model. Add the cheap model for parse/rewrite after the demo works.

**Why ReAct and not a fixed graph?** The brief requires genuine synthesis, meaning the LLM decides what tools to call based on the query. A hardcoded sequence (always classify → always RAG) would work but doesn't satisfy "the agent must genuinely synthesize across tools." ReAct gives the agent autonomy to route differently depending on the question.

**Why no explicit query rewrite?** The ReAct agent already reformulates the user's intent when constructing tool input arguments. That counts. A dedicated rewrite node is a refinement for later.

**Chunk size 400 tokens / 50 overlap?** Starting point. If retrieval quality is poor during testing, adjust. Document what you tried and why in the README — that's what the brief asks for.
