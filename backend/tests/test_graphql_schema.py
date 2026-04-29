from django.test import TestCase

from apps.api.schema import schema
from apps.jobs.models import Company, JobPosting
from apps.skills.models import CanonicalSkill, JobSkill


class GraphQLSchemaTests(TestCase):
    def test_search_jobs_returns_corrected_query_jobs_and_related_skills(self):
        company = Company.objects.create(external_id="stripe", name="Stripe")
        job = JobPosting.objects.create(
            external_id="job-1",
            company=company,
            title="Backend Engineer, Python Platform",
            description="Build Python services with Django and PostgreSQL.",
            location="Remote",
            remote_allowed=True,
        )
        python = CanonicalSkill.objects.create(name="Python")
        django = CanonicalSkill.objects.create(name="Django")
        JobSkill.objects.create(job=job, skill=python, original_phrase="Python services")
        JobSkill.objects.create(job=job, skill=django, original_phrase="Django")

        result = schema.execute_sync(
            """
            {
              searchJobs(query: "pythn backend engineer", skill: "Python", limit: 3) {
                correctedQuery
                total
                jobs {
                  title
                  company
                  skills {
                    name
                  }
                }
                relatedSkills {
                  name
                  count
                }
              }
            }
            """
        )

        self.assertIsNone(result.errors)
        payload = result.data["searchJobs"]
        self.assertEqual(payload["correctedQuery"], "python backend engineer")
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["jobs"][0]["title"], "Backend Engineer, Python Platform")
        self.assertEqual(payload["jobs"][0]["company"], "Stripe")
        self.assertEqual(payload["relatedSkills"], [{"name": "Django", "count": 1}])
