import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback, ALL, MATCH
from dash import clientside_callback, no_update, callback_context, set_props
import random

from traceback import format_exc as tra
import datetime as dt

from sendemail import send_chalk_message

from utils import BUILDINGS, BUILDING_PALETTES, dbm, track_usage, ROOM_STATUS, BUILDINGS_EN, log
from utils import D_BLOCK, D_NONE

dash.register_page(__name__, "/rooms")

ROOM_STATUS_ICONS = {
    "free": "bi bi-unlock",
    "busy": "bi bi-lock",
    "lecture": "bi bi-shield",
    "marked": "bi bi-pencil",
}

ROOM_STATUS_CLASSES = {
    "free": "status-free",
    "busy": "status-busy",
    "lecture": "status-lecture",
    "marked": "status-marked",
}

ROOM_STATUS_TEXT = {
    "free": "Свободно",
    "busy": "Занятие",
    "lecture": "Лекционная",
    "marked": "Занято",
}

ISO9 = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
    "й": "j", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya"
}

BUILDINGS_ROOMS = BUILDINGS[:1]

MARK_DISCLAIMER = html.Details([
    html.Summary(["О том как устроен сервис"]),
    html.Div([
        html.P(" ".join([
            "Здесь ты можешь указать, что аудитория занята.",
            "Запись нельзя сделать в лекционной аудитории или поверх имеющегося занятия.",
            "Все записи свободно добавляются и удаляются любым пользователем.",
            "Запись в этой табличке не является официальной и не гарантирует доступ к аудитории.",
            "Используйте сервис для информирования других студентов"
        ])),
        dbc.Alert("Запись продержится столько пар, сколько указано в длительности. После 20:00 пара это 2 астрономических часа", color="warning"),
        html.Hr(),
    ])
])

def room_indexer(room: str, building: str):
    new_room = room.replace(" ", "_").replace(".", "_").replace("!", "")
    new_room = "".join([ISO9.get(c, c) for c in new_room.lower()])
    building = BUILDINGS_EN[building]
    return new_room + "_" + building

for building in BUILDINGS_ROOMS:
    @callback(
        Output(f"r-card-{building}", "children"),
        Input(f"r-card-{building}", "id")
    )
    def fill_accordion(_, building=building):
        res = sorted(dbm.get_all_rooms(building))
        for room in res:
            try:
                dbm.get_room_status(building, room)
            except:
                raise ValueError(f"Room {room} in building {building} is not in the database.")
        return [
            dbc.Row([
                dbc.Col([
                    html.Div(
                        dbc.Card(
                            [
                                dcc.Store(
                                    id={"type": "room-card-store", "index": room_indexer(room, building)},
                                    data={"status": "free", "desc": "-"}, storage_type="session",
                                ),
                                dbc.CardHeader(
                                    room + " " + building,
                                    id={"type": "room-card-header", "index": room_indexer(room, building)},
                                    style={
                                        "background-color": random.choice(BUILDING_PALETTES[building]),
                                        "color": "white",
                                        "font-weight": "600",
                                    },
                                ),
                                dbc.CardBody([
                                    dcc.Markdown(
                                        "-",
                                        id={"type": "room-desc", "index": room_indexer(room, building)},className="mb-0",
                                        dangerously_allow_html=True
                                    )
                                ], style={"height": "100%"}, class_name="p-1"),
                                dbc.CardFooter([
                                    html.I(
                                        id={"type": "room-icon", "index": room_indexer(room, building)},
                                        className="bi bi-unlock"),
                                    " ",
                                    html.Span(
                                        id={"type": "room-status", "index": room_indexer(room, building)},
                                        children="Свободно")
                                ])
                            ],
                            id={"type": "room-card", "index": room_indexer(room, building)}, style={"height": "100%"}
                        ),
                        n_clicks=0, id={"type": "room-card-click", "index": room_indexer(room, building)}, style={"height": "100%"}
                    ),
                ])
                for room in res
            ], class_name="row-cols-2 row-cols-md-5 text-center g-2")
        ]



clientside_callback(
    """
    function(status, but) {
        const state = status.status;
        let desc = status.desc;
        if (state === "marked") {
            const [plim, unav, loud, dur] = desc.split("|");
            desc = '<div class="row gx-0 fs-4 fw-bold">' +
                   '<div class="col">' +
                   '<i class="bi bi-people"></i> <span>' + plim + '</span>' +
                   '</div>' +
                   '<div class="col">' +
                   '<i class="' + (loud === "loud" ? "bi bi-volume-up" : "bi bi-volume-off") + '" style="color: ' + (loud === "loud" ? "var(--bs-primary)" : "var(--bs-gray)") + '"></i>' +
                   '</div>' +
                   '<div class="col">' +
                   '<i class="' + (unav === "1" ? "bi bi-ban" : "bi bi-check2") + '" style="color: ' + (unav === "1" ? "var(--bs-danger)" : "var(--bs-success)") + '"></i>' +
                   '</div>' +
                   '<div class="col">' +
                   '<i class="bi bi-clock-history"></i> <span>' + dur + '</span>' +
                   '</div>' +
                   '</div>';
        }
        if (desc === "-") {
            return ['<p class="placeholder-wave"><span class="placeholder col-7"></span></p>', "bi bi-question-circle", "Нет данных", "status-lecture"]
        }
        const iconClass = {
            "free": "bi bi-unlock",
            "busy": "bi bi-lock",
            "lecture": "bi bi-shield",
            "chair": "bi bi-shield",
            "computer": "bi bi-shield",
            "marked": "bi bi-pencil"
        }[state];
        const statusText = {
            "free": "Свободно",
            "busy": "Занятие",
            "lecture": "Лекционная",
            "marked": "Занято",
            "chair": "Кафедральная",
            "computer": "Компьютерная"
        }[state];
        const statusClass = {
            "free": "status-free",
            "busy": "status-busy",
            "lecture": "status-lecture",
            "chair": "status-lecture",
            "computer": "status-lecture",
            "marked": "status-marked"
        }[state];
        return [desc, iconClass, statusText, statusClass];
    }
    """,
    Output({"type": "room-desc", "index": MATCH}, "children"),
    Output({"type": "room-icon", "index": MATCH}, "className"),
    Output({"type": "room-status", "index": MATCH}, "children"),
    Output({"type": "room-card", "index": MATCH}, "className"),
    Input({"type": "room-card-store", "index": MATCH}, "data"),
)


@callback(
    Output("modal", "is_open", allow_duplicate=True), 
    Input("modal-occupy", "n_clicks"),
    State("modal-room-name", "children"),
    State("modal-headcount", "value"),
    State("modal-dont-come", "value"),
    State("modal-loud", "value"),
    State("modal-duration", "value"),
    prevent_initial_call=True,
)
def occupy_room(_, room, headcount, dont_come, loud, duration):
    room, building = room.split()
    if not headcount:
        return False
    new_status = dbm.set_room_status(building, room, "marked", "|".join([str(headcount), ("1" if dont_come else "0"), loud, str(duration)]))
    set_props({"type": "room-card-store", "index": room_indexer(room, building)}, {"data": {"status": new_status.status, "desc": new_status.status_description}})
    return False


@callback(
    Output("modal", "is_open", allow_duplicate=True),
    Input("modal-p1", "n_clicks"),
    State("modal-room-name", "children"),
    prevent_initial_call=True,
)
def plus_one_room(_, room):
    room, building = room.split()
    new_status = dbm.room_status_plus_one(building, room)
    set_props({"type": "room-card-store", "index": room_indexer(room, building)}, {"data": {"status": new_status.status, "desc": new_status.status_description}})
    return False


@callback(
    Output("modal", "is_open", allow_duplicate=True),
    Input("modal-m1", "n_clicks"),
    State("modal-room-name", "children"),
    prevent_initial_call=True,
)
def minus_one_room(_, room):
    room, building = room.split()
    new_status = dbm.room_status_minus_one(building, room)
    set_props({"type": "room-card-store", "index": room_indexer(room, building)}, {"data": {"status": new_status.status, "desc": new_status.status_description}})
    return False


@callback(
    Output("modal", "is_open", allow_duplicate=True),
    Input("modal-remove", "n_clicks"),
    State("modal-room-name", "children"),
    prevent_initial_call=True,
)
def remove_mark(_, room):
    room, building = room.split()
    new_status = dbm.unmark_room(building, room)
    set_props({"type": "room-card-store", "index": room_indexer(room, building)}, {"data": {"status": new_status.status, "desc": new_status.status_description}})
    return False


@callback(
    Output("toast", "is_open", allow_duplicate=True),
    Output("toast-interval", "disabled", allow_duplicate=True),
    Output("toast-interval", "n_intervals", allow_duplicate=True),
    Input("toast-refresh", "n_clicks"),
    Input("refresh-button", "n_clicks"),
    prevent_initial_call=True,
)
def restart_toast(_, __):
    return False, False, 0


# Rewrite with no MATCH
@callback(
    Input("refresh-button", "n_clicks"),
    Input("toast-refresh", "n_clicks"),
    State({"type": "room-card-header", "index": ALL}, "children"),
    State({"type": "room-card-store", "index": ALL}, "data"),
    State({"type": "room-card-store", "index": ALL}, "id"),
)
@log
def update_rooms(_, __, rooms, data, indexes):
    statuses = []
    for r, d, i in zip(rooms, data, indexes):
        room, building = r.split(" ")
        status = dbm.get_room_status(building, room)
        if not status:
            st = "busy"
            ds = "Нет данных"
        else:
            st = status.status
            ds = status.status_description
        statuses.append((st, ds))
        ret = {"status": st, "desc": ds}
        if ret != d:
            set_props(i, {'data': ret})
    set_props("function-log", {"children": f"Updated {len(statuses)} rooms: {statuses}"})


# @callback(
#     Output("refresh-button", "n_clicks"),
#     Input("data-button", "n_clicks"),
#     prevent_initial_call=True,
# )
# def refresh_rooms(_):
#     dbm.set_room_statuses()
#     return 0

@callback(
    Output("room-id", "data"),
    Input({"type": "room-card-click", "index": ALL}, "n_clicks"),
    State({"type": "room-card-header", "index": ALL}, "children"),
    State({"type": "room-card-header", "index": ALL}, "id"),
    prevent_initial_call=True,
)
def get_room_id(a, headers, ids):
    ctx = callback_context
    index = ctx.triggered_id["index"]
    rooms = {rid["index"]: header for rid, header in zip(ids, headers)}
    room, building = rooms[index].split(" ")
    if all([n < 1 for n in a]):
        return no_update
    try:
        room_id = dbm.get_room_id(building, room)
        set_props("function-log", {"children": f"Clicked on room {room} in building {building}, got ID {room_id}\nAll clicks: {a}"})
    except ValueError:
        return no_update
    return room_id


@callback(
    Output("modal", "is_open"),
    Output("modal-room-name", "children"),
    Output("modal-mark-room", "style"),
    Output("modal-remove-div", "style"),
    Output("modal-remove", "style"),
    Output("modal-occupy", "style"),
    Output("modal-p1", "style"),
    Output("modal-events", "children"),
    Output("modal-status", "children"),
    Input("room-id", "data"),
)
def open_modal(room_id):
    try:
        room_id = int(room_id)
        if room_id < 0:
            return tuple([False]+[no_update]*8)
        room_obj = dbm.get_room_by_id(room_id)
        if not room_obj:
            return tuple([False]+[no_update]*8)
        room, building = room_obj.room, room_obj.building
        events_today = dbm.get_today_events(room, building)
        event_div = html.Ul([
            html.Li(f"{event.time_start} {event.description}") for event in events_today
        ])
        rb = room + " " + building
        print(f"Clicked! {rb}")
        status = dbm.get_room_status(building, room)
        if status.status == "free":
            return True, rb, D_BLOCK, D_NONE, D_NONE, D_BLOCK, D_NONE, event_div, "свободна"
        elif status.status == "marked":
            return True, rb, D_NONE, D_BLOCK, D_BLOCK, D_NONE, D_BLOCK, event_div, "занята"
        else:
            return True, rb, D_NONE, D_NONE, D_NONE, D_NONE, D_NONE, event_div, "занята"
    except Exception as e:
        set_props("function-log", {"children": f"Error in open_modal: {tra()}"})
        return tuple([no_update]*9)

clientside_callback(
    """
    function(text) {
        if (text === "свободна") {
            return "text-success fw-bold"
        } else {
            return "text-danger fw-bold"
        }
    }
    """,
    Output("modal-status", "className"),
    Input("modal-status", "children")
)

@callback(
    Output("toast", "is_open"),
    Output("toast-interval", "disabled"),
    Input("toast-interval", "n_intervals"),
    prevent_initial_call=True,
)
def show_toast(n):
    if n:
        return True, True
    return no_update, no_update

@callback(
    Output("chalk-alert", "style"),
    Output("chalk-error", "style"),
    Output("chalk-sent", "data"),
    Input("modal-no-chalk", "n_clicks"),
    State("chalk-sent", "data"),
    State("chalk-sent", "modified_timestamp"),
    State("modal-room-name", "children"),
    prevent_initial_call=True,
)
@track_usage("send_chalk_message")
def send_chalk_message_callback(n_clicks, chalk_sent, chalk_sent_ts, room):
    # If the button click is stored, we assume the message was sent
    # Button does no actions, but shows the success message
    # Blocking with chalk_sent is not securem but will work for now
    room, building = room.split()
    if chalk_sent:
        # Allow the sending if 2 hours passed
        if chalk_sent_ts + 7200 < dt.datetime.now().timestamp():
            chalk_sent = False
            set_props("chalk-sent", {"modified_timestamp": dt.datetime.now().timestamp()})
    if n_clicks > 0 and not chalk_sent:
        try:
            try:
                dbm.get_room_status(building, room)
            except ValueError:
                set_props("function-log", {"children": f"Room {room} in building {building} not found, not sending chalk message."})
                return D_NONE, D_BLOCK, no_update
            send_chalk_message(building, room)
            set_props("function-log", {"children": f"Sent chalk message for {room} in {building}"})
            return D_BLOCK, D_NONE, True
        except Exception as e:
            set_props("function-log", {"children": f"Error in send_chalk_message: {tra()}"})
            set_props("chalk-error", {"children": f"Произошла ошибка при отправке сообщения: {e}"})
            return D_NONE, D_BLOCK, no_update
    set_props("function-log", {"children": f"N_clicks is 0 or chalk already sent, not sending message, {n_clicks}"})
    return D_NONE, D_BLOCK, no_update


def layout(room=None, **kwargs):
    # Page URL is folegle.ru/rooms?room={room_id}
    # If we scatter the links to rooms, we can use this to open the modal directly
    room_id = int(room) if room else -1
    room_obj = dbm.get_room_by_id(room_id)
    if room_obj:
        building = room_obj.building
        # FUTURE: if rooms will support other buildings, this will switch to the correct building
        # BUT FOR NOW
        if building not in BUILDINGS_ROOMS:
            room_id = -1
    else:
        room_id = -1 
    return dbc.Container([
        dcc.Store(id="room-id", data=room_id, storage_type="memory"),
        dbc.Row(
            [html.H1("Текущий статус аудиторий", className="text-center")],
            # style={"margin-top": "2.5rem", "margin-bottom": "2.5rem"}
            class_name="mb-4 mt-4"
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.P("Для того чтобы отметить аудиторию как занятую, нажмите на свободную аудиторию."),
                    class_name="col-auto text-left"
                ),
                dbc.Col(
                    dbc.Button("Обновить", id="refresh-button", className="btn btn-primary", n_clicks=0),
                    class_name="col-auto"
                ),
                dbc.Col(
                    dbc.DropdownMenu([
                        dbc.DropdownMenuItem(building, href=f"#acc-{building}", style={
                            "color": palette[0],
                            "font-weight": "800",
                        }, external_link=True)
                        for building, palette in BUILDING_PALETTES.items()
                        if building != "Roomba"
                    ], style={"margin-right": "auto"}, label="Перейти к", disabled=True),
                    class_name="col-auto",
                ),
            ],
            class_name="justify-content-end my-4"
        ),
        html.Div([
            dbc.Card([
                dbc.CardHeader(
                    html.Button(
                        f"{building}",
                        id=f"r-group-{building}-toggle",
                        className="btn",
                        **{"data-bs-toggle": "collapse", "data-bs-target": f"#r-collapse-{building}"},
                        style={
                            "color": "white", "font-weight": "800",
                            "font-size": "20px"
                        }
                    ), style={"background-color": BUILDING_PALETTES[building][0]},
                    id=f"r-card-header-{building}", className="sticky-header"
                ),
                dbc.Collapse(
                    dcc.Loading([
                        html.Div(id=f"r-card-{building}", className="p-4")
                    ], type="cube"),
                    id=f"r-collapse-{building}",
                    is_open=True,
                    style={"min-height": "160px"}
                ),
            ], className="mb-4 pb-1", id=f"acc-{building}")
            for building in BUILDINGS_ROOMS
        ], id='cards'),
        dbc.Modal([
            dbc.ModalHeader("Занять аудиторию"),
            dbc.ModalBody([
                html.H4(id="modal-room-name"),
                html.Div([
                    "Сейчас аудитория ",
                    html.Span(id="modal-status", className="")
                ], className=""),
                html.Div([
                   dbc.Button("В аудитории нет мела, сообщить", id="modal-no-chalk", color="secondary", class_name="col-auto my-2"),
                   dcc.Store(id="chalk-sent", data=False, storage_type="local"),
                   html.Div("Сообщение отправлено!", id="chalk-alert", className="text-success my-2", style=D_NONE),
                   html.Div("Произошла ошибка! Может вы уже отправили сообщение?", id="chalk-error", className="text-danger my-2", style=D_NONE),
                ]),
                html.Hr(),
                html.Details([
                    html.Summary("События в аудитории сегодня"),
                    html.Div(id="modal-events"),
                ], open=False),
                html.Hr(),
                MARK_DISCLAIMER,
                html.Div([
                    html.P("Выберите количество человек в аудитории, возможность входа и уровень шума."),
                    dbc.Row([
                        dbc.Col(dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="bi bi-people")),
                            dbc.Input(id="modal-headcount", type="number", value=1, min=1, max=40, style={"height": "100%", "min-width": "50px"}),
                        ], style={"flex-wrap": "nowrap"}), width=3),
                        dbc.Col(dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="bi bi-slash-circle")),
                            dbc.InputGroupText(dbc.Checkbox(id="modal-dont-come"),),
                        ], style={"flex-wrap": "nowrap"}), width=3),
                        dbc.Col(html.Div(dbc.RadioItems(
                            id="modal-loud",
                            class_name="btn-group",
                            inputClassName="btn-check",
                            labelClassName="btn btn-outline-primary",
                            labelCheckedClassName="active",
                            options=[
                                {"label": "Громко", "value": "loud"},
                                {"label": "Тихо", "value": "silent"},
                            ],
                            value="silent",
                        ), className="radio-group"), width=6),
                        dbc.Col("Длительность отметки", width=12, lg=3),
                        dbc.Col(dcc.Slider(
                            min=1,
                            max=4,
                            step=1,
                            value=1,
                            marks=None,
                            tooltip={"placement": "bottom", "always_visible": True},
                            id="modal-duration",
                        ), class_name="dbc")
                    ], class_name="g-2 mb-2"),
                ], id="modal-mark-room", style=D_NONE),
                html.Div([
                    dbc.Alert("Вы точно хотите удалить отметку?", color="danger"),
                ], id="modal-remove-div", style=D_NONE),
            ]),
            dbc.ModalFooter([
                dbc.Button("Занять", id="modal-occupy", color="primary", style=D_NONE, class_name="col-auto"),
                dbc.Button("-1", id="modal-m1", color="primary", style=D_NONE, class_name="col-auto"),
                dbc.Button("+1", id="modal-p1", color="primary", style=D_NONE, class_name="col-auto"),
                dbc.Button("Удалить", id="modal-remove", color="danger", style=D_NONE, class_name="col-auto"),
            ], class_name="flex-row"),
        ], id="modal", is_open=False, ),
        dbc.Toast(
            dbc.Col([
                dbc.Row("Обновите страницу, чтобы увидеть новые данные."),
                dbc.Row([
                    dbc.Button("Обновить", id="toast-refresh", color="primary", class_name="col-auto"),
                ], className="mt-2 justify-content-end")
            ], className="px-2"),
            id="toast",
            header="Устарело?",
            icon="warning",
            style={"position": "fixed", "bottom": 20, "right": 20, "width": 250},
            is_open=False,
            dismissable=True
        ),
        dcc.Interval(id="toast-interval", interval=1000*60*3),
    ])