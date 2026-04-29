from __future__ import annotations

import strawberry
from django.db.models import Q

from apps.graph.neo4j_client import local_related_skills
from apps.jobs.models import JobPosting


@strawberry.type
class SkillType:
    name: str
    original_phrase: str


@strawberry.type
class JobResultType:
    id: str
    title: str
    company: str
    location: str
    remote_allowed: bool
    work_type: str
    experience_level: str
    description_snippet: str
    posting_url: str
    score: float
    match_reason: str
    skills: list[SkillType]


@strawberry.type
class RelatedSkillType:
    name: str
    count: int


@strawberry.type
class SearchPayload:
    query: str
    corrected_query: str
    total: int
    jobs: list[JobResultType]
    related_skills: list[RelatedSkillType]


@strawberry.type
class Query:
    @strawberry.field
    def search_jobs(
        self,
        query: str,
        skill: str | None = None,
        location: str | None = None,
        remote: bool | None = None,
        limit: int = 10,
    ) -> SearchPayload:
        corrected_query = _correct_query(query)
        queryset = JobPosting.objects.select_related("company").prefetch_related("job_skills__skill")

        terms = [term for term in corrected_query.split() if len(term) > 1]
        if terms:
            term_filter = Q()
            for term in terms:
                term_filter |= Q(title__icontains=term)
                term_filter |= Q(description__icontains=term)
                term_filter |= Q(company__name__icontains=term)
                term_filter |= Q(job_skills__skill__name__icontains=term)
            queryset = queryset.filter(term_filter)

        if skill:
            queryset = queryset.filter(job_skills__skill__name__iexact=skill)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if remote is not None:
            queryset = queryset.filter(remote_allowed=remote)

        queryset = queryset.distinct()
        total = queryset.count()
        jobs = [_to_job_result(job, corrected_query) for job in queryset[:limit]]

        related_seed = skill or _first_skill_from_jobs(jobs) or "Python"
        related = [
            RelatedSkillType(name=item["name"], count=item["count"])
            for item in local_related_skills(related_seed)
        ]
        return SearchPayload(
            query=query,
            corrected_query=corrected_query,
            total=total,
            jobs=jobs,
            related_skills=related,
        )


schema = strawberry.Schema(query=Query)


def _to_job_result(job: JobPosting, query: str) -> JobResultType:
    skills = [
        SkillType(name=job_skill.skill.name, original_phrase=job_skill.original_phrase)
        for job_skill in job.job_skills.all()
    ]
    matched = [skill.name for skill in skills if skill.name.casefold() in query.casefold()]
    if not matched:
        matched = [skill.name for skill in skills[:3]]
    match_reason = "Matched " + ", ".join(matched) if matched else "Matched title and description text"

    return JobResultType(
        id=job.external_id,
        title=job.title,
        company=job.company.name if job.company else "Unknown",
        location=job.location,
        remote_allowed=job.remote_allowed,
        work_type=job.work_type,
        experience_level=job.experience_level,
        description_snippet=_snippet(job.description),
        posting_url=job.posting_url,
        score=1.0,
        match_reason=match_reason,
        skills=skills,
    )


def _snippet(text: str, length: int = 180) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= length:
        return compact
    return compact[: length - 1].rstrip() + "…"


def _correct_query(query: str) -> str:
    replacements = {
        "pythn": "python",
        "softwere": "software",
        "enginer": "engineer",
        "develoepr": "developer",
    }
    words = query.split()
    return " ".join(replacements.get(word.casefold(), word) for word in words)


def _first_skill_from_jobs(jobs: list[JobResultType]) -> str | None:
    for job in jobs:
        if job.skills:
            return job.skills[0].name
    return None
