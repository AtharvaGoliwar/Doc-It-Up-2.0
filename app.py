# app.py
# Import necessary libraries
from flask import Flask, request, render_template
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS
import eventlet

# It's good practice to monkey patch at the beginning
eventlet.monkey_patch()

# -----------------------------------------------------------------------------
# App Initialization
# -----------------------------------------------------------------------------

# Initialize the Flask application
# The template_folder='templates' is the default, but we make it explicit here.
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your-very-secret-key!'

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Flask-SocketIO with eventlet as the async_mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', max_http_buffer_size=10 * 1024 * 1024)

# -----------------------------------------------------------------------------
# NEW: HTTP Route to Serve the Frontend
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """
    This route serves the main HTML page of the chat application.
    """
    return render_template('index.html')

# -----------------------------------------------------------------------------
# Data Storage (In-Memory)
# -----------------------------------------------------------------------------

users_in_room = {}

# -----------------------------------------------------------------------------
# SocketIO Event Handlers (No changes here)
# -----------------------------------------------------------------------------

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    if request.sid in users_in_room:
        user = users_in_room[request.sid]
        username = user['username']
        room = user['room']
        del users_in_room[request.sid]
        leave_room(room)
        emit('status', {'msg': f'{username} has left the room.'}, to=room)

@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    room = data.get('room')
    if not username or not room:
        return

    if request.sid in users_in_room:
        old_room = users_in_room[request.sid]['room']
        old_username = users_in_room[request.sid]['username']
        leave_room(old_room)
        emit('status', {'msg': f'{old_username} has left the room.'}, to=old_room)

    users_in_room[request.sid] = {'username': username, 'room': room}
    join_room(room)
    emit('status', {'msg': f'{username} has joined the room.'}, to=room)
    print(f"User {username} ({request.sid}) joined room: {room}")

@socketio.on('send_message')
def handle_send_message(data):
    room = data.get('room')
    if not room:
        return
    emit('receive_message', data, to=room)
    print(f"Message from {data.get('sender')} in room {room}")
