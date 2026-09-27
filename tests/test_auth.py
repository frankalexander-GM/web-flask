"""Pruebas de integración: registro, login, logout y control de acceso."""
from conftest import crear_usuario, login

import models
from werkzeug.security import check_password_hash


class TestRegistro:
    def test_pagina_registro_200(self, client):
        assert client.get("/registro").status_code == 200

    def test_registro_exitoso(self, client):
        resp = client.post("/registro", data={
            "email": "nueva@devplay.test", "username": "nueva",
            "password": "secreto1", "age": "20", "mayor13": "on",
        }, follow_redirects=False)
        assert resp.status_code == 302, "debe redirigir al feed"
        assert resp.headers["Location"].endswith("/")

        fila = models.q("SELECT * FROM users WHERE username='nueva'", one=True)
        assert fila and fila["devcoins"] == 100
        assert check_password_hash(fila["password_hash"], "secreto1")
        assert "secreto1" not in fila["password_hash"], "NUNCA guardar la clave plana"

    def test_sesion_activa_tras_registro(self, client):
        client.post("/registro", data={
            "email": "nueva@devplay.test", "username": "nueva",
            "password": "secreto1", "age": "20", "mayor13": "on",
        }, follow_redirects=True)
        assert client.get("/").status_code == 200

    def test_email_invalido(self, client):
        resp = client.post("/registro", data={
            "email": "no-es-correo", "username": "x1", "password": "secreto1",
            "age": "20", "mayor13": "on"})
        assert "correo válido" in resp.get_data(as_text=True)

    def test_username_con_espacios(self, client):
        resp = client.post("/registro", data={
            "email": "a@b.test", "username": "con espacios", "password": "secreto1",
            "age": "20", "mayor13": "on"})
        assert "3-20 letras" in resp.get_data(as_text=True)

    def test_password_corta(self, client):
        resp = client.post("/registro", data={
            "email": "a@b.test", "username": "usuario", "password": "123",
            "age": "20", "mayor13": "on"})
        assert "6 caracteres" in resp.get_data(as_text=True)

    def test_menor_de_13_rechazado(self, client):
        resp = client.post("/registro", data={
            "email": "a@b.test", "username": "peque", "password": "secreto1",
            "age": "12", "mayor13": "on"})
        assert "13 años" in resp.get_data(as_text=True)
        assert models.q("SELECT 1 x FROM users WHERE username='peque'", one=True) is None

    def test_sin_casilla_mayor13(self, client):
        resp = client.post("/registro", data={
            "email": "a@b.test", "username": "peque2", "password": "secreto1",
            "age": "20"})
        assert "casilla" in resp.get_data(as_text=True)

    def test_email_duplicado(self, client):
        crear_usuario(email="tomada@devplay.test")
        resp = client.post("/registro", data={
            "email": "tomada@devplay.test", "username": "otroname",
            "password": "secreto1", "age": "20", "mayor13": "on"})
        assert "ya tiene cuenta" in resp.get_data(as_text=True)

    def test_username_duplicado(self, client):
        crear_usuario(username="tomado")
        resp = client.post("/registro", data={
            "email": "nuevo@devplay.test", "username": "tomado",
            "password": "secreto1", "age": "20", "mayor13": "on"})
        assert "tomado" in resp.get_data(as_text=True)


class TestLogin:
    def test_login_con_email(self, client):
        crear_usuario()
        resp = login(client, "tester@devplay.test")
        assert resp.status_code == 302

    def test_login_con_username(self, client):
        crear_usuario()
        resp = login(client, "tester")
        assert resp.status_code == 302

    def test_login_password_incorrecta(self, client):
        crear_usuario()
        resp = login(client, "tester", "clave-mala")
        assert resp.status_code == 200
        assert "incorrectos" in resp.get_data(as_text=True)
        # y NO queda sesión:
        assert client.get("/", follow_redirects=False).status_code == 302

    def test_login_usuario_inexistente(self, client):
        resp = login(client, "fantasma")
        assert "incorrectos" in resp.get_data(as_text=True)

    def test_open_redirect_bloqueado(self, client):
        """next=https://malo.com NO debe mandar fuera del sitio."""
        crear_usuario()
        resp = client.post("/entrar?next=https://malo.com",
                           data={"ident": "tester", "password": "secret123"},
                           follow_redirects=False)
        assert resp.status_code == 302
        assert "malo.com" not in resp.headers["Location"]
        assert resp.headers["Location"].endswith("/")

    def test_next_interno_respetado(self, client):
        crear_usuario()
        resp = client.post("/entrar?next=/betas",
                           data={"ident": "tester", "password": "secret123"},
                           follow_redirects=False)
        assert resp.headers["Location"].endswith("/betas")

    def test_logout(self, client):
        crear_usuario()
        login(client, "tester")
        assert client.get("/", follow_redirects=False).status_code == 200
        client.get("/salir")
        assert client.get("/", follow_redirects=False).status_code == 302


class TestControlDeAcceso:
    def test_paginas_protegidas_redirigen_a_login(self, client):
        for ruta in ("/", "/betas", "/publicar", "/plaza", "/mensajes", "/u/tester"):
            resp = client.get(ruta, follow_redirects=False)
            assert resp.status_code == 302, f"{ruta} debería pedir login"
            assert "/entrar" in resp.headers["Location"]

    def test_apis_protegidas_responden_401(self, client):
        for metodo, ruta in (("post", "/api/post"), ("post", "/api/pixel"),
                             ("post", "/api/upload"), ("get", "/api/chat")):
            resp = client.open(ruta, method=metodo)
            assert resp.status_code == 401, f"{ruta} anon debería ser 401"
            assert "Inicia sesión" in resp.get_json()["error"]

    def test_cookie_de_sesion_segura(self, client):
        crear_usuario()
        resp = client.post("/entrar", data={"ident": "tester", "password": "secret123"},
                           follow_redirects=False)
        set_cookie = resp.headers.get("Set-Cookie", "")
        assert "session" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=Lax" in set_cookie
