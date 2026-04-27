"""
app.py — Main Flask application + Celery instance
──────────────────────────────────────────────────
Run Flask:  python app.py
Run Worker: celery -A app.celery worker --loglevel=info
Run Beat:   celery -A app.celery beat  --loglevel=info
"""

import os
from flask import Flask, render_template, session
from flask_mail import Mail
from celery import Celery
from sqlalchemy import inspect, text

from config import Config
from database.db import db

# ── Create the Celery instance FIRST (before Flask app) ──────────────────────
# This allows tasks to import `from app import celery` without circular issues.
celery = Celery(__name__)


def _ensure_sqlite_compat_columns():
    """Add columns that older SQLite databases may be missing."""
    engine = db.engine
    if engine.dialect.name != 'sqlite':
        return

    required_columns = {
        'publication': {
            'document_url': 'ALTER TABLE publication ADD COLUMN document_url VARCHAR(255)'
        },
        'ipr': {
            'document_url': 'ALTER TABLE ipr ADD COLUMN document_url VARCHAR(255)'
        },
    }

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in required_columns.items():
            existing_columns = {
                column['name'] for column in inspector.get_columns(table_name)
            }
            for column_name, ddl in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(ddl))


def create_app(config_class=Config):
    """Application factory — creates and configures the Flask app."""
    # Point to frontend/templates directory (one level up)
    template_folder = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates')
    app = Flask(__name__, template_folder=template_folder)
    app.config.from_object(config_class)

    # Session settings
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

    # ── Init extensions ───────────────────────────────────────────────────────
    db.init_app(app)
    mail.init_app(app)

    # ── Configure Celery to use this app's config ─────────────────────────────
    celery.config_from_object(app.config)
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        task_track_started=True,
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone=app.config.get('CELERY_TIMEZONE', 'Asia/Kolkata'),
        enable_utc=True,
    )

    # Beat schedule
    from celery_beat_schedule import CELERYBEAT_SCHEDULE
    celery.conf.beat_schedule = CELERYBEAT_SCHEDULE

    # Make every Celery task automatically push a Flask app context
    class ContextTask(celery.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # ── Register blueprints ───────────────────────────────────────────────────
    from auth.routes import auth_bp
    from admin.routes import admin_bp
    from faculty.routes import faculty_bp
    from student.routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(student_bp)

    # ── Seed DB ───────────────────────────────────────────────────────────────
    from database.models import Person
    with app.app_context():
        db.create_all()
        _ensure_sqlite_compat_columns()
        if not Person.query.filter_by(email="admin@portal.com").first():
            admin = Person(name="Admin", email="admin@portal.com", type="Admin", is_approved=True)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

    # ── Routes ────────────────────────────────────────────────────────────────
    @app.route('/')
    def home():
        return render_template('home.html', user=session.get('user_id'))

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app


# ── Flask-Mail (init before create_app so tasks can import it) ──────────────
mail = Mail()

# ── Autodiscover tasks so Celery finds them ───────────────────────────────────
celery.autodiscover_tasks(['tasks.mail_tasks', 'tasks.report_tasks'])

# ── Build the app ─────────────────────────────────────────────────────────────
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=8000)
