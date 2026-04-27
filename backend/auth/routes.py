from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from database.db import db
from database.models import Person
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Helper to get current user
def get_current_user():
    """Get the current logged-in user"""
    user_id = session.get('user_id')
    if user_id:
        return Person.query.get(user_id)
    return None

# ---------------- REGISTER STUDENT ----------------
@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    """Student registration route"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        # Validation
        if not all([name, email, password]):
            return render_template('auth/register_student.html', 
                                 error="All fields are required")
        
        if password != password_confirm:
            return render_template('auth/register_student.html', 
                                 error="Passwords do not match")
        
        if len(password) < 6:
            return render_template('auth/register_student.html', 
                                 error="Password must be at least 6 characters")

        # Check if email already exists
        existing_user = Person.query.filter_by(email=email).first()
        if existing_user:
            return render_template('auth/register_student.html', 
                                 error="This email is already registered. Please login or use a different email.")

        try:
            # Create new student
            user = Person(name=name, email=email, type='Student')
            user.set_password(password)
            user.is_approved = True  # Students are auto-approved

            db.session.add(user)
            db.session.commit()

            return render_template('auth/register_student.html', 
                                 success="Registration successful! You can now login.")
        except Exception as e:
            db.session.rollback()
            return render_template('auth/register_student.html', 
                                 error=f"Registration failed: {str(e)}")

    return render_template('auth/register_student.html')


# ---------------- REGISTER FACULTY ----------------
@auth_bp.route('/register/faculty', methods=['GET', 'POST'])
def register_faculty():
    """Faculty registration route - requires admin approval"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        department = request.form.get('department', '').strip()

        # Validation
        if not all([name, email, password, department]):
            return render_template('auth/register_faculty.html', 
                                 error="All fields are required")
        
        if password != password_confirm:
            return render_template('auth/register_faculty.html', 
                                 error="Passwords do not match")
        
        if len(password) < 6:
            return render_template('auth/register_faculty.html', 
                                 error="Password must be at least 6 characters")

        # Check if email already exists
        existing_user = Person.query.filter_by(email=email).first()
        if existing_user:
            return render_template('auth/register_faculty.html', 
                                 error="This email is already registered. Please login or use a different email.")

        try:
            # Create new faculty
            user = Person(name=name, email=email, type='Faculty', department=department)
            user.set_password(password)
            user.is_approved = False  # Needs admin approval

            db.session.add(user)
            db.session.commit()

            # Notify admin via Celery background task
            try:
                from tasks.mail_tasks import send_faculty_registration_pending
                send_faculty_registration_pending.delay(user.person_id)
            except Exception as mail_exc:
                # Non-critical — log but don't fail the registration
                import logging
                logging.getLogger(__name__).warning(
                    f"Could not queue faculty registration email: {mail_exc}"
                )

            return render_template('auth/register_faculty.html', 
                                 success="Registration submitted! Please wait for admin approval. You will receive an email notification.")
        except Exception as e:
            db.session.rollback()
            return render_template('auth/register_faculty.html', 
                                 error=f"Registration failed: {str(e)}")

    return render_template('auth/register_faculty.html')


# ---------------- LOGIN ----------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route with improved error handling"""
    # If already logged in, redirect to dashboard
    if session.get('user_id'):
        user = get_current_user()
        if user:
            if user.type == "Admin":
                return redirect('/admin/dashboard')
            elif user.type == "Faculty":
                return redirect('/faculty/dashboard')
            else:
                return redirect('/student/dashboard')
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Validation
        if not email or not password:
            return render_template('auth/login.html', error="Email and password are required")

        # Find user
        user = Person.query.filter_by(email=email).first()

        if not user:
            return render_template('auth/login.html', error="Invalid email or password")
        
        # Check password
        if not user.check_password(password):
            return render_template('auth/login.html', error="Invalid email or password")

        # Check if faculty is approved
        if user.type == "Faculty" and not user.is_approved:
            return render_template('auth/login.html', 
                                 error="Your account is pending admin approval. Please check again later.")

        # Check if user is admin or approved student/faculty
        if user.type != "Admin" and not user.is_approved:
            return render_template('auth/login.html', 
                                 error="Your account is not approved yet. Please contact the administrator.")

        # Set session
        session['user_id'] = user.person_id
        session['role'] = user.type
        session['user_name'] = user.name
        session['user_email'] = user.email

        # Redirect based on role
        if user.type == "Admin":
            return redirect('/admin/dashboard')
        elif user.type == "Faculty":
            return redirect('/faculty/dashboard')
        else:
            return redirect('/student/dashboard')

    return render_template('auth/login.html')


# ---------------- LOGOUT ----------------
@auth_bp.route('/logout')
def logout():
    """User logout route"""
    session.clear()
    return redirect('/auth/login')


# ---------------- CHECK AUTH STATUS ----------------
@auth_bp.route('/check')
def check_auth():
    """Check if user is logged in - useful for AJAX requests"""
    user_id = session.get('user_id')
    if user_id:
        user = get_current_user()
        if user:
            return {
                'authenticated': True,
                'user_id': user_id,
                'role': session.get('role'),
                'name': user.name,
                'email': user.email
            }
    
    return {'authenticated': False}