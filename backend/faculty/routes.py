from flask import Blueprint, render_template, request, redirect, session, jsonify, current_app
from database.db import db
from database.models import (
    Person, ResearchProject, ProjectPerson, Publication, IPR, Startup, 
    Competition, ProjectCompetition, Funder, ProjectFunding, PublicationAuthor, Author,
    StudentCompetition
)
from auth.decorators import login_required, role_required, faculty_can_create_projects, approved_required
from datetime import datetime
from sqlalchemy.orm import aliased
from werkzeug.utils import secure_filename
import os

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx'}


def allowed_document(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_DOCUMENT_EXTENSIONS


def save_uploaded_document(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    if not allowed_document(filename):
        return None
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        upload_folder = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file_storage.save(file_path)
    return f'/static/uploads/{filename}'


# ==================== DASHBOARD ====================
@faculty_bp.route('/dashboard')
@login_required
@role_required('Faculty')
def dashboard():
    """Faculty dashboard showing overview of projects and activities"""
    faculty_id = session['user_id']
    
    # Get faculty projects
    projects = ResearchProject.query.filter_by(faculty_id=faculty_id).all()
    
    # Calculate statistics
    total_projects = len(projects)
    ongoing_projects = len([p for p in projects if p.project_status == 'Ongoing'])
    completed_projects = len([p for p in projects if p.project_status == 'Completed'])
    startup_conversions = len([p for p in projects if p.is_startup_converted])
    
    # Get recent publications
    publications = Publication.query.join(
        ResearchProject, Publication.project_id == ResearchProject.project_id
    ).filter(
        ResearchProject.faculty_id == faculty_id
    ).order_by(Publication.publication_date.desc()).limit(5).all()
    
    # Get IPRs/Patents
    iprs = IPR.query.join(
        Publication, IPR.publication_id == Publication.publication_id
    ).join(
        ResearchProject, Publication.project_id == ResearchProject.project_id
    ).filter(
        ResearchProject.faculty_id == faculty_id
    ).all()
    
    return render_template('faculty/dashboard.html',
                         projects=projects,
                         total_projects=total_projects,
                         ongoing_projects=ongoing_projects,
                         completed_projects=completed_projects,
                         startup_conversions=startup_conversions,
                         publications=publications,
                         iprs=iprs)


# ==================== PROFILE ====================
@faculty_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def edit_profile():
    faculty_user = Person.query.get(session['user_id'])
    if request.method == 'POST':
        try:
            email = request.form.get('email', faculty_user.email).strip()
            if email != faculty_user.email:
                existing = Person.query.filter_by(email=email).first()
                if existing and existing.person_id != faculty_user.person_id:
                    return render_template('faculty/profile.html', faculty=faculty_user, error='Email already in use.')
            faculty_user.name = request.form.get('name', faculty_user.name).strip()
            faculty_user.email = email
            faculty_user.phone = request.form.get('phone', faculty_user.phone or '').strip()
            faculty_user.department = request.form.get('department', faculty_user.department or '').strip()
            faculty_user.bio = request.form.get('bio', faculty_user.bio or '').strip()
            faculty_user.skills = request.form.get('skills', faculty_user.skills or '').strip()
            db.session.commit()
            session['user_name'] = faculty_user.name
            session['user_email'] = faculty_user.email
            return redirect('/faculty/profile')
        except Exception as e:
            db.session.rollback()
            return render_template('faculty/profile.html', faculty=faculty_user, error=f'Error updating profile: {str(e)}')

    return render_template('faculty/profile.html', faculty=faculty_user)


# ==================== CREATE PROJECT ====================
@faculty_bp.route('/project/create', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
@faculty_can_create_projects
def create_project():
    """Create a new research project"""
    if request.method == 'POST':
        try:
            faculty_id = session['user_id']
            
            project = ResearchProject(
                faculty_id=faculty_id,
                project_title=request.form.get('project_title'),
                project_description=request.form.get('project_description'),
                domain=request.form.get('domain'),
                department=request.form.get('department'),
                required_skills=request.form.get('required_skills'),
                team_size=int(request.form.get('team_size', 1)),
                project_status='Proposed',
                program_location=request.form.get('program_location', '')
            )
            
            db.session.add(project)
            db.session.commit()
            
            # Add faculty as project lead
            project_person = ProjectPerson(
                project_id=project.project_id,
                person_id=faculty_id,
                role='Faculty Lead'
            )
            db.session.add(project_person)
            db.session.commit()

            # Notify admin about the new project submission
            try:
                from tasks.mail_tasks import send_project_submitted_email
                send_project_submitted_email.delay(project.project_id)
            except Exception as mail_exc:
                import logging
                logging.getLogger(__name__).warning(
                    f"Could not queue project submission email: {mail_exc}"
                )

            return redirect(f'/faculty/project/{project.project_id}')
        except Exception as e:
            return f"Error creating project: {str(e)}"
    
    return render_template('faculty/create_project.html')


# ==================== VIEW PROJECT DETAILS ====================
@faculty_bp.route('/project/<int:project_id>')
@login_required
@role_required('Faculty')
def view_project(project_id):
    """View project details and manage it"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    # Get project team
    team_members = db.session.query(
        ProjectPerson, Person
    ).filter(
        ProjectPerson.project_id == project_id,
        ProjectPerson.person_id == Person.person_id
    ).all()
    
    # Get students in project
    students = Person.query.join(
        ProjectPerson, Person.person_id == ProjectPerson.person_id
    ).filter(
        ProjectPerson.project_id == project_id,
        Person.type == 'Student'
    ).all()
    
    # Get available students (approved students not in this project)
    used_student_ids = db.session.query(ProjectPerson.person_id).filter(
        ProjectPerson.project_id == project_id
    ).all()
    used_student_ids = [s[0] for s in used_student_ids]
    
    available_students = Person.query.filter(
        Person.type == 'Student',
        Person.is_approved == True,
        ~Person.person_id.in_(used_student_ids)
    ).all()
    
    # Get project publications
    publications = Publication.query.filter_by(project_id=project_id).all()
    
    # Get project funding
    fundings = db.session.query(
        ProjectFunding, Funder
    ).filter(
        ProjectFunding.project_id == project_id,
        ProjectFunding.fund_id == Funder.fund_id
    ).all()
    
    # Get project IPRs
    iprs = IPR.query.join(
        Publication, IPR.publication_id == Publication.publication_id
    ).filter(
        Publication.project_id == project_id
    ).all()
    
    return render_template('faculty/project_details.html',
                         project=project,
                         team_members=team_members,
                         students=students,
                         available_students=available_students,
                         publications=publications,
                         fundings=fundings,
                         iprs=iprs)


# ==================== UPDATE PROJECT STATUS ====================
@faculty_bp.route('/project/<int:project_id>/update-status', methods=['POST'])
@login_required
@role_required('Faculty')
def update_project_status(project_id):
    """Update project status (Ongoing / Completed / On Hold)"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    new_status = request.form.get('project_status')
    if new_status in ['Ongoing', 'Completed', 'On Hold']:
        project.project_status = new_status
        db.session.commit()
        return redirect(f'/faculty/project/{project_id}')
    
    return "Invalid status", 400


# ==================== ADD STUDENT TO PROJECT ====================
@faculty_bp.route('/project/<int:project_id>/add-student', methods=['POST'])
@login_required
@role_required('Faculty')
def add_student_to_project(project_id):
    """Add a student to the project team"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    try:
        student_id = request.form.get('student_id')
        role = request.form.get('role', 'Team Member')
        
        # Check if student already in project
        existing = ProjectPerson.query.filter_by(
            project_id=project_id,
            person_id=student_id
        ).first()
        
        if existing:
            return "Student already in this project", 400

        if not project.is_approved:
            return "Cannot add students to an unapproved project", 400
        
        # Verify student exists and is actually a student
        student = Person.query.get(student_id)
        if not student or student.type != 'Student':
            return "Invalid student", 400
        
        project_person = ProjectPerson(
            project_id=project_id,
            person_id=student_id,
            role=role
        )
        db.session.add(project_person)
        db.session.commit()

        # Notify student they've been added to the project
        try:
            from tasks.mail_tasks import send_student_join_approved_email
            send_student_join_approved_email.delay(
                int(student_id), project_id, role
            )
        except Exception as mail_exc:
            import logging
            logging.getLogger(__name__).warning(
                f"Could not queue student join email: {mail_exc}"
            )

        return redirect(f'/faculty/project/{project_id}')
    except Exception as e:
        return f"Error adding student: {str(e)}", 400


# ==================== ASSIGN ROLE ====================
@faculty_bp.route('/project/<int:project_id>/assign-role/<int:person_id>', methods=['POST'])
@login_required
@role_required('Faculty')
def assign_role(project_id, person_id):
    """Update role for a team member"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    try:
        new_role = request.form.get('role')
        
        project_person = ProjectPerson.query.filter_by(
            project_id=project_id,
            person_id=person_id
        ).first()
        
        if not project_person:
            return "Team member not found", 404
        
        project_person.role = new_role
        db.session.commit()
        
        return redirect(f'/faculty/project/{project_id}')
    except Exception as e:
        return f"Error updating role: {str(e)}", 400


# ==================== REMOVE STUDENT FROM PROJECT ====================
@faculty_bp.route('/project/<int:project_id>/remove-student/<int:person_id>', methods=['POST'])
@login_required
@role_required('Faculty')
def remove_student_from_project(project_id, person_id):
    """Remove a student from the project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    try:
        project_person = ProjectPerson.query.filter_by(
            project_id=project_id,
            person_id=person_id,
        ).first()
        
        if not project_person:
            return "Team member not found", 404
        
        db.session.delete(project_person)
        db.session.commit()
        
        return redirect(f'/faculty/project/{project_id}')
    except Exception as e:
        return f"Error removing student: {str(e)}", 400


# ==================== ADD PUBLICATION ====================
@faculty_bp.route('/project/<int:project_id>/publication/add', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def add_publication(project_id):
    """Add a publication to the project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            doi = request.form.get('doi')

            # Check duplicates
            query = Publication.query.filter(Publication.project_id == project_id)
            if doi:
                query = query.filter((Publication.title == title) | (Publication.doi == doi))
            else:
                query = query.filter(Publication.title == title)

            existing_publication = query.first()
            if existing_publication:
                return "Duplicate publication entry detected for this project", 400

            # Validate and save document upload
            document_file = request.files.get('document')
            if not document_file or not document_file.filename:
                return "Document upload is required for publications", 400

            document_url = save_uploaded_document(document_file)
            if not document_url:
                return "Invalid document format. Only PDF, DOC, and DOCX files are allowed.", 400

            # FIX: handle date BEFORE creating object
            date_str = request.form.get('publication_date')
            publication_date = datetime.strptime(date_str, "%Y-%m").date() if date_str else None

            # Correct object creation
            indexing_values = request.form.getlist('indexing')
            indexing = ', '.join([item for item in indexing_values if item]) or None

            publication = Publication(
                project_id=project_id,
                title=title,
                publication_type=request.form.get('publication_type'),
                venue=request.form.get('venue'),
                status=request.form.get('status', 'Submitted'),
                indexing=indexing,
                publication_date=publication_date,
                volume=request.form.get('volume'),
                page_number=request.form.get('page_number'),
                doi=doi,
                issn_isbn=request.form.get('issn_isbn'),
                publisher=request.form.get('publisher'),
                document_url=document_url
            )
            
            db.session.add(publication)
            db.session.commit()
            
            return redirect(f'/faculty/project/{project_id}')
        
        except Exception as e:
            return f"Error adding publication: {str(e)}"
    
    return render_template('faculty/add_publication.html', project=project)


# ==================== ADD IPR / PATENT ====================
@faculty_bp.route('/project/<int:project_id>/ipr/add', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def add_ipr(project_id):
    """Add IPR/Patent to the project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    if request.method == 'POST':
        try:
            publication_id = request.form.get('publication_id')
            innovation_title = request.form.get('innovation_title')
            application_number = request.form.get('application_number')

            if publication_id:
                publication = Publication.query.get(publication_id)
                if not publication or publication.project_id != project_id:
                    return "Invalid publication selected", 400
            else:
                publication = Publication(
                    project_id=project_id,
                    title=innovation_title,
                    publication_type='Patent',
                    status='Submitted'
                )
                db.session.add(publication)
                db.session.flush()
                publication_id = publication.publication_id

            if application_number:
                duplicate_ipr = IPR.query.filter_by(application_number=application_number).first()
                if duplicate_ipr:
                    return "Duplicate IPR entry detected by application number", 400

            duplicate_title = IPR.query.join(Publication).filter(
                Publication.project_id == project_id,
                IPR.innovation_title == innovation_title
            ).first()
            if duplicate_title:
                return "Duplicate IPR entry detected for this project", 400

            document_file = request.files.get('document')
            if not document_file or not document_file.filename:
                return "Document upload is required for IPR entries", 400

            document_url = save_uploaded_document(document_file)
            if not document_url:
                return "Invalid document format. Only PDF, DOC, and DOCX files are allowed.", 400

            ipr = IPR(
                publication_id=publication_id,
                innovation_title=innovation_title,
                ipr_type=request.form.get('ipr_type'),
                application_number=application_number,
                grant_status=request.form.get('grant_status', 'Filed'),
                ownership_type=request.form.get('ownership_type', 'Individual'),
                document_url=document_url
            )
            
            db.session.add(ipr)
            db.session.commit()
            
            return redirect(f'/faculty/project/{project_id}')
        except Exception as e:
            return f"Error adding IPR: {str(e)}"
    
    publications = Publication.query.filter_by(project_id=project_id).all()
    return render_template('faculty/add_ipr.html', project=project, publications=publications)


# ==================== EDIT IPR / PATENT ====================
@faculty_bp.route('/project/<int:project_id>/ipr/<int:ipr_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def edit_ipr(project_id, ipr_id):
    """Edit an existing IPR/Patent"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    ipr = IPR.query.get(ipr_id)
    if not ipr or ipr.project_id != project_id:
        return "IPR not found", 404
    
    if request.method == 'POST':
        try:
            ipr.innovation_title = request.form.get('innovation_title')
            ipr.ipr_type = request.form.get('ipr_type')
            ipr.application_number = request.form.get('application_number')
            ipr.grant_status = request.form.get('grant_status')
            ipr.ownership_type = request.form.get('ownership_type')

            document_file = request.files.get('document')
            if document_file and document_file.filename:
                document_url = save_uploaded_document(document_file)
                if not document_url:
                    return "Invalid document format. Only PDF, DOC, and DOCX files are allowed.", 400
                ipr.document_url = document_url
            
            db.session.commit()
            
            return redirect(f'/faculty/project/{project_id}')
        except Exception as e:
            return f"Error updating IPR: {str(e)}"
    
    return render_template('faculty/edit_ipr.html', project=project, ipr=ipr)


# ==================== ADD FUNDING DETAILS ====================
@faculty_bp.route('/project/<int:project_id>/funding/add', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def add_funding(project_id):
    """Add funding details to the project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    if request.method == 'POST':
        try:
            # Create or get funder
            funding_agency = request.form.get('funding_agency')
            funding_type = request.form.get('funding_type')
            
            funder = Funder.query.filter_by(
                funding_agency=funding_agency
            ).first()
            
            if not funder:
                funder = Funder(
                    funding_agency=funding_agency,
                    funding_type=funding_type
                )
                db.session.add(funder)
                db.session.flush()
            
            project_funding = ProjectFunding(
                project_id=project_id,
                fund_id=funder.fund_id,
                sanctioned_amount=float(request.form.get('sanctioned_amount', 0)),
                sanctioned_date=datetime.strptime(
                    request.form.get('sanctioned_date'),
                    '%Y-%m-%d'
                ) if request.form.get('sanctioned_date') else None
            )
            
            db.session.add(project_funding)
            db.session.commit()
            
            return redirect(f'/faculty/project/{project_id}')
        except Exception as e:
            return f"Error adding funding: {str(e)}"
    
    return render_template('faculty/add_funding.html', project=project)


# ==================== EDIT FUNDING DETAILS ====================
@faculty_bp.route('/project/<int:project_id>/funding/<int:fund_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def edit_funding(project_id, fund_id):
    """Edit funding details for a project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    # Get the funding entry
    project_funding = ProjectFunding.query.filter_by(
        project_id=project_id,
        fund_id=fund_id
    ).first()
    
    if not project_funding:
        return "Funding not found", 404
    
    funder = Funder.query.get(fund_id)
    
    if request.method == 'POST':
        try:
            # Update funder details
            funder.funding_agency = request.form.get('funding_agency')
            funder.funding_type = request.form.get('funding_type')
            
            # Update project funding details
            project_funding.sanctioned_amount = float(request.form.get('sanctioned_amount', 0))
            project_funding.sanctioned_date = datetime.strptime(
                request.form.get('sanctioned_date'),
                '%Y-%m-%d'
            ) if request.form.get('sanctioned_date') else None
            
            db.session.commit()
            
            return redirect(f'/faculty/project/{project_id}')
        except Exception as e:
            return f"Error updating funding: {str(e)}"
    
    return render_template('faculty/edit_funding.html', project=project, funder=funder, project_funding=project_funding)


# ==================== COMPETITIONS LIST ====================
@faculty_bp.route('/project/<int:project_id>/competitions')
@login_required
@role_required('Faculty')
def view_competitions(project_id):
    """View all competitions for a project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    # Get all competitions for this project
    project_competitions = db.session.query(ProjectCompetition, Competition).filter(
        ProjectCompetition.project_id == project_id,
        ProjectCompetition.competition_id == Competition.competition_id
    ).all()
    
    competitions = []
    for pc, comp in project_competitions:
        competitions.append({
            'project_competition': pc,
            'competition': comp,
            'project': project
        })
    
    return render_template('faculty/competitions.html', 
                         project=project,
                         competitions=competitions)


# ==================== ADD/UPDATE COMPETITION ====================
@faculty_bp.route('/project/<int:project_id>/add-competition', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def add_competition(project_id):
    """Add or update competition participation details"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
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
            
            # Create project-competition link
            project_competition = ProjectCompetition(
                project_id=project_id,
                competition_id=competition.competition_id,
                team_name=request.form.get('team_name'),
                prize_money_received=float(request.form.get('prize_money_received', 0) or 0)
            )
            
            db.session.add(project_competition)
            db.session.commit()
            
            return redirect(f'/faculty/project/{project_id}/competitions')
        except Exception as e:
            db.session.rollback()
            return f"Error adding competition: {str(e)}", 400
    
    return render_template('faculty/add_competition.html', project=project)


# ==================== VIEW STARTUP ====================
@faculty_bp.route('/project/<int:project_id>/startup')
@login_required
@role_required('Faculty')
def view_startup(project_id):
    """View and manage startup status for a project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    # Get startup if exists
    startup = Startup.query.filter_by(project_id=project_id).first()
    
    return render_template('faculty/startup.html',
                         project=project,
                         startup=startup)


# ==================== CONVERT PROJECT TO STARTUP ====================
@faculty_bp.route('/project/<int:project_id>/convert-startup', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def convert_to_startup(project_id):
    """Convert a research project to a startup"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized or Project not found", 404
    
    if request.method == 'POST':
        try:
            # Check if already converted
            existing_startup = Startup.query.filter_by(project_id=project_id).first()
            if existing_startup:
                return "Project already converted to startup", 400
            
            startup = Startup(
                project_id=project_id,
                startup_name=request.form.get('startup_name'),
                registration_number=request.form.get('registration_number'),
                development_status=request.form.get('development_status', 'Idea'),
                fund_amount=float(request.form.get('fund_amount', 0) or 0)
            )
            
            db.session.add(startup)
            
            # Mark project as startup converted
            project.is_startup_converted = True
            
            db.session.commit()
            
            return redirect(f'/faculty/project/{project_id}/startup')
        except Exception as e:
            db.session.rollback()
            return f"Error converting to startup: {str(e)}", 400
    
    # Check if already a startup
    existing_startup = Startup.query.filter_by(project_id=project_id).first()
    
    return render_template('faculty/convert_startup.html', 
                         project=project, 
                         existing_startup=existing_startup)


# ==================== UPDATE STARTUP ====================
@faculty_bp.route('/project/<int:project_id>/startup/update', methods=['POST'])
@login_required
@role_required('Faculty')
def update_startup(project_id):
    """Update startup details for a project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    startup = Startup.query.filter_by(project_id=project_id).first()
    if not startup:
        return jsonify({'status': 'error', 'message': 'Startup not found'}), 404
    
    try:
        startup.startup_name = request.form.get('startup_name', startup.startup_name)
        startup.registration_number = request.form.get('registration_number', startup.registration_number)
        startup.development_status = request.form.get('development_status', startup.development_status)
        startup.fund_amount = float(request.form.get('fund_amount', startup.fund_amount) or 0)
        startup.revenue_generated = float(request.form.get('revenue_generated', startup.revenue_generated) or 0)
        
        db.session.commit()
        
        return redirect(f'/faculty/project/{project_id}/startup')
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== PROJECTS LIST ====================
@faculty_bp.route('/projects')
@login_required
@role_required('Faculty')
def projects_list():
    """View all projects for the faculty"""
    faculty_id = session['user_id']
    projects = ResearchProject.query.filter_by(faculty_id=faculty_id).all()
    
    return render_template('faculty/projects_list.html', projects=projects)


# ==================== GET AVAILABLE STUDENTS (for AJAX) ====================
@faculty_bp.route('/api/available-students/<int:project_id>')
@login_required
@role_required('Faculty')
def get_available_students(project_id):
    """Get list of students not yet in the project"""
    project = ResearchProject.query.get(project_id)
    
    if not project or project.faculty_id != session['user_id']:
        return jsonify([]), 404
    
    # Get students already in project
    used_student_ids = db.session.query(ProjectPerson.person_id).filter(
        ProjectPerson.project_id == project_id
    ).all()
    used_student_ids = [s[0] for s in used_student_ids]
    
    # Get available students
    available_students = Person.query.filter(
        Person.type == 'Student',
        ~Person.person_id.in_(used_student_ids),
        Person.is_approved == True
    ).all()
    
    return jsonify([{
        'id': s.person_id,
        'name': s.name,
        'email': s.email
    } for s in available_students])


# ==================== ANALYTICS APIs ====================
@faculty_bp.route('/api/analytics/projects')
@login_required
@role_required('Faculty')
def analytics_projects():
    """Get project status distribution for faculty"""
    faculty_id = session['user_id']
    
    projects = ResearchProject.query.filter_by(faculty_id=faculty_id).all()
    
    status_count = {
        'Proposed': 0,
        'Ongoing': 0,
        'Completed': 0,
        'On Hold': 0
    }
    
    for project in projects:
        if project.project_status in status_count:
            status_count[project.project_status] += 1
    
    return jsonify({
        'statuses': list(status_count.keys()),
        'counts': list(status_count.values())
    })


@faculty_bp.route('/api/analytics/publications')
@login_required
@role_required('Faculty')
def analytics_publications():
    """Get publication status breakdown for faculty's projects"""
    faculty_id = session['user_id']
    
    publications = db.session.query(Publication, ResearchProject).filter(
        ResearchProject.faculty_id == faculty_id,
        Publication.project_id == ResearchProject.project_id
    ).all()
    
    status_count = {
        'Submitted': 0,
        'Accepted': 0,
        'Published': 0,
        'Rejected': 0
    }
    
    for pub, _ in publications:
        if pub.status in status_count:
            status_count[pub.status] += 1
    
    return jsonify({
        'statuses': list(status_count.keys()),
        'counts': list(status_count.values())
    })


@faculty_bp.route('/api/analytics/iprs')
@login_required
@role_required('Faculty')
def analytics_iprs():
    """Get IPR grant status distribution for faculty's projects"""
    faculty_id = session['user_id']
    
    iprs = db.session.query(IPR, Publication, ResearchProject).filter(
        ResearchProject.faculty_id == faculty_id,
        Publication.project_id == ResearchProject.project_id,
        IPR.publication_id == Publication.publication_id
    ).all()
    
    status_count = {
        'Filed': 0,
        'Pending': 0,
        'Granted': 0,
        'Rejected': 0
    }
    
    for ipr, _, _ in iprs:
        if ipr.grant_status in status_count:
            status_count[ipr.grant_status] += 1
    
    return jsonify({
        'statuses': list(status_count.keys()),
        'counts': list(status_count.values())
    })
@faculty_bp.route('/api/analytics/team')
@login_required
@role_required('Faculty')
def analytics_team():
    """Get team composition for faculty's projects"""
    faculty_id = session['user_id']
    
    projects = ResearchProject.query.filter_by(faculty_id=faculty_id).all()
    project_ids = [p.project_id for p in projects]
    
    if not project_ids:
        return jsonify({
            'projects': [],
            'team_sizes': []
        })
    
    team_data = db.session.query(
        ResearchProject.project_id,
        ResearchProject.project_title,
        db.func.count(ProjectPerson.person_id)
    ).filter(
        ResearchProject.project_id.in_(project_ids),
        ProjectPerson.project_id == ResearchProject.project_id
    ).group_by(
        ResearchProject.project_id,
        ResearchProject.project_title   # IMPORTANT FIX
    ).all()
    
    project_titles = [item[1] for item in team_data]
    team_sizes = [item[2] for item in team_data]
    
    return jsonify({
        'projects': project_titles,
        'team_sizes': team_sizes
    })



# ==================== VIEW ALL COMPETITIONS (Faculty) ====================
@faculty_bp.route('/competitions')
@login_required
@role_required('Faculty')
def view_all_competitions():
    """View all competitions - both faculty-led and student competitions they mentored"""
    faculty_id = session['user_id']
    
    # Get all projects for this faculty
    projects = ResearchProject.query.filter_by(faculty_id=faculty_id).all()
    project_ids = [p.project_id for p in projects]
    
    competitions_data = []
    
    # 1. Get all competitions for faculty's projects (faculty-led)
    if project_ids:
        project_competitions = db.session.query(
            ProjectCompetition, Competition, ResearchProject
        ).join(
            Competition, ProjectCompetition.competition_id == Competition.competition_id
        ).join(
            ResearchProject, ProjectCompetition.project_id == ResearchProject.project_id
        ).filter(
            ProjectCompetition.project_id.in_(project_ids)
        ).all()
        
        for pc, comp, proj in project_competitions:
            competitions_data.append({
                'type': 'project',
                'project_competition': pc,
                'competition': comp,
                'project': proj,
                'student': None,
                'mentor': None
            })
    
    # 2. Get all student competitions where this faculty is the mentor
    student_alias = aliased(Person)
    mentor_alias = aliased(Person)

    student_comps = db.session.query(
        StudentCompetition, Competition, student_alias, mentor_alias
    ).join(
        Competition, StudentCompetition.competition_id == Competition.competition_id
    ).join(
        student_alias, StudentCompetition.student_id == student_alias.person_id,
        isouter=True
    ).join(
        mentor_alias, StudentCompetition.mentor_id == mentor_alias.person_id,
        isouter=True
    ).filter(
        StudentCompetition.mentor_id == faculty_id
    ).order_by(StudentCompetition.created_at.desc()).all()
    
    for sc, comp, student, mentor in student_comps:
        competitions_data.append({
            'type': 'student',
            'student_competition': sc,
            'competition': comp,
            'project': None,
            'student': student,
            'mentor': mentor
        })
    
    return render_template('faculty/competitions.html',
                         project=None,
                         competitions=competitions_data,
                         all_faculty_competitions=True,
                         show_both_types=True)

# ==================== EDIT PUBLICATION ====================
@faculty_bp.route('/publication/<int:pub_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Faculty')
def edit_publication(pub_id):
    """Edit an existing publication"""
    
    publication = Publication.query.get(pub_id)

    if not publication:
        return "Publication not found", 404

    # Check ownership
    project = ResearchProject.query.get(publication.project_id)
    if not project or project.faculty_id != session['user_id']:
        return "Unauthorized", 403

    if request.method == 'POST':
        try:
            publication.title = request.form.get('title')
            publication.publication_type = request.form.get('publication_type')
            publication.venue = request.form.get('venue')
            publication.status = request.form.get('status')
            indexing_values = request.form.getlist('indexing')
            publication.indexing = ', '.join([item for item in indexing_values if item]) or None

            # FIXED DATE HANDLING
            date_str = request.form.get('publication_date')
            publication.publication_date = datetime.strptime(date_str, "%Y-%m").date() if date_str else None

            publication.volume = request.form.get('volume')
            publication.page_number = request.form.get('page_number')
            publication.doi = request.form.get('doi')
            publication.issn_isbn = request.form.get('issn_isbn')
            publication.publisher = request.form.get('publisher')

            document_file = request.files.get('document')
            if document_file and document_file.filename:
                document_url = save_uploaded_document(document_file)
                if not document_url:
                    return "Invalid document format. Only PDF, DOC, and DOCX files are allowed.", 400
                publication.document_url = document_url

            db.session.commit()

            return redirect(f'/faculty/project/{publication.project_id}')
        except Exception as e:
            return f"Error updating publication: {str(e)}"

    return render_template('faculty/edit_publication.html', pub=publication)
