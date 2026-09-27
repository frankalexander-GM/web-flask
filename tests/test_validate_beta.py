"""Pruebas unitarias de la fábrica: validate_beta + utilidades de media.

Replica las restricciones de la versión Next.js (src/app/api/devplay/posts):
título 3+, descripción 20-2000, género, versión válida, plataformas,
portada obligatoria, máx 5 capturas, archivo 50MB o enlace externo.
"""
from app import (BETA_EXT, GENRES, LIMITS, VERSION_RE, is_valid_media_url,
                 media_kind, timeago, validate_beta)

VALID = dict(
    title="Mi juego gen", description="Descripción suficientemente larga para pasar",
    genre="RPG", version="v0.1", platforms=["PC"],
    cover="/uploads/media/portada.png", screenshots=[],
    download_type="LINK", file_name=None, file_size=None,
    external_url="https://juego.itch.io/demo",
)


def validar(**cambios):
    return validate_beta(**{**VALID, **cambios})


class TestValidateBetaValido:
    def test_todo_valido_pasa(self):
        assert validar() is None

    def test_versiones_validas(self):
        for v in ("v0.1", "1.0.2", "v1.0.0-rc1", "v0.5.0", "2", "1.2.3-beta"):
            assert validar(version=v) is None, f"versión {v} debería pasar"

    def test_versiones_invalidas_frase(self):
        # "Alpha 1.2" no cumple el formato (la fábrica pide v0.1 / 1.0.2)
        for v in ("Alpha 1.2", "Beta 0.9"):
            assert "formato válido" in validar(version=v), f"versión {v} debería fallar"

    def test_portada_video_y_externa(self):
        assert validar(cover="/files/betas/demo.mp4") is None
        assert validar(cover="https://cdn.algo.com/cover.png") is None

    def test_hasta_5_capturas(self):
        caps = [f"/uploads/media/c{i}.png" for i in range(5)]
        assert validar(screenshots=caps) is None

    def test_generos_todos_aceptados(self):
        for g in GENRES:
            assert validar(genre=g) is None


class TestValidateBetaRechaza:
    def test_titulo_corto(self):
        assert "título necesita al menos 3 letras" in validar(title="ab")

    def test_titulo_solo_espacios(self):
        assert validar(title="   ") is not None

    def test_descripcion_corta(self):
        assert "20 letras" in validar(description="muy corta")

    def test_descripcion_larga_demasiado(self):
        assert "2000" in validar(description="a" * 2001)

    def test_genero_invalido(self):
        assert "género" in validar(genre="MMO").lower()

    def test_genero_vacio(self):
        assert validar(genre="") is not None

    def test_version_obligatoria(self):
        assert "obligatoria" in validar(version="")

    def test_version_formato_invalido(self):
        for v in ("abc!!", "v..1", "1.2.3.4.5", "versión beta", "v 0.1"):
            assert "formato válido" in validar(version=v), f"versión {v} debería fallar"

    def test_sin_plataformas(self):
        assert "al menos una plataforma" in validar(platforms=[])

    def test_max_10_plataformas(self):
        muchas = ["PC"] * 11
        assert "Máximo 10 plataformas" in validar(platforms=muchas)

    def test_portada_obligatoria(self):
        assert "Sube una portada" in validar(cover="")

    def test_portada_javascript_bloqueada(self):
        assert validar(cover="javascript:alert(1)") is not None
        assert validar(cover="data:text/html,hola") is not None

    def test_max_5_capturas(self):
        caps = [f"/uploads/media/c{i}.png" for i in range(6)]
        assert "Máximo 5 capturas" in validar(screenshots=caps)

    def test_capturas_solo_de_devplay(self):
        assert "Las capturas deben ser archivos subidos" in validar(
            screenshots=["javascript:x"])

    def test_direct_sin_archivo(self):
        assert "Sube el archivo de tu beta" in validar(
            download_type="DIRECT", file_name=None)

    def test_direct_pasa_de_50mb(self):
        assert "pasa de 50MB" in validar(
            download_type="DIRECT", file_name="juego.zip",
            file_size=51 * 1024 * 1024)

    def test_direct_justo_50mb_pasa(self):
        assert validar(download_type="DIRECT", file_name="juego.zip",
                       file_size=50 * 1024 * 1024) is None

    def test_link_invalido(self):
        assert "enlace externo válido" in validar(external_url="no-es-link")
        assert "enlace externo válido" in validar(external_url="")

    def test_download_type_desconocido(self):
        assert "Elige cómo se descarga" in validar(download_type="TORRENT")


class TestVersionRegex:
    def test_regex_directa(self):
        assert VERSION_RE.match("v0.1")
        assert VERSION_RE.match("1.0.2")
        assert VERSION_RE.match("v1.0.0-rc1")
        assert not VERSION_RE.match("no sé")


class TestMediaUtils:
    def test_media_kind(self):
        assert media_kind("https://x.com/a.mp4") == "video"
        assert media_kind("/uploads/media/b.webm") == "video"
        assert media_kind("/uploads/media/c.MOV") == "video"
        assert media_kind("/uploads/media/d.png") == "image"
        assert media_kind("/uploads/media/e.gif") == "image"
        assert media_kind("https://x.com/f.mp4?token=1") == "video"
        assert media_kind(None) == "image"

    def test_is_valid_media_url(self):
        assert is_valid_media_url("/uploads/media/a.png")
        assert is_valid_media_url("/files/betas/a.zip")
        assert is_valid_media_url("https://x.com/a.png")
        assert is_valid_media_url("http://x.com/a.png")
        assert not is_valid_media_url(None)
        assert not is_valid_media_url("")
        assert not is_valid_media_url("javascript:alert(1)")
        assert not is_valid_media_url("data:image/png;base64,AAAA")
        assert not is_valid_media_url("ftp://x.com/a.png")
        assert not is_valid_media_url("////etc/passwd")

    def test_limites_conocidos(self):
        assert LIMITS == {"img_mb": 8, "video_mb": 25, "avatar_mb": 5, "beta_mb": 50}
        assert "zip" in BETA_EXT and "apk" in BETA_EXT and "png" not in BETA_EXT

    def test_timeago(self):
        from datetime import datetime, timedelta
        ahora = datetime.utcnow()
        assert timeago(ahora.strftime("%Y-%m-%d %H:%M:%S")) == "ahora"
        assert timeago((ahora - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")) == "5m"
        assert timeago((ahora - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")) == "3h"
        assert timeago((ahora - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")) == "2d"
        assert "mes" in timeago((ahora - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"))
        assert timeago("") == "" and timeago(None) == ""
