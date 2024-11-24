from icalendar import Calendar
from datetime import datetime, date, timedelta, time, timezone
import requests as rqt
from sql import Events, Base
from sqlalchemy import engine as sql_engine, select
from sqlalchemy.orm import Session
import json

WEEKS = 3
week_start = datetime.combine(date.today() - timedelta(days=date.today().weekday()), time(0, 0), tzinfo=timezone(timedelta(hours=3)))
week_end = week_start + timedelta(days=7*WEEKS-1)

with open("keys/SQL") as f:
    sql_url = f.read().strip()

with open("data/calendars.json", encoding="utf-8") as f:
    calendars = json.load(f)

engine = sql_engine.create_engine(sql_url)
Base.metadata.create_all(engine)

BUILDING = "КМО"

# Gather events from all iCal calendars
events_this_week = []
for room, url in calendars.items():
    summaries = {}
    response = rqt.get(url)
    calendar = Calendar.from_ical(response.content)
    for component in calendar.walk():
        if component.name != "VEVENT":
            continue
        summary = component.get('summary')
        start = component.get('dtstart').dt
        start_date = start.strftime('%d.%m')
        start_time = start.strftime('%H:%M')
        if component.get('dtend') is None:
            continue
        end = component.get('dtend').dt
        end_date = end.strftime('%d.%m')
        end_time = end.strftime('%H:%M')
        skey = summary+"@"+str(start.weekday()+1)
        if isinstance(start, date):
            start = datetime.combine(start, time(0, 0), tzinfo=timezone(timedelta(hours=3)))
        if not(week_start <= start <= week_end):
            rr = component.get("rrule")
            if rr is None:
                continue
            until = rr.get("until")
            if until and isinstance(until[0], date):
                until[0] = datetime.combine(until[0], time(0, 0), tzinfo=timezone(timedelta(hours=3)))
            if rr.get("until") and rr.get("until")[0] < week_start:
                continue
            event = {
                "description": " ".join([summary]),
                "time_start": start_time,
                "time_finish": end_time,
                "day": start.weekday()+1,
                "room": room,
                "building": BUILDING,
            }
            events_this_week.append(event)
            continue
        if start_date != end_date:
            continue
        if skey in summaries:
            event = summaries[skey]
            event["description"] = " ".join([start_date, event["description"]])
            if len(event["description"].split(" | ")[0].split(" ")) == WEEKS:
                try:
                    event["description"] = event["description"].split(" | ")[1]
                except IndexError:
                    print(event["description"])
                    raise
            continue
        description = " | ".join([start_date, summary])
        event = {
            "description": description,
            "time_start": start_time,
            "time_finish": end_time,
            "day": start.weekday()+1,
            "room": room,
            "building": BUILDING,
        }
        summaries[skey] = event
        events_this_week.append(event)

# Merge repeating events?
# If event is repeated its description should list all dates
# If event repeats every week during the specified period, no date should be listed
# NOT IMPLEMENTED for now (no repeating events spotted so far)

# with open("data/events.json", "w", encoding="utf-8") as f:
#     json.dump(events_this_week, f, indent=4, ensure_ascii=False)

with Session(engine) as session:
    # Remove KMO events from the database
    kmo_events = session.scalars(select(Events).where(Events.building == BUILDING)).all()
    for event in kmo_events:
        session.delete(event)
    session.commit()

    # Add KMO events from iCal to the database
    for event in events_this_week:
        session.add(Events(**event))
    session.commit()
