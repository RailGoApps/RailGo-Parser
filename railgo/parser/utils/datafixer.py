'''专门用来修补铁科院各种抽象代码及额外计算'''
from math import radians, sin, cos, sqrt, atan2
from pypinyin import pinyin, lazy_pinyin


def fix_train_id(tid):
    '''修正12306首页搜索提供的车次编码大小写问题'''
    tl = list(tid)
    tl[1] = tl[1].lower()
    return tl.join("")


def summary_train_codes(cs):
    '''MpaaS版时刻表不提供完整车次号，故需自行概括'''
    cs = list(sorted(cs))
    return cs[0][0]+"/".join(x[1:] for x in cs)


def searlize_simple_train_codes(cs):
    '''补全复车次 G1201/2 -> G1201/1202'''
    base = cs.split("/")[0]
    l = {base, }
    for x in cs.split("/")[1:]:
        ab = list(base)
        if len(x) == 1:
            ab[-1] = x
        elif len(x) == 2:
            ab[-1] = x[1]
            ab[-2] = x[0]
        elif len(x) == 3:
            ab[-1] = x[2]
            ab[-2] = x[1]
            ab[-3] = x[0]
        elif len(x) == 4:
            ab[-1] = x[3]
            ab[-2] = x[2]
            ab[-3] = x[1]
            ab[-4] = x[0]
        l.add("".join(ab))


def haversine(coords):
    '''计算经纬度集合距离'''
    def atob(lat1, lon1, lat2, lon2):
        R = 6371.0  # 地球半径
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        # 应用Haversine公式
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    distance = 0.0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        distance += atob(lat1, lon1, lat2, lon2)
    return distance


def stationPinyin(text, jianpin):
    '''复原车站拼音并概括三字拼音代码'''
    try:
        r = []
        if len(text) != len(jianpin):
            # 因更名
            r = lazy_pinyin(text, style=0)
        else:
            p = pinyin(text, heteronym=True, style=0)
            for x in range(len(text)):
                if len(p[x]) == 1:
                    # 不考虑多音字问题，避免更名历史车站简码出事
                    r.append(p[x][0])
                else:
                    for i in p[x]:
                        if jianpin[x].lower() == i[0]:
                            r.append(i)
                            break
                    if len(r) != x+1:
                        r.append(p[x][0])
        triple = ""
        if len(text) == 1:
            triple = r[0][:3]
        elif len(text) == 2:
            triple = r[0][0]+r[1][:2]
        elif len(text) == 3:
            triple = r[0][0]+r[1][0]+r[2][0]
        else:
            triple = r[0][0]+r[1][0]+r[-1][0]

        return "".join(r).capitalize(), triple.upper()
    except Exception as e:
        print(e, r, text, jianpin)
        return "".join(r).capitalize(), ""
