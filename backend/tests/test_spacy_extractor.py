from unittest import TestCase

from apps.skills.services.spacy_extractor import SpacySkillExtractor


class SpacySkillExtractorTests(TestCase):
    def test_extracts_longest_skill_phrase_with_spacy_phrase_matcher(self):
        extractor = SpacySkillExtractor(
            {
                "Django": ("django", "django rest api", "django rest apis"),
                "PostgreSQL": ("postgres",),
                "Docker": ("containerized deployments",),
            }
        )

        matches = extractor.extract(
            "Experience building Django REST APIs with Postgres and containerized deployments."
        )

        self.assertEqual(
            [(match.canonical, match.original) for match in matches],
            [
                ("Django", "Django REST APIs"),
                ("PostgreSQL", "Postgres"),
                ("Docker", "containerized deployments"),
            ],
        )
