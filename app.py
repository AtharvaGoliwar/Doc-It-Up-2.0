# app.py
# Import necessary libraries
from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS
import eventlet # Required for Gunicorn

# It's good practice to monkey patch at the beginning
eventlet.monkey_patch()

# -----------------------------------------------------------------------------
# App Initialization
# -----------------------------------------------------------------------------

# Initialize the Flask application
app = Flask(__name__)
# It's good practice to set a secret key
app.config['SECRET_KEY'] = 'your-very-secret-key!'

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Flask-SocketIO with eventlet as the async_mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', max_http_buffer_size=10 * 1024 * 1024)

# -----------------------------------------------------------------------------
# Data Storage (In-Memory)
# -----------------------------------------------------------------------------

users_in_room = {}

# -----------------------------------------------------------------------------
# SocketIO Event Handlers
# -----------------------------------------------------------------------------

@socketio.on('connect')
def handle_connect():
    """
    This event is triggered when a new client connects to the server.
    """
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """
    This event is triggered when a client disconnects.
    """
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
    """
    Handles a user's request to join a room.
    """
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
    """
    Handles incoming messages from a client.
    """
    room = data.get('room')
    if not room:
        return
    emit('receive_message', data, to=room)
    print(f"Message from {data.get('sender')} in room {room}")

# NOTE: The if __name__ == '__main__': block is removed as Gunicorn will run the app.
