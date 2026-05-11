from flask import Blueprint, render_template, request, redirect, session, url_for, flash, abort, jsonify, current_app
from project.database import db
from datetime import datetime
from functools import wraps
import sqlite3
import os
import time
from werkzeug.utils import secure_filename

messages_bp = Blueprint("messages", __name__)

def login_required(f):
    """Login gerekli decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Lütfen giriş yapın!", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

@messages_bp.route("/messages", methods=["GET", "POST"])
@messages_bp.route("/messages/<chat_user>", methods=["GET", "POST"])
@login_required
def messages(chat_user=None):
    """Mesajlaşma sayfası"""
    
    # Arama parametresi
    search = request.args.get("search_user", "").strip()
    if search:
        # XSS koruması için url_for kullan
        return redirect(url_for("messages.messages", chat_user=search))

    try:
        conn = db()
        c = conn.cursor()

        if request.method == "POST":
            target = (request.form.get("receiver") or chat_user).strip()
            body = request.form.get("content", "").strip()
            mid = request.form.get("edit_id")

            # Validasyon
            if not target or not body:
                flash("Boş mesaj gönderilemez!", "danger")
                return redirect(url_for("messages.messages", chat_user=chat_user))

            if len(body) > 5000:
                flash("Mesaj 5000 karakterden fazla olamaz!", "danger")
                return redirect(url_for("messages.messages", chat_user=chat_user))

            try:
                # Mesajı düzenle
                if mid:
                    c.execute("""
                    UPDATE messages
                    SET content=?, edited=1, edited_at=CURRENT_TIMESTAMP
                    WHERE id=? AND sender=?
                    """, (body, mid, session["user"]))
                    if c.rowcount == 0:
                        flash("Mesaj bulunamadı veya düzenleme yetkin yok.", "danger")
                    else:
                        flash("Mesaj düzenlendi!", "success")

                # Yeni mesaj gönder
                else:
                    # Alıcı var mı kontrol et
                    c.execute("SELECT username FROM users WHERE username=? AND banned=0", (target,))
                    if not c.fetchone():
                        flash("Alıcı bulunamadı!", "danger")
                        return redirect(url_for("messages.messages", chat_user=chat_user))

                    c.execute("""
                    INSERT INTO messages
                    (sender, receiver, content, timestamp)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (session["user"], target, body))
                    
                    flash("Mesaj gönderildi!", "success")

                conn.commit()
                return redirect(url_for("messages.messages", chat_user=target))

            except sqlite3.Error as e:
                flash("Mesaj gönderme sırasında hata oluştu!", "danger")
                print(f"Message error: {e}")
                return redirect(url_for("messages.messages", chat_user=chat_user))

        # Kontaklar listesi (son mesaja göre sıralı)
        u = session["user"]
        c.execute(
            """
            SELECT other.username AS contact, other.profile_pic AS pic, other.last_seen AS last_seen, MAX(m.id) AS last_id
            FROM messages m
            JOIN users other ON other.username = (
                CASE WHEN m.sender = ? THEN m.receiver ELSE m.sender END
            )
            WHERE (m.sender = ? AND m.deleted_by_sender = 0)
               OR (m.receiver = ? AND m.deleted_by_receiver = 0)
            GROUP BY other.username, other.profile_pic, other.last_seen
            ORDER BY last_id DESC
            """,
            (u, u, u),
        )

        contacts = [dict(r) for r in c.fetchall()]

        history = []
        profile_pic = "default.png"

        if chat_user:
            # Chat kullanıcı var mı kontrol et
            c.execute("SELECT username FROM users WHERE username=?", (chat_user,))
            if not c.fetchone():
                flash("Kullanıcı bulunamadı!", "danger")
                return redirect(url_for("messages.messages"))

            # Sohbet geçmişi
            c.execute("""
            SELECT *
            FROM messages
            WHERE
                (
                    sender = ? AND receiver = ?
                    AND deleted_by_sender = 0
                )
                OR
                (
                    sender = ? AND receiver = ?
                    AND deleted_by_receiver = 0
                )
            ORDER BY id ASC
            """, (
                session["user"],
                chat_user,
                chat_user,
                session["user"]
            ))

            history = [dict(r) for r in c.fetchall()]

            # Mesajları okundu olarak işaretle
            c.execute("""
            UPDATE messages
            SET is_read=1
            WHERE sender=? AND receiver=? AND is_read=0
            """, (chat_user, session["user"]))

            # Alıcının profil resmi
            c.execute("SELECT profile_pic FROM users WHERE username=?", (chat_user,))
            res = c.fetchone()
            if res:
                profile_pic = res["profile_pic"]

            conn.commit()

        conn.close()

        return render_template(
            "messages.html",
            contacts=contacts,
            history=history,
            chat_user=chat_user,
            other_pic=profile_pic
        )

    except Exception as e:
        flash("Mesajlar yüklenirken hata oluştu!", "danger")
        print(f"Messages error: {e}")
        return redirect(url_for("dashboard.dashboard"))

@messages_bp.route("/delete_message/<int:msg_id>", methods=["POST"])
@login_required
def delete_message(msg_id):
    """Tek bir mesajı sil"""
    
    try:
        conn = db()
        c = conn.cursor()

        # Mesaj var mı ve kime ait mi kontrol et
        c.execute("SELECT sender, receiver FROM messages WHERE id=?", (msg_id,))
        msg = c.fetchone()

        if not msg:
            flash("Mesaj bulunamadı!", "danger")
            return redirect(url_for("messages.messages"))

        # Sahibi mi kontrol et
        if msg["sender"] == session["user"]:
            c.execute("UPDATE messages SET deleted_by_sender=1 WHERE id=?", (msg_id,))
        elif msg["receiver"] == session["user"]:
            c.execute("UPDATE messages SET deleted_by_receiver=1 WHERE id=?", (msg_id,))
        else:
            flash("Bu mesajı silemezsin!", "danger")
            return redirect(url_for("messages.messages"))

        conn.commit()
        conn.close()

        flash("Mesaj silindi!", "success")
        return redirect(request.referrer or url_for("messages.messages"))

    except Exception as e:
        flash("Mesaj silinirken hata oluştu!", "danger")
        print(f"Delete message error: {e}")
        return redirect(url_for("messages.messages"))

@messages_bp.route("/delete_chat/<chat_user>", methods=["POST"])
@login_required
def delete_chat(chat_user):
    """Tüm sohbeti sil"""
    
    try:
        chat_user = chat_user.strip()
        
        conn = db()
        c = conn.cursor()

        # Kontrol: Kullanıcı var mı
        c.execute("SELECT username FROM users WHERE username=?", (chat_user,))
        if not c.fetchone():
            flash("Kullanıcı bulunamadı!", "danger")
            return redirect(url_for("messages.messages"))

        # Sohbeti sil
        c.execute("""
        UPDATE messages
        SET deleted_by_sender=1
        WHERE sender=? AND receiver=?
        """, (session["user"], chat_user))

        c.execute("""
        UPDATE messages
        SET deleted_by_receiver=1
        WHERE sender=? AND receiver=?
        """, (chat_user, session["user"]))

        conn.commit()
        conn.close()

        flash("Sohbet silindi!", "success")
        return redirect(url_for("messages.messages"))

    except Exception as e:
        flash("Sohbet silinirken hata oluştu!", "danger")
        print(f"Delete chat error: {e}")
        return redirect(url_for("messages.messages"))

@messages_bp.route("/archive")
@login_required
def archive():
    """Silinen mesajlar arşivi"""
    
    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
        SELECT *
        FROM messages
        WHERE
            (sender = ? AND deleted_by_sender = 1)
            OR
            (receiver = ? AND deleted_by_receiver = 1)
        ORDER BY timestamp DESC
        LIMIT 100
        """, (session["user"], session["user"]))

        archived_msgs = [dict(r) for r in c.fetchall()]
        conn.close()

        return render_template("archive.html", messages=archived_msgs)

    except Exception as e:
        flash("Arşiv yüklenirken hata oluştu!", "danger")
        return redirect(url_for("messages.messages"))

@messages_bp.route("/upload_chat_media", methods=["POST"])
@login_required
def upload_chat_media():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    if file:
        filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{filename}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        return jsonify({'url': url_for('static', filename='uploads/' + filename), 'filename': filename})
    return jsonify({'error': 'Unknown error'})

@messages_bp.route("/upload_voice", methods=["POST"])
@login_required
def upload_voice():
    """Sesli mesaj al ve kaydet"""
    if 'voice' not in request.files:
        return jsonify({'error': 'No audio file found'})
    
    file = request.files['voice']
    if file:
        filename = secure_filename(f"voice_{session['user']}_{int(time.time())}.webm")
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        return jsonify({'url': url_for('static', filename='uploads/' + filename), 'filename': filename})
    return jsonify({'error': 'Unknown error'})
