'''核心的任务队列（待完善）'''
from railgo.config import *
from railgo.parser.parse import *
from railgo.parser.parse.train import *
from railgo.parser.parse.station import *
import time

@PIPE_CELERY.task
def train(inst):
    LOGGER.info(f"{inst.number} 车次接收")
    for x in PIPE_TRAIN_PROCESSORS:
        LOGGER.debug(f"{inst.number} 执行抓取 {x}")
        try:
            inst = eval(x)(inst)
            if inst == None:
                # 备用模式
                LOGGER.debug(f"车次信息缺失，舍弃")
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

@PIPE_CELERY.task
def station(inst, kycache):
    LOGGER.info(f"{inst.name} 站接收")

    for x in PIPE_STATION_PROCESSORS:
        LOGGER.debug(f"{inst.name} 执行抓取 {x}")
        try:
            inst = eval(x)(inst)
        except Exception as e:
            # 防御不同步
            LOGGER.exception(e)
            LOGGER.critical(f"车站 {inst.name} 抓取有误")
            return
    
    for x in PIPE_TRAIN_EXPORTERS:
        try:
            eval(x)(inst)
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.critical(f"车站 {inst.name} 存储错误")

def init_train():
    try:
        for x in getTrainList():
            train(x)
    except Exception as e:
        LOGGER.exception(e)

def init_stations():
    try:
        STATION_KYLIST_CACHE = getKYFWList()
        for x in getKMList():
            station(x, STATION_KYLIST_CACHE)
    except Exception as e:
        LOGGER.exception(e)


def launchMainPipe():
    ts = time.time()
    init_train()
    LOGGER.info("车次信息爬取完成")
    time.sleep(1)
    LOGGER.info(f"本批耗时：{time.time()-ts}s")
    LOGGER.info("单批爬取完毕，结束本批运行")
