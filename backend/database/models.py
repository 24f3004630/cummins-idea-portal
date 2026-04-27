from .db import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ------------------ PERSON (Student / Faculty / Admin) ------------------
class Person(db.Model):
    __tablename__ = 'person'

    person_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # Student / Faculty / Admin
    department = db.Column(db.String(100))
    is_approved = db.Column(db.Boolean, default=False)
    
    # Student-specific fields
    skills = db.Column(db.Text)  # Comma-separated skills
    resume_url = db.Column(db.String(255))  # URL to uploaded resume
    bio = db.Column(db.Text)  # Short bio/profile description
    phone = db.Column(db.String(20))  # Contact phone number

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def can_create_projects(self):
        """Check if faculty can create projects"""
        return self.type == 'Faculty' and self.is_approved
    
    def can_approve_applications(self):
        """Check if user can approve applications"""
        return self.type in ['Faculty', 'Admin'] and self.is_approved


# ------------------ RESEARCH PROJECT ------------------
class ResearchProject(db.Model):
    __tablename__ = 'research_project'

    project_id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('person.person_id'))
    
    project_title = db.Column(db.String(200), nullable=False)
    project_description = db.Column(db.Text)
    domain = db.Column(db.String(100))
    department = db.Column(db.String(100))
    required_skills = db.Column(db.Text)  # Comma-separated skills
    team_size = db.Column(db.Integer)
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    project_status = db.Column(db.String(50), default='Proposed')  # Proposed / Ongoing / Completed / On Hold
    iic_registration_status = db.Column(db.String(50))
    project_level = db.Column(db.String(50))
    program_location = db.Column(db.String(100))
    is_approved = db.Column(db.Boolean, default=False)
    is_startup_converted = db.Column(db.Boolean, default=False)  # Track if converted to startup
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_publications(self):
        """Get all publications for this project"""
        return Publication.query.filter_by(project_id=self.project_id).all()
    
    def get_iprs(self):
        """Get all IPRs for this project"""
        return IPR.query.filter_by(project_id=self.project_id).all()
    
    def get_startup(self):
        """Get startup if converted"""
        return Startup.query.filter_by(project_id=self.project_id).first()
    
    def get_team_members(self):
        """Get all team members"""
        return db.session.query(ProjectPerson, Person).filter(
            ProjectPerson.project_id == self.project_id,
            ProjectPerson.person_id == Person.person_id
        ).all()
    
    def get_faculty(self):
        """Get faculty info"""
        return Person.query.get(self.faculty_id)
    
    def can_accept_students(self):
        """Check if project can accept more students"""
        if not self.is_approved:
            return False
        if self.project_status != 'Ongoing':
            return False
        current_team = len(ProjectPerson.query.filter_by(project_id=self.project_id).all())
        return current_team < (self.team_size or 999)

# ------------------ PROJECT_PERSON (M:N) ------------------
class ProjectPerson(db.Model):
    __tablename__ = 'project_person'

    project_id = db.Column(db.Integer, db.ForeignKey('research_project.project_id'), primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.person_id'), primary_key=True)
    role = db.Column(db.String(50))  # Student / Faculty / Mentor


# ------------------ FUNDER ------------------
class Funder(db.Model):
    __tablename__ = 'funder'

    fund_id = db.Column(db.Integer, primary_key=True)
    funding_agency = db.Column(db.String(200))
    funding_type = db.Column(db.String(50))  # NGO / GOVT


# ------------------ PROJECT_FUNDING (M:N) ------------------
class ProjectFunding(db.Model):
    __tablename__ = 'project_funding'

    project_id = db.Column(db.Integer, db.ForeignKey('research_project.project_id'), primary_key=True)
    fund_id = db.Column(db.Integer, db.ForeignKey('funder.fund_id'), primary_key=True)
    sanctioned_amount = db.Column(db.Float)
    sanctioned_date = db.Column(db.Date)


# ------------------ PUBLICATION ------------------
class Publication(db.Model):
    __tablename__ = 'publication'

    publication_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('research_project.project_id'))

    title = db.Column(db.String(200), nullable=False)
    publication_type = db.Column(db.String(50))  # Journal / Conference
    venue = db.Column(db.String(200))
    publication_date = db.Column(db.Date)

    indexing = db.Column(db.String(100))
    page_number = db.Column(db.String(50))
    year_of_publication = db.Column(db.Integer)
    volume = db.Column(db.String(50))

    doi = db.Column(db.String(100))
    issn_isbn = db.Column(db.String(100))
    publisher = db.Column(db.String(200))
    document_url = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Submitted')  # Submitted / Accepted / Published / Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: prevent duplicate publications for same project
    __table_args__ = (
        db.UniqueConstraint('project_id', 'title', 'venue', 'year_of_publication', name='uq_publication_unique'),
    )


# ------------------ AUTHOR ------------------
class Author(db.Model):
    __tablename__ = 'author'

    author_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))


# ------------------ PUBLICATION_AUTHOR (M:N) ------------------
class PublicationAuthor(db.Model):
    __tablename__ = 'publication_author'

    publication_id = db.Column(db.Integer, db.ForeignKey('publication.publication_id'), primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.author_id'), primary_key=True)
    sequence_of_author = db.Column(db.Integer)


# ------------------ IPR / PATENT ------------------
class IPR(db.Model):
    __tablename__ = 'ipr'

    ipr_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('research_project.project_id'))
    publication_id = db.Column(db.Integer, db.ForeignKey('publication.publication_id'))

    innovation_title = db.Column(db.String(200))
    ipr_type = db.Column(db.String(50))  # Patent / Copyright / Trademark / Design

    application_number = db.Column(db.String(100), unique=True)
    filing_date = db.Column(db.Date)
    registration_date = db.Column(db.Date)
    grant_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)

    grant_status = db.Column(db.String(50), default='Filed')  # Filed / Pending / Granted / Rejected
    ownership_type = db.Column(db.String(50))
    document_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: prevent duplicate IPRs for same project/innovation
    __table_args__ = (
        db.UniqueConstraint('project_id', 'innovation_title', name='uq_ipr_unique'),
    )


# ------------------ STARTUP (1:1 with Project) ------------------
class Startup(db.Model):
    __tablename__ = 'startup'

    startup_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('research_project.project_id'), unique=True)

    startup_name = db.Column(db.String(200), nullable=False)
    registration_number = db.Column(db.String(100))
    revenue_generated = db.Column(db.Float, default=0)
    development_status = db.Column(db.String(100), default='Idea')  # Idea / MVP / Beta / Live / Growth
    fund_amount = db.Column(db.Float, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_project(self):
        """Get associated project"""
        return ResearchProject.query.get(self.project_id)


# ------------------ COMPETITION ------------------
class Competition(db.Model):
    __tablename__ = 'competition'

    competition_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    venue = db.Column(db.String(200))
    organized_by = db.Column(db.String(200))
    start_date_of_competition = db.Column(db.Date)
    end_date_of_competition = db.Column(db.Date)


# ------------------ PROJECT_COMPETITION (M:N) ------------------
class ProjectCompetition(db.Model):
    __tablename__ = 'project_competition'

    project_id = db.Column(db.Integer, db.ForeignKey('research_project.project_id'), primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.competition_id'), primary_key=True)

    team_name = db.Column(db.String(100))
    prize_money_received = db.Column(db.Float)


# ------------------ STUDENT_COMPETITION (Competition participation by students) ------------------
class StudentCompetition(db.Model):
    __tablename__ = 'student_competition'

    student_competition_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('person.person_id'))
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.competition_id'))
    mentor_id = db.Column(db.Integer, db.ForeignKey('person.person_id'), nullable=True)  # Faculty mentor

    team_name = db.Column(db.String(100))  # Team name or individual name
    prize_money = db.Column(db.Float, default=0)  # Prize won (if any)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ------------------ PROJECT APPLICATION / JOIN REQUEST ------------------
class ProjectApplication(db.Model):
    __tablename__ = 'project_application'

    application_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('research_project.project_id'))
    student_id = db.Column(db.Integer, db.ForeignKey('person.person_id'))
    
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Pending')  # Pending / Approved / Rejected
    student_message = db.Column(db.Text)  # Optional message from student
    faculty_message = db.Column(db.Text)  # Optional feedback from faculty
    
    def __repr__(self):
        return f'<ProjectApplication {self.application_id}>'