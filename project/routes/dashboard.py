from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from project.database import db
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from project.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from datetime import datetime
import os

dashboard_bp = Blueprint("dashboard", __name__)

def login_required(f):
    """Login gerekli decorator"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Lütfen giriş yapın!", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# --- ANA DASHBOARD ---
@dashboard_bp.route("/")
def home():
    """Ana sayfaya yönlendir"""
    return redirect(url_for('dashboard.dashboard')) if "user" in session else redirect(url_for('auth.login'))

@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    """Ana dashboard sayfası"""
    try:
        conn = db()
        c = conn.cursor()
        
        # Şifre değiştirme
        if request.method == "POST":
            np = request.form.get("password")
            if np and len(np) >= 8:
                hashed = generate_password_hash(np)
                c.execute("UPDATE users SET password=? WHERE username=?", (hashed, session["user"]))
                flash("Şifre başarıyla değiştirildi!", "success")
            
            # Profil resmi yükleme
            if 'profile_pic' in request.files:
                f = request.files['profile_pic']
                if f and f.filename != '':
                    # Dosya türü kontrolü
                    if '.' in f.filename:
                        ext = f.filename.rsplit('.', 1)[1].lower()
                        if ext in ALLOWED_EXTENSIONS:
                            fn = secure_filename(f"{session['user']}_{datetime.now().timestamp()}.{ext}")
                            f.save(os.path.join(UPLOAD_FOLDER, fn))
                            c.execute("UPDATE users SET profile_pic=? WHERE username=?", (fn, session["user"]))
                            flash("Profil resmi başarıyla yüklendi!", "success")
                        else:
                            flash("Geçersiz dosya türü! PNG, JPG, GIF desteklenir.", "danger")
                    else:
                        flash("Dosyanın uzantısı yok!", "danger")
            
            conn.commit()
        
        # Kullanıcı bilgilerini getir
        c.execute("SELECT * FROM users WHERE username=?", (session["user"],))
        u_row = c.fetchone()
        u_data = dict(u_row) if u_row else {
            'username': session['user'],
            'profile_pic': 'default.png',
            'role': 'user',
            'banned': 0
        }
        # Postgres datetime objesi güvenliği
        if isinstance(u_data.get('created_at'), datetime):
            u_data['created_at'] = u_data['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        
        # Okunmamış mesaj sayısı
        c.execute("""SELECT COUNT(*) AS count FROM messages 
                     WHERE receiver=? AND is_read=0 AND deleted_by_receiver=0""", 
                  (session["user"],))
        row = c.fetchone()
        msg_count = row['count'] if row else 0
        
        # Son duyuru (şablon string bekliyor)
        c.execute("SELECT content FROM announcements ORDER BY id DESC LIMIT 1")
        ann_row = c.fetchone()
        ann = ann_row["content"] if ann_row else None
        
        # Katılımcı oldukları grup sayısı
        c.execute("SELECT COUNT(*) AS count FROM room_members WHERE username=?", (session["user"],))
        row = c.fetchone()
        group_count = row['count'] if row else 0
        
        # Vault öğeleri sayısı
        c.execute("SELECT COUNT(*) AS count FROM vault WHERE user_name=?", (session["user"],))
        row = c.fetchone()
        vault_count = row['count'] if row else 0

        # Toplam gönderilen mesaj sayısı (Mesajlar + Grup Mesajları)
        c.execute("SELECT COUNT(*) AS count FROM messages WHERE sender=?", (session["user"],))
        row_m = c.fetchone()
        sent_m_count = row_m['count'] if row_m else 0

        c.execute("SELECT COUNT(*) AS count FROM room_messages WHERE sender=?", (session["user"],))
        row_g = c.fetchone()
        sent_g_count = row_g['count'] if row_g else 0
        
        total_sent = sent_m_count + sent_g_count

        conn.close()

        return render_template(
            "dashboard.html",
            u=u_data,
            msg_count=msg_count,
            ann=ann,
            group_count=group_count,
            vault_count=vault_count,
            total_sent=total_sent
        )
    except Exception as e:
        flash("Dashboard yüklenirken bir hata oluştu!", "danger")
        print(f"Dashboard error: {e}")
        return redirect(url_for("auth.login"))

@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Kullanıcı profili ve ayarlar sayfası"""
    try:
        conn = db()
        c = conn.cursor()
        
        if request.method == "POST":
            # Şifre değiştirme
            np = request.form.get("password")
            if np and len(np) >= 8:
                c.execute("UPDATE users SET password=? WHERE username=?", 
                          (generate_password_hash(np), session["user"]))
                flash("Şifre başarıyla güncellendi!", "success")
            
            # Profil resmi (Kalıcı Base64 Depolama)
            if 'profile_pic' in request.files:
                f = request.files['profile_pic']
                if f and f.filename != '':
                    import base64
                    from io import BytesIO
                    from PIL import Image
                    try:
                        img = Image.open(f)
                        # Resmi optimize et ve küçült
                        img.thumbnail((300, 300))
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        data_uri = f"data:image/png;base64,{img_str}"
                        
                        c.execute("UPDATE users SET profile_pic=? WHERE username=?", (data_uri, session["user"]))
                        flash("Profil fotoğrafı güncellendi! (Veritabanına kalıcı olarak kaydedildi)", "success")
                    except Exception as e:
                        flash(f"Fotoğraf işlenirken hata oluştu: {e}", "danger")
            
            conn.commit()
            return redirect(url_for("dashboard.profile"))

        # Kullanıcı verileri ve İstatistikler
        c.execute("SELECT * FROM users WHERE username=?", (session["user"],))
        u_row = c.fetchone()
        u_data = dict(u_row) if u_row else {
            'username': session['user'],
            'profile_pic': 'default.png',
            'role': 'user',
            'created_at': 'Bilinmiyor'
        }
        
        # Postgres datetime objesi güvenliği
        if isinstance(u_data.get('created_at'), datetime):
            u_data['created_at'] = u_data['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute("SELECT COUNT(*) AS count FROM room_members WHERE username=?", (session["user"],))
        row = c.fetchone()
        group_count = row['count'] if row else 0
        
        c.execute("SELECT COUNT(*) AS count FROM vault WHERE user_name=?", (session["user"],))
        row = c.fetchone()
        vault_count = row['count'] if row else 0

        c.execute("SELECT COUNT(*) AS count FROM messages WHERE sender=?", (session["user"],))
        row_m = c.fetchone()
        sent_m = row_m['count'] if row_m else 0

        c.execute("SELECT COUNT(*) AS count FROM room_messages WHERE sender=?", (session["user"],))
        row_g = c.fetchone()
        sent_g = row_g['count'] if row_g else 0
        
        total_sent = sent_m + sent_g

        conn.close()
        return render_template("profile.html", u=u_data, group_count=group_count, vault_count=vault_count, total_sent=total_sent)

    except Exception as e:
        flash("Profil yüklenirken hata oluştu!", "danger")
        print(f"Profile error: {e}")
        return redirect(url_for("dashboard.dashboard"))






