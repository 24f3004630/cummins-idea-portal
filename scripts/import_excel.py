"""Import Excel data into the portal database.

Usage:
  python scripts/import_excel.py "Latest Data as on 230626.xlsx" --sheet People

The script currently upserts rows into `Person` model. It matches common
column names (case-insensitive) such as: email, name, type, department,
phone, skills, bio, password, is_approved.

Requires: pandas, openpyxl
    pip install pandas openpyxl
"""
import argparse
import os
import re
import sys
import logging

import pandas as pd
from sqlalchemy import func

# Ensure the repo root is on sys.path when running this script directly.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.database.db import db
from backend.database.models import Person, ResearchProject

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


COMMON_PERSON_COLUMNS = {
    'email': ['email', 'e-mail', 'email address'],
    'name': ['name', 'full name'],
    'type': ['type', 'role', 'user type'],
    'department': ['department', 'dept'],
    'phone': ['phone', 'phone number', 'contact'],
    'skills': ['skills', 'skillset'],
    'bio': ['bio', 'about', 'profile'],
    'password': ['password', 'pwd'],
    'is_approved': ['is_approved', 'approved', 'is approved']
}

COMMON_PROJECT_COLUMNS = {
    'project_title': ['brand name', 'project title', 'title', 'brand'],
    'project_description': ['product description', 'description', 'project description'],
    'domain': ['product category', 'product category', 'domain', 'category'],
    'project_status': ['current stage', 'status', 'idea status', 'project status'],
    'faculty_name': ['name', 'faculty / student', 'faculty name', 'student name']
}


def find_column(df_cols, candidates):
    """Return the first matching column name from df_cols for given candidates."""
    lowered = {c.lower(): c for c in df_cols}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    return None


def build_mapping(df):
    mapping = {}
    for key, candidates in COMMON_PERSON_COLUMNS.items():
        col = find_column(df.columns, candidates)
        if col:
            mapping[key] = col
    return mapping


def build_project_mapping(df):
    mapping = {}
    for key, candidates in COMMON_PROJECT_COLUMNS.items():
        col = find_column(df.columns, candidates)
        if col:
            mapping[key] = col
    return mapping


def to_bool(val):
    if pd.isna(val):
        return False
    if isinstance(val, bool):
        return val
    sval = str(val).strip().lower()
    return sval in ('1', 'true', 'yes', 'y', 'approved', 't')


def upsert_person(row, mapping):
    email = row.get(mapping.get('email'))
    if pd.isna(email) or not str(email).strip():
        logging.warning('Skipping row without email: %s', row.to_dict())
        return False
    email = str(email).strip()

    person = Person.query.filter_by(email=email).first()
    is_new = person is None
    if is_new:
        person = Person(email=email, name='', password='', type='Student')

    # Map fields if available
    if 'name' in mapping:
        name = row.get(mapping['name'])
        if not pd.isna(name):
            person.name = str(name).strip()
    if 'type' in mapping:
        t = row.get(mapping['type'])
        if not pd.isna(t):
            person.type = str(t).strip()
    if 'department' in mapping:
        d = row.get(mapping['department'])
        if not pd.isna(d):
            person.department = str(d).strip()
    if 'phone' in mapping:
        p = row.get(mapping['phone'])
        if not pd.isna(p):
            person.phone = str(p).strip()
    if 'skills' in mapping:
        s = row.get(mapping['skills'])
        if not pd.isna(s):
            person.skills = str(s).strip()
    if 'bio' in mapping:
        b = row.get(mapping['bio'])
        if not pd.isna(b):
            person.bio = str(b).strip()
    if 'password' in mapping:
        pw = row.get(mapping['password'])
        if not pd.isna(pw) and str(pw).strip():
            person.set_password(str(pw).strip())
    else:
        # Ensure new users have a password
        if is_new and (not getattr(person, 'password', None)):
            person.set_password('changeme123')

    if 'is_approved' in mapping:
        ia = row.get(mapping['is_approved'])
        person.is_approved = to_bool(ia)

    if is_new:
        db.session.add(person)

    return True


def import_people(filepath, sheet_name=None, dry_run=False):
    logging.info('Reading Excel: %s (sheet=%s)', filepath, sheet_name)
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    mapping = build_mapping(df)
    logging.info('Auto-detected columns: %s', mapping)

    inserted = 0
    skipped = 0

    with app.app_context():
        for _, row in df.iterrows():
            ok = upsert_person(row, mapping)
            if ok:
                inserted += 1
            else:
                skipped += 1

        if dry_run:
            logging.info('Dry run - rolling back')
            db.session.rollback()
        else:
            db.session.commit()

    logging.info('Done. inserted/updated=%d skipped=%d', inserted, skipped)


def slugify(text: str) -> str:
    text = text or ''
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:40]


def upsert_faculty_for_project(row, mapping):
    faculty_name = None
    if mapping.get('faculty_name'):
        faculty_name = row.get(mapping['faculty_name'])
    if pd.isna(faculty_name) or not str(faculty_name).strip():
        return None
    faculty_name = str(faculty_name).strip()

    email_base = slugify(faculty_name)
    email = f"{email_base}@imported.local"
    person = Person.query.filter_by(email=email).first()
    if person is None:
        person = Person(
            name=faculty_name,
            email=email,
            password='imported',
            type='Faculty',
            is_approved=True,
        )
        person.set_password('imported123')
        db.session.add(person)
        db.session.flush()

    return person.person_id


def upsert_project(row, mapping):
    title = None
    if mapping.get('project_title'):
        title = row.get(mapping['project_title'])
    if pd.isna(title) or not str(title).strip():
        # fallback to product description as title
        if mapping.get('project_description'):
            title = row.get(mapping['project_description'])
    if pd.isna(title) or not str(title).strip():
        return False
    title = str(title).strip()

    faculty_id = upsert_faculty_for_project(row, mapping)
    project = ResearchProject(project_title=title, faculty_id=faculty_id)

    if mapping.get('project_description'):
        desc = row.get(mapping['project_description'])
        if not pd.isna(desc):
            project.project_description = str(desc)
    if mapping.get('domain'):
        dom = row.get(mapping['domain'])
        if not pd.isna(dom):
            project.domain = str(dom)
    if mapping.get('project_status'):
        status = row.get(mapping['project_status'])
        if not pd.isna(status):
            project.project_status = str(status)

    db.session.add(project)
    return True


def find_existing_project(row, mapping):
    title = None
    if mapping.get('project_title'):
        title = row.get(mapping['project_title'])
    if pd.isna(title) or not str(title).strip():
        if mapping.get('project_description'):
            title = row.get(mapping['project_description'])
    if pd.isna(title) or not str(title).strip():
        return None
    title = str(title).strip().lower()

    with app.app_context():
        candidates = ResearchProject.query.filter(
            func.lower(ResearchProject.project_title) == title,
            (ResearchProject.faculty_id == None) | (ResearchProject.faculty_id == 0)
        ).all()

        if len(candidates) == 1:
            return candidates[0]

        if len(candidates) > 1 and mapping.get('project_description'):
            desc = row.get(mapping['project_description'])
            if not pd.isna(desc) and str(desc).strip():
                desc = str(desc).strip().lower()
                for project in candidates:
                    if project.project_description and desc in project.project_description.lower():
                        return project
        return candidates[0] if candidates else None


def patch_existing_projects(filepath, sheet_name=None, dry_run=False):
    logging.info('Patching existing projects using Excel: %s (sheet=%s)', filepath, sheet_name)
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    mapping = build_project_mapping(df)
    logging.info('Auto-detected project columns: %s', mapping)

    updated = 0
    skipped = 0
    with app.app_context():
        for _, row in df.iterrows():
            project = find_existing_project(row, mapping)
            if not project:
                skipped += 1
                continue

            if project.faculty_id:
                skipped += 1
                continue

            faculty_id = upsert_faculty_for_project(row, mapping)
            if faculty_id:
                project.faculty_id = faculty_id
                db.session.add(project)
                updated += 1
            else:
                skipped += 1

        if dry_run:
            logging.info('Dry run - rolling back')
            db.session.rollback()
        else:
            db.session.commit()

    logging.info('Done. updated=%d skipped=%d', updated, skipped)


def main():
    parser = argparse.ArgumentParser(description='Import Excel into portal DB')
    parser.add_argument('file', help='Path to Excel file')
    parser.add_argument('--sheet', help='Sheet name or index', default=0)
    parser.add_argument('--dry-run', action='store_true', help='Do not commit changes')
    parser.add_argument('--patch-existing', action='store_true', help='Patch existing projects instead of importing new ones')

    args = parser.parse_args()
    path = args.file
    if not os.path.exists(path):
        logging.error('File not found: %s', path)
        sys.exit(1)

    if args.patch_existing:
        patch_existing_projects(path, sheet_name=args.sheet, dry_run=args.dry_run)
        return

    # Quick header read to determine if the sheet has email column
    try:
        header_df = pd.read_excel(path, sheet_name=args.sheet, nrows=5)
    except Exception:
        header_df = pd.read_excel(path, sheet_name=args.sheet)

    email_col = find_column(header_df.columns, COMMON_PERSON_COLUMNS['email'])
    if email_col:
        logging.info('Detected email column (%s) — importing people', email_col)
        import_people(path, sheet_name=args.sheet, dry_run=args.dry_run)
    else:
        logging.info('No email column detected — importing as projects')
        import_projects(path, sheet_name=args.sheet, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
