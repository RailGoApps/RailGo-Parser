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
        yield i


def getHYFWList():
    '''95306车站列表'''
    req = post("https://ec.95306.cn/api/zd/vizm/queryZmBrief",
               json={"q": "", "limit": 99999}, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"})
    for x in req.json()["data"]:
        i = StationModel()
        i.type = ["货"]
        i.name = x["hzzm"]
        i.telecode = x["dbm"]
        i.tmism = x["tmism"]
        i.bureau = BUREAU_SGCODE[x["ljjc"]]
        i.pinyin, i.pinyinTriple = stationPinyin(x["hzzm"], x["pym"])
        if isinstance(x["hyzdmc"], str):
            if x["hyzdmc"].endswith("站") or x["hyzdmc"].endswith("车务段"):
                i.belong = re.sub(
                    "中国铁路.+公司", "", x["hyzdmc"]).replace("车站", "站")
        yield i


def getDetailedFreightInfo(inst):
    if "货" not in inst.type:
        LOGGER.debug(f"车站办理范围 {inst.name}: 客")
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
        inst.level = req.json()["features"][0]["attributes"]["GRADE"]
        if inst.level == " " or inst.level == None or inst.level == "":
            inst.level = "未知"
        LOGGER.debug(f"车站等级 {inst.name} : {inst.level}")
        time.sleep(0.05)
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
            if i["name"] != x.name:
                i["level"] = "未知"
            i["name"] = x.name
            i["pinyin"] = x.pinyin
            i["pinyinTriple"] = x.pinyinTriple
            i["type"].append("客")
            if "通" in i["type"]:
                i["type"].remove("通")
            EXPORTER.exportStationInfo(i)
        except:
            yield x
