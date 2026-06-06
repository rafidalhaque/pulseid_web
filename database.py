# database.py
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UUID, LargeBinary

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
    ntfy_token = db.Column(db.String(255), nullable=True)
    ntfy_topic = db.Column(db.String(255), nullable=True)
    attendance = db.relationship('Attendance', back_populates='employee', lazy=True)
    attendance_log = db.relationship('AttendanceLog', back_populates='employee', lazy=True)
    ble_credentials = db.relationship('BleCreds', back_populates='employee', cascade='all, delete-orphan', passive_deletes=True, lazy=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": str(self.name),
            "email": str(self.email),
            "id_number": str(self.id_number),
            "join_date": str(self.join_date.strftime("%d %B, %Y")),
            "designation": str(self.designation),
            "position": str(self.position),
            "is_admin": self.is_admin,
        }
class Attendance(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_attendance_entries"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id'))
    date = db.Column(db.Date, nullable=False)
    entry_time = db.Column(db.DateTime(timezone=True), nullable=True)
    exit_time = db.Column(db.DateTime(timezone=True), nullable=True)
    entry_comment = db.Column(db.String(255), nullable=True)
    exit_comment = db.Column(db.String(255), nullable=True)
    is_present = db.Column(db.Boolean, nullable=False, default=True)
    employee = db.relationship('Employees', back_populates='attendance')

    def to_dict(self):
        policy = db.session.query(WorkPolicy).filter(
            WorkPolicy.start_date <= self.date,
            WorkPolicy.end_date >= self.date
        ).first()

        late_minutes = None
        early_minutes = None
        overtime_minutes = None

        if policy and self.entry_time:
            entry = self.entry_time.astimezone(ZoneInfo("Asia/Dhaka")).time()
            allowed_start = (datetime.combine(self.date, policy.office_start) + timedelta(
                minutes=policy.late_minutes)).time()
            if entry > allowed_start:
                diff = datetime.combine(self.date, entry) - datetime.combine(self.date, policy.office_start)
                late_minutes = int(diff.total_seconds() / 60)

        if policy and self.exit_time:
            exit_ = self.exit_time.astimezone(ZoneInfo("Asia/Dhaka")).time()
            allowed_end = (
                        datetime.combine(self.date, policy.office_end) - timedelta(minutes=policy.early_minutes)).time()
            if exit_ < allowed_end:
                diff = datetime.combine(self.date, policy.office_end) - datetime.combine(self.date, exit_)
                early_minutes = int(diff.total_seconds() / 60)
            if exit_ > policy.office_end:
                diff = datetime.combine(self.date, exit_) - datetime.combine(self.date, policy.office_end)
                overtime_minutes = int(diff.total_seconds() / 60)
        return {
            "id": str(self.id),
            "employee_id": str(self.employee_id),
            "employee_name": self.employee.name if self.employee else None,
            "date": str(self.date.strftime("%d %B, %Y")),
            "entry_time": self.entry_time.astimezone(ZoneInfo("Asia/Dhaka")).isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.astimezone(ZoneInfo("Asia/Dhaka")).isoformat() if self.exit_time else None,
            "entry_comment": self.entry_comment,
            "exit_comment": self.exit_comment,
            "is_present": self.is_present,
            "late_entry": late_minutes,
            "early_exit": early_minutes,
            "overtime": overtime_minutes
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
            "recorded_rssi": self.recorded_rssi,
            "recorded_timestamp": self.recorded_timestamp.astimezone(ZoneInfo("Asia/Dhaka")).isoformat() if self.recorded_timestamp else None,
            "event_type": str(self.event_type),
        }
class LeaveEntries(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_leave_entries"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id'))
    date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(255), nullable=False)
    leave_cause = db.Column(db.Text, nullable=True)
    is_approved = db.Column(db.String(255), nullable=False, default="Not Approved")

    def to_dict(self):
        return {
            "id": str(self.id),
            "employee_id": str(self.employee_id),
            "date": str(self.date.strftime("%d %B, %Y")),
            "leave_type": str(self.leave_type),
            "leave_cause": str(self.leave_cause),
            "is_approved": str(self.is_approved)
        }

class Holidays(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_holidays"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    holiday_name = db.Column(db.String(255), nullable=False)
    is_national = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "date": str(self.date),
            "end_date": str(self.end_date) if self.end_date else None,
            "holiday_name": str(self.holiday_name),
            "is_national": self.is_national
        }

class WorkPolicy(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_work_policy"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    office_start = db.Column(db.Time, nullable=False)
    office_end = db.Column(db.Time, nullable=False)
    late_minutes = db.Column(db.Integer, nullable=False, default=0)
    early_minutes = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": str(self.id),
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "office_start": str(self.office_start),
            "office_end": str(self.office_end),
            "late_minutes": self.late_minutes,
            "early_minutes": self.early_minutes,
        }

class AuthorizedDevices(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_devices"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_secret_hash = db.Column(LargeBinary, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

class BleCreds(db.Model):
    __tablename__ = f"{table_prefix if table_prefix else ''}_ble_credentials"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f'{Employees.__tablename__}.id', ondelete='CASCADE'), nullable=False)
    ltk = db.Column(LargeBinary, nullable=False)
    irk = db.Column(LargeBinary, nullable=False)
    shared_secret = db.Column(LargeBinary, nullable=False)
    enrolled_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    revoked = db.Column(db.Boolean, nullable=False, default=False)

    employee = db.relationship('Employees', back_populates='ble_credentials')