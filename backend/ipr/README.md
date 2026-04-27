# IPR/Patent Management Module Documentation

## Overview
The IPR (Intellectual Property Rights) module is a comprehensive system for managing and tracking patents, copyrights, trademarks, trade secrets, and design patents within the Idea Portal ecosystem.

## Features

### 1. **IPR Monitoring Dashboard**
- **URL**: `/admin/ipr/monitoring`
- **Features**:
  - View all IPR records with status filtering
  - Tabbed interface by grant status (All, Filed, Pending, Granted, Rejected)
  - Quick access to detailed IPR information
  - Real-time status badges with color coding

### 2. **Analytics Dashboard**
- **URL**: `/admin/ipr/analytics`
- **Features**:
  - Key metrics cards (Total, Granted, In Progress, Rejected)
  - IPR status distribution chart (doughnut chart)
  - IPR type distribution (bar chart)
  - Timeline view of filed IPRs
  - Top faculty contributors
  - Top projects with IPRs
  - Interactive charts powered by Chart.js

### 3. **IPR Management Interface**
- **URL**: `/admin/ipr/management`
- **Features**:
  - Full CRUD operations (Create, Read, Update, Delete)
  - Search functionality
  - Status filtering
  - Modal-based forms
  - Batch operations support

### 4. **Data Export**
- **URL**: `/admin/ipr/export`
- **Format**: CSV
- **Includes**: All IPR fields with faculty and project associations

## Installation & Setup

### Step 1: Database Model Setup
Add the IPR model to your `database/models.py`:

```python
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

class IPR(db.Model):
    __tablename__ = 'ipr_records'
    
    ipr_id = db.Column(db.Integer, primary_key=True)
    innovation_title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    ipr_type = db.Column(db.String(50), nullable=False, index=True)
    grant_status = db.Column(db.String(50), nullable=False, index=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=True)
    application_number = db.Column(db.String(100), unique=True, index=True)
    filing_date = db.Column(db.Date)
    grant_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    faculty = db.relationship('Faculty', backref='iprs')
    project = db.relationship('Project', backref='iprs')
    
    def __repr__(self):
        return f'<IPR {self.ipr_id}: {self.innovation_title}>'
    
    def is_granted(self):
        """Check if IPR has been granted"""
        return self.grant_status == 'Granted'
    
    def is_pending(self):
        """Check if IPR is in progress"""
        return self.grant_status in ['Filed', 'Pending']
    
    def is_rejected(self):
        """Check if IPR was rejected"""
        return self.grant_status == 'Rejected'
```

### Step 2: Register Blueprint in Main App
In your `app.py`:

```python
from flask import Flask
from ipr import ipr_bp

app = Flask(__name__)

# ... other configurations ...

# Register IPR blueprint
app.register_blueprint(ipr_bp)

# Or if using app factory pattern:
def create_app(config=None):
    app = Flask(__name__)
    
    # ... setup code ...
    
    from ipr import ipr_bp
    app.register_blueprint(ipr_bp)
    
    return app
```

### Step 3: Update Routes Module
Update `ipr/routes.py` with proper imports:

```python
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
from database.models import IPR, Faculty, Project  # Adjust based on your model names
from database.db import db  # Your database instance
from flask_login import current_user
from auth.decorators import role_required

# ... rest of the routes
```

### Step 4: Create Database Migration
```bash
# Using Flask-Migrate
flask db migrate -m "Add IPR/Patent module"
flask db upgrade
```

Or manually create the table if not using migrations:
```sql
CREATE TABLE ipr_records (
    ipr_id INT PRIMARY KEY AUTO_INCREMENT,
    innovation_title VARCHAR(255) NOT NULL,
    description TEXT,
    ipr_type VARCHAR(50) NOT NULL,
    grant_status VARCHAR(50) NOT NULL,
    faculty_id INT NOT NULL,
    project_id INT,
    application_number VARCHAR(100) UNIQUE,
    filing_date DATE,
    grant_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_faculty (faculty_id),
    INDEX idx_project (project_id),
    INDEX idx_status (grant_status),
    INDEX idx_type (ipr_type),
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);
```

### Step 5: Update Navigation Menu
Add IPR links to your base template (`templates/base.html`):

```html
<!-- In Admin Menu -->
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" id="iprDropdown" role="button" data-bs-toggle="dropdown">
        <i class="fas fa-certificate"></i> IPR Management
    </a>
    <ul class="dropdown-menu" aria-labelledby="iprDropdown">
        <li><a class="dropdown-item" href="/admin/ipr/monitoring"><i class="fas fa-eye"></i> Monitoring</a></li>
        <li><a class="dropdown-item" href="/admin/ipr/analytics"><i class="fas fa-chart-bar"></i> Analytics</a></li>
        <li><a class="dropdown-item" href="/admin/ipr/management"><i class="fas fa-cogs"></i> Management</a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="/admin/ipr/export"><i class="fas fa-download"></i> Export Data</a></li>
    </ul>
</li>
```

## API Endpoints

### GET Endpoints

| Endpoint | Description | Returns |
|----------|-------------|---------|
| `/admin/ipr/monitoring` | IPR monitoring dashboard | HTML Page |
| `/admin/ipr/analytics` | Analytics dashboard with charts | HTML Page |
| `/admin/ipr/management` | IPR CRUD interface | HTML Page |
| `/admin/ipr/export` | Export IPRs to CSV | CSV File |

### POST Endpoints

| Endpoint | Description | Parameters |
|----------|-------------|-----------|
| `/admin/ipr/add` | Add new IPR | form data |
| `/admin/ipr/<id>/edit` | Edit IPR record | form data |
| `/admin/ipr/<id>/delete` | Delete IPR | form data |

## Data Model

### IPR Record Structure
```json
{
  "ipr_id": 1,
  "innovation_title": "AI-Based Analysis Tool",
  "description": "A machine learning tool for data analysis",
  "ipr_type": "Patent",
  "grant_status": "Pending",
  "faculty_id": 5,
  "project_id": 10,
  "application_number": "202121012345",
  "filing_date": "2021-06-15",
  "grant_date": null,
  "created_at": "2021-06-15 10:30:00",
  "updated_at": "2021-06-15 10:30:00"
}
```

## Usage Examples

### Adding an IPR
```python
from database.models import IPR
from database.db import db
from datetime import date

new_ipr = IPR(
    innovation_title="Novel Encryption Algorithm",
    description="A new approach to data encryption",
    ipr_type="Patent",
    grant_status="Filed",
    faculty_id=1,
    project_id=1,
    application_number="US123456789",
    filing_date=date(2021, 6, 15)
)

db.session.add(new_ipr)
db.session.commit()
```

### Querying IPRs
```python
# Get all granted IPRs
granted_iprs = IPR.query.filter_by(grant_status='Granted').all()

# Get IPRs by faculty
faculty_iprs = IPR.query.filter_by(faculty_id=1).all()

# Get pending IPRs for a project
project_pending = IPR.query.filter_by(
    project_id=1,
    grant_status='Pending'
).all()
```

## Front-End Features

### Monitoring Dashboard
- **Status Tabs**: All, Filed, Pending, Granted, Rejected
- **Quick Metrics**: Count per status with percentage
- **Action Buttons**: View details for each IPR
- **Responsive Table**: Works on mobile and desktop

### Analytics Dashboard
- **Key Metrics**: Total, Granted, In Progress, Rejected
- **Status Distribution**: Doughnut chart visualization
- **Type Distribution**: Bar chart by IPR type
- **Timeline**: Line chart showing IPRs filed over time
- **Top Contributors**: Faculty and projects with most IPRs

### Management Interface
- **Search Bar**: Real-time search across all fields
- **Status Filter**: Filter by grant status
- **Modal Forms**: Add/edit with inline validation
- **Confirmation**: Delete operation confirmation
- **Batch Export**: Download all data as CSV

## Advanced Features

### Role-Based Access Control
Add role decorators to routes for access control:

```python
from auth.decorators import role_required

@ipr_bp.route('/management', methods=['GET'])
@role_required(['admin', 'department_head'])
def management():
    # Only admins and department heads can access
    pass
```

### Custom Filters
Extend the monitoring dashboard with custom filters:

```python
# Filter by date range, faculty department, etc.
iprs = IPR.query.filter(
    IPR.filing_date >= start_date,
    IPR.filing_date <= end_date
).all()
```

### Notifications
Set up notifications for IPR status changes:

```python
@ipr_bp.route('/<int:ipr_id>/edit', methods=['POST'])
def edit_ipr(ipr_id):
    ipr = IPR.query.get(ipr_id)
    old_status = ipr.grant_status
    # ... update IPR ...
    new_status = ipr.grant_status
    
    if old_status != new_status:
        send_notification(ipr.faculty, 
                         f"IPR status changed from {old_status} to {new_status}")
```

## Troubleshooting

### Issue: Templates not found
**Solution**: Ensure templates are in `templates/admin/` directory with correct names:
- `iprs.html`
- `ipr_analytics.html`
- `ipr_management.html`

### Issue: Database migrations fail
**Solution**: Check that IPR model is imported in migration files and run migrations in order.

### Issue: Charts not displaying
**Solution**: Ensure Chart.js is loaded from CDN. Add to base template:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### Issue: Permission denied on exports
**Solution**: Ensure user has appropriate role/permissions for export functionality.

## Performance Optimization

### Database Indexing
The model includes indexes on frequently queried fields:
- `ipr_type`
- `grant_status`
- `faculty_id`
- `application_number`

### Query Optimization
Use eager loading for related data:
```python
from sqlalchemy.orm import joinedload

iprs = IPR.query.options(
    joinedload(IPR.faculty),
    joinedload(IPR.project)
).all()
```

## Future Enhancements

- [ ] IPR renewal reminders
- [ ] Bulk IPR import from CSV
- [ ] Email notifications for status changes
- [ ] PDF report generation
- [ ] IPR timeline visualization
- [ ] Collaboration features for co-inventors
- [ ] Integration with official IP office APIs
- [ ] Advanced search with filters
- [ ] Custom field support

## Support

For issues or questions about the IPR module, please:
1. Check this documentation
2. Review the code comments
3. Check database setup
4. Verify all imports are correct
5. Check browser console for frontend errors
