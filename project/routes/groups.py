from flask import Blueprint, render_template, request, redirect, session, url_for, flash, abort
from database import db
from datetime import datetime
from functools import wraps
import sqlite3

groups_bp = Blueprint("groups", __name__)

def login_required(f):
    """Login gerekli decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Lütfen giriş yapın!", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

@groups_bp.route("/groups", methods=["GET", "POST"])
@login_required
def groups_list():
    """Gruplar listesi"""
    
    try:
        conn = db()
        c = conn.cursor()

        if request.method == "POST":
            room_name = request.form.get("room_name", "").strip()

            # Validasyon
            if not room_name:
                flash("Grup adı boş olamaz!", "danger")
                return redirect(url_for("groups.groups_list"))

            if len(room_name) < 3:
                flash("Grup adı en az 3 karakter olmalı!", "danger")
                return redirect(url_for("groups.groups_list"))

            if len(room_name) > 50:
                flash("Grup adı 50 karakterden fazla olamaz!", "danger")
                return redirect(url_for("groups.groups_list"))

            try:
                # Grup oluştur
                c.execute(
                    "INSERT INTO rooms (room_name, creator, description) VALUES (?, ?, ?)",
                    (room_name, session["user"], "")
                )

                room_id = c.lastrowid

                # Yaratıcıyı üye olarak ekle
                c.execute(
                    "INSERT INTO room_members (room_id, username) VALUES (?, ?)",
                    (room_id, session["user"])
                )

                conn.commit()
                flash(f"'{room_name}' grubu başarıyla oluşturuldu!", "success")

            except sqlite3.IntegrityError:
                flash("Bu grup adı zaten kullanılıyor!", "danger")
            except Exception as e:
                flash("Grup oluşturma sırasında hata oluştu!", "danger")
                print(f"Create group error: {e}")

            return redirect(url_for("groups.groups_list"))

        # Kullanıcının üye olduğu grupları getir
        c.execute("""
        SELECT rooms.*, COUNT(room_members.username) as member_count
        FROM rooms
        JOIN room_members ON rooms.id = room_members.room_id
        WHERE room_members.username = ?
        GROUP BY rooms.id
        ORDER BY rooms.id DESC
        """, (session["user"],))

        my_groups = [dict(r) for r in c.fetchall()]

        conn.close()

        return render_template("groups_list.html", groups=my_groups)

    except Exception as e:
        flash("Gruplar yüklenirken hata oluştu!", "danger")
        print(f"Groups list error: {e}")
        return redirect(url_for("dashboard.dashboard"))

@groups_bp.route("/group/<int:room_id>", methods=["GET", "POST"])
@login_required
def group_chat(room_id):
    """Grup sohbeti"""
    
    try:
        conn = db()
        c = conn.cursor()

        # Üyelik kontrol et
        c.execute(
            "SELECT * FROM room_members WHERE room_id=? AND username=?",
            (room_id, session["user"])
        )

        if not c.fetchone():
            flash("Bu gruba erişme yetkin yok!", "danger")
            abort(403)

        if request.method == "POST":
            content = request.form.get("content", "").strip()
            new_member = request.form.get("new_member", "").strip()

            # Mesaj gönder
            if content:
                if len(content) < 1:
                    flash("Boş mesaj gönderilemez!", "danger")
                    return redirect(url_for("groups.group_chat", room_id=room_id))

                if len(content) > 5000:
                    flash("Mesaj 5000 karakterden fazla olamaz!", "danger")
                    return redirect(url_for("groups.group_chat", room_id=room_id))

                try:
                    c.execute("""
                    INSERT INTO room_messages
                    (room_id, sender, content, timestamp)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (room_id, session["user"], content))

                    conn.commit()
                    flash("Mesaj gönderildi!", "success")

                except Exception as e:
                    flash("Mesaj gönderme sırasında hata oluştu!", "danger")
                    print(f"Send message error: {e}")

            # Üye ekle
            if new_member:
                try:
                    # Kullanıcı var mı kontrol et
                    c.execute(
                        "SELECT username, banned FROM users WHERE username=?",
                        (new_member,)
                    )
                    user = c.fetchone()

                    if not user:
                        flash("Kullanıcı bulunamadı!", "danger")
                        return redirect(url_for("groups.group_chat", room_id=room_id))

                    if user["banned"] == 1:
                        flash("Yasaklı kullanıcı eklenemez!", "danger")
                        return redirect(url_for("groups.group_chat", room_id=room_id))

                    # Zaten üye mi kontrol et
                    c.execute(
                        "SELECT * FROM room_members WHERE room_id=? AND username=?",
                        (room_id, new_member)
                    )

                    if c.fetchone():
                        flash("Bu kullanıcı zaten grupta!", "danger")
                        return redirect(url_for("groups.group_chat", room_id=room_id))

                    # Üye ekle
                    c.execute(
                        "INSERT INTO room_members (room_id, username) VALUES (?, ?)",
                        (room_id, new_member)
                    )

                    conn.commit()
                    flash(f"{new_member} gruba eklendi!", "success")

                except sqlite3.IntegrityError:
                    flash("Bu kullanıcı zaten grupta!", "danger")
                except Exception as e:
                    flash("Üye eklerken hata oluştu!", "danger")
                    print(f"Add member error: {e}")

            return redirect(url_for("groups.group_chat", room_id=room_id))

        # Grup mesajlarını getir
        c.execute("""
        SELECT room_messages.*, users.profile_pic
        FROM room_messages
        JOIN users ON room_messages.sender = users.username
        WHERE room_id=?
        ORDER BY room_messages.id ASC
        """, (room_id,))

        messages = [dict(r) for r in c.fetchall()]

        # Grup bilgisi
        c.execute("SELECT room_name, creator FROM rooms WHERE id=?", (room_id,))
        room = c.fetchone()

        if not room:
            flash("Grup bulunamadı!", "danger")
            return redirect(url_for("groups.groups_list"))

        room_name = room["room_name"]
        room_creator = room["creator"]
        is_creator = session["user"] == room_creator

        # Üyeler listesi
        c.execute(
            "SELECT username FROM room_members WHERE room_id=?",
            (room_id,)
        )

        members = [r["username"] for r in c.fetchall()]

        conn.close()

        return render_template(
            "group_chat.html",
            room_id=room_id,
            room_name=room_name,
            messages=messages,
            members=members,
            is_creator=is_creator
        )

    except Exception as e:
        flash("Grup yüklenirken hata oluştu!", "danger")
        print(f"Group chat error: {e}")
        return redirect(url_for("groups.groups_list"))

@groups_bp.route("/leave_group/<int:room_id>", methods=["POST"])
@login_required
def leave_group(room_id):
    """Gruptan ayrıl"""
    
    try:
        conn = db()
        c = conn.cursor()

        # Grup var mı kontrol et
        c.execute("SELECT creator FROM rooms WHERE id=?", (room_id,))
        room = c.fetchone()

        if not room:
            flash("Grup bulunamadı!", "danger")
            return redirect(url_for("groups.groups_list"))

        # Yaratıcı ayrılamaz (grubu silmesi gerekir)
        if room["creator"] == session["user"]:
            flash("Grubu yaratıcısı ayrılamaz! Grubu silmek istiyorsan sil.", "danger")
            return redirect(url_for("groups.group_chat", room_id=room_id))

        # Üyelikten kaldır
        c.execute(
            "DELETE FROM room_members WHERE room_id=? AND username=?",
            (room_id, session["user"])
        )

        conn.commit()
        conn.close()

        flash("Gruptan ayrıldın!", "success")
        return redirect(url_for("groups.groups_list"))

    except Exception as e:
        flash("Gruptan ayrılırken hata oluştu!", "danger")
        print(f"Leave group error: {e}")
        return redirect(url_for("groups.groups_list"))

@groups_bp.route("/delete_group/<int:room_id>", methods=["POST"])
@login_required
def delete_group(room_id):
    """Grubu sil (sadece yaratıcı)"""
    
    try:
        conn = db()
        c = conn.cursor()

        # Grup var mı ve sahibi mi kontrol et
        c.execute("SELECT creator FROM rooms WHERE id=?", (room_id,))
        room = c.fetchone()

        if not room:
            flash("Grup bulunamadı!", "danger")
            return redirect(url_for("groups.groups_list"))

        if room["creator"] != session["user"]:
            flash("Sadece grup yaratıcısı grubu silebilir!", "danger")
            abort(403)

        # Grubu sil (CASCADE silme sayesinde üyeler de silinecek)
        c.execute("DELETE FROM rooms WHERE id=?", (room_id,))

        conn.commit()
        conn.close()

        flash("Grup başarıyla silindi!", "success")
        return redirect(url_for("groups.groups_list"))

    except Exception as e:
        flash("Grubu silerken hata oluştu!", "danger")
        print(f"Delete group error: {e}")
        return redirect(url_for("groups.groups_list"))

@groups_bp.route("/delete_group_message/<int:msg_id>", methods=["POST"])
@login_required
def delete_group_message(msg_id):
    """Grup mesajını sil (sadece sahibi)"""
    
    try:
        conn = db()
        c = conn.cursor()

        # Mesaj var mı ve kime ait mi kontrol et
        c.execute(
            "SELECT room_id, sender FROM room_messages WHERE id=?",
            (msg_id,)
        )

        msg = c.fetchone()

        if not msg:
            flash("Mesaj bulunamadı!", "danger")
            return redirect(url_for("groups.groups_list"))

        if msg["sender"] != session["user"]:
            flash("Sadece kendi mesajını silebilirsin!", "danger")
            return redirect(request.referrer or url_for("groups.groups_list"))

        # Mesajı sil
        c.execute("DELETE FROM room_messages WHERE id=?", (msg_id,))

        conn.commit()
        conn.close()

        flash("Mesaj silindi!", "success")
        return redirect(request.referrer or url_for("groups.groups_list"))

    except Exception as e:
        flash("Mesaj silinirken hata oluştu!", "danger")
        print(f"Delete group message error: {e}")
        return redirect(url_for("groups.groups_list"))