"""
IPR/Patent Management Module
Handles all intellectual property rights and patent management functionality

This module provides:
- IPR/Patent record management (CRUD operations)
- Faculty and project associations
- IPR monitoring and tracking dashboards
- Analytics and reporting
- Export functionality for data analysis
"""

from .routes import ipr_bp

__all__ = ['ipr_bp']
