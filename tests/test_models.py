"""Pruebas unitarias de models.py — esquema, helpers e integridad."""
import sqlite3

import pytest

import models
from models import execute, new_id, now_iso, q


class TestHelpers:
    def test_new_id_unico(self):
        ids = {new_id() for _ in range(200)}
        assert len(ids) == 200, "new_id() debe generar ids únicos"
        assert all(len(i) == 24 for i in ids)

    def test_now_iso_formato(self):
        valor = now_iso()
        assert len(valor) == 19 and valor[10] == " "
        assert valor[4] == "-" and valor[13] == ":"

    def test_q_y_execute(self):
        uid = crear_usuario_base()
        fila = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
        assert fila["username"] == "tester"
        assert q("SELECT * FROM users WHERE id=?", ("nadie",), one=True) is None

    def test_sql_parametrizado_siempre(self):
        uid = crear_usuario_base()
        # Si concatenaran strings, esto vaciaría la tabla; con parámetros no pasa nada
        filas = q("SELECT * FROM users WHERE username=? OR username=?",
                  ("tester", "' OR 1=1 --"))
        assert len(filas) == 1


def crear_usuario_base():
    execute(
        "INSERT INTO users (id,email,username,password_hash,full_name,age,avatar,devcoins)"
        " VALUES (?,?,?,?,?,?,?,100)",
        (new_id(), "tester@devplay.test", "tester", "hash", "Tester", 20, "a.png"),
    )
    return q("SELECT id FROM users WHERE username='tester'", one=True)["id"]


class TestEsquema:
    def test_tablas_creadas(self):
        tablas = {r["name"] for r in q("SELECT name FROM sqlite_master WHERE type='table'")}
        esperadas = {"users", "posts", "betas", "comments", "likes", "follows",
                     "dms", "chat_messages", "notifications", "pixel_messages"}
        assert esperadas <= tablas

    def test_email_unico(self):
        crear_usuario_base()
        with pytest.raises(sqlite3.IntegrityError):
            execute(
                "INSERT INTO users (id,email,username,password_hash,full_name,age,avatar)"
                " VALUES (?,?,?,?,?,?,?)",
                (new_id(), "tester@devplay.test", "otro", "hash", "Otro", 20, "b.png"),
            )

    def test_username_unico(self):
        crear_usuario_base()
        with pytest.raises(sqlite3.IntegrityError):
            execute(
                "INSERT INTO users (id,email,username,password_hash,full_name,age,avatar)"
                " VALUES (?,?,?,?,?,?,?)",
                (new_id(), "otro@devplay.test", "tester", "hash", "Otro", 20, "b.png"),
            )

    def test_like_unico_por_usuario(self):
        uid = crear_usuario_base()
        execute("INSERT INTO posts (id,author_id,type,content,created_at) VALUES (?,?,?,?,?)",
                (new_id(), uid, "POST", "hola", now_iso()))
        pid = q("SELECT id FROM posts", one=True)["id"]
        execute("INSERT INTO likes (id,post_id,user_id,created_at) VALUES (?,?,?,?)",
                (new_id(), pid, uid, now_iso()))
        with pytest.raises(sqlite3.IntegrityError):
            execute("INSERT INTO likes (id,post_id,user_id,created_at) VALUES (?,?,?,?)",
                    (new_id(), pid, uid, now_iso()))

    def test_cascade_borra_posts_y_betas(self):
        uid = crear_usuario_base()
        pid, bid = new_id(), new_id()
        execute("INSERT INTO posts (id,author_id,type,content,created_at) VALUES (?,?,?,?,?)",
                (pid, uid, "BETA", "beta", now_iso()))
        execute("INSERT INTO betas (id,post_id,title,description,cover_image) "
                "VALUES (?,?,?,?,?)", (bid, pid, "T", "Desc larga suficiente", "c.png"))
        execute("DELETE FROM users WHERE id=?", (uid,))
        assert q("SELECT 1 x FROM posts WHERE id=?", (pid,), one=True) is None
        assert q("SELECT 1 x FROM betas WHERE id=?", (bid,), one=True) is None

    def test_defaults_de_usuario(self):
        uid = crear_usuario_base()
        u = q("SELECT * FROM users WHERE id=?", (uid,), one=True)
        assert u["role"] == "USER" and u["devcoins"] == 100
        assert u["language"] == "es" and u["tour_completed"] == 0
