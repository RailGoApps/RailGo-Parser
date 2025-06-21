class StationModel(object):
    bureau = ""
    belong = ""
    name = ""
    tmism = "未知"
    telecode = ""
    pinyin = ""
    pinyinTriple = ""
    lines = []
    type = []  # 货 客 高 行 运
    trainList = []

    def toJson(self):
        return {
            "name": self.name,
            "tmism": self.tmism,
            "telecode": self.telecode,
            "pinyin": self.pinyin,
            "pinyinTriple": self.pinyinTriple,
            "bureau": self.bureau,
            "belong": self.belong,
            "lines": self.lines,
            "type": self.type,
            "trainList": self.trainList
        }

    def __hash__(self):
        return hash(self.tmism)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.tmism == other.tmism
        return False
