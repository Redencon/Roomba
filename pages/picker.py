from dash import html, dcc, Input, Output, State, MATCH, ALL, get_asset_url
from dash import callback_context, clientside_callback, register_page, callback
from utils import BUILDINGS, BUILDING_PALETTES, building_span, dbm, EQUIPMENT_OPTIONS
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import json
import flask


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
            dcc.Dropdown(options=EQUIPMENT_OPTIONS, multi=True, id="picker-equipment"),
        ], width=7, md=4),
        dbc.Col([
            dbc.Button("Подобрать", id="picker-submit", color="primary"),
        ], width=5, md=2, class_name="d-flex align-items-end"),
        dbc.Col(
            dbc.Row([
                dbc.Col([], width=0, md=8),
                dbc.Col(dbc.Button("Мои события", id="my-events-button", color="secondary"), width=12, md=4)
            ]),
        width=12)
    ], class_name="g-2"), # Filters
    html.Hr(),
    dbc.Row(id="picker-results", class_name="row-cols-2 row-cols-md-3 row-cols-xl-4 g-2"), # Results+
    dbc.Modal([  # Adding unconfirmed events for a selected room
        dbc.ModalHeader("Создать событие"),
        dbc.ModalBody(dbc.Row([
            dbc.Col(dbc.Input(type="text", id="event-building", value="", disabled=True), width=6),
            dbc.Col(dbc.Input(type="text", id="event-room", value="", disabled=True), width=6),
            dbc.Col(dbc.Label("Название"), width=4),
            dbc.Col(dbc.Input(type="text", id="event-name"), width=8),
            dbc.Col(dbc.Label("Время начала"), width=4),
            dbc.Col(dbc.Input(type="time", id="event-start", value=datetime.now().strftime("%H:%M")), width=3),
            dbc.Col(dbc.DropdownMenu(
                [
                    dbc.DropdownMenuItem("1 пара", id={"type": "event-pair-start", "value": "09:00"}),
                    dbc.DropdownMenuItem("2 пара", id={"type": "event-pair-start", "value": "10:45"}),
                    dbc.DropdownMenuItem("3 пара", id={"type": "event-pair-start", "value": "12:20"}),
                    dbc.DropdownMenuItem("4 пара", id={"type": "event-pair-start", "value": "13:55"}),
                    dbc.DropdownMenuItem("5 пара", id={"type": "event-pair-start", "value": "15:30"}),
                    dbc.DropdownMenuItem("6 пара", id={"type": "event-pair-start", "value": "17:05"}),
                    dbc.DropdownMenuItem("7 пара", id={"type": "event-pair-start", "value": "18:35"}),
                ],
                id="event-pair-start",
                label="Выбрать пару",
            ), width=5),
            dbc.Col(dbc.Label("Время окончания"), width=4),
            dbc.Col(dbc.Input(type="time", id="event-end", value=(datetime.now() + timedelta(hours=1)).strftime("%H:%M")), width=3),
            dbc.Col(dbc.DropdownMenu(
                [
                    dbc.DropdownMenuItem("1 пара", id={"type": "event-pair-end", "value": "10:25"}),
                    dbc.DropdownMenuItem("2 пара", id={"type": "event-pair-end", "value": "12:10"}),
                    dbc.DropdownMenuItem("3 пара", id={"type": "event-pair-end", "value": "13:45"}),
                    dbc.DropdownMenuItem("4 пара", id={"type": "event-pair-end", "value": "15:20"}),
                    dbc.DropdownMenuItem("5 пара", id={"type": "event-pair-end", "value": "16:55"}),
                    dbc.DropdownMenuItem("6 пара", id={"type": "event-pair-end", "value": "18:30"}),
                    dbc.DropdownMenuItem("7 пара", id={"type": "event-pair-end", "value": "20:00"}),
                ],
                id="event-pair-end",
                label="Выбрать пару",
            ), width=5),
            dbc.Col(dbc.Label("Дата"), width=4),
            dbc.Col(dcc.DatePickerSingle(
                id="event-date",
                min_date_allowed=datetime.now().date(),
                max_date_allowed=datetime.now().date() + timedelta(days=60),
                initial_visible_month=datetime.now().date(),
                    date=datetime.now().date(),
                    display_format="YYYY-MM-DD",
                ), width=4,
                style = {"border-radius": "var(--bs-border-radius)"}
            ),
            dbc.Col(dbc.Button("Проверить", id="event-check", color="secondary"), width=4),
            dbc.Col(dbc.Label("Участников"), width=4),
            dbc.Col(dbc.Input(type="number", min=2, max=100, step=1, value=9, id="event-capacity"), width=8),
            dbc.Col(dbc.Label("Почта для связи"), width=4),
            dbc.Col(dbc.Input(type="email", id="event-email"), width=8),
            dbc.Col(dbc.Label("Телефон"), width=4),
            dbc.Col(dbc.Input(type="tel", id="event-phone"), width=8),
            dbc.Col(dbc.Label("Комментарий"), width=4),
            dbc.Col(dbc.Textarea(id="event-comment"), width=8),
            dbc.Col(dbc.Alert(id="event-check-alert", color="danger", is_open=False), width=12),
        ], class_name="g-2")),
        dbc.ModalFooter(dbc.Row([
            dbc.Col([
                dbc.Button("Создать", id="event-submit", color="primary"),
            ], width=6),
            dbc.Col([
                dbc.Button("Отменить", id="event-cancel", color="secondary"),
            ], width=6),
        ]))
    ], id="event-modal", is_open=False),
    dbc.Modal([
        # My events modal
        # Lists all unconfirmed events of the current user
        dbc.ModalHeader("Мои события"),
        dbc.ModalBody(id="my-events-body"),
        dbc.ModalFooter(dbc.Button("Отменить", id="my-events-cancel", color="secondary", disabled=True)),
        dcc.Store(id="my-events-chosen-id", data=""),
    ], id="my-events-modal", is_open=False)
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

clientside_callback(
    """
    function(capacity) {
        if (capacity === null || isNaN(capacity) || !Number.isInteger(Number(capacity))) {
            return [false, true];
        }
        if (capacity < 2 || capacity > 120) {
            return [false, true];
        }
        return [true, false];
    }
    """,
    Output("picker-capacity", "valid"),
    Output("picker-submit", "disabled"),
    Input("picker-capacity", "value"),
)

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
        and eq_set.issubset(room.equipment.split(","))
    ]
    free_rooms.sort(key=lambda r: r.capacity)
    room_desc: dict[tuple[str, str], str] = {}
    for room in free_rooms:
        status, desc = dbm.room_status(room.building, room.room, date, time)
        if status != "free":
            continue
        room_desc[(room.building, room.room)] = desc
    
    return [
        dbc.Col(html.Div(dbc.Card([
            dbc.CardHeader(building_span(room.building, ("" if room.room.strip("!").isdigit() else " ")+room.room.strip("!"))),
            dbc.CardBody([
                html.P(f"Оборудование: {', '.join(room.equipment.split(',')) or 'нет'}", className="mb-1"),
                html.P(["Вместимость: ", html.Strong(str(room.capacity)), " человек"], className="mb-1"),
                html.P(["Свободно ", room_desc[(room.building, room.room)]], className="mb-1"),
            ]),
        ]), id={"type": "room-card", "building": room.building, "room": room.room}))
        for room in free_rooms if (room.building, room.room) in room_desc
    ]
    

clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks.some(click => click)) {
            return ["", "", "", false];
        }
        
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered.length) {
            return ["", "", "", false];
        }
        
        const prop_id = triggered[0].prop_id.split('.')[0];
        const room_id = JSON.parse(prop_id);
        
        const today = new Date();
        const dateStr = today.toISOString().split('T')[0];
        
        return [room_id.building, room_id.room, dateStr, true];
    }
    """,
    Output("event-building", "value"),
    Output("event-room", "value"),
    Output("event-date", "date"),
    Output("event-modal", "is_open"),
    Input({"type": "room-card", "building": ALL, "room": ALL}, "n_clicks"),
    prevent_initial_call=True
)


clientside_callback(
    """
    function(n_clicks) {
        return false;
    }
    """,
    Output("event-modal", "is_open", allow_duplicate=True),
    Input("event-cancel", "n_clicks"),
    prevent_initial_call=True
)

clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks.some(click => click)) {
            return false;
        }
        
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered.length) {
            return false;
        }
        
        const prop_id = triggered[0].prop_id.split('.')[0];
        const pair_id = JSON.parse(prop_id);
        const start_time = pair_id.value;
        const end_time = {
            "09:00": "10:25",
            "10:45": "12:10",
            "12:20": "13:45",
            "13:55": "15:20",
            "15:30": "16:55",
            "17:05": "18:30",
            "18:35": "20:00",
        }[start_time]
        return [start_time, end_time];
    }
    """,
    Output("event-start", "value", allow_duplicate=True),
    Output("event-end", "value", allow_duplicate=True),
    Input({"type": "event-pair-start", "value": ALL}, "n_clicks"),
    prevent_initial_call=True
)

clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks.some(click => click)) {
            return false;
        }
        
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered.length) {
            return false;
        }
        
        const prop_id = triggered[0].prop_id.split('.')[0];
        const pair_id = JSON.parse(prop_id);
        const end_time = pair_id.value;
        return end_time;
    }
    """,
    Output("event-end", "value", allow_duplicate=True),
    Input({"type": "event-pair-end", "value": ALL}, "n_clicks"),
    prevent_initial_call=True
)


@callback(
    Output("my-events-body", "children"),
    Output("my-events-modal", "is_open"),
    Input("my-events-button", "n_clicks"),
    prevent_initial_call=True
)
def show_my_events(_):
    user_token = flask.session.get("password")
    if not user_token:
        return [], False
    events = dbm.get_user_unconfirmed_events(user_token)
    if not events:
        return [
            html.Div("Нет событий", className="text-center"),
        ], True
    return dbc.Row([
            dbc.Col(html.Div(dbc.Card([
                dbc.CardHeader(
                    event.name,
                    style={
                        "background-color": BUILDING_PALETTES[event.building][0],
                        "color": "white", "font-weight": "bold",
                    }
                ),
                dbc.CardBody([
                    html.P(building_span(event.building, event.room)),
                    html.P(f"Время: {event.time_start} - {event.time_finish}"),
                ]),
            ], outline=True, color="secondary"), id={"type": "event-card", "id": event.id}))
            for event in events
        ], class_name="row-cols-auto"), True


clientside_callback(
    # when an event card is clicked, change its color to success and all others to secondary.
    # Store current chosen card id in Store
    """
    function(n_clicks) {
        if (!n_clicks.some(click => click)) {
            return false;
        }
        
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered.length) {
            return false;
        }
        
        const prop_id = triggered[0].prop_id.split('.')[0];
        const event_id = JSON.parse(prop_id)["id"];
        const event_cards = document.querySelectorAll("[id^='event-card']");
        event_cards.forEach(card => {
            if (card.id.id === event_id.id) {
                card.style.backgroundColor = "var(--bs-success)";
            } else {
                card.style.backgroundColor = "var(--bs-secondary)";
            }
        });
        return event_id.id;
    }   
    """,
    Output("my-events-chosen-id", "data"),
    Input({"type": "event-card", "id": ALL}, "n_clicks"),
    prevent_initial_call=True
)

clientside_callback(
    """
    function(data) {
        if (!data) {
            return false;
        }
        return true;
    }
    """,
    Output("my-events-cancel", "disabled"),
    Input("my-events-chosen-id", "data"),
    prevent_initial_call=True
)
