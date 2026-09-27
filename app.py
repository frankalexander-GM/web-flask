"""
DevPlay Flask — Red social para devs de videojuegos indie 🎮
Versión Python/Flask con el mismo diseño "Terracota & Crema" que la original.

Correr:   python3 app.py   →  http://localhost:3000
Entradas: username@devplay.test / test1234
"""
import json
import os
import re
import secrets
import unicodedata
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import pixel
from models import DB_PATH, execute, get_db, new_id, now_iso, q

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
BETA_FILES_DIR = os.path.join(BASE_DIR, "download", "betas")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("DEVPLAY_SECRET", secrets.token_hex(32)),
    MAX_CONTENT_LENGTH=60 * 1024 * 1024,  # 60MB hard cap (betas 50MB)
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
)

# ══════════════════════ Utilidades ══════════════════════

MEDIA_IMG_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
MEDIA_VIDEO_EXT = {"mp4", "webm", "mov"}
AVATAR_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
BETA_EXT = {"zip", "rar", "7z", "tar", "gz", "exe", "apk"}
LIMITS = {"img_mb": 8, "video_mb": 25, "avatar_mb": 5, "beta_mb": 50}
GENRES = ["Plataformas", "RPG", "Puzzle", "Aventura", "Shooter", "Estrategia",
          "Terror", "Carreras", "Deportes", "Simulación", "Otro"]
PLATFORMS = ["PC", "Mac", "Linux", "Android", "Web"]
STATUSES = {"alpha": "Alpha", "closed_beta": "Beta cerrada", "open_beta": "Beta abierta",
            "early_access": "Acceso anticipado", "tech_test": "Tech test",
            "coming_soon": "Próximamente", "ended": "Terminada"}
VERSION_RE = re.compile(r"^v?\d+(\.\d+){0,3}([-a-z0-9]*)?$", re.IGNORECASE)
SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,120}$")


def media_kind(url):
    """image | video — por extensión, igual que media-utils.ts."""
    u = (url or "").lower().split("?")[0].split("#")[0]
    if u.endswith((".mp4", ".webm", ".mov")):
        return "video"
    return "image"


def is_valid_media_url(url):
    """Solo archivos subidos a DevPlay o http(s). Bloquea javascript:/data:."""
    if not url:
        return False
    if url.startswith("/uploads/") or url.startswith("/files/betas/"):
        return True
    return bool(re.match(r"^https?://[^\s]+$", url, re.IGNORECASE))


def current_user():
    if not hasattr(g, "_user"):
        g._user = None
        uid = session.get("uid")
        if uid:
            g._user = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
    return g._user


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify({"error": "Inicia sesión primero"}), 401
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


@app.context_processor
def inject_globals():
    user = current_user()
    unread_dms = 0
    if user:
        row = q("SELECT COUNT(*) c FROM dms WHERE recipient_id=? AND read_at IS NULL", (user["id"],), one=True)
        unread_dms = row["c"]
    return dict(cur_user=user, media_kind=media_kind, GENRES=GENRES, PLATFORMS=PLATFORMS,
                STATUSES=STATUSES, unread_dms=unread_dms, json_loads=json.loads)


def parse_json(text, default):
    try:
        return json.loads(text) if text else default
    except Exception:
        return default


def timeago(s):
    if not s:
        return ""
    d = datetime.utcnow() - datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    m = int(d.total_seconds() // 60)
    if m < 1: return "ahora"
    if m < 60: return f"{m}m"
    h = m // 60
    if h < 24: return f"{h}h"
    days = h // 24
    if days < 30: return f"{days}d"
    return f"{days // 30}mes"


app.jinja_env.filters["timeago"] = timeago

# ══════════════════════ Autenticación ══════════════════════

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        username = (request.form.get("username") or "").strip().lower()
        full_name = (request.form.get("full_name") or "").strip()
        password = request.form.get("password") or ""
        age_raw = request.form.get("age") or ""
        acepta = request.form.get("mayor13")
        try:
            age = int(age_raw) if age_raw else None
        except ValueError:
            age = None
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
            flash("Escribe un correo válido", "error")
        elif not re.match(r"^[a-z0-9_]{3,20}$", username):
            flash("El usuario necesita 3-20 letras, números o _ (sin espacios)", "error")
        elif len(password) < 6:
            flash("La contraseña necesita al menos 6 caracteres", "error")
        elif not age or age < 13:
            flash("Debes tener al menos 13 años para entrar (Ley 1581 Art.7)", "error")
        elif not acepta:
            flash("Confirma que tienes 13+ años con la casilla", "error")
        elif q("SELECT id FROM users WHERE email=?", (email,), one=True):
            flash("Ese correo ya tiene cuenta, ¡inicia sesión!", "error")
        elif q("SELECT id FROM users WHERE username=?", (username,), one=True):
            flash("Ese usuario ya está tomado, prueba otro", "error")
        else:
            uid = new_id()
            execute(
                "INSERT INTO users (id,email,username,password_hash,full_name,age,avatar,devcoins)"
                " VALUES (?,?,?,?,?,?,?,100)",
                (uid, email, username, generate_password_hash(password),
                 full_name or username, age,
                 f"https://api.dicebear.com/9.x/bottts/svg?seed={username}&backgroundColor=bf5b34,e8c39e,dd8b62"))
            session["uid"] = uid
            session.permanent = True
            flash("¡Bienvenido a DevPlay! 🎮", "success")
            return redirect(url_for("feed"))
    return render_template("registro.html")


@app.route("/entrar", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident = (request.form.get("ident") or "").strip().lower()
        password = request.form.get("password") or ""
        user = q("SELECT * FROM users WHERE email=? OR username=?", (ident, ident), one=True)
        if user and user["password_hash"] and check_password_hash(user["password_hash"], password):
            session["uid"] = user["id"]
            session.permanent = True
            execute("UPDATE users SET last_seen=? WHERE id=?", (now_iso(), user["id"]))
            nxt = request.args.get("next") or request.form.get("next")
            return redirect(nxt if nxt and nxt.startswith("/") else url_for("feed"))
        flash("Correo/usuario o contraseña incorrectos", "error")
    return render_template("entrar.html")


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("login"))


# ══════════════════════ Páginas ══════════════════════

def post_rows(rows):
    """Decora posts con autor, likes, comentarios y media parseada."""
    out = []
    uid = (current_user() or {"id": None})["id"]
    for p in rows:
        author = q("SELECT id,username,full_name,avatar,profession FROM users WHERE id=?", (p["author_id"],), one=True)
        likes = q("SELECT COUNT(*) c FROM likes WHERE post_id=?", (p["id"],), one=True)["c"]
        ncom = q("SELECT COUNT(*) c FROM comments WHERE post_id=?", (p["id"],), one=True)["c"]
        liked = bool(uid and q("SELECT 1 x FROM likes WHERE post_id=? AND user_id=?", (p["id"], uid), one=True))
        beta = q("SELECT * FROM betas WHERE post_id=?", (p["id"],), one=True) if p["type"] == "BETA" else None
        out.append({
            "post": p, "author": author, "likes": likes, "ncom": ncom, "liked": liked,
            "media": parse_json(p["media_urls"], []),
            "beta": dict(beta, platforms=parse_json(beta["platforms"], []),
                         tags=parse_json(beta["tags"], []),
                         screenshots=parse_json(beta["screenshots"], [])) if beta else None,
        })
    return out


@app.route("/")
@login_required
def feed():
    rows = q("SELECT * FROM posts ORDER BY created_at DESC LIMIT 40")
    items = post_rows(rows)
    top_betas = q("SELECT b.*, u.username, u.avatar FROM betas b JOIN posts p ON p.id=b.post_id "
                  "JOIN users u ON u.id=p.author_id ORDER BY b.downloads DESC LIMIT 4")
    top_betas = [dict(b) for b in top_betas]
    for b in top_betas:
        b["platforms"] = parse_json(b["platforms"], [])
    suggestions = q("SELECT id,username,full_name,avatar,profession FROM users "
                    "WHERE id!=? ORDER BY RANDOM() LIMIT 4", (current_user()["id"],))
    return render_template("index.html", items=items, top_betas=top_betas, suggestions=suggestions)


@app.route("/betas")
@login_required
def betas():
    search = (request.args.get("q") or "").strip()
    genre = request.args.get("genero") or ""
    sql = ("SELECT b.*, p.author_id, u.username, u.avatar, u.full_name FROM betas b "
           "JOIN posts p ON p.id=b.post_id JOIN users u ON u.id=p.author_id WHERE 1=1")
    params = []
    if search:
        sql += " AND (b.title LIKE ? OR b.description LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if genre:
        sql += " AND b.genre=?"
        params.append(genre)
    sql += " ORDER BY b.created_at DESC LIMIT 60"
    rows = [dict(r) for r in q(sql, params)]
    for b in rows:
        b["platforms"] = parse_json(b["platforms"], [])
        b["tags"] = parse_json(b["tags"], [])
    return render_template("betas.html", betas=rows, search=search, genre=genre)


@app.route("/beta/<beta_id>")
@login_required
def beta_detail(beta_id):
    b = q("SELECT b.*, p.author_id, u.username, u.avatar, u.full_name, u.profession FROM betas b "
          "JOIN posts p ON p.id=b.post_id JOIN users u ON u.id=p.author_id WHERE b.id=?", (beta_id,), one=True)
    if not b:
        abort(404)
    b = dict(b)
    b["platforms"] = parse_json(b["platforms"], [])
    b["tags"] = parse_json(b["tags"], [])
    b["screenshots"] = parse_json(b["screenshots"], [])
    post = q("SELECT * FROM posts WHERE id=?", (b["post_id"],), one=True)
    comments = q("SELECT c.*, u.username, u.avatar FROM comments c JOIN users u ON u.id=c.user_id "
                 "WHERE c.post_id=? ORDER BY c.created_at ASC", (b["post_id"],))
    likes = q("SELECT COUNT(*) c FROM likes WHERE post_id=?", (b["post_id"],), one=True)["c"]
    uid = current_user()["id"]
    liked = bool(q("SELECT 1 x FROM likes WHERE post_id=? AND user_id=?", (b["post_id"], uid), one=True))
    more = q("SELECT b.id, b.title, b.cover_image, b.genre FROM betas b WHERE b.id!=? ORDER BY b.downloads DESC LIMIT 3", (beta_id,))
    return render_template("beta_detail.html", b=b, post=post, comments=comments,
                           likes=likes, liked=liked, more=more)


# ══════════════════════ Publicar beta — CON RESTRICCIONES ══════════════════════

def validate_beta(title, description, genre, version, platforms, cover, screenshots,
                  download_type, file_name, file_size, external_url):
    """Las reglas de la fábrica (mismas que la versión Next.js)."""
    if len((title or "").strip()) < 3:
        return "El título necesita al menos 3 letras"
    if len((description or "").strip()) < 20:
        return "La descripción necesita al menos 20 letras (cuenta con cariño lo que hace tu juego)"
    if len(description or "") > 2000:
        return "La descripción no puede pasar de 2000 letras"
    if not genre or genre not in GENRES:
        return "Elige el género del juego"
    if not (version or "").strip():
        return "La versión es obligatoria (ej: v0.1, 1.0.2)"
    if not VERSION_RE.match(version.strip()):
        return "La versión necesita un formato válido (ej: v0.1, 1.0.2)"
    if not platforms or len(platforms) < 1:
        return "Elige al menos una plataforma"
    if len(platforms) > 10:
        return "Máximo 10 plataformas"
    if not cover or not is_valid_media_url(cover):
        return "Sube una portada para tu beta (imagen o video) — es obligatoria"
    if len(screenshots) > 5:
        return "Máximo 5 capturas para la galería"
    for s in screenshots:
        if not is_valid_media_url(s):
            return "Las capturas deben ser archivos subidos a DevPlay"
    if download_type == "DIRECT":
        if not file_name:
            return "Sube el archivo de tu beta (ZIP, RAR, EXE, APK... máx 50MB)"
        if (file_size or 0) > 50 * 1024 * 1024:
            return "El archivo pasa de 50MB — usa un enlace externo (itch.io, Drive, Mega)"
    elif download_type == "LINK":
        if not external_url or not re.match(r"^https?://[^\s]+\.[^\s]+", external_url or ""):
            return "Pega un enlace externo válido (https://...)"
    else:
        return "Elige cómo se descarga tu beta: archivo o enlace externo"
    return None


@app.route("/publicar", methods=["GET", "POST"])
@login_required
def publicar():
    errors, values = [], {}
    if request.method == "POST":
        uid = current_user()["id"]
        values = {k: (request.form.get(k) or "").strip() for k in
                  ("title", "description", "genre", "version", "download_type",
                   "external_url", "external_platform", "requirements", "changelog",
                   "install_instructions", "beta_status", "tags")}
        cover = (request.form.get("cover") or "").strip()
        screenshots = [s for s in request.form.get("screenshots", "").split("|") if s]
        platforms = request.form.getlist("platforms")
        file_name = (request.form.get("file_name") or "").strip()
        file_url = (request.form.get("file_url") or "").strip()
        try:
            file_size = int(request.form.get("file_size") or 0)
        except ValueError:
            file_size = 0

        # Anti-spam: máx 3 betas por día
        today = q("SELECT COUNT(*) c FROM betas WHERE post_id IN "
                  "(SELECT id FROM posts WHERE author_id=?) AND created_at>=datetime('now','-1 day')",
                  (uid,), one=True)["c"]
        if today >= 3:
            errors.append("Ya publicaste 3 betas hoy, descansa y vuelve mañana jaja 🌙")
        else:
            err = validate_beta(values["title"], values["description"], values["genre"],
                                values["version"], platforms, cover, screenshots,
                                values["download_type"], file_name, file_size, values["external_url"])
            if err:
                errors.append(err)
            else:
                pid, bid = new_id(), new_id()
                content = f"¡Nueva beta disponible! 🎮 {values['title']}"
                execute("INSERT INTO posts (id,author_id,type,content,created_at) VALUES (?,?,?,?,?)",
                        (pid, uid, "BETA", content, now_iso()))
                execute(
                    "INSERT INTO betas (id,post_id,title,description,download_type,file_url,file_size,"
                    "file_name,external_url,external_platform,beta_status,genre,version,platforms,tags,"
                    "requirements,changelog,install_instructions,cover_image,screenshots,downloads,created_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)",
                    (bid, pid, values["title"], values["description"], values["download_type"],
                     file_url or None, file_size or None, file_name or None,
                     values["external_url"] or None, values["external_platform"] or None,
                     values["beta_status"] or "open_beta", values["genre"], values["version"],
                     json.dumps(platforms), json.dumps([t.strip() for t in values["tags"].split(",") if t.strip()][:10]),
                     values["requirements"] or None, values["changelog"] or None,
                     values["install_instructions"] or None, cover, json.dumps(screenshots), now_iso()))
                flash("¡Beta publicada! 🎮 La fábrica aprueba tu juego", "success")
                return redirect(url_for("beta_detail", beta_id=bid))
    return render_template("publicar.html", errors=errors, values=values,
                           limits=LIMITS, genres=GENRES, platforms=PLATFORMS, statuses=STATUSES)


# ══════════════════════ Uploads y archivos ══════════════════════

def _save_upload(fileobj, kind):
    """Guarda con nombre único saneado. Devuelve (url, size, name) o (None, msg)."""
    ext = (fileobj.filename or "").rsplit(".", 1)[-1].lower()
    base = os.path.splitext(os.path.basename(fileobj.filename or "archivo"))[0][:40]
    base = re.sub(r"[^a-zA-Z0-9_-]", "", base) or "archivo"
    if kind == "beta":
        if ext not in BETA_EXT:
            return None, "Formato no permitido pa' betas: ZIP, RAR, 7Z, TAR, GZ, EXE o APK"
        folder, max_mb = BETA_FILES_DIR, LIMITS["beta_mb"]
    elif kind == "avatar":
        if ext not in AVATAR_EXT:
            return None, "Formato de avatar no permitido: JPG, PNG, GIF o WEBP"
        folder, max_mb = os.path.join(UPLOAD_DIR, "avatar"), LIMITS["avatar_mb"]
    else:
        if ext in MEDIA_VIDEO_EXT:
            max_mb = LIMITS["video_mb"]
        elif ext in MEDIA_IMG_EXT:
            max_mb = LIMITS["img_mb"]
        else:
            return None, "Formato de media no permitido: JPG, PNG, GIF, WEBP, MP4, WEBM o MOV"
        folder = os.path.join(UPLOAD_DIR, "media")
    os.makedirs(folder, exist_ok=True)
    name = f"{datetime.utcnow().strftime('%y%m%d%H%M%S')}-{secrets.token_hex(3)}-{base}.{ext}"
    path = os.path.join(folder, name)
    fileobj.save(path)
    size = os.path.getsize(path)
    if size > max_mb * 1024 * 1024:
        os.remove(path)
        return None, f"El archivo pasa de {max_mb}MB"
    url = f"/files/betas/{name}" if kind == "beta" else f"/uploads/{'avatar' if kind == 'avatar' else 'media'}/{name}"
    return (url, size, name), None


@app.route("/api/upload", methods=["POST"])
@login_required
def upload():
    f = request.files.get("file")
    kind = request.form.get("kind") or "media"
    if not f or not f.filename:
        return jsonify({"error": "No llegió ningún archivo"}), 400
    result, err = _save_upload(f, kind)
    if err:
        return jsonify({"error": err}), 413
    url, size, name = result
    return jsonify({"url": url, "kind": kind, "size": size, "name": name,
                    "mediaKind": media_kind(url)})


@app.route("/uploads/<folder>/<name>")
def serve_upload(folder, name):
    if folder not in ("media", "avatar") or not SAFE_NAME_RE.match(name) or name.startswith("."):
        abort(404)
    return send_from_directory(os.path.join(UPLOAD_DIR, folder), name,
                               max_age=31536000, conditional=True)


@app.route("/files/betas/<name>")
def serve_beta_file(name):
    if not SAFE_NAME_RE.match(name) or name.startswith("."):
        abort(404)
    return send_from_directory(BETA_FILES_DIR, name, max_age=31536000, conditional=True)


@app.route("/descargar/<beta_id>")
@login_required
def descargar(beta_id):
    b = q("SELECT * FROM betas WHERE id=?", (beta_id,), one=True)
    if not b:
        abort(404)
    execute("UPDATE betas SET downloads=downloads+1 WHERE id=?", (beta_id,))
    if b["download_type"] == "DIRECT" and b["file_url"]:
        name = b["file_url"].rsplit("/", 1)[-1]
        if SAFE_NAME_RE.match(name):
            resp = send_from_directory(BETA_FILES_DIR, name, as_attachment=True,
                                       download_name=b["file_name"] or name)
            return resp
        abort(404)
    if b["external_url"]:
        return redirect(b["external_url"])
    flash("Esta beta aún no tiene archivo de descarga 😅", "warning")
    return redirect(url_for("beta_detail", beta_id=beta_id))


# ══════════════════════ Posts, likes, comentarios, seguir ══════════════════════

@app.route("/api/post", methods=["POST"])
@login_required
def create_post():
    content = (request.json.get("content") or "").strip()
    media = request.json.get("media") or []
    if not content and not media:
        return jsonify({"error": "Escribe algo o sube una imagen jaja"}), 400
    if len(content) > 1000:
        return jsonify({"error": "Máximo 1000 letras por post"}), 400
    if len(media) > 5:
        return jsonify({"error": "Máximo 5 archivos por post"}), 400
    for m in media:
        if not is_valid_media_url(m.get("url")):
            return jsonify({"error": "Los archivos deben estar subidos a DevPlay"}), 400
    pid = new_id()
    execute("INSERT INTO posts (id,author_id,type,content,media_urls,created_at) VALUES (?,?,?,?,?,?)",
            (pid, current_user()["id"], "POST", content or None,
             json.dumps([{"url": m["url"], "kind": media_kind(m["url"])} for m in media]), now_iso()))
    return jsonify({"ok": True, "id": pid})


@app.route("/api/post/<post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    uid = current_user()["id"]
    if q("SELECT 1 x FROM likes WHERE post_id=? AND user_id=?", (post_id, uid), one=True):
        execute("DELETE FROM likes WHERE post_id=? AND user_id=?", (post_id, uid))
        liked = False
    else:
        execute("INSERT INTO likes (id,post_id,user_id,created_at) VALUES (?,?,?,?)",
                (new_id(), post_id, uid, now_iso()))
        liked = True
    n = q("SELECT COUNT(*) c FROM likes WHERE post_id=?", (post_id,), one=True)["c"]
    return jsonify({"ok": True, "liked": liked, "count": n})


@app.route("/api/post/<post_id>/comment", methods=["POST"])
@login_required
def comment_post(post_id):
    content = (request.json.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Escribe tu comentario"}), 400
    if len(content) > 1000:
        return jsonify({"error": "Máximo 1000 letras"}), 400
    if not q("SELECT 1 x FROM posts WHERE id=?", (post_id,), one=True):
        return jsonify({"error": "Ese post ya no existe"}), 404
    u = current_user()
    execute("INSERT INTO comments (id,post_id,user_id,content,created_at) VALUES (?,?,?,?,?)",
            (new_id(), post_id, u["id"], content, now_iso()))
    return jsonify({"ok": True, "username": u["username"], "avatar": u["avatar"], "content": content})


@app.route("/api/seguir/<username>", methods=["POST"])
@login_required
def seguir(username):
    target = q("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404
    uid = current_user()["id"]
    if target["id"] == uid:
        return jsonify({"error": "No puedes seguirte a ti mismo jaja"}), 400
    if q("SELECT 1 x FROM follows WHERE follower_id=? AND followee_id=?", (uid, target["id"]), one=True):
        execute("DELETE FROM follows WHERE follower_id=? AND followee_id=?", (uid, target["id"]))
        following = False
    else:
        execute("INSERT INTO follows (id,follower_id,followee_id,created_at) VALUES (?,?,?,?)",
                (new_id(), uid, target["id"], now_iso()))
        following = True
    n = q("SELECT COUNT(*) c FROM follows WHERE followee_id=?", (target["id"],), one=True)["c"]
    return jsonify({"ok": True, "following": following, "count": n})


# ══════════════════════ Perfil ══════════════════════

@app.route("/u/<username>")
@login_required
def perfil(username):
    user = q("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not user:
        abort(404)
    uid = current_user()["id"]
    stats = {
        "posts": q("SELECT COUNT(*) c FROM posts WHERE author_id=?", (user["id"],), one=True)["c"],
        "betas": q("SELECT COUNT(*) c FROM betas b JOIN posts p ON p.id=b.post_id WHERE p.author_id=?", (user["id"],), one=True)["c"],
        "followers": q("SELECT COUNT(*) c FROM follows WHERE followee_id=?", (user["id"],), one=True)["c"],
        "following": q("SELECT COUNT(*) c FROM follows WHERE follower_id=?", (user["id"],), one=True)["c"],
    }
    following = bool(q("SELECT 1 x FROM follows WHERE follower_id=? AND followee_id=?", (uid, user["id"]), one=True))
    rows = q("SELECT * FROM posts WHERE author_id=? ORDER BY created_at DESC LIMIT 20", (user["id"],))
    items = post_rows(rows)
    user_betas = q("SELECT b.*, u.username FROM betas b JOIN posts p ON p.id=b.post_id "
                   "JOIN users u ON u.id=p.author_id WHERE p.author_id=? ORDER BY b.created_at DESC LIMIT 12", (user["id"],))
    user_betas = [dict(b) for b in user_betas]
    for b in user_betas:
        b["platforms"] = parse_json(b["platforms"], [])
    return render_template("perfil.html", user=user, stats=stats, following=following,
                           items=items, betas=user_betas)


# ══════════════════════ Mensajes directos ══════════════════════

@app.route("/mensajes")
@login_required
def mensajes():
    uid = current_user()["id"]
    convos = q(
        "SELECT u.id, u.username, u.full_name, u.avatar, m.content, m.created_at, m.sender_id, "
        "(SELECT COUNT(*) FROM dms x WHERE x.sender_id=u.id AND x.recipient_id=? AND x.read_at IS NULL) unread "
        "FROM dms m JOIN users u ON u.id = CASE WHEN m.sender_id=? THEN m.recipient_id ELSE m.sender_id END "
        "WHERE m.sender_id=? OR m.recipient_id=? "
        "AND m.id IN (SELECT MAX(id) FROM dms WHERE sender_id=? OR recipient_id=? GROUP BY sender_id, recipient_id) "
        "ORDER BY m.created_at DESC",
        (uid, uid, uid, uid, uid, uid))
    # Dedup por usuario (SQLite no hace DISTINCT ON)
    seen, clean = set(), []
    for c in convos:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        clean.append(c)
    return render_template("mensajes.html", convos=clean)


@app.route("/dm/<username>")
@login_required
def dm_view(username):
    other = q("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not other:
        abort(404)
    uid = current_user()["id"]
    execute("UPDATE dms SET read_at=? WHERE sender_id=? AND recipient_id=? AND read_at IS NULL",
            (now_iso(), other["id"], uid))
    convos = q("SELECT DISTINCT u.id, u.username, u.full_name, u.avatar FROM dms m "
               "JOIN users u ON u.id = CASE WHEN m.sender_id=? THEN m.recipient_id ELSE m.sender_id END "
               "WHERE m.sender_id=? OR m.recipient_id=?", (uid, uid, uid))
    return render_template("dm.html", other=other, convos=convos)


@app.route("/api/dm/<username>", methods=["GET", "POST"])
@login_required
def dm_api(username):
    uid = current_user()["id"]
    other = q("SELECT * FROM users WHERE username=?", (username,), one=True)
    if not other:
        return jsonify({"error": "Usuario no encontrado"}), 404
    if request.method == "POST":
        content = (request.json.get("content") or "").strip()
        if not content:
            return jsonify({"error": "Escribe tu mensaje"}), 400
        if len(content) > 2000:
            return jsonify({"error": "Máximo 2000 letras"}), 400
        execute("INSERT INTO dms (id,sender_id,recipient_id,content,created_at) VALUES (?,?,?,?,?)",
                (new_id(), uid, other["id"], content, now_iso()))
        return jsonify({"ok": True})
    msgs = q("SELECT m.*, u.username FROM dms m JOIN users u ON u.id=m.sender_id WHERE "
             "(sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?) ORDER BY created_at ASC LIMIT 100",
             (uid, other["id"], other["id"], uid))
    return jsonify({"ok": True, "me": uid, "messages": [dict(m) for m in msgs]})


# ══════════════════════ Plaza (chat mundial) ══════════════════════

@app.route("/plaza")
@login_required
def plaza():
    return render_template("plaza.html")


@app.route("/api/chat", methods=["GET", "POST"])
@login_required
def chat_api():
    if request.method == "POST":
        content = (request.json.get("content") or "").strip()
        if not content:
            return jsonify({"error": "Escribe tu mensaje"}), 400
        if len(content) > 500:
            return jsonify({"error": "Máximo 500 letras en la plaza"}), 400
        u = current_user()
        execute("INSERT INTO chat_messages (id,user_id,username,content,created_at) VALUES (?,?,?,?,?)",
                (new_id(), u["id"], u["username"], content, now_iso()))
        return jsonify({"ok": True})
    after = request.args.get("after") or ""
    if after and re.match(r"^\d{4}-\d{2}-\d{2}.*$", after):
        msgs = q("SELECT * FROM chat_messages WHERE created_at>? ORDER BY created_at ASC LIMIT 200", (after,))
    else:
        msgs = q("SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 50")
    msgs = list(reversed(msgs))
    return jsonify({"ok": True, "me": current_user()["id"],
                    "messages": [dict(m) for m in msgs],
                    "server_now": now_iso()})


# ══════════════════════ Pixel (asistente) ══════════════════════

@app.route("/api/pixel", methods=["POST"])
@login_required
def pixel_api():
    message = (request.json.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Escríbele algo a Pixel"}), 400
    if len(message) > 500:
        return jsonify({"error": "Mensaje muy largo pa' Pixel (máx 500)"}), 400
    u = current_user()
    reply = pixel.pixel_reply(message, u["username"])
    execute("INSERT INTO pixel_messages (id,user_id,role,content,created_at) VALUES (?,?,?,?,?)",
            (new_id(), u["id"], "user", message, now_iso()))
    execute("INSERT INTO pixel_messages (id,user_id,role,content,created_at) VALUES (?,?,?,?,?)",
            (new_id(), u["id"], "pixel", reply, now_iso()))
    return jsonify({"ok": True, "reply": reply})


# ══════════════════════ Errores ══════════════════════

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_big(e):
    return jsonify({"error": "Archivo demasiado grande (máx 50MB)"}), 413


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("🎮 Primera vez: sembrando la base de datos...")
        from seed import seed
        seed()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=False)
