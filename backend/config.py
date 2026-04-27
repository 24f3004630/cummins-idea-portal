import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '.env'))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(BASE_DIR, "idea_portal.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "Asia/Kolkata"
    CELERY_ENABLE_UTC = True

    # ── Email (Flask-Mail via SMTP) ───────────────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        os.environ.get("MAIL_USERNAME", "noreply@ccew-portal.com"),
    )

    # ── Portal Meta (used in email templates) ────────────────────────────────
    PORTAL_NAME = os.environ.get("PORTAL_NAME", "CCEW Research & Innovation Portal")
    PORTAL_URL = os.environ.get("PORTAL_URL", "http://localhost:8000")

    # ── Generated Reports Output Directory ───────────────────────────────────
    REPORTS_DIR = os.path.join(BASE_DIR, "generated_reports")

    # ── Uploaded Documents ───────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")