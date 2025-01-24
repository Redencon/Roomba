from functools import wraps
from sql import DatabaseManager, ROOM_STATUS, WEEKDAYS
import flask
import diskcache as dc
import traceback
from dash import html

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

BUILDING_SECTIONS = {
    "all": ['ГК', 'ЛК', 'Квант', 'КПМ', 'Цифра', 'Арктика', 'БК', 'УПМ', 'КМО'],
    "boat": ["КПМ", "ЛК"],
    "ulk": ["Арктика", "Цифра"],
    "prof": ["УПМ", "БК"],
}

BUILDING_NAVIGATION = [
    {"label": "Все", "value": "all", "style": {"color": "white", "font-weight": "800", "background-image": "linear-gradient(130deg, #6678B9, #ED6A66, #FAB62F)"}},
    {"label": "ГК", "value": "ГК", "style": {"color": "#00A19A", "font-weight": "800"}},
    {"label": "Квант", "value": "Квант", "style": {"color": "#F7A823", "font-weight": "800"}},
    {"label": "ЛК+КПМ", "value": "boat", "style": {"color": "white", "font-weight": "800", "background-image": "linear-gradient(130deg, #1E67AC, #6F4822)"}},
    {"label": "ЛК", "value": "ЛК", "style": {"color": "#6F4822", "font-weight": "800", "padding-left": "2.5rem"}},
    {"label": "КПМ", "value": "КПМ", "style": {"color": "#1E67AC", "font-weight": "800", "padding-left": "2.5rem"}},
    {"label": "УЛК", "value": "ulk", "style": {"color": "white", "font-weight": "800", "background-image": "linear-gradient(130deg, #8C7EB8, #B43D3E)"}},
    {"label": "Арктика", "value": "Арктика", "style": {"color": "#8C7EB8", "font-weight": "800", "padding-left": "2.5rem"}},
    {"label": "Цифра", "value": "Цифра", "style": {"color": "#B43D3E", "font-weight": "800", "padding-left": "2.5rem"}},
    {"label": "УПМ+БК", "value": "prof", "style": {"color": "white", "font-weight": "800", "background-image": "linear-gradient(130deg, #AF447F, #87B145)"}},
    {"label": "УПМ", "value": "УПМ", "style": {"color": "#AF447F", "font-weight": "800", "padding-left": "2.5rem"}},
    {"label": "БК", "value": "БК", "style": {"color": "#87B145", "font-weight": "800", "padding-left": "2.5rem"}},
    {"label": "КМО", "value": "КМО", "style": {"color": "#F47742", "font-weight": "800"}},
]

EQUIPMENT_OPTIONS = [
    "Маркерная доска", "Меловая доска", "Электронная доска", "Проектор", "Компьютер", "Кондиционер",
]

def log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            with open("/var/www/u2906537/data/www/folegle.ru/report.log", 'w') as f:
                f.write(traceback.format_exc())
            raise
    return wrapper


cache = dc.Cache("cache")
server = flask.Flask(__name__)
with open("keys/SQL") as f:
    sql_url = f.read().strip()
server.config['SQLALCHEMY_DATABASE_URI'] = sql_url
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
server.secret_key = "MyNameIsNotDiana"
dbm = DatabaseManager(server)


def building_span(building, addition=""):
    return html.Span(building+addition, style={
            'color': BUILDING_PALETTES[building][0],
            'font-weight': '700',
        })


def track_usage(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            dbm.counter_plus_one(name)
            return func(*args, **kwargs)
        return wrapper
    return decorator