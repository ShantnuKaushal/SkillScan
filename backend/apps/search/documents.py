from apps.jobs.models import JobPosting


def build_job_document(job: JobPosting) -> dict:
    skills = [job_skill.skill.name for job_skill in job.job_skills.select_related("skill").all()]
    return {
        "id": job.external_id,
        "title": job.title,
        "company": job.company.name if job.company else "",
        "location": job.location,
        "description": job.description,
        "work_type": job.work_type,
        "experience_level": job.experience_level,
        "remote_allowed": job.remote_allowed,
        "posting_url": job.posting_url,
        "skills": skills,
    }
