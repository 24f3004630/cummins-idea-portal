from flask import Flask, render_template, session
from backend.config import Config
from database.db import db

# CREATE APP FIRST
app = Flask(__name__)
app.config.from_object(Config)

# Set session configuration
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# INIT DB
db.init_app(app)

# IMPORT BLUEPRINTS AFTER APP
from backend.auth.routes import auth_bp
from backend.admin.routes import admin_bp
from backend.faculty.routes import faculty_bp
from backend.student.routes import student_bp

# REGISTER BLUEPRINTS
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(faculty_bp)
app.register_blueprint(student_bp)

# CREATE DB + ADMIN
from database.models import Person

with app.app_context():
    db.create_all()

    admin = Person.query.filter_by(email="admin@portal.com").first()
    if not admin:
        admin = Person(
            name="Admin",
            email="admin@portal.com",
            type="Admin",
            is_approved=True
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()

# PUBLIC HOME ROUTE
@app.route('/')
def home():
    """Public home page for all users"""
    return render_template('home.html', user=session.get('user_id'))

# ERROR HANDLERS
@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == "__main__":
    app.run(debug=True, port=8000)