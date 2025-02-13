class TrainModel(object):
    '''客运列车数据结构'''
    number = None
    code = None
    numberFull = None
    type = None

    bureau = None
    runner = None
    carowner = None
    car = None

    diagram = []
    timetable = None
    rundays = None
    route = None

    isTemp = False

    def toJson(self):
        return {
            "number": self.number,
            "code": self.code,
            "numberFull": self.numberFull,
            "bureau": self.bureau,
            "type": self.type,
            "diagram": self.diagram,
            "rundays": self.rundays,
            "route": self.route,
            "runner": self.runner,
            "carowner": self.carowner,
            "car": self.car,
            "timetable": self.timetable,
            "isTemp": self.isTemp
        }

    def __hash__(self):
        '''根据TrainCode分辨列车，避免一车多号导致缺少信息'''
        return hash(self.code)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.code == other.code
        return False
