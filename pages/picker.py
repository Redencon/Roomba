from dash import html, dcc, Input, Output, State, MATCH, ALL, get_asset_url
from dash import callback_context, clientside_callback, register_page, callback
from utils import BUILDINGS, BUILDING_PALETTES, building_span, dbm
import dash_bootstrap_components as dbc
from datetime import datetime


register_page(__name__)


BUILDING_FLOORS = {
    "ГК": [1, 2, 4, 5],
    "ЛК": [1, 2, 3, 4, 5],
    "Квант": [2, 3],
    "КПМ": [1, 2, 3, 6, 7, 8, 9],
    "Цифра": [2, 3, 4, 5],
    "Арктика": [4],
    "БК": [1, 2],
    "УПМ": [2],
    "КМО": [],
}

NAMED_ROOM_FLOORS = {
    "!Б.Физ.": 5,
    "!Б.Хим.": 5,
    "!Гл.Физ.": 5,
    "!Акт.зал": 2
}


layout = dbc.Container([
    html.H1("Подбор аудитории", className="my-4 text-center"),
    # Picking room using filters
    # Known room criteria:
    # Location: building, floor
    # Capacity: enough to hold, not too much (less than x7?)
    # Equipment: see equipment list <- full list yet unknown
    # With criteria set, two options for seeking:
    # 1. Find any room in a selected time frame
    # 2. Find time frame for a selected room
    # All options are available, but lacking fields will be wildcards.
    # RESULTS
    # Singular result is a time slot for a specific room
    dbc.Row([
        dbc.Col([
            dbc.FormText("Корпус"),
            dcc.Dropdown(
                id="picker-building",
                options=(
                    [{"label": html.Span("любой", className="fw-bold"), "value": "any"}]
                    +[{"label": building_span(b), "value": b} for b in BUILDINGS[:-1]]
                ),
                value="any", clearable=False),
        ], width=6, md=3),
        dbc.Col([
            dbc.FormText("Этаж"),
            dcc.Dropdown(
                id="picker-floor",
                clearable=False
            ),
        ], width=6, md=3),
        dbc.Col([
            dbc.FormText("Тип"),
            dcc.Dropdown([
                {"label": "Лекционная", "value": "lecture"},
                {"label": "Семинарская", "value": "seminar"},
                {"label": "Компьютерная", "value": "computer"},
                {"label": "Кафедральная", "value": "chair", "disabled": True},
            ], value="lecture", id="picker-type", clearable=False),
        ], width=6, md=4),
        dbc.Col([
            dbc.FormText("Участников"),
            dbc.Input(type="number", min=2, max=100, step=1, value=9, id="picker-capacity"),
        ], width=6, md=2),
        dbc.Col([
            dbc.FormText("Дата"),html.Br(),
            dcc.DatePickerSingle(
                id="picker-date",
                min_date_allowed=datetime.now().date(),
                initial_visible_month=datetime.now().date(),
                date=datetime.now().date(),
                display_format="YYYY-MM-DD",
            ),                                       
        ], width=6, md=3),
        dbc.Col([
            dbc.FormText("Время"),
            dcc.Input(type="time", id="picker-time", value=datetime.now().strftime("%H:%M")),
        ]),
        dbc.Col([
            dbc.FormText("Оборудование"),
            dcc.Dropdown(options=["меловая доска", "проектор", "электронная доска"], multi=True, id="picker-equipment"),
        ], width=7, md=4),
        dbc.Col([
            dbc.Button("Подобрать", id="picker-submit", color="primary"),
        ], width=5, md=2, class_name="d-flex align-items-end"),
    ]), # Filters
    html.Hr(),
    dbc.Row(id="picker-results", class_name="row-cols-2 row-cols-md-3 row-cols-xl-4 g-2"), # Results+
], class_name="col-11 col-lg-9 col-xxl-6")

@callback(
    Output("picker-floor", "options"),
    Output("picker-floor", "value"),
    Input("picker-building", "value")
)
def update_floors(building):
    any_floor = {"label": "любой", "value": "any"}
    if building == "any":
        return [any_floor], "any"
    return [any_floor]+[{"label": str(f), "value": f} for f in BUILDING_FLOORS[building]], "any"

@callback(
    Output("picker-capacity", "valid"),
    Output("picker-submit", "disabled"),
    Input("picker-capacity", "value"),
)
def validate_capacity(capacity):
    if not isinstance(capacity, int):
        return False, True
    if capacity < 2 or capacity > 120:
        return False, True
    return True, False

@callback(
    Output("picker-results", "children"),
    Input("picker-submit", "n_clicks"),
    State("picker-building", "value"),
    State("picker-floor", "value"),
    State("picker-type", "value"),
    State("picker-date", "date"),
    State("picker-time", "value"),
    State("picker-equipment", "value"),
    State("picker-capacity", "value"),
    prevent_initial_call=True
)
def show_picker_results(n_clicks, building, floor, room_type, date, time, equipment, capacity):
    free_rooms = dbm.get_free_rooms_picker(building, room_type, date, time)
    equipment = equipment or []
    if floor != "any":
        other_rooms = []
        for room in free_rooms:
            if room.room in NAMED_ROOM_FLOORS:
                if NAMED_ROOM_FLOORS[room.room] == floor:
                    other_rooms.append(room)
                continue
            if int(room.room.strip("!")[0]) == floor:
                other_rooms.append(room)
            # else:
                # print(f"'{room.room}'", f'"{int(room.room.strip("!")[0])}"', f"'{floor}'")
        free_rooms = other_rooms
    eq_set = set(equipment)
    free_rooms = [
        room for room in free_rooms
        if room.capacity >= capacity
        and eq_set.issubset(room.equipment)
    ]
    free_rooms.sort(key=lambda r: r.capacity)
    room_desc: dict[tuple[str, str], str] = {}
    for room in free_rooms:
        status, desc = dbm.room_status(room.building, room.room, date, time)
        if status != "free":
            free_rooms.remove(room)
            continue
        room_desc[(room.building, room.room)] = desc
    room_desc = {
        (room.building, room.room): dbm.room_status(room.building, room.room, date, time)[1]
        for room in free_rooms
    }
    return [
        dbc.Col(dbc.Card([
            dbc.CardHeader(building_span(room.building, room.room.strip("!"))),
            dbc.CardBody([
                html.P(f"Оборудование: {', '.join(room.equipment) or 'нет'}", className="mb-1"),
                html.P(["Вместимость: ", html.Strong(str(room.capacity)), " человек"], className="mb-1"),
                html.P(["Свободно ", room_desc[(room.building, room.room)]], className="mb-1"),
            ]),
        ]))
        for room in free_rooms
    ]
        