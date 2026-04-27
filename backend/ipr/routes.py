"""
IPR/Patent Management Routes
Handles all IPR-related operations including:
- Viewing IPR records
- Adding and editing IPRs
- IPR monitoring and analytics
- Faculty and project associations
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload

# Initialize blueprint
ipr_bp = Blueprint('ipr', __name__, url_prefix='/admin/ipr')


def get_ipr_data(db):
    """Get all IPR records with associated faculty and projects"""
    query = db.session.query(
        IPRModel,
        Faculty,
        Project
    ).outerjoin(Faculty, IPRModel.faculty_id == Faculty.faculty_id)\
     .outerjoin(Project, IPRModel.project_id == Project.project_id)
    
    return query.all()


@ipr_bp.route('/monitoring', methods=['GET'])
def monitoring():
    """IPR/Patent monitoring dashboard"""
    try:
        ipr_data = get_ipr_data(db)
        
        return render_template('admin/iprs.html', ipr_data=ipr_data)
    except Exception as e:
        flash(f'Error loading IPR data: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@ipr_bp.route('/analytics', methods=['GET'])
def analytics():
    """IPR/Patent analytics dashboard with charts and metrics"""
    try:
        ipr_data = get_ipr_data(db)
        
        # Calculate key metrics
        total_iprs = len(ipr_data)
        granted_count = sum(1 for item in ipr_data if item[0].grant_status == 'Granted')
        pending_count = sum(1 for item in ipr_data if item[0].grant_status == 'Pending')
        filed_count = sum(1 for item in ipr_data if item[0].grant_status == 'Filed')
        rejected_count = sum(1 for item in ipr_data if item[0].grant_status == 'Rejected')
        in_progress_count = pending_count + filed_count
        
        # IPR Type Distribution
        ipr_types = {}
        for item in ipr_data:
            ipr_type = item[0].ipr_type
            ipr_types[ipr_type] = ipr_types.get(ipr_type, 0) + 1
        
        ipr_type_labels = list(ipr_types.keys())
        ipr_type_counts = list(ipr_types.values())
        
        # Timeline data - IPRs filed over months
        timeline_data = {}
        for item in ipr_data:
            if item[0].filing_date:
                month_key = item[0].filing_date.strftime('%b %Y')
                timeline_data[month_key] = timeline_data.get(month_key, 0) + 1
        
        # Sort chronologically
        sorted_months = sorted(timeline_data.items(), 
                              key=lambda x: datetime.strptime(x[0], '%b %Y'))
        timeline_months = [m[0] for m in sorted_months]
        timeline_counts = [m[1] for m in sorted_months]
        
        # Top faculty contributors
        faculty_contributions = {}
        for item in ipr_data:
            if item[1]:  # Faculty
                faculty_id = item[1].faculty_id
                if faculty_id not in faculty_contributions:
                    faculty_contributions[faculty_id] = {
                        'name': item[1].name,
                        'department': item[1].department,
                        'count': 0
                    }
                faculty_contributions[faculty_id]['count'] += 1
        
        top_faculty = sorted(faculty_contributions.values(), 
                            key=lambda x: x['count'], reverse=True)[:5]
        
        # Top projects with IPRs
        project_iprs = {}
        for item in ipr_data:
            if item[2]:  # Project
                project_id = item[2].project_id
                if project_id not in project_iprs:
                    project_iprs[project_id] = {
                        'title': item[2].project_title,
                        'count': 0
                    }
                project_iprs[project_id]['count'] += 1
        
        top_projects = sorted(project_iprs.values(), 
                             key=lambda x: x['count'], reverse=True)[:5]
        
        return render_template('admin/ipr_analytics.html',
                             total_iprs=total_iprs,
                             granted_count=granted_count,
                             pending_count=pending_count,
                             filed_count=filed_count,
                             rejected_count=rejected_count,
                             in_progress_count=in_progress_count,
                             ipr_types=ipr_type_labels,
                             ipr_type_counts=ipr_type_counts,
                             timeline_months=timeline_months,
                             timeline_counts=timeline_counts,
                             top_faculty=top_faculty,
                             top_projects=top_projects)
    except Exception as e:
        flash(f'Error loading analytics: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@ipr_bp.route('/management', methods=['GET'])
def management():
    """IPR management interface for CRUD operations"""
    try:
        ipr_list = get_ipr_data(db)
        
        # Get faculties and projects for dropdown
        if has_role('admin'):
            faculties = db.session.query(Faculty).all()
            projects = db.session.query(Project).all()
        else:
            # Department heads see only their faculty
            department = current_user.department
            faculties = db.session.query(Faculty)\
                .filter_by(department=department).all()
            projects = db.session.query(Project)\
                .filter_by(department=department).all()
        
        return render_template('admin/ipr_management.html',
                             ipr_list=ipr_list,
                             faculties=faculties,
                             projects=projects)
    except Exception as e:
        flash(f'Error loading IPR management: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@ipr_bp.route('/add', methods=['POST'])
def add_ipr():
    """Add new IPR record"""
    try:
        # Validate required fields
        innovation_title = request.form.get('innovation_title', '').strip()
        ipr_type = request.form.get('ipr_type', '').strip()
        grant_status = request.form.get('grant_status', '').strip()
        faculty_id = request.form.get('faculty_id')
        
        if not all([innovation_title, ipr_type, grant_status, faculty_id]):
            flash('Please fill in all required fields', 'warning')
            return redirect(url_for('ipr.management'))
        
        # Get optional data
        description = request.form.get('description', '').strip()
        project_id = request.form.get('project_id') or None
        application_number = request.form.get('application_number', '').strip() or None
        
        # Parse dates
        filing_date = None
        if request.form.get('filing_date'):
            try:
                filing_date = datetime.strptime(request.form.get('filing_date'), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        grant_date = None
        if request.form.get('grant_date'):
            try:
                grant_date = datetime.strptime(request.form.get('grant_date'), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Create IPR record
        new_ipr = IPRModel(
            innovation_title=innovation_title,
            description=description,
            ipr_type=ipr_type,
            grant_status=grant_status,
            faculty_id=faculty_id,
            project_id=project_id,
            application_number=application_number,
            filing_date=filing_date,
            grant_date=grant_date,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.session.add(new_ipr)
        db.session.commit()
        
        flash(f'IPR "{innovation_title}" added successfully!', 'success')
        return redirect(url_for('ipr.management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding IPR: {str(e)}', 'danger')
        return redirect(url_for('ipr.management'))


@ipr_bp.route('/<int:ipr_id>/edit', methods=['POST'])
def edit_ipr(ipr_id):
    """Edit existing IPR record"""
    try:
        ipr_record = db.session.query(IPRModel).get(ipr_id)
        if not ipr_record:
            flash('IPR record not found', 'danger')
            return redirect(url_for('ipr.management'))
        
        # Update fields
        ipr_record.innovation_title = request.form.get('innovation_title', '').strip()
        ipr_record.description = request.form.get('description', '').strip()
        ipr_record.ipr_type = request.form.get('ipr_type', '').strip()
        ipr_record.grant_status = request.form.get('grant_status', '').strip()
        ipr_record.application_number = request.form.get('application_number', '').strip() or None
        
        # Update dates
        if request.form.get('filing_date'):
            try:
                ipr_record.filing_date = datetime.strptime(
                    request.form.get('filing_date'), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if request.form.get('grant_date'):
            try:
                ipr_record.grant_date = datetime.strptime(
                    request.form.get('grant_date'), '%Y-%m-%d').date()
            except ValueError:
                pass
        
        ipr_record.updated_at = datetime.now()
        
        db.session.commit()
        
        flash(f'IPR "{ipr_record.innovation_title}" updated successfully!', 'success')
        return redirect(url_for('ipr.management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating IPR: {str(e)}', 'danger')
        return redirect(url_for('ipr.management'))


@ipr_bp.route('/<int:ipr_id>/delete', methods=['POST'])
def delete_ipr(ipr_id):
    """Delete IPR record"""
    try:
        ipr_record = db.session.query(IPRModel).get(ipr_id)
        if not ipr_record:
            flash('IPR record not found', 'danger')
            return redirect(url_for('ipr.management'))
        
        ipr_title = ipr_record.innovation_title
        db.session.delete(ipr_record)
        db.session.commit()
        
        flash(f'IPR "{ipr_title}" deleted successfully!', 'success')
        return redirect(url_for('ipr.management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting IPR: {str(e)}', 'danger')
        return redirect(url_for('ipr.management'))


@ipr_bp.route('/export', methods=['GET'])
def export_iprs():
    """Export IPR data to CSV"""
    try:
        import csv
        from io import StringIO
        from flask import make_response
        
        ipr_data = get_ipr_data(db)
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Innovation Title',
            'IPR Type',
            'Faculty',
            'Department',
            'Status',
            'Application Number',
            'Filing Date',
            'Grant Date',
            'Project'
        ])
        
        # Data
        for item in ipr_data:
            ipr, faculty, project = item
            writer.writerow([
                ipr.innovation_title,
                ipr.ipr_type,
                faculty.name if faculty else '',
                faculty.department if faculty else '',
                ipr.grant_status,
                ipr.application_number or '',
                ipr.filing_date.strftime('%d-%b-%Y') if ipr.filing_date else '',
                ipr.grant_date.strftime('%d-%b-%Y') if ipr.grant_date else '',
                project.project_title if project else ''
            ])
        
        # Prepare response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=iprs_export.csv'
        response.headers['Content-Type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        flash(f'Error exporting IPR data: {str(e)}', 'danger')
        return redirect(url_for('ipr.management'))


# Import these at the top of your file
# from database.models import IPRModel, Faculty, Project
# from flask_login import current_user
# from auth.decorators import role_required
