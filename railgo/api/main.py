from flask import *
import requests
import time

app = Flask(__name__)


@app.route("/app/v0/offlineDatabase")
def offlineDB():
    with open("./manifest.json", "r", encoding="utf-8") as f:
        return f.read()


@app.route("/app/v0/data/bigScreen")
def bigScreen():
    try:
        if request.values.get("state", "") == "departure":
            r = requests.post("https://tripapi.ccrgt.com/crgt/trip-server-app/screen/getStationScreenByStationCode", json={
                "params": {
                    "stationCode": request.values.get("station", ""),
                    "type": "D"
                },
                "isSign": 0
            })
            return jsonify({
                "error": "",
                "data": [{
                    "train": x["trainCode"],
                    "from": x["startStation"],
                    "to": x["endStation"],
                    "time": time.strftime("%H:%M", time.localtime(x["startDepartTime"])),
                    "status": {
                        5: "候车",
                        3: "检票",
                        2: "候车",  # 暂时搞不清有什么区别
                        1: "候车",
                    }.get(x["status"], x["status"]),
                    "delay": x["delay"],
                    "port": x["wicket"]
                } for x in r.json()["data"]["list"]]
            })
        elif request.values.get("state", "") == "arrival":
            r = requests.post("https://tripapi.ccrgt.com/crgt/trip-server-app/screen/getStationScreenByStationCode", json={
                "params": {
                    "stationCode": request.values.get("station", ""),
                    "type": "A"
                },
                "isSign": 0
            })
            return jsonify({
                "error": "",
                "data": [{
                    "train": x["trainCode"],
                    "from": x["startStation"],
                    "to": x["endStation"],
                    "time": time.strftime("%H:%M", time.localtime(x["startDepartTime"])),
                    "status": {
                        4: "正点",
                        5: "晚点"
                    }.get(x["status"], x["status"]),
                    "delay": x["delay"],
                    "port": x["wicket"]
                } for x in r.json()["data"]["list"]]
            })
        else:
            return jsonify({
                "error": "Unknown Bigscreen type",
                "data": []
            })
    except:
        return jsonify({
            "error": "Service error, please check telecode",
            "data": []
        })


if __name__ == "__main__":
    app.run("0.0.0.0", 8888, debug=True)
