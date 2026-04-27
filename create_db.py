import os
from datetime import date

from flask import Flask

from backend.config import Config
from backend.database.db import db
from backend.database.models import (
    Person,
    ResearchProject,
    ProjectPerson,
    Publication,
    IPR,
    Startup,
    Funder,
    ProjectFunding,
    Competition,
    ProjectCompetition,
    StudentCompetition,
    ProjectApplication,
)


def build_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def get_sqlite_path():
    uri = Config.SQLALCHEMY_DATABASE_URI
    if uri.startswith('sqlite:///'):
        return uri.replace('sqlite:///', '')
    raise RuntimeError('Unsupported DB URI: %s' % uri)


def reset_database(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        print('Dropped existing schema and created new database schema.')


def seed_database(app):
    with app.app_context():
        # Admin
        admin = Person(
            name='Admin',
            email='admin@portal.com',
            type='Admin',
            is_approved=True,
            department='computer engineering',
            bio='System administrator for the portal.',
            phone='9999999999',
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Faculty
        faculty = [
            Person(
                name='Dr. Asha Sen',
                email='asha.sen@ccew.edu',
                type='Faculty',
                department='computer engineering',
                is_approved=True,
                bio='Research on AI and smart agriculture.',
                phone='8888880001',
            ),
            Person(
                name='Dr. Ravi Patil',
                email='ravi.patil@ccew.edu',
                type='Faculty',
                department='entc',
                is_approved=True,
                bio='Embedded systems and smart city solutions.',
                phone='8888880002',
            ),
            Person(
                name='Dr. Neha Malhotra',
                email='neha.malhotra@ccew.edu',
                type='Faculty',
                department='mechanical eng',
                is_approved=False,
                bio='Sustainable product design and prototyping.',
                phone='8888880003',
            ),
        ]
        for faculty_member in faculty:
            faculty_member.set_password('faculty123')
        db.session.add_all(faculty)

        # Students
        students = [
            Person(
                name='Priya Shah',
                email='priya.shah@student.ccew.edu',
                type='Student',
                department='information tech',
                is_approved=True,
                skills='Python, Machine Learning, Data Science',
                bio='Passionate about AI for agriculture.',
                phone='7777770001',
            ),
            Person(
                name='Ananya Joshi',
                email='ananya.joshi@student.ccew.edu',
                type='Student',
                department='information tech',
                is_approved=True,
                skills='React, JavaScript, UI/UX',
                bio='Building responsive web applications.',
                phone='7777770002',
            ),
            Person(
                name='Meera Desai',
                email='meera.desai@student.ccew.edu',
                type='Student',
                department='entc',
                is_approved=True,
                skills='IoT, Embedded Systems, PCB Design',
                bio='Interested in smart sensor systems.',
                phone='7777770003',
            ),
            Person(
                name='Riya Kulkarni',
                email='riya.kulkarni@student.ccew.edu',
                type='Student',
                department='mechanical eng',
                is_approved=True,
                skills='CAD, 3D Printing, Thermodynamics',
                bio='Designing prosthetics and fluid systems.',
                phone='7777770004',
            ),
            Person(
                name='Sneha Patil',
                email='sneha.patil@student.ccew.edu',
                type='Student',
                department='information tech',
                is_approved=False,
                skills='Data Analysis, SQL, Excel',
                bio='Excited to contribute in analytics projects.',
                phone='7777770005',
            ),
            Person(
                name='Kavya Nair',
                email='kavya.nair@student.ccew.edu',
                type='Student',
                department='computer engineering',
                is_approved=True,
                skills='AI, NLP, Python',
                bio='Working on language-driven research.',
                phone='7777770006',
            ),
            Person(
                name='Aarti Singh',
                email='aarti.singh@student.ccew.edu',
                type='Student',
                department='instrumentation',
                is_approved=True,
                skills='Biomedical, Image Processing, Python',
                bio='Combining biology with intelligent tools.',
                phone='7777770007',
            ),
            Person(
                name='Tania Rao',
                email='tania.rao@student.ccew.edu',
                type='Student',
                department='instrumentation',
                is_approved=True,
                skills='UI/UX, Figma, Design Thinking',
                bio='Creating human-centered product experiences.',
                phone='7777770008',
            ),
        ]
        for student in students:
            student.set_password('student123')
        db.session.add_all(students)
        db.session.commit()

        faculty_ids = [f.person_id for f in faculty]
        student_ids = [s.person_id for s in students]

        # Projects across different domains and statuses
        projects = [
            ResearchProject(
                faculty_id=faculty_ids[0],
                project_title='AI-driven Crop Disease Detector',
                project_description='A machine learning platform to spot crop disease from images.',
                domain='Agritech',
                department='computer engineering',
                required_skills='Python, Machine Learning, Computer Vision',
                team_size=5,
                start_date=date(2024, 1, 10),
                end_date=date(2024, 12, 31),
                project_status='Ongoing',
                iic_registration_status='Registered',
                project_level='Departmental',
                program_location='On Campus',
                is_approved=True,
            ),
            ResearchProject(
                faculty_id=faculty_ids[1],
                project_title='Smart Traffic Signal Optimization',
                project_description='Optimize traffic lights based on live sensor data.',
                domain='Smart City',
                department='entc',
                required_skills='IoT, Data Analytics, Embedded Systems',
                team_size=4,
                start_date=date(2024, 5, 1),
                end_date=date(2025, 2, 28),
                project_status='Proposed',
                iic_registration_status='Pending',
                project_level='Institutional',
                program_location='Off Campus',
                is_approved=False,
            ),
            ResearchProject(
                faculty_id=faculty_ids[2],
                project_title='3D Printed Prosthetic Hand',
                project_description='Designing an affordable prosthetic hand using 3D printing.',
                domain='Healthcare',
                department='mechanical eng',
                required_skills='CAD, 3D Printing, Materials Science',
                team_size=6,
                start_date=date(2023, 8, 1),
                end_date=date(2024, 3, 31),
                project_status='Completed',
                iic_registration_status='Registered',
                project_level='National',
                program_location='On Campus',
                is_approved=True,
            ),
            ResearchProject(
                faculty_id=faculty_ids[1],
                project_title='Sustainable Packaging Innovation',
                project_description='Developing eco-friendly packaging from agricultural waste.',
                domain='Sustainability',
                department='entc',
                required_skills='Materials Science, Design Thinking, Prototyping',
                team_size=4,
                start_date=date(2024, 2, 15),
                end_date=date(2024, 11, 30),
                project_status='On Hold',
                iic_registration_status='Registered',
                project_level='Departmental',
                program_location='On Campus',
                is_approved=True,
            ),
            ResearchProject(
                faculty_id=faculty_ids[0],
                project_title='Blockchain-based Credential System',
                project_description='A secure ledger for storing academic credentials.',
                domain='FinTech',
                department='information tech',
                required_skills='Blockchain, Python, Security',
                team_size=5,
                start_date=date(2024, 3, 1),
                end_date=date(2024, 12, 15),
                project_status='Completed',
                iic_registration_status='Registered',
                project_level='International',
                program_location='Off Campus',
                is_approved=True,
            ),
            ResearchProject(
                faculty_id=faculty_ids[0],
                project_title='Renewable Energy Forecasting',
                project_description='Predict renewable energy output using weather data.',
                domain='Energy',
                department='instrumentation',
                required_skills='Data Science, Python, Forecasting',
                team_size=5,
                start_date=date(2024, 4, 1),
                end_date=date(2025, 3, 31),
                project_status='Ongoing',
                iic_registration_status='Registered',
                project_level='Institutional',
                program_location='On Campus',
                is_approved=True,
            ),
            ResearchProject(
                faculty_id=faculty_ids[1],
                project_title='AR-enhanced Learning Platform',
                project_description='An educational augmented reality environment for interactive learning.',
                domain='EdTech',
                department='entc',
                required_skills='AR, UI/UX, Mobile Development',
                team_size=5,
                start_date=date(2024, 8, 1),
                end_date=date(2025, 5, 31),
                project_status='Proposed',
                iic_registration_status='Pending',
                project_level='Departmental',
                program_location='Off Campus',
                is_approved=False,
            ),
            ResearchProject(
                faculty_id=faculty_ids[2],
                project_title='Smart Waste Management System',
                project_description='Automated sorting and collection for campus waste.',
                domain='Environmental',
                department='mechanical eng',
                required_skills='Sensors, Automation, Data Analytics',
                team_size=4,
                start_date=date(2024, 1, 15),
                end_date=date(2024, 9, 30),
                project_status='On Hold',
                iic_registration_status='Registered',
                project_level='National',
                program_location='On Campus',
                is_approved=True,
            ),
        ]
        db.session.add_all(projects)
        db.session.commit()

        project_ids = [project.project_id for project in projects]

        # Project team assignments
        project_people = [
            ProjectPerson(project_id=project_ids[0], person_id=faculty_ids[0], role='Faculty'),
            ProjectPerson(project_id=project_ids[0], person_id=student_ids[0], role='Student'),
            ProjectPerson(project_id=project_ids[0], person_id=student_ids[1], role='Student'),
            ProjectPerson(project_id=project_ids[0], person_id=student_ids[5], role='Student'),

            ProjectPerson(project_id=project_ids[1], person_id=faculty_ids[1], role='Faculty'),
            ProjectPerson(project_id=project_ids[2], person_id=faculty_ids[2], role='Faculty'),
            ProjectPerson(project_id=project_ids[2], person_id=student_ids[3], role='Student'),
            ProjectPerson(project_id=project_ids[2], person_id=student_ids[6], role='Student'),

            ProjectPerson(project_id=project_ids[3], person_id=faculty_ids[1], role='Faculty'),
            ProjectPerson(project_id=project_ids[4], person_id=faculty_ids[0], role='Faculty'),
            ProjectPerson(project_id=project_ids[4], person_id=student_ids[4], role='Student'),
            ProjectPerson(project_id=project_ids[5], person_id=faculty_ids[0], role='Faculty'),
            ProjectPerson(project_id=project_ids[5], person_id=student_ids[2], role='Student'),
            ProjectPerson(project_id=project_ids[6], person_id=faculty_ids[1], role='Faculty'),
            ProjectPerson(project_id=project_ids[6], person_id=student_ids[7], role='Student'),
            ProjectPerson(project_id=project_ids[7], person_id=faculty_ids[2], role='Faculty'),
        ]
        db.session.add_all(project_people)

        # Student applications to projects
        applications = [
            ProjectApplication(
                project_id=project_ids[1],
                student_id=student_ids[2],
                status='Pending',
                student_message='I would like to work on edge device integration.',
            ),
            ProjectApplication(
                project_id=project_ids[4],
                student_id=student_ids[5],
                status='Approved',
                student_message='I have strong interest in blockchain systems.',
                faculty_message='Approved for the next phase.',
            ),
            ProjectApplication(
                project_id=project_ids[7],
                student_id=student_ids[0],
                status='Rejected',
                student_message='Can I join the waste management project?',
                faculty_message='Please complete the prerequisite sensors module first.',
            ),
        ]
        db.session.add_all(applications)
        db.session.commit()

        # Publications
        publications = [
            Publication(
                project_id=project_ids[0],
                title='Crop Disease Severity Classification using Deep Learning',
                publication_type='Journal',
                venue='International Journal of Agritech',
                publication_date=date(2024, 10, 20),
                indexing='Scopus',
                page_number='12-24',
                year_of_publication=2024,
                volume='14',
                doi='10.1000/agritech.2024.001',
                issn_isbn='1234-5678',
                publisher='AgriScience Publishers',
                status='Published',
            ),
            Publication(
                project_id=project_ids[1],
                title='Sensor Fusion for Smart Traffic Management',
                publication_type='Conference',
                venue='Smart City Summit',
                publication_date=date(2024, 7, 15),
                indexing='IEEE',
                page_number='100-108',
                year_of_publication=2024,
                volume='Conference 7',
                doi='10.1109/smartcity.2024.10',
                issn_isbn='8765-4321',
                publisher='CityTech Media',
                status='Accepted',
            ),
            Publication(
                project_id=project_ids[2],
                title='Design and Fabrication of a Low-cost Prosthetic Hand',
                publication_type='Journal',
                venue='Biomedical Engineering Letters',
                publication_date=None,
                indexing='Web of Science',
                page_number='45-58',
                year_of_publication=2024,
                volume='22',
                doi='10.1000/bioeng.2024.002',
                issn_isbn='2345-6789',
                publisher='HealthTech Publishers',
                status='Submitted',
            ),
            Publication(
                project_id=project_ids[3],
                title='Eco-friendly Packaging Solutions from Agricultural Waste',
                publication_type='Conference',
                venue='Sustainability Conclave',
                publication_date=date(2024, 6, 30),
                indexing='Scopus',
                page_number='210-218',
                year_of_publication=2024,
                volume='SUS-2024',
                doi='10.1000/sustain.2024.005',
                issn_isbn='3456-7890',
                publisher='GreenTech Conferences',
                status='Rejected',
            ),
            Publication(
                project_id=project_ids[4],
                title='Blockchain-based Academic Credential Ledger',
                publication_type='Journal',
                venue='Journal of FinTech Innovations',
                publication_date=date(2024, 8, 5),
                indexing='Scopus',
                page_number='33-44',
                year_of_publication=2024,
                volume='9',
                doi='10.1000/fintech.2024.011',
                issn_isbn='4567-8901',
                publisher='FinTech Journal',
                status='Published',
            ),
            Publication(
                project_id=project_ids[5],
                title='Forecasting Renewable Energy Output with Weather Data',
                publication_type='Journal',
                venue='Energy Analytics Journal',
                publication_date=None,
                indexing='IEEE',
                page_number='90-103',
                year_of_publication=2024,
                volume='31',
                doi='10.1109/energy.2024.050',
                issn_isbn='5678-9012',
                publisher='Energy Press',
                status='Submitted',
            ),
            Publication(
                project_id=project_ids[6],
                title='Augmented Reality Interfaces for Immersive Learning',
                publication_type='Conference',
                venue='Education Technology Expo',
                publication_date=date(2024, 11, 3),
                indexing='ACM',
                page_number='58-66',
                year_of_publication=2024,
                volume='ET-2024',
                doi='10.1145/edu.2024.032',
                issn_isbn='6789-0123',
                publisher='EduTech Media',
                status='Accepted',
            ),
            Publication(
                project_id=project_ids[7],
                title='Waste Segregation Analytics for Smart Campuses',
                publication_type='Journal',
                venue='Journal of Environmental Systems',
                publication_date=date(2024, 9, 20),
                indexing='Scopus',
                page_number='113-124',
                year_of_publication=2024,
                volume='18',
                doi='10.1000/envsys.2024.020',
                issn_isbn='7890-1234',
                publisher='EcoPublishers',
                status='Rejected',
            ),
        ]
        db.session.add_all(publications)
        db.session.commit()

        publication_ids = [pub.publication_id for pub in publications]

        iprs = [
            IPR(
                project_id=project_ids[0],
                publication_id=publication_ids[0],
                innovation_title='Crop Disease Analysis System',
                ipr_type='Patent',
                application_number='APP-CROP-001',
                filing_date=date(2024, 4, 10),
                registration_date=date(2024, 7, 1),
                grant_date=date(2024, 11, 5),
                expiry_date=date(2034, 11, 4),
                grant_status='Granted',
                ownership_type='College Owned',
            ),
            IPR(
                project_id=project_ids[1],
                publication_id=publication_ids[1],
                innovation_title='Traffic Signal Control Algorithm',
                ipr_type='Copyright',
                application_number='APP-TRAFFIC-002',
                filing_date=date(2024, 6, 1),
                registration_date=None,
                grant_date=None,
                expiry_date=None,
                grant_status='Pending',
                ownership_type='Joint Ownership',
            ),
            IPR(
                project_id=project_ids[2],
                publication_id=publication_ids[2],
                innovation_title='Adaptive Prosthetic Grip Design',
                ipr_type='Design',
                application_number='APP-PROSTHETIC-003',
                filing_date=date(2024, 2, 20),
                registration_date=None,
                grant_date=None,
                expiry_date=None,
                grant_status='Filed',
                ownership_type='College Owned',
            ),
            IPR(
                project_id=project_ids[3],
                publication_id=publication_ids[3],
                innovation_title='EcoPack Branding Identity',
                ipr_type='Trademark',
                application_number='APP-ECOPACK-004',
                filing_date=date(2024, 5, 13),
                registration_date=None,
                grant_date=None,
                expiry_date=None,
                grant_status='Rejected',
                ownership_type='Faculty Owned',
            ),
            IPR(
                project_id=project_ids[4],
                publication_id=publication_ids[4],
                innovation_title='Academic Credential Ledger',
                ipr_type='Patent',
                application_number='APP-LEDGER-005',
                filing_date=date(2024, 7, 22),
                registration_date=None,
                grant_date=None,
                expiry_date=None,
                grant_status='Pending',
                ownership_type='Joint Ownership',
            ),
            IPR(
                project_id=project_ids[6],
                publication_id=publication_ids[6],
                innovation_title='AR Educational Interface',
                ipr_type='Copyright',
                application_number='APP-ARLEARN-006',
                filing_date=date(2024, 9, 15),
                registration_date=date(2024, 12, 1),
                grant_date=date(2025, 2, 20),
                expiry_date=date(2035, 2, 19),
                grant_status='Granted',
                ownership_type='Faculty Owned',
            ),
            IPR(
                project_id=project_ids[7],
                publication_id=publication_ids[7],
                innovation_title='Campus Waste Sorting Device',
                ipr_type='Patent',
                application_number='APP-WASTE-007',
                filing_date=date(2024, 8, 10),
                registration_date=None,
                grant_date=None,
                expiry_date=None,
                grant_status='Filed',
                ownership_type='College Owned',
            ),
        ]
        db.session.add_all(iprs)

        startups = [
            Startup(
                project_id=project_ids[0],
                startup_name='AgriScan Labs',
                registration_number='REG-AGRI-2024-01',
                revenue_generated=12500.0,
                development_status='Beta',
                fund_amount=50000.0,
            ),
            Startup(
                project_id=project_ids[2],
                startup_name='Prosthetic Solutions',
                registration_number='REG-PROST-2024-02',
                revenue_generated=8200.0,
                development_status='MVP',
                fund_amount=30000.0,
            ),
            Startup(
                project_id=project_ids[4],
                startup_name='CrediChain Tech',
                registration_number='REG-CRED-2024-03',
                revenue_generated=6800.0,
                development_status='Live',
                fund_amount=75000.0,
            ),
            Startup(
                project_id=project_ids[5],
                startup_name='EnergyCast',
                registration_number='REG-ENER-2024-04',
                revenue_generated=0.0,
                development_status='MVP',
                fund_amount=42000.0,
            ),
        ]
        db.session.add_all(startups)

        funders = [
            Funder(
                funding_agency='State Innovation Fund',
                funding_type='GOVT',
            ),
            Funder(
                funding_agency='Tech Research NGO',
                funding_type='NGO',
            ),
            Funder(
                funding_agency='Campus Entrepreneurship Cell',
                funding_type='GOVT',
            ),
        ]
        db.session.add_all(funders)
        db.session.commit()

        funding_entries = [
            ProjectFunding(
                project_id=project_ids[0],
                fund_id=funders[0].fund_id,
                sanctioned_amount=55000.0,
                sanctioned_date=date(2024, 2, 5),
            ),
            ProjectFunding(
                project_id=project_ids[2],
                fund_id=funders[1].fund_id,
                sanctioned_amount=35000.0,
                sanctioned_date=date(2024, 1, 20),
            ),
            ProjectFunding(
                project_id=project_ids[4],
                fund_id=funders[2].fund_id,
                sanctioned_amount=65000.0,
                sanctioned_date=date(2024, 3, 10),
            ),
            ProjectFunding(
                project_id=project_ids[5],
                fund_id=funders[0].fund_id,
                sanctioned_amount=42000.0,
                sanctioned_date=date(2024, 4, 15),
            ),
        ]
        db.session.add_all(funding_entries)

        competitions = [
            Competition(
                name='National Innovation Challenge',
                venue='Pune',
                organized_by='TechFest',
                start_date_of_competition=date(2024, 7, 1),
                end_date_of_competition=date(2024, 7, 3),
            ),
            Competition(
                name='Smart City Hackathon',
                venue='Mumbai',
                organized_by='City Lab',
                start_date_of_competition=date(2024, 8, 12),
                end_date_of_competition=date(2024, 8, 14),
            ),
            Competition(
                name='HealthTech Expo',
                venue='Bangalore',
                organized_by='MedTech Society',
                start_date_of_competition=date(2024, 9, 10),
                end_date_of_competition=date(2024, 9, 12),
            ),
            Competition(
                name='Green Innovation Awards',
                venue='Delhi',
                organized_by='EcoCouncil',
                start_date_of_competition=date(2024, 10, 5),
                end_date_of_competition=date(2024, 10, 7),
            ),
        ]
        db.session.add_all(competitions)
        db.session.commit()

        project_competitions = [
            ProjectCompetition(
                project_id=project_ids[0],
                competition_id=competitions[0].competition_id,
                team_name='AgriVision',
                prize_money_received=15000.0,
            ),
            ProjectCompetition(
                project_id=project_ids[1],
                competition_id=competitions[1].competition_id,
                team_name='SignalSmart',
                prize_money_received=0.0,
            ),
            ProjectCompetition(
                project_id=project_ids[2],
                competition_id=competitions[2].competition_id,
                team_name='ProstheTech',
                prize_money_received=12000.0,
            ),
            ProjectCompetition(
                project_id=project_ids[3],
                competition_id=competitions[3].competition_id,
                team_name='EcoPackers',
                prize_money_received=8000.0,
            ),
        ]
        db.session.add_all(project_competitions)

        student_competitions = [
            StudentCompetition(
                student_id=student_ids[0],
                competition_id=competitions[0].competition_id,
                mentor_id=faculty_ids[0],
                team_name='Green AI',
                prize_money=15000.0,
            ),
            StudentCompetition(
                student_id=student_ids[1],
                competition_id=competitions[1].competition_id,
                mentor_id=faculty_ids[1],
                team_name='Urban Flow',
                prize_money=0.0,
            ),
            StudentCompetition(
                student_id=student_ids[3],
                competition_id=competitions[2].competition_id,
                mentor_id=faculty_ids[2],
                team_name='ProstheInnovate',
                prize_money=12000.0,
            ),
        ]
        db.session.add_all(student_competitions)
        db.session.commit()

        print('Seeded database with sample users, projects, publications, IPRs, startups, funding, competitions and applications.')
        print(f'Users: {Person.query.count()}')
        print(f'Projects: {ResearchProject.query.count()}')
        print(f'Publications: {Publication.query.count()}')
        print(f'IPRs: {IPR.query.count()}')
        print(f'Startups: {Startup.query.count()}')
        print(f'Domains: {len({p.domain for p in ResearchProject.query.all() if p.domain})}')


if __name__ == '__main__':
    application = build_app()
    reset_database(application)
    seed_database(application)


