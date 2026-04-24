# main.py
from flask import *
from database import *
from config import *

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = track_modify
db.init_app(app)

@app.route("/", methods=["GET"])
def main_page():
    #TODO
    return render_template("index.html")

@app.route("/whitelist", methods=["GET"])
def whitelist():
    """
    :return: current list of uuid's of members
    """
    return {
        "whitelist": []
    }
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
