from railgo.config import *
from railgo.parser.utils.client_web import *
from railgo.parser.parse.station import *
import json


def _decodeGeogvResponse(raw):
    if raw[0] == "\"":
        # 解密位移
        b = eval(raw)
        keyLen = ord(b[0])
        key = b[1:keyLen+1]
        res = ""
        for x in range(keyLen+1, len(b)):
            res += chr(ord(b[x]) - ord(key[(x-keyLen-1) % keyLen]))
        return json.loads(res)
    else:
        return json.loads(raw)


def getMapLineDFS(lineId, poolCallback):
    try:
        r = get("http://cnrail.geogv.org/api/feature/" + lineId)
        d = _decodeGeogvResponse(r.text)
        MAP_VISITED_LINES.append(lineId)
        for x in d["data"]["stations"]:
            if x["kid"] not in MAP_VISITED_STATIONS and x["kid"] != None:
                MAP_VISITED_STATIONS.append(x["kid"])
                poolCallback(getMapStation, x["kid"], poolCallback)
            # TODO: 登记整条线路信息
    except:
        pass

def getMapStation(poiId, poolCallback):
    rs = get("http://cnrail.geogv.org/api/poi/" + poiId)
    ds = _decodeGeogvResponse(rs.text)
    mytelecode = queryTelecodeFromName(x["name"])
    if mytelecode == "":
        return
    stnLineInfo = []
    for x in ds["exd"][0]["data"]["connection"]:
        if x["eid"] not in MAP_VISITED_LINES:
            poolCallback(getMapLineDFS, x["eid"], poolCallback)
            lineInf = {
                "name": x["linename"],
                "previous": "",
                "previousTelecode": "",
                "next": "",
                "nextTelecode": "",
            }
            if x["next"][0]["adj"]:
                lineInf["previous"] = x['next'][0]['adj']['name']
                lineInf["previousTelecode"] = queryTelecodeFromName(
                    x['next'][0]['adj']['name'])
            if x["prev"][0]["adj"]:
                lineInf["next"] = x['prev'][0]['adj']['name']
                lineInf["nextTelecode"] = queryTelecodeFromName(
                    x['prev'][0]['adj']['name'])
            stnLineInfo.append(lineInf)
            EXPORTER.updateStationInfo(mytelecode, {
                "lines": stnLineInfo
            })
            LOGGER.info(f"车站线路 {x['name']} 完成")

def getMapBeginLine():
    try:
        r = get("http://cnrail.geogv.org/api/search?keyword=" + MAP_BEGIN_LINE)
        d = _decodeGeogvResponse(r.text)
        return d[0]["query"].replace("rail/", "")
    except:
        raise LookupError
