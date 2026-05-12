import datetime
from flask import session, request
from flask_socketio import emit, join_room, leave_room
from project.socketio_instance import socketio
from project.database import db
import os

connected_users = {}

@socketio.on('connect')
def handle_connect():
    user = session.get('user')
    if user:
        connected_users[user] = request.sid
        join_room(user)
        # Also join any group rooms
        conn = db()
        c = conn.cursor()
        c.execute("SELECT room_id FROM room_members WHERE username=?", (user,))
        for row in c.fetchall():
            join_room(f"group_{row['room_id']}")
        conn.close()
        emit('presence', {'user': user, 'status': 'online', 'last_seen': 'Çevrimiçi'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    user = session.get('user')
    if user and user in connected_users:
        del connected_users[user]
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            conn = db()
            c = conn.cursor()
            c.execute("UPDATE users SET last_seen=? WHERE username=?", (now, user))
            conn.commit()
            conn.close()
        except:
            pass
        emit('presence', {'user': user, 'status': 'offline', 'last_seen': now}, broadcast=True)

@socketio.on('get_online_users')
def get_online_users():
    return list(connected_users.keys())

@socketio.on('private_message')
def handle_private_message(data):
    sender = session.get('user')
    if not sender: return
    receiver = data.get('receiver')
    content = data.get('content')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = db()
    c = conn.cursor()
    query = "INSERT INTO messages (sender, receiver, content, timestamp) VALUES (?, ?, ?, ?)"
    if os.getenv("DATABASE_URL"):
        query += " RETURNING id"
    
    c.execute(query, (sender, receiver, content, timestamp))
    
    if os.getenv("DATABASE_URL"):
        msg_id = c.fetchone()[0]
    else:
        msg_id = c.lastrowid
        
    conn.commit()
    conn.close()

    msg_data = {
        'id': msg_id,
        'sender': sender,
        'receiver': receiver,
        'content': content,
        'timestamp': timestamp,
        'type': 'private'
    }
    
    emit('new_message', msg_data, room=receiver)
    if receiver != sender:
        emit('new_message', msg_data, room=sender)

@socketio.on('group_message')
def handle_group_message(data):
    sender = session.get('user')
    if not sender: return
    room_id = data.get('room_id')
    content = data.get('content')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = db()
    c = conn.cursor()
    query = "INSERT INTO room_messages (room_id, sender, content, timestamp) VALUES (?, ?, ?, ?)"
    if os.getenv("DATABASE_URL"):
        query += " RETURNING id"
    
    c.execute(query, (room_id, sender, content, timestamp))
    
    if os.getenv("DATABASE_URL"):
        msg_id = c.fetchone()[0]
    else:
        msg_id = c.lastrowid
    
    # Get profile pic for frontend
    c.execute("SELECT profile_pic FROM users WHERE username=?", (sender,))
    row = c.fetchone()
    pic = row['profile_pic'] if row else 'default.png'
    conn.commit()
    conn.close()

    msg_data = {
        'id': msg_id,
        'room_id': room_id,
        'sender': sender,
        'content': content,
        'timestamp': timestamp,
        'profile_pic': pic,
        'type': 'group'
    }
    emit('new_message', msg_data, room=f"group_{room_id}")

@socketio.on('typing')
def handle_typing(data):
    sender = session.get('user')
    if not sender: return
    receiver = data.get('receiver')
    is_typing = data.get('is_typing', True)

    emit('typing_status', {'sender': sender, 'is_typing': is_typing}, room=receiver)

@socketio.on('mark_read')
def handle_mark_read(data):
    user = session.get('user')
    sender = data.get('sender')
    if not user or not sender: return
    
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE messages SET is_read=1 WHERE receiver=? AND sender=? AND is_read=0", (user, sender))
    if c.rowcount > 0:
        conn.commit()
        emit('messages_read', {'reader': user}, room=sender)
    conn.close()

@socketio.on('delete_message')
def handle_delete_message(data):
    user = session.get('user')
    msg_id = data.get('msg_id')
    if not user or not msg_id: return

    conn = db()
    c = conn.cursor()
    # Check if user is sender or receiver
    c.execute("SELECT sender, receiver FROM messages WHERE id=?", (msg_id,))
    msg = c.fetchone()
    if msg:
        if msg['sender'] == user:
            c.execute("UPDATE messages SET deleted_by_sender=1 WHERE id=?", (msg_id,))
            conn.commit()
            emit('message_deleted', {'msg_id': msg_id}, room=msg['receiver'])
            emit('message_deleted', {'msg_id': msg_id}, room=msg['sender'])
        elif msg['receiver'] == user:
            c.execute("UPDATE messages SET deleted_by_receiver=1 WHERE id=?", (msg_id,))
            conn.commit()
    conn.close()

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    sender = session.get('user')
    target = data.get('target')
    if not sender or not target: return
    emit('webrtc_offer', {'sender': sender, 'offer': data['offer']}, room=target)

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    sender = session.get('user')
    target = data.get('target')
    if not sender or not target: return
    emit('webrtc_answer', {'sender': sender, 'answer': data['answer']}, room=target)

@socketio.on('webrtc_ice_candidate')
def handle_webrtc_ice_candidate(data):
    sender = session.get('user')
    target = data.get('target')
    if not sender or not target: return
    emit('webrtc_ice_candidate', {'sender': sender, 'candidate': data['candidate']}, room=target)

@socketio.on('webrtc_end')
def handle_webrtc_end(data):
    sender = session.get('user')
    target = data.get('target')
    if not sender or not target: return
    emit('webrtc_end', {'sender': sender}, room=target)






