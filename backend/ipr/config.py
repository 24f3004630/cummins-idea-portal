"""
IPR Module Configuration
Centralized configuration for the IPR management module
"""

# IPR Types
IPR_TYPES = {
    'Patent': {
        'label': 'Patent',
        'description': 'Utility or design patent protection',
        'typical_duration_months': 36,
        'icon': 'fa-lightbulb'
    },
    'Copyright': {
        'label': 'Copyright',
        'description': 'Automatic protection for creative works',
        'typical_duration_months': 12,
        'icon': 'fa-copyright'
    },
    'Trademark': {
        'label': 'Trademark',
        'description': 'Brand name and logo protection',
        'typical_duration_months': 24,
        'icon': 'fa-trademark'
    },
    'Trade Secret': {
        'label': 'Trade Secret',
        'description': 'Confidential business information protection',
        'typical_duration_months': 6,
        'icon': 'fa-lock'
    },
    'Design Patent': {
        'label': 'Design Patent',
        'description': 'Protection for product design',
        'typical_duration_months': 36,
        'icon': 'fa-cube'
    }
}

# Grant Status
GRANT_STATUSES = {
    'Filed': {
        'label': 'Filed',
        'description': 'Application submitted to IP office',
        'color': 'warning',
        'icon': 'fa-file-alt',
        'position': 1
    },
    'Pending': {
        'label': 'Pending',
        'description': 'Under review by IP office',
        'color': 'info',
        'icon': 'fa-hourglass-half',
        'position': 2
    },
    'Granted': {
        'label': 'Granted',
        'description': 'Successfully granted/registered',
        'color': 'success',
        'icon': 'fa-check-circle',
        'position': 3
    },
    'Rejected': {
        'label': 'Rejected',
        'description': 'Application rejected',
        'color': 'danger',
        'icon': 'fa-times-circle',
        'position': 4
    }
}

# Alert Thresholds
ALERT_THRESHOLDS = {
    'high_priority_days': 1095,  # 3 years
    'medium_priority_days': 730,  # 2 years
    'low_priority_days': 365,     # 1 year
}

# Pagination
ITEMS_PER_PAGE = 20
EXPORT_BATCH_SIZE = 1000

# Dashboard Settings
DASHBOARD_CONFIG = {
    'enable_analytics': True,
    'enable_export': True,
    'enable_bulk_operations': True,
    'max_export_records': 10000,
    'chart_colors': {
        'Granted': '#28a745',
        'Pending': '#17a2b8',
        'Filed': '#ffc107',
        'Rejected': '#dc3545'
    }
}

# Email Notifications
EMAIL_NOTIFICATIONS = {
    'enabled': True,
    'on_status_change': True,
    'on_grant': True,
    'threshold_alert_enabled': True,
    'threshold_alert_days': 1095
}

# Search Configuration
SEARCH_CONFIG = {
    'enable_full_text_search': True,
    'searchable_fields': [
        'innovation_title',
        'description',
        'application_number',
        'ipr_type'
    ]
}

# Export Configuration
EXPORT_CONFIG = {
    'formats': ['csv', 'xlsx'],
    'default_format': 'csv',
    'include_fields': [
        'innovation_title',
        'description',
        'ipr_type',
        'grant_status',
        'faculty_name',
        'faculty_department',
        'project_title',
        'application_number',
        'filing_date',
        'grant_date'
    ]
}

# Analytics Configuration
ANALYTICS_CONFIG = {
    'enable_charts': True,
    'chart_library': 'chart.js',
    'enable_timeline': True,
    'enable_faculty_stats': True,
    'enable_project_stats': True,
    'refresh_interval_minutes': 5
}

# Report Configuration
REPORT_CONFIG = {
    'auto_generate_summary': True,
    'include_faculty_breakdown': True,
    'include_alerts': True,
    'include_pending_age_analysis': True,
    'alert_priority_levels': ['high', 'medium', 'low']
}

# API Configuration
API_CONFIG = {
    'enable_api': True,
    'api_prefix': '/api/ipr',
    'require_auth': True,
    'rate_limit_enabled': True,
    'rate_limit_requests': 100,
    'rate_limit_period_seconds': 3600
}

# Database Configuration
DATABASE_CONFIG = {
    'enable_soft_delete': False,
    'enable_audit_log': True,
    'index_fields': [
        'ipr_type',
        'grant_status',
        'faculty_id',
        'project_id',
        'application_number'
    ]
}

# Permission Configuration
PERMISSIONS = {
    'admin': {
        'view_all': True,
        'create': True,
        'edit_all': True,
        'delete_all': True,
        'export': True,
        'see_analytics': True
    },
    'department_head': {
        'view_all': True,
        'create': True,
        'edit_department': True,
        'delete_department': True,
        'export': True,
        'see_analytics': True
    },
    'faculty': {
        'view_own': True,
        'create': True,
        'edit_own': True,
        'delete_own': False,
        'export': False,
        'see_analytics': False
    }
}

# Status Transitions
VALID_STATUS_TRANSITIONS = {
    'Filed': ['Pending', 'Rejected'],
    'Pending': ['Granted', 'Rejected'],
    'Granted': [],
    'Rejected': ['Filed']  # Can be refiled
}

# Validation Rules
VALIDATION_RULES = {
    'innovation_title': {
        'required': True,
        'min_length': 5,
        'max_length': 255
    },
    'description': {
        'required': False,
        'max_length': 5000
    },
    'ipr_type': {
        'required': True,
        'valid_values': list(IPR_TYPES.keys())
    },
    'grant_status': {
        'required': True,
        'valid_values': list(GRANT_STATUSES.keys())
    },
    'faculty_id': {
        'required': True,
        'type': 'integer'
    },
    'project_id': {
        'required': False,
        'type': 'integer'
    },
    'application_number': {
        'required': False,
        'min_length': 5,
        'max_length': 100,
        'unique': True
    }
}

# Module Features
FEATURES = {
    'iprs': {
        'enabled': True,
        'allow_create': True,
        'allow_edit': True,
        'allow_delete': True,
        'allow_bulk_add': True,
        'allow_bulk_delete': True
    },
    'analytics': {
        'enabled': True,
        'show_status_distribution': True,
        'show_type_distribution': True,
        'show_timeline': True,
        'show_faculty_stats': True,
        'show_project_stats': True
    },
    'notifications': {
        'enabled': True,
        'email_alerts': True,
        'in_app_alerts': True,
        'status_change_alerts': True,
        'threshold_alerts': True
    },
    'reports': {
        'enabled': True,
        'auto_summary': True,
        'manual_export': True,
        'scheduled_reports': True
    }
}
