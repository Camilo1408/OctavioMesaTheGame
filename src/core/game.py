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
    ENEMY_SPAWN_INTERVAL_STEP, ENEMY_MAX_ON_SCREEN_BASE, PLAYER_STAT_MAX_LEVEL, ENEMIES_PER_LEVEL, MAX_PLAYER_LEVEL
)


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

        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGTH)
        self.tile_map = TileMap(tile_size=32, width=50, height=50)
        self.tile_map.build_map()
        # ---- Enemigos ----
        self.enemies = []
        # Enemigos se crean cuando realmente empieza la partida
  # sincronizar nivel del juego con nivel del jugador


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

                # Resetear progresión del jugador
        from core.settings import PLAYER_XP_BASE

        self.player.level = 1
        self.player.xp = 0
        self.player.xp_to_next = PLAYER_XP_BASE

        self.player.move_level = 1
        self.player.strength_level = 1
        self.player.range_level = 1
        self.player.resistance_level = 1

        self.player.recalculate_stats()
        self.level = self.player.level
        self.pending_level_up_choice = False

        self.max_enemies_on_screen = ENEMY_MAX_ON_SCREEN_BASE
        self.spawn_interval = ENEMY_INITIAL_SPAWN_INTERVAL


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

        if self.player.health <= 0:
            self.state = GameState.GAME_OVER      # solo cambio de estado
            # NO LLAMAR reset_game() aquí


    def handle_enemy_collisions(self):
        import pygame
        player_rect = pygame.Rect(
            self.player.x + self.player.hitbox_offset_x,
            self.player.y + self.player.hitbox_offset_y,
            self.player.hitbox_width,
            self.player.hitbox_height,
        )

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if player_rect.colliderect(enemy.rect):
                # daño por contacto muy simple
                self.player.take_damage(enemy.damage * (1 / FPS))

    def handle_player_attack_collisions(self):
        atk_rect = self.player.get_attack_hitbox()
        if atk_rect is None:
            return

        killed_now = 0

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if atk_rect.colliderect(enemy.rect):
                enemy.take_damage(self.player.attack_damage)
                if not enemy.alive:
                    killed_now += 1

        # Quitar los muertos de la lista
        self.enemies = [e for e in self.enemies if e.alive]

        # Actualizar estadísticas
        from core.settings import XP_PER_KILL

        if killed_now > 0:
            self.kills += killed_now
            self.score += killed_now * 10

            total_xp = killed_now * XP_PER_KILL
            self.give_xp_to_player(total_xp)

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
        import random

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

        # Mapa
        self.tile_map.draw(self.screen, camera_offset)

        # Enemigos
        for enemy in self.enemies:
            enemy.draw(self.screen, camera_offset)

        # Jugador
        player_pos = (
            self.player.x - camera_offset[0],
            self.player.y - camera_offset[1]
        )
        self.screen.blit(self.player.image, player_pos)

        # Hitbox debug
        pygame.draw.rect(
            self.screen,
            (255, 0, 0),
            pygame.Rect(
                player_pos[0] + self.player.hitbox_offset_x,
                player_pos[1] + self.player.hitbox_offset_y,
                self.player.hitbox_width,
                self.player.hitbox_height
            ),
            2
        )

        # UI
        self.draw_ui()

    def draw_ui(self):
        import pygame

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





    def run(self):
        while self.running:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
