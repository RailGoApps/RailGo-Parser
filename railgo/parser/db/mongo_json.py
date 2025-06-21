from pymongo import MongoClient
import json


class MongoJsonExporter(object):
    '''利用MongoDB存储导出数据，并导出为JSON文件'''

    def __init__(self):
        self.client = MongoClient("127.0.0.1", 27017)
        self.db = self.client["railgo_parser"]
        self.train_collection = self.db['trains']
        self.station_collection = self.db['stations']

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
            {'name': d["name"]},
            {'$set': d},
            upsert=True
        )
    
    def updateStationInfo(self, station, change, ats=False):
        self.station_collection.update_one(
            {'name':station},
            {('$addToSet' if ats else '$set'):change}
        )


    def getTrain(self, number):
        return self.train_collection.find_one({'number': number})

    def getStation(self, name):
        return self.station_collection.find_one({'name': name})

    def trainInfoList(self):
        return list(self.train_collection.find())

    def stationInfoList(self):
        return list(self.station_collection.find())

    def exportToJson(self, output_file):
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
        
        with open(output_file, 'w', encoding='utf-8') as f:
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
