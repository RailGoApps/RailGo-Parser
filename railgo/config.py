from railgo.parser.db.mongo_json import MongoJsonExporter
from railgo.parser.db.mongo_sqlite import MongoSQLiteExporter
from concurrent.futures import ThreadPoolExecutor
import logging

# 枚举车次列表
TRAIN_KIND_KEYWORDS = [
    "K", "T", "Z", "G", "D", "C", "Y", "L", "S",
    "1", "2", "3", "4", "5", "6", "7", "8"  # 无冠
]

# 路局代码数据
BUREAU_CODE = {
    "B": "哈尔滨局",
    "X": "香港铁路公司",
    "T": "沈阳局",
    "P": "北京局",
    "V": "太原局",
    "C": "呼和浩特局",
    "F": "郑州局",
    "N": "武汉局",
    "Y": "西安局",
    "K": "济南局",
    "H": "上海局",
    "G": "南昌局",
    "Q": "广铁集团",
    "Z": "南宁局",
    "W": "成都局",
    "M": "昆明局",
    "J": "兰州局",
    "R": "乌鲁木齐局",
    "O": "青藏铁路公司",
    "U": "广东城际",
    "I": "边境口岸",
    "-": "国际联运"
}

BUREAU_SHORT_CODE = {
    "B": "哈局",
    "X": "港铁",
    "T": "沈局",
    "P": "京局",
    "V": "太局",
    "C": "呼局",
    "F": "郑局",
    "N": "武局",
    "Y": "西局",
    "K": "济局",
    "H": "上局",
    "G": "南局",
    "Q": "广铁",
    "Z": "宁局",
    "W": "成局",
    "M": "昆局",
    "J": "兰局",
    "R": "乌局",
    "O": "青藏",
    "I": "口岸",
    "U": "广东城际",
    "-": "联运"
}

BUREAU_SGCODE = {
    "哈": "哈尔滨局",
    "沈": "沈阳局",
    "京": "北京局",
    "太": "太原局",
    "呼": "呼和浩特局",
    "郑": "郑州局",
    "武": "武汉局",
    "西": "西安局",
    "济": "济南局",
    "上": "上海局",
    "南": "南昌局",
    "广": "广铁集团",
    "宁": "南宁局",
    "成": "成都局",
    "昆": "昆明局",
    "兰": "兰州局",
    "乌": "乌鲁木齐局",
    "青": "青藏铁路公司",
    "口": "边境口岸"
}

CAR_STYLE_CODE_MAP = {
    "CR200J_16": "CR200J (长编)",
    "CR200J": "CR200J (短编)",
    "CR200J3-C_1012": "CR200J (智能型长编)", # 占位
    "CR200J3-C-676": "CR200J (智能型短编)", # 占位
    "CR200J_1012": "CR200J (智能型长编)", # 占位
    "CR400BF-C_563": "CR400BF-C “瑞雪迎春”",
    "CRH1_646": "CRH1A (200)",
    "CRH1_668": "CRH1A (200)",
    "CRH1_649": "CRH1A (250)",
    "CRH1_1299_1": "CRH1B (1E头型)",
    "CRH380A_494": "CRH380A (旧型)",
    "CRH380A_556": "CRH380A (统型)",
    "CRH380AL_1066": "CRH380AL (一阶)",
    "CRH380AL_1099": "CRH380AL (二阶)",
    "CRH380D_554H": "CRH380D (旧型)",
    "CRH380D_556": "CRH380D (统型)",
    "CRH380D_556W": "CRH380D (统型)",
    "CRH2A_610": "CRH2A (旧型)",
    "CRH2A_613": "CRH2A (统型)",
    "CRH2B_1230H": "CRH2B (旧型)",
    "CRH2B_1230": "CRH2B (统型)",
    "CRH2C2_610": "CRH2C (一阶)",
    "CRH2C1_610": "CRH2C (二阶)",
    "CRH3C_556": "CRH3C (一阶)",
    "CRH3C_556H": "CRH3C (二阶)",
    "CRH5G_606": "CRH5G (旧型)",
    "CRH5G_613": "CRH5G (技术提升)",
    "CJ1-0502_616": "CRH3A (城际型)"
    # CRH380A_556 + CRH380D = CRH380D 统
    # CRH2E_110 + CRH1E = CRH1E-NG
}
CAR_STYLE_NAME_MAP = {
    "25G": "25G (DC600V 供电)",
    "25GDC600V": "25G (DC600V 供电)",
    "25GAC380V": "25G (AC380V 供电)",
    "AC380V": "25G (AC380V 供电)",
    "DC600V": "25G (DC600V 供电)",
    "25KAC380V": "25K",
    "25DTDC600V": "25DT",
    "25TDC600V": "25T (国产)",
    "25TAC380V": "25T (BSP)",
    "BSTAC380V": "25T (BSP)",
    "BST": "25T (BSP)"
}

# 导出
#EXPORTER_MONGO_OUTPUT = "./export/railgo.json"
#EXPORTER = MongoJsonExporter()
EXPORTER_SQLITE_FILE = "./export/railgo.sqlite"
EXPORTER = MongoSQLiteExporter(EXPORTER_SQLITE_FILE)

# 车站信息列表
STATION_95306_CACHE = []  # 客运站缓存
STATION_UNIQUE_TELECODE_EXCEPT = ["UUH"] # 特判
STATION_CWD_SPECIAL_MAP = {
    "佳车站":"佳木斯车务段",
    "霍林郭勒运营维修段":"霍林郭勒车务段",
    "天津枢纽铁路站":"天津环线铁路公司",
    "山西武沁铁路公司站":"武沁铁路公司",
    "山西孝柳铁路公司站":"孝柳铁路公司",
    "临河运营维修段":"乌海车务段",
    "中铁电气化铁路运营管理有限公司额济纳运营维管段":"中铁运管公司",
    "呼中地方铁路有限公司站":"呼中铁路公司",
    "集通公司大板车务段":"大板车务段",
    "集通公司锡林浩特车务段":"锡林浩特车务段",
    "安李支线公司站":"安李铁路公司",
    "襄州运营维修段":"襄州运维段",
    "漯阜铁路有限责任公司站":"漯阜铁路公司",
    "延安运营维修段":"延安运维段",
    "威海地铁站":"桃威铁路公司",
    "益羊管理处站":"山东高速轨道公司",
    "岚山管理处站":"山东高速轨道公司",
    "威海桃威铁路有限公司站":"桃威铁路公司",
    "渤海轮渡站":"渤海铁路轮渡公司",
    "龙岩段":"龙岩车务段",
    "南平段":"南平车务段",
    "向塘西直属站":"向塘西站",
    "惠大铁路站":"中铁惠州公司",
    "广东地铁粤北分公司站":"粤北铁路公司",
    "广东地铁站":"广东地方铁路集团",
    "中铁（惠州）铁路公司站":"中铁惠州公司",
    "广东春罗铁路公司站":"春罗铁路公司",
    "深圳平南公司站":"平南铁路公司",
    "哈尔滨物流站":"哈尔滨车务段"
}
STATION_95572_TMISM_CACHE = {}

# 交路缓存
STATION_MAP_CACHE = {}
STATION_DIAGRAM_CACHE = {}

# 队列
PIPE_POOL = ThreadPoolExecutor(20)
PIPE_TRAIN_PROCESSORS = [
    "getTrainRundays",
    "getTrainMain",
    "getTrainMap",
    "getTrainKind",
    "getStopDistanceAndDiagram"
]
PIPE_STATION_PROCESSORS = [
    "getDetailedFreightInfo",
    "getLevel"
]
PIPE_TRAIN_EXPORTERS = [
    "EXPORTER.exportTrainInfo"
]
PIPE_STATION_EXPORTERS = [
    "EXPORTER.exportStationInfo"
]

# MpaaS 通讯数据
# q 3,143,85,51,185,189,86,234,100,155,143,82,147,16,39,237,126,143,118,38,14,236,7,167,187,208,65,144,46,5,201,168,70
# g 2,240,27,67,77,185,210,37,251,149,2,68,94,191,45,147,17,232,178,213,131,122,85,123,63,16,72,152,105,133,132,4,30
# Q -> Key: 16位分块 整块按位xor 剩余一个字节补\x0f
MGW_RG_CONST = b'\x02\xf0\x1bCM\xb9\xd2%\xfb\x95\x02D^\xbf-\x93\x11\xe8\xb2\xd5\x83zU{?\x10H\x98i\x85\x84\x04\x1e'
MGW_RQ_KEY = b'}\x00#\x15\xb7QQM\xdfK\xce\xc2\xbd\x15\xeeE'
MGW_RQ_IV = b'F\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f'
MGW_PATH = "https://mobile.12306.cn/otsmobile/app/mgs/mgw.htm"

# 95306 GIS 通讯数据
HYFW_GIS_KEY = b"ICT#2020ict_1234"
HYFW_GIS_IV = b"ICTbdzx_12345678"

# 日志
logging.basicConfig(
    format='[%(asctime)s][%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger("Parser")
# LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)
#LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.FileHandler("./railgo.log"))

# 重开

def resetWorks():
    EXPORTER.clear()
