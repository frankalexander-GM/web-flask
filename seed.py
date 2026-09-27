"""
DevPlay Flask — Semilla de presentación.
30 personas latinas + betas reales de itch.io + posts, comentarios y chat.
Igual que scripts/seed-presentation.mjs de la versión Next.js, pero en Python.
Uso:  python3 seed.py   (borra devplay.db y la reconcrea llena)
"""
import json
import os
import random

from models import BASE_DIR, get_db, init_db, new_id, now_iso
from werkzeug.security import generate_password_hash

DEMO_PASSWORD = "test1234"

# [nombre, username, edad, ciudad, profesión, tags, bio, esDev]
PERSONAS = [
    ["Luna Vera", "lunavera", 24, "Bogotá, Colombia", "Dev de videojuegos", ["dev-2d", "pixel-art", "platformer"], "Hago plataformas pixel art en Godot y me pierdo en los detalles jaja. Ahora mismo: metroidvania de luciérnagas 🌙", True],
    ["Juan Pico", "piko_juan", 31, "Medellín, Colombia", "Programador", ["programmer", "retro", "roguelike"], "Programador de día, roguelikes de noche. Los bugs me temen (mentira, yo a ellos jaja)", True],
    ["Mariana González", "mari_glez", 19, "CDMX, México", "Estudiante de animación", ["animator", "pixel-art", "retro"], "Estudio animación y dibujo pixel art pa' no dormir 💀 Bienvenida la crítica dura", False],
    ["Erik Kraft", "krafterik", 28, "Buenos Aires, Argentina", "Game Designer", ["game-designer", "rpg-fan", "metroidvania"], "Diseño niveles como si fueran rompecabezas crueles. Fan #1 de los RPG de SNES", True],
    ["Tomás Rojas", "tomasdev", 16, "Santiago, Chile", "Estudiante dev", ["programmer", "platformer", "retro"], "16 años, 2 juegos de jam en el bolsillo y muchas ganas. Siempre respondo los DMs ✌️", True],
    ["Valentina Ruiz", "valemakes", 22, "Guayaquil, Ecuador", "Dev + artista", ["dev-2d", "pixel-artist", "horror"], "Hago jueguitos de terror con mi hermana. Cuidado con el callback del ascensor jaja", True],
    ["Diego Núñez", "nube42", 35, "Lima, Perú", "Dev backend", ["programmer", "rpg-fan"], "Backend de profesión, RPG de vocación. Ahora le entro a mi primera novela visual 👀", True],
    ["Teo Sánchez", "teo_pixel", 21, "Madrid, España", "Pixel artist", ["pixel-artist", "retro", "animator"], "Pixel art, walkcycles y una obsesión ilegal con las paletas de 4 colores", False],
    ["Camila Ortega", "camiorta", 18, "Bogotá, Colombia", "Tester QA", ["tester", "horror", "visual-novel"], "Tester de betas: encuentro bugs que ni el dev sabía que tenía jaja. Mándame tu build", False],
    ["Andrés Peña", "andres_p", 27, "Monterrey, México", "Compositor", ["composer", "retro", "rpg-fan"], "Chiptune y baladas de calabozos. ¿Tu juego necesita tema de boss? Escríbeme 🎵", False],
    ["Sofía Lara", "sofi_lara", 20, "Quito, Ecuador", "Streamer", ["streamer", "horror", "pixel-art"], "Streameo indies de madrugada. Si sales en mi canal ya somos amigos 💜", False],
    ["Nicolás Ferrer", "nicofer", 30, "Valencia, España", "Dev 3D", ["dev-3d", "3d-artist", "rpg-fan"], "Blender + Unreal y proyectos demasiado grandes pa' mí. Como todos jaja", True],
    ["Julieta Ramos", "jujuramos", 23, "Rosario, Argentina", "Guionista", ["writer", "visual-novel", "horror"], "Escribo novelas visuales con finales feos 🖤 Fan de los juegos que te dejan pensando", False],
    ["Mateo Cárdenas", "mateo_c", 17, "Cali, Colombia", "Estudiante dev", ["programmer", "platformer", "roguelike"], "Mi computadora es una papa pero mis juegos corren bien jaja. Godot team 🤙", True],
    ["Daniela Cruz", "danicruz", 26, "San José, Costa Rica", "Community Manager", ["community-mgr", "pixel-art", "rpg-fan"], "CM de estudios indie chiquitos. Amo ver crecer una comunidad desde cero ✨", False],
    ["Pablo Mieres", "pablo_m", 33, "Montevideo, Uruguay", "Dev", ["dev-2d", "programmer", "retro"], "Remakeando el juego de mi infancia con permiso de nadie (es mío jaja)", True],
    ["Laura Restrepo", "laura_rest", 29, "Medellín, Colombia", "SFX Designer", ["sfx-designer", "horror", "retro"], "Hago sonidos con la cocina de mi casa. El sartén es mi laboratorio 🔊", False],
    ["Bruno Salas", "bruno_salas", 22, "La Paz, Bolivia", "Dev", ["programmer", "roguelike", "platformer"], "Roguelikes con física rota (a propósito... casi siempre jaja)", True],
    ["Emma Duarte", "emma_d", 15, "Santo Domingo, R. Dominicana", "Estudiante", ["pixel-art", "visual-novel"], "En la escuela me aburro, en mi notebook hago mundos 💫 Aventura gráfica en camino", False],
    ["Kevin Rojas", "kevinr", 38, "Guadalajara, México", "Level Designer", ["level-designer", "metroidvania", "retro"], "20 años jugando metroidvanias, ahora los diseño. El mapa es sagrado 🗺️", False],
    ["Isa Moreno", "isa_moreno", 19, "Barranquilla, Colombia", "Artista 3D", ["3d-artist", "retro"], "Low poly y colores melaza. Blender es mi segundo hogar 🍯", False],
    ["Fabián Ortiz", "fabianortiz", 25, "Asunción, Paraguay", "Dev", ["dev-2d", "pixel-art", "horror"], "Terror 2D con más ambiente que sustos baratos. Demo nueva muy pronto 👀", True],
    ["Renata Silva", "renata_s", 21, "São Paulo, Brasil", "Animadora", ["animator", "pixel-art", "platformer"], "Brasileña haciendo animación frame a frame. Falo português e español jaja", False],
    ["Óscar Vega", "ovega", 34, "Sevilla, España", "Programador", ["programmer", "unity", "retro"], "Estrategia por turnos y café. Mucho café. Y bugs jaja", True],
    ["Paula Niño", "paulan", 18, "Bucaramanga, Colombia", "Tester", ["tester", "platformer", "rpg-fan"], "Beta tester sin piedad pero con cariño 💅 Rompo tu juego antes que los usuarios", False],
    ["Samuel Ibarra", "sam_ibarra", 24, "Cuenca, Ecuador", "Compositor", ["composer", "pixel-art", "roguelike"], "Musiquita pa' juegos chiquitos con alma grande 🎧", False],
    ["Manuela Torres", "manu_torres", 27, "Caracas, Venezuela", "Game Designer", ["game-designer", "visual-novel", "horror"], "Diseño decisiones que duelen jaja. Escribo y diseño en equipo con mi novio", True],
    ["Joaquín Vera", "joaquin_v", 31, "Córdoba, Argentina", "Dev", ["dev-3d", "programmer", "rpg-fan"], "Devolviéndole golpes a Unity desde 2019. Mi RPG tiene 400h de dev y 20 de gameplay jaja", True],
    ["Catalina Duarte", "cata_duarte", 20, "Panamá", "Streamer + artista", ["streamer", "pixel-art", "retro"], "Retos de pixel art en vivo los viernes. Vengan a perder conmigo 🎨", False],
    ["Hugo Martínez", "hugo_m", 40, "Zaragoza, España", "Programador", ["programmer", "godot", "roguelike"], "Padre de dos, dev de uno (mi juego). Duermo poco pero feliz jaja", True],
]

COMMUNITY_POSTS = [
    ["¿Godot o Unity pa' un primer juego de plataformas? Ando perdido entre tutoriales 😅", 2],
    ["Llevo 3 semanas peleando con el sistema de guardado y POR FIN funciona jajaja 🎉 Nunca subestimen una coma", 1],
    ["Gente, ¿ya vieron que se viene un jam de Halloween? ¿Alguien se anima a hacer equipo? Yo dibujo, alguien más programa 👀", 14],
    ["Dato: si tu juego corre a 60fps en tu PC de guerra, no significa que corra en la mía jaja (probénlo en una laptop de 2015, plis)", 24],
    ["Hoy terminé el sprite del boss después de 9 intentos. Le puse cara de traicionado porque así me sentía yo 😂", 7],
    ["Pregunta seria: ¿cuánto cobrar por una banda sonora chiptune de 6 tracks? Es mi primer encargo 🎵", 9],
    ["El tester me mandó un video rompiendo mi juego en 40 segundos. 40 SEGUNDOS. Contratada jaja", 22],
    ["Viernes de betas 🕹️ ¿Qué están jugando estos días? Yo ando en una demo de plataformas que me tiene viciado", 25],
    ["Mi mamá vio mi juego y dijo \"ah pero ¿y cuándo te recibes?\" jajaja el apoyo familiar 🙃", 4],
    ["Terminé de escribir el final de mi novela visual. Lloré. Lo voy a dejar así, no soy tan cruel de cambiarlo 🖤", 12],
    ["Tips pa' las jams nuevas: duerman, coman, y NO refactoricen a las 3am. Escrito con dolor de experiencia jaja", 16],
    ["¿Alguien más usa papel cuadriculado pa' diseñar niveles? Me siento arquitecto de calabozos 🗺️", 19],
    ["Streameo hoy a las 9pm una demo de terror que encontré por aquí. Vengan con la luz prendida 💡", 10],
    ["Dibujé mi primer tileset completo: 32x32, paleta de 8 colores, cero arrepentimientos 🎨", 7],
    ["El mal del desarrollador: abrir el proyecto y solo mirarlo 20 minutos. Hoy lo vencí, avancé 2 quests ✊", 27],
    ["¿Recomendaciones de juegos cortos pa' un stream de 2 horas? Nada de survival craft, porfa 🙏", 28],
    ["Compositor busco equipo pa' el jam 🎧 Hago chiptune y algo de orquestal casero. ¡Escríbanme!", 25],
    ["Mi juego de estrategia por fin tiene IA que no se queda quieta mirando la pared. Es un día histórico jaja", 23],
    ["Hice el sonido de pasos con papitas fritas. El pitch down lo cambia TODO 🔊 Qué maravilla es el audio casero", 16],
    ["Aprendiendo shader para hacer agua pixel art. Tutorial de 10 minutos dijo. Van 4 horas jaja 💦", 0],
]

COMMENTS = [
    "Brutal 🔥🔥", "Probado y me encantó jaja, el arte está increíble", "Va directo a bookmarks 👀",
    "¿Cuándo sale pa' Linux? 🐧", "Mucha suerte con el launch 💪", "El sonido es lo mejor que tiene, no me discutan",
    "Lo jugué anoche y no dormí jaja gracias por nada", "Qué bueno ver más gente haciendo juegos por acá ✨",
    "Feedback: el nivel 2 está difícil pero justo. Sigan así", "Me uno a la jam si aún hay cupo!",
    "Ese sprite del boss está indignante (de lo bueno que está) 😤🔥", "Súper recomendado, la demo es cortita pero con alma",
    "Jaja el final me rompió el corazón 🖤", "¿Con qué motor lo hiciste?", "Esto merece más visibilidad, compartido 💜",
    "Vengo del stream y sí, es buenísimo jaja", "Lo probé con mi hermano y nos quedamos hasta tarde jugando 🎮",
    "El pixel art de este lado de la comunidad está de otro nivel jaja", "Agreguen modo fa' dos jugadores plis 🙏",
    "Suena brutal, cuándo sacas más música? 🎵", "Bajado y jugado. Reportando: adictivo jaja",
    "La estética 70s de la web me tiene flechado también ✌️",
]

CHAT_SEED = [
    [0, "hola gente 👋"], [2, "¿alguien probó la demo de plataformas nueva? jaja buenísimo"],
    [4, "buenas! ando buscando tester pa' mi demo, voluntarios? 👀"], [8, "aquí reportándome desde Bogotá 🇨🇴"],
    [13, "el jam del finde va a estar buenísimo, ya tengo equipo ✨"], [1, "gente del chat, ¿Godot o Unity? pregunta seria"],
    [26, "Godot, next question jaja"], [5, "acabo de subir mi beta, lluevan críticas (no tanto jaja)"],
    [23, "mañana sigo con el boss final 💤 hoy no puedo más"], [19, "quién es de México? voy a una expo indie el mes que viene"],
    [24, "yo 🙋 la Expo Indie de GDL está buenísima"],
]

BETA_STATUSES = ["alpha", "closed_beta", "open_beta", "early_access", "tech_test", "coming_soon"]
VERSIONS = ["v0.1", "v0.2.1", "v0.3", "Alpha 1.2", "v0.5.0", "Beta 0.9", "v1.0.0-rc1", "v0.8.2"]
TAG_POOL = ["2D", "Pixel Art", "Indie", "Multiplayer", "Singleplayer", "Retro", "Meteroidvania", "Terror", "Chiptune"]
REQS = "Mínimo: 2GB RAM · Procesador dual-core · 200MB de espacio · Windows 7+ / Linux / macOS"
INSTALL = "Descarga el ZIP, descomprímelo y ejecuta el archivo del juego. Si tu antivirus se asusta, es normal jaja (es un proyecto indie sin firma digital)."


def seed():
    db_path = os.path.join(BASE_DIR, "devplay.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        for suffix in ("-wal", "-shm"):
            if os.path.exists(db_path + suffix):
                os.remove(db_path + suffix)
    init_db()
    conn = get_db()
    cur = conn.cursor()
    rnd = random.Random(42)
    pw_hash = generate_password_hash(DEMO_PASSWORD)

    # ---------- Usuarios ----------
    user_ids = []
    for nombre, username, edad, ciudad, profesion, tags, bio, es_dev in PERSONAS:
        uid = new_id()
        user_ids.append(uid)
        avatar = f"https://api.dicebear.com/9.x/bottts/svg?seed={username}&backgroundColor=bf5b34,e8c39e,dd8b62,d6a26e"
        cur.execute(
            "INSERT INTO users (id,email,username,password_hash,full_name,bio,avatar,location,profession,age,role,tags,devcoins,created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','-'||?||' days'))",
            (uid, f"{username}@devplay.test", username, pw_hash, nombre, bio, avatar, ciudad, profesion, edad,
             "USER", json.dumps(tags), rnd.choice([100, 150, 220, 340, 500]), rnd.randint(3, 60)),
        )
    print(f"  users: {len(user_ids)}")

    # ---------- Betas desde itch-games.json ----------
    # Datos incluidos en el repo (data/itch-games.json) para que sea autónomo.
    # Si la carpeta vive dentro del monorepo DevPlay, también acepta ../scripts/.
    itch_path = os.path.join(BASE_DIR, "data", "itch-games.json")
    if not os.path.exists(itch_path):
        itch_path = os.path.join(os.path.dirname(BASE_DIR), "scripts", "itch-games.json")
    games = json.load(open(itch_path, encoding="utf-8"))["games"]
    devs = [i for i, u in enumerate(PERSONAS) if u[7]]
    n_betas = 0
    for idx, g in enumerate(games):
        author_i = rnd.choice(devs)
        author_id = user_ids[author_i]
        pid, bid = new_id(), new_id()
        status = rnd.choice(BETA_STATUSES)
        version = rnd.choice(VERSIONS)
        genre = g.get("genreES") or "Otro"
        platforms = json.dumps(g.get("platforms") or ["PC"])
        tags = json.dumps(rnd.sample(TAG_POOL, k=rnd.randint(2, 4)))
        desc = (g.get("description") or
                f"Demo jugable de {g['title']}. Versión temprana: puede contener bugs, funciones a medio hacer y mucha pasión jaja. "
                f"Feedback bienvenido, sobre todo de balance y rendimiento. ¡Gracias por probar betas indie! 🎮").strip()
        if len(desc) < 20:
            desc += " Versión temprana en desarrollo activo — toda retroalimentación ayuda muchísimo."
        cur.execute(
            "INSERT INTO posts (id,author_id,type,content,created_at) VALUES (?,?,?,?,datetime('now','-'||?||' hours'))",
            (pid, author_id, "BETA", f"¡Nueva beta disponible! 🎮 {g['title']}", rnd.randint(1, 300)),
        )
        cur.execute(
            "INSERT INTO betas (id,post_id,title,description,download_type,external_url,external_platform,"
            "beta_status,genre,version,platforms,tags,requirements,install_instructions,cover_image,screenshots,downloads,created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','-'||?||' hours'))",
            (bid, pid, g["title"][:90], desc[:2000], "LINK", g["url"], "itch.io",
             status, genre, version, platforms, tags, REQS, INSTALL, g.get("cover"),
             json.dumps([c for c in [g.get("cover")] if c]), rnd.randint(0, 850), rnd.randint(1, 240)),
        )
        # Comentarios en la beta
        for _ in range(rnd.randint(0, 3)):
            commenter = user_ids[rnd.choice(range(len(user_ids)))]
            cur.execute("INSERT INTO comments (id,post_id,user_id,content,created_at) VALUES (?,?,?,?,datetime('now','-'||?||' hours'))",
                        (new_id(), pid, commenter, rnd.choice(COMMENTS), rnd.randint(0, 100)))
        if rnd.random() < 0.75:
            for _ in range(rnd.randint(1, 7)):
                liker = user_ids[rnd.choice(range(len(user_ids)))]
                cur.execute("INSERT OR IGNORE INTO likes (id,post_id,user_id,created_at) VALUES (?,?,?,datetime('now'))",
                            (new_id(), pid, liker))
        n_betas += 1
    print(f"  betas: {n_betas}")

    # ---------- Posts comunitarios ----------
    for texto, author_i in COMMUNITY_POSTS:
        cur.execute("INSERT INTO posts (id,author_id,type,content,created_at) VALUES (?,?,?,?,datetime('now','-'||?||' hours'))",
                    (new_id(), user_ids[author_i], "POST", texto, rnd.randint(0, 96)))
    print(f"  posts: {len(COMMUNITY_POSTS)}")

    # ---------- Follows ----------
    nf = 0
    for i in range(len(user_ids)):
        for j in rnd.sample(range(len(user_ids)), k=rnd.randint(3, 9)):
            if i != j:
                cur.execute("INSERT OR IGNORE INTO follows (id,follower_id,followee_id,created_at) VALUES (?,?,?,datetime('now'))",
                            (new_id(), user_ids[i], user_ids[j]))
                nf += 1
    print(f"  follows: {nf}")

    # ---------- Chat de la plaza ----------
    base_min = 3
    for author_i, texto in CHAT_SEED:
        base_min += 2
        cur.execute("INSERT INTO chat_messages (id,user_id,username,content,created_at) VALUES (?,?,?,?,datetime('now','-'||?||' minutes'))",
                    (new_id(), user_ids[author_i], PERSONAS[author_i][1], texto, base_min))
    print(f"  chat: {len(CHAT_SEED)}")

    # ---------- DMs de ejemplo hacia nube42 ----------
    nube = user_ids[6]
    convo = [
        (8, "nube42! ¿ya viste mi demo? te mandé el enlace por Discord pero también está acá jaja", 180),
        (6, "¡Ya la bajé! Esta noche la pruebo y te mando feedback completo 🎮", 175),
        (8, "¡Eres el mejor! Ojo con el nivel 3, está cruel 😈", 170),
        (9, "Hola! Vi que buscas música pa' tu novela visual. ¿Qué onda, te late chiptune suave? 🎵", 90),
        (6, "¡Sí! Mándame 2 tracks de muestra y te digo 😄", 85),
    ]
    for author_i, texto, mins in convo:
        sender = user_ids[author_i] if author_i != 6 else nube
        recipient = nube if author_i != 6 else user_ids[author_i]
        cur.execute("INSERT INTO dms (id,sender_id,recipient_id,content,read_at,created_at) VALUES (?,?,?,?,?,datetime('now','-'||?||' minutes'))",
                    (new_id(), sender, recipient, texto, now_iso() if mins < 100 else None, mins))
    print("  dms: 5")

    conn.commit()
    conn.close()
    print("✅ Base sembrada pa' la presentación — entradas: username@devplay.test / test1234")


if __name__ == "__main__":
    seed()
