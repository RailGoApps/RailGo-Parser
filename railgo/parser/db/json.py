from tinydb import TinyDB, Query
from railgo.config import *
import os


class JsonExporter(object):
    '''利用JSON存储导出数据'''

    def __init__(self, path):
        self.db_train = TinyDB(path + "/trains.json")
        self.db_station = TinyDB(path + "/stations.json")
        # self.db_map = TinyDB(os.path.join(path, "map.json"))
        # self.db_emu = TinyDB(os.path.join(path, "emu_presequence.json"))
        # 清除陈年老数据
        self.db_train.truncate()
        self.db_station.truncate()

    def exportTrainInfo(self, train):
        d = train.toJson()
        if d == {} or d is None:
            LOGGER.warning("接收到空数据")
        self.db_train.insert(d)

    def exportStationInfo(self, station):
        d = station.toJson()
        if d == {} or d is None:
            LOGGER.warning("接收到空数据")
        self.db_station.insert(d)

    def getStation(self,name):
        RailgoStation = Query()
        return self.db_station.search(RailgoStation.name == name)[0]

    def updateStationInfo(self, station, name):
        d = station.toJson()
        RailgoStation = Query()
        if d == {} or d is None:
            LOGGER.warning("接收到空数据")
        self.db_station.upsert(d, RailgoStation.name == name)
