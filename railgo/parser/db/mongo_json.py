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
            #LOGGER.warning("接收到空数据")
            return
        self.train_collection.update_one(
            {'number': d["number"]},
            {'$set': d},
            upsert=True
        )

    def exportStationInfo(self, station):
        if not isinstance(station, dict):
            d = station.toJson()
        else:
            d = station
        if d == {} or d is None:
            #LOGGER.warning("接收到空数据")
            return
        self.station_collection.update_one(
            {'telecode': d["telecode"]},
            {'$set': d},
            upsert=True
        )
    
    def updateStationInfo(self, station, change, ats=False):
        self.station_collection.update_one(
            {'telecode':station},
            {('$addToSet' if ats else '$set'):change}
        )


    def getTrain(self, number):
        return self.train_collection.find_one({'number': number})

    def getStation(self, telecode):
        return self.station_collection.find_one({'telecode': telecode})

    def trainInfoList(self):
        return list(self.train_collection.find())

    def stationInfoList(self):
        return list(self.station_collection.find())

    def export(self):
        td = self.clearObjectID(self.train_collection.find())
        ts = self.clearObjectID(self.station_collection.find())
        it = {}
        ia = {}
        for x in range(0,len(td)):
            item = td[x]
            for i in item["numberFull"]:
                it[i] = x
        
        for x in range(0,len(ts)):
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

    def close(self):
        self.client.close()
