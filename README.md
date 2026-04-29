# SkillScan

SkillScan is a local job market search and skill graph platform. It ingests LinkedIn job posting data, extracts normalized skills from unstructured descriptions, indexes postings for typo-tolerant search, and models job-company-skill relationships in Neo4j.

## Stack

- Django 5.2 and Django ORM for ingestion, admin, relational models, and GraphQL.
- PostgreSQL for canonical companies, jobs, skills, and ingestion metadata.
- spaCy-compatible normalization services for skill extraction.
- Elasticsearch for fuzzy job search.
- Neo4j for relationship discovery.
- Strawberry GraphQL for the frontend API.
- Next.js, React, and Tailwind for the UI.

## Local Data

Raw Kaggle files live under `data/raw/` and are intentionally gitignored. The expected files are:

- `data/raw/postings.csv`
- `data/raw/companies/companies.csv`
- `data/raw/jobs/job_skills.csv`
- `data/raw/mappings/skills.csv`

Generated samples live under `data/samples/` and are also gitignored.

## Start The Backend

From the repo root:

```powershell
docker compose up --build
```

That starts:

- Django backend: `http://127.0.0.1:8001`
- GraphQL: `http://127.0.0.1:8001/graphql/`
- PostgreSQL: `localhost:55432`
- Elasticsearch: `http://localhost:9200`
- Neo4j browser: `http://localhost:7474`

The backend reads `backend/.env`, but Docker Compose overrides service hostnames inside containers. That is why local values can use `localhost`, while the Docker backend connects to `postgres`, `elasticsearch`, and `neo4j`.

## Start The Frontend

In a second terminal:

```powershell
cd frontend
cmd /c npm install
cmd /c npm run dev
```

The frontend runs at `http://localhost:3000/`.

## Backend Commands

Run Django commands through the backend container:

```powershell
docker compose exec backend python manage.py prepare_sample --limit 1000 --contains python django react data backend sql elasticsearch neo4j
docker compose exec backend python manage.py ingest_jobs --limit 1000
docker compose exec backend python manage.py reindex_jobs
docker compose exec backend python manage.py sync_graph
```

Run backend tests:

```powershell
docker compose exec backend python manage.py test tests -v 1
```

Stop everything:

```powershell
docker compose down
```
