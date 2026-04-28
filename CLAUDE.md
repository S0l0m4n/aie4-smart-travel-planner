# CLAUDE.md

### Introduction
You are a coding agent that will write code as I direct you to. There is a spec file that sets the scene, generated from a previous chat that I had with Claude. Read that first before continuing. (Location: docs/SPEC.md)

All code you suggest will be made in this Git repo. Wait for me to commit changes or to tell you to commit before proceeding onto the next task, unless we're iterating on the current code.

Follow all best practices in software development for project folder structure, preserving secrets, but don't overdo it. I need to understand all code that is written, so prefer simplicity over brevity or elegance.

Do not spawn unnecessary files. You can generate extra documentation files if you need to – I might not track these.

When I ask you a question in VS Code, I want you to directly answer it, not just suggest a code edit.

Try to keep Git diffs minimal between commits. Only change something that is working when you need to change it to support the new feature, or if the current way of doing it is dragging us down or a much better solution is available.

Never end a code file, e.g. `*.py`, with an empty line.

Do not run any script without expicit permission first. In particular, do not run any script that you just coded; let me review it first outside of our chat.

---

### Project-Specific Rules

- **Respect the current phase.** Do not add Phase 2/3 concerns (auth, webhooks, extra tables, Docker, tests) until told. But write Phase 1 code so it won't need restructuring later.
- **Async everything.** async def, await, AsyncSession, httpx.AsyncClient, ainvoke/astream. Never requests, never time.sleep.
- **Lifespan singletons.** DB engine, joblib model, embedding model, LLM clients, compiled graph — created once in FastAPI lifespan, stored on app.state. Never instantiated in route handlers or as module-level globals.
- **Dependency injection.** All shared resources via Depends(). No globals, no in-handler instantiation.
- **One Settings class.** pydantic-settings in config.py. No os.getenv() anywhere else. No magic strings.
- **Type hints on every function.** Pydantic models on every external boundary. Validate at the edge only.
- **Error handling.** Timeout + retry with backoff on every external call. Tool failures return structured errors, never raise exceptions that crash the agent.
- **Structured logging.** structlog or JSON stdlib logger. No print().
- **ML Pipeline.** Preprocessing inside the sklearn Pipeline. Never scale/transform outside it. Pin all seeds.
- **Agent flow is sequential, not ReAct.** parse → classify → rewrite → retrieve → live_conditions → synthesize. Only branching: ask followup if required fields are missing after parse.