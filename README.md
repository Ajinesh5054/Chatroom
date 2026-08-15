# Chatroom with Real-Time Messaging Using Python

This project is based on the uploaded task PDF.

## Included
- Sign Up
- Login / Logout
- Password hashing
- Session-based authentication
- Profile update and password change
- Create and join chatrooms
- Public/private room flag
- Real-time WebSocket messaging with Flask-SocketIO
- Message history using SQLite
- Online/offline user status
- Join/leave notifications
- Typing notification
- Emojis through normal Unicode text
- One-to-one private messaging
- Responsive HTML/CSS interface

## Requirements
Python 3.x

## Run
1. Open this project folder in CMD/Terminal.
2. Install packages:
   `pip install -r requirements.txt`
3. Start:
   `python app.py`
4. Open:
   `http://127.0.0.1:5000`

For testing real-time messaging, open the site in two browser windows and create two accounts.

## Database
The SQLite database `chatroom.db` is created automatically on first run.

## Important
The PDF lists HTTPS/WSS, horizontal scaling, failover/backups, GDPR compliance and an optional admin panel as requirements/advanced features. This single-machine academic implementation provides the core working features; production deployment would require a production server, HTTPS/WSS configuration, stronger authorization for private rooms, a scalable message broker, backups and additional compliance controls.
