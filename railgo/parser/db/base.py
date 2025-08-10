from abc import ABC, abstractmethod

class ExporterBase(ABC):
    @abstractmethod
    def clear(self):
        raise NotImplemented
    
    @abstractmethod
    def exportTrainInfo(self, train):
        raise NotImplemented
    
    @abstractmethod
    def exportStationInfo(self, station):
        raise NotImplemented

    @abstractmethod
    def updateStationInfo(self, station, change, ats=False):
        raise NotImplemented

    @abstractmethod
    def getTrain(self, number):
        raise NotImplemented
    
    @abstractmethod
    def getStation(self, name):
        raise NotImplemented

    @abstractmethod
    def trainInfoList(self):
        raise NotImplemented
    
    @abstractmethod
    def stationInfoList(self):
        raise NotImplemented
    
    @abstractmethod
    def export(self):
        raise NotImplemented
    
    @abstractmethod
    def close(self):
        raise NotImplemented