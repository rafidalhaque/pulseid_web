from flask import *

app = Flask(__name__)


@app.route("/", methods=["GET"])
def main_page():
    #TODO
    return render_template("index.html")

@app.route("/whitelist", methods=["GET"])
def whitelist():
    
if __name__ == '__main__':
    app.run()
