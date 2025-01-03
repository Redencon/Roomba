from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy import create_engine, select
from datetime import datetime, timedelta
from secrets import token_urlsafe
from hashlib import sha256
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import re


DATE_PATTERN = re.compile(r"\d{2}\.\d{2}")
DATE_RANGE_PATTERN = re.compile(r"\d{2}\.\d{2}-\d{2}\.\d{2}")

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


class DatabaseManager:
    EXPIRY_PERIOD = timedelta(days=5)

    def __init__(self, app: Flask):
        self.db = db
        db.init_app(app)
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
        db.session.add(Passwords(password_hash=password_hash, expiration_date=expiration_date, used=False))
        db.session.commit()
        print(password)
        return password

    def clear_expired_passwords(self):
        pwd = db.session.execute(
            select(Passwords)
            .where(Passwords.expiration_date < datetime.now())
        ).scalars().all()
        for p in pwd:
            db.session.delete(p)
        db.session.commit()

    def get_events(self, date: str):
        date_dtt = datetime.strptime(date, '%Y-%m-%d')
        weekday = date_dtt.weekday() + 1
        res = db.session.scalars(select(Events).where(Events.day == weekday)).all()
        return list(res)

    def get_all_rooms(self, building: str):
        res = db.session.scalars(select(Events.room).where(Events.building==building).distinct()).all()
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
        date_dtt = datetime.strptime(date, '%Y-%m-%d')
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