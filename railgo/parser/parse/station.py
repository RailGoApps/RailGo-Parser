'''车站核心抓取'''
from railgo.parser.utils.client_web import *
from railgo.parser.models.station import *
from railgo.parser.utils.datafixer import *
from railgo.config import *

import jionlp
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import re
import retry
import itertools

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
            if i.city == None:
                i.city = loc["county"]  # 省直辖县
        else:  # 外国
            i.province = r[9]
            i.city = r[7].replace(i.province, "")
        
        if i.telecode in STATION_95572_TMISM_CACHE:
            i.tmism = STATION_95572_TMISM_CACHE[i.telecode]
        yield i


def getHYFWList():
    '''95306车站列表'''
    req = post("https://ec.95306.cn/api/zd/vizm/queryZmBrief",
               json={"q": "", "limit": 99999}, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"})
    for x in req.json()["data"]:
        i = StationModel()
        i.type = ["货"]
        i.name = re.sub("\(*境\)*", "", x["hzzm"])
        i.telecode = x["dbm"]
        i.tmism = x["tmism"]
        i.bureau = BUREAU_SGCODE[x["ljjc"]]
        i.pinyin, i.pinyinTriple = stationPinyin(i.name, x["pym"])
        yield i

        if isinstance(x["hyzdmc"], str):
            updateStationBelongInfo(i.telecode, i.bureau, x["hyzdmc"])

@retry.retry(tries=5, delay=5)
def getDetailedFreightInfo(inst):
    if "货" not in inst.type:
        return inst

    req = post("https://ec.95306.cn/api/zx/czmpxx/queryByTimism",
               json={"fztmism": str(inst.tmism)}, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0", "Cookies": "SESSION=NjE4M2M0ZWEtMTkzZi00MzY2LWEwNWMtZGM4ZWRiZTQ1NzQ4; __jsluid_s=4eb7daa0ece1d593195f37a77cd3f8d2"})
    try:
        d = req.json()["data"]

        loc = jionlp.parse_location(d["jbxxList"][3]["vlaue"])
        inst.province = loc["province"]
        inst.city = loc["city"]
        if inst.city == None:
            inst.city = loc["county"]  # 省直辖县

        if d["jbxxList"][6]["vlaue"] != "是":
            inst.type.remove("货")
            inst.type.append("通")
        if d["jbxxList"][7]["vlaue"] == "是":
            inst.type.append("快")
        if d["jbxxList"][8]["vlaue"] == "是":
            inst.type.append("行")
        return inst
    except Exception as e:
        LOGGER.exception(e)
        return inst

@retry.retry(tries=5, delay=5)
def getLevel(inst):
    if "货" not in inst.type and "通" not in inst.type:
        return inst
    try:
        buffer = base64.b64encode(AES.new(HYFW_GIS_KEY, AES.MODE_CBC, HYFW_GIS_IV).encrypt(
            pad(f'"{str(inst.tmism)}"'.encode("utf-8"), 16))).decode("utf-8")
        req = post("https://ec.95306.cn/gisServerIPMapServer/OneMapServer/rest/services/HY_CZ_ZTT_JM/Transfer/1/query",
                   headers={
                       "Referer": "https://ec.95306.cn/gis/inputSearchStationHyzy.html",
                       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
                   }, data={
                       "where": f"TMISM='{buffer}'",
                       "OutFields": "*",
                       "f": "json"
                   })
        if req.json()["features"] != []:
            inst.level = req.json()["features"][0]["attributes"]["GRADE"]
            if inst.level == " " or inst.level == None or inst.level == "":
                inst.level = "未知"
        time.sleep(0.05)
        return inst
    except Exception as e:
        LOGGER.exception(e)
        return inst

def getSameCityStations(inst):
    try:
        req = post("https://www.12306.cn/index/otn/index12306/queryScSname", data={
            "station_telecode": restore_ky_telecode(inst.telecode)
        })
        ss = []
        if "data" in req.json():
            for x in req.json()["data"]:
                if x.split(",")[0] != restore_ky_telecode(inst.telecode) and " " not in x.split(",")[1]:
                    ss.append({
                        "stationTelecode": fix_ky_telecode(x.split(",")[0]),
                        "stationName": x.split(",")[1]
                    })
            inst.sameCityStationList = ss
        return inst
    except Exception as e:
        LOGGER.exception(e)
        return inst

def get95572TmismList():
    try:
        req = post("https://www.kyxtpt.com/base/api/v1/travel-train-station/page",
                   headers={
                       "6zubypya": " WECHAT:a8eb392ac90149b294bdf5b1b1180277",
                       "deviceType": "WECHAT"
                   },
                   json={
                       "status": "ENABLE",
                       "pageSize": 999999999,
                       "currentPage": 1,
                       "telegraphCode": ""
                   })
        for x in req.json()["data"]["tableData"]:
            tmism = int(x["trainStationCode"])
            telecode = x["telegraphCode"]
            if tmism >= 90000: # 正确的 TMISM 不使用 9XXXX 号段
                continue
            STATION_95572_TMISM_CACHE[telecode] = tmism
        
        req = post("https://www.kyxtpt.com/base/api/v1/travel-train-station/page",
                   headers={
                       "6zubypya:WECHAT": "a8eb392ac90149b294bdf5b1b1180277",
                       "deviceType": "WECHAT"
                   },
                   json={
                       "status": "DISABLE",
                       "pageSize": 999999999,
                       "currentPage": 1,
                       "telegraphCode": ""
                   })
        for x in req.json()["data"]["tableData"]:
            tmism = int(x["trainStationCode"])
            telecode = x["telegraphCode"]
            if tmism >= 90000: # 正确的 TMISM 不使用 9XXXX 号段
                continue
            STATION_95572_TMISM_CACHE[telecode] = tmism
    except Exception as e:
        LOGGER.exception(e)

def stationTogether():
    for x in itertools.chain(getHYFWList(), getKYFWList()):
        x.telecode = fix_ky_telecode(x.telecode)  # 修复徐州东+雅周bug
        i = EXPORTER.getStation(x.telecode)
        if i != None:
            # 存在同名同码重复车站
            if i["name"] != x.name:
                i["level"] = "未知"
            i["name"] = x.name
            i["pinyin"] = x.pinyin
            i["pinyinTriple"] = x.pinyinTriple
            i["type"].append("客")
            if "通" in i["type"]:
                i["type"].remove("通")
            EXPORTER.exportStationInfo(i)
        else:
            # 先导出一次以免后续查重漏掉
            EXPORTER.exportStationInfo(x)
            yield x
# 对接接口

def updateStationBelongInfo(station, bureau, belong):
    '''从列车时刻表更新车站所属路局及车务段'''
    belong = belong.replace("车站","站")
    if belong in STATION_CWD_SPECIAL_MAP:
        belong = STATION_CWD_SPECIAL_MAP[belong]
    elif not (belong.endswith("段") or belong.endswith("站")) and belong != "":
        belong += "站"
        belong = belong.replace("铁路公司站", "铁路公司").replace("地铁公司站", "铁路公司").replace(
            "公司站", "铁路公司").replace("地铁站", "铁路公司").replace("铁路站", "铁路公司")
    EXPORTER.updateStationInfo(station, {
        "belong": belong,
        "bureau": bureau
    })


def updatePassTrain(station, train):
    s = EXPORTER.getStation(station)
    if "客" not in s["type"]:
        s["type"].append("客")
        if "通" in s["type"]:
            s["type"].remove("通")
    EXPORTER.updateStationInfo(station,{
        "type": s["type"]
    })
    EXPORTER.updateStationInfo(station, {
        "trainList": train.number
    }, ats=True)
    if train.number.startswith("G"):
        EXPORTER.updateStationInfo(station, {
            "type": "高"
        }, ats=True)

def queryTelecodeFromName(name):
    try:
        return EXPORTER.getStationName(name)["telecode"]
    except:
        return ""

def kyLooplineStationMerge(telecode, name):
    EXPORTER.updateStationInfo(queryTelecodeFromName(name), {"telecodeAlias": telecode}, True)