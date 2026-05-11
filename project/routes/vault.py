import base64
import json
import sqlite3
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    url_for,
    flash,
    abort,
    Response,
)
from functools import wraps

from project.config import VAULT_PASSPHRASE
from project.database import db, PLACEHOLDER

vault_bp = Blueprint("vault", __name__)

_SALT = b"vortex-vault-salt-v1"


def _fernet_from_passphrase(passphrase: str) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=480_000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return Fernet(key)


_cipher = _fernet_from_passphrase(VAULT_PASSPHRASE)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Lütfen giriş yapın!", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def encrypt_data(data: str) -> Optional[str]:
    try:
        return _cipher.encrypt(data.encode("utf-8")).decode("ascii")
    except Exception as e:
        print(f"Encryption error: {e}")
        return None


def decrypt_data(encrypted_data: str) -> Optional[str]:
    try:
        return _cipher.decrypt(encrypted_data.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError) as e:
        print(f"Decryption error: {e}")
        return None


@vault_bp.route("/vault", methods=["GET", "POST"])
@login_required
def vault():
    try:
        conn = db()
        c = conn.cursor()

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            secret = request.form.get("secret", "").strip()
            v_id = request.form.get("v_id")

            if not title or not secret:
                flash("Başlık ve gizli veri boş olamaz!", "danger")
                return redirect(url_for("vault.vault"))

            if len(title) < 3:
                flash("Başlık en az 3 karakter olmalı!", "danger")
                return redirect(url_for("vault.vault"))

            if len(title) > 100:
                flash("Başlık 100 karakterden fazla olamaz!", "danger")
                return redirect(url_for("vault.vault"))

            if len(secret) > 10000:
                flash("Gizli veri 10000 karakterden fazla olamaz!", "danger")
                return redirect(url_for("vault.vault"))

            encrypted_secret = encrypt_data(secret)
            if encrypted_secret is None:
                flash("Şifreleme başarısız.", "danger")
                return redirect(url_for("vault.vault"))

            try:
                if v_id:
                    c.execute(
                        f"""
                        UPDATE vault
                        SET title={PLACEHOLDER}, secret_data={PLACEHOLDER}
                        WHERE id={PLACEHOLDER} AND user_name={PLACEHOLDER}
                        """,
                        (title, encrypted_secret, v_id, session["user"]),
                    )
                    if c.rowcount == 0:
                        flash("Kayıt bulunamadı veya güncellenemedi.", "danger")
                    else:
                        flash("Gizli veri güncellendi!", "success")
                else:
                    c.execute(
                        f"""
                        INSERT INTO vault (user_name, title, secret_data)
                        VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
                        """,
                        (session["user"], title, encrypted_secret),
                    )
                    flash("Gizli veri kaydedildi!", "success")

                conn.commit()

            except sqlite3.Error as e:
                flash("Veritabanı hatası!", "danger")
                print(f"Vault database error: {e}")
            except Exception as e:
                flash("Veri kaydedilirken hata oluştu!", "danger")
                print(f"Vault error: {e}")

            return redirect(url_for("vault.vault"))

        c.execute(
            f"SELECT id, title, user, created_at FROM vault WHERE user_name={PLACEHOLDER} ORDER BY id DESC",
            (session["user"],),
        )

        items = [dict(r) for r in c.fetchall()]

        for item in items:
            c.execute(
                f"SELECT secret_data FROM vault WHERE id={PLACEHOLDER} AND user_name={PLACEHOLDER}",
                (item["id"], session["user"]),
            )
            encrypted = c.fetchone()
            if not encrypted:
                item["secret_preview"] = ""
                continue
            plain = decrypt_data(encrypted["secret_data"])
            if plain is None:
                item["secret_preview"] = "***[Şifre çözülemedi]***"
                item["secret_full"] = ""
            else:
                item["secret_preview"] = (plain[:50] + "…") if len(plain) > 50 else plain
                item["secret_full"] = plain

        conn.close()

        return render_template("vault.html", items=items)

    except Exception as e:
        flash("Vault yüklenirken hata oluştu!", "danger")
        print(f"Vault load error: {e}")
        return redirect(url_for("dashboard.dashboard"))


@vault_bp.route("/vault/view/<int:vault_id>")
@login_required
def vault_view(vault_id):
    try:
        conn = db()
        c = conn.cursor()

        c.execute(
            f"SELECT * FROM vault WHERE id={PLACEHOLDER} AND user_name={PLACEHOLDER}",
            (vault_id, session["user"]),
        )

        row = c.fetchone()

        if not row:
            flash("Gizli veri bulunamadı!", "danger")
            return redirect(url_for("vault.vault"))

        item = dict(row)
        plain = decrypt_data(item["secret_data"])
        if plain is None:
            flash("Şifre çözülemedi (anahtar değişmiş olabilir).", "danger")
            item["secret_data"] = ""
        else:
            item["secret_data"] = plain

        conn.close()

        return render_template("vault_view.html", item=item)

    except Exception as e:
        flash("Gizli veri görüntülenirken hata oluştu!", "danger")
        print(f"Vault view error: {e}")
        return redirect(url_for("vault.vault"))


@vault_bp.route("/vault/delete/<int:vault_id>", methods=["POST"])
@login_required
def vault_delete(vault_id):
    try:
        conn = db()
        c = conn.cursor()

        c.execute(
            f"SELECT user FROM vault WHERE id={PLACEHOLDER}",
            (vault_id,),
        )

        row = c.fetchone()

        if not row:
            flash("Gizli veri bulunamadı!", "danger")
            return redirect(url_for("vault.vault"))

        if row["user"] != session["user"]:
            flash("Bu veriyi silemezsin!", "danger")
            abort(403)

        c.execute(
            f"DELETE FROM vault WHERE id={PLACEHOLDER} AND user_name={PLACEHOLDER}",
            (vault_id, session["user"]),
        )

        conn.commit()
        conn.close()

        flash("Gizli veri silindi!", "success")
        return redirect(url_for("vault.vault"))

    except Exception as e:
        flash("Gizli veri silinirken hata oluştu!", "danger")
        print(f"Vault delete error: {e}")
        return redirect(url_for("vault.vault"))


@vault_bp.route("/vault/export")
@login_required
def vault_export():
    try:
        conn = db()
        c = conn.cursor()

        c.execute(
            f"SELECT * FROM vault WHERE user_name={PLACEHOLDER}",
            (session["user"],),
        )

        items = [dict(r) for r in c.fetchall()]
        conn.close()

        for item in items:
            plain = decrypt_data(item["secret_data"])
            item["secret_data"] = plain if plain is not None else None

        payload = json.dumps(items, default=str, ensure_ascii=False, indent=2)
        return Response(
            payload,
            mimetype="application/json; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=vault_export.json",
            },
        )

    except Exception as e:
        flash("Vault dış aktarılırken hata oluştu!", "danger")
        print(f"Vault export error: {e}")
        return redirect(url_for("vault.vault"))

