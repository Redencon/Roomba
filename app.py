import flask
from flask import request, redirect, url_for, session, render_template
import secrets
from dash import Dash, dcc, html, Input, Output, callback, State
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import json
import datetime as dtt
import re

# Configuration
PASSWORD = "your_password"
SECRET_KEY = "your_secret_key"

server = flask.Flask(__name__)
server.secret_key = "MyNameIsNotDiana"
GOOGLE = "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap"
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP, GOOGLE, "static/style.css"], routes_pathname_prefix='/dash/')

with open("data/events.json", "r", encoding='utf-8') as f:
    EVENTS = json.load(f)

WEEKDAYS = {
    "1": "Monday",
    "2": "Tuesday",
    "3": "Wednesday",
    "4": "Thursday",
    "5": "Friday",
    "6": "Saturday",
    "7": "Sunday",
}

TIME_SLOTS = {
    "1": ("09:00", "10:25"),
    "2": ("10:45", "12:10"),
    "3": ("12:20", "13:45"),
    "4": ("13:55", "15:20"),
    "5": ("15:30", "16:55"),
    "6": ("17:05", "18:30"),
    "7": ("18:35", "20:00"),
    "8": ("20:00", "22:00"),
}

BUILDINGS = [
    'ГК', 'Квант', 'КПМ', 'Цифра', 'БК', 'УПМ', 'None'
]

def filter_data_for_day(data, selected_date):
    df = pd.DataFrame(data)
    df["description"] = df["description"].str.split(r"\s*//\s*")
    df = df.explode("description")
    df['building'] = df['audience_number'].apply(lambda x: x.split()[1])
    df['room'] = df['audience_number'].apply(lambda x: x.split()[0])
    room_order = sorted(df["room"].unique())
    df['room'] = pd.Categorical(df['room'], categories=room_order, ordered=True)
    df[['day', 'time']] = df['pair'].apply(lambda d: pd.Series(d['name'].split()[1:]))
    df['day'] = df['day'].astype(int)
    df[['time_start', 'time_finish']] = df['time'].apply(lambda x: pd.Series(TIME_SLOTS[x]))
    df[['stime', 'ftime']] = df[['time_start', 'time_finish']]
    df['time_start'] = pd.to_datetime(df['time_start'], format='%H:%M')
    df['time_finish'] = pd.to_datetime(df['time_finish'], format='%H:%M')
    selected_date = dtt.datetime.strptime(selected_date, '%Y-%m-%d')
    pattern = re.compile(r"\d{2}\.\d{2}")
    def is_not_weekly(description, date):
        dates = re.findall(pattern, description)
        if not dates:
            return True
        return date.strftime('%d.%m') in dates
    df = df[df['description'].apply(lambda x: is_not_weekly(x, selected_date))]
    weekday = selected_date.weekday()+1
    filtered_df = df[(df['day'] == weekday)]
    
    return filtered_df

NULL_PLOT = {"layout": {
    "xaxis": {"visible": False},
    "yaxis": {"visible": False},
    "annotations": [{
        "text": "No bookings for this day",
        "xref": "paper",
        "yref": "paper",
        "showarrow": False,
        "font": {"size": 28}
    }]
}}

def generate_gantt_chart(df, building, is_today=False):
    df = df[df['building'] == building]
    if df.empty:
        return NULL_PLOT
    fig = px.timeline(
        df,
        x_start="time_start",
        x_end="time_finish",
        y="room",
        color="room",
        # hover_data=["description", "time_start_str", "time_finish_str"],
        # custom_data=["description", "time_start_str", "time_finish_str"],
        custom_data=["description", "stime", "ftime"],
        labels={"room": "Room"},
        range_x=[
            pd.to_datetime("08:30", format='%H:%M'),
            pd.to_datetime("22:30", format='%H:%M')
        ],
        color_discrete_sequence=["#06826A", "#3A1771", "#24C1A4", "#4B44C5"]
    )
    num_rooms = len(df["room"].unique())
    fig.update_xaxes(tickformat="%H:%M")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>%{customdata[1]} - %{customdata[2]}<br><br>%{customdata[0]}<extra></extra>")
    fig.update_layout(
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        dragmode=False,
        modebar_remove=["zoom", "pan", "select", "lasso", "zoomIn", "zoomOut", "autoScale", "resetScale"],
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    fig.update_layout(height=150 + num_rooms * 40)
    if is_today:
        fig.add_vline(x=pd.to_datetime(dtt.datetime.now().strftime("%H:%M"), format='%H:%M'), line=dict(color="red", width=2))
    
    for slot in TIME_SLOTS.values():
        start = pd.to_datetime(slot[0], format='%H:%M')
        finish = pd.to_datetime(slot[1], format='%H:%M')
        fig.add_vline(x=start, line=dict(color="gray", dash="dash", width=1))
        fig.add_vline(x=finish, line=dict(color="gray", dash="dash", width=1))
    return fig

for building in BUILDINGS:
    @callback(
        Output(f'gantt-chart-{building}', 'figure'),
        Input('date-picker', 'date'),
        Input('interval', 'n_intervals')
    )
    def update_gantt_charts(selected_date, _, building=building):
        filtered_df = filter_data_for_day(EVENTS, selected_date)
        fig = generate_gantt_chart(filtered_df, building, selected_date == pd.to_datetime('today').strftime('%Y-%m-%d'))
        return fig

@callback(
    Output("scripts", "children"),
    Input("main_header", "children"),
)
def add_scripts(*_):
    return [
        html.Script(src=app.get_asset_url("js/bootstrap.bundle.min.js")),
        html.Script(src=app.get_asset_url("collapse.js")),
    ]

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

app.layout = html.Div([
    html.Div(
            html.Header("Roomba", id="main_header"),
            className="header-fullwidth"
        ),
    dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Room Availability Dashboard", className="text-center"), className="mb-4 mt-4")
        ]),
        dbc.Row([
            html.P("Select a date to view room availability for that day"),
            dcc.DatePickerSingle(
                id='date-picker',
                date=pd.to_datetime('today').date(),  # Default to today's date
                display_format='YYYY-MM-DD',
                className="mb-4"
            )
        ], className="d-flex"),
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
                                className="btn btn-link",
                                **{"data-bs-toggle": "collapse", "data-bs-target": f"#collapse-{building}"}
                            )
                        ),
                        dbc.Collapse(
                            dcc.Graph(id=f"gantt-chart-{building}"),
                            id=f"collapse-{building}",
                            is_open=True
                        ),
                    ], className="mb-4 pb-1")
                    for building in BUILDINGS
                ],id='gantt-charts')),
            ], type="cube", fullscreen=True)
        ])
    ]),
    html.Div(id="scripts")
])

@server.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == PASSWORD:
            session['token'] = SECRET_KEY
            return redirect(url_for('index'))
    return render_template('login.html')

@server.route('/request-password', methods=['GET', 'POST'])
def request_password():
    if request.method == 'POST':
        email = request.form.get('email')
        unique_password = secrets.token_urlsafe(16)
        # Save the unique password for the user (e.g., in a database or a file)
        # For simplicity, we'll just print it here
        print(f"Generated password for {email}: {unique_password}")
        # send_email(email, unique_password)
        return redirect(url_for('login'))
    return render_template('request_password.html')

@server.route('/')
def index():
    if session.get('token') == SECRET_KEY:
        return app.index()
    return redirect(url_for('login'))

@app.server.before_request
def before_request():
    if request.path.startswith('/dash') and session.get('token') != SECRET_KEY:
        return redirect(url_for('login'))

# Run the app
if __name__ == '__main__':
    app.run()