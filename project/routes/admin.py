from flask import Blueprint, render_template, request, redirect, session, url_for, abort, flash
from project.database import db
from functools import wraps
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

# Admin Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Bu işlem için yetkiniz yok!", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Audit Log Fonksiyonu
def log_admin_action(action, target_user, details=""):
    """Admin işlemlerini logla"""
    try:
        conn = db()
        c = conn.cursor()
        
        admin_user = session.get("user", "unknown")
        timestamp = datetime.now().isoformat()
        
        c.execute("""
        INSERT INTO admin_logs (admin_user, action, target_user, details, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """, (admin_user, action, target_user, details, timestamp))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Logging error: {e}")

# Admin Panel
@admin_bp.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    conn = db()
    c = conn.cursor()

    if request.method == "POST":
        try:
            # Duyuru gönder
            if "msg" in request.form:
                msg = request.form.get("msg", "").strip()
                
                if not msg or len(msg) < 3:
                    flash("Duyuru en az 3 karakter olmalı!", "danger")
                    return redirect(url_for("admin.admin"))
                
                if len(msg) > 1000:
                    flash("Duyuru 1000 karakterden fazla olamaz!", "danger")
                    return redirect(url_for("admin.admin"))

                c.execute("""
                INSERT INTO announcements (content, created_by)
                VALUES (?, ?)
                """, (msg, session.get("user")))

                conn.commit()
                log_admin_action("announcement", "all", msg[:50])
                flash("Duyuru başarıyla gönderildi!", "success")

            # Rol değiştir
            elif "change_role" in request.form:
                target_user = request.form.get("user_id", "").strip()
                new_role = request.form.get("new_role", "").strip()

                # Role validasyonu
                valid_roles = ["user", "moderator", "admin"]
                if new_role not in valid_roles:
                    flash("Geçersiz rol!", "danger")
                    return redirect(url_for("admin.admin"))

                # Kendi rolünü değiştiremesin
                if target_user == session.get("user"):
                    flash("Kendi rolünü değiştiremezsin!", "danger")
                    return redirect(url_for("admin.admin"))

                # Kullanıcı var mı kontrol et
                c.execute("SELECT username FROM users WHERE username = ?", (target_user,))
                if not c.fetchone():
                    flash("Kullanıcı bulunamadı!", "danger")
                    return redirect(url_for("admin.admin"))

                c.execute("""
                UPDATE users
                SET role = ?
                WHERE username = ?
                """, (new_role, target_user))

                conn.commit()
                log_admin_action("role_change", target_user, f"new_role={new_role}")
                flash(f"{target_user}'ün rolü {new_role} olarak değiştirildi!", "success")

        except Exception as e:
            flash("Veritabanı hatası!", "danger")
            print(f"Database error: {e}")
        except Exception as e:
            flash("Bir hata oluştu!", "danger")
            print(f"Error: {e}")

    # Tüm kullanıcıları getir
    try:
        c.execute("""
        SELECT id, username, role, banned, created_at
        FROM users
        ORDER BY created_at DESC
        """)
        users = [dict(r) for r in c.fetchall()]
    except Exception as e:
        users = []
        print(f"Error fetching users: {e}")

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        valid_roles=["user", "moderator", "admin"]
    )


# Kullanıcıyı Banla
@admin_bp.route("/ban/<username>", methods=["POST"])
@admin_required
def ban(username):
    """Kullanıcıyı banla"""
    
    # Kendi kendini banlamasın
    if username == session.get("user"):
        flash("Kendini banlanamaz!", "danger")
        return redirect(url_for("admin.admin"))

    try:
        conn = db()
        c = conn.cursor()

        # Kullanıcı var mı kontrol et
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            flash("Kullanıcı bulunamadı!", "danger")
            return redirect(url_for("admin.admin"))

        # Banla
        c.execute("""
        UPDATE users
        SET banned = 1
        WHERE username = ?
        """, (username,))

        conn.commit()
        conn.close()

        log_admin_action("ban", username, "banned=1")
        flash(f"{username} başarıyla banlandı!", "success")

    except Exception as e:
        flash("Ban işlemi sırasında hata oluştu!", "danger")
        print(f"Ban error: {e}")

    return redirect(url_for("admin.admin"))


# Kullanıcıyı Kaldır Bandan
@admin_bp.route("/unban/<username>", methods=["POST"])
@admin_required
def unban(username):
    """Kullanıcıyı banı kaldır"""
    
    try:
        conn = db()
        c = conn.cursor()

        # Kullanıcı var mı kontrol et
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            flash("Kullanıcı bulunamadı!", "danger")
            return redirect(url_for("admin.admin"))

        c.execute("""
        UPDATE users
        SET banned = 0
        WHERE username = ?
        """, (username,))

        conn.commit()
        conn.close()

        log_admin_action("unban", username, "banned=0")
        flash(f"{username}'ın banı başarıyla kaldırıldı!", "success")

    except Exception as e:
        flash("Ban kaldırma işlemi sırasında hata oluştu!", "danger")
        print(f"Unban error: {e}")

    return redirect(url_for("admin.admin"))






