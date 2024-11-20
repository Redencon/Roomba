from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy import create_engine, select
from datetime import datetime, timedelta
from secrets import token_urlsafe
from hashlib import sha256
from flask_sqlalchemy import SQLAlchemy
from flask import Flask


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

class Passwords(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str]
    expiration_date: Mapped[datetime]


class Events(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    building: Mapped[str]
    room: Mapped[str]
    time_start: Mapped[str]
    time_finish: Mapped[str]
    day: Mapped[int]


class DatabaseManager:
    EXPIRY_PERIOD = timedelta(days=15)

    def __init__(self, app: Flask):
        self.db = db
        db.init_app(app)
        with app.app_context():
            db.create_all()

    def add_password(self, password: Passwords):
        with Session(self.engine) as session:
            session.add(password)
            session.commit()

    def check_password(self, password: str):
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
        password = token_urlsafe(16)
        password_hash = sha256(password.encode("utf-8")).hexdigest()
        db.session.add(Passwords(password_hash=password_hash, expiration_date=expiration_date))
        db.session.commit()
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
        res: "list[Events]" = []
        for event in all_events:
            events_word_set = (
                set([w.lower() for w in event.description.split()])
                | set([w.lower() for w in event.room.split()])
                | set([w.lower() for w in event.building.split()])
                | set([event.building.lower()+event.room.lower()])
            )
            query_word_set = set([w.lower() for w in query.split()])
            if query_word_set & events_word_set or query.lower() in event.description.lower():
                match_count = len(query_word_set & events_word_set)
                res.append((event, match_count))
        res.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in res]