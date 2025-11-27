import math
import os

import pygame

from entities.entity import Entity
from core.settings import (
    ENEMY_BASE_HEALTH,
    ENEMY_ATTACK_RANGE,
    ENEMY_ATTACK_COOLDOWN,
)
from graphics.sprite_sheet import SpriteSheet


class BossDiablo(Entity):
    """
    Jefe final: Diablo.
    Compatible con la interfaz de Enemy:
      - .alive
      - .health
      - .rect
      - .update(dt, player)
      - .draw(screen, camera_offset)
      - .take_damage(amount)
      - .get_attack_hitbox()
    """

    def __init__(self, x, y):
        # tamaño base del sprite (cada celda)
        cell = 192
        super().__init__(x, y, cell, cell, speed=1.6)

        # Escala para que se vea más grande que Octavio
        self.scale = 2.0

        # --- Estadísticas del jefe ---
        # Mucha más vida que un enemigo normal
        self.max_health = ENEMY_BASE_HEALTH * 10
        self.health = self.max_health
        self.alive = True

        # pega más fuerte que un enemigo normal
        self.damage = 2.5  # se usa como "multiplicador" sobre el daño base del enemigo normal si quieres

        self.attack_range = ENEMY_ATTACK_RANGE * 1.4
        self.attack_cooldown = 2.0  # segundos entre ataques (lo que pediste)
        self.last_attack_time = 0.0
        self.attack_executed = False

        # --- SpriteSheets del Diablo ---
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "Enemys", "Diablo")
        # Ojo: ajusta las rutas si tu carpeta no coincide exactamente
        self.sheet_idle = SpriteSheet(os.path.join(base_path, "el propio diablo_idle.png"))
        self.sheet_attack = SpriteSheet(os.path.join(base_path, "el propio diablo_thrust.png"))
        self.sheet_walk = SpriteSheet(os.path.join(base_path, "el propio diablo_walk.png"))
        self.sheet_death = SpriteSheet(os.path.join(base_path, "el propio diablo_hurt.png"))

        # --- Diccionarios de animaciones ---
        # animations[state][direction] -> [frames]
        self.animations = {
            "idle": {},
            "walk": {},
            "attack": {},
            "death": {},
        }

        # Helper interno para cargar una fila completa
        def load_from_row(sheet, row, num_frames, start_col=0):
            frames = []
            sheet_surface = sheet.sprite_sheet
            sheet_w, sheet_h = sheet_surface.get_size()

            for f in range(num_frames):
                col = start_col + f
                x = col * cell
                y = row * cell
                if x + cell > sheet_w or y + cell > sheet_h:
                    break

                frame = sheet.get_sprite(x, y, cell, cell)

                # Escalar para que el jefe sea grande
                new_w = int(cell * self.scale)
                new_h = int(cell * self.scale)
                frame = pygame.transform.scale(frame, (new_w, new_h))
                frames.append(frame)
            return frames

        # Mapeos de filas (revisa si las direcciones coinciden visualmente)
        # Supuesto clásico: 0=down, 1=left, 2=right, 3=up
        idle_rows = {"down": 0, "left": 1, "right": 2, "up": 3}
        walk_rows = {"down": 0, "left": 1, "right": 2, "up": 3}
        attack_rows = {"down": 0, "left": 1, "right": 2, "up": 3}
        death_row = 0  # una sola fila para muerte

        # Idle (2 frames)
        for direction, row in idle_rows.items():
            self.animations["idle"][direction] = load_from_row(self.sheet_idle, row, num_frames=2)

        # Walk (8 frames)
        for direction, row in walk_rows.items():
            self.animations["walk"][direction] = load_from_row(self.sheet_walk, row, num_frames=8)

        # Attack (7 frames)
        for direction, row in attack_rows.items():
            self.animations["attack"][direction] = load_from_row(self.sheet_attack, row, num_frames=7)

        # Death (5 frames, misma fila para todas las direcciones)
        for direction in ["down", "left", "right", "up"]:
            self.animations["death"][direction] = load_from_row(self.sheet_death, death_row, num_frames=5)

        # --- Estado de animación ---
        self.state = "idle"
        self.direction = "down"
        self.current_frames = self.animations[self.state][self.direction]
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_frame_time = 0.12

        # Ancho/alto reales tras escalar
        first_frame = self.current_frames[0]
        self.width = first_frame.get_width()
        self.height = first_frame.get_height()

        # Hitbox del cuerpo
        self.hitbox_width = int(self.width * 0.35)
        self.hitbox_height = int(self.height * 0.55)
        self.hitbox_offset_x = (self.width - self.hitbox_width) // 2
        self.hitbox_offset_y = (self.height - self.hitbox_height) // 2

        # Rect para colisiones generales (igual que Enemy)
        self._rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # --- Sonido del ataque ---
        snd_path = os.path.join(os.path.dirname(__file__), "..", "assets", "Sounds", "SlashD.mp3")
        try:
            self.sound_attack = pygame.mixer.Sound(snd_path)
            self.sound_attack.set_volume(0.6)
        except pygame.error:
            self.sound_attack = None  # si falla, simplemente no suena

    # ==========================================================
    # Helpers de animación / estado
    # ==========================================================
    def set_state(self, state: str):
        if state == self.state:
            return
        self.state = state
        self.current_frames = self.animations[self.state][self.direction]
        self.current_frame_index = 0
        self.animation_timer = 0.0

    def set_direction(self, direction: str):
        if direction == self.direction:
            return
        self.direction = direction
        self.current_frames = self.animations[self.state][self.direction]
        self.current_frame_index = 0
        self.animation_timer = 0.0

    def update_animation(self, dt: float):
        if not self.current_frames:
            return
        self.animation_timer += dt
        if self.animation_timer >= self.animation_frame_time:
            self.animation_timer = 0.0
            self.current_frame_index = (self.current_frame_index + 1) % len(self.current_frames)

    # ==========================================================
    # Daño recibido (llamado desde Game.handle_player_attack_collisions)
    # ==========================================================
    def take_damage(self, amount: float):
        if not self.alive:
            return

        self.health -= amount
        if self.health <= 0:
            self.health = 0
            # Pasar a animación de muerte
            self.set_state("death")
            # seguimos "vivos" hasta terminar la animación

    # ==========================================================
    # Lógica de IA
    # ==========================================================
    def update(self, dt: float, player):
        if not self.alive:
            return

        # Si está en animación de muerte
        if self.state == "death":
            self.update_animation(dt)
            # cuando llegue al último frame, desaparece
            if self.current_frame_index == len(self.current_frames) - 1:
                self.alive = False
            return

        # Distancia al jugador
        dx = (player.x - self.x)
        dy = (player.y - self.y)
        dist = math.hypot(dx, dy) or 1.0  # evitar división por 0

        # Dirección hacia donde mira
        if abs(dx) > abs(dy):
            new_dir = "right" if dx > 0 else "left"
        else:
            new_dir = "down" if dy > 0 else "up"
        self.set_direction(new_dir)

        now = pygame.time.get_ticks() / 1000.0

        # Si está en rango y se acabó el cooldown -> atacar
        if dist <= self.attack_range and now - self.last_attack_time >= self.attack_cooldown:
            self.set_state("attack")
            self.last_attack_time = now
            self.attack_executed = False
            # en ataque, no se mueve; animación manejará el golpe
        else:
            # Movimiento hacia Octavio
            self.set_state("walk")
            speed = self.speed
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed
            self.update_animation(dt)

        # Rect en la nueva posición
        self._rect.x = int(self.x)
        self._rect.y = int(self.y)

        # Si está atacando, gestionar golpe en frame medio
        if self.state == "attack":
            self.update_animation(dt)
            total = len(self.current_frames)
            mid = total // 2

            if self.current_frame_index == mid and not self.attack_executed:
                if self.sound_attack:
                    self.sound_attack.play()
                if player.rect.colliderect(self.get_attack_hitbox()):
                    # usamos daño del jefe; si quieres multiplicar por daño base, hazlo en settings
                    player.take_damage(self.damage)
                self.attack_executed = True

            # Cuando termina la animación, volvemos a idle
            if self.current_frame_index == total - 1:
                self.set_state("idle")

    # ==========================================================
    # Campo de ataque del jefe (similar al Enemy)
    # ==========================================================
    def get_attack_hitbox(self):
        base = pygame.Rect(
            self.x + self.hitbox_offset_x,
            self.y + self.hitbox_offset_y,
            self.hitbox_width,
            self.hitbox_height
        )

        if self.direction == "up":
            return pygame.Rect(base.centerx - 30, base.top - 40, 60, 40)
        if self.direction == "down":
            return pygame.Rect(base.centerx - 30, base.bottom, 60, 40)
        if self.direction == "left":
            return pygame.Rect(base.left - 40, base.centery - 20, 40, 40)
        return pygame.Rect(base.right, base.centery - 20, 40, 40)

    # ==========================================================
    # Dibujar en pantalla (llamado desde Game.draw)
    # ==========================================================
    def draw(self, screen, camera_offset):
        if not self.alive:
            return

        frame = self.current_frames[self.current_frame_index]
        screen.blit(
            frame,
            (self.x - camera_offset[0], self.y - camera_offset[1])
        )
