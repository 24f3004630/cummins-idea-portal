"""
IPR Module Forms
WTForms for input validation and rendering
"""

try:
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, SelectField, DateField, SubmitField
    from wtforms.validators import DataRequired, Optional, Length, ValidationError, URL
    from datetime import datetime
    from ipr.config import IPR_TYPES, GRANT_STATUSES
    
    WTFORMS_AVAILABLE = True
except ImportError:
    WTFORMS_AVAILABLE = False


if WTFORMS_AVAILABLE:
    
    class IPRCreateForm(FlaskForm):
        """Form for creating new IPR record"""
        
        innovation_title = StringField(
            'Innovation Title',
            validators=[
                DataRequired(message='Innovation title is required'),
                Length(min=5, max=255, message='Title must be between 5 and 255 characters')
            ]
        )
        
        description = TextAreaField(
            'Description',
            validators=[
                Optional(),
                Length(max=5000, message='Description must be less than 5000 characters')
            ]
        )
        
        ipr_type = SelectField(
            'IPR Type',
            validators=[DataRequired(message='Please select an IPR type')],
            choices=[(k, v['label']) for k, v in IPR_TYPES.items()]
        )
        
        grant_status = SelectField(
            'Grant Status',
            validators=[DataRequired(message='Please select a grant status')],
            choices=[(k, v['label']) for k, v in GRANT_STATUSES.items()]
        )
        
        faculty_id = StringField(
            'Faculty',
            validators=[DataRequired(message='Please select a faculty member')]
        )
        
        project_id = StringField(
            'Associated Project',
            validators=[Optional()]
        )
        
        application_number = StringField(
            'Application Number',
            validators=[
                Optional(),
                Length(min=5, max=100, message='Application number must be between 5 and 100 characters')
            ]
        )
        
        filing_date = DateField(
            'Filing Date',
            validators=[Optional()],
            format='%Y-%m-%d'
        )
        
        grant_date = DateField(
            'Grant Date',
            validators=[Optional()],
            format='%Y-%m-%d'
        )
        
        submit = SubmitField('Add IPR')
        
        def validate_grant_date(self, field):
            """Validate that grant date is not before filing date"""
            if field.data and self.filing_date.data:
                if field.data < self.filing_date.data:
                    raise ValidationError('Grant date cannot be before filing date')
        
        def validate_filing_date(self, field):
            """Validate that filing date is not in the future"""
            if field.data and field.data > datetime.now().date():
                raise ValidationError('Filing date cannot be in the future')
        
        def validate_grant_date_future(self, field):
            """Validate that grant date is not in the future"""
            if field.data and field.data > datetime.now().date():
                raise ValidationError('Grant date cannot be in the future')
    
    
    class IPREditForm(FlaskForm):
        """Form for editing existing IPR record"""
        
        innovation_title = StringField(
            'Innovation Title',
            validators=[
                DataRequired(message='Innovation title is required'),
                Length(min=5, max=255, message='Title must be between 5 and 255 characters')
            ]
        )
        
        description = TextAreaField(
            'Description',
            validators=[
                Optional(),
                Length(max=5000, message='Description must be less than 5000 characters')
            ]
        )
        
        ipr_type = SelectField(
            'IPR Type',
            validators=[DataRequired(message='Please select an IPR type')],
            choices=[(k, v['label']) for k, v in IPR_TYPES.items()]
        )
        
        grant_status = SelectField(
            'Grant Status',
            validators=[DataRequired(message='Please select a grant status')],
            choices=[(k, v['label']) for k, v in GRANT_STATUSES.items()]
        )
        
        application_number = StringField(
            'Application Number',
            validators=[
                Optional(),
                Length(min=5, max=100, message='Application number must be between 5 and 100 characters')
            ]
        )
        
        filing_date = DateField(
            'Filing Date',
            validators=[Optional()],
            format='%Y-%m-%d'
        )
        
        grant_date = DateField(
            'Grant Date',
            validators=[Optional()],
            format='%Y-%m-%d'
        )
        
        submit = SubmitField('Update IPR')
        
        def validate_grant_date(self, field):
            """Validate that grant date is not before filing date"""
            if field.data and self.filing_date.data:
                if field.data < self.filing_date.data:
                    raise ValidationError('Grant date cannot be before filing date')
        
        def validate_filing_date(self, field):
            """Validate that filing date is not in the future"""
            if field.data and field.data > datetime.now().date():
                raise ValidationError('Filing date cannot be in the future')
    
    
    class IPRSearchForm(FlaskForm):
        """Form for searching IPRs"""
        
        search_query = StringField(
            'Search',
            validators=[
                Optional(),
                Length(min=2, max=255, message='Search query must be between 2 and 255 characters')
            ],
            render_kw={"placeholder": "Search by title, application number..."}
        )
        
        status_filter = SelectField(
            'Status',
            validators=[Optional()],
            choices=[('', 'All Status')] + [(k, v['label']) for k, v in GRANT_STATUSES.items()],
            coerce=str
        )
        
        type_filter = SelectField(
            'Type',
            validators=[Optional()],
            choices=[('', 'All Types')] + [(k, v['label']) for k, v in IPR_TYPES.items()],
            coerce=str
        )
        
        submit = SubmitField('Search')
    
    
    class IPRBulkActionForm(FlaskForm):
        """Form for bulk operations on IPRs"""
        
        action = SelectField(
            'Action',
            validators=[DataRequired(message='Please select an action')],
            choices=[
                ('', 'Select Action'),
                ('update_status', 'Update Status'),
                ('export', 'Export'),
                ('delete', 'Delete')
            ]
        )
        
        new_status = SelectField(
            'New Status',
            validators=[Optional()],
            choices=[(k, v['label']) for k, v in GRANT_STATUSES.items()]
        )
        
        submit = SubmitField('Apply')

else:
    # Fallback simple form class if WTForms is not available
    class IPRCreateForm:
        """Fallback form without WTForms"""
        def __init__(self, data=None):
            self.innovation_title = data.get('innovation_title', '') if data else ''
            self.description = data.get('description', '') if data else ''
            self.ipr_type = data.get('ipr_type', '') if data else ''
            self.grant_status = data.get('grant_status', '') if data else ''
            self.faculty_id = data.get('faculty_id', '') if data else ''
            self.project_id = data.get('project_id', '') if data else ''
            self.application_number = data.get('application_number', '') if data else ''
            self.filing_date = data.get('filing_date', '') if data else ''
            self.grant_date = data.get('grant_date', '') if data else ''
    
    class IPREditForm(IPRCreateForm):
        pass
    
    class IPRSearchForm:
        def __init__(self, data=None):
            self.search_query = data.get('search_query', '') if data else ''
            self.status_filter = data.get('status_filter', '') if data else ''
            self.type_filter = data.get('type_filter', '') if data else ''
