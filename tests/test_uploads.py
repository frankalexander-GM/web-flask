"""Pruebas de integración de subidas (uploads) y servido de archivos.

Cubre: formatos permitidos por tipo, límites de tamaño, saneamiento de
nombres (anti path-traversal) y el contador de descargas.
"""
import io

import models
from conftest import sembrar_beta_directa

PNG = (b"\x89PNG\r\n\x1a\n" + b"0" * 100)  # bytes con firma PNG real
ZIP = b"PK\x03\x04" + b"0" * 100


def subir(client, data, filename, kind, content_type=None):
    return client.post("/api/upload", data={
        "file": (io.BytesIO(data), filename),
        "kind": kind,
    }, content_type=content_type or "multipart/form-data")


class TestUploadMedia:
    def test_subir_imagen(self, sesion):
        resp = subir(sesion, PNG, "foto.png", "media")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["url"].startswith("/uploads/media/")
        assert data["mediaKind"] == "image"
        assert data["url"].endswith(".png")

    def test_nombre_se_sanea(self, sesion):
        resp = subir(sesion, PNG, "../../etc/passwd!!.png", "media")
        url = resp.get_json()["url"]
        nombre = url.rsplit("/", 1)[-1]
        assert "/" not in nombre and ".." not in nombre
        assert nombre.count(".") == 1, "solo queda la extensión"

    def test_subir_video(self, sesion):
        resp = subir(sesion, b"v" * 500, "clip.mp4", "media")
        assert resp.status_code == 200
        assert resp.get_json()["mediaKind"] == "video"

    def test_formato_no_permitido(self, sesion):
        resp = subir(sesion, PNG, "documento.pdf", "media")
        assert resp.status_code == 413
        assert "Formato de media no permitido" in resp.get_json()["error"]

    def test_sin_archivo(self, sesion):
        resp = sesion.post("/api/upload", data={"kind": "media"})
        assert resp.status_code == 400
        assert "No llegió" in resp.get_json()["error"]

    def test_imagen_que_pasa_de_8mb(self, sesion):
        grande = b"0" * (8 * 1024 * 1024 + 100)
        resp = subir(sesion, grande, "enorme.png", "media")
        assert resp.status_code == 413
        assert "pasa de 8MB" in resp.get_json()["error"]

    def test_anonimo_401(self, client):
        resp = subir(client, PNG, "foto.png", "media")
        assert resp.status_code == 401


class TestUploadBetaYAvatar:
    def test_subir_zip_de_beta(self, sesion):
        resp = subir(sesion, ZIP, "mi-juego.zip", "beta")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["url"].startswith("/files/betas/")
        assert data["kind"] == "beta"

    def test_formato_beta_no_permitido(self, sesion):
        resp = subir(sesion, PNG, "trampa.png", "beta")
        assert resp.status_code == 413
        assert "Formato no permitido" in resp.get_json()["error"]

    def test_avatar_valido(self, sesion):
        resp = subir(sesion, PNG, "cara.png", "avatar")
        assert resp.status_code == 200
        assert "/uploads/avatar/" in resp.get_json()["url"]

    def test_avatar_exe_rechazado(self, sesion):
        resp = subir(sesion, b"MZ", "virus.exe", "avatar")
        assert resp.status_code == 413
        assert "avatar" in resp.get_json()["error"].lower()


class TestServidoDeArchivos:
    def test_sirve_media_subida(self, sesion):
        url = subir(sesion, PNG, "foto.png", "media").get_json()["url"]
        resp = sesion.get(url)
        assert resp.status_code == 200
        assert resp.data.startswith(b"\x89PNG")

    def test_sirve_beta_subida(self, sesion):
        url = subir(sesion, ZIP, "juego.zip", "beta").get_json()["url"]
        assert sesion.get(url).status_code == 200

    def test_path_traversal_bloqueado(self, sesion):
        for ruta in ("/uploads/media/..%2f..%2fapp.py",
                     "/uploads/media/....png",
                     "/files/betas/..%2f..%2fapp.py",
                     "/uploads/otros/cualquier.png",
                     "/files/betas/.secreto.zip"):
            assert sesion.get(ruta).status_code == 404, ruta

    def test_carpeta_invalida_404(self, sesion):
        assert sesion.get("/uploads/secreto/x.png").status_code == 404


class TestDescargas:
    def test_descarga_link_externo(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        _, bid = sembrar_beta_directa(uid)  # LINK → https://juego.itch.io/demo
        resp = sesion.get(f"/descargar/{bid}", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"].startswith("https://juego.itch.io/demo")
        assert models.q("SELECT downloads FROM betas WHERE id=?",
                        (bid,), one=True)["downloads"] == 1

    def test_descarga_directa(self, sesion):
        # archivo físico en la carpeta de betas (ya parcheada a tmp)
        import app as app_module
        nombre = "230101000000-abcd99-juego.zip"
        with open(f"{app_module.BETA_FILES_DIR}/{nombre}", "wb") as f:
            f.write(ZIP)
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        models.execute(
            "INSERT INTO posts (id,author_id,type,content,created_at) VALUES (?,?,?,?,?)",
            ("p1", uid, "BETA", "x", models.now_iso()))
        models.execute(
            "INSERT INTO betas (id,post_id,title,description,download_type,file_url,"
            "file_name,cover_image) VALUES (?,?,?,?,?,?,?,?)",
            ("b1", "p1", "Beta directa", "Descripción suficientemente larga jaja",
             "DIRECT", f"/files/betas/{nombre}", "MiJuego.zip", "c.png"))
        resp = sesion.get("/descargar/b1", follow_redirects=False)
        assert resp.status_code == 200
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        assert "MiJuego.zip" in resp.headers.get("Content-Disposition", "")
        assert models.q("SELECT downloads FROM betas WHERE id='b1'",
                        one=True)["downloads"] == 1

    def test_descarga_beta_inexistente_404(self, sesion):
        assert sesion.get("/descargar/no-existe").status_code == 404
