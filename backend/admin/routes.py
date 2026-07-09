from flask import Blueprint, render_template, request, redirect, jsonify
from backend.database.models import Person, ResearchProject, Publication, IPR, Startup, ProjectPerson, Competition, ProjectCompetition
from backend.database.db import db
from auth.decorators import login_required, role_required
from sqlalchemy import func
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _fire_task(task_fn, *args, **kwargs):
    """Fire a Celery task safely; log and continue if Celery/Redis is unavailable."""
    import logging
    try:
        task_fn.delay(*args, **kwargs)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            f"[admin] Could not queue task {task_fn.name}: {exc}"
        )



# ---------------- DASHBOARD ----------------
@admin_bp.route('/dashboard')
@login_required
@role_required('Admin')
def dashboard():
    total_users = Person.query.count()
    total_students = Person.query.filter_by(type='Student').count()
    total_faculty = Person.query.filter_by(type='Faculty').count()
    active_users = Person.query.filter_by(is_approved=True).count()
    total_projects = ResearchProject.query.count()
    total_publications = Publication.query.count()
    total_iprs = IPR.query.count()
    total_startups = Startup.query.count()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_students=total_students,
                           total_faculty=total_faculty,
                           active_users=active_users,
                           total_projects=total_projects,
                           total_publications=total_publications,
                           total_iprs=total_iprs,
                           total_startups=total_startups)


# ==================== ANALYTICS API ====================
@admin_bp.route('/api/analytics/users')
@login_required
@role_required('Admin')
def api_analytics_users():
    """Get user distribution analytics"""
    total = Person.query.count()
    students = Person.query.filter_by(type='Student').count()
    faculty = Person.query.filter_by(type='Faculty').count()
    approved = Person.query.filter_by(is_approved=True).count()
    pending = Person.query.filter_by(is_approved=False).count()
    
    return jsonify({
        'total': total,
        'students': students,
        'faculty': faculty,
        'approved': approved,
        'pending': pending
    })


@admin_bp.route('/api/analytics/projects')
@login_required
@role_required('Admin')
def api_analytics_projects():
    """Get project status distribution"""
    proposed = ResearchProject.query.filter_by(project_status='Proposed').count()
    ongoing = ResearchProject.query.filter_by(project_status='Ongoing').count()
    completed = ResearchProject.query.filter_by(project_status='Completed').count()
    on_hold = ResearchProject.query.filter_by(project_status='On Hold').count()
    
    return jsonify({
        'proposed': proposed,
        'ongoing': ongoing,
        'completed': completed,
        'on_hold': on_hold
    })


@admin_bp.route('/api/analytics/publications')
@login_required
@role_required('Admin')
def api_analytics_publications():
    """Get publication status distribution"""
    submitted = Publication.query.filter_by(status='Submitted').count()
    accepted = Publication.query.filter_by(status='Accepted').count()
    published = Publication.query.filter_by(status='Published').count()
    rejected = Publication.query.filter_by(status='Rejected').count()
    
    return jsonify({
        'submitted': submitted,
        'accepted': accepted,
        'published': published,
        'rejected': rejected
    })


@admin_bp.route('/api/analytics/iprs')
@login_required
@role_required('Admin')
def api_analytics_iprs():
    """Get IPR grant status distribution"""
    filed = IPR.query.filter_by(grant_status='Filed').count()
    pending = IPR.query.filter_by(grant_status='Pending').count()
    granted = IPR.query.filter_by(grant_status='Granted').count()
    rejected = IPR.query.filter_by(grant_status='Rejected').count()
    
    return jsonify({
        'filed': filed,
        'pending': pending,
        'granted': granted,
        'rejected': rejected
    })


@admin_bp.route('/api/analytics/domains')
@login_required
@role_required('Admin')
def api_analytics_domains():
    """Get projects by domain"""
    results = db.session.query(
        ResearchProject.domain,
        func.count(ResearchProject.project_id)
    ).filter(ResearchProject.domain != None).group_by(ResearchProject.domain).all()
    
    domains = [r[0] for r in results]
    counts = [r[1] for r in results]
    
    return jsonify({
        'domains': domains,
        'counts': counts
    })


# ---------------- VIEW USERS ----------------
@admin_bp.route('/users')
@login_required
@role_required('Admin')
def view_users():
    users = Person.query.all()
    return render_template('admin/users.html', users=users)


# ---------------- VIEW PENDING FACULTY ----------------
@admin_bp.route('/pending_faculty')
@login_required
@role_required('Admin')
def view_pending_faculty():
    pending_faculty = Person.query.filter_by(type='Faculty', is_approved=False).all()
    return render_template('admin/pending_faculty.html', users=pending_faculty)


# ---------------- APPROVE FACULTY ----------------
@admin_bp.route('/approve/<int:user_id>')
@login_required
@role_required('Admin')
def approve_user(user_id):
    user = Person.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
        # Email the faculty that their account is now active
        if user.type == 'Faculty':
            from tasks.mail_tasks import send_faculty_approved_email
            _fire_task(send_faculty_approved_email, user.person_id)
    return redirect('/admin/users')


# ---------------- REJECT USER ----------------
@admin_bp.route('/reject/<int:user_id>')
@login_required
@role_required('Admin')
def reject_user(user_id):
    user = Person.query.get(user_id)
    if user:
        user.is_approved = False
        db.session.commit()
    return redirect('/admin/users')


# ---------------- DEACTIVATE USER ----------------
@admin_bp.route('/deactivate/<int:user_id>')
@login_required
@role_required('Admin')
def deactivate_user(user_id):
    user = Person.query.get(user_id)
    if user:
        user.is_approved = False
        db.session.commit()
    return redirect('/admin/users')


# ---------------- REJECT / DELETE USER ----------------
@admin_bp.route('/delete/<int:user_id>')
@login_required
@role_required('Admin')
def delete_user(user_id):
    user = Person.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect('/admin/users')


# ---------------- SEARCH USERS ----------------
@admin_bp.route('/search', methods=['GET'])
@login_required
@role_required('Admin')
def search_users():
    query = request.args.get('q')
    users = Person.query.filter(Person.name.contains(query)).all()
    return render_template('admin/users.html', users=users)


# ---------------- VIEW PROJECTS ----------------
@admin_bp.route('/projects')
@login_required
@role_required('Admin')
def view_projects():
    projects = ResearchProject.query.all()
    return render_template('admin/projects.html', projects=projects)


# ---------------- APPROVE PROJECT ----------------
@admin_bp.route('/approve_project/<int:project_id>')
@login_required
@role_required('Admin')
def approve_project(project_id):
    project = ResearchProject.query.get(project_id)
    if project:
        project.is_approved = True
        if project.project_status == 'Proposed':
            project.project_status = 'Ongoing'
        db.session.commit()
    return redirect('/admin/projects')


# ==================== VIEW PROJECTS BY STATUS ====================
@admin_bp.route('/projects/status/<status>')
@login_required
@role_required('Admin')
def projects_by_status(status):
    """View projects filtered by status"""
    valid_statuses = ['Proposed', 'Ongoing', 'Completed', 'On Hold']
    
    if status not in valid_statuses:
        return "Invalid status", 400
    
    projects = ResearchProject.query.filter_by(project_status=status).all()
    
    for project in projects:
        project.faculty = Person.query.get(project.faculty_id)
    
    return render_template('admin/projects_by_status.html',
                         projects=projects,
                         status=status)


# ==================== PROJECT LIFECYCLE VIEW ====================
@admin_bp.route('/project/<int:project_id>/lifecycle')
@login_required
@role_required('Admin')
def project_lifecycle(project_id):
    """View full project lifecycle: Project → Publication → IPR → Startup"""
    from database.models import Startup
    
    project = ResearchProject.query.get(project_id)
    
    if not project:
        return "Project not found", 404
    
    faculty = Person.query.get(project.faculty_id)
    team_members = db.session.query(ProjectPerson, Person).filter(
        ProjectPerson.project_id == project_id,
        ProjectPerson.person_id == Person.person_id
    ).all()
    
    # Get all output artifacts
    publications = Publication.query.filter_by(project_id=project_id).all()
    iprs = IPR.query.filter_by(project_id=project_id).all()
    startup = Startup.query.filter_by(project_id=project_id).first()
    
    return render_template('admin/project_lifecycle.html',
                         project=project,
                         faculty=faculty,
                         team_members=team_members,
                         publications=publications,
                         iprs=iprs,
                         startup=startup)


# ==================== PUBLICATION MONITORING ====================
@admin_bp.route('/publications')
@login_required
@role_required('Admin')
def view_publications():
    """View all publications with their statuses"""
    publications = Publication.query.all()
    
    pub_data = []
    for pub in publications:
        project = ResearchProject.query.get(pub.project_id)
        pub_data.append({
            'publication': pub,
            'project': project,
            'faculty': Person.query.get(project.faculty_id) if project else None
        })
    
    return render_template('admin/publications.html', pub_data=pub_data)


# ==================== IPR/PATENT MONITORING ====================
@admin_bp.route('/iprs')
@login_required
@role_required('Admin')
def view_iprs():
    """View all IPRs/Patents with their grant statuses"""
    iprs = IPR.query.all()
    
    ipr_data = []
    for ipr in iprs:
        project = ResearchProject.query.get(ipr.project_id)
        ipr_data.append({
            'ipr': ipr,
            'project': project,
            'faculty': Person.query.get(project.faculty_id) if project else None
        })
    
    return render_template('admin/iprs.html', ipr_data=ipr_data)


# ==================== STARTUP TRACKING ====================
@admin_bp.route('/startups')
@login_required
@role_required('Admin')
def view_startups():
    """View all startups converted from projects"""
    startups = Startup.query.all()
    
    startup_data = []
    for startup in startups:
        project = ResearchProject.query.get(startup.project_id)
        startup_data.append({
            'startup': startup,
            'project': project,
            'faculty': Person.query.get(project.faculty_id) if project else None
        })
    
    return render_template('admin/startups.html', startup_data=startup_data)


# ==================== STARTUP UPDATE ====================
@admin_bp.route('/startup/<int:startup_id>/update', methods=['POST'])
@login_required
@role_required('Admin')
def update_startup(startup_id):
    """Update startup details"""
    startup = Startup.query.get(startup_id)
    
    if not startup:
        return jsonify({'status': 'error', 'message': 'Startup not found'}), 404
    
    try:
        startup.startup_name = request.form.get('startup_name', startup.startup_name)
        startup.registration_number = request.form.get('registration_number', startup.registration_number)
        startup.development_status = request.form.get('development_status', startup.development_status)
        startup.fund_amount = float(request.form.get('fund_amount', startup.fund_amount) or 0)
        startup.revenue_generated = float(request.form.get('revenue_generated', startup.revenue_generated) or 0)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Startup updated successfully',
            'startup': {
                'startup_id': startup.startup_id,
                'startup_name': startup.startup_name,
                'development_status': startup.development_status,
                'fund_amount': startup.fund_amount,
                'revenue_generated': startup.revenue_generated
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== COMPETITIONS TRACKING ====================
@admin_bp.route('/competitions')
@login_required
@role_required('Admin')
def view_competitions():
    """View all competitions across all projects"""
    # Get all project competitions
    project_competitions = db.session.query(
        ProjectCompetition, Competition, ResearchProject, Person
    ).join(
        Competition, ProjectCompetition.competition_id == Competition.competition_id
    ).join(
        ResearchProject, ProjectCompetition.project_id == ResearchProject.project_id
    ).join(
        Person, ResearchProject.faculty_id == Person.person_id
    ).all()
    
    competitions = []
    for pc, comp, proj, faculty in project_competitions:
        competitions.append({
            'project_competition': pc,
            'competition': comp,
            'project': proj,
            'faculty': faculty
        })
    
    return render_template('admin/competitions.html', competitions=competitions)


# ==================== ACCREDITATION REPORTS ====================
@admin_bp.route('/accreditation')
@login_required
@role_required('Admin')
def accreditation_dashboard():
    """Accreditation report dashboard"""
    from backend.accreditation.generator import AccreditationReportGenerator
    
    current_year = request.args.get('year', default=datetime.now().year, type=int)
    
    generator = AccreditationReportGenerator()
    report = generator.generate_comprehensive_report(current_year)
    
    return render_template('admin/accreditation.html', 
                         report=report,
                         current_year=current_year,
                         available_years=list(range(2020, datetime.now().year + 1)))


@admin_bp.route('/accreditation/generate', methods=['POST'])
@login_required
@role_required('Admin')
def generate_accreditation_report():
    """Dispatch accreditation report generation as a Celery background task."""
    data = request.get_json(silent=True) or request.form
    year = data.get('year', datetime.now().year)
    report_format = data.get('format', 'pdf')

    try:
        year = int(year)
    except (TypeError, ValueError):
        year = datetime.now().year

    try:
        if report_format == 'csv':
            from backend.tasks.report_tasks import generate_accreditation_csv
            task = generate_accreditation_csv.delay(year)
        else:
            from backend.tasks.report_tasks import generate_accreditation_pdf
            task = generate_accreditation_pdf.delay(year)

        return jsonify({
            'status': 'queued',
            'task_id': task.id,
            'year': year,
            'format': report_format,
            'message': f'{report_format.upper()} report generation started. '
                       f'Poll /admin/task-status/{task.id} for progress.',
            'poll_url': f'/admin/task-status/{task.id}',
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== TASK STATUS POLLING ====================
@admin_bp.route('/task-status/<task_id>')
@login_required
@role_required('Admin')
def task_status(task_id):
    """
    Poll the status of any Celery background task.
    State values: PENDING | STARTED | PROGRESS | SUCCESS | FAILURE
    """
    from backend.app import celery
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery)
    state = result.state

    if state == 'PENDING':
        response = {'state': state, 'status': 'Task is waiting to be picked up by a worker…'}
    elif state == 'STARTED':
        response = {'state': state, 'status': 'Task has started…'}
    elif state == 'PROGRESS':
        meta = result.info or {}
        response = {
            'state': state,
            'step': meta.get('step', ''),
            'pct': meta.get('pct', 0),
        }
    elif state == 'SUCCESS':
        response = {'state': state, 'result': result.result}
    else:  # FAILURE or REVOKED
        response = {
            'state': state,
            'error': str(result.info) if result.info else 'Unknown error',
        }

    return jsonify(response)


# ==================== MANUAL REMINDER TRIGGER ====================
@admin_bp.route('/send-reminder', methods=['POST'])
@login_required
@role_required('Admin')
def send_reminder():
    """
    Manually trigger the weekly report-fill reminder blast.
    Sends emails to all active faculty + students immediately.
    POST body (JSON or form): { "target": "all" | "faculty" | "students" }
    """
    from backend.tasks.mail_tasks import (
        send_report_reminder_all_faculty,
        send_report_reminder_all_students,
    )

    data = request.get_json(silent=True) or request.form
    target = (data.get('target') or 'all').lower()
    queued = []

    try:
        if target in ('all', 'faculty'):
            t1 = send_report_reminder_all_faculty.delay()
            queued.append({'audience': 'faculty', 'task_id': t1.id})

        if target in ('all', 'students'):
            t2 = send_report_reminder_all_students.delay()
            queued.append({'audience': 'students', 'task_id': t2.id})

        return jsonify({
            'status': 'queued',
            'message': 'Reminder emails are being sent in the background.',
            'tasks': queued,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_bp.route('/accreditation/download/<format>')
@login_required
@role_required('Admin')
def download_accreditation_report(format):
    """Download accreditation report in specified format"""
    from backend.accreditation.generator import AccreditationReportGenerator
    from flask import send_file
    import csv
    from io import StringIO, BytesIO
    
    year = request.args.get('year', default=datetime.now().year, type=int)
    
    try:
        generator = AccreditationReportGenerator()
        report = generator.generate_comprehensive_report(year)
        
        if format == 'json':
            json_data = generator.export_to_json(year)
            return send_file(
                BytesIO(json_data.encode()),
                mimetype='application/json',
                as_attachment=True,
                download_name=f'CCEW_Accreditation_{year}.json'
            )
        
        elif format == 'csv':
            # Convert report to CSV
            output = StringIO()
            writer = csv.writer(output)
            
            writer.writerow(['Metric', 'Value'])
            writer.writerow([])
            
            writer.writerow(['PROJECTS METRICS'])
            for key, value in report['projects'].items():
                if isinstance(value, (int, float)):
                    writer.writerow([key, value])
            
            writer.writerow([])
            writer.writerow(['PUBLICATION METRICS'])
            for key, value in report['publications'].items():
                if isinstance(value, (int, float)):
                    writer.writerow([key, value])
            
            writer.writerow([])
            writer.writerow(['IPR METRICS'])
            for key, value in report['iprs'].items():
                if isinstance(value, (int, float)):
                    writer.writerow([key, value])
            
            writer.writerow([])
            writer.writerow(['STARTUP METRICS'])
            for key, value in report['startups'].items():
                if isinstance(value, (int, float)):
                    writer.writerow([key, value])
            
            output.seek(0)
            return send_file(
                BytesIO(output.getvalue().encode()),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'CCEW_Accreditation_{year}.csv'
            )
    
    except Exception as e:
        return f"Error generating report: {str(e)}", 500


# ==================== PROJECT APPROVAL WORKFLOW ====================
@admin_bp.route('/projects/pending-approval')
@login_required
@role_required('Admin')
def pending_projects():
    """View projects pending admin approval"""
    pending = ResearchProject.query.filter_by(is_approved=False).all()
    
    projects_data = []
    for project in pending:
        faculty = Person.query.get(project.faculty_id)
        team_members = ProjectPerson.query.filter_by(project_id=project.project_id).count()
        
        projects_data.append({
            'project': project,
            'faculty': faculty,
            'team_members': team_members
        })
    
    return render_template('admin/pending_projects.html', projects_data=projects_data)


@admin_bp.route('/project/<int:project_id>/approve-with-comments', methods=['POST'])
@login_required
@role_required('Admin')
def approve_project_with_comments(project_id):
    """Approve project with optional comments"""
    project = ResearchProject.query.get(project_id)
    
    if not project:
        return jsonify({'status': 'error', 'message': 'Project not found'}), 404
    
    try:
        project.is_approved = True

        # Update project status if Proposed
        if project.project_status == 'Proposed':
            project.project_status = 'Ongoing'

        # Store approval comments if provided
        comments = request.form.get('approval_comments')
        if comments:
            # Could store in a separate ApprovalNotes table if needed
            pass

        db.session.commit()

        # Email the faculty that their project is approved
        from tasks.mail_tasks import send_project_approved_email
        _fire_task(send_project_approved_email, project_id)

        return jsonify({
            'status': 'success',
            'message': 'Project approved successfully',
            'project_id': project_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


from datetime import datetime