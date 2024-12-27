'''客运列车核心抓取'''
from railgo.config import *
from railgo.parser.models.train import TrainModel
from railgo.parser.utils.appclient import *
from railgo.parser.utils.webclient import *
from railgo.parser.parse.station import *
from railgo.parser.utils.datafixer import *
import requests
import datetime
import time
import json


def getTrainList():
    '''获取全部车次列表 生成器'''
    ts = time.time()
    for td in range(7):  # 前后7天
        for key in TRAIN_KIND_KEYWORDS:
            for tn in range(1, 100):
                req = get(
                    f"https://search.12306.cn/search/v1/train/search?keyword={key+str(tn)}&date={(datetime.datetime.now()+datetime.timedelta(days=td)).strftime('%Y%m%d')}")
                jr = req.json()
                for car in jr["data"]:
                    if car["train_no"] in TRAIN_CODE_UNIQUE_LIST:
                        continue
                    TRAIN_CODE_UNIQUE_LIST.append(car["train_no"])
                    inst = TrainModel()
                    inst.number = car["station_train_code"]
                    inst.code = car["train_no"]
                    yield inst
                    LOGGER.debug(f"车次列表提交 {car['station_train_code']}")
                time.sleep(0.1)


def getTrainMap(inst):
    '''获取列车运行的地图坐标点'''
    req = post("https://mobile.12306.cn/wxxcx/wechat/main/getTrainMapLine", data={
        "version": "v2",
        "trainNo": inst.code
    })
    raw = req.json()
    res = []
    for pk in raw["data"].keys():
        res += raw["data"][pk]["line"]
    inst.route = res
    LOGGER.debug(f"车次地图信息拼接 {inst.number}: 完成")
    return inst


def getTrainMain(inst):
    '''列车时刻表，担当段和车型'''
    if len(inst.rundays) == 0:
        # 三折叠，怎么折，都停运
        return None

    req = post(
        "https://mobile.12306.cn/wxxcx/wechat/main/travelServiceQrcodeTrainInfo", data={
            "trainCode": inst.number,
            "startDay": inst.rundays[0]
        })
    crj = req.json()

    if crj["data"]=={}:
        # 只有在WXXCX查不到信息时再跳转APP版查询
        # 减少加解密开支和被炸可能
        return getTrainMainApp(inst)
    elif len(crj["data"]["trainDetail"])==0:
        return getTrainMainApp(inst)
    else:
        try:
            inst.numberFull = crj["data"]["trainDetail"]["stationTrainCodeAll"]
            inst.code = crj["data"]["trainNo"]
            inst.runner = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_corporation_code"]
            inst.carowner = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_dept_train"]
            inst.car = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_train_style"]
            inst.bureau = crj["data"]["trainDetail"]["stopTime"][0]["bureau_code"]
            if "trainsetTypeInfo" in crj["data"]["trainDetail"].keys():
                inst.car = crj["data"]["trainDetail"]["trainsetTypeInfo"]["trainsetTypeName"]

            inst.timetable = []
            for x in crj["data"]["trainDetail"]["stopTime"]:
                inst.timetable.append({
                    "trainCode": x["stationTrainCode"],
                    "day": int(x["dayDifference"]),
                    "arrive": x["arriveTime"][:2]+":"+x["arriveTime"][2:],
                    "depart": x["startTime"][:2]+":"+x["startTime"][2:],
                    "station": x["stationName"]
                })
                updateStationBelongInfo(
                    x["stationName"], x["station_corporation_code"])
        except:
            return getTrainMainApp(inst)

    LOGGER.debug(f"车次主信息 {inst.number}: 完成")
    return inst


def getTrainMainApp(inst):
    '''MpaaS API: getTrainMain备份平替'''
    if len(inst.rundays) == 0:
        # 三折叠，怎么折，都停运
        return None

    r = postM("trainTimeTable.queryTrainAllInfo",
                           {
                               "fromStation": "",
                               "toStation": "",
                               "trainCode": inst.number,
                               "trainType": "",
                               "trainDate": inst.rundays[0]
                           }
                           )
    crj = r["trainData"]

    #inst.numberFull = crj["trainDetail"]["stationTrainCodeAll"]
    #inst.code = crj["trainNo"]
    inst.runner = crj["stopTime"][0]["jiaolu_corporation_code"]
    inst.carowner = crj["stopTime"][0]["jiaolu_dept_train"]
    inst.car = crj["stopTime"][0]["jiaolu_train_style"]
    inst.bureau = crj["stopTime"][0]["bureau_code"]
    if "trainsetTypeInfo" in crj.keys():
        inst.car = crj["trainsetTypeInfo"]["trainsetTypeName"]
    inst.timetable = []

    tctemp = []
    for x in crj["stopTime"]:
        inst.timetable.append({
            "trainCode": x["dispTrainCode"],
            "day": int(x["dayDifference"]),
            "arrive": x["arriveTime"][:2]+":"+x["arriveTime"][2:],
            "depart": x["startTime"][:2]+":"+x["startTime"][2:],
            "station": x["stationName"]
        })
        tctemp.append(x["dispTrainCode"])
        updateStationBelongInfo(
            x["stationName"], x["station_corporation_code"])
    
    inst.numberFull = summary_train_codes(set(tctemp))
    LOGGER.debug(f"车次主信息 {inst.number}: 完成")
    return inst


def getTrainRundays(inst):
    '''MpaaS API: 获取未来列车运行计划'''
    j = postM("trainTimeTable.queryTrainDiagram",
                           {
                               "queryDate": datetime.date.today().strftime("%Y%m%d"),
                               "trainCode": inst.number
                           })
    rundays = []
    if "running_list" not in j:
        # 备用模式下不存在车次
        return None
    for x in j["running_list"]:
        if x["flag"] == "1" and datetime.datetime.strptime(x["date"], "%Y%m%d") >= datetime.datetime.now():
            rundays.append(x["date"])
    inst.rundays = rundays
    # print(j)
    LOGGER.debug(f"车次开行计划 {inst.number}: 完成")
    return inst


def getTrainKind(inst):
    '''获取车种（丐版时刻表）'''
    r = get(
        f"https://mobile.12306.cn/weixin/wxcore/queryByTrainNo?train_no={inst.code}")
    d = r.json()
    if d["data"]["data"][0]["train_class_name"] in ["高速", "动车"]:
        if ttl[0]["code"].startswith("S"):
            inst.type = "市域"
        else:
            inst.type = d["data"]["data"][0]["train_class_name"]
    else:
        if d["data"]["data"][0]["service_type"] == "0":
            inst.type = d["data"]["data"][0]["train_class_name"]
        else:
            inst.type = "新空调"+d["data"]["data"][0]["train_class_name"]
    return inst
