"""
Accreditation Report Generator
Generates comprehensive accreditation reports from research data
"""
from datetime import datetime, timedelta
from database.models import (
    ResearchProject, Publication, IPR, Startup, Person, 
    ProjectPerson, ProjectApplication
)
from database.db import db
from sqlalchemy import func, extract
import json


class AccreditationReportGenerator:
    """Generate institutional accreditation reports"""
    
    def __init__(self):
        self.report_date = datetime.now()
        self.data = {}
    
    def _normalize_department(self, department):
        if not department:
            return None
        normalized = department.strip()
        return None if normalized.lower() == 'all' else normalized

    # ==================== METRICS COLLECTION ====================
    
    def _project_query(self, year=None, department=None):
        query = ResearchProject.query

        department = self._normalize_department(department)
        if department:
            query = query.filter(func.lower(ResearchProject.department) == department.lower())

        return query

    def get_project_metrics(self, year=None, department=None):
        """Collect project-related metrics"""
        projects = self._project_query(year, department).all()
        approved_projects = [p for p in projects if p.is_approved]
        completed_projects = [p for p in projects if p.project_status == 'Completed']

        metrics = {
            'total_projects': len(projects),
            'approved_projects': len(approved_projects),
            'completed_projects': len(completed_projects),
            'ongoing_projects': len([p for p in projects if p.project_status == 'Ongoing']),
            'proposed_projects': len([p for p in projects if p.project_status == 'Proposed']),
            'on_hold_projects': len([p for p in projects if p.project_status == 'On Hold']),

            'projects_by_domain': self._group_by_domain(approved_projects),
            'projects_by_department': self._group_by_department(approved_projects),
            'average_team_size': self._avg_team_size(approved_projects),
        }

        return metrics

    def get_publication_metrics(self, year=None, department=None):
        """Collect publication-related metrics for accreditation"""
        query = Publication.query.join(
            ResearchProject, Publication.project_id == ResearchProject.project_id
        )

        department = self._normalize_department(department)
        if department:
            query = query.filter(func.lower(ResearchProject.department) == department.lower())

        publications = query.all()

        metrics = {
            'total_publications': len(publications),
            'published': len([p for p in publications if p.status == 'Published']),
            'accepted': len([p for p in publications if p.status == 'Accepted']),
            'submitted': len([p for p in publications if p.status == 'Submitted']),
            'rejected': len([p for p in publications if p.status == 'Rejected']),

            'international_journals': len([p for p in publications if p.publication_type == 'International Journal']),
            'national_journals': len([p for p in publications if p.publication_type == 'National Journal']),
            'conferences': len([p for p in publications if p.publication_type == 'Conference']),
            'books': len([p for p in publications if p.publication_type == 'Book']),

            'average_citations': 0,  # Citation field not available in Publication model
        }

        return metrics
    
    def get_ipr_metrics(self, year=None, department=None):
        """Collect IPR/Patent metrics for accreditation"""
        query = IPR.query.join(
            ResearchProject, IPR.project_id == ResearchProject.project_id
        )

        department = self._normalize_department(department)
        if department:
            query = query.filter(func.lower(ResearchProject.department) == department.lower())

        iprs = query.all()

        metrics = {
            'total_iprs_filed': len(iprs),
            'patents_filed': len([ipr for ipr in iprs if ipr.ipr_type == 'Patent']),
            'copyrights_filed': len([ipr for ipr in iprs if ipr.ipr_type == 'Copyright']),
            'trademarks_filed': len([ipr for ipr in iprs if ipr.ipr_type == 'Trademark']),

            'patents_granted': len([ipr for ipr in iprs if ipr.grant_status == 'Granted']),
            'patents_pending': len([ipr for ipr in iprs if ipr.grant_status == 'Pending']),
            'patents_rejected': len([ipr for ipr in iprs if ipr.grant_status == 'Rejected']),

            'average_days_to_grant': self._avg_days_to_grant(iprs),
        }

        return metrics

    def get_startup_metrics(self, year=None, department=None):
        """Collect startup metrics for entrepreneurship accreditation"""
        query = Startup.query.join(
            ResearchProject, Startup.project_id == ResearchProject.project_id
        )

        department = self._normalize_department(department)
        if department:
            query = query.filter(func.lower(ResearchProject.department) == department.lower())

        startups = query.all()

        metrics = {
            'total_startups': len(startups),

            'startups_in_ideas': len([s for s in startups if s.development_status == 'Idea']),
            'startups_mvp': len([s for s in startups if s.development_status == 'MVP']),
            'startups_beta': len([s for s in startups if s.development_status == 'Beta']),
            'startups_live': len([s for s in startups if s.development_status == 'Live']),
            'startups_growth': len([s for s in startups if s.development_status == 'Growth']),

            'total_funding_raised': sum([s.fund_amount for s in startups]),
            'total_revenue_generated': sum([s.revenue_generated for s in startups]),
            'average_funding_per_startup': sum([s.fund_amount for s in startups]) / len(startups) if startups else 0,
        }

        return metrics

    def get_faculty_metrics(self, year=None, department=None):
        """Collect faculty research activity metrics"""
        faculty_query = Person.query.filter_by(type='Faculty')
        if department and department != 'All':
            department_filter = department.strip().lower()
            faculty_query = faculty_query.filter(func.lower(Person.department) == department_filter)

        faculty = faculty_query.all()

        faculty_with_projects = []
        for f in faculty:
            project_query = ResearchProject.query.filter_by(faculty_id=f.person_id)
            if department and department != 'All':
                department_filter = department.strip().lower()
                project_query = project_query.filter(func.lower(ResearchProject.department) == department_filter)

            if project_query.count() > 0:
                faculty_with_projects.append(f)

        faculty_with_publications = []
        for f in faculty:
            pub_query = db.session.query(db.func.count(Publication.publication_id)).join(
                ResearchProject, Publication.project_id == ResearchProject.project_id
            ).filter(ResearchProject.faculty_id == f.person_id)
            if department and department != 'All':
                department_filter = department.strip().lower()
                pub_query = pub_query.filter(func.lower(ResearchProject.department) == department_filter)

            if pub_query.scalar() > 0:
                faculty_with_publications.append(f)

        faculty_with_iprs = []
        for f in faculty:
            ipr_query = db.session.query(db.func.count(IPR.ipr_id)).join(
                ResearchProject, IPR.project_id == ResearchProject.project_id
            ).filter(ResearchProject.faculty_id == f.person_id)
            if department and department != 'All':
                department_filter = department.strip().lower()
                ipr_query = ipr_query.filter(func.lower(ResearchProject.department) == department_filter)

            if ipr_query.scalar() > 0:
                faculty_with_iprs.append(f)

        metrics = {
            'total_faculty': len(faculty),
            'faculty_with_projects': len(faculty_with_projects),
            'faculty_with_publications': len(faculty_with_publications),
            'faculty_with_iprs': len(faculty_with_iprs),
            'faculty_with_startups': 0,  # TODO: Calculate from projects converted to startups
        }

        return metrics

    def get_student_metrics(self, year=None, department=None):
        """Collect student research engagement metrics"""
        student_query = Person.query.filter_by(type='Student')
        if department and department != 'All':
            department_filter = department.strip().lower()
            student_query = student_query.filter(func.lower(Person.department) == department_filter)

        students = student_query.all()

        students_in_projects = []
        for s in students:
            project_query = db.session.query(db.func.count(ProjectPerson.project_id)).join(
                ResearchProject, ProjectPerson.project_id == ResearchProject.project_id
            ).filter(ProjectPerson.person_id == s.person_id)
            if department and department != 'All':
                department_filter = department.strip().lower()
                project_query = project_query.filter(func.lower(ResearchProject.department) == department_filter)

            if project_query.scalar() > 0:
                students_in_projects.append(s)

        metrics = {
            'total_students': len(students),
            'students_in_projects': len(students_in_projects),
            'students_in_publications': 0,  # TODO: Track if students are co-authors
        }
        
        return metrics

    def get_project_details(self, year=None, department=None):
        """Return all research projects with related details."""
        projects = self._project_query(year, department).all()
        details = []

        for project in projects:
            faculty = project.get_faculty()
            members = []
            for member_row in project.get_team_members():
                if isinstance(member_row, tuple) and len(member_row) > 1:
                    _, person = member_row
                else:
                    person = member_row
                members.append({
                    'person_id': getattr(person, 'person_id', None),
                    'name': getattr(person, 'name', ''),
                    'email': getattr(person, 'email', ''),
                    'department': getattr(person, 'department', ''),
                    'role': getattr(person, 'type', ''),
                })

            startup = project.get_startup()

            details.append({
                'project_id': project.project_id,
                'project_title': project.project_title,
                'project_description': project.project_description or '',
                'domain': project.domain or '',
                'department': project.department or '',
                'required_skills': project.required_skills or '',
                'team_size': project.team_size or 0,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'project_status': project.project_status or '',
                'iic_registration_status': project.iic_registration_status or '',
                'project_level': project.project_level or '',
                'program_location': project.program_location or '',
                'is_approved': bool(project.is_approved),
                'is_startup_converted': bool(project.is_startup_converted),
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None,
                'faculty': {
                    'person_id': getattr(faculty, 'person_id', None),
                    'name': getattr(faculty, 'name', ''),
                    'email': getattr(faculty, 'email', ''),
                    'department': getattr(faculty, 'department', ''),
                },
                'team_members': members,
                'startup': {
                    'startup_id': startup.startup_id if startup else None,
                    'startup_name': startup.startup_name if startup else '',
                    'development_status': startup.development_status if startup else '',
                    'fund_amount': startup.fund_amount if startup else 0,
                    'revenue_generated': startup.revenue_generated if startup else 0,
                    'registration_number': startup.registration_number if startup else '',
                    'created_at': startup.created_at.isoformat() if startup and startup.created_at else None,
                    'updated_at': startup.updated_at.isoformat() if startup and startup.updated_at else None,
                } if startup else {},
            })

        return details

    def get_publication_details(self, year=None, department=None):
        """Return all publications with related project and faculty details."""
        query = Publication.query.join(
            ResearchProject, Publication.project_id == ResearchProject.project_id
        )

        department = self._normalize_department(department)
        if department:
            query = query.filter(func.lower(ResearchProject.department) == department.lower())

        publications = query.all()
        details = []

        for pub in publications:
            project = ResearchProject.query.get(pub.project_id)
            faculty = project.get_faculty() if project else None
            details.append({
                'publication_id': pub.publication_id,
                'project_id': pub.project_id,
                'project_title': project.project_title if project else '',
                'title': pub.title,
                'publication_type': pub.publication_type or '',
                'venue': pub.venue or '',
                'publication_date': pub.publication_date.isoformat() if pub.publication_date else None,
                'indexing': pub.indexing or '',
                'page_number': pub.page_number or '',
                'year_of_publication': pub.year_of_publication,
                'volume': pub.volume or '',
                'doi': pub.doi or '',
                'issn_isbn': pub.issn_isbn or '',
                'publisher': pub.publisher or '',
                'document_url': pub.document_url or '',
                'status': pub.status or '',
                'created_at': pub.created_at.isoformat() if pub.created_at else None,
                'updated_at': pub.updated_at.isoformat() if pub.updated_at else None,
                'faculty': {
                    'person_id': getattr(faculty, 'person_id', None),
                    'name': getattr(faculty, 'name', ''),
                    'email': getattr(faculty, 'email', ''),
                    'department': getattr(faculty, 'department', ''),
                } if faculty else {},
            })

        return details

    def get_ipr_details(self, year=None, department=None):
        """Return all IPR records with related project and publication data."""
        query = IPR.query.join(
            ResearchProject, IPR.project_id == ResearchProject.project_id
        )

        department = self._normalize_department(department)
        if department:
            query = query.filter(func.lower(ResearchProject.department) == department.lower())

        iprs = query.all()
        details = []

        for ipr in iprs:
            project = ResearchProject.query.get(ipr.project_id)
            publication = Publication.query.get(ipr.publication_id) if ipr.publication_id else None
            faculty = project.get_faculty() if project else None
            details.append({
                'ipr_id': ipr.ipr_id,
                'project_id': ipr.project_id,
                'project_title': project.project_title if project else '',
                'publication_id': ipr.publication_id,
                'publication_title': publication.title if publication else '',
                'innovation_title': ipr.innovation_title or '',
                'ipr_type': ipr.ipr_type or '',
                'application_number': ipr.application_number or '',
                'filing_date': ipr.filing_date.isoformat() if ipr.filing_date else None,
                'registration_date': ipr.registration_date.isoformat() if ipr.registration_date else None,
                'grant_date': ipr.grant_date.isoformat() if ipr.grant_date else None,
                'expiry_date': ipr.expiry_date.isoformat() if ipr.expiry_date else None,
                'grant_status': ipr.grant_status or '',
                'ownership_type': ipr.ownership_type or '',
                'document_url': ipr.document_url or '',
                'created_at': ipr.created_at.isoformat() if ipr.created_at else None,
                'updated_at': ipr.updated_at.isoformat() if ipr.updated_at else None,
                'faculty': {
                    'person_id': getattr(faculty, 'person_id', None),
                    'name': getattr(faculty, 'name', ''),
                    'email': getattr(faculty, 'email', ''),
                    'department': getattr(faculty, 'department', ''),
                } if faculty else {},
            })

        return details

    def get_startup_details(self, year=None, department=None):
        """Return all startup records with related project and faculty details."""
        query = Startup.query.join(
            ResearchProject, Startup.project_id == ResearchProject.project_id
        )

        department = self._normalize_department(department)
        if department:
            query = query.filter(func.lower(ResearchProject.department) == department.lower())

        startups = query.all()
        details = []

        for startup in startups:
            project = ResearchProject.query.get(startup.project_id)
            faculty = project.get_faculty() if project else None
            details.append({
                'startup_id': startup.startup_id,
                'project_id': startup.project_id,
                'project_title': project.project_title if project else '',
                'startup_name': startup.startup_name or '',
                'registration_number': startup.registration_number or '',
                'revenue_generated': startup.revenue_generated or 0,
                'development_status': startup.development_status or '',
                'fund_amount': startup.fund_amount or 0,
                'created_at': startup.created_at.isoformat() if startup.created_at else None,
                'updated_at': startup.updated_at.isoformat() if startup.updated_at else None,
                'faculty': {
                    'person_id': getattr(faculty, 'person_id', None),
                    'name': getattr(faculty, 'name', ''),
                    'email': getattr(faculty, 'email', ''),
                    'department': getattr(faculty, 'department', ''),
                } if faculty else {},
            })

        return details

    def get_faculty_details(self, year=None, department=None):
        """Return faculty records with engagement metrics."""
        faculty_query = Person.query.filter_by(type='Faculty')
        if department and department != 'All':
            department_filter = department.strip().lower()
            faculty_query = faculty_query.filter(func.lower(Person.department) == department_filter)

        details = []
        for faculty in faculty_query.all():
            projects_count = ResearchProject.query.filter_by(faculty_id=faculty.person_id).count()
            publications_count = db.session.query(func.count(Publication.publication_id)).join(
                ResearchProject, Publication.project_id == ResearchProject.project_id
            ).filter(ResearchProject.faculty_id == faculty.person_id).scalar()
            iprs_count = db.session.query(func.count(IPR.ipr_id)).join(
                ResearchProject, IPR.project_id == ResearchProject.project_id
            ).filter(ResearchProject.faculty_id == faculty.person_id).scalar()
            startups_count = db.session.query(func.count(Startup.startup_id)).join(
                ResearchProject, Startup.project_id == ResearchProject.project_id
            ).filter(ResearchProject.faculty_id == faculty.person_id).scalar()

            details.append({
                'person_id': faculty.person_id,
                'name': faculty.name,
                'email': faculty.email,
                'department': faculty.department or '',
                'type': faculty.type,
                'is_approved': bool(faculty.is_approved),
                'skills': faculty.skills or '',
                'resume_url': faculty.resume_url or '',
                'bio': faculty.bio or '',
                'phone': faculty.phone or '',
                'project_count': projects_count,
                'publication_count': publications_count or 0,
                'ipr_count': iprs_count or 0,
                'startup_count': startups_count or 0,
            })

        return details

    def get_student_details(self, year=None, department=None):
        """Return student records with research participation metrics."""
        student_query = Person.query.filter_by(type='Student')
        if department and department != 'All':
            department_filter = department.strip().lower()
            student_query = student_query.filter(func.lower(Person.department) == department_filter)

        details = []
        for student in student_query.all():
            projects_count = db.session.query(func.count(ProjectPerson.project_id)).filter(
                ProjectPerson.person_id == student.person_id
            ).scalar()
            details.append({
                'person_id': student.person_id,
                'name': student.name,
                'email': student.email,
                'department': student.department or '',
                'type': student.type,
                'is_approved': bool(student.is_approved),
                'skills': student.skills or '',
                'resume_url': student.resume_url or '',
                'bio': student.bio or '',
                'phone': student.phone or '',
                'project_count': projects_count or 0,
            })

        return details

    # ==================== HELPER METHODS ====================
    
    def _group_by_domain(self, projects):
        """Group projects by domain"""
        domains = {}
        for project in projects:
            domain = project.domain or 'Unspecified'
            domains[domain] = domains.get(domain, 0) + 1
        return domains
    
    def _group_by_department(self, projects):
        """Group projects by department"""
        departments = {}
        for project in projects:
            dept = project.department or 'Unspecified'
            departments[dept] = departments.get(dept, 0) + 1
        return departments
    
    def _avg_team_size(self, projects):
        """Calculate average team size"""
        if not projects:
            return 0
        total_team_size = sum([p.team_size or 0 for p in projects])
        return total_team_size / len(projects)
    
    def _avg_citations(self, publications):
        """Calculate average citations (if field exists)"""
        # Publication model doesn't have citations field, return 0
        return 0
    
    def _avg_days_to_grant(self, iprs):
        """Calculate average days from filing to grant"""
        granted = [ipr for ipr in iprs if ipr.grant_status == 'Granted' and ipr.filing_date and ipr.grant_date]
        if not granted:
            return 0
        
        total_days = sum([(ipr.grant_date - ipr.filing_date).days for ipr in granted])
        return total_days / len(granted)
    
    # ==================== REPORT GENERATION ====================
    
    def generate_comprehensive_report(self, year=None, department=None):
        """
        Generate comprehensive accreditation report
        Returns: dict with all metrics
        """
        if not year:
            year = self.report_date.year

        title = f'CCEW Institutional Accreditation Report - {year}'
        if department and department != 'All':
            title = f'{title} - {department}'

        report = {
            'report_title': title,
            'report_date': self.report_date.isoformat(),
            'academic_year': year,
            'department': department or 'All',
            'institution': 'Cummins College of Engineering for Women, Pune',

            'projects': self.get_project_metrics(year, department),
            'publications': self.get_publication_metrics(year, department),
            'iprs': self.get_ipr_metrics(year, department),
            'startups': self.get_startup_metrics(year, department),
            'faculty': self.get_faculty_metrics(year, department),
            'students': self.get_student_metrics(year, department),

            'project_records': self.get_project_details(year, department),
            'publication_records': self.get_publication_details(year, department),
            'ipr_records': self.get_ipr_details(year, department),
            'startup_records': self.get_startup_details(year, department),
            'faculty_records': self.get_faculty_details(year, department),
            'student_records': self.get_student_details(year, department),
        }
        
        # Add summary
        report['summary'] = self._generate_summary(report)
        
        return report
    
    def _generate_summary(self, report):
        """Generate executive summary"""
        return {
            'highlights': [
                f"Total Approved Projects: {report['projects']['approved_projects']}",
                f"Research Publications: {report['publications']['total_publications']}",
                f"IPR/Patents Filed: {report['iprs']['total_iprs_filed']}",
                f"Startups Incubated: {report['startups']['total_startups']}",
                f"Faculty Active in Research: {report['faculty']['faculty_with_projects']}",
                f"Students Engaged in Research: {report['students']['students_in_projects']}",
            ],
            'key_metrics': {
                'research_productivity': report['projects']['approved_projects'] + report['publications']['total_publications'],
                'innovation_index': report['iprs']['total_iprs_filed'] + report['startups']['total_startups'],
                'stakeholder_engagement': report['faculty']['total_faculty'] + report['students']['total_students'],
            }
        }
    
    def generate_pdf_report(self, year=None, department=None):
        """
        Generate PDF report (heavy operation)
        Should be run asynchronously with Celery
        """
        report_data = self.generate_comprehensive_report(year, department)

        # Format for PDF generation
        pdf_content = self._format_for_pdf(report_data)

        return {
            'data': report_data,
            'pdf_content': pdf_content,
            'filename': f"CCEW_Accreditation_Report_{year or self.report_date.year}.pdf"
        }
    
    def _render_records_table(self, title, records, columns):
        """Render a generic HTML table of records for PDF output."""
        html = f"""
    <h2>{title}</h2>
    <table>
        <tr>
"""
        for _, heading in columns:
            html += f"            <th>{heading}</th>\n"
        html += "        </tr>\n"

        if not records:
            html += '        <tr><td colspan="{0}" style="color:#718096;">No records found.</td></tr>\n'.format(len(columns))
        else:
            for record in records:
                html += '        <tr>'
                for key, _ in columns:
                    value = record.get(key, '')
                    if isinstance(value, list):
                        value = ', '.join(str(v) for v in value)
                    elif isinstance(value, dict):
                        value = ', '.join(f"{k}: {v}" for k, v in value.items() if v)
                    elif value is None:
                        value = ''
                    html += f"<td>{value}</td>"
                html += '</tr>\n'

        html += "    </table>\n"
        return html

    def _format_for_pdf(self, report_data):
        """Format report data for PDF rendering"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #0B3D91; text-align: center; }}
        h2 {{ color: #0B3D91; margin-top: 30px; border-bottom: 2px solid #D4AF37; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background-color: #0B3D91; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>{report_data['report_title']}</h1>
    <p style="text-align: center; color: #666;">
        Report Date: {report_data['report_date']}<br>
        Academic Year: {report_data['academic_year']}<br>
        Department: {report_data.get('department', 'All')}
    </p>
    
    <h2>Executive Summary</h2>
    <ul>
"""
        
        for highlight in report_data['summary']['highlights']:
            html += f"<li>{highlight}</li>"
        
        html += """
    </ul>
    
    <h2>Research Projects Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Count</th>
        </tr>
"""
        
        for key, value in report_data['projects'].items():
            if isinstance(value, (int, float)):
                html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
        
        html += """
    </table>
    
    <h2>Publication Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Count</th>
        </tr>
"""
        
        for key, value in report_data['publications'].items():
            if isinstance(value, (int, float)):
                html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
        
        html += """
    </table>
    
    <h2>IPR & Patent Metrics</h2>
    <table>
        <tr>
            <th>IPR Type</th>
            <th>Count</th>
        </tr>
"""
        
        for key, value in report_data['iprs'].items():
            if isinstance(value, (int, float)):
                html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
        
        html += """
    </table>
    
    <h2>Startup Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
"""
        
        for key, value in report_data['startups'].items():
            if isinstance(value, (int, float)):
                html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
        
        html += """
    </table>

"""
        html += self._render_records_table(
            'Project Records',
            report_data.get('project_records', []),
            [
                ('project_id', 'Project ID'),
                ('project_title', 'Title'),
                ('project_description', 'Description'),
                ('domain', 'Domain'),
                ('department', 'Department'),
                ('project_status', 'Status'),
                ('team_size', 'Team Size'),
                ('start_date', 'Start Date'),
                ('end_date', 'End Date'),
                ('iic_registration_status', 'IIC Status'),
                ('project_level', 'Level'),
                ('program_location', 'Location'),
                ('is_approved', 'Approved'),
                ('is_startup_converted', 'Startup Converted'),
                ('faculty', 'Faculty'),
                ('team_members', 'Team Members'),
            ]
        )

        html += self._render_records_table(
            'Publication Records',
            report_data.get('publication_records', []),
            [
                ('publication_id', 'Publication ID'),
                ('project_id', 'Project ID'),
                ('project_title', 'Project Title'),
                ('title', 'Title'),
                ('publication_type', 'Type'),
                ('venue', 'Venue'),
                ('publication_date', 'Publication Date'),
                ('indexing', 'Indexing'),
                ('page_number', 'Pages'),
                ('year_of_publication', 'Year'),
                ('volume', 'Volume'),
                ('doi', 'DOI'),
                ('issn_isbn', 'ISSN/ISBN'),
                ('publisher', 'Publisher'),
                ('document_url', 'Document URL'),
                ('status', 'Status'),
                ('faculty', 'Faculty'),
            ]
        )

        html += self._render_records_table(
            'IPR Records',
            report_data.get('ipr_records', []),
            [
                ('ipr_id', 'IPR ID'),
                ('project_id', 'Project ID'),
                ('project_title', 'Project Title'),
                ('publication_id', 'Publication ID'),
                ('publication_title', 'Publication Title'),
                ('innovation_title', 'Innovation Title'),
                ('ipr_type', 'Type'),
                ('application_number', 'Application #'),
                ('filing_date', 'Filing Date'),
                ('registration_date', 'Registration Date'),
                ('grant_date', 'Grant Date'),
                ('expiry_date', 'Expiry Date'),
                ('grant_status', 'Status'),
                ('ownership_type', 'Ownership'),
                ('document_url', 'Document URL'),
                ('faculty', 'Faculty'),
            ]
        )

        html += self._render_records_table(
            'Startup Records',
            report_data.get('startup_records', []),
            [
                ('startup_id', 'Startup ID'),
                ('project_id', 'Project ID'),
                ('project_title', 'Project Title'),
                ('startup_name', 'Startup Name'),
                ('registration_number', 'Registration #'),
                ('development_status', 'Status'),
                ('fund_amount', 'Funds'),
                ('revenue_generated', 'Revenue'),
                ('faculty', 'Faculty'),
            ]
        )

        html += self._render_records_table(
            'Faculty Records',
            report_data.get('faculty_records', []),
            [
                ('person_id', 'Faculty ID'),
                ('name', 'Name'),
                ('email', 'Email'),
                ('department', 'Department'),
                ('is_approved', 'Approved'),
                ('skills', 'Skills'),
                ('resume_url', 'Resume URL'),
                ('bio', 'Bio'),
                ('phone', 'Phone'),
                ('project_count', 'Projects'),
                ('publication_count', 'Publications'),
                ('ipr_count', 'IPRs'),
                ('startup_count', 'Startups'),
            ]
        )

        html += self._render_records_table(
            'Student Records',
            report_data.get('student_records', []),
            [
                ('person_id', 'Student ID'),
                ('name', 'Name'),
                ('email', 'Email'),
                ('department', 'Department'),
                ('is_approved', 'Approved'),
                ('skills', 'Skills'),
                ('resume_url', 'Resume URL'),
                ('bio', 'Bio'),
                ('phone', 'Phone'),
                ('project_count', 'Projects'),
            ]
        )

        html += """
    <footer style="margin-top: 50px; text-align: center; color: #666; font-size: 0.9em;">
        <p>This is an auto-generated accreditation report from CCEW Research Portal</p>
        <p>Cummins College of Engineering for Women, Pune</p>
    </footer>
</body>
</html>
        """
        
        return html
    
    def export_to_json(self, year=None, department=None):
        """Export report as JSON"""
        report_data = self.generate_comprehensive_report(year, department)
        return json.dumps(report_data, indent=2, default=str)
