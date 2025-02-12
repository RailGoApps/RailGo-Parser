'''专门用来修补铁科院各种抽象代码及额外计算'''
from math import radians, sin, cos, sqrt, atan2


def fix_train_id(tid):
    '''修正12306首页搜索提供的车次编码大小写问题'''
    tl = list(tid)
    tl[1] = tl[1].lower()
    return tl.join("")


def summary_train_codes(cs):
    '''MpaaS版时刻表不提供完整车次号，故需自行概括'''
    cs = list(sorted(cs))
    return cs[0][0]+"/".join(x[1:] for x in cs)


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
