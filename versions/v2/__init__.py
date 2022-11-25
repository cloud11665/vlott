from dataclasses import asdict
import datetime as dt
from datetime import datetime, time
from typing import List, Mapping, Tuple, Union
from pathlib import Path

from fastapi import APIRouter
from utils.responses import json_obj_response

from versions.v2.substitutions import SubstitutionUnion, get_substitution_data
from versions.v2.timetable import get_timetable_data

from versions.v2.schema import DBresponse, TTentry, get_data, class_id_t

router = APIRouter()

@router.get("/substitutions",
            response_model = Union[List[SubstitutionUnion], Mapping[str, List[SubstitutionUnion]]],
            summary = "Substitution data")
async def substitution_data_klass(
		classid: class_id_t = "4E",
		date: dt.date = dt.date.today().strftime("%Y-%m-%d")):
	"""
	 - **?date** - formatted as `%Y-%m-%d`.

	Notes about **classid=\\***:
	- Return schema is a `class |-> List[SubstitutionUnion]` mapping.

	Cache timeout:
	- 1h for future dates
	- forever for previous dates
	
	*Note: when requesting a previous date that is not in cache, bogus data may
	be returned*
	"""
	classid = classid.name
	data = get_substitution_data(datetime.combine(date, time.min))
	if classid == "*":
		return json_obj_response([SubstitutionUnion.saturate(x) for x in data])
	return json_obj_response([SubstitutionUnion.saturate(x) for x in data.get(classid, [])])

@router.get("/ttdata",
            response_model = Union[List[List[List[TTentry]]], Mapping[str, List[List[List[TTentry]]]]],
            summary = "Timetable data")
async def timetable_data_klass(
		classid: class_id_t = "4E",
		date: dt.date = dt.date.today().strftime("%Y-%m-%d"),
		raw: bool = False):
	"""
	 - **?date** - formatted as `%Y-%m-%d`.
	 - **?raw** - include all of the info as returned by edupage in the `TTentry.raw` field.

	Notes about **classid=\\***:
	- Return schema is a `class |-> ttdata` mapping.
	- **?raw** is unsupported due to bandwidth constraints (and DDOS potential).

	Cache timeout:
	- 6h for future dates
	- forever for previous dates
	
	*Note: when requesting a previous date that is not in cache, bogus data may
	be returned*
	"""
	if classid.name == "*":
		data = get_data()
		return json_obj_response(
			{klass: get_timetable_data(datetime.combine(date, time.min), klass, False) for klass in data.classes.name.keys()}
		)
	return json_obj_response(
		get_timetable_data(datetime.combine(date, time.min), classid.name, raw)
	)

@router.get("/get_db",
            response_model = DBresponse,
            summary = "Edupage DB dump")
async def timetable_data(raw: bool = True):
	"""
	Data may be bogus.
	"""
	data = get_data()
	process = lambda x: list(map(asdict, x))
	return json_obj_response({
		"classes":    process(data.classes._data_rows),
		"classrooms": process(data.classrooms._data_rows),
		"dayparts":   process(data.dayparts._data_rows),
		"periods":    process(data.periods._data_rows),
		"subjects":   process(data.subjects._data_rows),
		"teachers":   process(data.teachers._data_rows),
	})


@router.get("/cache_size",
			response_model = Tuple[int, List[Tuple[str, int]]])
async def get_cache_size():
	data = [(file.name, file.stat().st_size) for file in Path("./cache").rglob("*")]
	return [sum(x[1] for x in data), data]
