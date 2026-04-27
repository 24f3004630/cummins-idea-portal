"""
IPR Module Utilities
Provides helper functions and utilities for IPR management
"""

from datetime import datetime, timedelta
from sqlalchemy import func
from typing import List, Dict, Optional


class IPRUtils:
    """Utility class for IPR-related operations"""
    
    @staticmethod
    def calculate_grant_probability(filing_date, ipr_type):
        """
        Estimate grant probability based on filing date and type
        Note: This is a simplified estimation for demo purposes
        """
        if not filing_date:
            return 0
        
        months_pending = (datetime.now().date() - filing_date).days / 30
        
        # Type-based probabilities (simplified)
        base_probabilities = {
            'Patent': 0.65,
            'Copyright': 0.95,
            'Trademark': 0.75,
            'Trade Secret': 0.90,
            'Design Patent': 0.70
        }
        
        base_prob = base_probabilities.get(ipr_type, 0.70)
        
        # Adjust based on months pending
        if months_pending > 36:  # After 3 years
            return min(base_prob * 0.8, 0.95)  # Decrease probability
        elif months_pending > 12:
            return base_prob
        else:
            return base_prob * 0.5  # New applications have lower probability
    
    @staticmethod
    def get_status_color(status: str) -> str:
        """Get Bootstrap color class for status badge"""
        status_colors = {
            'Granted': 'success',
            'Pending': 'info',
            'Filed': 'warning',
            'Rejected': 'danger'
        }
        return status_colors.get(status, 'secondary')
    
    @staticmethod
    def get_status_icon(status: str) -> str:
        """Get Font Awesome icon for status"""
        status_icons = {
            'Granted': 'fa-check-circle',
            'Pending': 'fa-hourglass-half',
            'Filed': 'fa-file-alt',
            'Rejected': 'fa-times-circle'
        }
        return status_icons.get(status, 'fa-question-circle')
    
    @staticmethod
    def calculate_days_pending(filing_date) -> Optional[int]:
        """Calculate number of days since IPR filing"""
        if filing_date:
            return (datetime.now().date() - filing_date).days
        return None
    
    @staticmethod
    def format_filing_duration(filing_date, grant_date=None) -> str:
        """Format the duration of the filing process"""
        if not filing_date:
            return "N/A"
        
        end_date = grant_date if grant_date else datetime.now().date()
        duration = (end_date - filing_date).days
        
        years = duration // 365
        months = (duration % 365) // 30
        days = duration % 30
        
        parts = []
        if years > 0:
            parts.append(f"{years}y")
        if months > 0:
            parts.append(f"{months}m")
        if days > 0 or not parts:
            parts.append(f"{days}d")
        
        return " ".join(parts)
    
    @staticmethod
    def get_status_summary(iprs_list: List) -> Dict:
        """Get summary statistics from IPR list"""
        summary = {
            'total': len(iprs_list),
            'granted': 0,
            'pending': 0,
            'filed': 0,
            'rejected': 0,
            'by_type': {},
            'by_faculty': {},
            'average_pending_days': 0
        }
        
        pending_days_list = []
        
        for item in iprs_list:
            ipr = item[0] if isinstance(item, tuple) else item
            faculty = item[1] if isinstance(item, tuple) and len(item) > 1 else None
            
            # Count by status
            if ipr.grant_status == 'Granted':
                summary['granted'] += 1
            elif ipr.grant_status == 'Pending':
                summary['pending'] += 1
            elif ipr.grant_status == 'Filed':
                summary['filed'] += 1
            elif ipr.grant_status == 'Rejected':
                summary['rejected'] += 1
            
            # Count by type
            ipr_type = ipr.ipr_type
            summary['by_type'][ipr_type] = summary['by_type'].get(ipr_type, 0) + 1
            
            # Count by faculty
            if faculty:
                faculty_name = faculty.name
                summary['by_faculty'][faculty_name] = summary['by_faculty'].get(faculty_name, 0) + 1
            
            # Calculate pending days
            days_pending = IPRUtils.calculate_days_pending(ipr.filing_date)
            if days_pending is not None:
                pending_days_list.append(days_pending)
        
        # Calculate average pending days
        if pending_days_list:
            summary['average_pending_days'] = int(sum(pending_days_list) / len(pending_days_list))
        
        return summary
    
    @staticmethod
    def generate_application_number(faculty_id: int, ipr_type: str) -> str:
        """Generate a unique application number format"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        type_code = ipr_type[:3].upper()
        return f"{type_code}{faculty_id:03d}{timestamp}"
    
    @staticmethod
    def get_pending_iprs_by_age(iprs_list: List) -> Dict:
        """Categorize pending IPRs by age"""
        categories = {
            'less_than_6_months': [],
            '6_to_12_months': [],
            '1_to_2_years': [],
            '2_to_3_years': [],
            'more_than_3_years': []
        }
        
        for item in iprs_list:
            ipr = item[0] if isinstance(item, tuple) else item
            
            if ipr.grant_status not in ['Pending', 'Filed']:
                continue
            
            days_pending = IPRUtils.calculate_days_pending(ipr.filing_date)
            if days_pending is None:
                continue
            
            if days_pending < 180:
                categories['less_than_6_months'].append(ipr)
            elif days_pending < 365:
                categories['6_to_12_months'].append(ipr)
            elif days_pending < 730:
                categories['1_to_2_years'].append(ipr)
            elif days_pending < 1095:
                categories['2_to_3_years'].append(ipr)
            else:
                categories['more_than_3_years'].append(ipr)
        
        return categories
    
    @staticmethod
    def get_uptime_alert(ipr):
        """Generate alert message for long-pending IPRs"""
        days_pending = IPRUtils.calculate_days_pending(ipr.filing_date)
        
        if days_pending is None:
            return None
        
        if days_pending > 1095:  # More than 3 years
            return {
                'type': 'danger',
                'message': f'IPR pending for {days_pending} days (>3 years). Consider follow-up.',
                'priority': 'high'
            }
        elif days_pending > 730:  # More than 2 years
            return {
                'type': 'warning',
                'message': f'IPR pending for {days_pending} days (>2 years).',
                'priority': 'medium'
            }
        elif days_pending > 365:  # More than 1 year
            return {
                'type': 'info',
                'message': f'IPR pending for {days_pending} days (>1 year).',
                'priority': 'low'
            }
        
        return None


class IPRReportGenerator:
    """Generate various reports for IPR data"""
    
    @staticmethod
    def generate_summary_report(iprs_list: List) -> Dict:
        """Generate comprehensive summary report"""
        summary = IPRUtils.get_status_summary(iprs_list)
        
        return {
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'pending_by_age': IPRUtils.get_pending_iprs_by_age(iprs_list),
            'alerts': IPRReportGenerator.generate_alerts(iprs_list)
        }
    
    @staticmethod
    def generate_alerts(iprs_list: List) -> List[Dict]:
        """Generate alerts for IPR data"""
        alerts = []
        
        for item in iprs_list:
            ipr = item[0] if isinstance(item, tuple) else item
            alert = IPRUtils.get_uptime_alert(ipr)
            if alert:
                alert['ipr_id'] = ipr.ipr_id
                alert['title'] = ipr.innovation_title
                alerts.append(alert)
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return alerts
    
    @staticmethod
    def generate_faculty_report(iprs_list: List) -> List[Dict]:
        """Generate per-faculty IPR statistics"""
        faculty_stats = {}
        
        for item in iprs_list:
            ipr = item[0] if isinstance(item, tuple) else item
            faculty = item[1] if isinstance(item, tuple) and len(item) > 1 else None
            
            if not faculty:
                continue
            
            faculty_id = faculty.faculty_id
            if faculty_id not in faculty_stats:
                faculty_stats[faculty_id] = {
                    'name': faculty.name,
                    'department': faculty.department,
                    'total_iprs': 0,
                    'granted': 0,
                    'pending': 0,
                    'rejected': 0,
                    'types': {}
                }
            
            stats = faculty_stats[faculty_id]
            stats['total_iprs'] += 1
            
            if ipr.grant_status == 'Granted':
                stats['granted'] += 1
            elif ipr.grant_status in ['Pending', 'Filed']:
                stats['pending'] += 1
            elif ipr.grant_status == 'Rejected':
                stats['rejected'] += 1
            
            ipr_type = ipr.ipr_type
            stats['types'][ipr_type] = stats['types'].get(ipr_type, 0) + 1
        
        # Calculate success rate
        for faculty_id, stats in faculty_stats.items():
            if stats['total_iprs'] > 0:
                stats['grant_rate'] = round(
                    (stats['granted'] / stats['total_iprs']) * 100, 2
                )
            else:
                stats['grant_rate'] = 0
        
        return sorted(
            faculty_stats.values(),
            key=lambda x: x['total_iprs'],
            reverse=True
        )


class IPRValidation:
    """Validation utilities for IPR data"""
    
    @staticmethod
    def validate_innovation_title(title: str) -> tuple[bool, str]:
        """Validate innovation title"""
        if not title or len(title.strip()) == 0:
            return False, "Title cannot be empty"
        if len(title) > 255:
            return False, "Title must be less than 255 characters"
        if len(title) < 5:
            return False, "Title must be at least 5 characters"
        return True, "Valid"
    
    @staticmethod
    def validate_ipr_type(ipr_type: str) -> tuple[bool, str]:
        """Validate IPR type"""
        valid_types = ['Patent', 'Copyright', 'Trademark', 'Trade Secret', 'Design Patent']
        if ipr_type not in valid_types:
            return False, f"IPR type must be one of: {', '.join(valid_types)}"
        return True, "Valid"
    
    @staticmethod
    def validate_grant_status(status: str) -> tuple[bool, str]:
        """Validate grant status"""
        valid_statuses = ['Filed', 'Pending', 'Granted', 'Rejected']
        if status not in valid_statuses:
            return False, f"Status must be one of: {', '.join(valid_statuses)}"
        return True, "Valid"
    
    @staticmethod
    def validate_dates(filing_date, grant_date) -> tuple[bool, str]:
        """Validate filing and grant dates"""
        if filing_date and grant_date:
            if grant_date < filing_date:
                return False, "Grant date cannot be before filing date"
        if filing_date and filing_date > datetime.now().date():
            return False, "Filing date cannot be in the future"
        if grant_date and grant_date > datetime.now().date():
            return False, "Grant date cannot be in the future"
        return True, "Valid"
    
    @staticmethod
    def validate_application_number(application_number: str) -> tuple[bool, str]:
        """Validate application number format"""
        if not application_number:
            return True, "Optional field"
        if len(application_number) < 5:
            return False, "Application number too short"
        if len(application_number) > 100:
            return False, "Application number too long"
        return True, "Valid"
