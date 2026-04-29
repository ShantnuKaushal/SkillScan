from django.core.management.base import BaseCommand

from apps.jobs.models import JobPosting
from apps.search.elastic import JobSearchIndex


class Command(BaseCommand):
    help = "Index ingested jobs into Elasticsearch."

    def handle(self, *args, **options):
        index = JobSearchIndex()
        index.ensure_index()
        count = 0
        for job in JobPosting.objects.select_related("company").prefetch_related("job_skills__skill"):
            index.index_job(job)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Indexed {count} jobs."))
