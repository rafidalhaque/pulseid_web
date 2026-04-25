# main.py
import datetime
import zoneinfo
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
    }

@app.route("/api/attendance", methods=["POST"])
@check_api_key
@limiter.limit("5 per second")
def record_attendance():
    current_time = datetime.now(tz=zoneinfo.ZoneInfo("Asia/Dhaka"))
    if
    return

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
