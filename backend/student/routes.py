from flask import Blueprint, render_template, request, redirect, session, jsonify
from database.db import db
from database.models import (
    Person, ResearchProject, ProjectPerson, ProjectApplication, Publication, IPR, Startup,
    Competition, StudentCompetition
)
from auth.decorators import login_required, role_required, student_can_join_approved_projects
from datetime import datetime

student_bp = Blueprint('student', __name__, url_prefix='/student')


# ==================== DASHBOARD ====================
@student_bp.route('/dashboard')
@login_required
@role_required('Student')
def dashboard():
    """Student dashboard showing overview of projects and contributions"""
    student_id = session['user_id']
    student = Person.query.get(student_id)
    
    # Get joined projects (only from approved projects)
    joined_projects = db.session.query(
        ResearchProject
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        ResearchProject.is_approved == True  # Students can only be in approved projects
    ).all()
    
    # Get pending applications
    pending_applications = ProjectApplication.query.filter_by(
        student_id=student_id,
        status='Pending'
    ).all()
    
    # Get publications where student is involved
    publications = db.session.query(Publication).join(
        ResearchProject, Publication.project_id == ResearchProject.project_id
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        Publication.status == 'Published'  # Show only published
    ).all()
    
    # Get IPRs/Patents where student is involved
    iprs = db.session.query(IPR).join(
        Publication, IPR.publication_id == Publication.publication_id
    ).join(
        ResearchProject, Publication.project_id == ResearchProject.project_id
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        IPR.grant_status == 'Granted'  # Show only granted
    ).all()
    
    return render_template('student/dashboard.html',
                         student=student,
                         joined_projects=joined_projects,
                         pending_applications=pending_applications,
                         publications=publications,
                         iprs=iprs)


# ==================== UPDATE PROFILE ====================
@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('Student')
def update_profile():
    """Update student profile with skills, resume, and bio"""
    student_id = session['user_id']
    student = Person.query.get(student_id)
    
    if request.method == 'POST':
        try:
            student.name = request.form.get('name', student.name)
            student.email = request.form.get('email', student.email)
            student.phone = request.form.get('phone', '')
            student.department = request.form.get('department', '')
            student.bio = request.form.get('bio', '')
            student.skills = request.form.get('skills', '')
            
            if 'resume' in request.files:
                resume_file = request.files['resume']
                if resume_file and resume_file.filename:
                    student.resume_url = resume_file.filename
            
            db.session.commit()
            return redirect('/student/profile')
        except Exception as e:
            return f"Error updating profile: {str(e)}"
    
    return render_template('student/profile.html', student=student)


# ==================== SEARCH PROJECTS ====================
@student_bp.route('/projects', methods=['GET', 'POST'])
@login_required
@role_required('Student')
@student_can_join_approved_projects
def search_projects():
    """Search and view available APPROVED projects only"""
    student_id = session['user_id']
    
    domain_filter = request.args.get('domain', '').strip()
    faculty_filter = request.args.get('faculty', '').strip()
    status_filter = request.args.get('status', 'Ongoing').strip()
    
    # Base query - ONLY approved projects
    query = ResearchProject.query.filter_by(is_approved=True)
    
    if domain_filter:
        query = query.filter(ResearchProject.domain.ilike(f'%{domain_filter}%'))
    
    if status_filter:
        query = query.filter_by(project_status=status_filter)
    
    if faculty_filter:
        faculty_ids = db.session.query(Person.person_id).filter(
            Person.type == 'Faculty',
            Person.name.ilike(f'%{faculty_filter}%'),
            Person.is_approved == True  # Only from approved faculty
        ).all()
        faculty_ids = [f[0] for f in faculty_ids]
        query = query.filter(ResearchProject.faculty_id.in_(faculty_ids))
    
    # Exclude projects where student is already involved
    user_projects = db.session.query(ProjectPerson.project_id).filter(
        ProjectPerson.person_id == student_id
    ).all()
    user_projects = [p[0] for p in user_projects]
    
    projects = query.filter(~ResearchProject.project_id.in_(user_projects)).all()
    
    # Get faculty details
    project_faculty = {}
    for project in projects:
        faculty = Person.query.get(project.faculty_id)
        project_faculty[project.project_id] = faculty
    
    # Get unique domains
    all_domains = db.session.query(
        ResearchProject.domain.distinct()
    ).filter(ResearchProject.domain != None, ResearchProject.is_approved == True).all()
    domains = [d[0] for d in all_domains]
    
    all_faculty = Person.query.filter(Person.type == 'Faculty', Person.is_approved == True).all()
    
    return render_template('student/search_projects.html',
                         projects=projects,
                         project_faculty=project_faculty,
                         domains=domains,
                         all_faculty=all_faculty,
                         domain_filter=domain_filter,
                         faculty_filter=faculty_filter,
                         status_filter=status_filter)


# ==================== VIEW PROJECT DETAILS ====================
@student_bp.route('/project/<int:project_id>')
@login_required
@role_required('Student')
def view_project(project_id):
    """View detailed information about a project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or not project.is_approved:
        return "Project not found or not approved", 404
    
    student_id = session['user_id']
    
    already_joined = ProjectPerson.query.filter_by(
        project_id=project_id,
        person_id=student_id
    ).first()
    
    pending_application = ProjectApplication.query.filter_by(
        project_id=project_id,
        student_id=student_id,
        status='Pending'
    ).first()
    
    faculty = Person.query.get(project.faculty_id)
    
    team_members = db.session.query(
        ProjectPerson, Person
    ).filter(
        ProjectPerson.project_id == project_id,
        ProjectPerson.person_id == Person.person_id
    ).all()
    
    publications = Publication.query.filter_by(project_id=project_id).all()
    
    return render_template('student/project_view.html',
                         project=project,
                         faculty=faculty,
                         team_members=team_members,
                         publications=publications,
                         already_joined=already_joined,
                         pending_application=pending_application)


# ==================== REQUEST TO JOIN PROJECT ====================
@student_bp.route('/project/<int:project_id>/request-join', methods=['GET', 'POST'])
@login_required
@role_required('Student')
def request_join_project(project_id):
    """Request to join an APPROVED project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or not project.is_approved:
        return "Project not found or not approved", 404
    
    if not project.can_accept_students():
        return "This project is not accepting new members", 400
    
    student_id = session['user_id']
    
    if request.method == 'POST':
        try:
            existing_member = ProjectPerson.query.filter_by(
                project_id=project_id,
                person_id=student_id
            ).first()
            
            if existing_member:
                return "You are already part of this project", 400
            
            existing_app = ProjectApplication.query.filter_by(
                project_id=project_id,
                student_id=student_id,
                status='Pending'
            ).first()
            
            if existing_app:
                return "You have already applied to this project", 400
            
            application = ProjectApplication(
                project_id=project_id,
                student_id=student_id,
                student_message=request.form.get('message', ''),
                status='Pending'
            )
            
            db.session.add(application)
            db.session.commit()
            
            return redirect(f'/student/project/{project_id}')
        except Exception as e:
            return f"Error requesting to join: {str(e)}"
    
    return render_template('student/request_join.html', project=project)


# ==================== MY PROJECTS ====================
@student_bp.route('/my-projects')
@login_required
@role_required('Student')
def my_projects():
    """View all joined projects (only approved ones)"""
    student_id = session['user_id']
    
    joined_projects = db.session.query(
        ResearchProject, ProjectPerson
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        ResearchProject.is_approved == True
    ).all()
    
    project_faculty = {}
    for project, _ in joined_projects:
        faculty = Person.query.get(project.faculty_id)
        project_faculty[project.project_id] = faculty
    
    return render_template('student/my_projects.html',
                         joined_projects=joined_projects,
                         project_faculty=project_faculty)


# ==================== VIEW MY APPLICATIONS ====================
@student_bp.route('/applications')
@login_required
@role_required('Student')
def view_applications():
    """View all project applications and their status"""
    student_id = session['user_id']
    
    applications = ProjectApplication.query.filter_by(
        student_id=student_id
    ).all()
    
    application_projects = {}
    for app in applications:
        project = ResearchProject.query.get(app.project_id)
        faculty = Person.query.get(project.faculty_id) if project else None
        application_projects[app.application_id] = (project, faculty)
    
    return render_template('student/applications.html',
                         applications=applications,
                         application_projects=application_projects)


# ==================== CONTRIBUTIONS ====================
@student_bp.route('/contributions')
@login_required
@role_required('Student')
def contributions():
    """View contributions and track lifecycle"""
    student_id = session['user_id']
    
    projects = db.session.query(
        ResearchProject, ProjectPerson
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        ResearchProject.is_approved == True
    ).all()
    
    project_lifecycle = {}
    for project, _ in projects:
        publications = Publication.query.filter_by(project_id=project.project_id).all()
        iprs = db.session.query(IPR).join(
            Publication, IPR.publication_id == Publication.publication_id
        ).filter(
            Publication.project_id == project.project_id
        ).all()
        startup = Startup.query.filter_by(project_id=project.project_id).first()
        
        project_lifecycle[project.project_id] = {
            'publications': publications,
            'iprs': iprs,
            'startup': startup
        }
    
    return render_template('student/contributions.html',
                         projects=projects,
                         project_lifecycle=project_lifecycle)


# ==================== LEAVE PROJECT ====================
@student_bp.route('/project/<int:project_id>/leave', methods=['POST'])
@login_required
@role_required('Student')
def leave_project(project_id):
    """Leave a project"""
    student_id = session['user_id']
    
    project_person = ProjectPerson.query.filter_by(
        project_id=project_id,
        person_id=student_id
    ).first()
    
    if not project_person:
        return "You are not part of this project", 404
    
    try:
        db.session.delete(project_person)
        db.session.commit()
        return redirect('/student/my-projects')
    except Exception as e:
        return f"Error leaving project: {str(e)}"


# ==================== ANALYTICS APIs ====================
@student_bp.route('/api/analytics/projects')
@login_required
@role_required('Student')
def analytics_projects():
    """Get projects joined by student, grouped by status"""
    student_id = session['user_id']
    
    projects = db.session.query(
        ResearchProject, ProjectPerson
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        ResearchProject.is_approved == True
    ).all()
    
    status_count = {
        'Proposed': 0,
        'Ongoing': 0,
        'Completed': 0,
        'On Hold': 0
    }
    
    for project, _ in projects:
        if project.project_status in status_count:
            status_count[project.project_status] += 1
    
    return jsonify({
        'statuses': list(status_count.keys()),
        'counts': list(status_count.values())
    })


@student_bp.route('/api/analytics/contributions')
@login_required
@role_required('Student')
def analytics_contributions():
    """Get contribution breakdown (publications and IPRs) for student"""
    student_id = session['user_id']
    
    # Get projects student is part of
    student_projects = db.session.query(
        ResearchProject.project_id
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        ResearchProject.is_approved == True
    ).all()
    
    project_ids = [p[0] for p in student_projects]
    
    if not project_ids:
        return jsonify({
            'publication_count': 0,
            'ipr_count': 0,
            'startup_count': 0
        })
    
    # Get publications in these projects
    publications = Publication.query.filter(
        Publication.project_id.in_(project_ids)
    ).count()
    
    # Get IPRs in these projects
    iprs = db.session.query(IPR).join(
        Publication, IPR.publication_id == Publication.publication_id
    ).filter(
        Publication.project_id.in_(project_ids)
    ).count()
    
    # Get startups in these projects
    startups = Startup.query.filter(
        Startup.project_id.in_(project_ids)
    ).count()
    
    return jsonify({
        'publication_count': publications,
        'ipr_count': iprs,
        'startup_count': startups
    })


@student_bp.route('/api/analytics/skills-match')
@login_required
@role_required('Student')
def analytics_skills_match():
    """Get skill matching for projects joined"""
    student_id = session['user_id']
    
    student = Person.query.get(student_id)
    if not student or not student.skills:
        return jsonify({
            'skills': [],
            'matched_projects': [],
            'match_counts': []
        })
    
    student_skills = set(s.strip().lower() for s in student.skills.split(',') if s.strip())
    
    # Get projects student is part of
    projects = db.session.query(
        ResearchProject, ProjectPerson
    ).join(
        ProjectPerson, ResearchProject.project_id == ProjectPerson.project_id
    ).filter(
        ProjectPerson.person_id == student_id,
        ResearchProject.is_approved == True
    ).all()
    
    skill_match = {}
    for project, _ in projects:
        if project.required_skills:
            required_skills = set(s.strip().lower() for s in project.required_skills.split(',') if s.strip())
            match_count = len(student_skills.intersection(required_skills))
            skill_match[project.title] = match_count
    
    return jsonify({
        'projects': list(skill_match.keys()),
        'match_counts': list(skill_match.values())
    })


# ==================== COMPETITIONS (Student Independent) ====================
@student_bp.route('/competitions')
@login_required
@role_required('Student')
def view_competitions():
    """View all competitions added by the student"""
    student_id = session['user_id']
    
    # Get all competitions added by this student
    student_competitions = db.session.query(
        StudentCompetition, Competition
    ).join(
        Competition, StudentCompetition.competition_id == Competition.competition_id
    ).filter(
        StudentCompetition.student_id == student_id
    ).all()
    
    competitions = []
    for sc, comp in student_competitions:
        competitions.append({
            'student_competition': sc,
            'competition': comp
        })
    
    return render_template('student/competitions.html', competitions=competitions)


# ==================== ADD COMPETITION (Student) ====================
@student_bp.route('/competition/add', methods=['GET', 'POST'])
@login_required
@role_required('Student')
def add_competition():
    """Add a competition (without needing faculty)"""
    student_id = session['user_id']
    
    if request.method == 'POST':
        try:
            # Create competition
            competition = Competition(
                name=request.form.get('competition_name'),
                venue=request.form.get('venue'),
                organized_by=request.form.get('organized_by'),
                start_date_of_competition=request.form.get('start_date_of_competition') or None,
                end_date_of_competition=request.form.get('end_date_of_competition') or None
            )
            
            db.session.add(competition)
            db.session.flush()  # Get the competition_id without committing
            
            # Create student-competition link
            mentor_id = request.form.get('mentor_id')
            student_competition = StudentCompetition(
                student_id=student_id,
                competition_id=competition.competition_id,
                mentor_id=int(mentor_id) if mentor_id else None,
                team_name=request.form.get('team_name'),
                prize_money=float(request.form.get('prize_money', 0) or 0)
            )
            
            db.session.add(student_competition)
            db.session.commit()
            
            return redirect('/student/competitions')
        except Exception as e:
            db.session.rollback()
            return f"Error adding competition: {str(e)}", 400
    
    # GET request - load list of faculty mentors
    mentors = Person.query.filter_by(type='Faculty', is_approved=True).all()
    
    return render_template('student/add_competition.html', mentors=mentors)


# ==================== DELETE COMPETITION (Student) ====================
@student_bp.route('/competition/<int:competition_id>/delete', methods=['GET', 'POST'])
@login_required
@role_required('Student')
def delete_competition(competition_id):
    """Delete a competition added by student"""
    student_id = session['user_id']
    
    student_competition = StudentCompetition.query.filter_by(
        competition_id=competition_id,
        student_id=student_id
    ).first()
    
    if not student_competition:
        return "Competition not found or not yours", 404
    
    try:
        db.session.delete(student_competition)
        db.session.commit()
        return redirect('/student/competitions')
    except Exception as e:
        db.session.rollback()
        return f"Error deleting competition: {str(e)}", 400
