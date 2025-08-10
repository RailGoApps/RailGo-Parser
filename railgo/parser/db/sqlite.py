import sqlite3
import json
import threading
from railgo.parser.db.base import ExporterBase
from railgo.parser.models.station import StationModel
from railgo.parser.models.train import TrainModel


class SQLiteExporter(ExporterBase):
    def __init__(self, location):
        self.client = sqlite3.connect(location, check_same_thread=False)
        self.db = self.client.cursor()

        self.db.execute("CREATE TABLE IF NOT EXISTS trains(code TEXT PRIMARY KEY NOT NULL, number TEXT NOT NULL,numberFull TEXT NOT NULL,numberKind TEXT NOT NULL,bureau TEXT,bureauName TEXT,runner TEXT,car TEXT,carOwner TEXT,diagram TEXT,timetable TEXT NOT NULL,spend INT NOT NULL,rundays TEXT NOT NULL,route TEXT,isTemp INT,isFuxing INT);")
        self.db.execute("CREATE TABLE IF NOT EXISTS stations(telecode TEXT PRIMARY KEY NOT NULL,pinyin TEXT NOT NULL,pinyinTriple TEXT NOT NULL,tmism TEXT,name TEXT NOT NULL,bureau TEXT,belong TEXT,lines TEXT,type TEXT,trainList TEXT);")
        self.client.commit()
        
    def clear(self):
        self.db.execute("DELETE FROM trains;")
        self.db.execute("DELETE FROM stations;")
        self.client.commit()

    def exportTrainInfo(self, train):
        if not isinstance(train, dict):
            d = train.toJson()
        else:
            d = train
        if d == {} or d is None:
            # LOGGER.warning("接收到空数据")
            return
        self.db.execute("INSERT INTO trains (code, number, numberFull, numberKind, bureau, bureauName, runner, car, carOwner, diagram, timetable, spend, rundays, route, isTemp, isFuxing) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (d["code"], d["number"], json.dumps(d["numberFull"], indent=None, separators=(",", ":"), ensure_ascii=False), d["numberKind"], d["bureau"], d["bureauName"], d["runner"], d["car"], d["carOwner"], json.dumps(d["diagram"], indent=None, separators=(",", ":"), ensure_ascii=False)), json.dumps(d["timetable"], indent=None, separators=(",", ":"), ensure_ascii=False), int(d["spend"]), json.dumps(d["rundays"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["route"], indent=None, separators=(",", ":"), ensure_ascii=False), int(d["isTemp"]), int(d["isFuxing"]))
        self.client.commit()

    def exportStationInfo(self, station):
        if not isinstance(station, dict):
            d = station.toJson()
        else:
            d = station
        if d == {} or d is None:
            # LOGGER.warning("接收到空数据")
            return
        self.db.execute("INSERT INTO stations (telecode, pinyin, pinyinTriple, tmism, name, bureau, belong, lines, type, trainList) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (d["telecode"], d["pinyin"], d["pinyinTriple"], d["tmism"], d["name"], d["bureau"], d["belong"], json.dumps(d["lines"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["type"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["trainList"], indent=None, separators=(",", ":"), ensure_ascii=False)))
        self.client.commit()

    def updateStationInfo(self, station, change, ats=False):
        if ats:
            for x in change.keys():
                atsItem = None
                for _ in self.db.execute("SELECT ? FROM stations WHERE name=?", (x, station)):
                    atsItem = json.loads(x[0])
                    break
                atsItem.append(change[x])
                self.db.execute("UPDATE stations set ?=? where name=?", (x, json.dumps(
                    atsItem, indent=None, separators=(",", ":"), ensure_ascii=False), station))
        else:
            for x in change.keys():
                self.db.execute(
                    "UPDATE stations set ?=? where name=?", (x, change[x], station))
        self.client.commit()

    def getTrain(self, number):
        i = self.db.execute("SELECT * FROM trains WHERE number=?", (number))
        ist = TrainModel()
        for x in i:
            for a, b in zip(["code", "number", "numberFull", "numberKind", "bureau", "bureauName", "runner", "car", "carOwner", "diagram", "timetable", "spend", "rundays", "route", "isTemp", "isFuxing"], list(x)):
                if "[" in b or "{" in b:
                    exec(f"ist.{a} = {json.loads(b)}")
                elif b.isdigit():
                    exec(f"ist.{a} = {int(b)}")
                else:
                    exec(f"ist.{a} = {b}")
            break
        return ist

    def getStation(self, name):
        i = self.db.execute("SELECT * FROM stations WHERE name=?", (name))
        ist = StationModel()
        for x in i:
            for a, b in zip(["telecode", "pinyin", "pinyinTriple", "tmism", "name", "bureau", "belong", "lines", "type", "trainList"], list(x)):
                if "[" in b or "{" in b:
                    exec(f"ist.{a} = {json.loads(b)}")
                else:
                    exec(f"ist.{a} = {b}")
            break
        return ist

    def trainInfoList(self, name):
        r = []
        i = self.db.execute("SELECT * FROM trains")
        for x in i:
            ist = TrainModel()
            for a, b in zip(["code", "number", "numberFull", "numberKind", "bureau", "bureauName", "runner", "car", "carOwner", "diagram", "timetable", "spend", "rundays", "route", "isTemp", "isFuxing"], list(x)):
                if "[" in b or "{" in b:
                    exec(f"ist.{a} = {json.loads(b)}")
                elif b.isdigit():
                    exec(f"ist.{a} = {int(b)}")
                else:
                    exec(f"ist.{a} = {b}")
            r.append(ist)
        return r

    def stationInfoList(self):
        r = []
        i = self.db.execute("SELECT * FROM stations")
        for x in i:
            ist = StationModel()
            for a, b in zip(["telecode", "pinyin", "pinyinTriple", "tmism", "name", "bureau", "belong", "lines", "type", "trainList"], list(x)):
                if "[" in b or "{" in b:
                    exec(f"ist.{a} = {json.loads(b)}")
                else:
                    exec(f"ist.{a} = {b}")
            r.append(ist)
        return r

    def export(self):
        pass

    def close(self):
        self.client.close()
