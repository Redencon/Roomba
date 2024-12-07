from functools import wraps
from sql import DatabaseManager, ROOM_STATUS, WEEKDAYS
import flask
import diskcache as dc

BUILDINGS = [
    'ГК', 'ЛК', 'Квант', 'КПМ', 'Цифра', 'Арктика', 'БК', 'УПМ', 'КМО'
]

BUILDINGS_EN = {
    'ГК': 'GK', 'ЛК': 'LK', 'Квант': 'Quant', 'КПМ': 'KPM',
    'Цифра': 'Cifra', 'Арктика': 'Arktika', 'БК': 'BK', 'УПМ': 'UPM',
    'КМО': 'KMO'
}

BUILDING_PALETTES = {
    'ГК': ["#00A19A", "#0BC1B8", "#00635E"],
    'ЛК': ["#6F4822", "#A86C34", "#4C3117"],
    'Квант': ["#F7A823", "#CCBF30", "#AF761A"],
    'КПМ': ["#1E67AC", "#2B92F2", "#123F68"],
    'Цифра': ["#B43D3E", "#E54E50", "#7A292A"],
    'Арктика': ["#8C7EB8", "#AB9AE0", "#675D87"],
    'БК': ["#87B145", "#A6D854", "#678734"],
    'УПМ': ["#AF447F", "#E057A2", "#7F315C"],
    'КМО': ["#F47742", "#FF9C75", "#B55830"],
    'Roomba': ["#6678B9", "#ED6A66", "#FAB62F"]
}


cache = dc.Cache("cache")
server = flask.Flask(__name__)
with open("keys/SQL") as f:
    sql_url = f.read().strip()
server.config['SQLALCHEMY_DATABASE_URI'] = sql_url
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
server.secret_key = "MyNameIsNotDiana"
dbm = DatabaseManager(server)


def track_usage(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            dbm.counter_plus_one(name)
            return func(*args, **kwargs)
        return wrapper
    return decorator