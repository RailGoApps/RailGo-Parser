class StationModel(object):
    bureau = None
    belong = None
    name = None
    tmism = None
    tgcode = None
    pycode = None
    line = None
    type = 0  # 0=通过 1=客运 2=货运 3=客货 4=线路所
    trainList = []

    def toJson(self):
        return {
            "name": self.name,
            "tmism": self.tmism,
            "tgcode": self.tgcode,
            "pycode": self.pycode,
            "bureau": self.bureau,
            "belong": self.belong,
            "line": self.line,
            "type": self.type,
            "trainList": self.trainList
        }

    def __hash__(self):
        return hash(self.tmism)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.tmism == other.tmism
        return False
