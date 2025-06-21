from flask import *

app = Flask("RailGoServer")

@app.route("/app/v0/offlineDatabase")
def offlineDB():
    with open("./manifest.json", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    app.run("0.0.0.0", 8888)