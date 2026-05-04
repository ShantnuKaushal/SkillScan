from unittest.mock import Mock, patch

from django.test import TestCase

from apps.api.schema import schema
from apps.jobs.models import Company, JobPosting
from apps.skills.models import CanonicalSkill, JobSkill


class GraphQLSchemaTests(TestCase):
    def setUp(self):
        company = Company.objects.create(external_id="stripe", name="Stripe")
        self.job = JobPosting.objects.create(
            external_id="job-1",
            company=company,
            title="Backend Engineer, Python Platform",
            description="Build Python services with Django and PostgreSQL.",
            location="Remote",
            remote_allowed=True,
            posting_url="https://example.com/job-1",
        )
        python = CanonicalSkill.objects.create(name="Python")
        django = CanonicalSkill.objects.create(name="Django")
        JobSkill.objects.create(job=self.job, skill=python, original_phrase="Python services")
        JobSkill.objects.create(job=self.job, skill=django, original_phrase="Django")

    def test_search_jobs_uses_elasticsearch_hits_and_neo4j_graph_context(self):
        search_index = Mock()
        search_index.search.return_value = (
            1,
            [{"id": "job-1", "score": 12.5}],
        )
        graph = Mock()
        graph.related_skills.return_value = [{"name": "Django", "count": 1}]
        graph.skill_graph.return_value = {
            "nodes": [
                {"id": "skill:Python", "label": "Python", "type": "skill"},
                {"id": "skill:Django", "label": "Django", "type": "skill"},
            ],
            "edges": [
                {"source": "skill:Python", "target": "skill:Django", "type": "OFTEN_WITH", "weight": 1},
            ],
        }

        with patch("apps.api.schema.JobSearchIndex", return_value=search_index), patch(
            "apps.api.schema.SkillGraph", return_value=graph
        ):
            result = schema.execute_sync(
                """
                {
                  searchJobs(query: "pythn backend engineer", skill: "Python", limit: 3) {
                    correctedQuery
                    selectedSkill
                    total
                    jobs {
                      title
                      company
                      score
                      skills {
                        name
                      }
                    }
                    relatedSkills {
                      name
                      count
                    }
                    graph {
                      nodes {
                        id
                        label
                        type
                      }
                      edges {
                        source
                        target
                        type
                        weight
                      }
                    }
                  }
                }
                """
            )

        self.assertIsNone(result.errors)
        payload = result.data["searchJobs"]
        self.assertEqual(payload["correctedQuery"], "python backend engineer")
        self.assertEqual(payload["selectedSkill"], "Python")
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["jobs"][0]["title"], "Backend Engineer, Python Platform")
        self.assertEqual(payload["jobs"][0]["company"], "Stripe")
        self.assertEqual(payload["jobs"][0]["score"], 12.5)
        self.assertEqual(payload["relatedSkills"], [{"name": "Django", "count": 1}])
        self.assertEqual([node["type"] for node in payload["graph"]["nodes"]], ["skill", "skill"])
        self.assertEqual(payload["graph"]["nodes"][0]["id"], "skill:Python")
        self.assertEqual(payload["graph"]["edges"][0]["type"], "OFTEN_WITH")
        search_index.search.assert_called_once_with(
            query="python backend engineer",
            remote=None,
            skill="Python",
            location=None,
            size=3,
        )
        graph.related_skills.assert_called_once_with("Python")
        graph.skill_graph.assert_called_once_with("Python")
        graph.close.assert_called_once()

    def test_search_jobs_falls_back_to_database_and_local_graph_when_services_are_unavailable(self):
        with patch("apps.api.schema.JobSearchIndex", side_effect=RuntimeError("search unavailable")), patch(
            "apps.api.schema.SkillGraph", side_effect=RuntimeError("graph unavailable")
        ):
            result = schema.execute_sync(
                """
                {
                  searchJobs(query: "pythn backend engineer", skill: "Python", limit: 3) {
                    correctedQuery
                    selectedSkill
                    total
                    jobs {
                      title
                    }
                    relatedSkills {
                      name
                      count
                    }
                    graph {
                      nodes {
                        id
                      }
                      edges {
                        type
                      }
                    }
                  }
                }
                """
            )

        self.assertIsNone(result.errors)
        payload = result.data["searchJobs"]
        self.assertEqual(payload["correctedQuery"], "python backend engineer")
        self.assertEqual(payload["selectedSkill"], "Python")
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["jobs"][0]["title"], "Backend Engineer, Python Platform")
        self.assertEqual(payload["relatedSkills"], [{"name": "Django", "count": 1}])
        self.assertIn("skill:Python", [node["id"] for node in payload["graph"]["nodes"]])
        self.assertIn("OFTEN_WITH", [edge["type"] for edge in payload["graph"]["edges"]])
        self.assertTrue(all(node["id"].startswith("skill:") for node in payload["graph"]["nodes"]))

    def test_search_jobs_uses_query_skill_as_graph_focus_before_first_result_skill(self):
        search_index = Mock()
        search_index.search.return_value = (
            1,
            [{"id": "job-1", "score": 9.0}],
        )
        graph = Mock()
        graph.related_skills.return_value = [{"name": "Spring", "count": 1}]
        graph.skill_graph.return_value = {
            "nodes": [{"id": "skill:Java", "label": "Java", "type": "skill"}],
            "edges": [],
        }

        with patch("apps.api.schema.JobSearchIndex", return_value=search_index), patch(
            "apps.api.schema.SkillGraph", return_value=graph
        ):
            result = schema.execute_sync(
                """
                {
                  searchJobs(query: "java", limit: 3) {
                    selectedSkill
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
        self.assertEqual(payload["selectedSkill"], "Java")
        self.assertEqual(payload["relatedSkills"], [{"name": "Spring", "count": 1}])
        graph.related_skills.assert_called_once_with("Java")
        graph.skill_graph.assert_called_once_with("Java")

    def test_skill_graph_returns_graph_context_without_job_search(self):
        graph = Mock()
        graph.related_skills.return_value = [{"name": "Python", "count": 3}]
        graph.skill_graph.return_value = {
            "nodes": [
                {"id": "skill:AWS", "label": "AWS", "type": "skill"},
                {"id": "skill:Python", "label": "Python", "type": "skill"},
            ],
            "edges": [
                {"source": "skill:AWS", "target": "skill:Python", "type": "OFTEN_WITH", "weight": 3},
            ],
        }

        with patch("apps.api.schema.JobSearchIndex") as search_index, patch(
            "apps.api.schema.SkillGraph", return_value=graph
        ):
            result = schema.execute_sync(
                """
                {
                  skillGraph(skill: "aws") {
                    selectedSkill
                    relatedSkills {
                      name
                      count
                    }
                    graph {
                      nodes {
                        id
                      }
                      edges {
                        weight
                      }
                    }
                  }
                }
                """
            )

        self.assertIsNone(result.errors)
        payload = result.data["skillGraph"]
        self.assertEqual(payload["selectedSkill"], "AWS")
        self.assertEqual(payload["relatedSkills"], [{"name": "Python", "count": 3}])
        self.assertEqual(payload["graph"]["nodes"][0]["id"], "skill:AWS")
        search_index.assert_not_called()
        graph.related_skills.assert_called_once_with("AWS")
        graph.skill_graph.assert_called_once_with("AWS")
        graph.close.assert_called_once()

    def test_career_map_ranks_related_skills_by_example_jobs(self):
        company = Company.objects.get(external_id="stripe")
        job_two = JobPosting.objects.create(
            external_id="job-2",
            company=company,
            title="Platform Engineer",
            description="Build Python services with Docker and AWS.",
            location="New York",
            remote_allowed=False,
        )
        job_three = JobPosting.objects.create(
            external_id="job-3",
            company=company,
            title="Backend API Engineer",
            description="Build Python APIs with Docker.",
            location="Remote",
            remote_allowed=True,
        )
        job_four = JobPosting.objects.create(
            external_id="job-4",
            company=company,
            title="Cloud Engineer",
            description="Build AWS infrastructure.",
            location="Remote",
            remote_allowed=True,
        )
        docker = CanonicalSkill.objects.create(name="Docker")
        aws = CanonicalSkill.objects.create(name="AWS")
        JobSkill.objects.create(job=job_two, skill=CanonicalSkill.objects.get(name="Python"), original_phrase="Python")
        JobSkill.objects.create(job=job_two, skill=docker, original_phrase="Docker")
        JobSkill.objects.create(job=job_two, skill=aws, original_phrase="AWS")
        JobSkill.objects.create(job=job_three, skill=CanonicalSkill.objects.get(name="Python"), original_phrase="Python")
        JobSkill.objects.create(job=job_three, skill=docker, original_phrase="Docker")
        JobSkill.objects.create(job=job_four, skill=aws, original_phrase="AWS")

        search_index = Mock()
        search_index.search.return_value = (
            4,
            [
                {"id": "job-1", "score": 12.5},
                {"id": "job-2", "score": 9.0},
                {"id": "job-3", "score": 8.0},
                {"id": "job-4", "score": 7.0},
            ],
        )

        with patch("apps.api.schema.JobSearchIndex", return_value=search_index), patch(
            "apps.api.schema.SkillGraph", side_effect=RuntimeError("graph unavailable")
        ):
            result = schema.execute_sync(
                """
                {
                  careerMap(query: "backend engineer", selectedSkills: ["Python"], limit: 5) {
                    query
                    correctedQuery
                    total
                    selectedSkills
                    marketSkills {
                      name
                      count
                      selected
                    }
                    recommendedSkills {
                      name
                      count
                      exampleJobCount
                      previewJobs {
                        id
                        title
                      }
                    }
                    graph {
                      nodes {
                        id
                        label
                        type
                      }
                      edges {
                        source
                        target
                        type
                        weight
                      }
                    }
                  }
                }
                """
            )

        self.assertIsNone(result.errors)
        payload = result.data["careerMap"]
        self.assertEqual(payload["query"], "backend engineer")
        self.assertEqual(payload["correctedQuery"], "backend engineer")
        self.assertEqual(payload["total"], 4)
        self.assertEqual(payload["selectedSkills"], ["Python"])
        market_skill_by_name = {skill["name"]: skill for skill in payload["marketSkills"]}
        self.assertEqual(market_skill_by_name["Python"], {"name": "Python", "count": 3, "selected": True})
        self.assertEqual(market_skill_by_name["Docker"], {"name": "Docker", "count": 2, "selected": False})
        self.assertEqual(market_skill_by_name["AWS"], {"name": "AWS", "count": 2, "selected": False})
        self.assertEqual(payload["recommendedSkills"][0]["name"], "Docker")
        self.assertEqual(payload["recommendedSkills"][0]["count"], 2)
        self.assertEqual(payload["recommendedSkills"][0]["exampleJobCount"], 2)
        self.assertEqual(
            [job["id"] for job in payload["recommendedSkills"][0]["previewJobs"]],
            ["job-2", "job-3"],
        )
        aws_recommendation = next(skill for skill in payload["recommendedSkills"] if skill["name"] == "AWS")
        self.assertEqual(aws_recommendation["count"], 1)
        self.assertEqual(aws_recommendation["exampleJobCount"], 1)
        self.assertIn("skill:Python", [node["id"] for node in payload["graph"]["nodes"]])
        self.assertIn("skill:Docker", [node["id"] for node in payload["graph"]["nodes"]])
        self.assertIn("SELECTED_WITH", [edge["type"] for edge in payload["graph"]["edges"]])
        search_index.search.assert_called_once_with(
            query="backend engineer",
            remote=None,
            skill=None,
            location=None,
            size=5,
        )

    def test_career_map_returns_empty_recommendations_when_no_jobs_match(self):
        search_index = Mock()
        search_index.search.return_value = (0, [])

        with patch("apps.api.schema.JobSearchIndex", return_value=search_index):
            result = schema.execute_sync(
                """
                {
                  careerMap(query: "zzzzzz", selectedSkills: ["Python"], limit: 5) {
                    total
                    jobs {
                      id
                    }
                    marketSkills {
                      name
                    }
                    recommendedSkills {
                      name
                    }
                    graph {
                      nodes {
                        id
                      }
                      edges {
                        source
                      }
                    }
                  }
                }
                """
            )

        self.assertIsNone(result.errors)
        payload = result.data["careerMap"]
        self.assertEqual(payload["total"], 0)
        self.assertEqual(payload["jobs"], [])
        self.assertEqual(payload["marketSkills"], [])
        self.assertEqual(payload["recommendedSkills"], [])
        self.assertEqual(payload["graph"], {"nodes": [], "edges": []})

    def test_search_jobs_returns_empty_payload_when_no_jobs_exist(self):
        JobSkill.objects.all().delete()
        CanonicalSkill.objects.all().delete()
        JobPosting.objects.all().delete()
        Company.objects.all().delete()

        search_index = Mock()
        search_index.search.return_value = (0, [])

        with patch("apps.api.schema.JobSearchIndex", return_value=search_index):
            result = schema.execute_sync(
                """
                {
                  searchJobs(query: "python", limit: 3) {
                    selectedSkill
                    total
                    jobs {
                      id
                    }
                    relatedSkills {
                      name
                    }
                    graph {
                      nodes {
                        id
                      }
                      edges {
                        source
                      }
                    }
                  }
                }
                """
            )

        self.assertIsNone(result.errors)
        payload = result.data["searchJobs"]
        self.assertEqual(payload["selectedSkill"], "")
        self.assertEqual(payload["total"], 0)
        self.assertEqual(payload["jobs"], [])
        self.assertEqual(payload["relatedSkills"], [])
        self.assertEqual(payload["graph"], {"nodes": [], "edges": []})
