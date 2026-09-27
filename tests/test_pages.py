"""Pruebas de integración: páginas principales y sus filtros."""
from conftest import crear_usuario, sembrar_beta_directa

import models


class TestFeed:
    def test_feed_200(self, sesion):
        html = sesion.get("/").get_data(as_text=True)
        assert "DevPlay" in html

    def test_feed_muestra_posts(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        models.execute("INSERT INTO posts (id,author_id,type,content,created_at) "
                       "VALUES (?,?,?,?,?)",
                       (models.new_id(), uid, "POST", "post especial de prueba",
                        models.now_iso()))
        html = sesion.get("/").get_data(as_text=True)
        assert "post especial de prueba" in html

    def test_feed_sugiere_otras_personas(self, sesion):
        crear_usuario(username="lunavera")
        html = sesion.get("/").get_data(as_text=True)
        assert "lunavera" in html


class TestBetas:
    def test_lista_vacia(self, sesion):
        assert sesion.get("/betas").status_code == 200

    def test_lista_muestra_betas(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        sembrar_beta_directa(uid, title="Metroidvania de luciérnagas")
        html = sesion.get("/betas").get_data(as_text=True)
        assert "Metroidvania de luciérnagas" in html

    def test_buscador(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        sembrar_beta_directa(uid, title="Juego de carreras locas")
        html = sesion.get("/betas?q=carreras").get_data(as_text=True)
        assert "carreras locas" in html
        html = sesion.get("/betas?q=zzz-inexistente").get_data(as_text=True)
        assert "carreras locas" not in html

    def test_filtro_genero(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        sembrar_beta_directa(uid, title="RPG de prueba")
        models.execute("UPDATE betas SET genre='RPG'")
        assert sesion.get("/betas?genero=RPG").status_code == 200
        html = sesion.get("/betas?genero=Terror").get_data(as_text=True)
        assert "RPG de prueba" not in html

    def test_detalle_beta(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        _, bid = sembrar_beta_directa(uid, title="Beta con detalle")
        resp = sesion.get(f"/beta/{bid}")
        assert resp.status_code == 200
        assert "Beta con detalle" in resp.get_data(as_text=True)

    def test_detalle_inexistente_404(self, sesion):
        assert sesion.get("/beta/no-existe").status_code == 404


class TestPerfil:
    def test_perfil_propio(self, sesion):
        resp = sesion.get("/u/tester")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Tester" in html

    def test_perfil_inexistente_404(self, sesion):
        assert sesion.get("/u/fantasma").status_code == 404

    def test_perfil_con_stats(self, sesion):
        uid = models.q("SELECT id FROM users WHERE username='tester'", one=True)["id"]
        sembrar_beta_directa(uid)
        html = sesion.get("/u/tester").get_data(as_text=True)
        assert "betas" in html.lower()


class TestOtrasPaginas:
    def test_plaza(self, sesion):
        assert sesion.get("/plaza").status_code == 200

    def test_mensajes(self, sesion):
        assert sesion.get("/mensajes").status_code == 200

    def test_publicar_get(self, sesion):
        html = sesion.get("/publicar").get_data(as_text=True)
        assert "género" in html.lower() and "portada" in html.lower()

    def test_dm_pagina(self, sesion):
        crear_usuario(username="lunavera")
        assert sesion.get("/dm/lunavera").status_code == 200

    def test_dm_inexistente_404(self, sesion):
        assert sesion.get("/dm/fantasma").status_code == 404

    def test_404_personalizada(self, sesion):
        resp = sesion.get("/esta/ruta/no/existe")
        assert resp.status_code == 404
