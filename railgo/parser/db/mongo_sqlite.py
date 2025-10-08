from railgo.parser.db.mongo_json import MongoJsonExporter
import sqlite3
import json

class MongoSQLiteExporter(MongoJsonExporter):
    def clear(self):
        super().clear()
        db = sqlite3.connect(self.export_location)
        cursor = db.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS trains(code TEXT PRIMARY KEY NOT NULL, number TEXT NOT NULL,numberFull TEXT NOT NULL,numberKind TEXT NOT NULL,bureau TEXT,bureauName TEXT,type TEXT,diagramType TEXT,runner TEXT,car TEXT,carOwner TEXT,diagram TEXT,timetable TEXT NOT NULL,spend INT NOT NULL,rundays TEXT NOT NULL,route TEXT,isFuxing INT);")
        cursor.execute("CREATE TABLE IF NOT EXISTS stations(telecode TEXT PRIMARY KEY NOT NULL,pinyin TEXT NOT NULL,pinyinTriple TEXT NOT NULL,tmism TEXT,name TEXT NOT NULL,level TEXT,bureau TEXT,belong TEXT,province TEXT,city TEXT,lines TEXT,type TEXT,trainList TEXT);")
        db.commit()
        cursor.execute("DELETE FROM trains")
        cursor.execute("DELETE FROM stations")
        db.commit()
        db.close()
    def export(self):
        db = sqlite3.connect(self.export_location)
        cursor = db.cursor()
        for d in self.trainInfoList():
            try:
                cursor.execute("INSERT INTO trains (code, number, numberFull, numberKind, bureau, bureauName, type, diagramType, runner, car, carOwner, diagram, timetable, spend, rundays, route, isFuxing) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (d["code"], d["number"], json.dumps(d["numberFull"], indent=None, separators=(",", ":"), ensure_ascii=False), d["numberKind"], d["bureau"], d["bureauName"], d["type"], d["diagramType"], d["runner"], d["car"], d["carOwner"], json.dumps(d["diagram"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["timetable"], indent=None, separators=(",", ":"), ensure_ascii=False), int(d["spend"]), json.dumps(d["rundays"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["route"], indent=None, separators=(",", ":"), ensure_ascii=False), int(d["isTemp"]), int(d["isFuxing"])))
                db.commit()
            except:
                db.rollback()
        for d in self.stationInfoList():
            try:
                cursor.execute("INSERT INTO stations (telecode, pinyin, pinyinTriple, tmism, name, level, bureau, belong, province, city, lines, type, trainList) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (d["telecode"], d["pinyin"], d["pinyinTriple"], d["tmism"], d["name"], d["level"], d["bureau"], d["belong"], d["province"], d["city"], json.dumps(d["lines"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["type"], indent=None, separators=(",", ":"), ensure_ascii=False), json.dumps(d["trainList"], indent=None, separators=(",", ":"), ensure_ascii=False)))
                db.commit()
            except:
                db.rollback()
        db.close()        