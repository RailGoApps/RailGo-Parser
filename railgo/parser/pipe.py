'''核心的任务队列（待完善）'''
from railgo.config import *
from railgo.parser.parse import *
from railgo.parser.parse.train import *
from railgo.parser.parse.station import *
from functools import wraps
import time


def task(f):
    @wraps(f)
    def wraptask(*args, **kwargs):
        PIPE_POOL.submit(f, *args, **kwargs)
    return wraptask


@task
def train(inst):
    LOGGER.info(f"{inst.number} 车次接收")
    for x in PIPE_TRAIN_PROCESSORS:
        LOGGER.debug(f"{inst.number} 执行抓取 {x}")
        try:
            inst = eval(x)(inst)
        except LookupError as e:
            LOGGER.debug(f"车次 {inst.number} 信息缺失或未在目前开行范围内 报出错误的抓取：{x}")
            return
        except Exception as e:
            # 防御不同步
            LOGGER.exception(e)
            LOGGER.critical(f"车次 {inst.number} 抓取有误")
        time.sleep(0.05)

    for x in PIPE_TRAIN_EXPORTERS:
        try:
            eval(x)(inst)
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.critical(f"车次 {inst.number} 存储错误")
    time.sleep(0.02)


@task
def station(inst):
    LOGGER.info(f"{inst.name}站接收")

    for x in PIPE_STATION_PROCESSORS:
        LOGGER.debug(f"{inst.name} 执行抓取 {x}")
        try:
            inst = eval(x)(inst)
        except LookupError:
            LOGGER.debug(f"车站信息缺失，舍弃")
            return
        except Exception as e:
            # 防御不同步
            LOGGER.exception(e)
            LOGGER.critical(f"车站 {inst.name} 抓取有误")
            return

    for x in PIPE_STATION_EXPORTERS:
        try:
            eval(x)(inst)
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.critical(f"车站 {inst.name} 存储错误")
    time.sleep(0.02)


def init_train():
    try:
        for x in getTrainList():
            train(x)
    except Exception as e:
        LOGGER.exception(e)


def init_stations():
    try:
        for x in stationTogether():
            station(x)
    except Exception as e:
        LOGGER.exception(e)


def init_jiaolu():
    try:
        for x in EXPORTER.trainInfoList():
            if x["diagram"] == []:
                afterFixJiaolu(x)
                EXPORTER.exportTrainInfo(x)
        LOGGER.info("没有消化的缓存交路如下")
        LOGGER.info(JIAOLU_SYNC)
    except Exception as e:
        LOGGER.exception(e)


def launchMainPipe():
    ts = time.time()
    init_stations()
    LOGGER.info("=======车站信息爬取完成=======")
    init_train()
    init_jiaolu()
    LOGGER.info("=======车次信息爬取完成=======")
    PIPE_POOL.shutdown(wait=True)
    EXPORTER.exportToJson(EXPORTER_MONGO_OUTPUT)
    EXPORTER.close()
    LOGGER.info(f"本批耗时：{time.time()-ts}s")
    LOGGER.info("单批爬取完毕，结束本批运行")
