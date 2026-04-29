from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.graph.neo4j_client import SkillGraph
from apps.ingestion.models import IngestionRun
from apps.jobs.models import Company, JobPosting
from apps.search.elastic import JobSearchIndex
from apps.skills.models import JobSkill


DEFAULT_TERMS = ["python", "django", "react", "data", "backend", "sql", "elasticsearch", "neo4j"]


class Command(BaseCommand):
    help = "Prepare, ingest, index, and graph-sync a deterministic local demo dataset."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=1000)
        parser.add_argument("--no-reset", action="store_true", help="Keep existing local demo data before loading.")
        parser.add_argument(
            "--contains",
            nargs="*",
            default=DEFAULT_TERMS,
            help="Terms used when selecting demo rows from the raw postings CSV.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        contains = options["contains"]
        if not options["no_reset"]:
            self._reset_demo_state()

        self.stdout.write(f"Preparing demo sample with up to {limit} postings...")
        call_command("prepare_sample", limit=limit, contains=contains)

        self.stdout.write("Loading jobs, companies, and normalized skills into PostgreSQL...")
        call_command("ingest_jobs", limit=limit)

        self.stdout.write("Indexing jobs into Elasticsearch...")
        call_command("reindex_jobs")

        self.stdout.write("Syncing jobs, companies, skills, and co-occurrences into Neo4j...")
        call_command("sync_graph")

        self.stdout.write(self.style.SUCCESS("SkillScan demo data is ready."))

    def _reset_demo_state(self) -> None:
        self.stdout.write("Resetting previous local demo data...")
        JobSkill.objects.all().delete()
        JobPosting.objects.all().delete()
        Company.objects.all().delete()
        IngestionRun.objects.all().delete()

        try:
            JobSearchIndex().reset_index()
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Could not reset Elasticsearch index before load: {exc}"))

        graph = None
        try:
            graph = SkillGraph()
            graph.clear()
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Could not reset Neo4j graph before load: {exc}"))
        finally:
            if graph is not None:
                graph.close()
