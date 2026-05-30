# scripts/provision_existing_employees.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db
from database import Employees
from utils.ntfy import provision_ntfy_user

with app.app_context():
    employees = db.session.query(Employees).filter(
        Employees.ntfy_topic.is_(None)
    ).all()

    for emp in employees:
        topic, token = provision_ntfy_user(str(emp.id))
        emp.ntfy_topic = topic
        emp.ntfy_token = token
        print(f"Provisioned: {emp.name}")

    db.session.commit()
    print("Done.")