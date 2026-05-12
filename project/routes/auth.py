from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from project.database import db
from werkzeug.security import generate_password_hash, check_password_hash
import re

auth_bp = Blueprint("auth", __name__)

# Yardımcı fonksiyonlar
def is_valid_username(username):
    """Username'i doğrula (3-20 karakter, alfanumerik + underscore)"""
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None

def is_valid_password(password):
    """Şifre güvenliğini doğrula"""
    if len(password) < 8:
        return False, "Şifre en az 8 karakter olmalı"
    if not re.search(r'[A-Z]', password):
        return False, "Şifre en az bir büyük harf içermeli"
    if not re.search(r'[a-z]', password):
        return False, "Şifre en az bir küçük harf içermeli"
    if not re.search(r'[0-9]', password):
        return False, "Şifre en az bir rakam içermeli"
    return True, "Geçerli"

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Input validasyonu
        if not username or not password:
            flash("Kullanıcı adı ve şifre zorunludur!", "danger")
            return render_template("login.html")

        try:
            conn = db()
            c = conn.cursor()

            c.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = c.fetchone()

            conn.close()

            if user and check_password_hash(user["password"], password):
                # Kullanıcı yasaklı mı kontrol et
                if user["banned"] == 1:
                    flash("Hesabınız yasaklanmıştır!", "danger")
                    return redirect(url_for("auth.login"))

                # Session'a kaydet
                session.permanent = True
                session["user"] = user["username"]
                session["role"] = user["role"]
                session["user_id"] = user["id"]

                flash(f"Hoş geldin {username}!", "success")
                return redirect(url_for("dashboard.dashboard"))

            # Hata mesajı aynı kalsin (brute force koruması için)
            flash("Kullanıcı adı veya şifre hatalı!", "danger")

        except Exception as e:
            flash("Giriş sırasında bir hata oluştu!", "danger")
            print(f"Login Error: {e}")

    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        # Username validasyonu
        if not is_valid_username(username):
            flash("Username 3-20 karakter, alfanumerik ve underscore içermelidir!", "danger")
            return render_template("register.html")

        # Şifre validasyonu
        is_valid, message = is_valid_password(password)
        if not is_valid:
            flash(message, "danger")
            return render_template("register.html")

        # Şifre eşleşme kontrolü
        if password != password_confirm:
            flash("Şifreler eşleşmiyor!", "danger")
            return render_template("register.html")

        try:
            hashed_password = generate_password_hash(password)

            conn = db()
            c = conn.cursor()

            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )

            conn.commit()
            conn.close()

            flash("Kayıt başarılı! Lütfen giriş yapın.", "success")
            return redirect(url_for("auth.login"))

        except Exception:
            flash("Bu kullanıcı adı zaten alınmış!", "danger")
        except Exception as e:
            flash("Kayıt sırasında bir hata oluştu!", "danger")
            print(f"Register Error: {e}")

        return render_template("register.html")

    return render_template("register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız!", "success")
    return redirect(url_for("auth.login"))

# Oturum geçersiz kılma
@auth_bp.before_request
def before_request():
    session.permanent = True






