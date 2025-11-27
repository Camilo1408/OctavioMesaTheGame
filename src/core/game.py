import pygame
import sys
from entities.player import Player
from core.camera import Camera
from core.map import TileMap
from entities.enemy import Enemy
from core.game_state import GameState
from core.settings import (
    SCREEN_HEIGTH, SCREEN_WIDTH, FPS, WINDOW_TITLE, COLOR_BG,
    ENEMY_INITIAL_SPAWN_INTERVAL, ENEMY_MIN_SPAWN_INTERVAL,
    ENEMY_SPAWN_INTERVAL_STEP, ENEMY_MAX_ON_SCREEN_BASE, 
    ENEMIES_PER_LEVEL, MAX_PLAYER_LEVEL, XP_PER_KILL, KILLS_PER_BANDAGE, MAX_BANDAGES,
    PLAYER_XP_BASE,
    DEBUG_DRAW_HITBOXES,
    DEBUG_DRAW_ATTACK_FIELDS, ENEMY_BASE_HEALTH, SPECIAL_FRONTAL_DAMAGE,
    SPECIAL_SPIRAL_DAMAGE, SPECIAL_RADIUS, XP_PER_KILL, SPECIAL_FRONTAL_KILLS,SPECIAL_SPIRAL_KILLS
)
import math, os, random
from entities.boss_diablo import BossDiablo



class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGTH))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        
        # --- Estados de juego ---
        self.state = GameState.MENU

        # --- Progresión ---
        self.level = 1
        self.kills = 0        # total de enemigos derrotados
        self.score = 0        # puntos

        # Flag para menú de subida de nivel
        self.pending_level_up_choice = False

        self.max_enemies_on_screen = ENEMY_MAX_ON_SCREEN_BASE

        # Tiempo de partida (en segundos)
        self.run_time = 0.0

        # Resumen de la última partida (para mostrar en el menú)
        self.last_run_summary = None
        
        # --- Spawn dinámico ---
        self.spawn_timer = 0.0
        self.spawn_interval = ENEMY_INITIAL_SPAWN_INTERVAL
        self.max_enemies_on_screen = ENEMY_MAX_ON_SCREEN_BASE


        # Create game objects
        # Configure player to use 8 frames per direction and 1-based row indexing
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGTH // 2,
                            frames_per_direction=8,
                            unarmed_row=39,
                            armed_row=9,
                            row_index_base=1)
        
        self.level = self.player.level  # sincronizar nivel del juego con nivel del jugador

        # Efectos visuales de habilidades especiales (Q/E)
        # Cada efecto será un dict con:
        # {
        #   "type": "frontal" | "spiral",
        #   "time": float,
        #   "duration": float,
        #   "direction": str,   # 'up','down','left','right' (para frontal)
        #   "center": (x, y),   # posición del jugador cuando casteó
        # }
        self.special_effects = []

        # DEBUG: comprobar balance de daño en nivel 1

        print("=== DEBUG BALANCE NIVEL 1 ===")
        print(f"Vida enemigo base: {ENEMY_BASE_HEALTH}")
        print(f"Daño puños (sin fuerza extra): {self.player.base_attack_damage_unarmed}")
        print(f"Golpes necesarios (puños): {ENEMY_BASE_HEALTH / self.player.base_attack_damage_unarmed:.2f}")
        print(f"Daño machete (sin fuerza extra): {self.player.base_attack_damage_armed}")
        print(f"Golpes necesarios (machete): {ENEMY_BASE_HEALTH / self.player.base_attack_damage_armed:.2f}")
        print("================================")

        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGTH)
        self.tile_map = TileMap(tile_size=32, width=50, height=50)
        self.tile_map.build_map()
        # ---- Enemigos ----
        self.enemies = []
        # Enemigos se crean cuando realmente empieza la partida
        # sincronizar nivel del juego con nivel del jugador

        self.flash_timer = 0.0
        self.shake_timer = 0.0
        self.shake_strength = 0

                    # === CARGA DE SONIDOS ===
        sound_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds")

        self.snd_slash_q = pygame.mixer.Sound(os.path.join(sound_path, "Slash.mp3"))
        self.snd_slash_d = pygame.mixer.Sound(os.path.join(sound_path, "SlashD.mp3"))
        self.snd_explosion_e = pygame.mixer.Sound(os.path.join(sound_path, "Explosion.mp3"))
        self.snd_whoosh = pygame.mixer.Sound(os.path.join(sound_path, "Woosh.mp3"))

        # Ajustar volumen si deseas
        self.snd_slash_q.set_volume(0.7)
        self.snd_slash_d.set_volume(0.7)
        self.snd_explosion_e.set_volume(0.8)
        self.snd_whoosh.set_volume(0.6)

        # --- Estado del jefe ---
        self.boss_active = False      # Hay combate contra el Diablo
        self.boss_spawned = False     # Ya se creó al menos una vez




    def save_current_run_summary(self):
        """Guarda un resumen de la partida actual para mostrar en el menú."""
        self.last_run_summary = {
            "level": self.level,
            "kills": self.kills,
            "score": self.score,
            "time": int(self.run_time),   # en segundos
        }

    def format_time(self, total_seconds: int) -> str:
        m = total_seconds // 60
        s = total_seconds % 60
        return f"{m:02d}:{s:02d}"

    def reset_game(self):
        # Reiniciar jugador, vida, etc...
        self.player.x = SCREEN_WIDTH // 2
        self.player.y = SCREEN_HEIGTH // 2
        self.player.health = self.player.max_health
        self.player.is_armed = False
        self.player.is_attacking = False

        self.level = 1
        self.kills = 0
        self.score = 0
        self.run_time = 0.0      # 👈 tiempo de partida

        self.player.level = 1
        self.player.xp = 0
        self.player.xp_to_next = PLAYER_XP_BASE

        self.player.move_level = 1
        self.player.strength_level = 1
        self.player.range_level = 1
        self.player.resistance_level = 1

        self.player.bandages = 0
        self.player.special_kill_counter = 0

        self.player.recalculate_stats()
        self.level = self.player.level
        self.pending_level_up_choice = False

        self.max_enemies_on_screen = ENEMY_MAX_ON_SCREEN_BASE
        self.spawn_interval = ENEMY_INITIAL_SPAWN_INTERVAL

        # --- Reset completo de enemigos y spawns ---
        # eliminar TODOS los enemigos de la partida anterior
        self.enemies = []
        # reiniciar el temporizador de spawn
        self.spawn_timer = 0.0

        # si estás usando un registro de enemigos ya contados (por si acaso)
        if hasattr(self, "killed_enemies_registered"):
            self.killed_enemies_registered.clear()

            # --- Reset de estados especiales del jugador (muerte / daño / animaciones) ---
        if hasattr(self.player, "is_dying"):
            self.player.is_dying = False
        if hasattr(self.player, "death_animation_finished"):
            self.player.death_animation_finished = False
        if hasattr(self.player, "is_hurt"):
            self.player.is_hurt = False

        # reset básico de animación del player
        self.player.animation_frame = 0
        self.player.animation_timer = 0.0
        # lo dejamos mirando hacia abajo en idle (ajusta si usas otro nombre)
        if hasattr(self.player, "direction"):
            self.player.direction = "down"
        if hasattr(self.player, "current_animation"):
            # según cómo nombres tus animaciones de idle, ajusta esta cadena
            self.player.current_animation = "idle_down"




    def start_game(self):
        """Pasa de MENÚ a RUNNING y prepara la partida."""
        self.reset_game()
        self.state = GameState.RUNNING
        # Si quieres, puedes spawnear algunos al inicio:
        self.spawn_initial_enemies(count=5)



    def spawn_initial_enemies(self, count: int = 5):
    # """Crea algunos enemigos en posiciones aleatorias lejos del jugador."""
        import random
        from core.settings import MAP_WIDTH_PX, MAP_HEIGHT_PX, TILE_SIZE

        for _ in range(count):
            while True:
                x = random.randint(0, MAP_WIDTH_PX - TILE_SIZE)
                y = random.randint(0, MAP_HEIGHT_PX - TILE_SIZE)

                dx = x - self.player.x
                dy = y - self.player.y
                if dx * dx + dy * dy > (TILE_SIZE * 10) ** 2:
                    break

            from core.settings import (
                ENEMY_BASE_HEALTH, ENEMY_BASE_DAMAGE,
                ENEMY_HEALTH_GROWTH, ENEMY_DAMAGE_GROWTH,
            )

            # Factor según nivel actual del jugador
            level_index = max(0, self.player.level - 1)
            health = int(ENEMY_BASE_HEALTH * (ENEMY_HEALTH_GROWTH ** level_index))
            damage = ENEMY_BASE_DAMAGE * (ENEMY_DAMAGE_GROWTH ** level_index)

            enemy = Enemy(x, y, health=health, damage=damage)
            self.enemies.append(enemy) 



    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                # ESC ya no sale siempre: depende del estado
                if self.state == GameState.RUNNING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED

                    elif event.key == pygame.K_SPACE:
                        self.player.toggle_weapon()
                    
                    elif event.key == pygame.K_h:
                        self.player.use_bandage()
                    elif event.key == pygame.K_q:
                        self.use_special_frontal()
                    elif event.key == pygame.K_e:
                        self.use_special_spiral()

                elif self.state == GameState.PAUSED:
                    if self.pending_level_up_choice:
                        # Menú de subida de nivel: obligar a elegir 1–4
                        if event.key == pygame.K_1:
                            self.apply_stat_upgrade("move")
                        elif event.key == pygame.K_2:
                            self.apply_stat_upgrade("strength")
                        elif event.key == pygame.K_3:
                            self.apply_stat_upgrade("range")
                        elif event.key == pygame.K_4:
                            self.apply_stat_upgrade("resistance")
                        # Ignoramos ESC/ENTER mientras haya elección pendiente
                    else:
                        # Pausa normal
                        if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                            self.state = GameState.RUNNING
                        elif event.key == pygame.K_m:
                            self.save_current_run_summary()
                            self.state = GameState.MENU


                elif self.state == GameState.MENU:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self.start_game()
                    elif event.key == pygame.K_q:
                        self.running = False

                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_RETURN:
                        self.start_game()
                    elif event.key == pygame.K_m:
                        self.save_current_run_summary()
                        self.state = GameState.MENU
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False


    def update(self, dt: float):
        if self.state != GameState.RUNNING:
            return
        # Tiempo total de la partida
        self.run_time += dt

        self.player.update(dt)
        self.camera.update(self.player)

        for enemy in self.enemies:
            enemy.update(dt, self.player)

        self.handle_enemy_collisions()
        self.handle_player_attack_collisions()
        self.update_enemy_spawning(dt)

        # Actualizar efectos visuales de habilidades especiales
        self.update_special_effects(dt)

        # Cambiar a GAME_OVER solo cuando termine la animación de muerte
        if self.player.health <= 0 and getattr(self.player, "death_animation_finished", False):
            self.state = GameState.GAME_OVER
            # NO LLAMAR reset_game() aquí

        if self.flash_timer > 0:
            self.flash_timer -= dt

        # --- actualizar screen shake ---
        if self.shake_timer > 0:
            self.shake_timer -= dt
            if self.shake_timer < 0:
                self.shake_timer = 0




    def handle_enemy_collisions(self):
        """
        Por ahora no hacemos daño por contacto.
        El daño de los enemigos se calcula en Enemy.update() usando su campo de ataque.
        Aquí podrías manejar solo empujones/colisiones físicas si lo quieres más adelante.
        """
        return

    def handle_player_attack_collisions(self):

        atk_rect = self.player.get_attack_hitbox()
        if atk_rect is None:
            return

        # Seguridad: si por alguna razón aún no existe el set, lo creamos
        if not hasattr(self.player, "hit_enemies_this_swing"):
            self.player.hit_enemies_this_swing = set()

        killed_now = 0

        for enemy in self.enemies:
            if not enemy.alive:
                continue

            # Si este enemigo ya fue golpeado en este swing, lo ignoramos
            if enemy in self.player.hit_enemies_this_swing:
                continue

            if atk_rect.colliderect(enemy.rect):
                # Marcamos que ya fue golpeado en este ataque
                self.player.hit_enemies_this_swing.add(enemy)

                # Vida antes del golpe
                prev_health = enemy.health
                was_alive = enemy.alive

                enemy.take_damage(self.player.attack_damage)

                # Registrar la kill cuando la vida pasa de >0 a <=0
                if was_alive and prev_health > 0 and enemy.health <= 0:
                    killed_now += 1

        # Quitar de la lista SOLO a los que ya terminaron animación de muerte
        self.enemies = [e for e in self.enemies if e.alive]

        # --- Si hubo kills, actualizamos todo ---
        if killed_now > 0:
            prev_kills = self.kills
            self.kills += killed_now
            self.score += killed_now * 10

            # XP por enemigo
            total_xp = killed_now * XP_PER_KILL
            self.give_xp_to_player(total_xp)

            # Contador especial
            self.player.special_kill_counter += killed_now

            # Vendas por grupos
            prev_groups = prev_kills // KILLS_PER_BANDAGE
            new_groups = self.kills // KILLS_PER_BANDAGE
            gained = max(0, new_groups - prev_groups)

            if gained > 0:
                self.player.bandages = min(
                    self.player.bandages + gained,
                    MAX_BANDAGES
                )



    def give_xp_to_player(self, amount: int):
        from core.settings import PLAYER_XP_GROWTH, MAX_PLAYER_LEVEL

        # Si ya alcanzó el nivel máximo, no acumulamos más XP para subir
        if self.player.level >= MAX_PLAYER_LEVEL:
            return

        self.player.xp += amount

        # Mientras tengamos XP suficiente y no hayamos llegado al nivel máximo
        while (
            self.player.level < MAX_PLAYER_LEVEL
            and self.player.xp >= self.player.xp_to_next
        ):
            # Restar la XP requerida para este nivel
            self.player.xp -= self.player.xp_to_next

            # Subir nivel (esto ajusta spawn, etc.)
            self.level_up()

            # Incrementar la XP requerida para el siguiente nivel (+15%)
            self.player.xp_to_next = int(self.player.xp_to_next * PLAYER_XP_GROWTH)

            # Activar menú de mejora
            self.pending_level_up_choice = True
            self.state = GameState.PAUSED




    def update_enemy_spawning(self, dt: float):
        """Spawnea enemigos con el tiempo, limitado por max_enemies_on_screen."""
        from core.settings import MAP_WIDTH_PX, MAP_HEIGHT_PX, TILE_SIZE

        # Si estamos en combate con el jefe, NO spawneamos más orcos
        if self.boss_active:
            return
        
        # Si ya hay muchos enemigos, no spawnear más
        alive_count = sum(1 for e in self.enemies if e.alive)
        if alive_count >= self.max_enemies_on_screen:
            return

        self.spawn_timer += dt
        if self.spawn_timer < self.spawn_interval:
            return

        self.spawn_timer = 0.0

        # Buscar posición aleatoria lejos del jugador
        while True:
            x = random.randint(0, MAP_WIDTH_PX - TILE_SIZE)
            y = random.randint(0, MAP_HEIGHT_PX - TILE_SIZE)

            dx = x - self.player.x
            dy = y - self.player.y
            if dx * dx + dy * dy > (TILE_SIZE * 8) ** 2:
                break

        from core.settings import (
            ENEMY_BASE_HEALTH, ENEMY_BASE_DAMAGE,
            ENEMY_HEALTH_GROWTH, ENEMY_DAMAGE_GROWTH,
        )

        # Factor según nivel actual del jugador
        level_index = max(0, self.player.level - 1)
        health = int(ENEMY_BASE_HEALTH * (ENEMY_HEALTH_GROWTH ** level_index))
        damage = ENEMY_BASE_DAMAGE * (ENEMY_DAMAGE_GROWTH ** level_index)

        enemy = Enemy(x, y, health=health, damage=damage)
        self.enemies.append(enemy)





    def level_up(self):
        if self.player.level >= MAX_PLAYER_LEVEL:
            return

        # Subir nivel de jugador y sincronizar
        self.player.level += 1
        self.level = self.player.level

        # Si llegamos al nivel del jefe, lo spawneamos
        if self.level == 6 and not self.boss_spawned:
            self.spawn_boss_diablo()

        # Spawn más rápido (como ya tenías)
        self.spawn_interval = max(
            ENEMY_MIN_SPAWN_INTERVAL,
            self.spawn_interval - ENEMY_SPAWN_INTERVAL_STEP,
        )

        # +5 enemigos máximos en pantalla por nivel
        self.max_enemies_on_screen += ENEMIES_PER_LEVEL

        # Bonus de score por subir
        self.score += 50

    def apply_stat_upgrade(self, stat_key: str):
        from core.settings import PLAYER_STAT_MAX_LEVEL
        p = self.player

        upgraded = False  # flag para saber si se mejoró algo

        if stat_key == "move" and p.move_level < PLAYER_STAT_MAX_LEVEL:
            p.move_level += 1
            upgraded = True
        elif stat_key == "strength" and p.strength_level < PLAYER_STAT_MAX_LEVEL:
            p.strength_level += 1
            upgraded = True
        elif stat_key == "range" and p.range_level < PLAYER_STAT_MAX_LEVEL:
            p.range_level += 1
            upgraded = True
        elif stat_key == "resistance" and p.resistance_level < PLAYER_STAT_MAX_LEVEL:
            p.resistance_level += 1
            upgraded = True

        # Si NO se pudo mejorar (ya estaba en el nivel máximo), salimos sin cerrar el menú
        if not upgraded:
            return

        # Si sí se mejoró algo, recalculamos y cerramos menú
        p.recalculate_stats()
        self.pending_level_up_choice = False
        self.state = GameState.RUNNING

    def draw_level_up_menu(self):
        import pygame

        # Dibujar juego de fondo
        self.draw_game()

        # Overlay oscuro
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGTH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("arial", 32, bold=True)
        font_opt = pygame.font.SysFont("arial", 22)
        font_hint = pygame.font.SysFont("arial", 18)

        title = font_title.render("¡Subes de nivel!", True, (255, 255, 255))
        hint = font_hint.render("Elige una mejora: 1-MOV  2-Fuerza  3-Rango  4-Resistencia", True, (220, 220, 220))

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGTH // 2

        self.screen.blit(title, (cx - title.get_width() // 2, cy - 150))
        self.screen.blit(hint, (cx - hint.get_width() // 2, cy + 100))

        from core.settings import PLAYER_STAT_MAX_LEVEL

        p = self.player

        def label(stat_name, current_level):
            if current_level >= PLAYER_STAT_MAX_LEVEL:
                return f"{stat_name} (nivel: {current_level}) [MAX]"
            return f"{stat_name} (nivel: {current_level})"

        options = [
            f"1) {label('Movimiento', p.move_level)}",
            f"2) {label('Fuerza', p.strength_level)}",
            f"3) {label('Rango', p.range_level)}",
            f"4) {label('Resistencia', p.resistance_level)}",
]

        for i, text in enumerate(options):
            surf = font_opt.render(text, True, (255, 255, 255))
            self.screen.blit(surf, (cx - surf.get_width() // 2, cy - 60 + i * 30))


    def draw(self):
        self.screen.fill(COLOR_BG)

        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.RUNNING:
            self.draw_game()
        elif self.state == GameState.PAUSED:
            if self.pending_level_up_choice:
                self.draw_level_up_menu()
            else:
                self.draw_pause_menu()
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()

        pygame.display.flip()


    def draw_pause_menu(self):
        # Dibuja el juego de fondo
        self.draw_game()

        # Overlay oscuro
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGTH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("arial", 40, bold=True)
        font_small = pygame.font.SysFont("arial", 20)

        text_title = font_title.render("PAUSA", True, (255, 255, 255))

        # Resumen de la partida actual
        time_text = self.format_time(int(self.run_time))

        text_level = font_small.render(f"Nivel actual: {self.level}", True, (230, 230, 230))
        text_score = font_small.render(f"Puntuación: {self.score}", True, (230, 230, 230))
        text_kills = font_small.render(f"Enemigos derrotados: {self.kills}", True, (230, 230, 230))
        text_time = font_small.render(f"Tiempo de juego: {time_text}", True, (230, 230, 230))

        text_hint = font_small.render(
            "ENTER / ESC: Reanudar   |   M: Menú principal",
            True,
            (200, 200, 200),
        )

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGTH // 2

        self.screen.blit(text_title, (cx - text_title.get_width() // 2, cy - 120))
        self.screen.blit(text_level, (cx - text_level.get_width() // 2, cy - 40))
        self.screen.blit(text_score, (cx - text_score.get_width() // 2, cy - 10))
        self.screen.blit(text_kills, (cx - text_kills.get_width() // 2, cy + 20))
        self.screen.blit(text_time, (cx - text_time.get_width() // 2, cy + 50))
        self.screen.blit(text_hint, (cx - text_hint.get_width() // 2, cy + 100))


    def draw_game(self):

        camera_offset = self.camera.get_offset()

        # 1) Mapa
        self.tile_map.draw(self.screen, camera_offset)

        # 2) Construir lista de entidades ordenadas por profundidad (rect.bottom)
        drawables = []

        special_ready = self.player.can_use_special_frontal() or self.player.can_use_special_spiral()
        # --- Enemigos ---
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            depth_rect = enemy.rect  # rect en coordenadas del mundo
            drawables.append(("enemy", depth_rect.bottom, enemy))

        # --- Jugador ---
        # Usamos hitbox reducida si es posible para la profundidad
        if hasattr(self.player, "hitbox_width"):
            player_rect_world = pygame.Rect(
                self.player.x + self.player.hitbox_offset_x,
                self.player.y + self.player.hitbox_offset_y,
                self.player.hitbox_width,
                self.player.hitbox_height,
            )
        elif hasattr(self.player, "rect"):
            player_rect_world = self.player.rect
        else:
            player_rect_world = pygame.Rect(
                self.player.x,
                self.player.y,
                self.player.width,
                self.player.height,
            )

        drawables.append(("player", player_rect_world.bottom, self.player))

        # Ordenar de más arriba (menor bottom) a más abajo (mayor bottom)
        drawables.sort(key=lambda item: item[1])

        # 3) Pintar entidades en orden
        for kind, _, obj in drawables:
            if kind == "enemy":
                # Sprite
                obj.draw(self.screen, camera_offset)

                # Hitbox del enemigo (debug)
                if DEBUG_DRAW_HITBOXES:
                    enemy_rect = obj.rect
                    debug_rect = pygame.Rect(
                        enemy_rect.x - camera_offset[0],
                        enemy_rect.y - camera_offset[1],
                        enemy_rect.width,
                        enemy_rect.height,
                    )
                    pygame.draw.rect(self.screen, (0, 255, 0), debug_rect, 1)

                # Campo de ataque del enemigo (debug)
                if DEBUG_DRAW_ATTACK_FIELDS and hasattr(obj, "get_attack_hitbox"):
                    atk_rect = obj.get_attack_hitbox()
                    if atk_rect is not None:
                        debug_atk = pygame.Rect(
                            atk_rect.x - camera_offset[0],
                            atk_rect.y - camera_offset[1],
                            atk_rect.width,
                            atk_rect.height,
                        )
                        # Magenta
                        pygame.draw.rect(self.screen, (255, 0, 255), debug_atk, 2)

            elif kind == "player":
                # Posición del jugador en pantalla
                player_pos = (
                    obj.x - camera_offset[0],
                    obj.y - camera_offset[1],
                )

                # --- Hurt flash (parpadeo blanco cuando recibe daño) ---
                image_to_draw = obj.image
                if getattr(obj, "is_hurt", False):
                    t = pygame.time.get_ticks() // 40
                    if t % 2 == 0:
                        image_to_draw = obj.image.copy()
                        image_to_draw.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)

                # Dibujar sprite del jugador
                self.screen.blit(image_to_draw, player_pos)

                # --- Aura de especial listo ---
                if special_ready:
                    # centro cerca de los pies del jugador
                    center_x = player_pos[0] + obj.width // 2
                    center_y = player_pos[1] + obj.height

                    # radio del círculo
                    radius = int(obj.width * 0.7)
                    aura_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

                    # pequeño pulso con sin() para que respire
                    t = pygame.time.get_ticks() / 1000.0
                    alpha = 120 + int(80 * math.sin(t * 4))  # oscila entre ~40 y ~200

                    pygame.draw.circle(
                        aura_surface,
                        (255, 255, 150, alpha),
                        (radius, radius),
                        radius,
                        3
                    )

                    # dibujamos la aura centrada en los pies
                    self.screen.blit(
                        aura_surface,
                        (center_x - radius, center_y - radius)
                    )


                # Hitbox del jugador (debug)
                if DEBUG_DRAW_HITBOXES:
                    pygame.draw.rect(
                        self.screen,
                        (255, 0, 0),
                        pygame.Rect(
                            player_pos[0] + obj.hitbox_offset_x,
                            player_pos[1] + obj.hitbox_offset_y,
                            obj.hitbox_width,
                            obj.hitbox_height,
                        ),
                        1,
                    )

                # Campo de ataque del jugador (debug)
                if DEBUG_DRAW_ATTACK_FIELDS and hasattr(obj, "get_attack_hitbox"):
                    atk_rect = obj.get_attack_hitbox()
                    if atk_rect is not None:
                        debug_atk = pygame.Rect(
                            atk_rect.x - camera_offset[0],
                            atk_rect.y - camera_offset[1],
                            atk_rect.width,
                            atk_rect.height,
                        )
                        # Amarillo
                        pygame.draw.rect(self.screen, (255, 255, 0), debug_atk, 2)
                
                # 🔥 Swing del ataque del jugador (si está atacando)
                swing_data = obj.get_attack_swing_sprite() if hasattr(obj, "get_attack_swing_sprite") else None
                if swing_data is not None:
                    swing_img, swing_x, swing_y = swing_data
                    swing_pos = (
                        swing_x - camera_offset[0],
                        swing_y - camera_offset[1],
                    )
                    self.screen.blit(swing_img, swing_pos)

        # 4) UI siempre encima
        self.draw_ui()

        # 3.5) Efectos visuales de habilidades especiales por encima de entidades
        self.draw_special_effects(camera_offset)

        if self.flash_timer > 0:
            alpha = int(255 * (self.flash_timer / 0.15))
            flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGTH))
            flash_surface.set_alpha(alpha)
            flash_surface.fill((255, 255, 255))
            self.screen.blit(flash_surface, (0, 0))

            # offset base de cámara (sin temblor)
            camera_offset = self.camera.get_offset()

            shake_x = 0
            shake_y = 0
            if self.shake_timer > 0:
                shake_x = random.randint(-self.shake_strength, self.shake_strength)
                shake_y = random.randint(-self.shake_strength, self.shake_strength)

            # offset final con temblor
            camera_offset = (
                camera_offset[0] + shake_x,
                camera_offset[1] + shake_y,
            )

            # 1) Mapa
            self.tile_map.draw(self.screen, camera_offset)




    def draw_ui(self):

        bar_width = 200
        bar_height = 20
        margin = 10

        # --- Barra de vida ---
        pygame.draw.rect(
            self.screen,
            (60, 60, 60),
            pygame.Rect(margin, margin, bar_width, bar_height),
            border_radius=4
        )

        ratio = self.player.health / self.player.max_health if self.player.max_health > 0 else 0
        pygame.draw.rect(
            self.screen,
            (0, 200, 60),
            pygame.Rect(margin, margin, int(bar_width * ratio), bar_height),
            border_radius=4
        )

        # Marco
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            pygame.Rect(margin, margin, bar_width, bar_height),
            2,
            border_radius=4
        )

        # --- Texto: LVL y Score ---
        font = pygame.font.SysFont("arial", 18)

        txt_level = font.render(f"Nivel: {self.level}", True, (230, 230, 230))
        txt_score = font.render(f"Score: {self.score}", True, (230, 230, 230))

        self.screen.blit(txt_level, (margin, margin + bar_height + 8))
        self.screen.blit(txt_score, (margin, margin + bar_height + 8 + txt_level.get_height()))

        txt_xp = font.render(
            f"XP: {int(self.player.xp)}/{self.player.xp_to_next}",
            True,
            (180, 200, 255)
        )
        self.screen.blit(
            txt_xp,
            (margin, margin + bar_height + 8 + txt_level.get_height() + txt_score.get_height())
        )

        # Vendas
        txt_bandages = font.render(f"Vendas (H): {self.player.bandages}", True, (180, 220, 255))
        self.screen.blit(
            txt_bandages,
            (margin, margin + bar_height + 8 + txt_level.get_height() + txt_score.get_height() + txt_xp.get_height())
        )

        # Contador especial
        from core.settings import SPECIAL_FRONTAL_KILLS, SPECIAL_SPIRAL_KILLS

        special = self.player.special_kill_counter
        ready = self.player.can_use_special_frontal() or self.player.can_use_special_spiral()

        color = (255, 220, 120) if ready else (200, 200, 200)
        txt_special = font.render(
            f"Especial: {special}/{SPECIAL_FRONTAL_KILLS} (Q) | {special}/{SPECIAL_SPIRAL_KILLS} (E)",
            True,
            color
        )
        self.screen.blit(
            txt_special,
            (margin, SCREEN_HEIGTH - txt_special.get_height() - margin)
        )

        # Indicador extra cuando el especial está listo
        if ready:
            # pequeño parpadeo usando el tiempo global
            t = pygame.time.get_ticks() // 150  # cambia cada 150 ms
            if t % 2 == 0:
                ready_text = "¡ESPECIAL LISTA!"
                txt_ready = font.render(ready_text, True, (255, 255, 150))
                # lo dibujamos justo encima de la línea de especial
                self.screen.blit(
                    txt_ready,
                    (margin, SCREEN_HEIGTH - txt_special.get_height() - margin - txt_ready.get_height() - 4)
                )



    def draw_menu(self):
        font = pygame.font.SysFont("arial", 32, bold=True)
        hint_font = pygame.font.SysFont("arial", 20)

        title_surf = font.render("The Epic Feat of Octavio Mesa", True, (240, 240, 240))
        hint_surf = hint_font.render("ENTER / ESPACIO: Nueva partida   |   Q: Salir", True, (200, 200, 200))

        self.screen.blit(
            title_surf,
            (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, SCREEN_HEIGTH // 3)
        )
        self.screen.blit(
            hint_surf,
            (SCREEN_WIDTH // 2 - hint_surf.get_width() // 2, SCREEN_HEIGTH // 2)
        )

        # Resumen de la última partida (si existe)
        if self.last_run_summary is not None:
            small = pygame.font.SysFont("arial", 18)
            t = self.format_time(self.last_run_summary["time"])
            txt = small.render(
                f"Última partida — Nivel {self.last_run_summary['level']} | "
                f"Score {self.last_run_summary['score']} | "
                f"Kills {self.last_run_summary['kills']} | "
                f"Tiempo {t}",
                True,
                (210, 210, 210),
            )
            self.screen.blit(
                txt,
                (SCREEN_WIDTH // 2 - txt.get_width() // 2, SCREEN_HEIGTH - 60)
            )


    def draw_game_over(self):
        # Fondo de la última escena de juego
        self.draw_game()

        # Overlay oscuro
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGTH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        font_big = pygame.font.SysFont("arial", 40, bold=True)
        font_small = pygame.font.SysFont("arial", 20)

        text_go = font_big.render("GAME OVER", True, (255, 80, 80))
        text_score = font_small.render(f"Puntuación: {self.score}", True, (230, 230, 230))
        text_kills = font_small.render(f"Enemigos derrotados: {self.kills}", True, (230, 230, 230))
        text_level = font_small.render(f"Nivel alcanzado: {self.level}", True, (230, 230, 230))
        text_hint = font_small.render("ENTER: Reiniciar  |  M: Menú  |  ESC: Salir", True, (200, 200, 200))

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGTH // 2

        self.screen.blit(text_go, (cx - text_go.get_width() // 2, cy - 100))
        self.screen.blit(text_score, (cx - text_score.get_width() // 2, cy - 40))
        self.screen.blit(text_kills, (cx - text_kills.get_width() // 2, cy - 10))
        self.screen.blit(text_level, (cx - text_level.get_width() // 2, cy + 20))
        self.screen.blit(text_hint, (cx - text_hint.get_width() // 2, cy + 70))

    def _build_base_attack_rect(self):
        """Rect básico frente al jugador si no está atacando justo ahora."""
        import pygame

        base_rect = pygame.Rect(
            self.player.x + self.player.hitbox_offset_x,
            self.player.y + self.player.hitbox_offset_y,
            self.player.hitbox_width,
            self.player.hitbox_height,
        )

        if self.player.facing == 'up':
            return pygame.Rect(
                base_rect.centerx - base_rect.width // 2,
                base_rect.top - base_rect.height,
                base_rect.width,
                base_rect.height
            )
        elif self.player.facing == 'down':
            return pygame.Rect(
                base_rect.centerx - base_rect.width // 2,
                base_rect.bottom,
                base_rect.width,
                base_rect.height
            )
        elif self.player.facing == 'left':
            return pygame.Rect(
                base_rect.left - base_rect.width,
                base_rect.centery - base_rect.height // 2,
                base_rect.width,
                base_rect.height
            )
        else:  # right
            return pygame.Rect(
                base_rect.right,
                base_rect.centery - base_rect.height // 2,
                base_rect.width,
                base_rect.height
            )

    
    def use_special_frontal(self):
            p = self.player

        # Comprobar si puede usarla (ya tienes helpers en Player normalmente)
            if hasattr(p, "can_use_special_frontal"):
                if not p.can_use_special_frontal():
                            return
            else:
                # fallback: comprobamos el contador directamente
                if p.special_kill_counter < SPECIAL_FRONTAL_KILLS:
                    self.snd_slash_q.play()
                    return

            # Consumir kills
            p.special_kill_counter -= SPECIAL_FRONTAL_KILLS
            if p.special_kill_counter < 0:
                p.special_kill_counter = 0

            # --- Área de daño frontal ---
            base_rect = self._build_base_attack_rect()  # ya existe en Game

            # Vamos a hacer un rect más largo hacia la dirección del jugador
            rect = base_rect.copy()
            expand_factor = 3  # alargas 3x el alcance

            if p.facing == "up":
                rect.height *= expand_factor
                rect.y = base_rect.bottom - rect.height
            elif p.facing == "down":
                rect.height *= expand_factor
            elif p.facing == "left":
                rect.width *= expand_factor
                rect.x = base_rect.right - rect.width
            elif p.facing == "right":
                rect.width *= expand_factor

            # Aplicar daño a todos los enemigos que colisionen
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if rect.colliderect(enemy.rect):
                    enemy.take_damage(SPECIAL_FRONTAL_DAMAGE)

            # Crear efecto visual
            effect = {
                "type": "frontal",
                "time": 0.0,
                "duration": 0.35,   # duración visual ~0.35s
                "direction": p.facing,
                "center": (p.x + p.width // 2, p.y + p.height // 2),
            }
            self.special_effects.append(effect)

            if hasattr(self, "snd_slash_q"):
                self.snd_slash_q.play()
                self.flash_timer = 0.10   # dura 0.10s

            self.shake_timer = 0.20
            self.shake_strength = 5

    def use_special_spiral(self):
            p = self.player

            if hasattr(p, "can_use_special_spiral"):
                if not p.can_use_special_spiral():
                    return
            else:
                if p.special_kill_counter < SPECIAL_SPIRAL_KILLS:
                    return

            # Consumir kills
            p.special_kill_counter -= SPECIAL_SPIRAL_KILLS
            if p.special_kill_counter < 0:
                p.special_kill_counter = 0

            # Daño en área
            cx = p.x + p.width // 2.5
            cy = p.y + p.height // 2.5
            radius_sq = SPECIAL_RADIUS * SPECIAL_RADIUS

            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                ex, ey = enemy.rect.center
                dx = ex - cx
                dy = ey - cy
                if dx * dx + dy * dy <= radius_sq:
                    enemy.take_damage(SPECIAL_SPIRAL_DAMAGE)

            # Efecto visual tipo explosión (usaremos varias direcciones)
            effect = {
                "type": "spiral",
                "time": 0.0,
                "duration": 0.45,  # un poco más larga que Q
                "center": (cx, cy),
                "shockwave": True,
            }
            self.special_effects.append(effect)

                # 5) Sonido + shake SOLO si se lanzó el ataque
            if hasattr(self, "snd_explosion_e"):
                self.snd_explosion_e.play()
            if hasattr(self, "snd_whoosh"):
                self.snd_whoosh.play()
                self.flash_timer = 0.15

            self.shake_timer = 0.3
            self.shake_strength = 12


    def update_special_effects(self, dt: float):
        """Actualiza el tiempo de vida de los efectos especiales."""
        alive_effects = []
        for eff in self.special_effects:
            eff["time"] += dt
            if eff["time"] < eff["duration"]:
                alive_effects.append(eff)
        self.special_effects = alive_effects


    def draw_special_effects(self, camera_offset):

        # Dirección lógica del ataque -> fila visual del sprite
        dir_visual_map = {
            "up": "down",
            "down": "up",
            "left": "left",
            "right": "right",
        }

        for eff in self.special_effects:
            t = eff["time"]
            duration = eff["duration"]
            progress = max(0.0, min(1.0, t / duration))

            cx, cy = eff["center"]
            screen_x = cx - camera_offset[0]
            screen_y = cy - camera_offset[1]

            # Animación frames
            p = self.player
            direction = eff.get("direction", "down")

            # usamos la fila visual correcta según el mapa
            visual_dir = dir_visual_map.get(direction, direction)
            frames = p.swing_frames.get(visual_dir, [])

            if eff.get("shockwave", False):
                radius = int(40 + 120 * progress)
                alpha = int(200 * (1 - progress))
                sw = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(sw, (255,255,255, alpha), (radius, radius), radius, 4)
                self.screen.blit(sw, (screen_x - radius, screen_y - radius))


            if not frames:
                continue

            frame_index = int(progress * (len(frames)-1))
            base_frame = frames[frame_index]

            # ==========================
            # ATAQUE FRONTAL  (Q)
            # ==========================
            if eff["type"] == "frontal":

                scale = 1.0 + 1.5 * progress
                img = pygame.transform.rotozoom(base_frame, 0, scale)
                rect = img.get_rect(center=(screen_x, screen_y))

                # desplazamiento hacia adelante
                offset = 90 * progress
                if direction == "up":
                    rect.centery -= offset
                elif direction == "down":
                    rect.centery += offset
                elif direction == "left":
                    rect.centerx -= offset
                elif direction == "right":
                    rect.centerx += offset

                self.screen.blit(img, rect.topleft)

            # ==========================
            # ATAQUE ESPIRAL (E)
            # ==========================
            elif eff["type"] == "spiral":

                frame_index = int(progress * (len(self.player.swing_frames["up"]) - 1))

                for logical_dir in ["up", "down", "left", "right"]:
                    # fila visual que debemos usar en el sprite
                    visual_dir = dir_visual_map.get(logical_dir, logical_dir)
                    frames_dir = self.player.swing_frames.get(visual_dir, [])
                    if not frames_dir:
                        continue

                    base_frame_dir = frames_dir[frame_index]

                    scale = 1.0 + 1.8 * progress
                    dist = 110 * progress

                    angle_map = {
                        "up": 270,
                        "down": 90,
                        "left": 180,
                        "right": 0,
                    }
                    ang = math.radians(angle_map[logical_dir])

                    ex = screen_x + math.cos(ang) * dist
                    ey = screen_y + math.sin(ang) * dist

                    img = pygame.transform.rotozoom(base_frame_dir, 0, scale)
                    rect = img.get_rect(center=(ex, ey))
                    self.screen.blit(img, rect.topleft)

    def start_boss_music(self):
        base_path = os.path.dirname(__file__)
        music_path = os.path.join(base_path, "..", "assets", "Sounds", "LaPeleaConelDiablo.wav")

        try:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(0.8)
            pygame.mixer.music.play(-1)  # loop infinito
        except pygame.error as e:
            print("Error cargando música del jefe:", e)

    def spawn_boss_diablo(self):
        """Invoca al jefe Diablo y prepara el combate."""
        if self.boss_spawned:
            return

        self.boss_spawned = True
        self.boss_active = True

        # Limpiar enemigos normales
        self.enemies.clear()

        # Posicionar al jefe cerca del centro del mapa
        boss_x = self.player.x + 150
        boss_y = self.player.y - 100
        boss = BossDiablo(boss_x, boss_y)
        self.enemies.append(boss)

        # Música del jefe
        self.start_boss_music()



    def run(self):
        while self.running:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
