'''客运列车核心抓取'''
from railgo.config import *
from railgo.parser.models.train import TrainModel
from railgo.parser.utils.client_app import *
from railgo.parser.utils.client_web import *
from railgo.parser.parse.station import *
from railgo.parser.utils.datafixer import *
import datetime
import time


def getTrainList():
    '''获取全部车次列表 生成器'''
    _cachedTrainIDs = []
    for x in range(7):
        for key in TRAIN_KIND_KEYWORDS:
            req = get(
                f"https://mobile.12306.cn/weixin/wxcore/queryTrain?ticket_no={key}&depart_date={(datetime.datetime.now() + datetime.timedelta(days=x)).strftime('%Y%m%d')}")
            jr = req.json()
            for car in jr["data"]:
                if car["train_code"] in _cachedTrainIDs:
                    continue
                _cachedTrainIDs.append(car["train_code"])
                inst = TrainModel()
                inst.number = car["ticket_no"]
                inst.code = car["train_code"]
                inst._dataBeginDay = (datetime.datetime.now(
                ) + datetime.timedelta(days=x)).strftime('%Y%m%d')
                yield inst
            time.sleep(0.5)
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
    return inst


def getCarBackup(inst):
    '''交路车型不全的情况下尝试补全'''
    try:
        r = post("https://mobile.12306.cn/wxxcx/openplatform-inner/miniprogram/wifiapps/appFrontEnd/v2/lounge/open-smooth-common/qrCode/getDeptByTrainCode", data={
            "trainCode": inst.number,
            "reqType": "form"
        })
        d = r.json()
        if "data" in d["content"]:
            inst.runner = d["content"]["data"]["deptName"]
            if inst.car == "":
                inst.car = d["content"]["data"]["carInfo"]["trainStyle"]
    except Exception as e:
        LOGGER.exception(e)
    return inst


def getTrainMain(inst):
    '''列车时刻表，担当段和车型'''
    if len(inst.rundays) == 0:
        raise LookupError

    req = post(
        "https://mobile.12306.cn/wxxcx/wechat/main/travelServiceQrcodeTrainInfo", data={
            "trainCode": inst.number,
            "startDay": inst._beginDay
        })
    crj = req.json()

    if crj["data"] == {}:
        return getTrainMainDowngrade(inst)
    elif len(crj["data"]["trainDetail"]) == 0:
        return getTrainMainDowngrade(inst)
    else:
        try:
            reconnectionFlag = False
            inst.numberKind = "" if inst.number[0].isdigit(
            ) else inst.number[0]
            # inst.code = crj["data"]["trainNo"]
            inst.runner = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_corporation_code"]
            inst.carOwner = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_dept_train"]
            inst.car = crj["data"]["trainDetail"]["stopTime"][0]["jiaolu_train_style"]
            if "重联" in inst.car:
                reconnectionFlag = True
                inst.car = inst.car.replace("重联", "")
            elif inst.car == "" or inst.runner == "":
                inst = getCarBackup(inst)

            if inst.runner in BUREAU_KYD_MAP:
                if BUREAU_SHORT_CODE[BUREAU_KYD_MAP[inst.runner]] != inst.bureau:
                    # 进一步修正乱维护的数据
                    inst.bureau = BUREAU_KYD_MAP[inst.runner]
                    inst.bureauName = BUREAU_SHORT_CODE[BUREAU_KYD_MAP[inst.runner]]

            if crj["data"]["trainDetail"]["stopTime"][0]["corporation_code"][0] == "U":
                # 广东城际的信息由广铁代维护 信息方维护的内容不准
                inst.bureau = "U"
                inst.bureauName = "广东城际"
            try:
                inst.car = crj["data"]["trainDetail"]["trainsetTypeInfo"]["trainsetTypeName"]
                if "重联" in inst.car:
                    reconnectionFlag = True
                    inst.car = inst.car.replace("重联", "")
            except:
                pass

            inst.timetable = []
            tctemp = set()
            for x in crj["data"]["trainDetail"]["stopTime"]:
                if " " in x["stationName"]:
                    # 合并车站
                    kyLooplineStationMerge(fix_ky_telecode(
                        x["stationTelecode"]), x["stationName"].replace(" ", ""))

                inst.timetable.append({
                    "trainCode": x["stationTrainCode"],
                    "day": int(x["dayDifference"]),
                    "arrive": x["arriveTime"][:2]+":"+x["arriveTime"][2:],
                    "depart": x["startTime"][:2]+":"+x["startTime"][2:],
                    "stopTime": int(x["stopover_time"]),
                    "station": x["stationName"].replace(" ", ""),
                    "stationTelecode": fix_ky_telecode(x["stationTelecode"]),
                    "runTime": int(x["runningTime"])
                })
                tctemp.add(x["stationTrainCode"])
                try:
                    updateStationBelongInfo(
                        fix_ky_telecode(x["stationTelecode"]), BUREAU_CODE[x["station_corporation_code"].split("#")[0]], x["station_corporation_code"].split("#")[1])
                except:
                    # 暂时忽略无信息的车站段
                    pass
                updatePassTrain(
                    fix_ky_telecode(x["stationTelecode"]), inst
                )
            inst.spend = int(crj["data"]["trainDetail"]
                             ["stopTime"][-1]["runningTime"])
            inst.numberFull = list(sorted(list(tctemp)))

            if "train_style" in crj["data"]["trainDetail"]["stopTime"][0]:
                style = crj["data"]["trainDetail"]["stopTime"][0]["train_style"]
                if style in CAR_STYLE_CODE_MAP:
                    # 特判错误或复杂车型
                    if "CRH380D" in inst.car and style == "CRH380A_556":
                        inst.car = "CRH380D (统型)"
                    elif "CRH380B" in inst.car and style == "CRH380A_556":
                        inst.car = "CRH380B"
                    elif "CRH1E" in inst.car and style == "CRH2E_110":
                        inst.car = "CRH1E-NG"
                    elif "CRH2A" in inst.car and style == "CRH3A_613":
                        inst.car = "CRH2A (统型)"
                    elif "CR200J" in inst.car and "-C" in inst.car and style in CAR_STYLE_CODE_MAP:
                        if inst.car == "" or inst.car == "CR200J-C":
                            req = get("https://mobile.12306.cn/wxxcx/openplatform-inner/miniprogram/wifiapps/appFrontEnd/v2/lounge/open-smooth-common/trainStyleBatch/getCarDetail",
                                      data={
                                          "carCode": "",
                                          "trainCode": inst.number,
                                          "runningDay": inst._beginDay,
                                          "reqType": "form"
                                      })
                            try:
                                inst.car = CAR_STYLE_CODE_MAP[style].replace(
                                    "CR200JC", fix_cr200j_series(req.json()["content"]["data"]["carCode"]))
                            except:
                                inst.car = ""
                        else:
                            inst.car = CAR_STYLE_CODE_MAP[style].replace(
                                "CR200JC", inst.car)
                    elif style == "CRH1_668":
                        req = post("https://mobile.12306.cn/wxxcx/openplatform-inner/miniprogram/wifiapps/appFrontEnd/v2/lounge/open-smooth-common/qrCode/getDeptByTrainCode",
                                   data={
                                       "trainCode": inst.number,
                                       "reqType": "form"
                                   })
                        try:
                            if req.json()["content"]["data"]["carInfo"]["perHourSpeed"] == "200":
                                inst.car = "CRH1A (200km/h,早期型)"
                            else:
                                inst.car = "CRH1A (250km/h,后期型)"
                        except:
                            inst.car = "CRH1A (200km/h,早期型)"
                    elif style == "CRH1A-A_596":
                        req = post("https://mobile.12306.cn/wxxcx/openplatform-inner/miniprogram/wifiapps/appFrontEnd/v2/lounge/open-smooth-common/qrCode/getDeptByTrainCode",
                                   data={
                                       "trainCode": inst.number,
                                       "reqType": "form"
                                   })
                        try:
                            if req.json()["content"]["data"]["carInfo"]["carCapacity"] == "596":
                                inst.car = "CRH1A-A (多一等座前期型)"
                            else:
                                inst.car = "CRH1A-A (多一等座后期型)"
                        except:
                            inst.car = "CRH1A-A (多一等座后期型)"
                    else:
                        inst.car = CAR_STYLE_CODE_MAP[style]

                if reconnectionFlag:
                    inst.car += " 重联"
            if inst.car in CAR_STYLE_NAME_MAP:  # 普速
                inst.car = CAR_STYLE_NAME_MAP[inst.car]
        except Exception as e:
            return getTrainMainDowngrade(inst)
    return inst


def getTrainMainDowngrade(inst):
    '''涉及停靠不上网售票车站车次时 wxxcx查不到 舍弃部分信息分类查询'''
    LOGGER.warning(f"{inst.number} ({inst.code}) 被动降级")
    if len(inst.rundays) == 0:
        raise LookupError

    inst.numberKind = "" if inst.number[0].isdigit() else inst.number[0]

    r = get(
        f"https://mobile.12306.cn/weixin/wxcore/queryByTrainNo?train_no={inst.code}&depart_date={datetime.datetime.strptime(inst._beginDay,'%Y%m%d').strftime('%Y-%m-%d')}")
    d = r.json()
    for x in d["data"]["data"]:
        inst.timetable.append({
            "trainCode": x["station_train_code"],
            "day": int(x["arrive_day_diff"]),
            "arrive": x["arrive_time"],
            "depart": x["start_time"],
            "station": x["station_name"].replace(" ", ""),
            "stationTelecode": x["station_telecode"],
            "stopTime": int(x["stopover_time"].replace("分钟", "") if "分钟" in x["stopover_time"] else 0),
            "runTime": int(x["running_time"].split(":")[0])*60 + int(x["running_time"].split(":")[1])
        })
        updatePassTrain(
            fix_ky_telecode(x["station_telecode"]), inst
        )
    if inst.number.startswith("G"):
        inst.type = "高速"
    elif inst.number.startswith("D") or inst.number.startswith("C"):
        inst.type = "动车"
    elif inst.number.startswith("S"):
        inst.type = "市域"
    else:
        if d["data"]["data"][0]["train_class_name"] in ["高速", "动车"]:
            inst.type = d["data"]["data"][0]["train_class_name"]
        else:
            if d["data"]["data"][0]["service_type"] == "0":
                # 非空
                inst.type = d["data"]["data"][0]["train_class_name"].replace(
                    "快慢", "普慢")
            else:
                inst.type = "新空调" + \
                    d["data"]["data"][0]["train_class_name"].replace(
                        "快慢", "普慢")

    # r = post("https://mobile.12306.cn/wxxcx/wechat/bigScreen/queryTrainBureau", data={
    #    "queryDate": inst._beginDay,
    #    "trainCode": inst.number
    # })
    # d = r.json()
    # inst.bureau = d["data"]["bureau_code"]
    # inst.bureauName = BUREAU_SHORT_CODE.get(inst.bureau, "未知")

    return inst


def getTrainRundays(inst):
    '''获取未来列车运行计划'''
    j = post("https://mobile.12306.cn/wxxcx/wechat/bigScreen/queryTrainDiagram", data={
        "queryDate": inst._dataBeginDay,
        "trainCode": inst.number
    }).json()["data"]

    rundays = []
    inst.rundays = []
    if "running_list" not in j:
        # 不存在车次
        raise LookupError(f"{inst.number} ({inst.code}) 开行日查询回报删图，自动舍弃")
    for x in j["running_list"]:
        if x["flag"] == "1":
            rundays.append(x["date"])

    inst.rundays = rundays
    inst._beginDay = list(filter(lambda date: datetime.datetime.strptime(date, '%Y%m%d') >=
                                 datetime.datetime.now(), inst.rundays))[0]
    if (datetime.datetime.strptime(inst._beginDay, "%Y%m%d") - datetime.datetime.now()).days < 14:
        inst.bureau = j["bureau_code"]
        inst.bureauName = BUREAU_SHORT_CODE.get(inst.bureau, "未知")
    else:
        raise LookupError(f"{inst.number} ({inst.code}) 开行日查询回报14日内无计划，自动舍弃")

    return inst


def getTrainKind(inst):
    '''获取车种（丐版时刻表）'''
    raise DeprecationWarning
    if inst.number.startswith("G"):
        inst.type = "高速"
    elif inst.number.startswith("D") or inst.number.startswith("C"):
        inst.type = "动车"
    elif inst.number.startswith("S"):
        inst.type = "市域"
    else:
        r = get(
            f"https://mobile.12306.cn/weixin/wxcore/queryByTrainNo?train_no={inst.code}&depart_date={datetime.datetime.strptime(inst._beginDay,'%Y%m%d').strftime('%Y-%m-%d')}")
        d = r.json()
        if len(d["data"]["data"]) == 0:
            return inst

        if d["data"]["data"][0]["train_class_name"] in ["高速", "动车"]:
            inst.type = d["data"]["data"][0]["train_class_name"]
        else:
            if d["data"]["data"][0]["service_type"] == "0":
                # 非空
                inst.type = d["data"]["data"][0]["train_class_name"].replace(
                    "快慢", "普慢")
            else:
                inst.type = "新空调" + \
                    d["data"]["data"][0]["train_class_name"].replace(
                        "快慢", "普慢")
    LOGGER.debug(f"车次车种 {inst.number}: 完成")
    return inst


def getStopDistanceAndDiagram(inst):
    '''获取里程及交路'''
    try:
        for si in range(len(inst.timetable)):
            stop = inst.timetable[si]
            t = restore_ky_telecode(stop["stationTelecode"])
            day = (datetime.datetime.strptime(inst._beginDay, "%Y%m%d") +
                   datetime.timedelta(days=stop["day"])).strftime("%Y%m%d")
            if (day+t) not in STATION_MAP_CACHE:
                LOGGER.debug(
                    f"{inst.number} ({inst.code}) 缓存 {day} {t} 站查信息未命中")
                res = {}
                r = post(
                    f"https://mobile.12306.cn/wxxcx/wechat/bigScreen/queryTrainByStation?train_start_date={day}&train_station_code={t}")
                if "data" in r.json():
                    d = r.json()["data"]
                    if len(d) == 0:  # 偶发拿不到数据
                        return getStopDistanceAndDiagram(inst)
                    for x in d:
                        # 处理交路
                        dg_raw = x["jiaolu_train"]
                        if dg_raw != "":
                            dg = []
                            for i in dg_raw.split("#"):
                                s = i.split("|")
                                if s != [""]:
                                    dg.append({
                                        "number": s[0].split("/")[0],
                                        "from": [s[1], s[2]],
                                        "to": [s[3], s[4]]
                                    })
                            for i in dg:
                                STATION_DIAGRAM_CACHE[i["number"]] = dg

                        dtype = x["train_class_name"]
                        if dtype not in ["高速", "动车"]:
                            if x["service_type"] != "0":
                                dtype = "新空调" + dtype
                            dtype = dtype.replace("快慢", "普慢")

                        # 处理距离和详细车种缓存
                        res[x["station_train_code"]] = [
                            int(x["distance"]), x["train_type_name"], dtype]
                STATION_MAP_CACHE[day+t] = res

            inf = []
            for x in inst.numberFull:
                if x in STATION_MAP_CACHE[day+t]:
                    inf = STATION_MAP_CACHE[day+t][x]

            if inf != []:
                stop["distance"] = inf[0]
                if inst.diagramType == "":
                    if inst.number.startswith("S"):
                        inst.diagramType = ""
                    else:
                        inst.diagramType = inf[1]

                if inst.diagram == []:
                    for x in inst.numberFull:
                        if x in STATION_DIAGRAM_CACHE:
                            inst.diagram = STATION_DIAGRAM_CACHE.pop(x)
                            break
                inst.timetable[si] = stop
                if not inst.type:
                    inst.type = inf[2]
    except Exception as e:
        LOGGER.exception(e)
    return inst


def getTrainDistanceCRGT(inst):
    '''国铁吉讯：获取列车运行里程'''
    for x in inst.timetable[1:]:
        if int(x.get("distance", 0)) == 0:
            break
    else:
        return inst

    try:
        r = post("https://tripapi.ccrgt.com/crgt/trip-server-app/wx/train/getTrainInfoNode", json={
            "params": {"trainNumber": inst.number, "date": datetime.datetime.strptime(inst._beginDay, "%Y%m%d").strftime("%Y-%m-%d")},
            "isSign": 0,
            "token": "",
            "cguid": "",
            "sign": ""
        })
        d = r.json()
        ds = d["data"]["trainScheduleList"]
        if d["code"] != 0:
            return inst

        distance_cache = [0]
        for x in range(len(inst.timetable)):
            if x != 0:
                distance_cache.append(ds[x]["miles"] + distance_cache[x-1])
            i = inst.timetable[x]
            if i.get("distance", 0) == 0 and x != 0:
                i["distance"] = distance_cache[x]
            inst.timetable[x] = i
    except:
        LOGGER.warning(f"{inst.number} ({inst.code}) 里程信息不完整")
    return inst


def getSpeed(inst):
    '''里程信息得出后复算速度'''
    for x in range(1, len(inst.timetable)):
        try:
            inst.timetable[x]["speed"] = (float(inst.timetable[x]["distance"]) - float(inst.timetable[x-1]["distance"])) / (
                (inst.timetable[x]["runTime"] - inst.timetable[x-1]["runTime"]) / 60)
        except:
            inst.timetable[x]["speed"] = -1
    return inst
