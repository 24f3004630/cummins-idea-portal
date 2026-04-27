"""
celery_beat_schedule.py
───────────────────────
Periodic task schedule for Celery Beat.

Timezone: Asia/Kolkata (IST)

Schedule:
  • Every Monday 9:00 AM IST  → reminder emails to all active faculty
  • Every Monday 9:00 AM IST  → reminder emails to all active students
  • 1st of every month 8:00 AM → auto-generate monthly accreditation summary → email admin
"""

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # ── Weekly faculty reminder ───────────────────────────────────────────────
    "weekly-faculty-report-reminder": {
        "task": "tasks.mail_tasks.send_report_reminder_all_faculty",
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
        "args": [],
        "options": {"expires": 3600},
    },

    # ── Weekly student reminder ───────────────────────────────────────────────
    "weekly-student-report-reminder": {
        "task": "tasks.mail_tasks.send_report_reminder_all_students",
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
        "args": [],
        "options": {"expires": 3600},
    },

    # ── Monthly accreditation report generation + email to admin ─────────────
    "monthly-accreditation-report": {
        "task": "tasks.report_tasks.generate_and_email_monthly_report",
        "schedule": crontab(hour=8, minute=0, day_of_month="1"),
        "args": [],
        "options": {"expires": 86400},
    },
}
