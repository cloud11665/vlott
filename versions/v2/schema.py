from dataclasses import dataclass, fields, asdict
from typing import List, TypeVar, Generic, Dict, Optional
from datetime import time
from enum import Enum

import requests

import utils.date
from utils.cache.pickle import pickle_cache

T = TypeVar('T')

class Table(Generic[T]):
	"""
	Represents a queryable database table.

	obj[x] - lookup by `id`
	obj.foo[x] - lazy lookup by `foo`, returns `id`
	obj[obj.foo[x]] - full lookup by `foo`
	"""
	_data_rows: List[T]
	_lut: Dict[int, T]

	def __init__(self, data_rows: List[T]):
		self._data_rows = list(data_rows)
		self._lut = dict()

		for field in fields(self._data_rows[0]):
			if field.name == "id": continue
			setattr(self, field.name, dict())

		for row in self._data_rows:
			id = row.id
			self._lut[id] = row
			for k,v in asdict(row).items():
				if k == "id": continue
				getattr(self, k)[v] = id

	def __getitem__(self, key):
		return self._lut.get(key, None)

@dataclass
class Teacher:
	id: int
	short: str
	# cb_hidden: bool
	# expired: bool

@dataclass
class Subject:
	id: int
	name: str
	short: str

@dataclass
class Classroom:
	id: int
	short: str

@dataclass
class Class:
	id: int
	name: str
	short: str

@dataclass
class Period:
	id: int
	# name: str
	short: int
	# period: int
	starttime: time
	endtime: time

@dataclass
class Daypart:
	id: str
	starttime: time
	endtime: time

@dataclass
class DBAccessor:
	teachers: Table[Teacher]
	subjects: Table[Subject]
	classrooms: Table[Classroom]
	classes: Table[Class]
	periods: Table[Period]
	dayparts: Table[Daypart]

@dataclass
class DBresponse:
	teachers: List[Teacher]
	subjects: List[Subject]
	classrooms: List[Classroom]
	classes: List[Class]
	periods: List[Period]
	dayparts: List[Daypart]


@pickle_cache()
def get_data() -> DBAccessor:
	args = {
		"__args": [
			None,
			2022,
			{
				"vt_filter":{
					"datefrom": utils.date.monday_before().strftime(utils.date.FMT),
					"dateto": utils.date.friday_after().strftime(utils.date.FMT)
				}
			},
			{
				"op": "fetch",
				"needed_part": {
					"teachers": [
						"short",
						"name",
						# "firstname",
						# "lastname",
						# "subname",
						# "code",
						# "cb_hidden",
						# "expired",
						# "firstname",
						# "lastname",
						# "short"
					],
					"classes": [
						"short",
						"name",
						"firstname",
						"lastname",
						"subname",
						"code",
						"classroomid"
					],
					"classrooms": [
						"short",
						"name",
						"firstname",
						"lastname",
						"subname",
						"code",
						"name",
						"short"
					],
					# "igroups": [
					# 	"short",
					# 	"name",
					# 	"firstname",
					# 	"lastname",
					# 	"subname",
					# 	"code"
					# ],
					# "students": [
					# 	"short",
					# 	"name",
					# 	"firstname",
					# 	"lastname",
					# 	"subname",
					# 	"code",
					# 	"classid"
					# ],
					"subjects": [
						"short",
						"name",
						"firstname",
						"lastname",
						"subname",
						"code",
						"name",
						"short"
					],
					# "events": ["typ", "name"],
					# "event_types": ["name", "icon"],
					# "subst_absents": ["date", "absent_typeid","groupname"],
					"periods": [
						"short",
						# "name",
						# "firstname",
						# "lastname",
						# "subname",
						# "code",
						# "period",
						"starttime",
						"endtime"
					],
					"dayparts": ["starttime","endtime"],
					# "dates": ["tt_num","tt_day"]
				},
				"needed_combos": {}
			}
		],
		"__gsh": "00000000"
	}

	resp = requests.post(
		"https://v-lo-krakow.edupage.org/rpr/server/maindbi.js?__func=mainDBIAccessor",
		json = args
	)

	typemap = {
		"teachers": Teacher,
		"subjects": Subject,
		"classrooms": Classroom,
		"classes": Class,
		"periods": Period,
		"dayparts": Daypart,
	}

	data: Dict[str, Table] = {}

	for table in resp.json()["r"]["tables"]:
		if table["id"] not in typemap: continue
		t = typemap[table["id"]]
		data[table["id"]] = Table([t(**x) for x in table["data_rows"]])

	return DBAccessor(**data)

class_id_t = Enum("class_id", {"*":"*", **{x:x for x in get_data().classes.short.keys()}})

@dataclass
class TTentryRaw:
	subject: Subject
	period: Period
	teacher: Teacher
	classroom: Classroom

@dataclass
class TGroup:
	name: str
	raw: str
	short: str

@dataclass
class TTeacher:
	name: str
	short: str

@dataclass
class TTentry:
	subject: str
	subject_short: str
	teacher: TTeacher
	classroom: str
	color: str
	time_index: int
	duration: int
	group: Optional[TGroup]
	date: str
	day_index: int
	removed: bool
	raw: Optional[TTentryRaw]

@dataclass
class TTabsent:
	duration: int
	time_index: int
	day_index: int
	name: str
	date: str
	group: Optional[TGroup]
