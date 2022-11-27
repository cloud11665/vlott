from collections import defaultdict
from datetime import date, datetime
from itertools import groupby
import logging
import utils.date
from utils.cache.timed import timed_lru_cache
from versions.v2.processors import prep_subject, prep_subject_short, prep_teacher, prep_classroom, prep_group
from versions.v2.schema import *
from pydantic.color import Color

@dataclass
class Lesson:
	subject: str
	subject_short: str
	teacher: str
	classroom: str
	color: Color

def trule(*args, **kwargs):
	now = datetime.now()
	date = args[0]
	if now < date:
		return 3600 * 6
	return 1e18

@pickle_cache(timeout_rule = trule)
def get_timetable_data_raw(_date: datetime, class_id: str):
	_date = datetime.date(_date)
	year = _date.year
	if _date.month < 7:
		year = year - 1

	table = get_data()

	monday_before = utils.date.monday_before(_date)
	firday_after = utils.date.friday_after(_date)

	resp = requests.post(
		"https://v-lo-krakow.edupage.org/timetable/server/currenttt.js?__func=curentttGetData&lang=en",
		json = {
			"__args": [
				None,
				{
					"year": year,
					"datefrom": monday_before.strftime(utils.date.FMT),
					"dateto": firday_after.strftime(utils.date.FMT),
					"id": table.classes.name[class_id],
					"showColors": True,
					"showIgroupsInClasses": True,
					"showOrig": True,
					"table": "classes",
				},
			],
			"__gsh": "00000000"
		}
	)

	if not resp.ok:
		logging.warn(f"get_timetable_data_raw: request failed. args=({_date}, {class_id})")
		return []

	return resp.json()["r"]["ttitems"]

@timed_lru_cache(5*60)
def get_timetable_data(_date: datetime, class_id: str, raw: bool):
	resp = get_timetable_data_raw(_date, class_id)
	_date = datetime.date(_date)
	table = get_data()
	monday_before = utils.date.monday_before(_date)
	data: List[TTentry] = []
	events: List[TTabsent] = []

	# TODO: Add "group_short" support and give language groups special treatment
	#       Idk if it should be stored in a db globally or what. May just resort
	#       to db.json with fs locks and some ram cache on top of that.
	#       Multithreading really is a big pain in the ass.
	for obj in resp:
		obj       = defaultdict(lambda: None, obj)
		date_     = date(*map(int, obj["date"].split("-")))
		teacher   = table.teachers[(obj["teacherids"] or ["0"])[0]]
		classroom = table.classrooms[(obj["classroomids"] or ["0"])[0]]
		subject   = table.subjects[obj["subjectid"]]

		# Edupage never ceases to suprise us with yet another standard oddity !
		start = time.fromisoformat(obj["starttime"])
		if start < time(7, 10):    starttime = "07:10"
		elif start > time(16, 30): starttime = "16:30"
		elif obj["starttime"] not in table.periods.starttime:
			logging.error(f"Unusual starttime encountered ({obj['starttime']})")
			continue
		else: starttime = obj["starttime"]

		period    = table.periods[table.periods.starttime[starttime]]
		type_     = obj["type"]
		group_raw = (obj["groupnames"] or [""])[0]

		if type_ == "card":
			data.append(asdict(TTentry(
				subject       = prep_subject(subject, obj),
				subject_short = prep_subject_short(subject, obj),
				teacher       = prep_teacher(teacher),
				classroom     = prep_classroom(classroom, obj),
				color         = (obj["colors"] or ["#d0ffd0"])[0],
				time_index    = int(table.periods.starttime[obj["starttime"]]),
				duration      = obj["durationperiods"] or 1,
				group_raw     = group_raw,
				group         = prep_group(group_raw),
				date          = date_.strftime("%Y-%m-%d"),
				day_index     = (date_ - monday_before).days,
				removed       = obj["removed"] or False,
				raw = TTentryRaw(
					subject   = subject,
					period    = period,
					teacher   = teacher,
					classroom = classroom,
				) if raw else None,
			)))
		else:
			duration = obj["durationperiods"] or 1
			time_index = int(table.periods.starttime[starttime])
			if date_.weekday() == 4 and duration + time_index > 9:
				duration = 9 - time_index
			events.append(TTabsent(
				date       = date_.strftime("%Y-%m-%d"),
				day_index  = (date_ - monday_before).days,
				duration   = duration,
				group      = prep_group(group_raw),
				name       = obj["name"],
				time_index = time_index,
			))

	# Stupid edupage rolls a D100 dice, and returns unsorted data
	# once every 100 requests.
	data.sort(key = lambda x: x["day_index"])

	# Allow filtering by adding a bogus group.
	for x in data:
		if x["subject"] == "religia":
			x["group"] = "religia 1"

	output = [[[]]*10 for _ in range(5)]
	days = {x["day_index"]:[] for x in data}
	for x in data:
		days[x["day_index"]].append(x)

	for idx, day in days.items():
		for x, y in groupby(day, lambda x: x["time_index"]):
			output[idx][x] = list(y)

	return {"ttdata": output, "events": events}
