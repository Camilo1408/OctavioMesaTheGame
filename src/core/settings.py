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

ENEMY_MAX_ON_SCREEN_BASE = 6     # como ya tenías
ENEMIES_PER_LEVEL = 5            # +5 enemigos máx. por nivel

ENEMY_HEALTH_GROWTH = 1.10   # +10% vida por nivel
ENEMY_DAMAGE_GROWTH = 1.10   # +10% daño por nivel

ENEMY_BASE_DAMAGE = 6.0  # daño base por “golpe/contacto”

# --- Armas jugador ---
FIST_BASE_DAMAGE = 15
MACHETE_BASE_DAMAGE = 30

FIST_BASE_RANGE = 1.0    # multiplicador de rango
MACHETE_BASE_RANGE = 1.5

# --- Progresión del jugador ---
XP_PER_KILL = 25              # XP que da cada enemigo
PLAYER_XP_BASE = 75           # XP necesaria de nivel 1 -> 2
PLAYER_XP_GROWTH = 1.15       # +15% XP necesaria por nivel
MAX_PLAYER_LEVEL = 13         # nivel global máximo (1 + 12 mejoras)

PLAYER_STAT_MAX_LEVEL = 4

# --- Curación e inventario ---
BANDAGE_HEAL_AMOUNT = 25      # HP curados por venda
MAX_BANDAGES = 5              # tope de vendas que puedes acumular
KILLS_PER_BANDAGE = 6         # cada cuántas kills ganas 1 venda

# --- Habilidades especiales ---
SPECIAL_FRONTAL_KILLS = 12    # kills necesarias para Q
SPECIAL_SPIRAL_KILLS = 20     # kills necesarias para E

SPECIAL_FRONTAL_DAMAGE = 999  # daño muy alto en línea (ajustable)
SPECIAL_SPIRAL_DAMAGE = 999   # daño muy alto en área (ajustable)
SPECIAL_RADIUS = 200          # radio del ataque en área (E)
