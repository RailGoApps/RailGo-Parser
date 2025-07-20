'''车站核心抓取'''
from railgo.parser.utils.client_web import *
from railgo.parser.models.station import *
from railgo.parser.utils.datafixer import stationPinyin
from railgo.config import *


def getKMList():
    raise DeprecationWarning


def getKYFWList():
    '''12306车站汇总'''
    req = get("https://kyfw.12306.cn/otn/resources/js/framework/station_name.js")
    stl = req.text.split("=")[-1].strip("'")
    for x in stl[1:].split("@"):
        r = x.split("|")
        i = StationModel()
        i.type = ["客"]
        i.name = r[1]
        i.pinyin = r[3].capitalize()
        i.pinyinTriple = r[0].upper()
        i.telecode = r[2]
        yield i


def getHYFWList():
    '''95306车站列表'''
    req = post("https://ec.95306.cn/api/yjgl/zd/gxkcx/listStaByPara",
               json={"code": "", "ljdm": ""})
    for x in req.json()["data"]:
        i = StationModel()
        i.type = ["货"]
        i.name = x["czmc"]
        i.telecode = x["czdbm"]
        i.tmism = x["cztmis"]
        # if "境" in x["czmc"]:
        #    i.bureau = "边境口岸"
        # else:
        #    i.bureau = BUREAU_SGCODE[x["ljjc"]]
        i.bureau = BUREAU_SGCODE[x["ljjc"]]
        i.pinyin, i.pinyinTriple = stationPinyin(x["czmc"], x["czpym"])
        yield i


def getKMLineInfo(inst, kycache):
    raise DeprecationWarning


def updateStationBelongInfo(station, bureau, belong):
    '''从列车时刻表更新车站所属路局及车务段'''
    if not (belong.endswith("段") or belong.endswith("站")) and belong != "":
        belong += "站"
    EXPORTER.updateStationInfo(station, {
        "belong": belong,
        "bureau": bureau
    })


def updatePassTrain(station, train):
    EXPORTER.updateStationInfo(station, {
        "trainList": train.number
    }, ats=True)
    if train.number.startswith("G"):
        EXPORTER.updateStationInfo(station, {
            "type": "高"
        }, ats=True)


def stationTogether():
    yield from getHYFWList()
    for x in getKYFWList():
        try:
            i = EXPORTER.getStation(x.name)
            i["type"].append("客")
            EXPORTER.exportStationInfo(i)
        except:
            yield x
