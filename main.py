from flask import request, redirect, url_for, session, render_template, jsonify, make_response
from dash import Dash, html, page_container, callback, Input, Output, no_update, State, set_props
from dash import dcc
import dash_bootstrap_components as dbc
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import datetime as dtt
from sendemail import send_email
import requests
import traceback
from utils import track_usage, server, dbm, WEEKDAYS
from new_features import new_features
import sys


SEARCH_RESULT_LIMIT = 25

def error_handler(err):
    set_props("error_report", {"children": traceback.format_exception(err)})

GOOGLE = "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap"
application = Dash("Folegle", title="Folegle", server=server, external_stylesheets=[
    dbc.themes.BOOTSTRAP, GOOGLE, "static/style.css",
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
], use_pages=True, on_error=error_handler)

with open("keys/DEBUG") as f:
    IS_DEBUG = f.read().strip() == "True"


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
    Output("new-features-modal", "is_open"),
    Input("new-features-button", "n_clicks"),
    State("new-features-modal", "is_open"),
    prevent_initial_call=True
)
@track_usage("open_new_features")
def toggle_new_features(n_clicks, is_open):
    return not is_open


application.layout = html.Div([
    dbc.Navbar(dbc.Container([
        dbc.NavbarBrand(
            [html.Img(src=application.get_asset_url("icon.png"), height="30px", style={"margin-right": "10px"}, id="main_header"), "Folegle"],
            href="/", className="d-flex align-items-center", style={"font-weight": "800", "color": "white"}
        ),
        dbc.Nav([
            dbc.NavItem(dbc.NavLink("График", href="/")),
            dbc.NavItem(dbc.NavLink("Аудитории", href="/rooms")),
        ], class_name="fw-bold", navbar=True),
    ]), style={"background-image": "var(--main-gradient)", "color": "white"}, dark=True),
    # html.Div(
    #     html.Header("Folegle", id="main_header"),
    #     className="header-fullwidth",
    #     # style={"height": "12rem"}
    # ),
    # dbc.Breadcrumb(),
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
    dcc.Location(id='redirect', refresh=True),
    page_container,
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
    html.Div(id="error_report"),
    html.Footer(dbc.Container(dbc.Row(dbc.Col(
        html.Div(["Собрано ", html.A("Folegle", href="https://t.me/folegle")," - для ", html.A("МКИ (Студсовета МФТИ)", href="https://t.me/mki_mipt")], className="small m-0")
    ), class_name="align-items-center justify-content-between flex-column flex-sm-row"), className="px-5"), className="bg-white py-1 mt-auto", id="footer"),
])

@callback(
    Output("redirect", "pathname"),
    Input("main_header", "n_clicks")
)
def go_home(_):
    if not(dbm.verify_password(request.cookies.get('password')) or IS_DEBUG):
        return url_for('request_password')
    return no_update

@server.route('/login', methods=['GET', 'POST'])
@track_usage("login_page")
def login():
    if 'password' in request.args:
        password = request.args.get('password')
        if dbm.check_password(password):
            session['password'] = password
            response = redirect(url_for('/'))
            response.set_cookie('password', password, max_age=60*60*24)  # Store password in cookies for 30 days
            return response
    if request.method == 'POST':
        password = request.form.get('password')
        if dbm.check_password(password):
            session['password'] = password
            response = redirect(url_for('/'))
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
    if (("dash" in request.path or request.path == "/" or request.path == "/rooms") and not dbm.verify_password(request.cookies.get('password'))):
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
            server.run(port=8050, debug=True)
            # server.run(host='0.0.0.0', ssl_context=('local.crt', 'local.key'))