# Smart Travel Planner — Technical Spec

## 1. Overview

An AI-powered travel planning agent. A user asks a natural language travel question via a React chat UI. A FastAPI backend runs a LangGraph agent that calls three tools — an ML classifier, a RAG retriever, and a live conditions API — then synthesizes a detailed travel recommendation using a strong LLM.

### Architecture

```
React Frontend (Vite)
    ↓ POST /api/chat
FastAPI Backend (async)
    ↓
LangGraph Agent
    ├── Parse (cheap LLM) — extract structured preferences
    ├── Classify (scikit-learn model) — predict travel style
    ├── Rewrite Query (cheap LLM) — optimize query for RAG
    ├── Retrieve (pgvector RAG) — find matching destinations
    ├── Live Conditions (Open-Meteo API) — weather for dates
    └── Synthesize (strong LLM) — final recommendation
    ↓
Postgres + pgvector (one database for everything)
```

### Tech Stack

- **Backend:** FastAPI, async throughout
- **Agent:** LangGraph + LangChain
- **LLMs:** Groq/OpenAI via LangChain (cheap model for parse/rewrite, strong model for synthesis)
- **ML:** scikit-learn Pipeline, joblib
- **Database:** Postgres 16 + pgvector, SQLAlchemy 2.x async, asyncpg driver
- **Embeddings:** SentenceTransformers `all-MiniLM-L6-v2` (384 dimensions), runs locally
- **Live API:** Open-Meteo (free, no API key)
- **Frontend:** Vite + React
- **Auth:** FastAPI + JWT (Phase 2)
- **Containerization:** Docker Compose (Phase 3)

---

## 2. Phases

### Phase 1 — Core AI Loop (Tuesday–Wednesday)

Get a working end-to-end system: user sends a message, agent runs all three tools, returns a synthesized recommendation.

- Postgres + pgvector running in Docker (with named volume)
- Documents table only (content, source, embedding)
- ML classifier: dataset, one trained pipeline, saved with joblib
- RAG tool: Wikivoyage content chunked, embedded, stored in pgvector
- Live conditions tool: Open-Meteo weather API
- LangGraph agent with structured flow (parse → classify → retrieve → live conditions → synthesize)
- Two-model routing: cheap LLM for parse/rewrite, strong LLM for synthesis
- FastAPI with one route: POST /api/chat (non-streaming)
- React frontend: text input, message history, tool call visibility
- Async from the start: async routes, async DB, async HTTP calls
- LangSmith tracing enabled via environment variables

### Phase 2 — Polish, Persistence, Webhooks, Auth (Thursday morning/afternoon)

1. ML classifier polish: k-fold CV on 3+ classifiers, tune one, class imbalance reporting, clean results.csv run
2. Additional tables: agent_runs, tool_calls — log every agent run and tool invocation
3. Webhook delivery (Discord): timeout, retry with backoff, structured logging
4. Auth: users table, signup, login, JWT, password hashing. Agent runs scoped to logged-in user
5. Webhook_logs table: track delivery attempts, status codes, retries

### Phase 3 — Docker, Docs, Stretch (Thursday evening)

- Dockerfiles for backend and frontend
- docker-compose.yml: backend + frontend + Postgres, one command startup
- Streaming response (SSE) if time allows
- Tests: each tool in isolation, Pydantic schema validation, one end-to-end agent test with mocked APIs
- README: architecture diagram, labeling rules, chunking rationale, model comparison table, cost breakdown, LangSmith trace screenshot
- 3-minute demo video

---

## 3. ML Classifier

### Dataset

- 150–200 destinations (city, country)
- Generated with LLM assistance, sample-verified (15–20 rows spot-checked manually)
- Stored as `data/destinations.csv`

### Features

Decide during dataset creation. Justify each feature in README. Example starting set:

- avg_daily_cost_usd
- avg_temp_summer_c
- num_hiking_trails
- num_beaches
- num_museums_historical_sites
- num_family_attractions
- num_luxury_hotels
- safety_index (1–10)
- remoteness_score (1–10, inverse of tourism volume)

Features and labeling rubric above are illustrative. Final choices to be determined during dataset creation. Whatever you choose, justify in README.

### Labels (6 classes)

Adventure, Relaxation, Culture, Budget, Luxury, Family

### Labeling Rubric

Define clear rules before labeling. Document in README. Example:

- Adventure: high hiking/outdoor scores, moderate to low cost
- Relaxation: high beach scores, resort presence
- Culture: high museum/historical site count
- Budget: low avg_daily_cost is the dominant signal
- Luxury: high cost + high luxury hotel count
- Family: high family attraction scores
- When multiple styles apply, pick the dominant one

### Phase 1 (get it working)

- One scikit-learn Pipeline (e.g. StandardScaler + RandomForestClassifier)
- Train/test split, basic accuracy check
- Save with `joblib.dump(pipeline, "models/model.joblib")`
- Pin random seed everywhere

### Phase 2 (polish)

- Compare 3+ classifiers (e.g. RandomForest, SVM, GradientBoosting) with 5-fold cross-validation
- Report accuracy and macro F1 with mean and std for each
- Tune best performer with GridSearchCV or RandomizedSearchCV — document what you searched and why
- Report per-class precision, recall, F1 to address class imbalance
- Log every experiment to `data/results.csv` (model, params, accuracy_mean, accuracy_std, f1_mean, f1_std, timestamp)
- One clean reproducible run generates results.csv

### Training Script

- `scripts/train.py` — standalone, runnable, produces results.csv and model.joblib
- Notebook `notebooks/exploration.ipynb` for EDA and feature verification (not required to be clean)

### Agent Integration

- Tool loads joblib model once at startup via FastAPI lifespan handler
- Tool input: Pydantic schema with destination features
- Tool output: predicted travel style string

---

## 4. RAG Tool

### Content Source

- Wikivoyage pages for 10–15 destinations (free, openly licensed)
- 20–30 documents total (some destinations may have multiple pages)
- Scrape or download as plain text

### Chunking

- Split each document into chunks (e.g. 300–500 tokens per chunk)
- Overlap between chunks (e.g. 50–100 tokens) so context isn't lost at boundaries
- Justify chunk size and overlap in README — "I tried X, retrieval quality was Y, so I settled on Z"
- Each chunk stored as a row in the documents table

### Documents Table (Postgres + pgvector)

```
documents:
  id: Integer, primary key
  destination_name: String (e.g. "Tbilisi")
  content: Text (the chunk)
  source: String (e.g. "Wikivoyage: Tbilisi - See")
  embedding: Vector(384)
  created_at: DateTime
```

### Embedding Model

- SentenceTransformers `all-MiniLM-L6-v2` (384 dimensions)
- Runs locally, no API key needed
- Vector column: Vector(384)
- Loaded once at startup via FastAPI lifespan handler
- All chunks and user queries embedded with the same model

### Embedding Pipeline

- Script that reads raw documents, chunks them, generates embeddings, and inserts into Postgres
- Run once to populate the database, not on every app startup
- Stored as `scripts/embed.py`

### Retrieval

- User query (rewritten by cheap LLM) is embedded with the same model
- pgvector cosine similarity search returns top-k chunks (e.g. k=3–5)
- Test retrieval on a few hand-written queries before plugging into agent (brief requirement, Page 1, Section 2)
- Document test queries and results in README

### Agent Integration

- Tool input: Pydantic schema with query string
- Tool output: list of retrieved chunks with destination name and source
- The cheap LLM rewrites the user's raw input into a better search query before this tool is called

---

## 5. LangGraph Agent

### Structured Flow

The agent is a LangGraph StateGraph with a fixed sequence of nodes:

```
parse → is_complete? → classify → rewrite_query → retrieve → live_conditions → synthesize
              ↓ (no)
        ask_followup
```

### State

A single state object accumulates results as it flows through the graph:

```python
class AgentState(TypedDict):
    user_message: str
    parsed_preferences: dict          # budget, dates, interests, constraints
    is_complete: bool                  # all required fields present?
    travel_style: str                  # from classifier
    rag_query: str                     # rewritten by cheap LLM
    retrieved_chunks: list[str]        # from pgvector
    live_conditions: list[dict]        # weather data per destination
    response: str                      # final synthesized answer
    tool_calls: list[dict]            # log of what fired and returned
```

### Nodes

1. **parse** (cheap LLM) — extracts structured preferences from user message: budget, dates, duration, interests, constraints. Returns is_complete flag. If dates are missing, flow goes to ask_followup instead of continuing.

2. **classify** (ML model) — takes parsed preferences, runs through joblib classifier, returns travel style (Adventure, Relaxation, etc.). Logs to tool_calls.

3. **rewrite_query** (cheap LLM) — takes parsed preferences + travel style, generates a search query optimized for matching Wikivoyage content. E.g. "warm adventure hiking destinations off the beaten path."

4. **retrieve** (pgvector) — embeds the rewritten query with SentenceTransformers, runs cosine similarity search against documents table, returns top-k chunks. Logs to tool_calls.

5. **live_conditions** (Open-Meteo API) — takes candidate destinations from retrieved chunks + date range from parsed preferences. Calls weather API for each destination. Use asyncio.gather for concurrent calls. Logs to tool_calls.

6. **synthesize** (strong LLM) — receives full state: user message, preferences, travel style, retrieved chunks, live conditions. Produces a detailed recommendation: top pick with reasoning, alternatives, booking advice, practical tips. Handles conflicts (e.g. RAG says great hiking but weather shows monsoon season).

### Two-Model Routing (Page 2, Section 4)

- **Cheap model** (e.g. Llama 3.1 8B via Groq, or GPT-4o-mini): parse, rewrite_query
- **Strong model** (e.g. GPT-4o): synthesize
- Log token usage per step
- Report cost of one full query in README

### Tool Input Validation (Page 1, Section 3)

- Every tool input validated by a Pydantic schema before execution
- If validation fails, return structured error to the agent — do not crash
- Maintain an explicit tool allowlist — only the three registered tools can be called

### Error Handling

- Every external call (LLM, Open-Meteo, database) wrapped with timeout and retry with backoff
- Tool failures returned to the LLM as structured errors so it can reason about them
- A failed weather API call should not crash the entire agent run

### Tracing

- LangSmith free tier enabled via environment variables:
  - LANGCHAIN_TRACING_V2=true
  - LANGCHAIN_API_KEY=your_free_key
  - LANGCHAIN_PROJECT=travel-planner
- Every run traced end-to-end automatically by LangGraph
- Screenshot of a multi-tool trace included in README

---

## 6. FastAPI Backend

### Project Layout

```
smart-travel-planner/
  backend/
    Dockerfile
    requirements.txt
    app/
      main.py              # FastAPI app, lifespan handler
      config.py            # pydantic-settings Settings class
      models/              # SQLAlchemy models
      schemas/             # Pydantic request/response models
      routes/              # API route handlers
      services/            # business logic, agent orchestration
      tools/               # classifier, rag, live conditions
      agent/               # LangGraph graph definition
  frontend/
    Dockerfile
    src/
  scripts/
    train.py             # ML training pipeline
    embed.py             # document chunking + embedding pipeline
  data/
    destinations.csv     # training dataset
    results.csv          # experiment log
  models/
    model.joblib         # saved classifier
  notebooks/
    exploration.ipynb
  docker-compose.yml
  README.md
  .env.example
```

### Lifespan Handler (Page 2, "Singletons — Done Right")

Created once at startup, disposed on shutdown:

- Database engine (async SQLAlchemy)
- Loaded joblib classifier
- SentenceTransformers embedding model
- LLM clients (cheap + strong)
- LangGraph compiled graph

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    engine = create_async_engine(settings.database_url)
    classifier = joblib.load("models/model.joblib")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    # ... store on app.state
    yield
    # shutdown
    await engine.dispose()
```

### Dependency Injection (Page 2, "Use FastAPI's Depends")

- Database session: Depends(get_db_session)
- Current user: Depends(get_current_user) (Phase 2)
- Classifier, embed model, LLM clients: accessed via Depends functions that read from app.state
- No globals, no instantiation inside route handlers

### Configuration (Page 3, "pydantic-settings")

One Settings class, all config from environment variables:

```python
class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    openai_api_key: str
    langchain_api_key: str
    cheap_model_name: str
    strong_model_name: str
    open_meteo_base_url: str = "https://api.open-meteo.com"

    model_config = SettingsConfigDict(env_file=".env")
```

App refuses to start if required keys are missing.

### Routes

**Phase 1:**

```
POST /api/chat
  body: { "message": str }
  response: { "response": str, "tool_calls": list[dict] }
```

**Phase 2 additions:**

```
POST /api/auth/signup
  body: { "email": str, "password": str }

POST /api/auth/login
  body: { "email": str, "password": str }
  response: { "token": str }

GET /api/history
  response: list of past agent runs for logged-in user
```

### Async All the Way Down (Page 2)

- All route handlers: async def
- Database: SQLAlchemy AsyncSession via asyncpg
- HTTP calls: httpx.AsyncClient
- LLM calls: ainvoke, astream
- Zero requests.get, zero time.sleep, zero synchronous DB calls

### Error Handling

- All external calls wrapped with timeout and retry (tenacity or hand-rolled)
- Structured logging with structlog or stdlib JSON logger — no print statements
- .env.example listing every required key

---

## 7. React Frontend

### Setup

- Vite + React: `npm create vite@latest frontend -- --template react`
- Minimal dependencies

### Pages/Views

**Phase 1:**

- **Chat view** — the main interface
  - Text input at the bottom for typing trip questions
  - Message history: user messages and agent responses displayed as a conversation
  - Tool calls panel: collapsible section under each agent response showing which tools fired, their inputs, and outputs (brief requirement, Page 2, Section 7)

**Phase 2 additions:**

- **Login/Signup view** — email + password forms
- **History view** — list of past agent runs for the logged-in user (optional, time permitting)

### Chat Flow (Phase 1)

1. User types a message, hits send
2. Frontend POSTs to /api/chat with { "message": "..." }
3. Shows a loading state while waiting
4. Receives response with { "response": "...", "tool_calls": [...] }
5. Renders the response as a new message in the conversation
6. Tool calls rendered in a collapsible panel (e.g. "Classifier → Adventure", "RAG → 3 chunks retrieved", "Weather → Tbilisi 28°C July")

### Phase 3 — Streaming (if time allows)

- Switch from POST/response to SSE
- Frontend reads the stream with EventSource or fetch with readable stream
- Response renders token by token
- Tool call notifications appear as the agent progresses

### Design

- Keep it minimal and functional — don't spend time on visual polish
- A chat bubble layout, an input box, a send button, a collapsible tool panel
- Mobile responsiveness is not a priority

---

## 8. Auth (Phase 2)

### Users Table

```
users:
  id: Integer, primary key
  email: String, unique
  hashed_password: String
  created_at: DateTime
```

### Implementation

- Password hashing with bcrypt via passlib
- JWT tokens for session management
- Login returns a token, frontend stores it and sends in Authorization: Bearer <token> header
- Depends(get_current_user) middleware decodes token and provides current user to routes
- Agent runs scoped to logged-in user via foreign key

### Routes

```
POST /api/auth/signup — creates user, returns token
POST /api/auth/login — validates credentials, returns token
```

---

## 9. Webhook Delivery (Phase 2)

### Channel

- Discord webhook (simplest — just a POST to a URL with a JSON payload, no auth setup)
- User configures their webhook URL (store in users table or a separate config)

### Payload

- Trip query, synthesized recommendation, travel style, destinations mentioned, timestamp

### Reliability

- Timeout on the HTTP call (e.g. 10 seconds)
- At least one retry with exponential backoff on failure
- Structured logging on success and failure
- Webhook failure must not break the user-facing response — fire after the response is returned, or use asyncio.create_task

### Webhook Logs Table

```
webhook_logs:
  id: Integer, primary key
  agent_run_id: Integer, foreign key to agent_runs
  destination_url: String
  payload: JSON
  status_code: Integer (nullable, null if timeout)
  retries: Integer
  success: Boolean
  created_at: DateTime
```

---

## 10. Persistence — Additional Tables (Phase 2)

### agent_runs

```
agent_runs:
  id: Integer, primary key
  user_id: Integer, foreign key to users
  query: Text
  response: Text
  travel_style: String
  model_used: String
  total_tokens: Integer
  cost_usd: Float
  created_at: DateTime
```

### tool_calls

```
tool_calls:
  id: Integer, primary key
  agent_run_id: Integer, foreign key to agent_runs
  tool_name: String (classifier, rag, live_conditions)
  input: JSON
  output: JSON
  tokens_used: Integer (nullable, only for LLM-backed tools)
  duration_ms: Integer
  created_at: DateTime
```

---

## 11. Docker (Phase 3)

### docker-compose.yml

Three services:

- **db** — pgvector/pgvector:pg16, named volume for data persistence, exposes port 5432
- **backend** — builds from backend/Dockerfile, depends on db, exposes port 8000
- **frontend** — builds from frontend/Dockerfile, depends on backend, exposes port 5173

### Backend Dockerfile

- Python 3.11+ base image
- Install dependencies from requirements.txt
- Copy app code
- Run with uvicorn app.main:app --host 0.0.0.0 --port 8000

### Frontend Dockerfile

- Node base image
- Install dependencies, build with Vite
- Serve static files with nginx or similar

### Key Requirement

`docker compose up` brings the entire stack up. If it doesn't, the project is incomplete (Page 2, Section 9).

---

## 12. Tests (Phase 3)

### Required (Page 3, "Tests — At Least the Critical Path")

- Each tool tested in isolation with a fake/mocked LLM
- Pydantic schemas tested with valid and invalid inputs
- One end-to-end agent test with mocked external APIs (Open-Meteo, LLM)
- Tests run with pytest

### Nice to Have

- CI with GitHub Actions on every push

---

## 13. Engineering Standards (Apply from Phase 1)

These are not Phase 2 polish — they're how every line of code is written from the start:

- **Async everywhere** — async def, await, AsyncSession, httpx.AsyncClient, ainvoke
- **Dependency injection** — Depends() for db session, LLM clients, models, current user
- **Lifespan singletons** — db engine, joblib model, embedding model, LLM clients created once at startup
- **pydantic-settings** — one Settings class, no os.getenv scattered in code
- **Type hints** — every function
- **Pydantic validation** — at every external boundary (HTTP requests, tool inputs, webhook payloads)
- **Error handling** — timeouts, retries with backoff on all external calls
- **Structured logging** — structlog or JSON logger, no print statements
- **Code hygiene** — ruff or black formatter, no 600-line files, .env.example
