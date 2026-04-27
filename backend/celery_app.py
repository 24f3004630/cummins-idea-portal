"""
celery_app.py
─────────────
Thin shim so the Celery CLI can find the celery instance.

CLI commands (run from backend/ directory):
  # Start worker:
  celery -A celery_app worker --loglevel=info --concurrency=4

  # Start Beat scheduler:
  celery -A celery_app beat --loglevel=info

  # Flower monitoring UI (pip install flower):
  celery -A celery_app flower --port=5555
"""

# Import the celery instance that lives in app.py.
# app.py applies all Flask-aware config and context wrapping when it runs.
from app import celery  # noqa: F401
