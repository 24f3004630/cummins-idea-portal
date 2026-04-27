"""
tasks/mail_tasks.py
───────────────────
All Celery email notification tasks for the Idea Portal.

Available tasks:
  • send_faculty_registration_pending  — notify admin of new faculty signup
  • send_faculty_approved_email        — notify faculty of their approval
  • send_project_submitted_email       — notify admin of new project submission
  • send_project_approved_email        — notify faculty of their project approval
  • send_student_join_approved_email   — notify student they joined a project
  • send_report_reminder_all_faculty   — weekly blast to all active faculty
  • send_report_reminder_all_students  — weekly blast to all active students
  • send_accreditation_report_ready    — notify admin that monthly report is ready
"""

import os
from datetime import datetime

from flask import current_app
from flask_mail import Message

# Import the shared celery instance from app.py
from app import celery


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _send(subject: str, recipients: list, html_body: str) -> bool:
    """Build a Flask-Mail Message and send it. Returns True on success."""
    from app import mail
    sender = current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@ccew.edu")
    msg = Message(subject=subject, recipients=recipients, html=html_body, sender=sender)
    try:
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error(f"[mail_tasks] Email to {recipients} failed: {exc}")
        return False


def _portal_ctx() -> dict:
    """Common template variables injected into every email."""
    return {
        "portal_name": current_app.config.get("PORTAL_NAME", "CCEW Research Portal"),
        "portal_url":  current_app.config.get("PORTAL_URL", "http://localhost:8000"),
        "year":        datetime.now().year,
    }


def _render(template_name: str, **kwargs) -> str:
    """Render a Jinja2 email template from tasks/email_templates/."""
    from jinja2 import Environment, FileSystemLoader
    templates_dir = os.path.join(os.path.dirname(__file__), "email_templates")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    template = env.get_template(template_name)
    return template.render(**{**_portal_ctx(), **kwargs})


# ────────────────────────────────────────────────────────────────────────────
# 1. Faculty Registration Pending → Admin
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_faculty_registration_pending",
             bind=True, max_retries=3, default_retry_delay=60)
def send_faculty_registration_pending(self, faculty_id: int):
    """Notify admin that a new faculty has registered and awaits approval."""
    from database.models import Person
    try:
        faculty = Person.query.get(faculty_id)
        if not faculty:
            return {"status": "skipped", "reason": "faculty not found"}

        admin = Person.query.filter_by(type="Admin").first()
        if not admin:
            return {"status": "skipped", "reason": "no admin found"}

        html = _render(
            "faculty_registration_pending.html",
            faculty_name=faculty.name,
            faculty_email=faculty.email,
            faculty_department=faculty.department or "N/A",
            registered_at=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        )
        ok = _send(
            subject=f"[Action Required] New Faculty Registration — {faculty.name}",
            recipients=[admin.email],
            html_body=html,
        )
        return {"status": "sent" if ok else "failed", "to": admin.email}
    except Exception as exc:
        raise self.retry(exc=exc)


# ────────────────────────────────────────────────────────────────────────────
# 2. Faculty Approved → Faculty
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_faculty_approved_email",
             bind=True, max_retries=3, default_retry_delay=60)
def send_faculty_approved_email(self, faculty_id: int):
    """Notify approved faculty that their account is now active."""
    from database.models import Person
    try:
        faculty = Person.query.get(faculty_id)
        if not faculty:
            return {"status": "skipped", "reason": "faculty not found"}

        html = _render(
            "faculty_approved.html",
            faculty_name=faculty.name,
            faculty_email=faculty.email,
            faculty_department=faculty.department or "N/A",
            approved_at=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        )
        ok = _send(
            subject="✅ Your Faculty Account Has Been Approved",
            recipients=[faculty.email],
            html_body=html,
        )
        return {"status": "sent" if ok else "failed", "to": faculty.email}
    except Exception as exc:
        raise self.retry(exc=exc)


# ────────────────────────────────────────────────────────────────────────────
# 3. Project Submitted → Admin
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_project_submitted_email",
             bind=True, max_retries=3, default_retry_delay=60)
def send_project_submitted_email(self, project_id: int):
    """Notify admin that a new project has been submitted for review."""
    from database.models import ResearchProject, Person
    try:
        project = ResearchProject.query.get(project_id)
        if not project:
            return {"status": "skipped", "reason": "project not found"}

        faculty = Person.query.get(project.faculty_id)
        admin = Person.query.filter_by(type="Admin").first()
        if not admin:
            return {"status": "skipped", "reason": "no admin found"}

        html = _render(
            "project_submitted.html",
            project_title=project.project_title,
            project_domain=project.domain or "N/A",
            project_department=project.department or "N/A",
            team_size=project.team_size or "N/A",
            faculty_name=faculty.name if faculty else "Unknown",
            faculty_email=faculty.email if faculty else "Unknown",
            submitted_at=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        )
        ok = _send(
            subject=f"[Review Required] New Project Submitted — {project.project_title}",
            recipients=[admin.email],
            html_body=html,
        )
        return {"status": "sent" if ok else "failed", "to": admin.email}
    except Exception as exc:
        raise self.retry(exc=exc)


# ────────────────────────────────────────────────────────────────────────────
# 4. Project Approved → Faculty
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_project_approved_email",
             bind=True, max_retries=3, default_retry_delay=60)
def send_project_approved_email(self, project_id: int):
    """Notify faculty that their project has been approved."""
    from database.models import ResearchProject, Person
    try:
        project = ResearchProject.query.get(project_id)
        if not project:
            return {"status": "skipped", "reason": "project not found"}

        faculty = Person.query.get(project.faculty_id)
        if not faculty:
            return {"status": "skipped", "reason": "faculty not found"}

        html = _render(
            "project_approved.html",
            faculty_name=faculty.name,
            project_title=project.project_title,
            project_domain=project.domain or "N/A",
            project_department=project.department or "N/A",
            project_id=project.project_id,
            approved_at=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        )
        ok = _send(
            subject=f"🚀 Your Project Has Been Approved — {project.project_title}",
            recipients=[faculty.email],
            html_body=html,
        )
        return {"status": "sent" if ok else "failed", "to": faculty.email}
    except Exception as exc:
        raise self.retry(exc=exc)


# ────────────────────────────────────────────────────────────────────────────
# 5. Student Approved to Join Project → Student
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_student_join_approved_email",
             bind=True, max_retries=3, default_retry_delay=60)
def send_student_join_approved_email(self, student_id: int, project_id: int,
                                      role: str = "Team Member"):
    """Notify a student that they have been added to a research project."""
    from database.models import ResearchProject, Person
    try:
        student = Person.query.get(student_id)
        project = ResearchProject.query.get(project_id)
        if not student or not project:
            return {"status": "skipped", "reason": "student or project not found"}

        faculty = Person.query.get(project.faculty_id)

        html = _render(
            "student_approved.html",
            student_name=student.name,
            project_title=project.project_title,
            project_department=project.department or "N/A",
            faculty_name=faculty.name if faculty else "N/A",
            student_role=role,
            project_id=project.project_id,
        )
        ok = _send(
            subject=f"🎉 You've Joined a Research Project — {project.project_title}",
            recipients=[student.email],
            html_body=html,
        )
        return {"status": "sent" if ok else "failed", "to": student.email}
    except Exception as exc:
        raise self.retry(exc=exc)


# ────────────────────────────────────────────────────────────────────────────
# 6. Weekly Reminder → All Active Faculty
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_report_reminder_all_faculty",
             bind=True, max_retries=2)
def send_report_reminder_all_faculty(self):
    """
    Weekly blast: email all approved faculty with active projects and ask
    them to update their data in the portal.
    Triggered by Celery Beat every Monday 9:00 AM IST, or manually from admin.
    """
    from database.models import Person, ResearchProject
    faculty_list = Person.query.filter_by(type="Faculty", is_approved=True).all()

    sent_count, fail_count = 0, 0
    for faculty in faculty_list:
        active = ResearchProject.query.filter_by(
            faculty_id=faculty.person_id, project_status="Ongoing"
        ).count()

        html = _render(
            "report_reminder_faculty.html",
            faculty_name=faculty.name,
            active_projects=active,
        )
        ok = _send(
            subject="📝 Weekly Reminder: Please Update Your Project Data",
            recipients=[faculty.email],
            html_body=html,
        )
        if ok:
            sent_count += 1
        else:
            fail_count += 1

    return {
        "status": "complete",
        "sent": sent_count,
        "failed": fail_count,
        "total_faculty": len(faculty_list),
    }


# ────────────────────────────────────────────────────────────────────────────
# 7. Weekly Reminder → All Active Students
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_report_reminder_all_students",
             bind=True, max_retries=2)
def send_report_reminder_all_students(self):
    """
    Weekly blast: email all approved students asking them to check project
    status and update their profiles.
    Triggered by Celery Beat every Monday 9:00 AM IST, or manually from admin.
    """
    from database.models import Person, ProjectPerson
    students = Person.query.filter_by(type="Student", is_approved=True).all()

    sent_count, fail_count = 0, 0
    for student in students:
        active = ProjectPerson.query.filter_by(person_id=student.person_id).count()

        html = _render(
            "report_reminder_student.html",
            student_name=student.name,
            active_projects=active,
        )
        ok = _send(
            subject="💡 Weekly Reminder: Check Your Research Projects",
            recipients=[student.email],
            html_body=html,
        )
        if ok:
            sent_count += 1
        else:
            fail_count += 1

    return {
        "status": "complete",
        "sent": sent_count,
        "failed": fail_count,
        "total_students": len(students),
    }


# ────────────────────────────────────────────────────────────────────────────
# 8. Accreditation Report Ready → Admin
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.mail_tasks.send_accreditation_report_ready",
             bind=True, max_retries=3, default_retry_delay=60)
def send_accreditation_report_ready(self, metrics: dict, month_year: str):
    """
    Notify admin that the monthly accreditation report has been generated.
    `metrics` dict must have: total_projects, total_publications,
                               total_iprs, total_startups
    """
    from database.models import Person
    try:
        admin = Person.query.filter_by(type="Admin").first()
        if not admin:
            return {"status": "skipped", "reason": "no admin found"}

        html = _render(
            "accreditation_report_ready.html",
            month_year=month_year,
            total_projects=metrics.get("total_projects", 0),
            total_publications=metrics.get("total_publications", 0),
            total_iprs=metrics.get("total_iprs", 0),
            total_startups=metrics.get("total_startups", 0),
            generated_at=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        )
        ok = _send(
            subject=f"📊 Monthly Accreditation Report Ready — {month_year}",
            recipients=[admin.email],
            html_body=html,
        )
        return {"status": "sent" if ok else "failed", "to": admin.email}
    except Exception as exc:
        raise self.retry(exc=exc)
