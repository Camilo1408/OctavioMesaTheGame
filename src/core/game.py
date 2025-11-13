import pygame
import sys
from entities.player import Player
from core.camera import Camera
from core.map import TileMap
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

    def update(self):
        self.player.update()
        self.camera.update(self.player)

    def draw(self):
        self.screen.fill((0, 0, 0))

        camera_offset = self.camera.get_offset()

        # 🗺️ Dibuja el mapa procedural
        self.tile_map.draw(self.screen, camera_offset)

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



        pygame.display.flip()


    def run(self):
        while self.running:
            dt_ms = self.clock.tick(60)
            dt = dt_ms / 1000.0
            self.handle_events()
            # Pass dt to update for animation timing
            self.player.update(dt)
            self.camera.update(self.player)
            self.draw()

        pygame.quit()
        sys.exit()
