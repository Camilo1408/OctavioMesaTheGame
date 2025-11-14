import pygame
import sys
from entities.player import Player
from core.camera import Camera
from core.map import TileMap
from entities.enemy import Enemy
from core.settings import SCREEN_HEIGTH, SCREEN_WIDTH, FPS,WINDOW_TITLE, COLOR_BG

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGTH))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Create game objects
        # Configure player to use 8 frames per direction and 1-based row indexing
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGTH // 2,
                            frames_per_direction=8,
                            unarmed_row=39,
                            armed_row=9,
                            row_index_base=1)
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGTH)
        self.tile_map = TileMap(tile_size=32, width=50, height=50)
        self.tile_map.build_map()
        # ---- Enemigos ----
        self.enemies = []
        self.spawn_initial_enemies()

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

            self.enemies.append(Enemy(x, y))



    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Toggle weapon once per key press
                    self.player.toggle_weapon()
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self, dt: float):
        self.player.update(dt)
        self.camera.update(self.player)

        # Actualizar enemigos
        for enemy in self.enemies:
            enemy.update(dt, self.player)

        # Colisión: enemigos dañan al jugador si lo tocan
        self.handle_enemy_collisions()

        # Colisión: ataque del jugador golpea enemigos
        self.handle_player_attack_collisions()


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
                self.player.take_damage(0.3)  # daño por frame, se escala con FPS

    def handle_player_attack_collisions(self):
        atk_rect = self.player.get_attack_hitbox()
        if atk_rect is None:
            return

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if atk_rect.colliderect(enemy.rect):
                enemy.take_damage(self.player.attack_damage)

        # eliminar muertos
        self.enemies = [e for e in self.enemies if e.alive]




    def draw(self):
        self.screen.fill((0, 0, 0))

        camera_offset = self.camera.get_offset()

        # 🗺️ Dibuja el mapa procedural
        self.tile_map.draw(self.screen, camera_offset)
        
        # 🧟 Dibuja enemigos
        for enemy in self.enemies:
            enemy.draw(self.screen, camera_offset)

        # 🧍 Dibuja al jugador
        player_pos = (
            self.player.x - camera_offset[0],
            self.player.y - camera_offset[1]
        )
        self.screen.blit(self.player.image, player_pos)

        # 🟥 DEBUG: dibujar hitbox reducida
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


        self.draw_ui()
        pygame.display.flip()

    def draw_ui(self):
        # Barra de vida del jugador
        import pygame

        bar_width = 200
        bar_height = 20
        margin = 10

        # fondo
        pygame.draw.rect(
            self.screen,
            (60, 60, 60),
            pygame.Rect(margin, margin, bar_width, bar_height),
            border_radius=4
        )

        # vida actual
        ratio = self.player.health / self.player.max_health if self.player.max_health > 0 else 0
        pygame.draw.rect(
            self.screen,
            (0, 200, 60),
            pygame.Rect(margin, margin, int(bar_width * ratio), bar_height),
            border_radius=4
        )


    def run(self):
        while self.running:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
