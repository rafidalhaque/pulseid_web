# database.py
import uuid
from datetime import datetime
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UUID

db = SQLAlchemy()

class Employees(db.Model):
    __tablename__ = 'employees'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    id_number = db.Column(db.Integer, nullable=False)
    join_date = db.Column(db.DateTime, nullable=False)
    designation = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())

    attendance = db.relationship('Attendance', backref='employee', lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendance_entries'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey('employees.id'))
    entry_time = db.Column(db.DateTime, nullable=True)
    exit_time = db.Column(db.DateTime, nullable=True)
    entry_comment = db.Column(db.String(255), nullable=True)
    exit_comment = db.Column(db.String(255), nullable=True)