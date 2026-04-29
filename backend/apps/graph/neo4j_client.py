from __future__ import annotations

from collections import Counter

from django.conf import settings
from neo4j import GraphDatabase

from apps.jobs.models import JobPosting
from apps.skills.models import CanonicalSkill


class SkillGraph:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None) -> None:
        self.driver = GraphDatabase.driver(
            uri or settings.NEO4J_URI,
            auth=(user or settings.NEO4J_USER, password or settings.NEO4J_PASSWORD),
        )

    def close(self) -> None:
        self.driver.close()

    def ensure_constraints(self) -> None:
        statements = [
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:Job) REQUIRE j.id IS UNIQUE",
            "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement)

    def clear(self) -> None:
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def sync_job(self, job: JobPosting) -> None:
        skills = [job_skill.skill.name for job_skill in job.job_skills.select_related("skill")]
        company_id = job.company.external_id if job.company else "unknown"
        company_name = job.company.name if job.company else "Unknown"

        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Company {id: $company_id})
                SET c.name = $company_name
                MERGE (j:Job {id: $job_id})
                SET j.title = $title, j.location = $location, j.remote = $remote
                MERGE (c)-[:POSTED]->(j)
                WITH j
                UNWIND $skills AS skill_name
                MERGE (s:Skill {name: skill_name})
                MERGE (j)-[:REQUIRES]->(s)
                """,
                company_id=company_id,
                company_name=company_name,
                job_id=job.external_id,
                title=job.title,
                location=job.location,
                remote=job.remote_allowed,
                skills=skills,
            )

    def sync_cooccurrences(self) -> int:
        pairs: Counter[tuple[str, str]] = Counter()
        for job in JobPosting.objects.prefetch_related("job_skills__skill"):
            skills = sorted({job_skill.skill.name for job_skill in job.job_skills.all()})
            for index, left in enumerate(skills):
                for right in skills[index + 1 :]:
                    pairs[(left, right)] += 1

        with self.driver.session() as session:
            for (left, right), count in pairs.items():
                session.run(
                    """
                    MERGE (a:Skill {name: $left})
                    MERGE (b:Skill {name: $right})
                    MERGE (a)-[r:OFTEN_WITH]-(b)
                    SET r.count = $count
                    """,
                    left=left,
                    right=right,
                    count=count,
                )

        return len(pairs)

    def related_skills(self, skill_name: str, limit: int = 8) -> list[dict]:
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (:Skill {name: $skill})-[r:OFTEN_WITH]-(related:Skill)
                RETURN related.name AS name, r.count AS count
                ORDER BY r.count DESC, related.name ASC
                LIMIT $limit
                """,
                skill=skill_name,
                limit=limit,
            )
            return [{"name": record["name"], "count": record["count"]} for record in records]

    def skill_graph(self, skill_name: str, limit: int = 8) -> dict[str, list[dict]]:
        related = self.related_skills(skill_name, limit=limit)
        return skill_graph_from_related(skill_name, related)

    def graph_for_jobs(
        self,
        job_ids: list[str],
        seed_skill: str | None = None,
        related_limit: int = 8,
    ) -> dict[str, list[dict]]:
        nodes: dict[str, dict] = {}
        edges: dict[tuple[str, str, str], dict] = {}

        def add_node(node_id: str, label: str, node_type: str) -> None:
            nodes[node_id] = {"id": node_id, "label": label, "type": node_type}

        def add_edge(source: str, target: str, edge_type: str, weight: int = 1) -> None:
            edges[(source, target, edge_type)] = {
                "source": source,
                "target": target,
                "type": edge_type,
                "weight": weight,
            }

        with self.driver.session() as session:
            job_records = session.run(
                """
                MATCH (c:Company)-[:POSTED]->(j:Job)-[:REQUIRES]->(s:Skill)
                WHERE j.id IN $job_ids
                RETURN c.id AS company_id, c.name AS company_name,
                       j.id AS job_id, j.title AS job_title,
                       collect(DISTINCT s.name) AS skills
                """,
                job_ids=job_ids,
            )
            for record in job_records:
                company_node_id = f"company:{record['company_id']}"
                job_node_id = f"job:{record['job_id']}"
                add_node(company_node_id, record["company_name"], "company")
                add_node(job_node_id, record["job_title"], "job")
                add_edge(company_node_id, job_node_id, "POSTED", 1)
                for skill_name in record["skills"]:
                    skill_node_id = f"skill:{skill_name}"
                    add_node(skill_node_id, skill_name, "skill")
                    add_edge(job_node_id, skill_node_id, "REQUIRES", 1)

            if seed_skill:
                related_records = session.run(
                    """
                    MATCH (:Skill {name: $skill})-[r:OFTEN_WITH]-(related:Skill)
                    RETURN related.name AS name, r.count AS count
                    ORDER BY r.count DESC, related.name ASC
                    LIMIT $limit
                    """,
                    skill=seed_skill,
                    limit=related_limit,
                )
                seed_node_id = f"skill:{seed_skill}"
                add_node(seed_node_id, seed_skill, "skill")
                for record in related_records:
                    related_node_id = f"skill:{record['name']}"
                    add_node(related_node_id, record["name"], "skill")
                    add_edge(seed_node_id, related_node_id, "OFTEN_WITH", record["count"])

        return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def local_related_skills(skill_name: str, limit: int = 8) -> list[dict]:
    target = CanonicalSkill.objects.filter(name__iexact=skill_name).first()
    if target is None:
        return []

    target_job_ids = set(target.job_skills.values_list("job_id", flat=True))
    counts: Counter[str] = Counter()
    for job in JobPosting.objects.filter(id__in=target_job_ids).prefetch_related("job_skills__skill"):
        for job_skill in job.job_skills.all():
            name = job_skill.skill.name
            if name != target.name:
                counts[name] += 1

    return [
        {"name": name, "count": count}
        for name, count in counts.most_common(limit)
    ]


def skill_graph_from_related(skill_name: str, related: list[dict]) -> dict:
    if not skill_name:
        return {"nodes": [], "edges": []}

    nodes = [{"id": f"skill:{skill_name}", "label": skill_name, "type": "skill"}]
    edges = []
    seen = {skill_name.casefold()}
    for item in related:
        name = item["name"]
        if name.casefold() in seen:
            continue
        seen.add(name.casefold())
        nodes.append({"id": f"skill:{name}", "label": name, "type": "skill"})
        edges.append(
            {
                "source": f"skill:{skill_name}",
                "target": f"skill:{name}",
                "type": "OFTEN_WITH",
                "weight": item["count"],
            }
        )
    return {"nodes": nodes, "edges": edges}


def local_graph_for_jobs(jobs: list[JobPosting], seed_skill: str | None = None, related_limit: int = 8) -> dict:
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str, str], dict] = {}

    def add_node(node_id: str, label: str, node_type: str) -> None:
        nodes[node_id] = {"id": node_id, "label": label, "type": node_type}

    def add_edge(source: str, target: str, edge_type: str, weight: int = 1) -> None:
        edges[(source, target, edge_type)] = {
            "source": source,
            "target": target,
            "type": edge_type,
            "weight": weight,
        }

    for job in jobs:
        company_id = job.company.external_id if job.company else "unknown"
        company_label = job.company.name if job.company else "Unknown"
        company_node_id = f"company:{company_id}"
        job_node_id = f"job:{job.external_id}"
        add_node(company_node_id, company_label, "company")
        add_node(job_node_id, job.title, "job")
        add_edge(company_node_id, job_node_id, "POSTED", 1)
        for job_skill in job.job_skills.all():
            skill_node_id = f"skill:{job_skill.skill.name}"
            add_node(skill_node_id, job_skill.skill.name, "skill")
            add_edge(job_node_id, skill_node_id, "REQUIRES", 1)

    if seed_skill:
        seed_node_id = f"skill:{seed_skill}"
        add_node(seed_node_id, seed_skill, "skill")
        for item in local_related_skills(seed_skill, related_limit):
            related_node_id = f"skill:{item['name']}"
            add_node(related_node_id, item["name"], "skill")
            add_edge(seed_node_id, related_node_id, "OFTEN_WITH", item["count"])

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def local_skill_graph(skill_name: str, limit: int = 8) -> dict:
    return skill_graph_from_related(skill_name, local_related_skills(skill_name, limit=limit))
