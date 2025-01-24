import dash_bootstrap_components as dbc
import dash
from dash import html, dcc, Input, Output, State, callback, ALL
import traceback
import re
import datetime as dtt
import json
import plotly.graph_objects as go
import pandas as pd
import plotly.express as px

from utils import track_usage, dbm, cache, BUILDING_PALETTES, BUILDINGS, BUILDING_NAVIGATION, BUILDING_SECTIONS


TIME_SLOTS = [
    ("09:00", "10:25"),
    ("10:45", "12:10"),
    ("12:20", "13:45"),
    ("13:55", "15:20"),
    ("15:30", "16:55"),
    ("17:05", "18:30"),
    ("18:35", "20:00"),
    ("20:00", "22:00"),
]

dash.register_page(__name__, "/")


def cache_charts(key, charts: "list[go.Figure]"):
    # Serialize the charts to JSON and store in Redis
    try:
        cache.set(key, [fig.to_plotly_json() for fig in charts])
    except Exception as e:
        return traceback.format_exc()


def get_cached_charts(key):
    # Retrieve the cached charts from Redis
    cached_charts = cache.get(key)
    if cached_charts:
        return [dcc.Graph(figure=json.loads(fig), style={"min-width": "900px", "width": "100%"}) for fig in json.loads(cached_charts)]
    return None


def filter_events(events, date):
    date_proper = dtt.datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m')
    date_to_check = dtt.datetime.strptime(date, '%Y-%m-%d')
    pattern = re.compile(r"\d{2}\.\d{2}")
    pattern_between = re.compile(r"(\d{2}\.\d{2})\s*-\s*(\d{2}\.\d{2})")
    def is_not_weekly(description, date):
        dates = re.findall(pattern, description)
        dates_between = re.findall(pattern_between, description)
        for start_date, end_date in dates_between:
            dleft = dtt.datetime.strptime(start_date, '%d.%m')
            dright = dtt.datetime.strptime(end_date, '%d.%m')
            if dleft <= date_to_check <= dright:
                return True
        if not dates:
            return True
        return date in dates
    df = pd.DataFrame([
        {'description': event.description, 'building': event.building, 'room': event.room, 'time_start': event.time_start, 'time_finish': event.time_finish}
        for event in events 
        if is_not_weekly(event.description, date_proper)
    ])
    df[['stime', 'ftime']] = df[['time_start', 'time_finish']]
    df['time_start'] = pd.to_datetime(df['time_start'], format='%H:%M')
    df['time_finish'] = pd.to_datetime(df['time_finish'], format='%H:%M')
    df["description"] = df["description"].apply(lambda x: '<br>'.join(re.findall('.{1,30}(?:\\s+|$)', x)))
    df["weekly"] = df["description"].apply(lambda x: ("False" if re.findall(pattern, x) else "True"))
    return df

NULL_PLOT = {"layout": {
    "xaxis": {"visible": False},
    "yaxis": {"visible": False},
    "annotations": [{
        "text": "На этот день<br>не запланировано мероприятий",
        "xref": "paper",
        "yref": "paper",
        "showarrow": False,
        "font": {"size": 28}
    }]
}}

def process_room_name(room_name: str):
    if room_name.startswith('!'):
        return f"<b>{room_name[1:]}</b>"
    return room_name

@cache.memoize(expire=60*60*48)
def get_event_charts(selected_date, building, theme="navy"):
    events = dbm.get_events(selected_date)
    filtered_df = filter_events(events, selected_date)
    charts = generate_gantt_charts(filtered_df, building, theme)
    return charts

def generate_gantt_charts(df, building, theme="navy"):
    df = df[df['building'] == building]
    if df.empty:
        return None
    rooms = sorted(dbm.get_rooms_gantt(building))
    room_groups = []
    i = 0
    for room in rooms:
        if i % 10 == 0:
            room_groups.append([])
        room_groups[-1].append(room)
        i += 1
    df_groups = [
        df[df["room"].isin(room_group)]
        for room_group in room_groups
    ]
    for i, df_group in enumerate(df_groups):
        for room in room_groups[i]:
            if room not in df_group["room"].values:
                rdf = pd.Series({
                    "time_start":dtt.datetime.strptime("07:30", '%H:%M'),
                    "time_finish":dtt.datetime.strptime("08:30", '%H:%M'),
                    "description":"NaE",
                    "stime":"07:30",
                    "ftime":"08:30",
                    "weekly":"True",
                    "room":room,
                })
                df_groups[i] = pd.concat([df_groups[i], rdf.to_frame().T], ignore_index=True)
    line_dash_map = {"True": "", "False": "x"}
    figs = []
    while len(figs) < len(room_groups):
        try:
            for i, df_group in enumerate(df_groups):
                fig = px.timeline(
                    df_group,
                    x_start="time_start",
                    x_end="time_finish",
                    y="room",
                    color="room",
                    custom_data=["description", "stime", "ftime"],
                    labels={"room": "Room"},
                    color_discrete_sequence=(BUILDING_PALETTES[building] if theme == "navy" else BUILDING_PALETTES["Roomba"]),
                    range_x=[dtt.datetime.strptime("08:30", '%H:%M'), dtt.datetime.strptime("22:30", '%H:%M')],
                    pattern_shape="weekly",
                    pattern_shape_map=line_dash_map,
                    category_orders={"room": room_groups[i][::-1]},
                )
                ticktext = [slot[0] for slot in TIME_SLOTS] + [TIME_SLOTS[-1][1]]
                tickvals = [dtt.datetime.strptime(tick, '%H:%M') for tick in ticktext]
                fig.update_xaxes(
                    tickmode="array",
                    tickvals=tickvals,
                    ticktext=ticktext,
                )
                y_labels = [process_room_name(room) for room in room_groups[i][::-1]]
                fig.update_yaxes(
                    categoryarray=room_groups[i][::-1],
                    ticktext=y_labels,
                    tickvals=room_groups[i][::-1],
                )
                num_rooms = len(room_groups[i])
                fig.update_traces(hovertemplate="<b>%{y}</b><br>%{customdata[1]} - %{customdata[2]}<br><br>%{customdata[0]}<extra></extra>")
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="",
                    showlegend=False,
                    dragmode=False,
                    modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale", "resetScale"],
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                fig.update_layout(height=80 + num_rooms * 45 - (20 if num_rooms == 1 else 0))
                for slot in TIME_SLOTS:
                    start = pd.to_datetime(slot[0], format='%H:%M')
                    finish = pd.to_datetime(slot[1], format='%H:%M')
                    fig.add_vline(x=start, line=dict(color="gray", dash="dash", width=1))
                    fig.add_vline(x=finish, line=dict(color="gray", dash="dash", width=1))
                figs.append(fig)
        except ValueError as e:
            figs = []
            # logging.error(e)
            continue
        else:
            break
    return figs

@callback(
    Output("gantt-charts", "children"),
    Input("building-nav-store", "data"),
    Input('date-picker', 'date'),
)
def show_gantt_charts(selection, selected_date):
    if selection in BUILDING_SECTIONS:
        buildings = BUILDING_SECTIONS[selection]
    else:
        buildings = [selection]
    ret = []
    for bld in buildings:
        figures = get_event_charts(selected_date, bld)
        if figures:
            if selected_date == dtt.datetime.now().strftime('%Y-%m-%d'):
                now = dtt.datetime.strptime(dtt.datetime.now().strftime('%H:%M'), '%H:%M')
                for chart in figures:
                    chart: go.Figure
                    chart.add_vline(x=now, line=dict(color="red", width=2))
            charts = [dcc.Graph(figure=fig, style={"min-width": "900px", "width": "100%"}) for fig in figures]
        else:
            charts = html.H1("На этот день нет мероприятий", className="text-center text-muted m-4")
        ret.append(dbc.Card([
            dbc.CardHeader(
                html.Button(
                    f"{bld}",
                    id=f"group-{bld}-toggle",
                    className="btn",
                    **{"data-bs-toggle": "collapse", "data-bs-target": f"#collapse-{bld}"},
                    style={
                        "color": "white", "font-weight": "800",
                        "font-size": "20px"
                    }
                ), style={"background-color": BUILDING_PALETTES[bld][0]},
                id=f"card-header-{bld}", className="sticky-header"
            ),
            dbc.Collapse(
                html.Div(charts, id=f"gantt-chart-{bld}"),
                id=f"collapse-{bld}",
                is_open=True,
                style={"overflow-x": "auto"}
            ),
        ], className="mb-4 pb-1", id=f"card-{bld}"))
    return ret


# @callback(
#     Output("scripts", "children"),
#     Input("main_header", "children"),
# )
# def add_scripts(*_):
#     return [
#         html.Script(src=("assets/js/bootstrap.bundle.min.js")),
#         html.Script(src=("assets/collapse.js")),
#     ]


# @callback(
#     [Output("card-header-"+building, "style") for building in BUILDINGS],
#     Input("theme-switch", "value")
# )
# def change_theme(theme):
#     if theme == "navy":
#         return [{"background-color": BUILDING_PALETTES[building][0]} for building in BUILDINGS]
#     dbm.counter_plus_one("use_roomba_theme")
#     return [{"background-color": BUILDING_PALETTES["Roomba"][i % 3]} for i, _ in enumerate(BUILDINGS)]

# @app.callback(
#     [Output(f"collapse-{building}", "is_open") for building in BUILDINGS],
#     [Input(f"group-{building}-toggle", "n_clicks") for building in BUILDINGS],
#     [State(f"store-{building}", "data") for building in BUILDINGS]
# )
# def toggle_collapse(*args):
#     ctx = dash.callback_context
#     if not ctx.triggered:
#         return [True] * len(BUILDINGS)
#     button_id = ctx.triggered[0]['prop_id'].split('.')[0]
#     building = button_id.split('-')[1]
#     is_open = args[len(BUILDINGS) + BUILDINGS.index(building)]['is_open']
#     return [not is_open if f"group-{building}-toggle" == button_id else is_open for building in BUILDINGS]

@callback(
    Output("fr-modal", "is_open"),
    Input("fr-button", "n_clicks"),
    Input("fr-close", "n_clicks"),
    State("fr-modal", "is_open"),
    prevent_initial_call=True
)
@track_usage("open_free_rooms")
def toggle_free_rooms(_a, _b, is_open):
    return not is_open

@callback(
    Output("free-rooms", "children", allow_duplicate=True),
    Input("fr-submit", "n_clicks"),
    State("fr-building-dropdown", "value"),
    State("fr-time", "value"),
    State("date-picker", "date"),
    prevent_initial_call=True,
)
@track_usage("show_free_rooms")
def show_free_rooms(n_clicks, building, time, date):
    if not time:
        time = dtt.datetime.now().strftime('%H:%M')
    else:
        dbm.counter_plus_one("free_rooms_time_set")
    free_rooms = dbm.get_free_rooms(time, date)
    if building != "all":
        dbm.counter_plus_one("filtered_free_rooms_building")
        free_rooms = [room for room in free_rooms if room[1] == building]
    return html.Ul([
        html.Li([
            html.Span(
                room[0].strip("!")+"  ",
                style=({
                    "color": (BUILDING_PALETTES[room[1]][0] if room[1] in BUILDING_PALETTES else BUILDING_PALETTES["Roomba"][0]),
                    "font-weight": "700"
                } if room[0].startswith("!") else {})
            ),
            html.Span(room[1], style={
                "color": (BUILDING_PALETTES[room[1]][0] if room[1] in BUILDING_PALETTES else BUILDING_PALETTES["Roomba"][0]),
                "font-weight": "700"}
            )
        ])
        for room in free_rooms
    ])


@callback(
    Output("fr-header", "children"),
    Output("free-rooms", "children"),
    Input("date-picker", "date"),
)
def update_fr_header(selected_date):
    return f"Свободные аудитории {selected_date}", None

@callback(
    Output("building-nav-store", "data"),
    Input({"type": "building-nav", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def set_building_nav(_):
    index = dash.callback_context.triggered_id["index"]
    return index


layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("График занятости аудиторий", className="text-center"), className="mb-4 mt-4"),
        ]),
        dbc.Row([
            dbc.Col([
                html.P("Выберите дату чтобы проверить занятость"),
                dcc.DatePickerSingle(
                    id='date-picker',
                    date=pd.to_datetime('today').date(),  # Default to today's date
                    display_format='YYYY-MM-DD',
                    className="mb-4",
                    first_day_of_week=1,
                    style={"z-index": "15"}
                )
            ]),
            dbc.Col([
               html.Button("Свободные аудитории", id="fr-button", className="btn btn-primary", style={"width": "100%"})
            ]),
            dbc.Col([
                html.Div([
                    dbc.RadioItems(
                        id="theme-switch",
                        class_name="btn-group",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-primary",
                        labelCheckedClassName="active",
                        options=[
                            {"label": "Навигация", "value": "navy"},
                            {"label": "Roomba", "value": "roomba"},
                        ],
                        value="navy",
                    )
                ], className="radio-group", style={"margin-left": "auto", "width": "auto"}),
                dbc.DropdownMenu([
                    dbc.DropdownMenuItem(
                        btn["label"], id={"type": "building-nav", "index": btn["value"]}, style=btn["style"],
                        class_name="mx-0 my-1"
                    )
                    for btn in BUILDING_NAVIGATION
                ], style={"margin-right": "auto"}, label="Перейти к", className="my-2"),
                dcc.Store(id="building-nav-store", data="ГК"),
            ], width="auto"),
        ], className="d-flex justify-content-between"),
        dbc.Row([
            dcc.Loading([
                html.Div([
                    dcc.Store(id=f"store-{building}", data={"is_open": True})
                    for building in BUILDINGS
                ], id="stores"),
                dbc.Col(html.Div(id='gantt-charts')),
            ], type="cube", fullscreen=True, style={"z-index": 9999})
        ])
    ]),
    dbc.Modal([
        dbc.ModalHeader("Свободные аудитории", id="fr-header"),
        dbc.ModalBody([
            html.Div([
                dcc.Dropdown([
                    {"label": html.Span("Все"), "value": "all"}
                ]+[
                    {"label": html.Span(building, style={
                        'color': BUILDING_PALETTES[building][0],
                        'font-weight': '700',
                    }), "value": building}
                    for building in BUILDINGS
                ], value='all', id="fr-building-dropdown", style={"min-width": "160px"}, clearable=False),
                dcc.Input(
                    id="fr-time", type="time", required=False, placeholder="Сейчас",
                    style={"height": "36px"}, className="mx-1"
                ),
                html.Button("Показать", id="fr-submit", className="btn btn-primary")
            ], className="d-flex justify-content-between"),
            html.Div(id="free-rooms")
        ], style={"min-height": "500px"}),
        dbc.ModalFooter(
            dbc.Button("Закрыть", id="fr-close", className="btn btn-secondary ms-auto")
        )
    ], scrollable=True, id="fr-modal", is_open=False, backdrop='static'),
    
    html.Div(id="scripts")
])