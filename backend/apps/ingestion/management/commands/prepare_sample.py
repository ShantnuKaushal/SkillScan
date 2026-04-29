from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.services.sampling import create_deterministic_sample


class Command(BaseCommand):
    help = "Create a deterministic local sample from the raw Kaggle postings CSV."

    def add_arguments(self, parser):
        parser.add_argument("--input", default=str(settings.DATA_RAW_DIR / "postings.csv"))
        parser.add_argument("--output", default=str(settings.DATA_SAMPLE_DIR / "postings_1000.csv"))
        parser.add_argument("--limit", type=int, default=1000)
        parser.add_argument(
            "--contains",
            nargs="*",
            default=[],
            help="Only include rows whose title, description, company, or skills text contains one of these terms.",
        )

    def handle(self, *args, **options):
        source = Path(options["input"])
        output = Path(options["output"])
        if not source.exists():
            raise CommandError(f"Input CSV does not exist: {source}")

        count = create_deterministic_sample(source, output, options["limit"], include_terms=options["contains"])
        self.stdout.write(self.style.SUCCESS(f"Wrote {count} rows to {output}"))
