"""
Fixtures de pytest para DevPlay Flask — pruebas de software.

Cada prueba corre con:
  • una base de datos SQLite limpia en una carpeta temporal
  • carpetas de subidas (uploads/ y download/betas/) también temporales

Así las pruebas NUNCA tocan los archivos reales del repo.
Correr:  python3 -m pytest tests/ -v
"""
import os
import sys

import pytest
from werkzeug.security import generate_password_hash

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import models  # noqa: E402
import app as app_module  # noqa: E402


@pytest.fixture(autouse=True)
def entorno_aislado(tmp_path, monkeypatch):
    """BD temporal + carpetas de uploads temporales para CADA prueba."""
    monkeypatch.setattr(models, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(app_module, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(app_module, "BETA_FILES_DIR", str(tmp_path / "betas"))
    for sub in ("uploads/media", "uploads/avatar"):
        os.makedirs(tmp_path / sub, exist_ok=True)
    os.makedirs(tmp_path / "betas", exist_ok=True)
    models.init_db()
    yield


@pytest.fixture()
def client():
    """Cliente HTTP de pruebas (Flask test client)."""
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


# ────────────── helpers compartidos ──────────────

def crear_usuario(username="tester", email=None, password="secret123", **extra):
    """Inserta un usuario directo en BD y devuelve su id."""
    uid = models.new_id()
    email = email or f"{username}@devplay.test"
    models.execute(
        "INSERT INTO users (id,email,username,password_hash,full_name,age,avatar,devcoins,"
        "location,profession)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (uid, email, username, generate_password_hash(password),
         extra.get("full_name", username.title()), extra.get("age", 20),
         f"https://api.dicebear.com/9.x/bottts/svg?seed={username}",
         extra.get("devcoins", 100), extra.get("location", "Bogotá, Colombia"),
         extra.get("profession", "Dev de videojuegos")),
    )
    return uid


def login(client, ident, password="secret123"):
    """Login por /entrar. Devuelve la respuesta (302 si fue bien)."""
    return client.post("/entrar", data={"ident": ident, "password": password},
                       follow_redirects=False)


@pytest.fixture()
def sesion(client):
    """Cliente con sesión ya iniciada como 'tester'."""
    crear_usuario()
    login(client, "tester")
    return client


def publicar_beta_valida(client, title="Beta de Prueba", **overrides):
    """Publica una beta válida vía POST /publicar. Devuelve la respuesta 302."""
    datos = {
        "title": title,
        "description": "Descripción suficientemente larga para pasar la fábrica sin problemas jaja",
        "genre": "RPG",
        "version": "v0.1.0",
        "platforms": ["PC", "Linux"],
        "beta_status": "open_beta",
        "download_type": "LINK",
        "external_url": "https://juego.itch.io/demo",
        "cover": "/uploads/media/portada.png",
        "screenshots": "",
        "tags": "Pixel Art, Indie",
    }
    datos.update(overrides)
    return client.post("/publicar", data=datos, follow_redirects=False)


def sembrar_beta_directa(author_id, title="Beta directa", created_hours_ago=0):
    """Inserta post+beta directo en BD (para anti-spam y descargas)."""
    import json as _json
    from datetime import datetime, timedelta
    pid, bid = models.new_id(), models.new_id()
    created = datetime.utcnow()
    if created_hours_ago:
        created -= timedelta(hours=created_hours_ago)
    models.execute("INSERT INTO posts (id,author_id,type,content,created_at) VALUES (?,?,?,?,?)",
                   (pid, author_id, "BETA", f"¡Nueva beta! {title}",
                    created.strftime("%Y-%m-%d %H:%M:%S")))
    models.execute(
        "INSERT INTO betas (id,post_id,title,description,download_type,external_url,"
        "beta_status,genre,version,platforms,cover_image,screenshots,downloads,created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (bid, pid, title, "Descripción suficientemente larga para la fábrica de betas jaja",
         "LINK", "https://juego.itch.io/demo", "open_beta", "RPG", "v0.1",
         _json.dumps(["PC"]), "/uploads/media/portada.png", _json.dumps([]), 0,
         created.strftime("%Y-%m-%d %H:%M:%S")))
    return pid, bid
