from railgo.parser.db.mongo_json import MongoJsonExporter
import sqlite3
import json

class MongoSQLiteExporter(MongoJsonExporter):
    def clear(self):
        pass
    def export(self):
        db = sqlite3.connect(self.export_location)
        cursor = db.cursor()
        for d in self.trainInfoList():
            try:
                cursor.execute("INSERT INTO trains (code, number, numberFull, numberKind, bureau, bureauName, runner, car, carOwner, diagram, timetable, spend, rundays, route, isTemp, isFuxing) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (d["code"], d["number"], json.dumps(d["numberFull"], indent=None, separators=(",", ":"), ensure_ascii=False), d["numberKind"], d["bureau"], d["bureauName"], d["runner"], d["car"], d["carOwner"], json.dumps(d["diagram"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["timetable"], indent=None, separators=(",", ":"), ensure_ascii=False), int(d["spend"]), json.dumps(d["rundays"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["route"], indent=None, separators=(",", ":"), ensure_ascii=False), int(d["isTemp"]), int(d["isFuxing"])))
                db.commit()
            except:
                db.rollback()
        for d in self.stationInfoList():
            try:
                cursor.execute("INSERT INTO stations (telecode, pinyin, pinyinTriple, tmism, name, bureau, belong, lines, type, trainList) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (d["telecode"], d["pinyin"], d["pinyinTriple"], d["tmism"], d["name"], d["bureau"], d["belong"], json.dumps(d["lines"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["type"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["trainList"], indent=None, separators=(",", ":"), ensure_ascii=False)))
                db.commit()
            except:
                db.rollback()
        db.close()        