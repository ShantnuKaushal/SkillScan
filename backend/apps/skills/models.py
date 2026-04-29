from django.db import models

from apps.jobs.models import JobPosting


class CanonicalSkill(models.Model):
    name = models.CharField(max_length=128, unique=True)
    source = models.CharField(max_length=64, default="normalizer")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SkillAlias(models.Model):
    skill = models.ForeignKey(CanonicalSkill, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=128, unique=True)

    class Meta:
        ordering = ["alias"]

    def __str__(self) -> str:
        return f"{self.alias} -> {self.skill.name}"


class JobSkill(models.Model):
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="job_skills")
    skill = models.ForeignKey(CanonicalSkill, on_delete=models.CASCADE, related_name="job_skills")
    original_phrase = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=64, default="description")

    class Meta:
        unique_together = ("job", "skill")
        indexes = [
            models.Index(fields=["source"]),
        ]

    def __str__(self) -> str:
        return f"{self.job.external_id}: {self.skill.name}"
