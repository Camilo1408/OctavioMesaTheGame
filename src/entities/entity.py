class Entity:
    def __init__(self, x: float, y: float, width: int, height: int, speed: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.alive = True

    @property
    def rect(self):
        """Rectángulo de colisión base (sin hitbox especial)."""
        from pygame import Rect
        return Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self, dt: float):
        """Sobrescribir en subclases."""
        pass

    def draw(self, screen, camera_offset):
        """Sobrescribir en subclases."""
        pass