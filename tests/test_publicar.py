"""Pruebas de integración de /publicar — la fábrica de betas.

Verifica TODAS las restricciones en el flujo real (POST → HTML):
las mismas que la versión Next.js valida en el servidor.
"""
import json

import models
from conftest import crear_usuario, publicar_beta_valida, sembrar_beta_directa


def postear(sesion, **cambios):
    base = dict(
        title="Mi juego gen",
        description="Descripción suficientemente larga para pasar la fábrica jaja",
        genre="RPG", version="v0.1", platforms=["PC"],
        beta_status="open_beta", download_type="LINK",
        external_url="https://juego.itch.io/demo",
        cover="/uploads/media/portada.png", screenshots="", tags="",
    )
    base.update(cambios)
    return sesion.post("/publicar", data=base)


class TestPublicacionValida:
    def test_publica_y_redirige_al_detalle(self, sesion):
        resp = publicar_beta_valida(sesion, title="Beta válida de pytest")
        assert resp.status_code == 302, "debe redirigir al detalle de la beta"
        bid = resp.headers["Location"].rsplit("/", 1)[-1]
        beta = models.q("SELECT * FROM betas WHERE id=?", (bid,), one=True)
        assert beta and beta["title"] == "Beta válida de pytest"
        assert json.loads(beta["platforms"]) == ["PC", "Linux"]
        assert beta["downloads"] == 0

    def test_crea_post_tipo_beta(self, sesion):
        publicar_beta_valida(sesion)
        post = models.q("SELECT * FROM posts WHERE type='BETA'", one=True)
        assert post and "¡Nueva beta disponible!" in post["content"]

    def test_tags_se_guardan_como_json(self, sesion):
        publicar_beta_valida(sesion, tags="Pixel Art, Indie, Retro")
        beta = models.q("SELECT tags FROM betas", one=True)
        assert json.loads(beta["tags"]) == ["Pixel Art", "Indie", "Retro"]

    def test_detalle_muestra_la_beta(self, sesion):
        resp = publicar_beta_valida(sesion, title="Visible en detalle")
        bid = resp.headers["Location"].rsplit("/", 1)[-1]
        html = sesion.get(f"/beta/{bid}").get_data(as_text=True)
        assert "Visible en detalle" in html


class TestRestricciones:
    def test_titulo_corto(self, sesion):
        html = postear(sesion, title="ab").get_data(as_text=True)
        assert "El título necesita al menos 3 letras" in html

    def test_descripcion_corta(self, sesion):
        html = postear(sesion, description="corta").get_data(as_text=True)
        assert "20 letras" in html

    def test_genero_falta(self, sesion):
        html = postear(sesion, genre="").get_data(as_text=True)
        assert "Elige el género" in html

    def test_version_invalida(self, sesion):
        html = postear(sesion, version="abc!!").get_data(as_text=True)
        assert "formato válido" in html

    def test_sin_plataformas(self, sesion):
        html = postear(sesion, platforms=[]).get_data(as_text=True)
        assert "al menos una plataforma" in html

    def test_portada_obligatoria(self, sesion):
        html = postear(sesion, cover="").get_data(as_text=True)
        assert "Sube una portada" in html

    def test_link_externo_invalido(self, sesion):
        html = postear(sesion, external_url="no-es-link").get_data(as_text=True)
        assert "enlace externo válido" in html

    def test_nada_se_guarda_cuando_falla(self, sesion):
        postear(sesion, title="ab")
        assert models.q("SELECT 1 x FROM posts", one=True) is None
        assert models.q("SELECT 1 x FROM betas", one=True) is None


class TestAntiSpam:
    def test_max_3_betas_por_dia(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        for i in range(3):
            sembrar_beta_directa(uid, title=f"Previa {i}")
        html = publicar_beta_valida(sesion, title="La cuarta de hoy").get_data(as_text=True)
        assert "3 betas hoy" in html
        assert models.q("SELECT * FROM betas WHERE title='La cuarta de hoy'",
                        one=True) is None

    def test_al_dia_siguiente_se_puede(self, sesion):
        """Betas de hace 2 días no cuentan para el límite diario."""
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        for i in range(3):
            _, bid = sembrar_beta_directa(uid, title=f"Vieja {i}")
            models.execute(
                "UPDATE betas SET created_at=datetime('now','-2 days') WHERE id=?", (bid,))
            pid = models.q("SELECT post_id FROM betas WHERE id=?", (bid,), one=True)["post_id"]
            models.execute(
                "UPDATE posts SET created_at=datetime('now','-2 days') WHERE id=?", (pid,))
        resp = publicar_beta_valida(sesion, title="Nueva de hoy")
        assert resp.status_code == 302

    def test_otro_usuario_no_afecta_mi_limite(self, sesion):
        otro = crear_usuario(username="otrodev")
        for i in range(3):
            sembrar_beta_directa(otro, title=f"De otro {i}")
        resp = publicar_beta_valida(sesion, title="Mía tranquila")
        assert resp.status_code == 302
