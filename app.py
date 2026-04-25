# main.py
from functools import wraps

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

@app.route("/", methods=["GET"])
def main_page():
    #TODO
    return render_template("index.html")

@app.route("/api/whitelist", methods=["GET"])
@check_api_key
def whitelist():
    """
    :return: current list of uuid's of members
    """
    users_uuid = db.session.query(Employees.id).all()
    return {
        "whitelist": [str(uid.id) for uid in users_uuid]
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
