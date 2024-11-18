from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy import create_engine, select
from datetime import datetime, timedelta
from secrets import token_urlsafe
from hashlib import sha256


class Base(DeclarativeBase):
    pass


class Password(Base):
    __tablename__ = "passwords"

    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str]
    expiration_date: Mapped[datetime]


class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    building: Mapped[str]
    room: Mapped[str]
    time_start: Mapped[str]
    time_finish: Mapped[str]
    day: Mapped[int]


class DatabaseManager:
    EXPIRY_PERIOD = timedelta(days=15)

    def __init__(self, url, username, password):
        self.engine = create_engine(url)
        Base.metadata.create_all(self.engine)

    def add_password(self, password: Password):
        with Session(self.engine) as session:
            session.add(password)
            session.commit()

    def check_password(self, password: str):
        password_hash = sha256(password.encode()).hexdigest()
        with Session(self.engine) as session:
            query = session.scalars(
                select(Password.password_hash)
                .where(Password.password_hash == password_hash)
                .where(Password.expiration_date > datetime.now())
            )
            if query.one_or_none():
                return True
            return False

    def generate_password(self):
        expiration_date = datetime.now() + self.EXPIRY_PERIOD
        password = token_urlsafe(16)
        password_hash = sha256(password.encode("utf-8")).hexdigest()
        with Session(self.engine) as session:
            session.add(Password(password_hash=password_hash, expiration_date=expiration_date))
            session.commit()
        return password
        

    def clear_expired_passwords(self):
        with Session(self.engine) as session:
            old_passwords = session.scalars(
                select(Password)
                .where(Password.expiration_date < datetime.now())
            ).all()
            for password in old_passwords:
                session.delete(password)
            session.commit()

    def get_events(self, date: str):
        date_dtt = datetime.strptime(date, '%Y-%m-%d')
        weekday = date_dtt.weekday() + 1
        with Session(self.engine) as session:
            events = session.scalars(
                select(Event)
                .where(Event.day == weekday)
            ).all()
        return events