from core.settings import MAP_WIDTH_PX, MAP_HEIGHT_PX


class Camera:
    def __init__(self, screen_width, screen_height):
        self.x = 0
        self.y = 0
        self.screen_width = screen_width
        self.screen_height = screen_height
        
    def update(self, target):
        """Centrar la cámara suavemente en el objetivo (jugador)."""
        self.x = int(target.x + target.width / 2 - self.screen_width / 2)
        self.y = int(target.y + target.height / 2 - self.screen_height / 2)

        # Limitar movimiento de cámara para no mostrar más allá del mapa
        map_width = MAP_WIDTH_PX
        map_height = MAP_HEIGHT_PX

        self.x = max(0, min(self.x, map_width - self.screen_width))
        self.y = max(0, min(self.y, map_height - self.screen_height))

    def get_offset(self):
        return (self.x, self.y)