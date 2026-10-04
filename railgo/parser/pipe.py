'''核心的任务队列（待完善）'''
from railgo.config import *
from railgo.parser.parse import *
from railgo.parser.parse.train import *
from railgo.parser.parse.station import *
from functools import wraps
import time
import copy
import tqdm
import tqdm_logging_wrapper as tqdl
import sys


def task(f):
    @wraps(f)
    def wraptask(*args, **kwargs):
        PIPE_POOL.submit(f, *args, **kwargs)
    return wraptask


@task
def train(inst, pbar):
    LOGGER.info(f"{inst.number} ({inst.code}) 车次接收")
    for x in PIPE_TRAIN_PROCESSORS:
        LOGGER.debug(f"{inst.number} ({inst.code})执行抓取 {x}")
        try:
            inst = eval(x)(inst)
        except LookupError as e:
            LOGGER.info(f"{inst.number} ({inst.code}) 流程 {x} 错误：{sys.exc_info()[1]}")
            return
        except Exception as e:
            # 防御不同步
            LOGGER.exception(e)
            LOGGER.critical(f"{inst.number} ({inst.code}) 车次抓取有误")
        time.sleep(0.05)

    for x in PIPE_TRAIN_EXPORTERS:
        try:
            eval(x)(inst)
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.critical(f"{inst.number} ({inst.code}) 车次存储错误")
    pbar.update(1)
    LOGGER.info(f"{inst.number} ({inst.code}) 车次完成")
    time.sleep(0.02)


@task
def station(inst, pbar):
    LOGGER.info(f"{inst.name} ({inst.telecode}) 车站接收")

    for x in PIPE_STATION_PROCESSORS:
        LOGGER.debug(f"{inst.name} ({inst.telecode}) 执行抓取 {x}")
        try:
            inst = eval(x)(inst)
        except LookupError:
            LOGGER.info(f"{inst.name} ({inst.telecode}) 车站流程 {x} 错误：{sys.exc_info()[1]}")
            return
        except Exception as e:
            # 防御不同步
            LOGGER.exception(e)
            LOGGER.critical(f"{inst.name} ({inst.telecode}) 车站抓取有误")
            return

    for x in PIPE_STATION_EXPORTERS:
        try:
            eval(x)(inst)
        except Exception as e:
            LOGGER.exception(e)
            LOGGER.critical(f"{inst.name} ({inst.telecode}) 车站存储错误")
    pbar.update(1)
    LOGGER.info(f"{inst.number} ({inst.telecode}) 车站完成")
    time.sleep(0.02)


def init_train():
    try:
        pbar = tqdm.tqdm(total=0, desc="遍历列车", unit="次",
                      position=1, file=sys.stdout, leave=True)
        with tqdl.wrap_logging_for_tqdm(pbar, logger=LOGGER):
            for x in getTrainList():
                pbar.total += 1
                train(x, pbar)
    except Exception as e:
        LOGGER.exception(e)


def init_stations():
    try:
        pbar = tqdm.tqdm(total=0, desc="遍历车站", unit="个",
                      position=0, file=sys.stdout, leave=True)
        with tqdl.wrap_logging_for_tqdm(pbar, logger=LOGGER):
            #get95572TmismList()
            for x in stationTogether():
                pbar.total += 1
                station(x, pbar)
    except Exception as e:
        LOGGER.exception(e)

def launchMainPipe():
    ts = time.time()
    init_stations()
    init_train()
    PIPE_POOL.shutdown(wait=True)
    LOGGER.info("=======爬取完成=======")
    EXPORTER._stationFinal()
    EXPORTER.export()
    LOGGER.info("全库导出成功")
    EXPORTER.close()
    LOGGER.info(f"本批耗时：{time.time()-ts}s")
    LOGGER.info("单批爬取完毕，结束本批运行")
