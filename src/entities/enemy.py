import pygame
import random
from entities.entity import Entity
from core.settings import TILE_SIZE, ENEMY_BASE_HEALTH, ENEMY_BASE_DAMAGE

class Enemy(Entity):
    def __init__(self, x, y, health=None, damage=None):
        super().__init__(x, y, TILE_SIZE, TILE_SIZE, speed=2.0)
        self.max_health = health if health is not None else ENEMY_BASE_HEALTH
        self.health = self.max_health

        self.damage = damage if damage is not None else ENEMY_BASE_DAMAGE

        # Por ahora: un simple círculo rojo como sprite
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (200, 40, 40), (self.width // 2, self.height // 2), self.width // 2)

        # Pequeño jitter para que no se muevan totalmente igual
        self.speed_variation = random.uniform(0.8, 1.2)

    def take_damage(self, amount: float):
        self.health -= amount
        if self.health <= 0:
            self.alive = False

    def update(self, dt: float, player):
        """IA muy básica: seguir al jugador en línea recta."""
        if not self.alive:
            return

        dx = player.x - self.x
        dy = player.y - self.y
        dist_sq = dx * dx + dy * dy
        if dist_sq == 0:
            return

        dist = dist_sq ** 0.5
        dir_x = dx / dist
        dir_y = dy / dist

        vel = self.speed * self.speed_variation
        self.x += dir_x * vel
        self.y += dir_y * vel

    def draw(self, screen, camera_offset):
        if not self.alive:
            return

        screen.blit(
            self.image,
            (self.x - camera_offset[0], self.y - camera_offset[1])
        )
