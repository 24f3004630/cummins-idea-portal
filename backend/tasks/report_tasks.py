"""
tasks/report_tasks.py
──────────────────────
Celery tasks for async document generation.

Tasks:
  • generate_accreditation_pdf          — full accreditation PDF via WeasyPrint
  • generate_accreditation_csv          — CSV export of all metrics
  • generate_project_report_pdf         — per-project status PDF
  • generate_and_email_monthly_report   — monthly Beat task (generate + email admin)
"""

import os
import csv
from datetime import datetime
from io import StringIO

from app import celery


# ────────────────────────────────────────────────────────────────────────────
# Helper
# ────────────────────────────────────────────────────────────────────────────

def _reports_dir() -> str:
    """Return the output directory for generated reports, create if missing."""
    from flask import current_app
    path = current_app.config.get(
        "REPORTS_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_reports"),
    )
    os.makedirs(path, exist_ok=True)
    return path


def _write_pdf(html: str, output_path: str) -> str:
    """
    Convert HTML to PDF using WeasyPrint.
    Falls back to saving as .html if WeasyPrint is unavailable.
    Returns the actual path written (may differ if fallback used).
    """
    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(output_path)
        return output_path
    except ImportError:
        fallback = output_path.replace(".pdf", ".html")
        with open(fallback, "w", encoding="utf-8") as f:
            f.write(html)
        return fallback


# ────────────────────────────────────────────────────────────────────────────
# 1. Generate Accreditation PDF
# ────────────────────────────────────────────────────────────────────────────

@celery.task(
    name="tasks.report_tasks.generate_accreditation_pdf",
    bind=True,
    max_retries=2,
    track_started=True,
)
def generate_accreditation_pdf(self, year: int = None, department: str = None):
    """
    Generate a full accreditation PDF report.
    Returns: dict with filename and path.
    Poll /admin/task-status/<task_id> for live progress updates.
    """
    from accreditation.generator import AccreditationReportGenerator

    if not year:
        year = datetime.now().year

    self.update_state(state="PROGRESS", meta={"step": "Collecting metrics…", "pct": 10})

    generator = AccreditationReportGenerator()
    report_data = generator.generate_comprehensive_report(year, department)

    self.update_state(state="PROGRESS", meta={"step": "Rendering HTML…", "pct": 40})
    html_content = generator._format_for_pdf(report_data)

    self.update_state(state="PROGRESS", meta={"step": "Converting to PDF…", "pct": 65})

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"CCEW_Accreditation_{year}_{ts}.pdf"
    output_path = os.path.join(_reports_dir(), filename)
    actual_path = _write_pdf(html_content, output_path)
    actual_filename = os.path.basename(actual_path)

    self.update_state(state="PROGRESS", meta={"step": "Done!", "pct": 100})

    return {
        "status": "success",
        "year": year,
        "filename": actual_filename,
        "path": actual_path,
        "generated_at": datetime.now().isoformat(),
    }


# ────────────────────────────────────────────────────────────────────────────
# 2. Generate Accreditation CSV
# ────────────────────────────────────────────────────────────────────────────

@celery.task(
    name="tasks.report_tasks.generate_accreditation_csv",
    bind=True,
    max_retries=2,
    track_started=True,
)
def generate_accreditation_csv(self, year: int = None, department: str = None):
    """
    Generate a CSV export of all accreditation metrics.
    Returns: dict with filename and path.
    """
    from accreditation.generator import AccreditationReportGenerator

    if not year:
        year = datetime.now().year

    self.update_state(state="PROGRESS", meta={"step": "Collecting metrics…", "pct": 20})

    generator = AccreditationReportGenerator()
    report = generator.generate_comprehensive_report(year, department)

    self.update_state(state="PROGRESS", meta={"step": "Building CSV…", "pct": 60})

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["CCEW Institutional Accreditation Report", f"Year: {year}"])
    writer.writerow(["Generated at", datetime.now().strftime("%d %b %Y %H:%M")])
    writer.writerow([])

    sections = [
        ("PROJECT METRICS", report.get("projects", {})),
        ("PUBLICATION METRICS", report.get("publications", {})),
        ("IPR METRICS", report.get("iprs", {})),
        ("STARTUP METRICS", report.get("startups", {})),
        ("FACULTY METRICS", report.get("faculty", {})),
        ("STUDENT METRICS", report.get("students", {})),
    ]

    for title, data in sections:
        writer.writerow([title])
        writer.writerow(["Metric", "Value"])
        for key, val in data.items():
            if isinstance(val, (int, float)):
                writer.writerow([key.replace("_", " ").title(), val])
        writer.writerow([])

    writer.writerow(["PROJECT RECORDS"])
    writer.writerow([
        'Project ID', 'Title', 'Description', 'Domain', 'Department', 'Status',
        'Team Size', 'Start Date', 'End Date', 'IIC Status', 'Level', 'Location',
        'Approved', 'Startup Converted', 'Faculty Name', 'Faculty Email', 'Team Members'
    ])
    for project in report.get('project_records', []):
        writer.writerow([
            project.get('project_id'),
            project.get('project_title'),
            project.get('project_description'),
            project.get('domain'),
            project.get('department'),
            project.get('project_status'),
            project.get('team_size'),
            project.get('start_date'),
            project.get('end_date'),
            project.get('iic_registration_status'),
            project.get('project_level'),
            project.get('program_location'),
            project.get('is_approved'),
            project.get('is_startup_converted'),
            project.get('faculty', {}).get('name'),
            project.get('faculty', {}).get('email'),
            ', '.join([m.get('name', '') for m in project.get('team_members', [])])
        ])
    writer.writerow([])

    writer.writerow(["PUBLICATION RECORDS"])
    writer.writerow([
        'Publication ID', 'Project ID', 'Project Title', 'Title', 'Type', 'Venue',
        'Publication Date', 'Indexing', 'Pages', 'Year', 'Volume', 'DOI',
        'ISSN/ISBN', 'Publisher', 'Document URL', 'Status', 'Faculty Name', 'Faculty Email'
    ])
    for pub in report.get('publication_records', []):
        writer.writerow([
            pub.get('publication_id'),
            pub.get('project_id'),
            pub.get('project_title'),
            pub.get('title'),
            pub.get('publication_type'),
            pub.get('venue'),
            pub.get('publication_date'),
            pub.get('indexing'),
            pub.get('page_number'),
            pub.get('year_of_publication'),
            pub.get('volume'),
            pub.get('doi'),
            pub.get('issn_isbn'),
            pub.get('publisher'),
            pub.get('document_url'),
            pub.get('status'),
            pub.get('faculty', {}).get('name'),
            pub.get('faculty', {}).get('email'),
        ])
    writer.writerow([])

    writer.writerow(["IPR RECORDS"])
    writer.writerow([
        'IPR ID', 'Project ID', 'Project Title', 'Publication ID', 'Publication Title',
        'Innovation Title', 'Type', 'Application Number', 'Filing Date', 'Registration Date',
        'Grant Date', 'Expiry Date', 'Status', 'Ownership Type', 'Document URL', 'Faculty Name', 'Faculty Email'
    ])
    for ipr in report.get('ipr_records', []):
        writer.writerow([
            ipr.get('ipr_id'),
            ipr.get('project_id'),
            ipr.get('project_title'),
            ipr.get('publication_id'),
            ipr.get('publication_title'),
            ipr.get('innovation_title'),
            ipr.get('ipr_type'),
            ipr.get('application_number'),
            ipr.get('filing_date'),
            ipr.get('registration_date'),
            ipr.get('grant_date'),
            ipr.get('expiry_date'),
            ipr.get('grant_status'),
            ipr.get('ownership_type'),
            ipr.get('document_url'),
            ipr.get('faculty', {}).get('name'),
            ipr.get('faculty', {}).get('email'),
        ])
    writer.writerow([])

    writer.writerow(["STARTUP RECORDS"])
    writer.writerow([
        'Startup ID', 'Project ID', 'Project Title', 'Startup Name', 'Registration Number',
        'Development Status', 'Fund Amount', 'Revenue Generated', 'Faculty Name', 'Faculty Email'
    ])
    for startup in report.get('startup_records', []):
        writer.writerow([
            startup.get('startup_id'),
            startup.get('project_id'),
            startup.get('project_title'),
            startup.get('startup_name'),
            startup.get('registration_number'),
            startup.get('development_status'),
            startup.get('fund_amount'),
            startup.get('revenue_generated'),
            startup.get('faculty', {}).get('name'),
            startup.get('faculty', {}).get('email'),
        ])
    writer.writerow([])

    writer.writerow(["FACULTY RECORDS"])
    writer.writerow([
        'Faculty ID', 'Name', 'Email', 'Department', 'Approved', 'Skills',
        'Resume URL', 'Bio', 'Phone', 'Project Count', 'Publication Count', 'IPR Count', 'Startup Count'
    ])
    for faculty in report.get('faculty_records', []):
        writer.writerow([
            faculty.get('person_id'),
            faculty.get('name'),
            faculty.get('email'),
            faculty.get('department'),
            faculty.get('is_approved'),
            faculty.get('skills'),
            faculty.get('resume_url'),
            faculty.get('bio'),
            faculty.get('phone'),
            faculty.get('project_count'),
            faculty.get('publication_count'),
            faculty.get('ipr_count'),
            faculty.get('startup_count'),
        ])
    writer.writerow([])

    writer.writerow(["STUDENT RECORDS"])
    writer.writerow([
        'Student ID', 'Name', 'Email', 'Department', 'Approved', 'Skills',
        'Resume URL', 'Bio', 'Phone', 'Project Count'
    ])
    for student in report.get('student_records', []):
        writer.writerow([
            student.get('person_id'),
            student.get('name'),
            student.get('email'),
            student.get('department'),
            student.get('is_approved'),
            student.get('skills'),
            student.get('resume_url'),
            student.get('bio'),
            student.get('phone'),
            student.get('project_count'),
        ])
    writer.writerow([])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"CCEW_Accreditation_{year}_{ts}.csv"
    output_path = os.path.join(_reports_dir(), filename)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write(output.getvalue())

    return {
        "status": "success",
        "year": year,
        "filename": filename,
        "path": output_path,
        "generated_at": datetime.now().isoformat(),
    }


# ────────────────────────────────────────────────────────────────────────────
# 3. Generate Per-Project Status PDF
# ────────────────────────────────────────────────────────────────────────────

@celery.task(
    name="tasks.report_tasks.generate_project_report_pdf",
    bind=True,
    max_retries=2,
    track_started=True,
)
def generate_project_report_pdf(self, project_id: int):
    """
    Generate a detailed status report PDF for one research project.
    Returns: dict with filename and path.
    """
    from database.models import (
        ResearchProject, Person, Publication, IPR,
        ProjectPerson, Startup
    )

    self.update_state(state="PROGRESS", meta={"step": "Loading project data…", "pct": 15})

    project = ResearchProject.query.get(project_id)
    if not project:
        return {"status": "error", "reason": "project not found"}

    faculty      = Person.query.get(project.faculty_id)
    publications = Publication.query.filter_by(project_id=project_id).all()
    iprs         = IPR.query.filter_by(project_id=project_id).all()
    startup      = Startup.query.filter_by(project_id=project_id).first()
    team = (
        Person.query
        .join(ProjectPerson, Person.person_id == ProjectPerson.person_id)
        .filter(ProjectPerson.project_id == project_id)
        .all()
    )

    self.update_state(state="PROGRESS", meta={"step": "Rendering report…", "pct": 50})

    html = _build_project_html(project, faculty, publications, iprs, startup, team)

    self.update_state(state="PROGRESS", meta={"step": "Generating PDF…", "pct": 75})

    safe_title = "".join(
        c if c.isalnum() or c in " _-" else "_"
        for c in project.project_title
    )[:50].strip()
    ts = datetime.now().strftime("%Y%m%d")
    filename = f"Project_{project_id}_{safe_title}_{ts}.pdf"
    output_path = os.path.join(_reports_dir(), filename)
    actual_path = _write_pdf(html, output_path)
    actual_filename = os.path.basename(actual_path)

    return {
        "status": "success",
        "project_id": project_id,
        "project_title": project.project_title,
        "filename": actual_filename,
        "path": actual_path,
        "generated_at": datetime.now().isoformat(),
    }


def _build_project_html(project, faculty, publications, iprs, startup, team) -> str:
    """Build the styled HTML content for a project report."""
    pub_rows = "".join(
        f"<tr><td>{p.title}</td><td>{p.publication_type or ''}</td>"
        f"<td>{p.venue or ''}</td><td>{p.status}</td>"
        f"<td>{p.year_of_publication or ''}</td></tr>"
        for p in publications
    ) or '<tr><td colspan="5" style="color:#718096;">No publications yet.</td></tr>'

    ipr_rows = "".join(
        f"<tr><td>{i.innovation_title}</td><td>{i.ipr_type or ''}</td>"
        f"<td>{i.application_number or ''}</td><td>{i.grant_status}</td></tr>"
        for i in iprs
    ) or '<tr><td colspan="4" style="color:#718096;">No IPRs filed yet.</td></tr>'

    team_rows = "".join(
        f"<tr><td>{m.name}</td><td>{m.type}</td><td>{m.email}</td></tr>"
        for m in team
    ) or '<tr><td colspan="3" style="color:#718096;">No members added yet.</td></tr>'

    startup_section = ""
    if startup:
        startup_section = f"""
        <h2>Startup</h2>
        <table>
          <tr><th>Startup Name</th><th>Status</th><th>Fund (₹)</th><th>Revenue (₹)</th></tr>
          <tr>
            <td>{startup.startup_name}</td>
            <td>{startup.development_status}</td>
            <td>{startup.fund_amount:,.2f}</td>
            <td>{startup.revenue_generated:,.2f}</td>
          </tr>
        </table>"""

    return f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #1a202c; }}
  h1 {{ color: #1e3a5f; border-bottom: 3px solid #2563eb; padding-bottom: 10px; margin-bottom: 20px; }}
  h2 {{ color: #1e3a5f; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13px; }}
  th {{ background: #1e3a5f; color: #fff; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
  tr:nth-child(even) td {{ background: #f7faff; }}
  .meta {{ background: #f7faff; border-left: 4px solid #2563eb; padding: 14px 18px;
           margin: 16px 0; border-radius: 4px; font-size: 14px; }}
  .meta p {{ margin: 5px 0; }}
  footer {{ margin-top: 50px; text-align: center; color: #718096; font-size: 12px;
            border-top: 1px solid #e2e8f0; padding-top: 16px; }}
</style></head>
<body>
  <h1>Research Project Report</h1>
  <div class="meta">
    <p><strong>Title:</strong> {project.project_title}</p>
    <p><strong>Faculty:</strong> {faculty.name if faculty else 'N/A'}
       {(' (' + faculty.email + ')') if faculty else ''}</p>
    <p><strong>Department:</strong> {project.department or 'N/A'} &nbsp;|&nbsp;
       <strong>Domain:</strong> {project.domain or 'N/A'}</p>
    <p><strong>Status:</strong> {project.project_status} &nbsp;|&nbsp;
       <strong>Team Size:</strong> {project.team_size or 'N/A'}</p>
    <p><strong>Report Generated:</strong> {datetime.now().strftime('%d %b %Y, %I:%M %p')}</p>
  </div>

  <h2>Description</h2>
  <p style="font-size:14px;line-height:1.6;color:#4a5568;">
    {project.project_description or 'No description provided.'}
  </p>

  <h2>Team Members ({len(team)})</h2>
  <table>
    <tr><th>Name</th><th>Type</th><th>Email</th></tr>
    {team_rows}
  </table>

  <h2>Publications ({len(publications)})</h2>
  <table>
    <tr><th>Title</th><th>Type</th><th>Venue</th><th>Status</th><th>Year</th></tr>
    {pub_rows}
  </table>

  <h2>IPRs / Patents ({len(iprs)})</h2>
  <table>
    <tr><th>Innovation Title</th><th>Type</th><th>App. No.</th><th>Grant Status</th></tr>
    {ipr_rows}
  </table>

  {startup_section}

  <footer>
    <p>Generated by CCEW Research &amp; Innovation Portal</p>
    <p>Cummins College of Engineering for Women, Pune</p>
  </footer>
</body>
</html>"""


# ────────────────────────────────────────────────────────────────────────────
# 4. Monthly Beat Task: Generate + Email Report to Admin
# ────────────────────────────────────────────────────────────────────────────

@celery.task(name="tasks.report_tasks.generate_and_email_monthly_report", bind=True)
def generate_and_email_monthly_report(self):
    """
    Runs on the 1st of every month (via Celery Beat).
    1. Fetches accreditation metrics for the current year.
    2. Dispatches generate_accreditation_pdf as a background task.
    3. Dispatches send_accreditation_report_ready to email the admin.
    """
    from accreditation.generator import AccreditationReportGenerator
    from tasks.mail_tasks import send_accreditation_report_ready

    year = datetime.now().year
    month_year = datetime.now().strftime("%B %Y")

    generator = AccreditationReportGenerator()
    report = generator.generate_comprehensive_report(year)

    metrics = {
        "total_projects":    report["projects"]["total_projects"],
        "total_publications": report["publications"]["total_publications"],
        "total_iprs":        report["iprs"]["total_iprs_filed"],
        "total_startups":    report["startups"]["total_startups"],
    }

    # Fire these as independent background tasks
    generate_accreditation_pdf.delay(year)
    send_accreditation_report_ready.delay(metrics, month_year)

    return {
        "status": "triggered",
        "month_year": month_year,
        "metrics": metrics,
    }
