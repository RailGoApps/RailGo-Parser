from celery import Celery
import logging

# 枚举车次列表
TRAIN_KIND_KEYWORDS = [
    "", "K", "T", "Z", "G", "D", "C", "Y", "L", "S"  # 无冠
]
TRAIN_CODE_UNIQUE_LIST = []

# 静态数据
BUREAU_CODE = {
    "B":"哈尔滨局",
    "X":"香港铁路公司",
    "T":"沈阳局",
    "P":"北京局",
    "V":"太原局",
    "C":"呼和浩特局",
    "F":"郑州局",
    "N":"武汉局",
    "Y":"西安局",
    "K":"济南局",
    "H":"上海局",
    "G":"南昌局",
    "Q":"广铁集团",
    "Z":"南宁局",
    "W":"成都局",
    "M":"昆明局",
    "J":"兰州局",
    "R":"乌鲁木齐局",
    "O":"青藏铁路公司",
    "I":"口岸",
    "-":"中老铁路公司"
}

BUREAU_SIMPLE_CODE = {
    "B":"哈局",
    "X":"港铁",
    "T":"沈局",
    "P":"京局",
    "V":"太局",
    "C":"呼局",
    "F":"郑局",
    "N":"武局",
    "Y":"西局",
    "K":"济局",
    "H":"上局",
    "G":"南局",
    "Q":"广铁",
    "Z":"宁局",
    "W":"成局",
    "M":"昆局",
    "J":"兰局",
    "R":"乌局",
    "O":"青藏",
    "I":"口岸",
    "-":"中老"
}

# 车站信息列表
STATION_KYLIST_CACHE = [] # 客运站缓存
STATION_XLS_EXCEPT = ["花所","八所"] # 特判

# 队列
PIPE_CELERY = Celery(
    "railgo",
    broker="redis://localhost:6379/railgo_queue_broker",
    backend="redis://localhost:6379/railgo_queue_backend"
    )
PIPE_TRAIN_PROCESSORS = [
    "getTrainRundays",
    "getTrainMain",
    "getTrainMap",
    "getTrainKind"
]
PIPE_STATION_PROCESSORS = [
    "getKMLineInfo"
]
PIPE_TRAIN_EXPORTERS = [
    "lambda i:print(i.toJson())"
]

# MpaaS通讯数据
# q 3,143,85,51,185,189,86,234,100,155,143,82,147,16,39,237,126,143,118,38,14,236,7,167,187,208,65,144,46,5,201,168,70
# g 2,240,27,67,77,185,210,37,251,149,2,68,94,191,45,147,17,232,178,213,131,122,85,123,63,16,72,152,105,133,132,4,30
MGW_RG_CONST = b'\x02\xf0\x1bCM\xb9\xd2%\xfb\x95\x02D^\xbf-\x93\x11\xe8\xb2\xd5\x83zU{?\x10H\x98i\x85\x84\x04\x1e'
MGW_RQ_KEY = b'}\x00#\x15\xb7QQM\xdfK\xce\xc2\xbd\x15\xeeE'
MGW_RQ_IV = b'F\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f'
MGW_PATH = "https://mobile.12306.cn/otsmobile/app/mgs/mgw.htm"

# 日志
logging.basicConfig(
    format='[%(asctime)s][%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger("Parser")
# LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)

# 重开
def resetWorks():
    TRAIN_CODE_UNIQUE_LIST = []
