from datetime import date, timedelta

FMT = "%Y-%m-%d"

def monday_before(x: date = date.today()) -> date:
	return x + timedelta(days=-x.weekday())

def friday_after(x: date = date.today()) -> date:
	return monday_before(x) + timedelta(days=4)

def next_weekday(x: date) -> date:
	tomorrow = x + timedelta(days=1)
	if tomorrow.weekday() >= 5:
		tomorrow += timedelta(days=7-tomorrow.weekday())
	return tomorrow
