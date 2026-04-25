# main.py
import datetime, hmac, hashlib, uuid
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask import *
from database import *
from config import *

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = track_modify
db.init_app(app)

def check_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get("PASSWORD")
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
    todays_date = datetime.date.today().isoformat()
    results = []
    for member in member_uuid:
        time_wrapped_uuid = str(member.id) + todays_date
        hashed = hmac.new(master_secret.encode(), time_wrapped_uuid.encode(), hashlib.sha256).hexdigest()[:32]
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
    attendance_status = db.session.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.exit_time.is_(None), Attendance.entry_time>=todays_date).first()
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
def import_employee(file):
    with open(file, "r") as f:
        f.read()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
