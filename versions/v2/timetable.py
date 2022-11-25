from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import date, datetime
from itertools import groupby
from typing import List
import os
import json
import re
import logging

import requests

import utils.date
from utils.cache.pickle import pickle_cache
from utils.cache.timed import timed_lru_cache
from versions.v2.schema import Classroom, Subject, TTabsent, TTentry, TTentryRaw, Teacher, get_data
from versions.v2 import overrides
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

@timed_lru_cache(60*60)
def get_overrides(name:str):
	path = os.path.join("versions/v2/overrides/", name + ".json")
	if not os.path.exists(path): return {}
	with open(path, "r") as fh:
		return json.load(fh)

def canonicalize(x): return x.replace("_", " ").lower()

def prep_subject(x: Subject, ctx):
	if not x: return ""
	if x.name in (ovr := get_overrides("subject")): return ovr[x.name]
	return canonicalize(x.name)

def prep_subject_short(x: Subject, ctx):
	if not x: return ""
	if x.short in (ovr := get_overrides("subject_short")): return ovr[x.short]
	return canonicalize(x.short)

def prep_group(x: str, ctx):
	if not x: return ""
	if x in (ovr := get_overrides("group")): return ovr[x]

	if reg := re.match(r"([1-4])([a-zA-Z]|DSD)[1-4]?kl[1-4]?-(\d+)", x):
		cnt, tok, idx = reg.groups()
		cnt, idx = int(cnt), int(idx)
		if tok.lower() == "dsd": return f"DSD {idx}"
		name = {
			"a": "angielski",
			"n": "niemiecki",
			"f": "francuski",
			"h": "hiszpański",
			"r": "rosyjski",
			"w": "włoski"
		}[tok.lower()]
		type_ = ["mały", "duży"][tok.islower()]

		return f"język {name} {type_} {idx}"
	return canonicalize(x)

def prep_teacher(x: Teacher, ctx):
	if not x: return ""
	ovr = overrides.parse()
	if (key := x.short.lower()) in ovr: return ovr[key]
	logging.info(f"No name expansion for key \"{x.short}\"")
	return x.short #Don't canonicalize

def prep_classroom(x: Classroom, ctx):
	if not x: return ""
	ovr = get_overrides("classroom")
	if x.short in ovr: return ovr[x.short]
	return x.short

@pickle_cache(timeout_rule = trule)
def get_timetable_data(_date: datetime, class_id: str, raw: bool):
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
		return [[]]*5

	resp = resp.json()["r"]["ttitems"]
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
		period    = table.periods[table.periods.starttime[obj["starttime"]]]
		type_     = obj["type"]

		if type_ == "card":
			data.append(asdict(TTentry(
				subject       = prep_subject(subject, obj),
				subject_short = prep_subject_short(subject, obj),
				teacher       = prep_teacher(teacher, obj),
				classroom     = prep_classroom(classroom, obj),
				color         = (obj["colors"] or ["#d0ffd0"])[0],
				time_index    = int(table.periods.starttime[obj["starttime"]]),
				duration      = obj["durationperiods"] or 1,
				group         = prep_group((obj["groupnames"] or [None])[0], obj),
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
			time_index = int(table.periods.starttime[obj["starttime"]])
			if date_.weekday() == 4 and duration + time_index > 9:
				duration = 9 - time_index
			events.append(TTabsent(
				date       = date_.strftime("%Y-%m-%d"),
				day_index  = (date_ - monday_before).days,
				duration   = duration,
				group      = prep_group((obj["groupnames"] or [None])[0], obj),
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
