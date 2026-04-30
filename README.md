README
======
A smart travel planner for suggesting a trip plan according to the user's specific request.

Suppose a friend texts you: "I have two weeks off in July and around $1,500. I want somewhere warm, not too touristy, and I like hiking. Where should I go, when should I book, and what should I expect?"

This system answers that quesiton. An agent that figures out what kind of trip the person actually wants, pulls up what it knows about destinations matching that vibe, checks live conditions, and delivers a real plan to a real channel.

Components
----------
1. **ML classifier:** Build a dataset of 200 travel locations and classify with a trained ML model them according to these categories:
    - *Adventure*
    - *Budget*
    - *Culture*
    - *Family*
    - *Luxury*
    - *Relaxation*
2. **RAG tool:** Retrieve relevant destination content about 10-15 cities in the dataset. These are the *only* cities the planner can recommend in response to the user's prompt.
3. **Agent with three tools:** Destination classifier, RAG retrieval tool, live conditions API (for weather).
4. **Two models, one agent:** Use a weak model for tool arguments and RAG, a strong one for the final synthesis.
5. **Persistence:** One Postgres database for everything, including users and embeddings (pgvector). Use SQLAlchemy for relational models.
6. **Auth:** User signup and login
7. **React frontend:** User interface
8. **Webhook delivery:** Send the trip plan to a real channel, e.g. Discord, Slack, email.
9. **Docker:** Containerise the whole stack (frontend, backend, Postgres database).

Setup
-----
Install Python virtual environment:
```
uv sync
source .venv/bin/activate
```
(To end the session, run `deactivate` or just kill the terminal.)

To run the FastAPI server:
```
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Dataset
-------
### Classifying features
We will prepare a dataset of 200 likely cities and judge them on the following features:
1. **hiking_score** (1–10): quality and quantity of hiking, trekking, and trail-based outdoor activities
2. **beach_score** (1–10): quality, quantity, and accessibility of beaches
3. **cultural_sites_score** (1–10): museums, historical landmarks, architecture, local traditions and heritage
4. **nightlife_score** (1–10): bars, clubs, live music, entertainment scene
5. **family_friendly_score** (1–10): kid-oriented attractions, ease of travel with children, general safety for families
6. **luxury_infrastructure_score** (1–10): high-end hotels, fine dining, spas, exclusive experiences
7. **avg_accom_cost** (USD):  average nightly accommodation cost, mid-range
8. **avg_daily_expense** (USD): food, transport, activities per day, excluding accommodation
9. **safety_score** (1–10): personal safety for tourists, low crime, political stability
10. **remoteness_score** (1–10): how off-the-beaten-path it is, inverse of mass tourism volume

The dataset is `data/destinations.csv`.

### Labelling rubric
An LLM will assess each city in the dataset and apply one of the following **labels** to it:
* **Adventure:** hiking_score is the dominant feature. Remote. Defined by active outdoor exploration.
* **Relaxation:** beach_score is the dominant feature. Nightlife not excessive. Defined by unwinding.
* **Culture:** cultural_sites_score is the dominant feature. Defined by museums, history, heritage.
* **Budget:** accommodation is reasonable, daily expenses are low. No single other feature overwhelmingly dominates.
* **Luxury:** high luxury_infrastructure_score and high accommodation cost. Defined by premium experiences.
* **Family:** family_friendly_score is the dominant feature with high safety. Easy and safe for kids.

In case of a tiebreaker, when multiple styles apply, pick what a travel magazine would file it under.

Database
--------
We create the Postgres database from the Docker container as follows:
```
docker run -d \
  --name travel-postgres \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=travel_planner \
  -v travel_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16
```

Afterwards, we **run** it with:
```
docker start travel-postgres
```
