from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy import create_engine, select, func
from datetime import datetime, timedelta
from secrets import token_urlsafe
from hashlib import sha256
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import re
from typing import Literal
from enum import Enum


ROOM_STATUS = Literal["free", "marked", "busy", "lecture"]

DATE_PATTERN = re.compile(r"\d{2}\.\d{2}")
DATE_RANGE_PATTERN = re.compile(r"\d{2}\.\d{2}-\d{2}\.\d{2}")

RESET_TIMES = [
    "09:00", "10:25", "12:10", "13:45", "15:20", "16:55", "18:30", "20:00",
    "22:00", "00:01", "01:30", "03:00", "04:30", "06:00", "07:30"
]
RESET_TIMES_DTT = [datetime.strptime(t, '%H:%M') for t in RESET_TIMES]

ROOM_TYPE = Literal["lecture", "seminar", "chair", "lab"]

class RoomType(Enum):
    lecture = 0
    seminar = 1
    chair = 2
    lab = 3

WEEKDAYS = {
    1: "ПН",
    2: "ВТ",
    3: "СР",
    4: "ЧТ",
    5: "ПТ",
    6: "СБ",
    7: "ВС",
}

PS = {
    "01": "фркт",
    "02": "лфи",
    "03": "факт",
    "04": "фэфм",
    "05": "фпми",
    "06": "фбмф",
    "07": "кнт",
    "09": "фбвт",
    "13": "вшпи",
}

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

class Passwords(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str]
    expiration_date: Mapped[datetime]
    used: Mapped[bool]


class Events(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    building: Mapped[str]
    room: Mapped[str]
    time_start: Mapped[str]
    time_finish: Mapped[str]
    day: Mapped[int]


class Counter(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    count: Mapped[int]


class Room(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    building: Mapped[str]
    room: Mapped[str]
    room_type: Mapped[RoomType] = mapped_column(default="seminar")
    status: Mapped[str]
    status_description: Mapped[str]
    capacity: Mapped[int] = mapped_column(default=9)
    equipment: Mapped[str] = mapped_column(default="")


class DatabaseManager:
    EXPIRY_PERIOD = timedelta(days=5)

    def __init__(self, app: Flask):
        self.db = db
        db.init_app(app)
        self.app = app
        with app.app_context():
            db.create_all()

    def add_password(self, password: Passwords):
        self.clear_expired_passwords()
        self.db.session.add(password)
        self.db.session.commit()

    def check_password(self, password: str):
        if password is None:
            return False
        password_hash = sha256(password.encode()).hexdigest()
        password_query = db.session.scalars(
            select(Passwords)
            .filter(Passwords.password_hash == password_hash)
            .filter(Passwords.expiration_date > datetime.now())
            .filter(Passwords.used != True)
        ).one_or_none()
        if password_query:
            password_query.used = True
            self.db.session.commit()
            return True
        return False

    def verify_password(self, password: str):
        if password is None:
            return False
        password_hash = sha256(password.encode()).hexdigest()
        password_query = db.session.scalars(
            select(Passwords)
            .filter(Passwords.password_hash == password_hash)
            .filter(Passwords.expiration_date > datetime.now())
        ).one_or_none()
        if password_query:
            return True
        return False

    def generate_password(self):
        self.clear_expired_passwords()
        expiration_date = datetime.now() + self.EXPIRY_PERIOD
        password = token_urlsafe(6)
        password_hash = sha256(password.encode("utf-8")).hexdigest()
        self.db.session.add(Passwords(password_hash=password_hash, expiration_date=expiration_date, used=False))
        self.db.session.commit()
        print(password)
        return password

    def clear_expired_passwords(self):
        pwd = self.db.session.execute(
            select(Passwords)
            .where(Passwords.expiration_date < datetime.now())
        ).scalars().all()
        for p in pwd:
            self.db.session.delete(p)
        self.db.session.commit()

    def get_events(self, date: str):
        date_dtt = datetime.strptime(date, '%Y-%m-%d')
        weekday = date_dtt.weekday() + 1
        res = self.db.session.scalars(select(Events).where(Events.day == weekday)).all()
        return list(res)

    def get_all_rooms(self, building: str):
        res = self.db.session.scalars(select(Room.room).where(Room.building==building)).all()
        return list(res)

    def get_events_by_query(self, query: str):
        """Parse search query and return ordered list of events that fully or partially match the query"""
        all_events: "list[Events]" = db.session.scalars(select(Events)).all()
        res: "list[tuple[Events, int]]" = []
        query_word_set = set([w.lower() for w in query.split()])
        group = re.search(r"[бмс]\d\d-\d\d\d", query.lower())
        text="&*!@$&!@^$*"
        if group:
            self.counter_plus_one("group_in_query")
            text = group.group(0)
            ps = PS[text[1:3]]
            year = str(5-int(text[4]))
            query_word_set.update([
                ps, year, year+"к", year+"к."
            ])
        for event in all_events:
            room = (event.room[1:] if event.room.startswith('!') else event.room).lower()
            events_word_set = set([w.lower() for w in event.description.split()]
                + [
                    event.building.lower(), room, event.description.lower(),
                    event.building.lower()+room,
                    room+event.building.lower(),
                ]
            )
            pattern = re.compile(r"\d{2}\.\d{2}")
            dates = re.findall(pattern, event.description)
            if dates:
                today = datetime.now()
                dates_dtt = [datetime.strptime(date, '%d.%m') for date in dates if not date.startswith('00') and not date.endswith('00')]
                if dates_dtt:
                    maxdate = max(dates_dtt)
                    if maxdate < today:
                        continue
            start_time = datetime.strptime(event.time_start, '%H:%M')
            finish_time = datetime.strptime(event.time_finish, '%H:%M')
            time_mentions = re.findall(r'\d{1,2}:\d{2}', query)
            for time_mention in time_mentions:
                time_mention_dtt = datetime.strptime(time_mention, '%H:%M')
                if start_time <= time_mention_dtt <= finish_time:
                    query_word_set.add(event.time_start)
                    events_word_set.add(event.time_start)
                    break
            events_word_set.add(WEEKDAYS[event.day].lower())
            if query_word_set & events_word_set or query.lower() in event.description.lower():
                match_count = len(query_word_set & events_word_set)
                res.append((event, match_count + int(text in event.description.lower())))
        res.sort(key=lambda x: x[1], reverse=True)
        return res
    
    def get_free_rooms(self, time: str, date: str):
        date_dtt = datetime.strptime(datetime.strptime(date, '%Y-%m-%d').strftime("%d.%m"), "%d.%m")
        weekday = date_dtt.weekday() + 1
        time_dtt = datetime.strptime(time, '%H:%M')
        res = db.session.scalars(select(Events).where(Events.day == weekday)).all()
        all_rooms = set([
            (e.room, e.building)
            for e in res
        ])
        def event_at_time(event: Events, time_dtt: datetime, date_dtt: datetime):
            start_time = datetime.strptime(event.time_start, '%H:%M')
            finish_time = datetime.strptime(event.time_finish, '%H:%M')
            date_str = date_dtt.strftime('%d.%m')
            dates = re.findall(DATE_PATTERN, event.description)
            date_range = re.search(DATE_RANGE_PATTERN, event.description)
            if date_range:
                date_start, date_finish = date_range.group().split('-')
                start_dtt = datetime.strptime(date_start, '%d.%m')
                finish_dtt = datetime.strptime(date_finish, '%d.%m')
                return start_time <= time_dtt <= finish_time and start_dtt <= date_dtt <= finish_dtt
            if not dates:
                return start_time <= time_dtt <= finish_time
            return start_time <= time_dtt <= finish_time and date_str in dates
        busy_rooms = set([
            (event.room, event.building)
            for event in db.session.scalars(select(Events).where(Events.day == weekday)).all()
            if event_at_time(event, time_dtt, date_dtt)
        ])
        return sorted(list(all_rooms - busy_rooms), key=lambda x: x[1]+x[0])

    def counter_plus_one(self, name: str):
        counter = db.session.scalars(select(Counter).where(Counter.name == name)).one_or_none()
        if counter:
            counter.count += 1
        else:
            db.session.add(Counter(name=name, count=1))
        db.session.commit()

    def get_all_counters(self):
        return [(c.name, c.count) for c in db.session.scalars(select(Counter)).all()]
    
    def fill_rooms(self):
        with self.app.app_context():
            Base.metadata.drop_all(bind=db.engine, tables=[Room.__table__])
            Base.metadata.create_all(bind=db.engine, tables=[Room.__table__])
            prevrooms = db.session.scalars(select(Room)).all()
            if prevrooms:
                for room in prevrooms:
                    db.session.delete(room)
                db.session.commit()
            rooms = db.session.scalars(select(Events.room+" "+Events.building).distinct()).all()
            print(len(rooms))
            for room in rooms:
                try:
                    *r, b = room.split()
                    r  = "_".join(r)
                except ValueError:
                    print(room)
                    raise
                db.session.add(Room(building=b, room=r, status="free", status_description=""))
            db.session.commit()

    def external_room_status_update(self):
        with self.app.app_context():
            self.set_room_statuses()

    def get_today_events(self, room: str, building: str):
        now = datetime.now()
        weekday = now.weekday() + 1
        events = db.session.scalars(
            select(Events)
            .where(Events.room == room)
            .where(Events.building == building)
            .where(Events.day == weekday)
        ).all()
        return events

    def set_room_statuses(self):
        MAX_LEN = 45
        rooms = db.session.scalars(select(Room)).all()
        now = datetime.strptime(datetime.now().strftime('%H:%M'), '%H:%M')
        today = datetime.today().strftime("%d.%m")
        today_dtt = datetime.strptime(today, "%d.%m")
        for room in rooms:
            room_events = db.session.scalars(
                select(Events)
                .where(Events.room == room.room)
                .where(Events.building == room.building)
                .where(Events.day == datetime.today().weekday() + 1)
            ).all()
            for event in room_events:
                start_time = datetime.strptime(event.time_start, '%H:%M')
                for i in range(len(RESET_TIMES_DTT) - 1):
                    if RESET_TIMES_DTT[i] <= start_time < RESET_TIMES_DTT[i + 1]:
                        start_time = RESET_TIMES_DTT[i]
                        break
                finish_time = datetime.strptime(event.time_finish, '%H:%M')
                dates = re.findall(DATE_PATTERN, event.description)
                date_range = re.search(DATE_RANGE_PATTERN, event.description)
                if date_range:
                    date_start, date_finish = date_range.group().split('-')
                    start_dtt = datetime.strptime(date_start, '%d.%m')
                    finish_dtt = datetime.strptime(date_finish, '%d.%m')
                    if not start_dtt <= today_dtt <= finish_dtt:
                        continue
                if dates and today not in dates:
                    continue
                if start_time <= now <= finish_time:
                    room.status = "busy"
                    long_description = "..." if len(event.description) > MAX_LEN else ""
                    room.status_description = event.description[:MAX_LEN] + long_description
                    break
            else:
                start_times = sorted([datetime.strptime(event.time_start, '%H:%M') for event in room_events])
                closest = None
                for st in start_times:
                    if st <= now:
                        continue
                    closest = st
                    break
                desc = "до " + closest.strftime('%H:%M') if closest else "до конца дня"
                room.status_description = desc
                if "!" in room.room:
                    room.status = "lecture"
                else:
                    room.status = "free"
        db.session.commit()

    def get_room_statuses(self):
        return db.session.scalars(select(Room)).all()

    def get_room_status(self, building: str, room: str):
        all_roooms = self.get_all_rooms(building)
        if room not in all_roooms:
            raise ValueError("Room not found")
        return db.session.scalars(
            select(Room)
            .where(Room.building == building)
            .where(Room.room == room)
        ).one()

    def set_room_status(self, building: str, room: str, status: ROOM_STATUS, description: str):
        room_status = db.session.scalars(
            select(Room)
            .where(Room.building == building)
            .where(Room.room == room)
        ).one()
        if room_status.status in ["busy", "lecture"]:
            raise ValueError("Room is busy or lecture, cannot change status")
        if status == "marked" and room_status.status == "marked":
            raise ValueError("Room is already marked")
        room_status.status = status
        room_status.status_description = description
        db.session.commit()
        return room_status

    def room_status_plus_one(self, building: str, room: str):
        room_status = db.session.scalars(
            select(Room)
            .where(Room.building == building)
            .where(Room.room == room)
        ).one()
        if room_status.status in ["busy", "lecture", "free"]:
            raise ValueError("Room is busy, free or lecture, cannot change status")
        desc = room_status.status_description
        plim, unav, loud = desc.split("|")
        plim = str(int(plim) + 1)
        desc = f"{plim}|{unav}|{loud}"
        room_status.status_description = desc
        db.session.commit()
        return room_status

    def unmark_room(self, building: str, room: str):
        now = datetime.now()
        now_t = datetime.strptime(now.strftime('%H:%M'), '%H:%M')
        events_starts = db.session.scalars(
            select(Events.time_start)
            .where(Events.room == room)
            .where(Events.building == building)
            .where(Events.day == now.weekday() + 1)
        ).all()
        room_status = db.session.scalars(
            select(Room)
            .where(Room.building == building)
            .where(Room.room == room)
        ).one()
        if room_status.status in ["busy", "lecture"]:
            raise ValueError("Room is busy or lecture, cannot change status")
        start_times = sorted([datetime.strptime(st, '%H:%M') for st in events_starts])
        for st in start_times:
            if st <= now_t:
                continue
            closest = st
            break
        else:
            closest = None
        desc = "до " + closest.strftime('%H:%M') if closest else "до конца дня"
        room_status.status_description = desc
        room_status.status = "free"
        return room_status
        
        