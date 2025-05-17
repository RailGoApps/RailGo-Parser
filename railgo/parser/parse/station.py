'''车站核心抓取'''
from railgo.parser.utils.client_web import *
from railgo.parser.models.station import *
from railgo.config import *
import json
import re


def getKMList():
    '''昆铁车站列表'''
    req = get("http://www.kmrail.cn/common/autoComplete/getAllCz.do?q=&limit=999999")
    res = req.json()
    if len(res["data"]) == 0:
        return
    for x in res["data"]:
        inst = StationModel()
        inst.name = x["hzzm"]
        inst.tmism = int(x["tmism"])
        inst.tgcode = x["dbm"]
        inst.pycode = x["pym"]
        inst.bureau = x["ljqc"]
        yield inst


def getKYFWList():
    '''12306车站汇总'''
    req = get("https://kyfw.12306.cn/otn/resources/js/framework/station_name.js")
    stl = req.text.split("=")[-1].strip("'")
    for x in stl[1:].split("@"):
        r = x.split("|")
        i = StationModel()
        i.type = 1
        i.name = r[1]
        i.pycode = r[4].upper()
        i.tgcode = r[2]
        yield i


def getHYFWList():
    '''95306车站列表'''
    req = post("https://ec.95306.cn/api/yjgl/zd/gxkcx/listStaByPara",
               json={"code": "", "ljdm": ""})
    for x in req.json()["data"]:
        i = StationModel()
        i.type = 2
        i.name = x["czmc"]
        i.pycode = x["czpym"]
        i.tgcode = x["czdbm"]
        i.tmism = x["cztmis"]
        #if "境" in x["czmc"]:
        #    i.bureau = "边境口岸"
        #else:
        #    i.bureau = BUREAU_SGCODE[x["ljjc"]]
        i.bureau = BUREAU_SGCODE[x["ljjc"]]
        yield i


def getKMLineInfo(inst, kycache):
    '''昆铁 获得车站管理局和主要线路'''
    req = get("http://www.kmrail.cn/wap/queryBlxz.do",
              data={"tmism": inst.tmism})
    hp = req.text

    ln = re.findall("<li>(.+)</li>",
                    hp)[2].replace("<li>", "").replace("</li>", "")
    cst = re.findall(
        "<td>(.+)</td>", hp)[0].replace("<td>", "").replace("</td>", "")
    br = re.findall("<li>(.+)</li>",
                    hp)[1].replace("<li>", "").replace("</li>", "")

    if cst != "不办理货物发送、到达。":
        if inst.name.endswith("所") and not (inst.name in STATION_XLS_EXCEPT):
            inst.type = 2
        inst.type += 2

    inst.bureau = br
    inst.lines = ln if ln != "null" else "未知"
    return inst


def updateStationBelongInfo(station, bureau, belong):
    '''从列车时刻表更新车站所属路局及车务段'''
    EXPORTER.updateStationInfo(station, {
        "belong": belong,
        "bureau": bureau
    })

def updatePassTrain(station, train):
    EXPORTER.updateStationInfo(station, {
        "trainList": train
    }, ats=True)


def stationTogether():
    yield from getHYFWList()
    for x in getKYFWList():
        try:
            i = EXPORTER.getStation(x.name)
            i["type"] += 1
            EXPORTER.exportStationInfo(i)
        except:
            yield x
