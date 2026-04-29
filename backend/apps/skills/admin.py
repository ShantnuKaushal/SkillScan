from django.contrib import admin

from apps.skills.models import CanonicalSkill, JobSkill, SkillAlias


class SkillAliasInline(admin.TabularInline):
    model = SkillAlias
    extra = 0


@admin.register(CanonicalSkill)
class CanonicalSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "source")
    search_fields = ("name", "aliases__alias")
    inlines = [SkillAliasInline]


@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    list_display = ("job", "skill", "original_phrase", "source")
    search_fields = ("job__title", "skill__name", "original_phrase")
