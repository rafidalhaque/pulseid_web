# database.py
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now())
    master_secret = db.Column(db.String(255), nullable=True, default=gen_member_master_secret)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    attendance = db.relationship('Attendance', back_populates='employee', lazy=True)
    attendance_log = db.relationship('AttendanceLog', back_populates='employee', lazy=True)

class Attendance(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_attendance_entries"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id'))
    date = db.Column(db.Date, nullable=False)
    entry_time = db.Column(db.DateTime(timezone=True), nullable=True)
    exit_time = db.Column(db.DateTime(timezone=True), nullable=True)
    entry_comment = db.Column(db.String(255), nullable=True)
    exit_comment = db.Column(db.String(255), nullable=True)
    employee = db.relationship('Employees', back_populates='attendance')

    def to_dict(self):
        return {
            "id": str(self.id),
            "employee_id": str(self.employee_id),
            "employee_name": self.employee.name if self.employee else None,
            "date": str(self.date),
            "entry_time": self.entry_time.astimezone(ZoneInfo("Asia/Dhaka")).isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.astimezone(ZoneInfo("Asia/Dhaka")).isoformat() if self.exit_time else None,
            "entry_comment": self.entry_comment,
            "exit_comment": self.exit_comment,
        }

class AttendanceLog(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_attendance_logs"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id'))
    ble_uuid = db.Column(db.String(255), nullable=False)
    recorded_rssi = db.Column(db.Float, nullable=False)
    recorded_timestamp = db.Column(db.DateTime(timezone=True), nullable=False)
    event_type = db.Column(db.String(255), nullable=False, default="IN")
    employee = db.relationship('Employees', back_populates='attendance_log')

    def to_dict(self):
        return {
            "id": str(self.id),
            "employee_id": str(self.employee_id),
            "employee_name": self.employee.name if self.employee else None,
            "ble_uuid": str(self.ble_uuid),
            "recorded_rssi": str(self.recorded_rssi),
            "recorded_timestamp": str(self.recorded_timestamp.astimezone(ZoneInfo("Asia/Dhaka")).isoformat() if self.recorded_timestamp else None),
            "event_type": str(self.event_type),
        }
class LeaveEntries(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_leave_entries"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id'))
    date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(255), nullable=False)
    leave_cause = db.Column(db.Text, nullable=True)
    approved = db.Column(db.Boolean, nullable=False, default=False)

class Holidays(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_holidays"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = db.Column(db.Date, nullable=False)
    holiday_name = db.Column(db.String(255), nullable=False)
    is_national = db.Column(db.Boolean, nullable=False, default=True)