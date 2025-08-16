# app.py
# Import necessary libraries
import os
import uuid
from flask import Flask, request, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS
import eventlet

# It's good practice to monkey patch at the beginning
eventlet.monkey_patch()

# -----------------------------------------------------------------------------
# App Initialization
# -----------------------------------------------------------------------------

# Create an upload folder if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'your-very-secret-key!'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', max_http_buffer_size=10 * 1024 * 1024)

# -----------------------------------------------------------------------------
# HTTP Routes
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file uploads."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        # Create a unique filename to prevent overwrites
        filename = str(uuid.uuid4()) + "_" + file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Return the URL to access the file
        file_url = f"/uploads/{filename}"
        return jsonify({"url": file_url, "name": file.filename, "size": os.path.getsize(filepath)})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serves uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -----------------------------------------------------------------------------
# Data Storage (In-Memory)
# -----------------------------------------------------------------------------

users_in_room = {}

# -----------------------------------------------------------------------------
# SocketIO Event Handlers
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
    if not username or not room: return
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
    if not room: return
    emit('receive_message', data, to=room)
    print(f"Message from {data.get('sender')} in room {room}")
