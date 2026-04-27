"""
IPR/Patent Database Models
Defines database schema and relationships for IPR management
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime

# This file extends your existing database/models.py
# Add this to your existing models.py or import and use separately


class IPRModel:
    """
    IPR/Patent Record Model
    Stores information about intellectual property registrations
    
    Attributes:
        ipr_id: Unique identifier
        innovation_title: Title of the innovation/invention
        description: Detailed description of the IPR
        ipr_type: Type of IPR (Patent, Copyright, Trademark, Trade Secret, Design Patent)
        grant_status: Current status (Filed, Pending, Granted, Rejected)
        faculty_id: Reference to faculty member who created/owns the IPR
        project_id: Reference to associated project (optional)
        application_number: Official application number from IP office
        filing_date: Date IPR application was filed
        grant_date: Date IPR was granted (if applicable)
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
    """
    
    # Use this SQLAlchemy model structure:
    # __tablename__ = 'ipr_records'
    # 
    # ipr_id = Column(Integer, primary_key=True)
    # innovation_title = Column(String(255), nullable=False)
    # description = Column(Text)
    # ipr_type = Column(String(50), nullable=False)  # Patent, Copyright, Trademark, etc.
    # grant_status = Column(String(50), nullable=False)  # Filed, Pending, Granted, Rejected
    # faculty_id = Column(Integer, ForeignKey('faculty.faculty_id'), nullable=False)
    # project_id = Column(Integer, ForeignKey('projects.project_id'), nullable=True)
    # application_number = Column(String(100), unique=True)
    # filing_date = Column(Date)
    # grant_date = Column(Date)
    # created_at = Column(DateTime, default=datetime.now)
    # updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    # 
    # # Relationships
    # faculty = relationship('Faculty', backref='iprs')
    # project = relationship('Project', backref='iprs')
    
    pass


# Example SQLAlchemy implementation:
"""
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class IPR(db.Model):
    __tablename__ = 'ipr_records'
    
    ipr_id = db.Column(db.Integer, primary_key=True)
    innovation_title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    ipr_type = db.Column(
        db.String(50), 
        nullable=False,
        index=True
    )
    grant_status = db.Column(
        db.String(50), 
        nullable=False,
        index=True
    )
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=True)
    application_number = db.Column(db.String(100), unique=True, index=True)
    filing_date = db.Column(db.Date)
    grant_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    faculty = db.relationship('Faculty', backref='iprs')
    project = db.relationship('Project', backref='iprs')
    
    def __repr__(self):
        return f'<IPR {self.ipr_id}: {self.innovation_title}>'
    
    def is_granted(self):
        return self.grant_status == 'Granted'
    
    def is_pending(self):
        return self.grant_status in ['Filed', 'Pending']
    
    def is_rejected(self):
        return self.grant_status == 'Rejected'
    
    def days_pending(self):
        '''Calculate days since filing'''
        if self.filing_date:
            return (datetime.now().date() - self.filing_date).days
        return None
"""
