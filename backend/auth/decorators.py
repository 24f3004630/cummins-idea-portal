from functools import wraps
from flask import session, redirect, render_template, abort
from database.models import Person, ResearchProject, ProjectApplication


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/auth/login')  # Fixed redirect path
        return f(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') != role:
                abort(403)  # Return proper 403 error instead of plain text
            return f(*args, **kwargs)
        return wrapper
    return decorator


def approved_required(f):
    """Ensure user is approved"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = Person.query.get(session.get('user_id'))
        if not user or not user.is_approved:
            abort(403)  # Return proper 403 error instead of plain text
        return f(*args, **kwargs)
    return wrapper


def faculty_can_create_projects(f):
    """Ensure only approved faculty can create projects"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = Person.query.get(session.get('user_id'))
        if not user or not user.can_create_projects():
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def student_can_join_approved_projects(f):
    """Ensure student can only join approved projects"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = Person.query.get(session.get('user_id'))
        if not user or user.type != 'Student':
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def admin_or_faculty_required(f):
    """Ensure user is admin or faculty"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        role = session.get('role')
        if role not in ['Admin', 'Faculty']:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def project_owner_or_admin(f):
    """Ensure user is project owner (faculty) or admin"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        project_id = kwargs.get('project_id')
        user = Person.query.get(user_id)
        
        if not user:
            return redirect('/auth/login')
        
        if user.type == 'Admin':
            return f(*args, **kwargs)
        
        if user.type == 'Faculty':
            project = ResearchProject.query.get(project_id)
            if project and project.faculty_id == user_id:
                return f(*args, **kwargs)
        
        abort(403)
    return wrapper