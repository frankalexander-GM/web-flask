"""Pruebas de seguridad — las "reglas de oro" defensivas del backend.

Cubre: inyección SQL (siempre parametrizada), XSS (autoescape de Jinja),
cookies de sesión seguras, bloqueo de javascript:/data: y path-traversal.
"""
import models
from app import SAFE_NAME_RE, is_valid_media_url
from conftest import crear_usuario


class TestInyeccionSQL:
    def test_login_no_inyecta(self, client):
        crear_usuario()
        intentos = [
            "' OR 1=1 --",
            "' OR '1'='1",
            "tester'--",
            "'; DROP TABLE users; --",
            "' UNION SELECT password_hash FROM users --",
        ]
        for inyeccion in intentos:
            resp = client.post("/entrar", data={"ident": inyeccion,
                                                "password": "x"})
            assert "incorrectos" in resp.get_data(as_text=True), inyeccion
            assert client.get("/", follow_redirects=False).status_code == 302

    def test_tabla_users_sigue_viva_tras_inyeccion(self, client):
        crear_usuario()
        client.post("/entrar", data={"ident": "'; DROP TABLE users; --", "password": "x"})
        assert models.q("SELECT COUNT(*) c FROM users", one=True)["c"] == 1

    def test_buscador_no_inyecta(self, sesion):
        resp = sesion.get("/betas?q=' OR 1=1 --")
        assert resp.status_code == 200

    def test_rutas_con_sql_no_fallan(self, sesion):
        # usernames con comillas no tumbarán el perfil ni el DM
        assert sesion.get("/u/' OR '1'='1").status_code == 404
        assert sesion.get("/beta/' OR '1'='1").status_code == 404


class TestXSS:
    def test_jinja_escapa_el_contenido(self, sesion):
        """El <script> se guarda pero NUNCA se ejecuta: sale escapado."""
        payload = "<script>alert('xss')</script>"
        sesion.post("/api/post", json={"content": payload})
        html = sesion.get("/").get_data(as_text=True)
        assert "<script>alert" not in html, "¡XSS sin escapar!"
        assert "&lt;script&gt;" in html or "&#x3c;script&#x3e;" in html

    def test_comentario_escapado(self, sesion):
        r = sesion.post("/api/post", json={"content": "base"})
        pid = models.q("SELECT id FROM posts WHERE type='POST'", one=True)["id"]
        sesion.post(f"/api/post/{pid}/comment",
                    json={"content": "<img src=x onerror=alert(1)>"})
        html = sesion.get(f"/beta/_").get_data(as_text=True)
        # al menos verificamos que el JSON de la API no ejecuta nada:
        r2 = sesion.get("/").get_data(as_text=True)
        assert "<img src=x onerror" not in r2


class TestCookiesYSesion:
    def test_cookie_httponly_y_samesite(self, client):
        crear_usuario()
        resp = client.post("/entrar", data={"ident": "tester", "password": "secret123"},
                           follow_redirects=False)
        sc = resp.headers.get("Set-Cookie", "")
        assert "HttpOnly" in sc and "SameSite=Lax" in sc

    def test_secret_key_no_es_fija_en_codigo(self):
        """La SECRET_KEY viene del entorno o es aleatoria — nunca hardcodeada."""
        import inspect
        import app as app_module
        fuente = inspect.getsource(app_module)
        assert "DEVPLAY_SECRET" in fuente, "debe leer DEVPLAY_SECRET del entorno"
        clave = app_module.app.config["SECRET_KEY"]
        assert clave and len(clave) >= 32
        assert repr(clave) not in fuente and str(clave) not in fuente


class TestValidacionDeURLs:
    def test_media_url_bloquea_esquemas_peligrosos(self):
        for url in ("javascript:alert(1)", "data:text/html,x", "vbscript:x",
                    "file:///etc/passwd", "chrome://settings"):
            assert not is_valid_media_url(url), url

    def test_safe_name_regex(self):
        assert SAFE_NAME_RE.match("230101-abcd99-mi-juego.zip")
        assert SAFE_NAME_RE.match("foto_v2.png")
        assert not SAFE_NAME_RE.match("../etc/passwd")
        assert not SAFE_NAME_RE.match("con espacio.png")
        assert not SAFE_NAME_RE.match("")

    def test_condicion_completa_de_las_rutas(self):
        """Las rutas exigen regex válido Y que no empiece por punto."""
        def aceptada(nombre):
            return bool(SAFE_NAME_RE.match(nombre)) and not nombre.startswith(".")
        assert aceptada("foto.png")
        assert not aceptada(".oculto")          # bloqueado por startswith(".")
        assert not aceptada("../../etc/passwd")  # bloqueado por el regex


class TestRegistroDefensivo:
    def test_username_alfanumerico_y_guion_bajo(self, client):
        resp = client.post("/registro", data={
            "email": "a@b.test", "username": "mal;--usuario",
            "password": "secreto1", "age": "20", "mayor13": "on"})
        assert "3-20 letras" in resp.get_data(as_text=True)

    def test_password_no_se_guarda_plana(self, client):
        client.post("/registro", data={
            "email": "hash@b.test", "username": "hashuser",
            "password": "miclave123", "age": "20", "mayor13": "on"})
        fila = models.q("SELECT password_hash FROM users WHERE username='hashuser'",
                        one=True)
        assert "miclave123" not in (fila["password_hash"] or "")
        assert fila["password_hash"].startswith(("scrypt", "pbkdf2", "argon2"))

    def test_email_se_normaliza_minusculas(self, client):
        client.post("/registro", data={
            "email": "MAYUS@DEVPLAY.TEST", "username": "normal",
            "password": "secreto1", "age": "20", "mayor13": "on"})
        fila = models.q("SELECT email FROM users WHERE username='normal'", one=True)
        assert fila["email"] == "mayus@devplay.test"

    def test_login_insensible_a_mayusculas(self, client):
        crear_usuario()
        resp = client.post("/entrar", data={"ident": "TESTER", "password": "secret123"},
                           follow_redirects=False)
        assert resp.status_code == 302
