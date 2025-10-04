'''车站核心抓取'''
from railgo.parser.utils.client_web import *
from railgo.parser.models.station import *
from railgo.parser.utils.datafixer import *
from railgo.config import *

import jionlp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

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

        if r[8] == "":
            loc = jionlp.parse_location(r[7])
            i.province = loc["province"]
            i.city = loc["city"]
        else:  # 外国
            i.province = r[9]
            i.city = r[7].replace(i.province, "")
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

def getDetailedFreightInfo(inst):
    if "货" not in inst.type:
        LOGGER.debug(f"车站办理范围 {inst.name}: 客")
        return inst
    
    req = post("https://ec.95306.cn/api/zx/czmpxx/queryByTimism", json={"fztmism":str(inst.tmism)})
    try:
        d = req.json()["data"]

        loc = jionlp.parse_location(d["jbxxList"][3]["vlaue"])
        inst.province = loc["province"]
        inst.city = loc["city"]

        if d["jbxxList"][6]["vlaue"] != "是":
            inst.type.remove("货")
            if "客" not in inst.type:
                inst.type.append("通")
        if d["jbxxList"][7]["vlaue"] == "是":
            inst.type.append("高")
        if d["jbxxList"][8]["vlaue"] == "是":
            inst.type.append("行")
        LOGGER.debug(f"车站办理范围 {inst.name}: {' '.join(inst.type)}")
        LOGGER.debug(f"车站地址 {inst.name}: {inst.province}{inst.city}")
        return inst
    except Exception as e:
        LOGGER.exception(e)
        LOGGER.debug(f"车站附加信息 {inst.name} 获取失败")
        return inst

def getLevel(inst):
    if "货" not in inst.type and "通" not in inst.type:
        return inst
    try:
        buffer = base64.b64encode(AES.new(HYFW_GIS_KEY, AES.MODE_CBC, HYFW_GIS_IV).encrypt(pad(f'"{str(inst.tmism)}"'.encode("utf-8"), 16))).decode("utf-8")
        req = post("https://ec.95306.cn/gisServerIPMapServer/OneMapServer/rest/services/HY_CZ_ZTT_JM/Transfer/1/query",
             headers={
                 "Referer": "https://ec.95306.cn/gis/inputSearchStationHyzy.html"
             },data={
                 "where": f"TMISM='{buffer}'",
                 "OutFields":"*",
                 "f":"json"
             })
        inst.level = req.json()["features"][0]["attributes"]["GRADE"]
        LOGGER.debug(f"车站等级 {inst.name} : {inst.level}")
        return inst
    except Exception as e:
        LOGGER.exception(e)
        LOGGER.debug(f"车站等级 {inst.name} 获取失败")
        return inst
    

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
            x.telecode = fix_ky_telecode(x.telecode)  # 修复徐州东+雅周bug
            i = EXPORTER.getStation(x.telecode)
            i["name"] = x.name
            i["pinyin"] = x.pinyin
            i["pinyinTriple"] = x.pinyinTriple
            i["type"].append("客")
            EXPORTER.exportStationInfo(i)
        except:
            yield x
