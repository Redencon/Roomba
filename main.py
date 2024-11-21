import flask
from flask import request, redirect, url_for, session, render_template, jsonify
import secrets
from dash import Dash, dcc, html, Input, Output, callback, State
import dash
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
# import logging

# Configuration
PASSWORD = "your_password"
SECRET_KEY = "your_secret_key"

server = flask.Flask(__name__)
server.secret_key = "MyNameIsNotDiana"
GOOGLE = "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap"
application = Dash("Roomba", title="Roomba", server=server, external_stylesheets=[
    dbc.themes.BOOTSTRAP, GOOGLE, "static/style.css",
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
], routes_pathname_prefix='/dash/')
with open("keys/SQL") as f:
    sql_username, sql_password = f.read().splitlines()
# sql_url = f"mysql+pymysql://{sql_username}:{sql_password}@localhost/u2906537_roomba"
sql_url = r"sqlite:///C:\Users\Redencon\Documents\PyScripts\Roomba\db.sqlite"
server.config['SQLALCHEMY_DATABASE_URI'] = sql_url
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
dbm = DatabaseManager(server)

IS_DEBUG = False
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
    'ГК', 'ЛК', 'Квант', 'КПМ', 'Цифра', 'Арктика', 'БК', 'УПМ'
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
    'Roomba': ["#06826A", "#3A1771", "#24C1A4", "#4B44C5"]
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

def generate_gantt_charts(df, building, is_today=False, theme="navy"):
    df = df[df['building'] == building]
    if df.empty:
        return dcc.Graph(figure=NULL_PLOT, style={"width": "100%", "height": "210px"})
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
    graphs = []
    while len(graphs) < len(room_groups):
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
                    pattern_shape_map=line_dash_map
                )
                ticktext = [slot[0] for slot in TIME_SLOTS] + [TIME_SLOTS[-1][1]]
                tickvals = [dtt.datetime.strptime(tick, '%H:%M') for tick in ticktext]
                fig.update_xaxes(
                    tickmode="array",
                    tickvals=tickvals,
                    ticktext=ticktext,
                )
                fig.update_yaxes(categoryarray=room_groups[i][::-1])
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
                if is_today:
                    fig.add_vline(x=pd.to_datetime(dtt.datetime.now().strftime("%H:%M"), format='%H:%M'), line=dict(color="red", width=2))
                for slot in TIME_SLOTS:
                    start = pd.to_datetime(slot[0], format='%H:%M')
                    finish = pd.to_datetime(slot[1], format='%H:%M')
                    fig.add_vline(x=start, line=dict(color="gray", dash="dash", width=1))
                    fig.add_vline(x=finish, line=dict(color="gray", dash="dash", width=1))
                graphs.append(dcc.Graph(figure=fig, style={"min-width": "900px", "width": "100%"}))
        except ValueError as e:
            graphs = []
            # logging.error(e)
            continue
        else:
            break
    return graphs


for building in BUILDINGS:
    @callback(
        Output(f'gantt-chart-{building}', 'children'),
        Input('date-picker', 'date'),
        Input('interval', 'n_intervals'),
        Input('theme-switch', 'value')
    )
    def update_gantt_charts(selected_date, _, theme, building=building):
        events = dbm.get_events(selected_date)
        filtered_df = filter_events(events, selected_date)
        charts = generate_gantt_charts(filtered_df, building, selected_date == pd.to_datetime('today').strftime('%Y-%m-%d'), theme)
        return charts

@callback(
    Output("interval", "interval"),
    Input("date-picker", "date"),
)
def disable_interval(selected_date):
    return 180000 if selected_date == pd.to_datetime('today').strftime('%Y-%m-%d') else 60*60*1000

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
    events = dbm.get_events_by_query(query)[:SEARCH_RESULT_LIMIT]
    
    return [
        dbc.Card([
            dbc.CardHeader(" ".join([WEEKDAYS[event.day],"|",event.time_start,"-",event.time_finish,"|",event.building,event.room])),
            dbc.CardBody(event.description)
        ])
        for event in events
    ]


@callback(
    Output("search-offcanvas", "is_open"),
    Input("search-button", "n_clicks"),
    prevent_initial_call=True
)
def open_search(n_clicks):
    return True

@callback(
    [Output("card-header-"+building, "style") for building in BUILDINGS],
    Input("theme-switch", "value")
)
def change_theme(theme):
    if theme == "navy":
        return [{"background-color": BUILDING_PALETTES[building][0]} for building in BUILDINGS]
    return [{"background-color": BUILDING_PALETTES["Roomba"][i % 2]} for i, _ in enumerate(BUILDINGS)]

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

application.layout = html.Div([
    html.Div(
            html.Header("Roomba", id="main_header"),
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
                    first_day_of_week=1
                )
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
                ], className="radio-group", style={"margin-left": "auto", "width": "auto"})
            ], width="auto"),
        ], className="d-flex justify-content-between"),
        dbc.Row([
            dcc.Loading([
                html.Div([
                    dcc.Store(id=f"store-{building}", data={"is_open": True})
                    for building in BUILDINGS
                ], id="stores"),
                dcc.Interval(id='interval', interval=180000, n_intervals=0),
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
                    ], className="mb-4 pb-1")
                    for building in BUILDINGS
                ], id='gantt-charts')),
            ], type="cube", fullscreen=True)
        ])
    ]),
    html.Button(
        html.I(className="bi bi-search"),
        id="search-button",
        className="menu-toggle",
    ),
    dbc.Offcanvas([
        dcc.Input(id="search-input", type="text", placeholder="Поиск...", debounce=True),
        html.Br(),
        html.Div(id="search-results")
    ], id="search-offcanvas", scrollable=True, is_open=False, title="Поиск"),
    html.Footer(dbc.Container(dbc.Row(dbc.Col(
        html.Div(["Собрано ", html.A("Folegle", href="https://t.me/folegle")," - для ", html.A("МКИ (Студсовета МФТИ)", href="https://t.me/mki_mipt")], className="small m-0")
    ), class_name="align-items-center justify-content-between flex-column flex-sm-row"), className="px-5"), className="bg-white py-1 mt-auto"),
    html.Div(id="scripts")
])

@server.route('/login', methods=['GET', 'POST'])
def login():
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
def request_password():
    if request.method == 'POST':
        if 'last_request' in session:
            last_request = session['last_request']
            now = dtt.datetime.now(tz=last_request.tzinfo)
            if (now - last_request).total_seconds() < 60:  # Limit to 1 request per minute
                return render_template("request-login.html", error="Слишком много запросов. Попробуйте позже.")
        
        address = request.form.get('email')
        if "@" in address:
            return render_template("request-login.html", error="Неверный формат. Напишите только часть до @.")
        
        password = dbm.generate_password()
        proper_address = address+"@phystech.edu"
        send_email(proper_address, password)
        
        session['last_request'] = dtt.datetime.now()
        return redirect(url_for('login'))
    return render_template('request-login.html')

@server.route('/')
def index():
    if dbm.verify_password(request.cookies.get('password')) or IS_DEBUG:
        return application.index()
    return redirect(url_for('request_password'))

@server.before_request
def before_request():
    if (request.path.startswith('/dash') and not dbm.verify_password(request.cookies.get('password'))) and not IS_DEBUG:
        return redirect(url_for('request_password'))

@server.route('/check_events')
def check_events():
    if not dbm.verify_password(request.cookies.get('password')):
        return redirect(url_for('request_password'))
    events = dbm.get_events(dtt.datetime.now().strftime('%Y-%m-%d'))
    if not events:
        return jsonify({"status": "error", "message": "No events found in the database."})
    
    event_list = [{"id": e.id, "description": e.description, "building": e.building, "room": e.room, "time_start": e.time_start, "time_finish": e.time_finish, "day": e.day} for e in events]
    return jsonify({"status": "success", "events": event_list})


# Run the app
if __name__ == '__main__':
    server.run(port=8050)
    # server.run(host='0.0.0.0', ssl_context=('local.crt', 'local.key'))