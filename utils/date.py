from datetime import date, timedelta

FMT = "%Y-%m-%d"

def monday_before(x: date = date.today()) -> date:
	return x + timedelta(days=-x.weekday())

def friday_after(x: date = date.today()) -> date:
	return monday_before(x) + timedelta(days=4)