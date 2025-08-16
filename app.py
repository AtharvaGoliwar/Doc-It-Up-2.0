# app.py
# Import necessary libraries
from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS

# -----------------------------------------------------------------------------
# App Initialization
# -----------------------------------------------------------------------------

# Initialize the Flask application
app = Flask(__name__)
# It's good practice to set a secret key, though not strictly necessary for SocketIO
app.config['SECRET_KEY'] = 'your-very-secret-key!'

# Enable Cross-Origin Resource Sharing (CORS) to allow your frontend,
# which may be on a different domain, to connect to this backend.
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Flask-SocketIO
# The 'cors_allowed_origins' argument is crucial for allowing frontend connections.
# "*" allows connections from any origin. For production, you should restrict
# this to your frontend's actual domain.
# We increase max_http_buffer_size to allow for larger file transfers (e.g., 10MB)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10 * 1024 * 1024)

# -----------------------------------------------------------------------------
# Data Storage (In-Memory)
# -----------------------------------------------------------------------------

# A simple in-memory dictionary to store user information.
# The key is the session ID (request.sid) and the value is a dictionary
# containing the username and the current room.
# In a production application, you would use a database (like Redis or a SQL DB)
# for more persistent and scalable user management.
users_in_room = {}

# -----------------------------------------------------------------------------
# SocketIO Event Handlers
# -----------------------------------------------------------------------------

@socketio.on('connect')
def handle_connect():
    """
    This event is triggered when a new client connects to the server.
    It's a good place for initial setup or logging.
    """
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """
    This event is triggered when a client disconnects.
    It's crucial to clean up user data and notify others in the room.
    """
    print(f"Client disconnected: {request.sid}")
    # Check if the disconnected user was in a room
    if request.sid in users_in_room:
        # Retrieve user details before removing them
        user = users_in_room[request.sid]
        username = user['username']
        room = user['room']

        # Remove the user from the room's user list
        del users_in_room[request.sid]

        # Explicitly have the user leave the SocketIO room
        leave_room(room)

        # Emit a 'status' message to the room to notify other users
        emit('status', {'msg': f'{username} has left the room.'}, to=room)


@socketio.on('join')
def handle_join(data):
    """
    Handles a user's request to join a room.
    The client should send a 'join' event with a JSON payload
    containing 'username' and 'room'.
    """
    username = data.get('username')
    room = data.get('room')

    if not username or not room:
        # You might want to send an error back to the client here
        return

    # If user was in a previous room, leave it
    if request.sid in users_in_room:
        old_room = users_in_room[request.sid]['room']
        old_username = users_in_room[request.sid]['username']
        leave_room(old_room)
        emit('status', {'msg': f'{old_username} has left the room.'}, to=old_room)

    # Add the user to our in-memory user list
    users_in_room[request.sid] = {'username': username, 'room': room}

    # Use the join_room function to subscribe the client to a specific room
    join_room(room)

    # Emit a 'status' message to the room to notify other users
    # The 'to=room' argument ensures this message only goes to clients in this room.
    emit('status', {'msg': f'{username} has joined the room.'}, to=room)
    print(f"User {username} ({request.sid}) joined room: {room}")


@socketio.on('send_message')
def handle_send_message(data):
    """
    Handles incoming messages from a client.
    The client sends a rich data object which we will broadcast to the room.
    The data object contains 'room', 'sender', 'type', and content.
    """
    room = data.get('room')
    if not room:
        return

    # UPDATED LINE: We now emit to everyone in the room, including the sender.
    # The `to=room` argument ensures it only goes to clients in the specified room.
    emit('receive_message', data, to=room)
    print(f"Message from {data.get('sender')} in room {room}")


# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # The entry point for running the Flask application.
    # 'host="0.0.0.0"' makes the server accessible from any network interface,
    # which is useful for development and testing.
    # 'debug=True' enables Flask's debug mode for easier development.
    print("Starting Flask-SocketIO server...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
