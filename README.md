# SkillScan

SkillScan is a job market search and skill graph platform. It ingests job posting data, extracts normalized skills from unstructured descriptions, indexes postings for fuzzy search, and models job-company-skill relationships in Neo4j.

The app lets you search a role, view matching jobs, click skills in a Market Map, and filter the job list by the selected skills.

## Features

- Search job postings by role, skill, company, or technology.
- Extract and normalize skills from job descriptions.
- Index jobs in Elasticsearch for typo-tolerant search.
- Model companies, jobs, skills, and skill co-occurrences in Neo4j.
- Explore top skills through an interactive Market Map.
- Filter matching jobs by clicking skills in the graph or related skills panel.
- Open original postings from the job cards.

## Stack

### Backend

- Django 5.2
- PostgreSQL 16
- Elasticsearch 8
- Neo4j 5
- Strawberry GraphQL
- spaCy-compatible skill extraction and normalization

### Frontend

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- lucide-react

## Product Flow

1. Search a role such as `software engineer`, `backend engineer`, or `React`.
2. SkillScan returns matching jobs and extracts the top skills from those results.
3. The Market Map shows the role in the center and related skills around it.
4. Clicking a skill selects it and filters the matching job list.
5. The right panel shows selected skills and related skills.
6. Job cards include an external-link action for viewing the original posting.

## Project Structure

```text
SkillScan/
|-- backend/              Django API, ingestion, search, graph, and skill services
|-- frontend/             Next.js app and Market Map UI
|-- data/                 Local development data directory
|-- docker-compose.yml    Backend service stack
|-- README.md
```

## Setup

### Prerequisites

- Docker Desktop
- Node.js
- npm

### Environment Variables

`backend/.env.example` contains the values needed for a local `backend/.env` file.

## Start The Backend

From the repo root:

```powershell
docker compose up --build
```

This starts:

- Django backend: `http://127.0.0.1:8001`
- GraphQL: `http://127.0.0.1:8001/graphql/`
- PostgreSQL: `localhost:55432`
- Elasticsearch: `http://localhost:9200`
- Neo4j browser: `http://localhost:7474`

Load the demo data:

```powershell
docker compose exec backend python manage.py bootstrap_demo --limit 1000
```

## Start The Frontend

In a second terminal:

```powershell
cd frontend
cmd /c npm install
cmd /c npm run dev
```

The frontend runs at `http://localhost:3000/`.

## Useful Commands

Run backend tests:

```powershell
cd backend
python manage.py test tests -v 2
```

Run a frontend production build check:

```powershell
cd frontend
cmd /c npm run build
```

Stop the backend stack:

```powershell
docker compose down
```
## Market Map Preview

A quick look at SkillScan’s presentation-focused workspace, showing the career search flow, matching job results, and interactive skill graph used to explore role-specific technology demand.
<img width="2560" height="1440" alt="skillscan-poster" src="https://github.com/user-attachments/assets/392f1fef-880d-48cc-b08a-ad46d06e06b5" />

