class TrainModel(object):
    '''客运列车数据结构'''
    number = ""
    numberFull = []
    numberKind = ""
    code = ""
    type = ""

    bureau = ""
    bureauName = ""
    runner = ""
    carOwner = ""
    car = ""

    diagram = []
    timetable = []
    spend = 0
    rundays = []
    route = []

    isTemp = False # 临客flag 因为交路按缓存跑的比较麻烦 先放着空
    isFuxing = False

    _beginDay = ""

    def toJson(self):
        return {
            "number": self.number,
            "numberFull": self.numberFull,
            "numberKind": self.numberKind,
            "code": self.code,
            "bureau": self.bureau,
            "bureauName": self.bureauName,
            "type": self.type,
            "diagram": self.diagram,
            "rundays": self.rundays,
            "route": self.route,
            "runner": self.runner,
            "carOwner": self.carOwner,
            "car": self.car,
            "timetable": self.timetable,
            "spend": self.spend,
            "isTemp": self.isTemp
        }

    def __hash__(self):
        '''根据TrainCode分辨列车，避免一车多号导致缺少信息'''
        return hash(self.code)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.code == other.code
        return False
