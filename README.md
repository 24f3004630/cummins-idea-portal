# Cummins Idea Portal
**For: Cummins College of Engineering
**By: Cummins College of Engineering

## Project Overview

The Cummins Idea Portal is a multi-user research and innovation management web application built for Cummins College of Engineering. It provides a centralised platform for managing research projects, faculty approvals, student participation, publications, intellectual property records, startup conversions, and college-wide analytics.

The portal supports three user roles:
- **Admin**: manages users and approvals, tracks campus research metrics, and exports reports.
- **Faculty**: creates and manages projects, publications, IPRs, and views college analytics in read-only mode.
- **Student**: registers, builds a profile, browses projects, joins teams, and tracks participation.

## Key Features

- Role-based authentication and access control
- Admin approval workflow for faculty registrations and user accounts
- Research project creation and lifecycle management
- Publication tracking and submission status management
- IPR / patent/copyright registration tracking
- Startup conversion support for approved projects
- Competition and funding management
- Faculty-only college analytics dashboard view
- Full export support for CSV, JSON, PDF reports
- Background email notifications using Celery and SMTP
- Responsive UI with Bootstrap and Chart.js visual analytics

## Role Capabilities

### Admin
- View the main dashboard with total users, projects, publications, IPRs, and startups
- Approve or reject faculty registrations
- Activate/deactivate or delete user accounts
- Search users and review pending approvals
- View and manage projects, publications, and IPR records
- Access analytics endpoints used by dashboard charts
- Export detailed reports for accreditation and portal data

### Faculty
- Register for an account and await admin approval
- Create and manage research projects with required skills, timeline, and status
- Add project publications, IPR entries, and funding details
- Convert research projects into startup records
- View assigned project team members and available students
- Access college-wide analytics in a view-only dashboard
- Edit faculty profile and contact details

### Student
- Self-register and automatically receive approval
- Build a profile with skills, bio, and resume upload
- Browse approved faculty research projects
- Join project teams and participate in research activities
- Explore competitions and contributions
- View project details and student involvement

## Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Flask, Flask-SQLAlchemy, Flask-Mail, Celery, Redis |
| Task Queue | Redis, Celery |
| Database | SQLite |
| Templates | Jinja2, HTML, CSS, Bootstrap |
| Charts | Chart.js |
| PDF Export | WeasyPrint |
| Config | dotenv / environment variables |

## Project Structure

```
cummins-idea-portal/
├── app.py                      # Public Flask entry point
├── create_db.py                # Database reset + sample seeding script
├── backend/
│   ├── app.py                  # Flask app factory, Celery setup
│   ├── config.py               # App and environment configuration
│   ├── requirements.txt        # Python dependencies
│   ├── accreditation/          # Accreditation report generation logic
│   ├── admin/                  # Admin routes and analytics APIs
│   ├── auth/                   # Authentication and registration routes
│   ├── database/               # SQLAlchemy models and DB init
│   ├── faculty/                # Faculty dashboard and project management
│   ├── generated_reports/      # Generated CSV/PDF/JSON output storage
│   ├── ipr/                    # IPR-specific logic and export routes
│   ├── student/                # Student views and routes
│   ├── tasks/                  # Celery background tasks and email templates
│   └── ...
├── frontend/
│   └── templates/              # Jinja2 templates for auth, admin, faculty, student
└── venv/                       # Python virtual environment (local)
```

## Database Schema Summary

Core tables include:
- `person` — stores Admin, Faculty, and Student accounts
- `research_project` — project metadata and status
- `publication` — publication records linked to projects
- `ipr` — intellectual property / patent records
- `startup` — startup conversions for projects
- `competition` — competition events and participation relations
- `project_person` — team membership between projects and people
- `project_funding` — funding relationships for projects
- `publication_author` — publication authorship mapping
- `student_competition` — student competition entries

## Installation and Setup

### Requirements
- Python 3.10+
- pip
- Redis for Celery task queue
- Optional: SMTP credentials for email notifications

### Steps

1. Clone the repository:

```bash
git clone <your-repo-url>
cd cummins-idea-portal
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

4. Start Redis (required for Celery):

```bash
redis-server
```

5. Run the Flask app:

```bash
python app.py
```

6. Optionally start Celery worker and beat scheduler:

```bash
cd backend
celery -A app.celery worker --loglevel=info
celery -A app.celery beat --loglevel=info
```

7. Open the application in a browser:

```text
http://127.0.0.1:8000
```

### Seed sample data

Use the `create_db.py` script to reset the database and create sample users:

```bash
python create_db.py
```

## Environment Variables

The application supports configuration via environment variables. Common values include:
- `SECRET_KEY` — Flask secret key
- `REDIS_URL` — Redis connection URL
- `MAIL_SERVER` — SMTP server
- `MAIL_PORT` — SMTP port
- `MAIL_USERNAME` — SMTP username
- `MAIL_PASSWORD` — SMTP password
- `MAIL_DEFAULT_SENDER` — default sender email
- `PORTAL_NAME` — portal display name
- `PORTAL_URL` — public portal URL

## Default Login Credentials

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@portal.com | admin123 |

Students and faculty can register through the application UI.

## Usage Notes

- Faculty accounts require admin approval before login.
- Students are approved automatically.
- Admin can view and download analytics and reports.
- Faculty can view a college-wide analytics dashboard in read-only mode.
- The system stores uploaded resumes and generated reports in the backend directories.

## Author

Student Of Cummins College of Engineering

## License

This repository does not include a license file.
