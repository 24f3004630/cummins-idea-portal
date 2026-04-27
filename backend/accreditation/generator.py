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

        if year:
            query = query.filter(
                extract('year', ResearchProject.start_date) == year
            )

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

        if year:
            query = query.filter(
                Publication.year_of_publication == year
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

        if year:
            query = query.filter(
                extract('year', IPR.filing_date) == year
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

        if year:
            query = query.filter(
                extract('year', ResearchProject.start_date) == year
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
            if year:
                project_query = project_query.filter(
                    extract('year', ResearchProject.start_date) == year
                )
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
            if year:
                pub_query = pub_query.filter(
                    extract('year', ResearchProject.start_date) == year
                )
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
            if year:
                ipr_query = ipr_query.filter(
                    extract('year', ResearchProject.start_date) == year
                )
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
            if year:
                project_query = project_query.filter(
                    extract('year', ResearchProject.start_date) == year
                )
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
