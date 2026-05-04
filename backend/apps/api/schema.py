from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

import strawberry
from django.db.models import Q

from apps.graph.neo4j_client import SkillGraph, local_related_skills, local_skill_graph
from apps.jobs.models import JobPosting
from apps.search.elastic import JobSearchIndex
from apps.skills.services.normalization import SkillNormalizer


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
class MarketSkillType:
    name: str
    count: int
    selected: bool


@strawberry.type
class RecommendedSkillType:
    name: str
    count: int
    example_job_count: int
    preview_jobs: list[JobResultType]


@strawberry.type
class GraphNodeType:
    id: str
    label: str
    type: str


@strawberry.type
class GraphEdgeType:
    source: str
    target: str
    type: str
    weight: int


@strawberry.type
class GraphPayload:
    nodes: list[GraphNodeType]
    edges: list[GraphEdgeType]


@strawberry.type
class SearchPayload:
    query: str
    corrected_query: str
    selected_skill: str
    total: int
    jobs: list[JobResultType]
    related_skills: list[RelatedSkillType]
    graph: GraphPayload


@strawberry.type
class SkillGraphPayload:
    selected_skill: str
    related_skills: list[RelatedSkillType]
    graph: GraphPayload


@strawberry.type
class CareerMapPayload:
    query: str
    corrected_query: str
    total: int
    selected_skills: list[str]
    jobs: list[JobResultType]
    market_skills: list[MarketSkillType]
    recommended_skills: list[RecommendedSkillType]
    graph: GraphPayload


@dataclass(frozen=True)
class SearchResult:
    total: int
    jobs: list[JobPosting]
    score_by_external_id: dict[str, float]


@strawberry.type
class Query:
    @strawberry.field
    def career_map(
        self,
        query: str,
        selected_skills: list[str] | None = None,
        known_skills: list[str] | None = None,
        remote: bool | None = None,
        limit: int = 20,
    ) -> CareerMapPayload:
        bounded_limit = max(1, min(limit, 50))
        corrected_query = _correct_query(query)
        normalized_selected_skills = _normalize_selected_skills(
            selected_skills if selected_skills is not None else known_skills or []
        )
        search_result = _search_with_elasticsearch(
            corrected_query,
            skill=None,
            location=None,
            remote=remote,
            limit=bounded_limit,
        )
        if search_result is None:
            search_result = _search_with_database(
                corrected_query,
                skill=None,
                location=None,
                remote=remote,
                limit=bounded_limit,
            )

        jobs = [
            _to_job_result(job, corrected_query, search_result.score_by_external_id.get(job.external_id, 1.0))
            for job in search_result.jobs
        ]
        market_skills = _market_skills(jobs, normalized_selected_skills)
        recommended_skills = _recommended_skills(jobs, normalized_selected_skills, corrected_query)
        graph_payload = _career_graph(jobs, normalized_selected_skills, market_skills, recommended_skills)

        return CareerMapPayload(
            query=query,
            corrected_query=corrected_query,
            total=search_result.total,
            selected_skills=normalized_selected_skills,
            jobs=jobs,
            market_skills=market_skills,
            recommended_skills=recommended_skills,
            graph=GraphPayload(
                nodes=[
                    GraphNodeType(id=node["id"], label=node["label"], type=node["type"])
                    for node in graph_payload["nodes"]
                ],
                edges=[
                    GraphEdgeType(
                        source=edge["source"],
                        target=edge["target"],
                        type=edge["type"],
                        weight=edge["weight"],
                    )
                    for edge in graph_payload["edges"]
                ],
            ),
        )

    @strawberry.field
    def search_jobs(
        self,
        query: str,
        skill: str | None = None,
        location: str | None = None,
        remote: bool | None = None,
        limit: int = 10,
    ) -> SearchPayload:
        bounded_limit = max(1, min(limit, 50))
        corrected_query = _correct_query(query)
        search_result = _search_with_elasticsearch(
            corrected_query,
            skill=skill,
            location=location,
            remote=remote,
            limit=bounded_limit,
        )
        if search_result is None:
            search_result = _search_with_database(
                corrected_query,
                skill=skill,
                location=location,
                remote=remote,
                limit=bounded_limit,
            )

        jobs = [
            _to_job_result(job, corrected_query, search_result.score_by_external_id.get(job.external_id, 1.0))
            for job in search_result.jobs
        ]
        selected_skill = _selected_skill_for_search(skill, corrected_query, jobs)
        related_items, graph_payload = _graph_context(selected_skill)

        return SearchPayload(
            query=query,
            corrected_query=corrected_query,
            selected_skill=selected_skill,
            total=search_result.total,
            jobs=jobs,
            related_skills=[RelatedSkillType(name=item["name"], count=item["count"]) for item in related_items],
            graph=GraphPayload(
                nodes=[
                    GraphNodeType(id=node["id"], label=node["label"], type=node["type"])
                    for node in graph_payload["nodes"]
                ],
                edges=[
                    GraphEdgeType(
                        source=edge["source"],
                        target=edge["target"],
                        type=edge["type"],
                        weight=edge["weight"],
                    )
                    for edge in graph_payload["edges"]
                ],
            ),
        )

    @strawberry.field
    def skill_graph(self, skill: str) -> SkillGraphPayload:
        selected_skill = SkillNormalizer().normalize_term(skill) or skill.strip()
        related_items, graph_payload = _graph_context(selected_skill)
        return SkillGraphPayload(
            selected_skill=selected_skill,
            related_skills=[RelatedSkillType(name=item["name"], count=item["count"]) for item in related_items],
            graph=GraphPayload(
                nodes=[
                    GraphNodeType(id=node["id"], label=node["label"], type=node["type"])
                    for node in graph_payload["nodes"]
                ],
                edges=[
                    GraphEdgeType(
                        source=edge["source"],
                        target=edge["target"],
                        type=edge["type"],
                        weight=edge["weight"],
                    )
                    for edge in graph_payload["edges"]
                ],
            ),
        )


schema = strawberry.Schema(query=Query)


def _search_with_elasticsearch(
    query: str,
    skill: str | None,
    location: str | None,
    remote: bool | None,
    limit: int,
) -> SearchResult | None:
    try:
        total, hits = JobSearchIndex().search(
            query=query,
            remote=remote,
            skill=skill,
            location=location,
            size=limit,
        )
    except Exception:
        return None

    external_ids = [str(hit["id"]) for hit in hits if hit.get("id")]
    if not external_ids:
        return SearchResult(total=total, jobs=[], score_by_external_id={})

    jobs_by_external_id = {
        job.external_id: job
        for job in _base_job_queryset().filter(external_id__in=external_ids)
    }
    ordered_jobs = [jobs_by_external_id[external_id] for external_id in external_ids if external_id in jobs_by_external_id]
    score_by_external_id = {str(hit["id"]): float(hit.get("score") or 1.0) for hit in hits if hit.get("id")}
    return SearchResult(total=total, jobs=ordered_jobs, score_by_external_id=score_by_external_id)


def _search_with_database(
    query: str,
    skill: str | None,
    location: str | None,
    remote: bool | None,
    limit: int,
) -> SearchResult:
    queryset = _base_job_queryset()
    terms = [term for term in query.split() if len(term) > 1]
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
    jobs = list(queryset[:limit])
    return SearchResult(total=total, jobs=jobs, score_by_external_id={job.external_id: 1.0 for job in jobs})


def _base_job_queryset():
    return JobPosting.objects.select_related("company").prefetch_related("job_skills__skill")


def _graph_context(seed_skill: str) -> tuple[list[dict], dict]:
    if seed_skill:
        graph = None
        try:
            graph = SkillGraph()
            related = graph.related_skills(seed_skill)
            graph_payload = graph.skill_graph(seed_skill)
            return related, graph_payload
        except Exception:
            return local_related_skills(seed_skill), local_skill_graph(seed_skill)
        finally:
            if graph is not None:
                graph.close()
    return [], {"nodes": [], "edges": []}


def _normalize_selected_skills(skills: list[str]) -> list[str]:
    normalizer = SkillNormalizer()
    normalized: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        candidate = normalizer.normalize_term(skill) or skill.strip()
        if not candidate:
            continue
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(candidate)
    return normalized


def _market_skills(jobs: list[JobResultType], selected_skills: list[str], limit: int = 12) -> list[MarketSkillType]:
    selected_keys = {skill.casefold() for skill in selected_skills}
    counts = _skill_counts(jobs)
    return [
        MarketSkillType(name=name, count=count, selected=name.casefold() in selected_keys)
        for name, count in counts.most_common(limit)
    ]


def _recommended_skills(
    jobs: list[JobResultType],
    selected_skills: list[str],
    query: str,
    limit: int = 6,
) -> list[RecommendedSkillType]:
    selected_keys = {skill.casefold() for skill in selected_skills}
    scored: list[tuple[str, int, list[JobResultType]]] = []
    for name, count in _skill_counts(jobs).most_common():
        if name.casefold() in selected_keys:
            continue
        preview_jobs = _preview_jobs_for_skill(jobs, name, selected_keys)
        if not preview_jobs:
            continue
        scored.append((name, count, preview_jobs))

    scored.sort(key=lambda item: (-len(item[2]), -item[1], item[0].casefold()))
    return [
        RecommendedSkillType(
            name=name,
            count=len(preview_jobs),
            example_job_count=len(preview_jobs),
            preview_jobs=[
                _job_with_match_reason(job, query, f"Adds {name} to your selected skill set")
                for job in preview_jobs[:3]
            ],
        )
        for name, count, preview_jobs in scored[:limit]
    ]


def _preview_jobs_for_skill(
    jobs: list[JobResultType],
    skill_name: str,
    selected_keys: set[str],
) -> list[JobResultType]:
    preview_jobs: list[JobResultType] = []
    for job in jobs:
        job_skill_keys = {skill.name.casefold() for skill in job.skills}
        if skill_name.casefold() not in job_skill_keys:
            continue
        if selected_keys and not selected_keys.issubset(job_skill_keys):
            continue
        preview_jobs.append(job)
    return preview_jobs


def _career_graph(
    jobs: list[JobResultType],
    selected_skills: list[str],
    market_skills: list[MarketSkillType],
    recommended_skills: list[RecommendedSkillType],
) -> dict:
    selected_keys = {skill.casefold() for skill in selected_skills}
    recommended_keys = {skill.name.casefold() for skill in recommended_skills}
    visible_names = [item.name for item in market_skills[:10]]
    visible_keys = {name.casefold() for name in visible_names}

    nodes = []
    for name in visible_names:
        node_type = "selectedSkill" if name.casefold() in selected_keys else "recommendedSkill" if name.casefold() in recommended_keys else "marketSkill"
        nodes.append({"id": f"skill:{name}", "label": name, "type": node_type})

    edge_counts: Counter[tuple[str, str]] = Counter()
    for job in jobs:
        names = sorted({skill.name for skill in job.skills if skill.name.casefold() in visible_keys})
        for left, right in combinations(names, 2):
            edge_counts[(left, right)] += 1

    edges = [
        {
            "source": f"skill:{left}",
            "target": f"skill:{right}",
            "type": "SELECTED_WITH" if left.casefold() in selected_keys or right.casefold() in selected_keys else "OFTEN_WITH",
            "weight": count,
        }
        for (left, right), count in edge_counts.most_common(14)
    ]
    return {"nodes": nodes, "edges": edges}


def _skill_counts(jobs: list[JobResultType]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for job in jobs:
        for name in {skill.name for skill in job.skills}:
            counts[name] += 1
    return counts


def _job_with_match_reason(job: JobResultType, query: str, match_reason: str) -> JobResultType:
    return JobResultType(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        remote_allowed=job.remote_allowed,
        work_type=job.work_type,
        experience_level=job.experience_level,
        description_snippet=job.description_snippet,
        posting_url=job.posting_url,
        score=job.score,
        match_reason=match_reason or f"Matched {query}",
        skills=job.skills,
    )


def _to_job_result(job: JobPosting, query: str, score: float) -> JobResultType:
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
        score=score,
        match_reason=match_reason,
        skills=skills,
    )


def _snippet(text: str, length: int = 180) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= length:
        return compact
    return compact[: length - 1].rstrip() + "..."


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


def _first_skill_from_query(query: str) -> str | None:
    matches = SkillNormalizer().extract_skills(query)
    return matches[0].canonical if matches else None


def _selected_skill_for_search(skill: str | None, query: str, jobs: list[JobResultType]) -> str:
    if not jobs:
        return ""
    return skill or _first_skill_from_query(query) or _first_skill_from_jobs(jobs) or ""
