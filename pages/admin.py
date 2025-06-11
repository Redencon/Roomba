import dash
from dash import html, dcc, Input, Output, callback, State, clientside_callback, ALL, callback_context
from dash import dash_table, no_update, set_props
from flask import session
from utils import dbm, BUILDINGS, BUILDING_PALETTES, building_span, EQUIPMENT_OPTIONS
import dash_bootstrap_components as dbc
from datetime import datetime
from sql import Events, Room
from flask import request

from typing import NamedTuple


dash.register_page(__name__)


class FictionalEvent(NamedTuple):
    id: int
    building: str
    room: str
    time_start: str
    time_finish: str
    description: str


layout = html.Div([
    html.H1(["Управление", html.Br(), "мероприятиями"], className="text-center my-4"),
    dbc.Toast(
        id="error-toast",
        header="", is_open=False,
        dismissable=True, duration=5000,
        icon="danger",
        style={"position": "fixed", "bottom": 40, "right": 20, "width": 250, "z-index": 1000}),
    dbc.Tabs([
        dbc.Tab([
            dbc.Row([
                dbc.Col(html.H4("Подтвердить мероприятия", className="text-center"), width=6, md=9),
                dbc.Col(dbc.Button("Обновить", id="refresh-button", color="primary"), width=6, md=3),
                dbc.Col(id="uncertain-events", children=[], width=12),
            ], class_name="mt-3"),
        ], label="Подтверждение", label_style={"color": "var(--color-primary)"}, active_label_style={"color": "white"}),
        dbc.Tab([
            #  - Add event -
            # Event has fields: room, building, date, time range, description
            # Building selected from dropdown
            # Room selected from all rooms in building
            # Date is selected as one date from calendar, or multiple dates
            # For each different weekday a separate event is created
            # Time range is selected as start and end time
            # It is highly encouraged to add the person who is responsible for the event
            # to the description (separate field in a form?)
            dbc.Row([
                dbc.FormText("Дата проведения"),
                dbc.Col(dcc.DatePickerSingle(
                    date=datetime.today().date(), id="date-picker", display_format='YYYY-MM-DD',
                    first_day_of_week=1,
                ), width=12),
                dbc.Col(dbc.Checkbox(id="multiple-dates", label="Еженедельно", value=False), width=12),
                dbc.Collapse(dbc.Row([
                    dbc.Col(["до: ", dcc.DatePickerSingle(
                        date=datetime.now(), id="date-picker-end", display_format='YYYY-MM-DD',
                        first_day_of_week=1,
                    )], width=7),
                    dbc.Col(dbc.Checkbox(id="date-forever", label="До конца семестра", value=False), width=5),
                ]), id="date-picker-end-collapse", is_open=False),
                dbc.Col([
                    dbc.FormText("Начало"),
                    dbc.Input(id="start-time", type="time", debounce=True, placeholder="00:00"),
                ], class_name="col-3 col-lg-2"),
                dbc.Col([
                    dbc.FormText("Окончание"),
                    dbc.Input(id="finish-time", type="time", debounce=True, placeholder="00:00"),
                ], class_name="col-3 col-lg-2"),
                # dbc.Col(dcc.Input(id="finish-time", type="time", placeholder="Время окончания", debounce=True), class_name="col-3 col-lg-2"),
                dbc.Col([
                    dbc.FormText("Корпус"),
                    dcc.Dropdown(options=[
                        {"label": html.Span(building, style={
                            'color': BUILDING_PALETTES[building][0],
                            'font-weight': '700',
                        }), "value": building}
                        for building in BUILDINGS
                    ], id="building", value=BUILDINGS[0], clearable=False),
                ], class_name="col-3 col-lg-2"),
                dbc.Col([
                    dbc.FormText("Аудитория"),
                    dcc.Dropdown(id="room", options=[], value=None, placeholder="ауд."),
                ], width=3),
                dbc.Col(dbc.Button("Проверить", id="check"), class_name="col-4 col-lg-3 align-items-end d-flex"),
                dbc.Collapse(id="check-result", is_open=False),
                dbc.Col(dbc.Textarea(id="description", placeholder="Описание"), width=12),
                dbc.Col(dbc.Button("Добавить", id="add-button", color="primary", disabled=True), width=12),
            ], class_name="gy-2 mb-4 mt-1 gx-1"),
        ], label="Добавить", tab_id="add", label_style={"color": "var(--color-primary)"}, active_label_style={"color": "white"}),
        dbc.Tab([
            # - Remove event -
            # First, the event should be selected either by date or by room
            # Then either the event is removed or any of its fields are changed
            # Removal or change should be confirmed by the user by pressing a button
            # (with a confirmation dialog)
            dbc.Row([
                dbc.Col([
                    dbc.FormText("Дата проведения"),
                    html.Br(),
                    dcc.DatePickerSingle(date=datetime.today().date(), id="date-picker-remove", display_format='YYYY-MM-DD'),
                ], width=3),
                dbc.Col([
                    dbc.FormText("Корпус"),
                    dcc.Dropdown(options=[
                        {"label": building_span(building), "value": building}
                        for building in BUILDINGS
                    ], id="building-remove", value=BUILDINGS[0], clearable=False),
                ], width=3),
                dbc.Col([
                    dbc.FormText("Аудитория"),
                    dcc.Dropdown(id="room-remove", options=[], value=None, placeholder="ауд."),
                ], width=3),
                dbc.Col(dbc.Button("Найти", id="check-remove"), width=3, class_name="d-flex align-items-end"),
            ]),
            dbc.Row(class_name="my-2 row-cols-2 g-2", id="search-results-admin"), # search results are displayed here
            dbc.Collapse([
                dbc.Row([
                    # Selected card details
                    # Time range, description, room and building
                    dbc.Col(html.H3("Изменить данные"), width=12),
                    dbc.Col([
                        dbc.FormText("Начало"),
                        dbc.Input(id="start-time-remove", type="time", debounce=True, placeholder="00:00"),
                    ], class_name="col-3 col-lg-2"),
                    dbc.Col([
                        dbc.FormText("Окончание"),
                        dbc.Input(id="finish-time-remove", type="time", debounce=True, placeholder="00:00"),
                    ], class_name="col-3 col-lg-2"),
                    dbc.Col([
                        dbc.FormText("Корпус"),
                        dcc.Dropdown(options=[
                            {"label": html.Span(building, style={
                                'color': BUILDING_PALETTES[building][0],
                                'font-weight': '700',
                            }), "value": building}
                            for building in BUILDINGS
                        ], id="building-remove-select", value=BUILDINGS[0], clearable=False),
                    ], class_name="col-3 col-lg-2"),
                    dbc.Col([
                        dbc.FormText("Аудитория"),
                        dcc.Dropdown(id="room-remove-select", options=[], value=None, placeholder="ауд."),
                    ], width=3),
                    dbc.Col([
                        dbc.FormText("Описание"),
                        dbc.Textarea(id="description-remove", placeholder="Описание"),
                    ], width=12),
                ]),
                dbc.Row([
                    dbc.Col(dbc.Button("Сохранить", id="save-button", color="primary", disabled=True), width=6),
                    dbc.Col(dbc.Button("Удалить", id="remove-button", color="danger", disabled=True), width=6),
                ], class_name="mt-3"),
            ], is_open=False, id="remove-collapse"),
            dcc.Store(id="selected-event"),
        ], label="Убрать/изменить", tab_id="remove", label_style={"color": "var(--color-primary)"}, active_label_style={"color": "white"}),
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.FormText("Корпус"),
                    dcc.Dropdown(options=[
                        {"label": building_span(building), "value": building}
                        for building in BUILDINGS
                    ], id="building-equipment", value=BUILDINGS[0], clearable=False),
                ], width=6, md=3),
                dbc.Col([dbc.Button("Показать", id="select-equipment", color="primary")], width=6, md=3, class_name="d-flex align-items-end"),
            ], class_name="g-2"),
            dbc.Row(dbc.Col(dbc.Alert(
                "Изменение номеров аудиторий не отражается на существующих мероприятиях в системе. Удаление, изменение или добавление аудиторий может привести к неправильной работе графика. По возможности, убедитесь в отсутствии мероприятий в аудитории перед изменением её номера или удалением.",
                color="warning",
                dismissable=True,
            ), width=12), class_name="my-2"),
            dbc.Row(id="room-cards", children=[], class_name="g-2 my-2"),
        ], label="Аудитории", tab_id="rooms", label_style={"color": "var(--color-primary)"}, active_label_style={"color": "white"})
    ], class_name="nav-pills", ),
    dbc.Modal([
        dbc.ModalHeader("Подтвердите действие"),
        dbc.ModalBody(id="confirm-body"),
        dbc.ModalFooter(dbc.Row([
            dbc.Col(dbc.Button("Отмена", id="cancel-remove", color="secondary"), width=6),
            dbc.Col(dbc.Button("Удалить", id="confirm-remove", color="danger"), width=6, style={"display": "none"}, id="remove-col"),
            dbc.Col(dbc.Button("Сохранить", id="confirm-save", color="primary"), width=6, style={"display": "none"}, id="save-col"),
        ]))
    ], id="confirm-dialog", is_open=False),
    dbc.Modal([
        dbc.ModalHeader("Подтвердите добавление"),
        dbc.ModalBody(id="confirm-add-body"),
        dbc.ModalFooter(dbc.Row([
            dbc.Col(dbc.Button("Отмена", id="cancel-add", color="secondary"), width=6),
            dbc.Col(dbc.Button("Добавить", id="confirm-add", color="primary"), width=6),
        ]))
    ], id="confirm-add-dialog", is_open=False),
    dbc.Modal([
        dbc.ModalHeader("", id="room-change-header"),
        dbc.ModalBody(id="room-change-body"),
        dbc.ModalFooter(dbc.Row([
            dbc.Col(dbc.Button("Отмена", id="cancel-room-change", color="secondary"), width=6),
            dbc.Col(dbc.Button("Сохранить", id="confirm-room-change", color="primary"), width=6),
        ])),
        dcc.Store(id="room-change-data", data={}),
    ], id="room-change-dialog", is_open=False),
], className="container")

clientside_callback(
    """
    function (checked) {
        return checked;
    }
    """,
    Output("date-picker-end", "disabled"),
    Input("date-forever", "value"),
)

clientside_callback(
    """
    function (checked) {
        return checked;
    }
    """,
    Output("date-picker-end-collapse", "is_open"),
    Input("multiple-dates", "value"),
)

@callback(
    Output("uncertain-events", "children"),
    Input("refresh-button", "n_clicks")
)
def show_uncertain_events(n_clicks):
    events = dbm.get_uncertain_events()
    if not events:
        return html.Div("Нет неподтвержденных мероприятий", className="text-center text-muted my-3")
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                event_card(event, show_contact=True),
                dbc.Row([
                    dbc.Col(building_span(event.building, event.room), width=12, class_name="text-center mb-2"),
                    dbc.Col([
                        dbc.Button(
                            "Подтвердить", 
                            id={"type": "confirm-event", "index": event.id},
                            color="success",
                            class_name="w-100"
                        ),
                    ], width=6),
                    dbc.Col([
                        dbc.Button(
                            "Отклонить",
                            id={"type": "deny-event", "index": event.id},
                            color="danger",
                            class_name="w-100"
                        ),
                    ], width=6),
                ], class_name="mt-2")
            ], width=12)
            for event in events
        ], class_name="g-2")
    ])

@callback(
    Output("uncertain-events", "children", allow_duplicate=True),
    Input({"type": "confirm-event", "index": ALL}, "n_clicks"),
    State({"type": "confirm-event", "index": ALL}, "id"),
    prevent_initial_call=True
)
def confirm_event(n_clicks, ids):
    if not any(n_clicks):
        return no_update
    
    # Find which button was clicked
    ctx = callback_context
    button_id = ctx.triggered_id
    event_id = button_id["index"]
    
    try:
        dbm.confirm_event(event_id)
    except ValueError as e:
        return dbc.Alert(str(e), color="danger", dismissable=True)
    
    # Refresh the list
    return show_uncertain_events(None)

@callback(
    Output("uncertain-events", "children", allow_duplicate=True),
    Input({"type": "deny-event", "index": ALL}, "n_clicks"),
    State({"type": "deny-event", "index": ALL}, "id"),
    prevent_initial_call=True
)
def deny_event(n_clicks, ids):
    if not any(n_clicks):
        return no_update
    
    # Find which button was clicked
    ctx = callback_context
    button_id = ctx.triggered_id
    event_id = button_id["index"]
    
    # TODO This looks rather smart. Copy such error handling in other callbacks.
    try:
        dbm.deny_event(event_id)
    except ValueError as e:
        return dbc.Alert(str(e), color="danger", dismissable=True)
    
    # Refresh the list
    return show_uncertain_events(None)

@callback(
    Output("check-result", "children"),
    Output("check-result", "is_open"),
    Output("add-button", "disabled"),
    Input("check", "n_clicks"),
    Input("building", "value"),
    Input("room", "value"),
    Input("date-picker", "date"),
    Input("start-time", "value"),
    Input("finish-time", "value"),
    Input("date-picker-end", "date"),
    Input("multiple-dates", "value"),
    Input("date-forever", "value"),
    prevent_initial_call=True
)
def show_check_result(n_clicks, building, room, date, start_time, finish_time, date_end, multiple_dates, date_forever):
    if dash.callback_context.triggered_id == "check":
        if not start_time or not finish_time or not room:
            return "", False, True
        # date = date if not date_forever else None
        date_end = date_end if multiple_dates and not date_forever else None
        evs = dbm.check_room(building, room, date, start_time, finish_time, date_end)
        if evs:
            return html.Span("На выбранное время аудитория занята: "+evs.description, className="text-danger"), True, True
        else:
            return html.Span("На выбранное время аудитория свободна", className="text-success"), True, False
    else:
        return "", False, True


@callback(
    Output("room", "options"),
    Input("building", "value"),
)
@callback(
    Output("room-remove", "options"),
    Input("building-remove", "value"),
)
@callback(
    Output("room-remove-select", "options"),
    Input("building-remove-select", "value"),
    State("room-remove-select", "value"),
    prevent_initial_call=True
)
def update_room_options(building, *values):
    res = []
    for room in dbm.get_all_rooms(building):
        if room.startswith("!"):
            res.append({"label": html.Strong(room[1:]), "value": room})
        else:
            res.append({"label": room, "value": room})
    res.sort(key=lambda x: x["value"])
    return res


def event_card(event: "Events|FictionalEvent", for_search=False, show_contact=False):
    cardid = {"type": "search-card-admin", "index": event.id} if for_search else "remove-card"
    
    # Show badge for event type
    badges = []
    # All FicitonalEvents are temporary and confirmed?
    if isinstance(event, Events) and not event.is_confirmed:
        badges.append(dbc.Badge(
            "Неподтверждено",
            color="warning",
            pill=True,
            class_name="m-1"
        ))
        if event.is_special:
            badges.append(dbc.Badge(
                "Специальное",
                color="info",
                pill=True,
                class_name="m-1"
            ))
    else:
        badges.append(dbc.Badge(
            "Разовое" if dbm.event_temporary(event) else "Регулярное",
            color=("warning" if dbm.event_temporary(event) else "success"),
            pill=True,
            class_name="m-1"
        ))

    # Add contact info if available and requested
    description = event.description
    if show_contact and isinstance(event, Events) and event.contact_info:
        description = html.Div([
            html.Div(event.description),
            html.Hr(className="my-1"),
            html.Small(["Контакты: ", html.Strong(event.contact_info)], className="text-muted")
        ])

    return dbc.Card([
        dbc.CardHeader(html.Strong([
            event.time_start+" - "+event.time_finish,
            *badges
        ])),
        dbc.CardBody([html.Span(description)]),
    ], id=cardid)

@callback(
    Output("search-results-admin", "children"),
    Input("check-remove", "n_clicks"),
    State("date-picker-remove", "date"),
    State("building-remove", "value"),
    State("room-remove", "value"),
    prevent_initial_call=True
)
def search_events_admin(_, date, building, room):
    if not date or not building or not room:
        return [dbc.Col()]
    events = dbm.find_events(building, room, date)
    return [
        dbc.Col(html.Div(
            event_card(ev, for_search=True),
        id={"type": "search-div-admin", "index": ev.id}, className="h-100"))
        for ev in events
    ]

@callback(
    Output("start-time-remove", "value"),
    Output("finish-time-remove", "value"),
    Output("building-remove-select", "value"),
    Output("room-remove-select", "value"),
    Output("description-remove", "value"),
    Output("save-button", "disabled"),
    Output("remove-button", "disabled"),
    Output("remove-collapse", "is_open"),
    Output("selected-event", "data"),
    Input({"type": "search-div-admin", "index": ALL}, "n_clicks"),
    Input({"type": "search-card-admin", "index": ALL}, "id"),
    prevent_initial_call=True
)
def select_event(n_clicks, ids):
    if not any(n_clicks):
        return "", "", "", "", "", True, True, False, None
    evid = callback_context.triggered_id["index"]
    ev = dbm.get_event_by_id(evid)
    for div_id in ids:
        if div_id["index"] == evid:
            dash.set_props({"type": "search-card-admin", "index": div_id["index"]}, {"className": "h-100 border-3 border-success"})
        else:
            dash.set_props({"type": "search-card-admin", "index": div_id["index"]}, {"className": "h-100 border-1 border-primary"})
    return ev.time_start, ev.time_finish, ev.building, ev.room, dbm.dateless_event(ev), False, False, True, evid

@callback(
    Output("confirm-body", "children"),
    Output("remove-col", "style"),
    Output("save-col", "style"),
    Output("confirm-dialog", "is_open"),
    Input("save-button", "n_clicks"),
    Input("remove-button", "n_clicks"),
    State("selected-event", "data"),
    State("start-time-remove", "value"),
    State("finish-time-remove", "value"),
    State("building-remove-select", "value"),
    State("room-remove-select", "value"),
    State("description-remove", "value"),
    prevent_initial_call=True
)
def open_save_dialog(n_save, n_remove, evid, str, ftr, bld, room, dsc):
    event = dbm.get_event_by_id(evid)
    to_remove = callback_context.triggered_id == "remove-button"
    if to_remove:
        return [
            html.Span("Вы уверены, что хотите удалить это мероприятие?", className="text-danger"),
            dbc.Row(dbc.Col(event_card(event)), class_name="my-2"),
            dbc.Row(dbc.Col(building_span(event.building, event.room)), class_name="text-center")
        ], {"display": "block"}, {"display": "none"}, True
    else:
        print(str, ftr, bld, room, dsc)
        fictive = FictionalEvent(
            id=0, time_start=str, time_finish=ftr,
            building=bld, room=room, description=dsc,
        )
        return [
            html.Span("Вы уверены, что хотите сохранить изменения?", className="text-primary"),
            dbc.Row([
                dbc.Col(event_card(event)),
                dbc.Col(event_card(fictive))
            ], class_name="my-2 row-cols-2 g-2"),
            dbc.Row([
                dbc.Col([building_span(event.building, event.room)], width=6, class_name="text-center"),
                dbc.Col([building_span(fictive.building, fictive.room)], width=6, class_name="text-center")
            ]),
            dbc.Row([
                dbc.Col(html.Span("Было"), width=6, class_name="text-center"),
                dbc.Col(html.Span("Стало"), width=6, class_name="text-center"),
            ])
        ], {"display": "none"}, {"display": "block"}, True

@callback(
    Output("confirm-add-body", "children"),
    Output("confirm-add-dialog", "is_open"),
    Input("add-button", "n_clicks"),
    State("date-picker", "date"),
    State("building", "value"),
    State("room", "value"),
    State("start-time", "value"),
    State("finish-time", "value"),
    State("description", "value"),
    State("date-picker-end", "date"),
    State("multiple-dates", "value"),
    State("date-forever", "value"),
    prevent_initial_call=True
)
def confirm_add(_, date, building, room, start_time, finish_time, description, date_end, multiple_dates, date_forever):
    date_str = ""
    if not date_forever:
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m")
        date_str = date
        if multiple_dates:
            date_end = datetime.strptime(date_end, "%Y-%m-%d").strftime("%d.%m")
            date_str += " - "+date_end
    fictive = FictionalEvent(
        id=0, time_start=start_time, time_finish=finish_time,
        building=building, room=room, description=" ".join([description, date_str])
    )
    return [
        html.Span("Вы уверены, что хотите добавить это мероприятие?", className="text-primary"),
        dbc.Row([
            dbc.Col(event_card(fictive)),
        ],class_name="mt-2"),
        dbc.Row(dbc.Col(building_span(fictive.building, fictive.room)), class_name="text-center mb-2"),
    ], True

clientside_callback(
    """function (n_clicks) {
        return false;
    }""",
    Output("confirm-add-dialog", "is_open", allow_duplicate=True),
    Input("cancel-add", "n_clicks"),
    prevent_initial_call=True
)


clientside_callback(
    """
    function (checked) {
        return false;
    }
    """,
    Output("confirm-dialog", "is_open", allow_duplicate=True),
    Input("cancel-remove", "n_clicks"),
    prevent_initial_call=True
)

ROOM_TYPE_BADGES = {
    "lecture": dbc.Badge("Лекц.", color="primary", pill=True),
    "seminar": dbc.Badge("Сем.", color="success", pill=True),
    "lab": dbc.Badge("Лаб.", color="warning", pill=True),
    "computer": dbc.Badge("Комп.", color="info", pill=True),
    "chair": dbc.Badge("Каф.", color="secondary", pill=True),
}

def room_card(room: Room):
    equipment = room.equipment.split(",")
    return html.Div(dbc.Card([
        dbc.CardHeader([
            html.Div(html.Strong(room.room.strip("!"))),
            html.Div(ROOM_TYPE_BADGES[room.room_type.name], className="ms-auto")
        ], className="d-flex align-items-center justify-content-between"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.I(className="bi bi-people me-1"),
                    html.Strong(str(room.capacity)),
                ], width=6, class_name="fs-3"),
                dbc.Col([
                    html.Span([
                        html.I(className="bi bi-projector", title="Проектор")
                    ], className="me-2")
                    if "Проектор" in equipment
                    or room.room_type.name == "lecture"
                    or "Мультимедийная трибуна" in equipment
                    else None,
                    html.Span([
                        html.I(className="bi bi-pencil-square", title="Меловая доска")
                    ], className="me-2") if "Меловая доска" in equipment else None,
                    html.Span([
                        html.I(className="bi bi-display", title="Электронная доска")
                    ], className="me-2") if "Электронная доска" in equipment else None,
                    html.Span([
                        html.I(className="bi bi-easel", title="Маркерная доска")
                    ], className="me-2") if "Маркерная доска" in equipment else None,
                ], width=6, class_name="d-flex justify-content-end fs-3")
            ], class_name="g-2")
        ], class_name="h-100"),
    ], className="h-100"), id={"type": "room-card", "index": room.id}, className="h-100")

@callback(
    Output("room-cards", "children"),
    Input("select-equipment", "n_clicks"),
    State("building-equipment", "value"),
    prevent_initial_call=True
)
def show_room_cards(n_clicks, building):
    if not building:
        return [dbc.Col()]
    rooms = dbm.get_all_rooms_obj(building)
    rooms.sort(key=lambda x: x.room)
    return [
        dbc.Col(room_card(room), width=6, md=4, lg=3)
        for room in rooms
    ]

@callback(
    Output("room-change-dialog", "is_open", allow_duplicate=True),
    Output("room-change-header", "children"),
    Output("room-change-body", "children"),
    Output("room-change-data", "data"),
    Input({"type": "room-card", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_room_change_dialog(n_clicks):
    if not any(n_clicks):
        return False, "", "", {}
    room_id = callback_context.triggered_id["index"]
    room = dbm.get_room_by_id(room_id)
    if room.room_type.name in ["chair", "computer"]:
        set_props("error-toast", {"header": "Нет доступа", "children": "Кафедральные аудитории нельзя изменять", "is_open": True})
        return no_update, no_update, no_update, no_update
    room_title = html.Div(html.Strong(room.building+" "+room.room), className="text-center")
    room_body = dbc.Row([
        dbc.Col([
            dbc.FormText("Корпус"),
            dbc.Input(id="room-building", value=room.building, disabled=True),
        ], width=6, class_name="mb-3"),
        dbc.Col([
            dbc.FormText("Номер аудитории"),
            dbc.Input(id="room-number", value=room.room.strip("!")),
        ], width=6, class_name="mb-3"),
        dbc.Col([
            dbc.FormText("Вместимость"),
            dbc.Input(id="room-capacity", type="number", value=room.capacity, min=0, debounce=True),
        ], width=12, class_name="mb-3"),
        dbc.Col([
            dbc.FormText("Тип аудитории"),
            dcc.Dropdown(
                id="room-type",
                options=[
                    {"label": "Лекционная", "value": "lecture"},
                    {"label": "Семинарская", "value": "seminar"}, 
                    {"label": "Компьютерная", "value": "computer"}
                ],
                value=room.room_type.name,
                clearable=False
            )
        ], width=12, class_name="mb-3"),
        dbc.Col([
            dbc.FormText("Оборудование"),
            *[
                dbc.Checkbox(
                    id={"type": "equipment-checkbox", "index": equipment},
                    label=equipment,
                    value=equipment in room.equipment,
                    className="mb-2"
                )
                for equipment in EQUIPMENT_OPTIONS
            ]
        ], width=12)
    ])
    return True, room_title, room_body, {"room_id": room_id}


# On Save button click
@callback(
    Output("room-change-dialog", "is_open", allow_duplicate=True),
    Input("save-room-change", "n_clicks"),
    State("room-change-data", "data"),
    State("room-building", "value"),
    State("room-number", "value"),  
    State("room-capacity", "value"),
    State("room-type", "value"),
    State("equipment-checkbox", "value"),
    prevent_initial_call=True
)
def save_room_change(_, room_id, building, number, capacity, _type, equipment):
    # Get all data and room id
    room = dbm.get_room_by_id(room_id)
    # Update room data
    user = request.cookies.get('password')
    dbm.update_room(room_id, building, number, capacity, _type, equipment, user)
    return False


# Close dialog without any backed changes
clientside_callback(
    """
    function (checked) {
        return false;
    }
    """,
    Output("room-change-dialog", "is_open", allow_duplicate=True),
    Input("cancel-room-change", "n_clicks"),
    prevent_initial_call=True
)

#clientside prevent room capacity below 1 and above 300
clientside_callback(
    """
    function (capacity) {
        // Check if capacity contains non-digit characters
        if (capacity === null || isNaN(capacity) || !Number.isInteger(Number(capacity))) {
            return 9;
        }
        if (capacity < 1 || capacity > 300) {
            return 9;
        }
        return capacity;
    }
    """,
    Output("room-capacity", "value"),
    Input("room-capacity", "value"),
    prevent_initial_call=True
)

