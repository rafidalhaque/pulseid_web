# app.py
import datetime, hmac, hashlib, uuid, csv, io, click, secrets
import json
import os
from functools import wraps
from pathlib import Path

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask import *
from database import db, Employees, Attendance, AttendanceLog, Holidays, WorkPolicy, LeaveEntries
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
    all_view = request.args.get("all", "false").lower() == "true"
    logger.debug(f"all_view is {all_view}")
    user_profile_view = request.args.get("uuid")
    if all_view and g.is_admin:
        employee = db.session.query(Employees).all()
        logger.debug(f"employee data fetched {employee}")
        return {"success": True, "employee": [e.to_dict() for e in employee]}, 200
    elif user_profile_view and g.is_admin:
        user_profile_uuid = uuid.UUID(user_profile_view)
        employee = db.session.query(Employees).filter(Employees.id == user_profile_uuid).first()
        logger.debug(f"employee data fetched {employee}")
        history = db.session.query(Attendance).filter(Attendance.employee_id == user_profile_uuid).all()
        logger.debug(f"attendance data fetched {history} for {employee}")
        return {"success": True, "employee": employee.to_dict(), "history": [h.to_dict() for h in history]}, 200
    else:
        employee = db.session.query(Employees).filter(Employees.id == g.employee_id).first()
        logger.debug(f"Employee Data Fetched {employee}")
        return {"success": True, "employee": employee.to_dict()}, 200


@app.route("/api/attendance/present", methods=["GET"])
@check_api_key
@limiter.limit("20 per second")
def currently_present():
    today = datetime.date.today()
    in_office = db.session.query(Attendance).options(joinedload(Attendance.employee)).filter(Attendance.date == today, Attendance.is_present.is_(True)).all()
    return jsonify([a.to_dict() for a in in_office]), 200

@app.route("/api/attendance/left", methods=["GET"])
@check_api_key
@limiter.limit("20 per second")
def left_today():
    today = datetime.date.today()
    not_in_office = db.session.query(Attendance).options(joinedload(Attendance.employee)).filter(Attendance.date == today, Attendance.is_present.is_(False), Attendance.exit_time.isnot(None)).all()
    return jsonify([a.to_dict() for a in not_in_office]), 200

@app.route("/api/attendance/history", methods=["GET"])
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

@app.route("/api/employee/key", methods=["GET"])
@check_api_key
@limiter.limit("1 per second")
def employee_key_route():
    employee_key = db.session.query(Employees.master_secret).filter(Employees.id == g.employee_id).first()
    logger.debug(f"Employee Key Fetched {employee_key}")
    return {"success": True, "master_secret": str(employee_key.master_secret)}, 200

@app.route("/api/employee/add", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def add_employee():
    if not g.is_admin:
        return abort(403)
    name = request.json.get("name")
    email = request.json.get("email")
    id_number = int(request.json.get("id_number"))
    join_date = datetime.date.fromisoformat(request.json.get("join_date"))
    designation = request.json.get("designation")
    password = generate_password_hash(request.json.get("password"))
    position = int(request.json.get("position"))
    is_admin = request.json.get("is_admin", False)

    logger.debug(f"Employee data fetched: {name}, {email}, {id_number}, {join_date}, {designation}, {password}, {position}, {is_admin}")
    if isinstance(is_admin, str):
        is_admin = is_admin.lower() == "true"

    if not all([name, email, id_number, join_date, designation, password, position]):
        logger.debug("Missing Parameters")
        return abort(400, "Missing parameters")

    employee_add = Employees(
        name=name,
        email=email,
        id_number=id_number,
        join_date=join_date,
        designation=designation,
        password=password,
        position=position,
        is_admin=is_admin
    )
    db.session.add(employee_add)
    logger.debug(f"Employee Added Successfully {employee_add}")
    db.session.commit()

    return {"success": True, "id": str(employee_add.id)}, 200

@app.route("/api/employee/edit", methods=["PATCH"])
@check_api_key
@limiter.limit("1 per second")
def edit_employee():
    if not g.is_admin:
        return abort(403)
    name = request.json.get("name") if request.json.get("name") else None
    email = request.json.get("email") if request.json.get("email") else None
    id_number = int(request.json.get("id_number")) if request.json.get("id_number") else None
    join_date = datetime.date.fromisoformat(request.json.get("join_date")) if request.json.get("join_date") else None
    designation = request.json.get("designation") if request.json.get("designation") else None
    password = generate_password_hash(request.json.get("password")) if request.json.get("password") else None
    position = int(request.json.get("position")) if request.json.get("position") else None
    is_admin = request.json.get("is_admin", None)
    employee_uuid = request.json.get("uuid")
    logger.debug(f"Employee data fetched: {name}, {email}, {id_number}, {join_date}, {designation}, {password}, {position}, {is_admin}, {employee_uuid}")

    if isinstance(is_admin, str):
        is_admin = is_admin.lower() == "true"

    if not employee_uuid:
        return abort(400, "Missing employee uuid")

    employee = db.session.query(Employees).filter(Employees.id == employee_uuid).first()
    if not employee:
        return abort(404, "Employee not found")

    # only update fields that were sent
    if name: employee.name = name
    if email: employee.email = email
    if id_number: employee.id_number = id_number
    if join_date: employee.join_date = join_date
    if designation: employee.designation = designation
    if position: employee.position = position
    if is_admin is not None: employee.is_admin = is_admin
    logger.debug(f"Employee Edited Successfully")
    db.session.commit()

    return {"success": True, "message": "Successfully Edited"}, 200

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
    if timestamp_object.tzinfo is None:
        bd_tz = datetime.timezone(datetime.timedelta(hours=6))
        timestamp_object = timestamp_object.replace(tzinfo=bd_tz)
    timestamp_object = timestamp_object.astimezone(datetime.timezone.utc)
    todays_date = timestamp_object.date()
    attendance_status = db.session.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.date==todays_date).first()
    if not attendance_status:
        attendance_new = Attendance(
            employee_id=employee_id,
            date=todays_date,
            entry_time=timestamp_object,
            is_present=True
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
    else:
        last_log = db.session.query(AttendanceLog).filter(AttendanceLog.employee_id == employee_id,AttendanceLog.recorded_timestamp >= todays_date).order_by(AttendanceLog.recorded_timestamp.desc()).first()
        last_event = last_log.event_type if last_log else None
        if last_event == "OUT" or last_event is None:
            attendance_status.exit_time = None
            attendance_status.is_present = True
            event_type = "IN"
        else:
            attendance_status.exit_time = timestamp_object
            attendance_status.is_present = False
            event_type = "OUT"
            logger.debug(f"attendance exit time logged in DB: {attendance_status}")
        log_attendance = AttendanceLog(
                employee_id=employee_id,
                ble_uuid=ble_uuid,
                recorded_rssi=rssi,
                recorded_timestamp=timestamp_object,
                event_type=event_type
            )
        db.session.add(log_attendance)
        logger.debug(f"Attendance exit")
        db.session.commit()

    return {"success": True}, 201

@app.route("/api/attendance/leave", methods=["GET"])
@check_api_key
@limiter.limit("1 per second")
def get_leave_reqs():
    if not g.is_admin:
        leave_reqs = db.session.query(LeaveEntries).filter(LeaveEntries.employee_id == g.employee_id).all()
        return {"success": True, "body": [reqs.to_dict() for reqs in leave_reqs]}, 200

    leave_reqs = db.session.query(LeaveEntries).all()

    return {"success": True, "body": [reqs.to_dict() for reqs in leave_reqs]}, 200

@app.route("/api/attendance/leave/add", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def request_leave():
    employee_id = uuid.UUID(g.employee_id)
    requested_date = datetime.date.fromisoformat(request.json.get("date"))
    leave_type = request.json.get("leave_type")
    leave_cause = request.json.get("leave_cause")
    is_approved = "Not Approved"

    if not all([employee_id, requested_date, leave_type, leave_cause]):
        return abort(400, "Missing parameters")

    leave_req = LeaveEntries(
        employee_id=employee_id,
        date=requested_date,
        leave_type=leave_type,
        leave_cause=leave_cause,
        is_approved=is_approved
    )
    db.session.add(leave_req)
    db.session.commit()

    return {"success": True}, 201

@app.route("/api/attendance/leave/manage", methods=["PATCH"])
@check_api_key
@limiter.limit("1 per second")
def handle_leave_reqs():
    if not g.is_admin:
        return abort(403)

    is_approved = request.json.get("is_approved")
    leave_req_id = uuid.UUID(request.json.get("id"))
    leave_req = db.session.query(LeaveEntries).filter(LeaveEntries.id == leave_req_id).first()

    if not leave_req:
        return abort(404, "Leave request not found")

    leave_req.is_approved = is_approved
    db.session.commit()
    return {"success": True}, 201

@app.route("/api/attendance/log", methods=["GET"])
@check_api_key
@limiter.limit("20 per second")
def attendance_log():
    if not g.is_admin:
        return abort(403)
    log = db.session.query(AttendanceLog).options(joinedload(AttendanceLog.employee)).all()

    return {"success": True, "log":[l.to_dict() for l in log]}, 200

@app.route("/api/employee/import", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def import_employee():
    if not g.is_admin:
        return abort(403)
    if "file" not in request.files:
        logger.debug("no 'file' field in request")
        return {"error": "no file field"}, 400
    try:
        file = request.files["file"]
        with io.TextIOWrapper(file.stream, encoding="utf-8-sig") as file_stream:
            csv_file = csv.DictReader(file_stream)
            csv_file.fieldnames = [f.strip().lower() for f in csv_file.fieldnames]
            logger.debug(f"CSV headers detected: {csv_file.fieldnames}")
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
        logger.debug(message)
        return f"{message}", 400
    except Exception as e:
        logger.error(e)
        return f"{e}", 500

@app.route("/api/settings/work_policy", methods=["GET"])
@check_api_key
@limiter.limit("1 per second")
def get_work_policy():
    if not g.is_admin:
        return abort(403)
    work_policy = db.session.query(WorkPolicy).all()

    return {"success": True, "policy": [wp.to_dict() for wp in work_policy]}, 200

@app.route("/api/settings/work_policy/add", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def add_work_policy():
    if not g.is_admin:
        return abort(403)
    start_date = datetime.date.fromisoformat(request.json.get("start_date"))
    end_date = datetime.date.fromisoformat(request.json.get("end_date"))
    office_start = datetime.time.fromisoformat(request.json.get("office_start"))
    office_end = datetime.time.fromisoformat(request.json.get("office_end"))
    late_minutes = int(request.json.get("late_minutes"))
    early_minutes = int(request.json.get("early_minutes"))

    if not all([start_date, end_date, office_start, office_end, late_minutes is not None, early_minutes is not None]):
        return abort(400, "Missing Parameters")

    overlap = db.session.query(WorkPolicy).filter(
        WorkPolicy.start_date <= end_date,
        WorkPolicy.end_date >= start_date
    ).first()
    if overlap:
        return abort(400, "Policy overlaps with existing policy")

    work_policy = WorkPolicy(
        start_date=start_date,
        end_date=end_date,
        office_start=office_start,
        office_end=office_end,
        late_minutes=late_minutes,
        early_minutes=early_minutes
    )
    db.session.add(work_policy)
    db.session.commit()
    return {"success": True}, 201

@app.route("/api/settings/work_policy/edit", methods=["PATCH"])
@check_api_key
@limiter.limit("1 per second")
def edit_work_policy():
    if not g.is_admin:
        return abort(403)

    start_date = datetime.date.fromisoformat(request.json.get("start_date")) if request.json.get("start_date") else None
    end_date = datetime.date.fromisoformat(request.json.get("end_date")) if request.json.get("end_date") else None
    office_start = datetime.time.fromisoformat(request.json.get("office_start")) if request.json.get("office_start") else None
    office_end = datetime.time.fromisoformat(request.json.get("office_end")) if request.json.get("office_end") else None
    late_minutes = int(request.json.get("late_minutes")) if request.json.get("late_minutes") is not None else None
    early_minutes = int(request.json.get("early_minutes")) if request.json.get("early_minutes") is not None else None
    work_policy_id = uuid.UUID(request.json.get("work_policy_id"))

    if not work_policy_id:
        return abort(400, "Invalid ID")

    work_policy = db.session.query(WorkPolicy).filter(WorkPolicy.id == work_policy_id).first()
    if not work_policy:
        return abort(404, "Not found")

    check_start = start_date if start_date is not None else work_policy.start_date
    check_end = end_date if end_date is not None else work_policy.end_date

    overlap = db.session.query(WorkPolicy).filter(
        WorkPolicy.id != work_policy_id,
        WorkPolicy.start_date <= check_end,
        WorkPolicy.end_date >= check_start
    ).first()
    if overlap:
        return abort(400, "Policy overlaps with existing policy")

    if start_date: work_policy.start_date = start_date
    if end_date: work_policy.end_date = end_date
    if office_start: work_policy.office_start = office_start
    if office_end: work_policy.office_end = office_end
    if late_minutes is not None: work_policy.late_minutes = late_minutes
    if early_minutes is not None: work_policy.early_minutes = early_minutes

    db.session.commit()

    return {"success": True}, 200

@app.route("/api/settings/holidays", methods=["GET"])
@check_api_key
@limiter.limit("1 per second")
def get_holiday():
    if not g.is_admin:
        return abort(403)
    holiday = db.session.query(Holidays).all()

    return {"success": True, "holidays":[h.to_dict() for h in holiday]}, 200

@app.route("/api/settings/holidays/add", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def add_holiday():
    if not g.is_admin:
        return abort(403)
    holiday_date = datetime.date.fromisoformat(request.json.get("date"))
    holiday_name = request.json.get("name")
    is_national = request.json.get("is_national")

    if isinstance(is_national, str):
        is_national = is_national.lower() == "true"

    if not all([holiday_date, holiday_name, is_national]):
        return abort(400, "Missing Parameters")

    holiday = Holidays(
        date=holiday_date,
        holiday_name=holiday_name,
        is_national=is_national
    )
    db.session.add(holiday)
    db.session.commit()

    return {"success": True}, 200

esp32_pending_command = None

@app.route("/api/admin/esp32/command", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def esp32_command():
    if not g.is_admin:
        return abort(404)
    global esp32_pending_command
    esp32_pending_command = request.json.get("command")
    return {"success": True}, 200

@app.route("/api/iot/esp32", methods=["GET"])
@check_secret_key
@limiter.limit("1 per second")
def get_admin_command():
    global esp32_pending_command
    cmd = esp32_pending_command
    esp32_pending_command = None
    return {"success": True, "cmd": cmd or "none"}, 200

pong = None

@app.route("/api/iot/esp32/ping", methods=["POST"])
@check_secret_key
@limiter.limit("1 per second")
def esp32_ping():
    data = request.json
    global pong
    pong = data
    metrics_logger.info(
        f"esp32_ping uptime_ms={data.get('uptime_ms')} free_heap={data.get('free_heap')} wifi_rssi={data.get('wifi_rssi')} wifi_ip={data.get('wifi_ip')} ntp_time={data.get('ntp_time')}",
        extra={
            "tags": {
                "device": "esp32",
                "door": "main"
            }
        }
    )
    return {"success": True}, 200

@app.route("/api/admin/esp32/ping", methods=["GET"])
@check_api_key
@limiter.limit("20 per second")
def admin_ping():
    if not g.is_admin:
        return abort(404)
    global pong
    if pong is None:
        return {"success": False, "msg": "No ping data"}, 404
    logger.debug(f"Pong data {pong}")
    return {"success": True, "uptime_ms": pong["uptime_ms"], "free_heap": pong["free_heap"], "wifi_ip": pong["wifi_ip"], "wifi_rssi": pong["wifi_rssi"], "ntp_time": pong["ntp_time"]}, 200

@app.route("/api/app/release", methods=["POST"])
@limiter.limit("1 per second")
def upload_releases():
    version_code = request.form.get("version_code")
    version_name = request.form.get("version_name")
    apk_file = request.files.get("apk")
    key = request.headers.get("X-RELEASE-KEY")

    if key != release_key:
        return abort(400, "header mismatch")

    if not all([version_code, version_name, apk_file]):
        return jsonify({"success": False, "msg": "Missing Parameters"}), 400

    version_data = {
        "version_code": int(version_code),
        "version_name": version_name,
        "download_url": f"{cf_public}/pulseid-{version_name}.apk"
    }
    cf_client.r2.buckets.objects.upload(
        bucket_name=cf_bucket_name,
        object_key=f"pulseid-{version_name}.apk",
        account_id=cf_ac_id,
        body=apk_file.read()
    )
    static_dir=os.path.join(app.root_path, "static")
    os.makedirs(static_dir, exist_ok=True)
    with open(os.path.join(static_dir, "version.json"), "w") as f:
        json.dump(version_data, f)

    return jsonify({"success": True}), 200

@app.route("/api/app/version", methods=["GET"])
@check_api_key
@limiter.limit("10 per second")
def check_update():
    with open(os.path.join(app.root_path, "static", "version.json"), "r") as f:
        version_json = json.loads(f.read())
        return jsonify(version_json), 200

@app.cli.command("create-service-account")
def create_service_account():
    name = "PulseID"
    email = "service@pulse.id"
    designation = "Service Account"
    raw_passwd = secrets.token_urlsafe(16)

    account = Employees(
        name=name,
        email=email,
        id_number=0,
        join_date=datetime.date.today(),
        designation=designation,
        password=generate_password_hash(raw_passwd),
        position=0,
        is_admin=True
    )
    db.session.add(account)
    db.session.commit()
    click.echo("Service Account created")
    click.echo(f"Account ID: {account.id}")
    click.echo(f"Password: {raw_passwd}")
    click.echo("Save Account ID and Password Now in a secure place. Shown once only.")

@app.route("/test-loki")
def test_loki():
    logger.error("🔥 LOKI TEST DIRECT FIRE")
    return {"ok": True}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
