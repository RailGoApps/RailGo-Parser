'''客运列车核心抓取'''
from railgo.config import *
from railgo.parser.models.train import TrainModel
from railgo.parser.utils.client_app import *
from railgo.parser.utils.client_web import *
from railgo.parser.parse.station import *
from railgo.parser.utils.datafixer import *
import requests
import datetime
import time
import json


def getTrainList():
    '''获取全部车次列表 生成器'''
    ts = time.time()
    for key in TRAIN_KIND_KEYWORDS:
        req = get(
            f"https://mobile.12306.cn/weixin/wxcore/queryTrain?ticket_no={key}&depart_date={datetime.datetime.now().strftime('%Y%m%d')}")
        jr = req.json()
        for car in jr["data"]:
            inst = TrainModel()
            inst.number = car["ticket_no"]
            inst.code = car["train_code"]
            yield inst
            LOGGER.debug(f"车次列表提交 {car['ticket_no']}")
        time.sleep(1)


def getTrainMap(inst):
    '''获取列车运行的地图坐标点'''
    req = post("https://mobile.12306.cn/wxxcx/wechat/main/getTrainMapLine", data={
        "version": "v2",
        "trainNo": inst.code
    })
    raw = req.json()
    if raw["data"] == {}:
        # 这辆车没有地图路径
        inst.route = []
        return inst

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
        raise LookupError

    req = post(
        "https://mobile.12306.cn/wxxcx/wechat/main/travelServiceQrcodeTrainInfo", data={
            "trainCode": inst.number,
            "startDay": inst.rundays[0]
        })
    crj = req.json()

    if crj["data"] == {}:
        # 只有在WXXCX查不到信息时再跳转APP版查询
        # 减少加解密开支和被炸可能
        return getTrainMainApp(inst)
    elif len(crj["data"]["trainDetail"]) == 0:
        return getTrainMainApp(inst)
    else:
        try:
            inst.numberFull = crj["data"]["trainDetail"]["stationTrainCodeAll"]
            inst.code = crj["data"]["trainNo"]
            inst.runner = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_corporation_code"]
            inst.carowner = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_dept_train"]
            inst.car = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_train_style"]
            inst.bureau = BUREAU_CODE[crj["data"]["trainDetail"]["stopTime"][0]["bureau_code"]]
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
                try:
                    updateStationBelongInfo(
                        x["stationName"], BUREAU_CODE[x["station_corporation_code"].split("#")[0]], x["station_corporation_code"].split("#")[1])
                except:
                    # 暂时忽略无信息的车站段
                    pass
        except Exception as e:
            return getTrainMainApp(inst)

    LOGGER.debug(f"车次主信息 {inst.number}: 完成")
    return inst


def getTrainMainApp(inst):
    '''MpaaS API: getTrainMain备份平替'''
    if len(inst.rundays) == 0:
        # 三折叠，怎么折，都停运
        raise LookupError

    r = postM("trainTimeTable.queryTrainAllInfo",
              {
                  "fromStation": "",
                  "toStation": "",
                               "trainCode": inst.number,
                               "trainType": "",
                               "trainDate": inst.rundays[0]
              }
              )
    crj = json.loads(r["trainData"])

    # inst.numberFull = crj["trainDetail"]["stationTrainCodeAll"]
    # inst.code = crj["trainNo"]
    inst.runner = crj["stopTime"][0]["jiaolu_corporation_code"]
    inst.carowner = crj["stopTime"][0]["jiaolu_dept_train"]
    inst.car = crj["stopTime"][0]["jiaolu_train_style"]
    inst.bureau = BUREAU_CODE[crj["stopTime"][0]["bureau_code"]]
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
    inst.rundays = []
    if "running_list" not in j:
        # 不存在车次
        raise LookupError
    for x in j["running_list"]:
        if x["flag"] == "1" and datetime.datetime.strptime(x["date"], "%Y%m%d") >= datetime.datetime.now():
            if len(rundays) == 0 and (datetime.datetime.strptime(x["date"], "%Y%m%d") - datetime.datetime.now()).days > 14:
                raise LookupError
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

    if len(d["data"]["data"])==0:
        # 图纸车
        raise LookupError

    if d["data"]["data"][0]["train_class_name"] in ["高速", "动车"]:
        if ttl[0]["code"].startswith("S"):
            inst.type = "市域"
        else:
            inst.type = d["data"]["data"][0]["train_class_name"]
    else:
        if d["data"]["data"][0]["service_type"] == "0":
            # 非空
            inst.type = d["data"]["data"][0]["train_class_name"]
        else:
            inst.type = "新空调"+d["data"]["data"][0]["train_class_name"]
    return inst


def getTrainDistanceCRGT(inst):
    '''国铁吉讯：获取列车运行里程'''
    r = post("https://tripapi.ccrgt.com/crgt/trip-server-app/wx/train/getTrainInfoNode", json={
        "params": {"trainNumber": inst.number, "date": datetime.datetime.strptime(inst.rundays[0], "%Y%m%d").strftime("%Y-%m-%d")},
        "isSign": 0,
        "token": "",
        "cguid": "",
        "sign": ""
    })
    d = r.json()
    ds = d["data"]["trainScheduleList"]
    if d["code"] != 0:
        return inst

    for x in range(len(inst.timetable)):
        i = inst.timetable[x]
        if x == 0:
            i["distance"] = ds[x]["miles"]
        else:
            i["distance"] = ds[x]["miles"]+inst.timetable[x-1]["distance"]
        inst.timetable[x] = i

    return inst
