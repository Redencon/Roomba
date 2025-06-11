import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from flask import Flask
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sql import Base, Room, Events, db
import pandas as pd
import dash_bootstrap_components as dbc

# Initialize Flask and Dash
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Database setup
DATABASE_URL = "sqlite:///db.sqlite"  # Update with your database URL
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Fetch all rooms
rooms = session.scalars(select(Room).order_by(Room.building, Room.room)).all()
room_ids = [room.id for room in rooms]

# Layout
app.layout = dbc.Container([
    dbc.Button('Next Room', id='next-room-button', n_clicks=0),
    dcc.Store(id='current-room-index', data=0),
    html.Div(id='room-content'),
])

@app.callback(
    Output('current-room-index', 'data'),
    Input('next-room-button', 'n_clicks'),
    State('current-room-index', 'data')
)
def update_room_index(n_clicks, current_index):
    return (current_index + 1) % len(room_ids)


events_df = pd.read_csv('data/sus.csv')

@app.callback(
    Output('room-content', 'children'),
    Input('current-room-index', 'data')
)
def display_room_content(current_index):
    room_id = room_ids[current_index]
    room = session.scalars(select(Room).where(Room.id == room_id)).one()
    
    # Load events from CSV
    room_events = events_df[(events_df['room'] == room.room.strip("!")) & (events_df['building'] == room.building)]
    
    event_list = html.Ul([html.Li(f"{row['description']}") for index, row in room_events.iterrows()])
    
    return html.Div([
        html.H3(f"Room: {room.room} in Building: {room.building}"),
        html.P(f"Room Type: {room.room_type.name}"),
        html.P(f"Status: {room.status}"),
        html.P(f"Status Description: {room.status_description}"),
        html.H4("Events:"),
        event_list
    ])

if __name__ == '__main__':
    app.run_server(debug=True)