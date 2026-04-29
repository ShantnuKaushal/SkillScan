import csv
from pathlib import Path
import shutil
from unittest import TestCase

from apps.ingestion.services.sampling import create_deterministic_sample


class SamplingTests(TestCase):
    def setUp(self):
        self.tmpdir = Path(__file__).resolve().parent / ".tmp_sampling"
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)
        self.tmpdir.mkdir()

    def tearDown(self):
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)

    def test_creates_stable_first_n_sample_with_header(self):
        source = self.tmpdir / "postings.csv"
        target = self.tmpdir / "sample.csv"
        with source.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["job_id", "title"])
            writer.writeheader()
            writer.writerow({"job_id": "3", "title": "Third"})
            writer.writerow({"job_id": "1", "title": "First"})
            writer.writerow({"job_id": "2", "title": "Second"})

        count = create_deterministic_sample(source, target, limit=2)

        self.assertEqual(count, 2)
        with target.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            rows,
            [
                {"job_id": "3", "title": "Third"},
                {"job_id": "1", "title": "First"},
            ],
        )

    def test_rejects_non_positive_limit(self):
        source = self.tmpdir / "postings.csv"
        target = self.tmpdir / "sample.csv"
        source.write_text("job_id,title\n1,Backend Engineer\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            create_deterministic_sample(source, target, limit=0)

    def test_filters_rows_by_search_terms_when_requested(self):
        source = self.tmpdir / "postings.csv"
        target = self.tmpdir / "sample.csv"
        with source.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["job_id", "title", "description"])
            writer.writeheader()
            writer.writerow({"job_id": "1", "title": "Marketing Coordinator", "description": "Adobe campaigns"})
            writer.writerow({"job_id": "2", "title": "Backend Engineer", "description": "Python and Django APIs"})
            writer.writerow({"job_id": "3", "title": "Data Engineer", "description": "Spark and SQL pipelines"})

        count = create_deterministic_sample(source, target, limit=2, include_terms=["python", "sql"])

        self.assertEqual(count, 2)
        with target.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual([row["job_id"] for row in rows], ["2", "3"])
