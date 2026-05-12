# database.py
import uuid
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UUID

from tools import *
from config import *

db = SQLAlchemy()

class Employees(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_employees"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    id_number = db.Column(db.Integer, nullable=False)
    join_date = db.Column(db.Date, nullable=False)
    designation = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    master_secret = db.Column(db.String(255), nullable=True, default=gen_member_master_secret)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    attendance = db.relationship('Attendance', backref='employee', lazy=True)

class Attendance(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_attendance_entries"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id'))
    date = db.Column(db.Date, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=True)
    exit_time = db.Column(db.DateTime, nullable=True)
    entry_comment = db.Column(db.String(255), nullable=True)
    exit_comment = db.Column(db.String(255), nullable=True)

class AttendanceLog(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_attendance_logs"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id'))
    ble_uuid = db.Column(db.String(255), nullable=False)
    recorded_rssi = db.Column(db.Float, nullable=False)
    recorded_timestamp = db.Column(db.DateTime, nullable=False)
    event_type = db.Column(db.String(255), nullable=False, default="IN")