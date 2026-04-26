# main.py
import datetime, hmac, hashlib, uuid, csv, io
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask import *
from database import db, Employees, Attendance, AttendanceLog
from config import *

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = track_modify
db.init_app(app)
migrate = Migrate(app, db)
def check_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get("Authorization")
        if not key:
            abort(401, "No API key provided")
        if key != api_key:
            abort(401, "Invalid API key")
        return f(*args, **kwargs)
    return decorated_function

def generated_ble_uuid():
    """
    master_secret + member_uuid + date.isoformat
    :return: hashed secret uuid
    """
    member_uuid = db.session.query(Employees.id).all()
    print(member_uuid)
    todays_date = datetime.date.today().isoformat()
    results = []
    for member in member_uuid:
        per_member_secret = db.session.query(Employees.master_secret).filter(Employees.id == member).first()
        print(per_member_secret)
        print(member)
        time_wrapped_uuid = str(member.id) + todays_date
        hashed = hmac.new(per_member_secret.encode(), time_wrapped_uuid.encode(), hashlib.sha256).hexdigest()[:32]
        resulted_uuid = str(uuid.UUID(hashed))
        results.append({
            "member_id": str(member.id),
            "ble_uuid": resulted_uuid
        })
    result = {item["ble_uuid"]:item["member_id"] for item in results}
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

@app.route("/api/whitelist", methods=["GET"])
@check_api_key
@limiter.limit("5 per second")
def whitelist():
    """
    :return: current list of uuid's of members
    """
    users_uuid = db.session.query(Employees.id).all()
    return {
        "whitelist": [str(uid.id) for uid in users_uuid]
    }, 200

@app.route("/api/attendance", methods=["POST"])
@check_api_key
@limiter.limit("5 per second")
def record_attendance():
    ble_uuid = request.json.get("uuid")
    timestamp = request.json.get("timestamp")
    rssi = request.json.get("rssi")
    door = request.json.get("door")

    if not ble_uuid or not timestamp or not rssi or not door:
        return abort(400, "Missing parameters")

    gened_uuids = generated_ble_uuid()

    if ble_uuid not in gened_uuids.keys():
        return abort(400, "BLE UUID mismatch")

    employee_id = gened_uuids[ble_uuid]
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
        db.session.commit()
    elif attendance_status:
        attendance_status.exit_time = timestamp_object
        log_attendance = AttendanceLog(
            employee_id=employee_id,
            ble_uuid=ble_uuid,
            recorded_rssi=rssi,
            recorded_timestamp=timestamp_object,
            event_type="OUT"
        )
        db.session.add(log_attendance)
        db.session.commit()

    return {"success": True}, 201

@app.route("/api/import-employee", methods=["POST"])
@check_api_key
@limiter.limit("1 per second")
def import_employee():
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
    app.run(host="0.0.0.0", port=5000, debug=True)
