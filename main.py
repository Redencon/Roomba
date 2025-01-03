import flask
from flask import request, redirect, url_for, session, render_template, jsonify, make_response
import secrets
from dash import Dash, dcc, html, Input, Output, callback, State
import diskcache as dc
import dash_bootstrap_components as dbc
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import datetime as dtt
import re
from sendemail import send_email
from sql import DatabaseManager, Events, Passwords, WEEKDAYS
import requests
import traceback
from new_features import new_features
import logging
from functools import wraps
import sys

# Configuration
PASSWORD = "your_password"
SECRET_KEY = "your_secret_key"

server = flask.Flask(__name__)
server.secret_key = "MyNameIsNotDiana"
GOOGLE = "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap"
application = Dash("Folegle", title="Folegle", server=server, external_stylesheets=[
    dbc.themes.BOOTSTRAP, GOOGLE, "static/style.css",
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
], routes_pathname_prefix='/dash/')
with open("keys/SQL") as f:
    sql_url = f.read().strip()
server.config['SQLALCHEMY_DATABASE_URI'] = sql_url
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
dbm = DatabaseManager(server)

# Initialize Redis client
cache = dc.Cache("cache")

with open("keys/DEBUG") as f:
    IS_DEBUG = f.read().strip() == "True"
SEARCH_RESULT_LIMIT = 25

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

BUILDINGS = [
    'ГК', 'ЛК', 'Квант', 'КПМ', 'Цифра', 'Арктика', 'БК', 'УПМ', 'КМО'
]

BUILDING_PALETTES = {
    'ГК': ["#00A19A", "#00E2D7", "#00635E"],
    'ЛК': ["#6F4822", "#A86C34", "#4C3117"],
    'Квант': ["#F7A823", "#FFDA38", "#AF761A"],
    'КПМ': ["#1E67AC", "#2B92F2", "#123F68"],
    'Цифра': ["#B43D3E", "#E54E50", "#7A292A"],
    'Арктика': ["#8C7EB8", "#AB9AE0", "#675D87"],
    'БК': ["#87B145", "#A6D854", "#678734"],
    'УПМ': ["#AF447F", "#E057A2", "#7F315C"],
    'КМО': ["#F47742", "#FF9C75", "#B55830"],
    'Roomba': ["#6678B9", "#ED6A66", "#FAB62F"]
}

# def filter_data_for_day(data, selected_date):
#     df = pd.DataFrame(data)
#     df["description"] = df["description"].str.split(r"\s*//\s*")
#     df = df.explode("description")
#     df['building'] = df['audience_number'].apply(lambda x: x.split()[1])
#     df['room'] = df['audience_number'].apply(lambda x: x.split()[0])
#     room_order = sorted(df["room"].unique())
#     df['room'] = pd.Categorical(df['room'], categories=room_order, ordered=True)
#     df[['day', 'time']] = df['pair'].apply(lambda d: pd.Series(d['name'].split()[1:]))
#     df['day'] = df['day'].astype(int)
#     df[['time_start', 'time_finish']] = df['time'].apply(lambda x: pd.Series(TIME_SLOTS[x]))
#     df[['stime', 'ftime']] = df[['time_start', 'time_finish']]
#     df['time_start'] = pd.to_datetime(df['time_start'], format='%H:%M')
#     df['time_finish'] = pd.to_datetime(df['time_finish'], format='%H:%M')
#     selected_date = dtt.datetime.strptime(selected_date, '%Y-%m-%d')
#     pattern = re.compile(r"\d{2}\.\d{2}")
#     def is_not_weekly(description, date):
#         dates = re.findall(pattern, description)
#         if not dates:
#             return True
#         return date.strftime('%d.%m') in dates
#     df = df[df['description'].apply(lambda x: is_not_weekly(x, selected_date))]
#     weekday = selected_date.weekday()+1
#     filtered_df = df[(df['day'] == weekday)]
    
#     return filtered_df

def track_usage(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            dbm.counter_plus_one(name)
            return func(*args, **kwargs)
        return wrapper
    return decorator


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
        return [go.Figure(NULL_PLOT)]
    rooms = sorted(dbm.get_all_rooms(building))
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


for building in BUILDINGS:
    @callback(
        Output(f'gantt-chart-{building}', 'children'),
        Input('date-picker', 'date'),
        Input('theme-switch', 'value')
    )
    def update_gantt_charts(selected_date, theme, building=building):
        charts = get_event_charts(selected_date, building, theme)
        if selected_date == dtt.datetime.now().strftime('%Y-%m-%d'):
            print("Adding current time line")
            now = dtt.datetime.strptime(dtt.datetime.now().strftime('%H:%M'), '%H:%M')
            for chart in charts:
                chart: go.Figure
                chart.add_vline(x=now, line=dict(color="red", width=2))
        return [dcc.Graph(figure=fig, style={"min-width": "900px", "width": "100%"}) for fig in charts]


@callback(
    Output("scripts", "children"),
    Input("main_header", "children"),
)
def add_scripts(*_):
    return [
        html.Script(src=application.get_asset_url("js/bootstrap.bundle.min.js")),
        html.Script(src=application.get_asset_url("collapse.js")),
    ]


@callback(
    Output("search-results", "children"),
    Input("search-input", "value"),
)
def search_events(query: str):
    if not query:
        return []
    dbm.counter_plus_one("non_empty_search")
    events_tuple = dbm.get_events_by_query(query)[:SEARCH_RESULT_LIMIT]
    max_score = max([score for _, score in events_tuple], default=0)

    return [
        dbc.Card([
            dbc.CardHeader(" ".join([
                WEEKDAYS[event.day],"|",
                event.time_start,"-",event.time_finish,
                "|",event.building,
                (event.room[1:] if event.room.startswith("!") else event.room)
            ])),
            dbc.CardBody(event.description)
        ], className=("faded-card" if score < max_score else "mb-1"))
        for event, score in events_tuple
    ]


@callback(
    Output("search-offcanvas", "is_open"),
    Input("search-button", "n_clicks"),
    prevent_initial_call=True
)
@track_usage("open_search")
def open_search(n_clicks):
    return True

@callback(
    [Output("card-header-"+building, "style") for building in BUILDINGS],
    Input("theme-switch", "value")
)
def change_theme(theme):
    if theme == "navy":
        return [{"background-color": BUILDING_PALETTES[building][0]} for building in BUILDINGS]
    dbm.counter_plus_one("use_roomba_theme")
    return [{"background-color": BUILDING_PALETTES["Roomba"][i % 3]} for i, _ in enumerate(BUILDINGS)]

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
    Output("new-features-modal", "is_open"),
    Input("new-features-button", "n_clicks"),
    State("new-features-modal", "is_open"),
    prevent_initial_call=True
)
@track_usage("open_new_features")
def toggle_new_features(n_clicks, is_open):
    return not is_open


application.layout = html.Div([
    html.Div(
            html.Header("Folegle", id="main_header"),
            className="header-fullwidth"
        ),
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
                    dbc.DropdownMenuItem(building, href=f"#card-{building}", style={
                        "color": palette[0],
                        "font-weight": "800",
                    }, external_link=True)
                    for building, palette in BUILDING_PALETTES.items()
                    if building != "Roomba"
                ], style={"margin-right": "auto"}, label="Перейти к", className="my-2"),
            ], width="auto"),
        ], className="d-flex justify-content-between"),
        dbc.Row([
            dcc.Loading([
                html.Div([
                    dcc.Store(id=f"store-{building}", data={"is_open": True})
                    for building in BUILDINGS
                ], id="stores"),
                dbc.Col(html.Div([
                    dbc.Card([
                        dbc.CardHeader(
                            html.Button(
                                f"{building}",
                                id=f"group-{building}-toggle",
                                className="btn",
                                **{"data-bs-toggle": "collapse", "data-bs-target": f"#collapse-{building}"},
                                style={
                                    "color": "white", "font-weight": "800",
                                    "font-size": "20px"
                                }
                            ), style={"background-color": BUILDING_PALETTES[building][0]},
                            id=f"card-header-{building}", className="sticky-header"
                        ),
                        dbc.Collapse(
                            html.Div(id=f"gantt-chart-{building}"),
                            id=f"collapse-{building}",
                            is_open=True,
                            style={"overflow-x": "auto"}
                        ),
                    ], className="mb-4 pb-1", id=f"card-{building}")
                    for building in BUILDINGS
                ], id='gantt-charts')),
            ], type="cube", fullscreen=True, style={"z-index": 9999})
        ])
    ]),
    html.Div([
        html.Button(
            html.I(className="bi bi-search"),
            id="search-button",
            className="menu-toggle",
        ),
        html.Button(
            html.I(className="bi bi-stars"),
            id="new-features-button",
            className="menu-toggle",
        ),
        html.Button(
            html.I(className="bi bi-chevron-up"),
            id="go-top-button",
            className="menu-toggle",
        ),
    ], id="hover-buttons", className="d-flex flex-column", style={
            "position": "fixed",
            "top": "20px",
            "right": "20px",
            "z-index": "100",
        }),
    dbc.Offcanvas([
        dcc.Input(id="search-input", type="text", placeholder="Поиск...", debounce=True),
        html.Br(),
        html.Div(id="search-results")
    ], id="search-offcanvas", scrollable=True, is_open=False, title="Поиск"),
    dbc.Modal([
        dbc.ModalHeader("Новое в этой версии"),
        dbc.ModalBody(new_features()),
        dbc.ModalFooter([
            "Для связи напишите Folegle в Telegram: ", html.A("@folegle", href="https://t.me/folegle")
        ])
    ], id="new-features-modal", is_open=False, scrollable=True),
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
    html.Footer(dbc.Container(dbc.Row(dbc.Col(
        html.Div(["Собрано ", html.A("Folegle", href="https://t.me/folegle")," - для ", html.A("МКИ (Студсовета МФТИ)", href="https://t.me/mki_mipt")], className="small m-0")
    ), class_name="align-items-center justify-content-between flex-column flex-sm-row"), className="px-5"), className="bg-white py-1 mt-auto"),
    html.Div(id="scripts")
])

@server.route('/login', methods=['GET', 'POST'])
@track_usage("login_page")
def login():
    if 'password' in request.args:
        password = request.args.get('password')
        if dbm.check_password(password):
            session['password'] = password
            response = redirect(url_for('index'))
            response.set_cookie('password', password, max_age=60*60*24)  # Store password in cookies for 30 days
            return response
    if request.method == 'POST':
        password = request.form.get('password')
        if dbm.check_password(password):
            session['password'] = password
            response = redirect(url_for('index'))
            response.set_cookie('password', password, max_age=60*60*24)  # Store password in cookies for 30 days
            return response
        return render_template('login.html', error="Неверный пароль. Попробуйте ещё раз.")
    return render_template('login.html')

@server.route('/request-password', methods=['GET', 'POST'])
@track_usage("request_password_page")
def request_password():
    if request.method == 'POST':
        address = request.form.get('email')
        if address:
            if "@" in address:
                return render_template("request-login.html", error="Неверный формат. Напишите только часть до @.")
            
            password = dbm.generate_password()
            proper_address = address+"@phystech.edu"
            send_email(proper_address, password)
            
            session['last_request'] = dtt.datetime.now()
            return redirect(url_for('login'))
        data = request.json
        token = data.get('token')
        try:
            if token:
                headers = {
                    'Authorization': f'OAuth {token}'
                }
                rqt_response = requests.get('https://login.yandex.ru/info', headers=headers)
                
                if rqt_response.status_code != 200:
                    return jsonify({"status": "error", "message": f"Failed to retrieve user information, {rqt_response.reason}"})
                user_info = rqt_response.json()
                email = user_info.get('default_email')
                
                # Check the domain of the email
                if not email or not email.endswith('@phystech.edu'):
                    return jsonify({"status": "error", "message": f"Invalid email domain: {email}. Please use a phystech.edu email address"})
                    # Authenticate the user and create a session
                password = dbm.generate_password()
                response = jsonify({"status": "success"})
                response.set_cookie('password', password, max_age=60*60*24)  # Store password in cookies for 30 days
                return response
            if 'last_request' in session:
                last_request = session['last_request']
                now = dtt.datetime.now(tz=last_request.tzinfo)
                if (now - last_request).total_seconds() < 60:  # Limit to 1 request per minute
                    return render_template("request-login.html", error="Слишком много запросов. Попробуйте позже.")
        except Exception as e:
            return jsonify({"status": "error", "message": traceback.format_exc()})
    return render_template('request-login.html')

@server.route('/oauth')
@track_usage("oauth_page")
def oauth():
    try:
        return render_template('oauth.html')
    except Exception as e:
        return jsonify({"status": "error", "message": traceback.format_exc()})

@server.route('/')
@track_usage("index_page")
def index():
    if dbm.verify_password(request.cookies.get('password')) or IS_DEBUG:
        return application.index()
    return redirect(url_for('request_password'))

@server.before_request
def before_request():
    if request.host.startswith('www.') and not IS_DEBUG:
        return redirect(f"{request.scheme}://folegle.ru{request.path}", code=301)
    if (request.path.startswith('/dash') and not dbm.verify_password(request.cookies.get('password'))) and not IS_DEBUG:
        dbm.counter_plus_one("unauthorized_dash_access")
        return redirect(url_for('request_password'))

@server.route('/check_events')
@track_usage("check_events_request")
def check_events():
    if not dbm.verify_password(request.cookies.get('password')):
        return redirect(url_for('request_password'))
    events = dbm.get_events(dtt.datetime.now().strftime('%Y-%m-%d'))
    if not events:
        return jsonify({"status": "error", "message": "No events found in the database."})
    
    event_list = [{"id": e.id, "description": e.description, "building": e.building, "room": e.room, "time_start": e.time_start, "time_finish": e.time_finish, "day": e.day} for e in events]
    return jsonify({"status": "success", "events": event_list})


@server.route('/get_counters')
@track_usage("get_counters_request")
def get_counters():
    if not dbm.verify_password(request.cookies.get('password')) and not IS_DEBUG:
        return redirect(url_for('request_password'))
    counters = dbm.get_all_counters()
    return jsonify({"status": "success", "counters": {k: v for k, v in counters}})


# Run the app
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "-d":
        IS_DEBUG = True
        server.run(host='0.0.0.0', ssl_context=('local.crt', 'local.key'))
    else:
        if IS_DEBUG:
            server.run(port=8050, debug=True)
        else:
            server.run(host='0.0.0.0', ssl_context=('local.crt', 'local.key'))