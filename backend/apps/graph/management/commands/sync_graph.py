from django.core.management.base import BaseCommand

from apps.graph.neo4j_client import SkillGraph
from apps.jobs.models import JobPosting


class Command(BaseCommand):
    help = "Sync companies, jobs, skills, and skill co-occurrences into Neo4j."

    def handle(self, *args, **options):
        graph = SkillGraph()
        try:
            graph.ensure_constraints()
            jobs = JobPosting.objects.select_related("company").prefetch_related("job_skills__skill")
            count = 0
            for job in jobs:
                graph.sync_job(job)
                count += 1
            pair_count = graph.sync_cooccurrences()
        finally:
            graph.close()

        self.stdout.write(self.style.SUCCESS(f"Synced {count} jobs and {pair_count} skill co-occurrence pairs."))
