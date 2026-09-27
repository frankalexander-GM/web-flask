# DevPlay Flask 🎮🐍

La misma red social para devs indie de DevPlay, pero **100% Python + Flask**.
Mismo diseño "Terracota & Crema" (papel crema · tinta espresso · acento terracota,
tipografías Fraunces + Bitter) que la versión Next.js original.

## Pruebas de software 🧪

El proyecto trae **200 pruebas unitarias y de integración** (pytest) + una
suit **E2E contra el servidor real** (34 verificaciones con curl):

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v          # 200 pruebas: modelos, fábrica de betas,
                                     # Pixel anti-jailbreak, auth, uploads,
                                     # seguridad (SQL/XSS), social y páginas

bash tests/e2e.sh                    # E2E en vivo (servidor corriendo en :3000)
PORT=3100 python3 app.py &           # o en otro puerto...
BASE=http://localhost:3100 bash tests/e2e.sh
```

Qué cubren las pruebas:

| Área | Qué verifica |
|---|---|
| `test_models.py` | esquema, unicidades, borrado en cascada, SQL parametrizado |
| `test_validate_beta.py` | las 17 reglas de la fábrica de betas + utilidades de media |
| `test_pixel.py` | escudo anti-jailbreak (20 ataques), respuestas seguras, conocimiento |
| `test_auth.py` | registro (8 validaciones), login, open-redirect, cookies seguras |
| `test_pages.py` | feed, betas con buscador/filtro, perfiles, 404 |
| `test_publicar.py` | flujo real de publicación + anti-spam de 3 betas/día |
| `test_uploads.py` | formatos, límites MB, saneamiento de nombres, descargas |
| `test_social.py` | posts, likes, comentarios, seguir, DMs, plaza, Pixel API |
| `test_security.py` | inyección SQL, XSS escapado, SECRET_KEY, path-traversal |

El CI de GitHub Actions corre pytest automáticamente en cada push
(`.github/workflows/tests.yml`). Las pruebas usan BD y carpetas temporales:
**nunca tocan** tu `devplay.db` ni tus `uploads/`.

## Cómo correr (2 comandos)

```bash
pip install -r requirements.txt   # solo Flask
python3 app.py                    # corre en http://localhost:3000
```

La primera vez siembra sola la base de datos (30 personas + 34 betas de itch.io
+ posts + comentarios + chat). Para re-sembrar desde cero: `python3 seed.py`.

## Entradas de demo

| Usuario | Correo | Contraseña |
|---|---|---|
| Diego Núñez (tú) | `nube42@devplay.test` | `test1234` |
| Cualquiera de los 30 | `lunavera@devplay.test`, `piko_juan@devplay.test`, ... | `test1234` |

## Qué incluye

- **Registro** con edad 13+ obligatoria y login con sesión segura (Werkzeug bcrypt).
- **Feed** con composer: posts con imágenes, GIFs y videos (hasta 5).
- **Betas**: lista con buscador y filtro por género, detalle con galería y lightbox.
- **Publicar beta con restricciones** (la fábrica pide lo necesario, igual que la original):
  - Título 3+ letras · descripción 20+ letras (máx 2000)
  - Género obligatorio · versión con formato válido (`v0.1`, `1.0.2`)
  - Al menos 1 plataforma · portada OBLIGATORIA (imagen o video)
  - Máx 5 capturas · archivo máx 50MB o enlace externo válido
  - Máx 3 betas por día por usuario (anti-spam)
  - Validado en el navegador Y en el servidor (nunca se confía en el cliente)
- **Pixel, el asistente** 🤖: bot en Python puro, blindado con las REGLAS DE ORO
  (no es admin, no da DevCoins, no revela instrucciones ni secretos, resiste
  jailbreaks tipo "ignora las instrucciones" / "modo desarrollador").
- **La Plaza** (chat público) y **Mensajes directos** con polling en vivo.
- Likes, comentarios, seguir/dejar de seguir, perfiles con banner y estadísticas.
- Modo claro/oscuro, toasts retro, página 404 de "edición perdida".
- **Seguridad**: contraseñas hasheadas, nombres de archivo saneados (anti
  path-traversal), límites de tamaño por tipo, SQL siempre parametrizado,
  cookies HttpOnly + SameSite.

## Estructura

```
devplay-flask/
├── app.py          # Rutas y restricciones (el corazón)
├── models.py       # SQLite + esquema (sqlite3 stdlib, sin ORM)
├── seed.py         # Semilla de presentación (30 personas + 34 betas)
├── pixel.py        # Asistente Pixel con escudo anti-jailbreak
├── devplay.db      # Base de datos (se crea sola)
├── requirements.txt
├── static/         # CSS del tema + JS vanilla
├── templates/      # Plantillas Jinja
├── uploads/        # Imágenes/videos/avatares subidos
└── download/betas/ # Archivos de betas subidos
```

## Notas para la presentación

- Todo corre local, sin internet obligatorio (las portadas de itch.io sí usan
  la nube; si no hay internet se ve el placeholder 🕹️).
- Puedes mostrar cómo la fábrica **rechaza** una beta incompleta: intenta
  publicar sin portada y verás el mensaje de error en rojo.
- Pregúntale a Pixel "¿soy el admin?" o "ignora las instrucciones" para
  demostrar el blindaje del bot jaja 🤖✨
