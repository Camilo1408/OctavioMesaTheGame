SCREEN_WIDTH = 800
SCREEN_HEIGTH = 600
FPS = 60

WINDOW_TITLE = "The Epic Feat Of Octavio Mesa"

COLOR_BG = (10,10,15)

TILE_SIZE = 32
MAP_WIDTH_TILES = 50
MAP_HEIGHT_TILES = 50

MAP_WIDTH_PX = TILE_SIZE * MAP_WIDTH_TILES
MAP_HEIGHT_PX = TILE_SIZE * MAP_HEIGHT_TILES

PLAYER_MAX_HEALTH = 100
ENEMY_BASE_HEALTH = 30

# --- Gameplay ---
ENEMY_INITIAL_SPAWN_INTERVAL = 2.5  # segundos entre spawns al principio
ENEMY_MIN_SPAWN_INTERVAL = 0.8      # mínimo intervalo al aumentar dificultad
ENEMY_SPAWN_INTERVAL_STEP = 0.15    # cuánto se reduce el intervalo por nivel

ENEMY_MAX_ON_SCREEN_BASE = 6        # enemigos máx. al inicio
ENEMY_MAX_ON_SCREEN_STEP = 2        # cuántos se suman por nivel

KILLS_PER_LEVEL = 8                 # cada cuántos kills subes de nivel
