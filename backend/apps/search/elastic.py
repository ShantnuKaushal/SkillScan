from __future__ import annotations

from django.conf import settings
from elasticsearch import Elasticsearch

from apps.jobs.models import JobPosting
from apps.search.documents import build_job_document


JOB_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "company": {"type": "keyword"},
            "location": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "description": {"type": "text"},
            "work_type": {"type": "keyword"},
            "experience_level": {"type": "keyword"},
            "remote_allowed": {"type": "boolean"},
            "posting_url": {"type": "keyword"},
            "skills": {"type": "keyword"},
        }
    }
}


class JobSearchIndex:
    def __init__(self, client: Elasticsearch | None = None, index_name: str | None = None) -> None:
        self.client = client or Elasticsearch(settings.ELASTICSEARCH_URL)
        self.index_name = index_name or settings.ELASTICSEARCH_INDEX

    def ensure_index(self) -> None:
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, **JOB_INDEX_MAPPING)

    def index_job(self, job: JobPosting) -> None:
        self.client.index(index=self.index_name, id=job.external_id, document=build_job_document(job))

    def search(self, query: str, remote: bool | None = None, skill: str | None = None, size: int = 20) -> list[dict]:
        filters: list[dict] = []
        if remote is not None:
            filters.append({"term": {"remote_allowed": remote}})
        if skill:
            filters.append({"term": {"skills": skill}})

        response = self.client.search(
            index=self.index_name,
            size=size,
            query={
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^4", "skills^3", "company^2", "location", "description"],
                                "fuzziness": "AUTO",
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
        )
        return [
            {"score": hit["_score"], **hit["_source"]}
            for hit in response["hits"]["hits"]
        ]
