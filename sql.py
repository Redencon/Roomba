from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy import create_engine, select
from datetime import datetime, timedelta
from secrets import token_urlsafe
from hashlib import sha256
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import re


WEEKDAYS = {
    1: "ПН",
    2: "ВТ",
    3: "СР",
    4: "ЧТ",
    5: "ПТ",
    6: "СБ",
    7: "ВС",
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


class DatabaseManager:
    EXPIRY_PERIOD = timedelta(days=1)

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
        all_events: "list[Events]" = db.session.scalars(select(Events)).all()
        res: "list[tuple[Events, int]]" = []
        for event in all_events:
            events_word_set = set([w.lower() for w in event.description.split()]
                + [
                    event.building.lower(), event.room.lower(), event.description.lower(),
                    event.building.lower()+event.room.lower(),
                    event.room.lower()+event.building.lower(),
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
            query_word_set = set([w.lower() for w in query.split()])
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
                res.append((event, match_count))
        res.sort(key=lambda x: x[1], reverse=True)
        return res