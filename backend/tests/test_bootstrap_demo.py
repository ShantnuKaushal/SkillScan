from unittest.mock import call, patch

from django.core.management import call_command
from django.test import SimpleTestCase


class BootstrapDemoCommandTests(SimpleTestCase):
    def test_runs_demo_pipeline_in_order(self):
        with patch("apps.ingestion.management.commands.bootstrap_demo.call_command") as mocked_call_command, patch(
            "apps.ingestion.management.commands.bootstrap_demo.Command._reset_demo_state"
        ) as reset_demo_state:
            call_command("bootstrap_demo", limit=25, contains=["python", "neo4j"])

        reset_demo_state.assert_called_once_with()
        self.assertEqual(
            mocked_call_command.call_args_list,
            [
                call("prepare_sample", limit=25, contains=["python", "neo4j"]),
                call("ingest_jobs", limit=25),
                call("reindex_jobs"),
                call("sync_graph"),
            ],
        )

    def test_can_keep_existing_demo_state_when_requested(self):
        with patch("apps.ingestion.management.commands.bootstrap_demo.call_command"), patch(
            "apps.ingestion.management.commands.bootstrap_demo.Command._reset_demo_state"
        ) as reset_demo_state:
            call_command("bootstrap_demo", limit=25, no_reset=True)

        reset_demo_state.assert_not_called()
