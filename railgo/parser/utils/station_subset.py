'''堆算法：统计可查询到全路全部车次的最小子集，以给车站大屏查询交路'''
import heapq
from collections import defaultdict

def getMinStationSubset(train_stations):
    # 创建一个字典，存储每个车站覆盖的列车索引集合
    station_to_trains = defaultdict(set)
    for train_index, train in enumerate(train_stations):
        for station in train_stations:
            station_to_trains[station].add(train_index)

    heap = []
    for station, train_set in station_to_trains.items():
        heapq.heappush(heap, (-len(train_set), station))  # 用负数来实现最大堆

    # 用一个集合记录已覆盖的列车
    covered_trains = set()
    # 用一个集合记录选中的车站
    selected_stations = set()

    while len(covered_trains) < len(trains):
        # 从堆中取出覆盖最多列车的车站
        _, best_station = heapq.heappop(heap)
        if best_station in selected_stations:
            continue  # 已选中的车站跳过

        # 选定最佳车站
        selected_stations.add(best_station)

        # 更新已覆盖的列车
        newly_covered_trains = station_to_trains[best_station] - covered_trains
        covered_trains.update(newly_covered_trains)

        # 重新将剩余的车站重新加入堆
        for station, train_set in station_to_trains.items():
            if station not in selected_stations:
                heapq.heappush(heap, (-len(train_set - covered_trains), station))

    return selected_stations