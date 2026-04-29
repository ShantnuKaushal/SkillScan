from unittest import TestCase

from apps.skills.services.normalization import SkillNormalizer


class SkillNormalizerTests(TestCase):
    def test_normalizes_common_skill_aliases_to_canonical_names(self):
        normalizer = SkillNormalizer()

        self.assertEqual(normalizer.normalize_term("ReactJS"), "React")
        self.assertEqual(normalizer.normalize_term("react.js"), "React")
        self.assertEqual(normalizer.normalize_term("nodejs"), "Node.js")
        self.assertEqual(normalizer.normalize_term("postgres"), "PostgreSQL")

    def test_extracts_unique_canonical_skills_from_description(self):
        normalizer = SkillNormalizer()

        matches = normalizer.extract_skills(
            "We build Python services with Django REST APIs, Postgres, Docker, and React.js."
        )

        labels = [match.canonical for match in matches]
        self.assertEqual(labels, ["Python", "Django", "PostgreSQL", "Docker", "React"])

    def test_reports_original_phrase_for_each_normalized_skill(self):
        normalizer = SkillNormalizer()

        matches = normalizer.extract_skills("Experience with ReactJS and Postgres required.")
        phrase_by_skill = {match.canonical: match.original for match in matches}

        self.assertEqual(phrase_by_skill["React"], "ReactJS")
        self.assertEqual(phrase_by_skill["PostgreSQL"], "Postgres")
