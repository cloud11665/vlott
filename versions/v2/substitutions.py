import dataclasses
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Mapping, Optional, Tuple, Union

import requests
from lxml import html
from utils.cache.pickle import pickle_cache
from utils.date import next_weekday


@dataclass
class SBST_Unknown:...

@dataclass
class SBST_Substitution:
	_pattern = re.compile(r"^(?:(.+?):\s)*(?:\((.+?)\)\s➔\s)*(.+?)\s-\sSubstitution:\s\((.+?)\)\s➔\s(.+?)(?:,\s(.*))*$")
	group: Optional[str]
	subject_before: Optional[str]
	subject: str
	teacher_before: str
	teacher: str
	comment: Optional[str]

@dataclass
class SBST_Cancellation:
	_pattern = re.compile(r"^(?:(?:(.+?):\s)*(.+?)\s-\s(?:(.+?),\s)*Cancelled(?:,\s(.*))*)|Absent$")
	group: Optional[str]
	subject: str
	teacher: str
	comment: Optional[str]

@dataclass
class SBST_Teacher_Decl:
	_pattern = re.compile(r"^(?:(.+?):\s)?(.+?)\s-\sTeacher:\s(.+?)(?:,\s(.*))?$")
	group: Optional[str]
	subject: str
	teacher: str
	comment: Optional[str]

@dataclass
class SBST_Teacher_Decl_Untagged:
	_pattern = re.compile(r"^(?:(.+?):\s)*(?:\((.+?)\)\s➔\s)*(.+?)\s-\s\((.+?)\)$")
	group: Optional[str]
	subject: str
	teacher_before: Optional[str]
	teacher: str

type_map: Mapping[str, object] = {
	"cancellation": SBST_Cancellation,
	"teacher_decl": SBST_Teacher_Decl,
	"teacher_decl_untagged": SBST_Teacher_Decl_Untagged,
	"substitution": SBST_Substitution,
}

_time_regex = re.compile(r"\(?(\d+)\s-\s(\d+)\)?|\(?(\d+)\)?|")

@dataclass()
class Substitution:
	type: str
	time: Optional[Union[int, Tuple[int, int]]]
	data: Union[
		SBST_Unknown,
		SBST_Substitution,
		SBST_Cancellation,
		SBST_Teacher_Decl,
		SBST_Teacher_Decl_Untagged
	]
	content: str

	def __init__(self, time: str, data: str):
		self.content = data
		for (name, klass) in type_map.items():
			if (res := klass._pattern.match(data)):
				self.type = name
				self.data = klass(*res.groups())
				break
		else:
			self.type = "unknown"
			self.data = SBST_Unknown()

		self.time = None
		if any((match := _time_regex.match(time)).groups()):
			if match.groups()[2]:
				self.time = int(match.groups()[2])
			else:
				self.time = tuple(map(int, match.groups()[:2]))

	def __repr__(self):
		fields = dataclasses.asdict(self)
		del fields["content"]
		fields.update(fields["data"])
		del fields["data"]

		repr_fmt = ", ".join(f"{k}={repr(v)}" for k,v in fields.items())
		return f"{self.__class__.__name__}({repr_fmt})"

	@staticmethod
	def fromHtmlElement(elem: html.HtmlElement) -> "Substitution":
		data = elem.xpath(".//div[@class='info']/span/text()") + [""]
		time = elem.xpath(".//div[@class='period']/span/text()") + [""]
		return Substitution(time[0], data[0])

@dataclass()
class SubstitutionUnion:
	type: str
	time: Optional[Union[int, Tuple[int, int]]]
	content: str
	group: Optional[str]
	subject_before: Optional[str]
	subject: str
	teacher_before: Optional[str]
	teacher: str
	comment: Optional[str]

	@staticmethod
	def saturate(sub: Substitution) -> "SubstitutionUnion":
		fields = dataclasses.asdict(sub)
		fields.update(fields["data"])
		del fields["data"]
		return fields

def trule(*args, **kwargs):
	today = datetime.today()
	_date = args[0]
	if _date < today:  # Past, cache forever
		return 1e18
	if _date == today and 6 <= datetime.now().hour < 18:  # Today, during lessons
		return 5 * 60
	if _date <= next_weekday(today):  # Before next school day
		return 30 * 60
	return 120 * 60  # Future

@pickle_cache(timeout_rule = trule)
def get_substitution_data(date_: date) -> Mapping[str, List[Substitution]]:
	resp = requests.post(
		"https://v-lo-krakow.edupage.org/substitution/server/viewer.js?__func=getSubstViewerDayDataHtml&lang=en",
		json = {
			"__args": [
				None,
				{
					"date": date_.strftime("%Y-%m-%d"),
					"mode": "classes"
				},
			],
			"__gsh": "00000000"
		}
	)

	dom = html.fromstring(resp.json()["r"])
	queries = dom.xpath(f"//div[@class='section print-nobreak']")
	if not queries: return []

	ret = {}

	for query in queries:
		klass = query.xpath(".//div[@class='header']/span/text()")
		if not klass:
			print(query)
			continue
		data = query.xpath(".//div[./div[@class='period'] and ./div[@class='info']]")
		ret[klass[0]] = [Substitution.fromHtmlElement(elem) for elem in data]

	return ret


