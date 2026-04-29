from django.db import models


class IngestionRun(models.Model):
    source_name = models.CharField(max_length=255)
    row_limit = models.PositiveIntegerField(null=True, blank=True)
    companies_loaded = models.PositiveIntegerField(default=0)
    jobs_loaded = models.PositiveIntegerField(default=0)
    skills_linked = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="running")
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.source_name} ({self.status})"
