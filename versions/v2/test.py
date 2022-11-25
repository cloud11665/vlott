from dataclasses import asdict
import datetime as dt
from datetime import datetime, time
from typing import List, Literal, Mapping, Optional, Tuple, Union

from fastapi import FastAPI, APIRouter, Path
from fastapi.responses import PlainTextResponse
from utils.responses import json_obj_response
from utils.openapi import build_docs

from versions.v2.substitutions import SubstitutionUnion, get_substitution_data
from versions.v2.timetable import get_timetable_data

from versions.v2.schema import DBresponse, TTentry, get_data, class_id_t

router = APIRouter()

@router.get("/substitutions/{class_id}",
            response_model = List[SubstitutionUnion],
            summary = "Substitution data for a single class")
async def substitution_data_klass(
		class_id: class_id_t = "4E",
		date: dt.date = dt.date.today().strftime("%Y-%m-%d")):
	"""
	`class_id` is case sensitive
	
	`date` is formatted as '%Y-%m-%d'
	
	Cache timeout:
	- 1h for future dates
	- forever for previous dates
	
	*Note: when requesting a previous date that is not in cache, bogus data may
	be returned*
	"""
	class_id = class_id.name
	return json_obj_response([
		SubstitutionUnion.saturate(x) for x in 
		get_substitution_data(datetime.combine(date, time.min))[class_id]]
	)

@router.get("/substitutions",
            response_model = Mapping[str, List[SubstitutionUnion]],
            summary = "Substitution data for all classes")
async def substitution_data(
		date: dt.date = dt.date.today().strftime("%Y-%m-%d")):
	"""	
	`date` is formatted as '%Y-%m-%d'
	
	Cache timeout:
	- 1h for future dates
	- forever for previous dates
	
	*Note: when requesting a previous date that is not in cache, bogus data may
	be returned*
	"""
	return json_obj_response(
		{klass : list(map(SubstitutionUnion.saturate, data))
			for klass, data
		in get_substitution_data(datetime.combine(date, time.min)).items()}
	)

@router.get("/ttdata/{class_id}",
            response_model = List[List[List[TTentry]]],
            summary = "Timetable data")
async def timetable_data_klass(
		class_id: class_id_t = "4E",
		date: dt.date = dt.date.today().strftime("%Y-%m-%d"),
		raw: bool = False
		):
	"""	
	`class_id` is case sensitive

	Returned array is **always** of size 5. 

	`date` is formatted as '%Y-%m-%d'

	`raw` - include `raw` field
	
	Cache timeout:
	- 6h for future dates
	- forever for previous dates
	
	*Note: when requesting a previous date that is not in cache, bogus data may
	be returned*
	"""
	return json_obj_response(
		get_timetable_data(datetime.combine(date, time.min), class_id.name, raw)
	)

@router.get("/attdata",
            response_model = List[List[List[TTentry]]],
            summary = "Timetable data")
async def timetable_data(
		date: dt.date = dt.date.today().strftime("%Y-%m-%d"),
		raw: bool = False):
	"""	
	Returned array is **always** of size 5. 

	`date` is formatted as '%Y-%m-%d'
	
	`raw` - include `raw` field

	Cache timeout:
	- 6h for future dates
	- forever for previous dates
	
	*Note: when requesting a previous date that is not in cache, bogus data may
	be returned*
	"""
	data = get_data()
	return json_obj_response(
		{klass: get_timetable_data(datetime.combine(date, time.min), klass, raw)
			for klass in data.classes.name.keys()}
	)

@router.get("/get_db",
            response_model = DBresponse,
            summary = "Raw/Processed edupage db dump")
async def timetable_data(raw: bool = True):
	"""
	
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

@router.get("/secret",
			include_in_schema = False,
			response_model = str)
async def troll():
	return PlainTextResponse("trolled", 418)
