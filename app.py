# app.py
import datetime, hmac, hashlib, uuid, csv, io
from functools import wraps
from pathlib import Path

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask import *
from database import db, Employees, Attendance, AttendanceLog
from config import *
from auth import *
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = track_modify
db.init_app(app)
migrate = Migrate(app, db)

def generated_ble_uuid():
    """
    master_secret + member_uuid + date.isoformat
    :return: hashed secret uuid
    """
    employees_uuid = db.session.query(Employees.id, Employees.master_secret).all()
    todays_date = datetime.date.today().isoformat()
    results = []
    for emp in employees_uuid:
        time_wrapped_uuid = str(emp.id) + todays_date
        hashed = hmac.new(emp.master_secret.encode(), time_wrapped_uuid.encode(), hashlib.sha256).hexdigest()[:32]
        results.append({
            "emp_id": str(emp.id),
            "ble_uuid": str(uuid.UUID(hashed))
        })
    result = {item["ble_uuid"]:item["emp_id"] for item in results}
    logger.debug(result)
    return result

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per second"],
    storage_uri="memory://",
)
@app.route("/", methods=["GET"])
def main_page():
    #TODO
    return render_template("index.html")

@app.route("/api/login", methods=["POST", "GET"])
@limiter.limit("5 per second")
def login_route():
    emp_id = request.json.get("uuid")
    emp_pass = request.json.get("password")
    logger.debug(f"employee id {emp_id} and password {emp_pass} received from request")
    employee = db.session.query(Employees).filter(Employees.id == str(emp_id)).first()
    logger.debug(f"employee data fetched {employee}")
    if not employee or check_password_hash(employee.password, emp_pass) == False:
        logger.debug(f"credentials for {employee} is not matched")
        return {"success": False, "message": "credentials did not matched"}, 403
    token = generate_token(employee.id, employee.position, employee.is_admin)
    logger.debug(f"token generated for {employee.id}")
    return {"success": True, "token": token}, 200

@app.route("/api/profile", methods=["GET"])
@check_api_key
@limiter.limit("5 per second")
def profile_route():
    employee = db.session.query(Employees).filter(Employees.id == g.employee_id).first()
    logger.debug(f"Employee Data Fetched {employee}")
    result = {
        "id": str(employee.id),
        "name": str(employee.name),
        "email": str(employee.email),
        "id_no": str(employee.id_number),
        "join_date": str(employee.join_date),
        "designation": str(employee.designation),
        "position": str(employee.position),
        "is_admin": str(employee.is_admin),
    }
    return result

@app.route("/api/attendance/present", methods=["GET"])
@check_api_key
@limiter.limit("20 per second")
def currently_present():
    today = datetime.date.today()
    in_office = db.session.query(Attendance).options(joinedload(Attendance.employee)).filter(Attendance.date == today, Attendance.entry_time.isnot(None), Attendance.exit_time.is_(None)).all()
    return jsonify([a.to_dict() for a in in_office]), 200

@app.route("/api/attendance_history", methods=["GET"])
@check_api_key
@limiter.limit("1 per second")
def attendance_history():
    admin_view = request.args.get("all", "false").lower() == "true"
    logger.debug(f"admin_view is {admin_view}")
    if admin_view and g.is_admin:
        records = db.session.query(Attendance).all()
    else:
        records = db.session.query(Attendance).filter(
            Attendance.employee_id == g.employee_id
        ).all()

    return {"success": True, "records": [r.to_dict() for r in records]}, 200

@app.route("/api/employee_key", methods=["GET"])
@check_api_key
@limiter.limit("1 per second")
def employee_key_route():
    employee_key = db.session.query(Employees.master_secret).filter(Employees.id == g.employee_id).first()
    logger.debug(f"Employee Key Fetched {employee_key}")
    return {"success": True, "master_secret": str(employee_key.master_secret)}, 200

@app.route("/api/whitelist", methods=["GET"])
@check_secret_key
@limiter.limit("5 per second")
def whitelist():
    """
    :return: current list of uuid's of employees
    """
    employees_secret = db.session.query(Employees.id, Employees.master_secret).all()
    logger.debug(f"Employee ID and Master Secret fetched {employees_secret}")
    return {
        "whitelist": [{"employee_id": str(emp.id), "employee_key": emp.master_secret}
                      for emp in employees_secret]
    }, 200

@app.route("/api/attendance", methods=["POST"])
@check_secret_key
@limiter.limit("5 per second")
def record_attendance():
    ble_uuid = request.json.get("uuid")
    timestamp = request.json.get("timestamp")
    rssi = request.json.get("rssi")
    door = request.json.get("door")
    logger.debug(f"ble uuid {ble_uuid if ble_uuid else 'none'}, timestamp {timestamp if timestamp else 'none'}, rssi {rssi if rssi else 'none'}, door {door if door else 'none'} fetched from request")
    if not ble_uuid or not timestamp or not rssi or not door:
        logger.debug("parameter missing")
        return abort(400, "Missing parameters")

    gened_uuids = generated_ble_uuid()
    if ble_uuid not in gened_uuids.keys():
        logger.debug(f"BLE UUID mismatch with {ble_uuid} and {gened_uuids.keys()}")
        return abort(400, "BLE UUID mismatch")

    employee_id = gened_uuids[ble_uuid]
    logger.debug(f"{employee_id} mapped with ble_uuid")
    timestamp_object = datetime.datetime.fromisoformat(timestamp)
    todays_date = timestamp_object.date()
    attendance_status = db.session.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.exit_time.is_(None), Attendance.date>=todays_date).first()
    if not attendance_status:
        attendance_new = Attendance(
            employee_id=employee_id,
            date=todays_date,
            entry_time=timestamp_object
        )
        db.session.add(attendance_new)
        log_attendance = AttendanceLog(
            employee_id=employee_id,
            ble_uuid=ble_uuid,
            recorded_rssi=rssi,
            recorded_timestamp=timestamp_object,
            event_type="IN"
        )
        db.session.add(log_attendance)
        logger.debug(f"New Attendance Saved in DB: {attendance_new} and {log_attendance}")
        db.session.commit()
    elif attendance_status:
        attendance_status.exit_time = timestamp_object
        logger.debug(f"attendance exit time logged in DB: {attendance_status}")
        log_attendance = AttendanceLog(
            employee_id=employee_id,
            ble_uuid=ble_uuid,
            recorded_rssi=rssi,
            recorded_timestamp=timestamp_object,
            event_type="OUT"
        )
        db.session.add(log_attendance)
        logger.debug(f"Attendance exit")
        db.session.commit()

    return {"success": True}, 201

@app.route("/api/import-employee", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def import_employee():
    if not g.is_admin:
        return abort(403)
    try:
        file = request.files["file"]
        with io.TextIOWrapper(file.stream, encoding="utf-8-sig") as file_stream:
            csv_file = csv.DictReader(file_stream)

            employees = []
            for row in csv_file:
                name = row["name"].strip()
                email = row["email"].strip()
                id_number = int(row["id_number"].strip())
                join_date = datetime.date.fromisoformat(row["join_date"].strip())
                designation = row["designation"].strip()
                password = generate_password_hash(row["password"].strip())
                position = int(row["position"].strip())

                upload_employees = Employees(
                    name=name,
                    email=email,
                    id_number=id_number,
                    join_date=join_date,
                    designation=designation,
                    password=password,
                    position=position
                )
                employees.append(upload_employees)
            db.session.add_all(employees)
            db.session.commit()

        return {"success": True}, 201

    except KeyError:
        message = "Use this format for your csv: name, email, id_number, join_date, designation, password, position"
        return f"{message}", 400


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
