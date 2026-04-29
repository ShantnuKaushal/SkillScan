from django.test import SimpleTestCase

from apps.ingestion.management.commands.ingest_jobs import parse_remote_allowed


class IngestJobsCommandTests(SimpleTestCase):
    def test_parses_kaggle_remote_allowed_values(self):
        self.assertTrue(parse_remote_allowed("1"))
        self.assertTrue(parse_remote_allowed("1.0"))
        self.assertTrue(parse_remote_allowed("true"))
        self.assertTrue(parse_remote_allowed("YES"))
        self.assertFalse(parse_remote_allowed(""))
        self.assertFalse(parse_remote_allowed("0"))
        self.assertFalse(parse_remote_allowed("0.0"))
