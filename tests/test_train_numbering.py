"""Offline regressions for the November/December train-number transition."""
import copy
from contextlib import closing
import datetime
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from railgo.parser.db.mongo_json import MongoJsonExporter
from railgo.parser.db.mongo_sqlite import MongoSQLiteExporter

# Import seams: train tests need neither a MongoDB server nor geography data.
with patch("railgo.parser.db.mongo_json.MongoClient"), patch.dict(
    sys.modules, {"jionlp": ModuleType("jionlp")}
):
    from railgo import config
    from railgo.parser.models.train import TrainModel
    from railgo.parser.parse import train


class FrozenDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 18, 12)


def response(data):
    return SimpleNamespace(json=lambda: copy.deepcopy(data))


def instance(number="Z16", code="0100000Z1630", day="20261118"):
    inst = TrainModel()
    inst.number, inst.code = number, code
    inst._dataBeginDay = inst._beginDay = day
    inst.timetable, inst.numberFull, inst.diagram = [], [], []
    inst.rundays = [day]
    return inst


def diagram(*days):
    return {"data": {"bureau_code": "B", "running_list": [
        {"date": day, "flag": "1"} for day in days
    ]}}


def timetable(number, kind="特快"):
    return {"data": {"data": [
        {"station_train_code": number, "arrive_day_diff": "0",
         "arrive_time": clock, "start_time": clock, "station_name": name,
         "station_telecode": telecode, "stopover_time": "0分钟",
         "running_time": elapsed, "train_class_name": kind, "service_type": "1"}
        for name, telecode, clock, elapsed in [
            ("甲站", "AAA", "08:00", "00:00"),
            ("乙站", "BBB", "09:00", "01:00")
        ]
    ]}}


def primary_timetable(code):
    return {"data": {"trainNo": code, "trainDetail": {"stopTime": [
        {"stationTrainCode": "Z16", "stationName": name,
         "stationTelecode": telecode, "dayDifference": "0",
         "arriveTime": clock, "startTime": clock, "stopover_time": "0",
         "runningTime": elapsed, "jiaolu_corporation_code": "哈尔滨客运段",
         "jiaolu_dept_train": "哈尔滨", "jiaolu_train_style": "25T",
         "corporation_code": "B", "station_corporation_code": "B#哈尔滨站"}
        for name, telecode, clock, elapsed in [
            ("甲站", "AAA", "0800", "0"), ("乙站", "BBB", "0900", "60")
        ]
    ]}}}


class MemoryCollection:
    """Only the Mongo operations used by the real exporters."""
    def __init__(self):
        self.rows = []

    def update_one(self, query, update, upsert=False):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                row.update(copy.deepcopy(update["$set"]))
                return
        if upsert:
            self.rows.append(dict(copy.deepcopy(update["$set"]), _id=len(self.rows)))

    def find(self):
        return copy.deepcopy(self.rows)

    def delete_many(self, query):
        self.rows.clear()


def exporter(path, cls=MongoSQLiteExporter):
    result = cls.__new__(cls)
    result.export_location = str(path)
    result.train_collection = MemoryCollection()
    result.station_collection = MemoryCollection()
    return result


class TrainTestCase(unittest.TestCase):
    def replace(self, obj, name, **kwargs):
        replacement = patch.object(obj, name, **kwargs)
        self.addCleanup(replacement.stop)
        return replacement.start()

    def setUp(self):
        self.replace(train.datetime, "datetime", new=FrozenDateTime)
        self.replace(train.time, "sleep")
        self.get = self.replace(train, "get", side_effect=AssertionError("unexpected GET"))
        self.post = self.replace(train, "post", side_effect=AssertionError("unexpected POST"))
        self.replace(train, "updatePassTrain")
        self.replace(train, "updateStationBelongInfo")
        self.replace(train, "TRAIN_DISCOVERY_DAYS", new=14, create=True)
        self.replace(train, "REQUIRE_RUN_WITHIN_14_DAYS", new=True, create=True)


class ExistingBehaviourTests(TrainTestCase):
    def test_gdc_discovery_preserves_codes_and_deduplicates_dates(self):
        self.replace(train, "TRAIN_KIND_KEYWORDS", new=["G", "D", "C"])
        self.replace(train, "TRAIN_DISCOVERY_DAYS", new=7)
        def query(url):
            prefix = parse_qs(urlparse(url).query)["ticket_no"][0]
            return response({"data": [{"ticket_no": prefix + "1", "train_code": prefix + "CODE0A"}]})
        self.get.side_effect = query
        result = list(train.getTrainList())
        self.assertEqual([(x.number, x.code) for x in result],
                         [(p + "1", p + "CODE0A") for p in ["G", "D", "C"]])
        self.assertEqual(self.get.call_count, 21)

    def test_gdc_fallback_classification_is_unchanged(self):
        for number, expected in [("G1", "高速"), ("D1", "动车"), ("C1", "动车")]:
            with self.subTest(number=number):
                self.get.side_effect = None
                self.get.return_value = response(timetable(number))
                result = train.getTrainMainDowngrade(instance(number))
                self.assertEqual(result.type, expected)
                self.assertEqual(len(result.timetable), 2)

    def test_default_guard_keeps_original_datetime_boundary(self):
        # Original code uses timedelta.days, not a calendar-day comparison.
        for day, accepted in [("20261202", True), ("20261203", False)]:
            with self.subTest(day=day):
                self.post.side_effect = None
                self.post.return_value = response(diagram(day))
                if accepted:
                    self.assertEqual(train.getTrainRundays(instance())._beginDay, day)
                else:
                    with self.assertRaises(LookupError):
                        train.getTrainRundays(instance())

    def test_unambiguous_train_keeps_long_term_plan(self):
        days = ("20261110", "20261119", "20270125")
        self.post.side_effect = None
        self.post.return_value = response(diagram(*days))
        result = train.getTrainRundays(instance("G1"))
        self.assertEqual(result.rundays, list(days))
        self.assertEqual(result._beginDay, "20261119")

    def test_matching_primary_response_preserves_discovered_code(self):
        inst = instance()
        self.post.side_effect = None
        self.post.return_value = response(primary_timetable(inst.code))
        fallback = self.replace(train, "getTrainMainDowngrade")
        result = train.getTrainMain(inst)
        self.assertEqual(result.code, inst.code)
        self.assertEqual(len(result.timetable), 2)
        fallback.assert_not_called()


class NumberingChangeTests(TrainTestCase):
    def test_new_prefixes_and_defaults(self):
        self.assertTrue({"N", "V", "X"}.issubset(config.TRAIN_KIND_KEYWORDS))
        self.assertEqual(config.TRAIN_DISCOVERY_DAYS, 14)
        self.assertIs(config.REQUIRE_RUN_WITHIN_14_DAYS, True)

    def test_configurable_window_includes_today_and_last_day(self):
        self.replace(train, "TRAIN_KIND_KEYWORDS", new=["V"])
        self.replace(train, "TRAIN_DISCOVERY_DAYS", new=20)
        self.get.side_effect = None
        self.get.return_value = response({"data": []})
        list(train.getTrainList())
        dates = [parse_qs(urlparse(c[0][0]).query)["depart_date"][0]
                 for c in self.get.call_args_list]
        self.assertEqual(dates, [(FrozenDateTime.now() + datetime.timedelta(days=d)).strftime("%Y%m%d")
                                 for d in range(20)])

    def test_invalid_windows_fail_before_network(self):
        for days in [0, -1, True, "14", 1.5]:
            with self.subTest(days=days), patch.object(train, "TRAIN_DISCOVERY_DAYS", days):
                with self.assertRaises(ValueError):
                    list(train.getTrainList())
        self.get.assert_not_called()

    def test_new_prefix_without_data_does_not_abort_gdc_discovery(self):
        self.replace(train, "TRAIN_KIND_KEYWORDS", new=["N", "V", "X", "G", "D", "C"])
        self.replace(train, "TRAIN_DISCOVERY_DAYS", new=1)
        def query(url):
            prefix = parse_qs(urlparse(url).query)["ticket_no"][0]
            if prefix in ["N", "V", "X"]:
                return response({"status": False, "data": None})
            return response({"data": [{"ticket_no": prefix + "1", "train_code": prefix + "CODE"}]})
        self.get.side_effect = query
        self.assertEqual([x.number for x in train.getTrainList()], ["G1", "D1", "C1"])

    def test_failed_query_does_not_discard_buffered_trains(self):
        self.replace(train, "TRAIN_KIND_KEYWORDS", new=["G", "X", "D", "C"])
        self.replace(train, "TRAIN_DISCOVERY_DAYS", new=1)
        def query(url):
            prefix = parse_qs(urlparse(url).query)["ticket_no"][0]
            if prefix == "X":
                raise ConnectionRefusedError("temporary list failure")
            return response({"data": [{"ticket_no": prefix + "1", "train_code": prefix + "CODE"}]})
        self.get.side_effect = query
        self.assertEqual([x.number for x in train.getTrainList()], ["G1", "D1", "C1"])

    def test_new_prefixes_reach_timetable_and_storage(self):
        self.replace(train, "TRAIN_KIND_KEYWORDS", new=["N", "V", "X"])
        self.replace(train, "TRAIN_DISCOVERY_DAYS", new=2)
        kinds = {"N": "特快", "V": "快速", "X": "高速"}
        def query(url):
            params = parse_qs(urlparse(url).query)
            if "ticket_no" in params:
                prefix = params["ticket_no"][0]
                return response({"data": [{"ticket_no": prefix + "1", "train_code": prefix + "CODE0A"}]})
            prefix = params["train_no"][0][0]
            return response(timetable(prefix + "1", kinds[prefix]))
        def post(url, data):
            return response(diagram("20261119") if "queryTrainDiagram" in url else {"data": {}})
        self.get.side_effect, self.post.side_effect = query, post
        store = exporter("unused")
        for inst in train.getTrainList():
            store.exportTrainInfo(train.getTrainMain(train.getTrainRundays(inst)))
        self.assertEqual({row["number"] for row in store.trainInfoList()}, {"N1", "V1", "X1"})
        self.assertTrue(all(len(row["timetable"]) == 2 for row in store.trainInfoList()))

    def test_discovery_binds_same_name_versions_to_observed_dates(self):
        self.replace(train, "TRAIN_KIND_KEYWORDS", new=["Z"])
        def query(url):
            day = parse_qs(urlparse(url).query)["depart_date"][0]
            code = "0100000Z1630" if day < "20261125" else "0100000Z1600"
            return response({"data": [{"ticket_no": "Z16", "train_code": code}]})
        self.get.side_effect = query
        versions = list(train.getTrainList())
        self.assertEqual([x.code for x in versions], ["0100000Z1630", "0100000Z1600"])
        for inst in versions:
            self.post.side_effect = None
            self.post.return_value = response(diagram("20261119", "20261124", "20261125", "20261126"))
            train.getTrainRundays(inst)
        self.assertEqual(versions[0].rundays, ["20261119", "20261124"])
        self.assertEqual(versions[1].rundays, ["20261125", "20261126"])
        self.assertEqual(versions[1]._beginDay, "20261125")

    def test_future_candidate_does_not_choose_old_version_begin_day(self):
        self.post.side_effect = None
        self.post.return_value = response(diagram("20261119", "20261125"))
        result = train.getTrainRundays(instance(day="20261125"))
        self.assertEqual(result._beginDay, "20261125")
        self.assertEqual(result.rundays, ["20261125"])

    def test_disabling_guard_accepts_future_plan_and_sets_bureau(self):
        self.replace(train, "REQUIRE_RUN_WITHIN_14_DAYS", new=False)
        self.post.side_effect = None
        self.post.return_value = response(diagram("20261210"))
        result = train.getTrainRundays(instance())
        self.assertEqual(result._beginDay, "20261210")
        self.assertEqual((result.bureau, result.bureauName), ("B", "哈局"))

    def test_old_version_dates_are_not_assigned_to_new_code(self):
        self.post.side_effect = None
        self.post.return_value = response(diagram("20261119"))
        with self.assertRaises(LookupError):
            train.getTrainRundays(instance(day="20261125"))

    def test_primary_code_mismatch_uses_code_based_fallback(self):
        inst = instance(code="0100000Z1600", day="20261125")
        self.post.side_effect = None
        self.post.return_value = response(primary_timetable("0100000Z1630"))
        fallback = self.replace(train, "getTrainMainDowngrade", return_value=inst)
        self.assertIs(train.getTrainMain(inst), inst)
        fallback.assert_called_once_with(inst)

    def test_ambiguous_primary_without_code_uses_fallback(self):
        inst = instance()
        inst._validRunDays = {"20261119"}
        payload = primary_timetable(inst.code)
        del payload["data"]["trainNo"]
        self.post.side_effect = None
        self.post.return_value = response(payload)
        fallback = self.replace(train, "getTrainMainDowngrade", return_value=inst)
        train.getTrainMain(inst)
        fallback.assert_called_once_with(inst)

    def test_old_and_new_kt_and_new_prefixes_keep_source_classification(self):
        for number, kind, expected in [
            ("K1", "快速", "新空调快速"), ("T1", "特快", "新空调特快"),
            ("K1", "动车", "动车"), ("T1", "高速", "高速"),
            ("N1", "特快", "新空调特快"), ("V1", "快速", "新空调快速"),
            ("X1", "高速", "高速")
        ]:
            with self.subTest(number=number, kind=kind):
                inst = instance(number)
                inst.timetable = [{"station": "wrong version"}]
                self.get.side_effect = None
                self.get.return_value = response(timetable(number, kind))
                result = train.getTrainMainDowngrade(inst)
                self.assertEqual(result.type, expected)
                self.assertEqual(len(result.timetable), 2)
                self.assertEqual(result.numberFull, [number])

    def test_diagram_cache_separates_same_name_on_different_start_days(self):
        self.replace(train, "STATION_MAP_CACHE", new={
            day + "AAA": {"Z16": [0, "普通", "特快"]}
            for day in ["20261124", "20261125"]
        })
        self.replace(train, "STATION_DIAGRAM_CACHE", new={
            (day, "Z16"): [{"number": "Z16", "version": day}]
            for day in ["20261124", "20261125"]
        })
        for day in ["20261124", "20261125"]:
            inst = instance(day=day)
            inst.numberFull = ["Z16"]
            inst.timetable = [{"stationTelecode": "AAA", "day": 0}]
            train.getStopDistanceAndDiagram(inst)
            self.assertEqual(inst.diagram, [{"number": "Z16", "version": day}])

    def test_sqlite_keeps_both_versions_and_updates_only_matching_code(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "railgo.sqlite"
            store = exporter(path)
            store.clear()
            for code, day in [("0100000Z1630", "20261124"), ("0100000Z1600", "20261125")]:
                store.exportTrainInfo(instance(code=code, day=day))
            updated = instance(code="0100000Z1600", day="20261126")
            store.exportTrainInfo(updated)
            store.export()
            with closing(sqlite3.connect(path)) as db:
                rows = db.execute("SELECT code, number, rundays FROM trains ORDER BY code").fetchall()
            self.assertEqual(rows, [
                ("0100000Z1600", "Z16", '["20261126"]'),
                ("0100000Z1630", "Z16", '["20261124"]')
            ])

    def test_json_structure_is_unchanged_and_raw_versions_coexist(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "railgo.json"
            store = exporter(path, MongoJsonExporter)
            for code in ["0100000Z1630", "0100000Z1600"]:
                inst = instance(code=code)
                inst.numberFull = ["Z16"]
                store.exportTrainInfo(inst)
            store.export()
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(result), {"trains", "stations", "_index_trains", "_index_stations"})
            self.assertEqual({x["code"] for x in result["trains"]},
                             {"0100000Z1630", "0100000Z1600"})
            self.assertIsInstance(result["_index_trains"]["Z16"], int)


if __name__ == "__main__":
    unittest.main()
