from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chatroom.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="offline")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Chatroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), default="")
    is_private = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100), nullable=False)
    sender = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_private = db.Column(db.Boolean, default=False)
    receiver = db.Column(db.String(80), nullable=True)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("chatrooms"))
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("signup"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("signup"))
        user = User(username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please log in.")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            user.status = "online"
            db.session.commit()
            return redirect(url_for("chatrooms"))
        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        if user:
            user.status = "offline"
            db.session.commit()
    session.clear()
    return redirect(url_for("login"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = db.session.get(User, session["user_id"])
    if request.method == "POST":
        new_username = request.form["username"].strip()
        new_password = request.form["password"]
        existing = User.query.filter(User.username == new_username, User.id != user.id).first()
        if existing:
            flash("Username already exists.")
        else:
            user.username = new_username
            session["username"] = new_username
            if new_password:
                user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("Profile updated.")
            return redirect(url_for("chatrooms"))
    return render_template("profile.html", user=user)

@app.route("/chatrooms")
@login_required
def chatrooms():
    rooms = Chatroom.query.order_by(Chatroom.name).all()
    users = User.query.order_by(User.username).all()
    return render_template("chatrooms.html", rooms=rooms, users=users)

@app.route("/create-room", methods=["POST"])
@login_required
def create_room():
    name = request.form["name"].strip()
    description = request.form["description"].strip()
    private = request.form.get("private") == "on"
    if not name:
        flash("Room name is required.")
    elif Chatroom.query.filter_by(name=name).first():
        flash("Room already exists.")
    else:
        room = Chatroom(name=name, description=description,
                        is_private=private, created_by=session["user_id"])
        db.session.add(room)
        db.session.commit()
        flash("Chatroom created.")
    return redirect(url_for("chatrooms"))

@app.route("/room/<path:room_name>")
@login_required
def room(room_name):
    chatroom = Chatroom.query.filter_by(name=room_name).first()
    if not chatroom:
        flash("Chatroom not found.")
        return redirect(url_for("chatrooms"))
    messages = Message.query.filter_by(room=room_name, is_private=False).order_by(Message.timestamp).all()
    users = User.query.order_by(User.username).all()
    return render_template("room.html", room=chatroom, messages=messages, users=users)

@app.route("/dm/<username>")
@login_required
def dm(username):
    if not User.query.filter_by(username=username).first():
        flash("User not found.")
        return redirect(url_for("chatrooms"))
    return render_template("dm.html", username=username)

@socketio.on("join_room")
def handle_join(data):
    if "username" not in session:
        return
    room = data["room"]
    join_room(room)
    emit("system_message", {
        "message": f'{session["username"]} joined the room.',
        "timestamp": datetime.utcnow().strftime("%H:%M")
    }, to=room)

@socketio.on("leave_room")
def handle_leave(data):
    if "username" not in session:
        return
    room = data["room"]
    leave_room(room)
    emit("system_message", {
        "message": f'{session["username"]} left the room.',
        "timestamp": datetime.utcnow().strftime("%H:%M")
    }, to=room)

@socketio.on("send_message")
def handle_message(data):
    if "username" not in session:
        return
    room = data.get("room")
    content = data.get("content", "").strip()
    if not room or not content:
        return
    msg = Message(room=room, sender=session["username"], content=content)
    db.session.add(msg)
    db.session.commit()
    emit("receive_message", {
        "sender": msg.sender,
        "content": msg.content,
        "timestamp": msg.timestamp.strftime("%d-%m-%Y %H:%M")
    }, to=room)

@socketio.on("private_message")
def handle_private(data):
    if "username" not in session:
        return
    receiver = data.get("receiver")
    content = data.get("content", "").strip()
    target = User.query.filter_by(username=receiver).first()
    if not target or not content:
        return
    room = f"dm_{min(session['username'], receiver)}_{max(session['username'], receiver)}"
    msg = Message(room=room, sender=session["username"], receiver=receiver,
                  content=content, is_private=True)
    db.session.add(msg)
    db.session.commit()
    emit("receive_private", {
        "sender": msg.sender,
        "receiver": receiver,
        "content": msg.content,
        "timestamp": msg.timestamp.strftime("%d-%m-%Y %H:%M")
    }, to=request.sid)
    emit("receive_private", {
        "sender": msg.sender,
        "receiver": receiver,
        "content": msg.content,
        "timestamp": msg.timestamp.strftime("%d-%m-%Y %H:%M")
    }, to=target.status if False else request.sid)

@socketio.on("typing")
def typing(data):
    room = data.get("room")
    if room and "username" in session:
        emit("typing", {"username": session["username"]}, to=room, include_self=False)

@socketio.on("connect")
def connected():
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        if user:
            user.status = "online"
            db.session.commit()

@socketio.on("disconnect")
def disconnected():
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        if user:
            user.status = "offline"
            db.session.commit()

with app.app_context():
    db.create_all()
    if not Chatroom.query.filter_by(name="General").first():
        db.session.add(Chatroom(name="General",
                                description="Public general discussion room.",
                                is_private=False, created_by=0))
        db.session.commit()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
