from django.contrib import admin

from apps.ingestion.models import IngestionRun


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("source_name", "status", "row_limit", "jobs_loaded", "skills_linked", "started_at", "finished_at")
    readonly_fields = ("started_at", "finished_at")
