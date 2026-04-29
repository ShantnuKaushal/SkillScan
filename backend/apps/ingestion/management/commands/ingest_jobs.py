from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.ingestion.models import IngestionRun
from apps.jobs.models import Company, JobPosting
from apps.skills.models import CanonicalSkill, JobSkill, SkillAlias
from apps.skills.services.normalization import DEFAULT_SKILL_ALIASES, SkillNormalizer


class Command(BaseCommand):
    help = "Ingest Kaggle LinkedIn job postings into PostgreSQL and extract normalized skills."

    def add_arguments(self, parser):
        parser.add_argument("--postings", default=str(settings.DATA_SAMPLE_DIR / "postings_1000.csv"))
        parser.add_argument("--companies", default=str(settings.DATA_RAW_DIR / "companies" / "companies.csv"))
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **options):
        postings_path = Path(options["postings"])
        companies_path = Path(options["companies"])
        if not postings_path.exists():
            raise CommandError(f"Postings CSV does not exist: {postings_path}")
        if not companies_path.exists():
            raise CommandError(f"Companies CSV does not exist: {companies_path}")

        run = IngestionRun.objects.create(
            source_name=str(postings_path),
            row_limit=options["limit"],
        )
        try:
            self._seed_skill_aliases()
            company_ids = self._collect_company_ids(postings_path, options["limit"])
            companies_loaded = self._load_companies(companies_path, company_ids)
            jobs_loaded, skills_linked = self._load_jobs(postings_path, options["limit"])
            run.status = "completed"
            run.companies_loaded = companies_loaded
            run.jobs_loaded = jobs_loaded
            run.skills_linked = skills_linked
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "companies_loaded", "jobs_loaded", "skills_linked", "finished_at"])
        except Exception as exc:
            run.status = "failed"
            run.message = str(exc)
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "message", "finished_at"])
            raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {jobs_loaded} jobs, {companies_loaded} companies, and {skills_linked} job-skill links."
            )
        )

    def _seed_skill_aliases(self) -> None:
        for canonical_name, aliases in DEFAULT_SKILL_ALIASES.items():
            skill, _ = CanonicalSkill.objects.get_or_create(name=canonical_name)
            for alias in aliases:
                SkillAlias.objects.get_or_create(skill=skill, alias=alias)

    def _collect_company_ids(self, path: Path, limit: int | None) -> set[str]:
        company_ids: set[str] = set()
        loaded = 0
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if limit is not None and loaded >= limit:
                    break
                job_id = row.get("job_id", "").strip()
                title = row.get("title", "").strip()
                if not job_id or not title:
                    continue
                company_id = _normalize_external_id(row.get("company_id", ""))
                if company_id:
                    company_ids.add(company_id)
                loaded += 1
        return company_ids

    def _load_companies(self, path: Path, allowed_company_ids: set[str]) -> int:
        loaded = 0
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                company_id = _normalize_external_id(row.get("company_id", ""))
                name = row.get("name", "").strip()
                if allowed_company_ids and company_id not in allowed_company_ids:
                    continue
                if not company_id or not name:
                    continue
                Company.objects.update_or_create(
                    external_id=company_id,
                    defaults={
                        "name": name,
                        "description": row.get("description", ""),
                        "city": row.get("city", ""),
                        "state": row.get("state", ""),
                        "country": row.get("country", ""),
                        "url": row.get("url", ""),
                    },
                )
                loaded += 1
        return loaded

    def _load_jobs(self, path: Path, limit: int | None) -> tuple[int, int]:
        normalizer = SkillNormalizer()
        jobs_loaded = 0
        skills_linked = 0

        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if limit is not None and jobs_loaded >= limit:
                    break

                job_id = row.get("job_id", "").strip()
                title = row.get("title", "").strip()
                if not job_id or not title:
                    continue

                company = None
                company_id = _normalize_external_id(row.get("company_id", ""))
                if company_id:
                    company = Company.objects.filter(external_id=company_id).first()
                if company is None and row.get("company_name", "").strip():
                    company_name = row.get("company_name", "").strip()
                    company, _ = Company.objects.get_or_create(
                        external_id=f"inline:{company_name.casefold()}",
                        defaults={"name": company_name},
                    )

                description = row.get("description", "") or ""
                skills_description = row.get("skills_desc", "") or ""
                job, _ = JobPosting.objects.update_or_create(
                    external_id=job_id,
                    defaults={
                        "company": company,
                        "title": title,
                        "description": description,
                        "location": row.get("location", ""),
                        "work_type": row.get("formatted_work_type", "") or row.get("work_type", ""),
                        "experience_level": row.get("formatted_experience_level", ""),
                        "remote_allowed": row.get("remote_allowed", "").strip() in {"1", "true", "True"},
                        "posting_url": row.get("job_posting_url", ""),
                        "listed_time": row.get("listed_time", ""),
                        "raw_payload": row,
                    },
                )

                for match in normalizer.extract_skills(f"{title}\n{description}\n{skills_description}"):
                    skill, _ = CanonicalSkill.objects.get_or_create(name=match.canonical)
                    _, created = JobSkill.objects.get_or_create(
                        job=job,
                        skill=skill,
                        defaults={"original_phrase": match.original},
                    )
                    if created:
                        skills_linked += 1

                jobs_loaded += 1

        return jobs_loaded, skills_linked


def _normalize_external_id(value: str) -> str:
    cleaned = (value or "").strip()
    if cleaned.endswith(".0"):
        cleaned = cleaned[:-2]
    return cleaned
