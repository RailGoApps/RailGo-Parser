from railgo.config import *
from railgo.parser.parse import train
from railgo.parser.pipe import *

def parseOnceMain():
    LOGGER.info("爬取主进程: 启动")
    resetWorks()
    launchMainPipe(pushQueue)

def pushQueue():
    for x in train.TrainParser.getTrainList():
        WORKS_QUEUE.put(x)

if __name__ == "__main__":
    parseOnceMain()