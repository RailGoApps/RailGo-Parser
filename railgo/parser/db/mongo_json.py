from pymongo import MongoClient
import json

from railgo.parser.db.base import ExporterBase


class MongoJsonExporter(ExporterBase):
    '''利用MongoDB存储导出数据，并导出为JSON文件'''

    def __init__(self, location):
        self.client = MongoClient("127.0.0.1", 27017)
        self.db = self.client["railgo_parser"]
        self.train_collection = self.db['trains']
        self.station_collection = self.db['stations']
        self.export_location = location

    def clear(self):
        '''避免人工导出时误清理'''
        self.train_collection.delete_many({})
        self.station_collection.delete_many({})

    def exportTrainInfo(self, train):
        if not isinstance(train, dict):
            d = train.toJson()
        else:
            d = train
        if d == {} or d is None:
            # LOGGER.warning("接收到空数据")
            return
        d.pop("_id", None)
        self.train_collection.update_one(
            {'number': d["number"]},
            {'$set': d},
            upsert=True
        )

    def exportStationInfo(self, station):
        if station == None:
            return
        if not isinstance(station, dict):
            d = station.toJson()
        else:
            d = station
        if d == {} or d is None:
            # LOGGER.warning("接收到空数据")
            return
        d.pop("_id", None)
        self.station_collection.update_one(
            {'telecode': d["telecode"]},
            {'$set': d},
            upsert=True
        )

    def updateStationInfo(self, station, change, ats=False):
        self.station_collection.update_one(
            {
                '$or': [
                    {'telecode': station},
                    {'telecodeAlias': station}
                ]
            },
            {('$addToSet' if ats else '$set'): change}
        )

    def getTrain(self, number):
        return self.train_collection.find_one({'number': number})

    def getStation(self, telecode):
        return self.station_collection.find_one({
            '$or': [
                {'telecode': telecode},
                {'telecodeAlias': telecode}
            ]
        })

    def removeStation(self, telecode):
        self.station_collection.delete_one({'telecode': telecode})

    def getStationName(self, name):
        return self.station_collection.find_one({'name': name})

    def trainInfoList(self):
        return list(self.train_collection.find())

    def stationInfoList(self):
        return list(self.station_collection.find())

    def export(self):
        td = self.clearObjectID(self.train_collection.find())
        ts = self.clearObjectID(self.station_collection.find())
        it = {}
        ia = {}
        for x in range(0, len(td)):
            item = td[x]
            for i in item["numberFull"]:
                it[i] = x

        for x in range(0, len(ts)):
            item = ts[x]
            ia[item["telecode"]] = x

        with open(self.export_location, 'w', encoding='utf-8') as f:
            json.dump({
                'trains': td,
                'stations': ts,
                '_index_trains': it,
                '_index_stations': ia
            }, f, ensure_ascii=False)

    def clearObjectID(self, iterator):
        l = []
        for x in iterator:
            del x["_id"]
            l.append(x)
        return l

    def _stationFinal(self):
        pipeline = [
            {"$group": {"_id": "$name", "docs": {"$push": "$$ROOT"}}},
            {"$match": {"$expr": {"$gt": [{"$size": "$docs"}, 1]}}}
        ]
        for group in self.station_collection.aggregate(pipeline, allowDiskUse=True):
            docs = group["docs"]

            main = None
            for d in docs:
                tele = d.get("telecode", "")
                typ = d.get("type", [])
                if "客" in typ or not tele.endswith("I"):
                    main = d
                    break
            if main is None:
                main = docs[0]
                others = docs[1:]
            else:
                others = [d for d in docs if d["_id"] != main["_id"]]

            tele_aliases = set(main.get("telecodeAlias", []))
            tmism_aliases = set(main.get("tmismAlias", []))
            merged_type = main.get("type", [])[:]
            merged_trainList = main.get("trainList", [])

            for d in others:
                if d.get("telecode"):
                    tele_aliases.add(d["telecode"])
                tm = d.get("tmism")
                if tm and tm != "未知":
                    tmism_aliases.add(tm)
                for t in d.get("type", []):
                    if t not in merged_type:
                        merged_type.append(t)
                merged_trainList+=d.get("trainList", [])

            update = {}
            new_tele = list(tele_aliases)
            if set(new_tele) != set(main.get("telecodeAlias", [])):
                update["telecodeAlias"] = new_tele
            new_tmism = list(tmism_aliases)
            if set(new_tmism) != set(main.get("tmismAlias", [])):
                update["tmismAlias"] = new_tmism
            if set(merged_type) != set(main.get("type", [])):
                update["type"] = merged_type
            update["trainList"] = merged_trainList

            if update:
                self.station_collection.update_one({"_id": main["_id"]}, {"$set": update})

            if others:
                self.station_collection.delete_many({"_id": {"$in": [d["_id"] for d in others]}})

    def close(self):
        self.client.close()
