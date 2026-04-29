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
