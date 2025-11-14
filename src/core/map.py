import os
import pygame
import random
from perlin_noise import PerlinNoise
from core.settings import TILE_SIZE, MAP_WIDTH_TILES, MAP_HEIGHT_TILES



class TileMap:
    def __init__(self, tile_size=TILE_SIZE, width=MAP_WIDTH_TILES, height=MAP_HEIGHT_TILES):
        self.tile_size = tile_size
        self.width = width
        self.height = height
        self.tiles = []
        self.biome_map = []
        self.surfaces = {}
        self.map_surface = None

        # Generadores de ruido
        self.noise_biome = PerlinNoise(octaves=2, seed=random.randint(0, 5000))
        self.noise_detail = PerlinNoise(octaves=4, seed=random.randint(0, 20000))

    # ---------------------------------------------------------------------
    # 🔹 Cargar sprites y ajustar tamaños
    # ---------------------------------------------------------------------
    def load_images(self):
        base_path = os.path.join("..","assets", "sprites")

        def load_folder(folder_path, max_size=None):
            images = []
            for file in os.listdir(folder_path):
                if file.endswith(".png"):
                    path = os.path.join(folder_path, file)
                    image = pygame.image.load(path).convert_alpha()
                    if max_size:
                        w, h = image.get_size()
                        if w > max_size[0] or h > max_size[1]:
                            scale_factor = min(max_size[0] / w, max_size[1] / h)
                            new_size = (int(w * scale_factor), int(h * scale_factor))
                            image = pygame.transform.smoothscale(image, new_size)
                    images.append((file, image))
            return images

        self.surfaces["floor"] = load_folder(os.path.join(base_path, "Nature Floor"))
        self.surfaces["particles"] = load_folder(os.path.join(base_path, "Objects", "Grass Particles"))
        self.surfaces["shadows"] = load_folder(os.path.join(base_path, "Objects", "Shadow Grass"), max_size=(32, 32))
        self.surfaces["stones"] = load_folder(os.path.join(base_path, "Objects", "Stones"))

    # ---------------------------------------------------------------------
    # 🔹 Generar mapa procedural con biomas balanceados
    # ---------------------------------------------------------------------
    def generate_noise_map(self):
        """Usa un mapa de ruido y mapeo de percentiles para equilibrar biomas."""
        raw_values = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                v = self.noise_biome([x / 25, y / 25])
                v += 0.3 * self.noise_detail([x / 10, y / 10])
                row.append(v)
                raw_values.append(v)
            self.biome_map.append(row)

        # Balancear proporciones (campo, rocoso, húmedo ≈ 1/3 cada uno)
        sorted_vals = sorted(raw_values)
        n = len(sorted_vals)
        th1 = sorted_vals[n // 3]
        th2 = sorted_vals[2 * n // 3]
        self.thresholds = (th1, th2)

    def get_biome(self, v):
        """Asigna bioma en proporciones similares."""
        th1, th2 = self.thresholds
        if v < th1:
            return "rocky"
        elif v < th2:
            return "field"
        else:
            return "wet"

    # ---------------------------------------------------------------------
    # 🔹 Aplicar paleta de color según bioma
    # ---------------------------------------------------------------------
    def tint_surface(self, surface, brightness_factor=1.0):
        """Ajusta el brillo general del Surface (sin cambiar transparencia)."""
        if brightness_factor == 1.0:
            return surface

        tinted = surface.copy()
        w, h = tinted.get_size()
        arr = pygame.surfarray.pixels3d(tinted)
        arr[:] = (arr * brightness_factor).clip(0, 255)
        del arr  # liberar bloqueo de surfarray
        return tinted

    def apply_biome_color(self, image, biome):
        """Retorna versión adaptada por bioma (solo el húmedo se oscurece)."""
        if biome == "wet":
            # oscurecer ligeramente, sin cambiar tono (~15% más oscuro)
            return self.tint_surface(image, 0.85)
        else:
            # campo y rocoso usan los sprites originales
            return image


    # ---------------------------------------------------------------------
    # 🔹 Construir mapa final
    # ---------------------------------------------------------------------
    def build_map(self):
        self.load_images()
        self.generate_noise_map()

        self.map_surface = pygame.Surface(
            (self.width * self.tile_size, self.height * self.tile_size), pygame.SRCALPHA
        )

        for y in range(self.height):
            for x in range(self.width):
                biome = self.get_biome(self.biome_map[y][x])
                world_x = x * self.tile_size
                world_y = y * self.tile_size

                # Detectar vecinos (para bordes)
                neighbors = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            neighbors.append(self.get_biome(self.biome_map[ny][nx]))

                # Seleccionar textura base coherente con bioma
                if biome == "rocky":
                    if any(nb != "rocky" for nb in neighbors):
                        candidates = [img for name, img in self.surfaces["floor"] if "rock.grass" in name or "grass.rock" in name]
                    else:
                        candidates = [img for name, img in self.surfaces["floor"] if "rock" in name and "grass" not in name]
                elif biome == "field":
                    candidates = [img for name, img in self.surfaces["floor"] if "grass" in name and "rock" not in name]
                else:  # wet
                    candidates = [img for name, img in self.surfaces["floor"] if "grass" in name and "rock" not in name]

                if not candidates:
                    candidates = [img for _, img in self.surfaces["floor"]]

                base_img = random.choice(candidates)
                base_img = self.apply_biome_color(base_img, biome)
                self.map_surface.blit(base_img, (world_x, world_y))

                # --- 🌿 Decoraciones según bioma ---
                r = random.random()

                if biome == "field":
                    # Mayor densidad de pasto y partículas
                    if r < 0.25:
                        deco = random.choice([img for _, img in self.surfaces["particles"]])
                        self.map_surface.blit(deco, (world_x, world_y))
                    # posibilidad de doble capa de hierba (más densa visualmente)
                    if random.random() < 0.1:
                        deco2 = random.choice([img for _, img in self.surfaces["particles"]])
                        offset_x = random.randint(-8, 8)
                        offset_y = random.randint(-4, 4)
                        self.map_surface.blit(deco2, (world_x + offset_x, world_y + offset_y))

                elif biome == "rocky":
                    # rocas y piedras dispersas
                    if r < 0.12:
                        deco = random.choice([img for _, img in self.surfaces["stones"]])
                        self.map_surface.blit(deco, (world_x, world_y))

                elif biome == "wet":
                    # Más vegetación húmeda + sombras
                    if r < 0.20:
                        deco = random.choice([img for _, img in self.surfaces["particles"]])
                        self.map_surface.blit(deco, (world_x, world_y))
                    if random.random() < 0.12:
                        shadow = random.choice([img for _, img in self.surfaces["shadows"]])
                        rect = shadow.get_rect(center=(world_x + 16, world_y + 16))
                        self.map_surface.blit(shadow, rect.topleft)


    # ---------------------------------------------------------------------
    # 🔹 Dibujar mapa en pantalla
    # ---------------------------------------------------------------------
    def draw(self, screen, camera_offset):
        if not self.map_surface:
            return
        screen.blit(self.map_surface, (-camera_offset[0], -camera_offset[1]))
