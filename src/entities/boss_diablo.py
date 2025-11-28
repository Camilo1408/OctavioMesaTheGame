import math
import os

import pygame

from entities.entity import Entity
from core.settings import (
    ENEMY_BASE_HEALTH,
    ENEMY_ATTACK_RANGE,
    ENEMY_ATTACK_COOLDOWN,
    MAP_HEIGHT_PX,
    MAP_WIDTH_PX
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

    def __init__(self, x, y, sound_manager=None):
        # tamaño base del sprite (cada celda)
        cell = 192
        super().__init__(x, y, cell, cell, speed=1.6)

        # Escala para que se vea más grande que Octavio
        self.scale = 2.0

        # Gestor de sonidos
        self.sound_manager = sound_manager

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
        idle_rows = {"down": 2, "left": 1, "right": 3, "up": 0}
        walk_rows = {"down": 2, "left": 1, "right": 3, "up": 0}
        attack_rows = {"down": 2, "left": 1, "right": 3, "up": 0}
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

        # --- Hitbox del cuerpo del Diablo ---
        # Más pegada al contorno del cuerpo (sin incluir la lanza completa)
        self.hitbox_width = int(self.width * 0.22)      # cuerpo relativamente estrecho
        self.hitbox_height = int(self.height * 0.27)    # parte baja del cuerpo
        self.hitbox_offset_x = (self.width - self.hitbox_width) // 2
        # la subimos para que quede en piernas/torso, no flotando en el centro
        self.hitbox_offset_y = self.height - self.hitbox_height - 130

        # Rect para colisiones generales (igual que Enemy)
        self._rect = pygame.Rect(self.x, self.y, self.width, self.height)

        self.is_boss = True


    @property
    def rect(self):
        """Hitbox real del Diablo usada en colisiones y daño."""
        return pygame.Rect(
            int(self.x + self.hitbox_offset_x),
            int(self.y + self.hitbox_offset_y),
            self.hitbox_width,
            self.hitbox_height,
        )


    def clamp_to_map(self):
        """Evita que el Diablo salga de los límites del mapa."""
        max_x = MAP_WIDTH_PX - self.width
        max_y = MAP_HEIGHT_PX - self.height

        if self.x < 0:
                self.x = 0
        elif self.x > max_x:
                self.x = max_x

        if self.y < 0:
                self.y = 0
        elif self.y > max_y:
                self.y = max_y


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

    def update_animation(self, dt: float,  loop: bool = True):
        if not self.current_frames:
            return

        self.animation_timer += dt
        if self.animation_timer >= self.animation_frame_time:
            self.animation_timer = 0.0
            self.current_frame_index += 1

            if self.current_frame_index >= len(self.current_frames):
                if loop:
                    # volver al inicio (idle, walk, attack)
                    self.current_frame_index = 0
                else:
                    # quedarnos en el último frame (muerte)
                    self.current_frame_index = len(self.current_frames) - 1

    # ==========================================================
    # Daño recibido (llamado desde Game.handle_player_attack_collisions)
    # ==========================================================
    def take_damage(self, amount: float):
        if not self.alive or self.state == "death":
            return

        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.set_state("death")
            if self.sound_manager:
                self.sound_manager.play("diablo_death")
        else:
            if self.sound_manager:
                self.sound_manager.play("diablo_hurt")

    # ==========================================================
    # Lógica de IA
    # ==========================================================
    def update(self, dt: float, player):
        if not self.alive:
            return

        # ---------------------------
        # MUERTE: solo animación
        # ---------------------------
        if self.state == "death":
            # Anim de muerte sin loop (se queda en el último frame)
            self.update_animation(dt, loop=False)
            return

        # --------------------------------------------------
        # Distancia REAL usando hitboxes (no solo x,y)
        # --------------------------------------------------
        boss_hitbox = pygame.Rect(
            self.x + self.hitbox_offset_x,
            self.y + self.hitbox_offset_y,
            self.hitbox_width,
            self.hitbox_height,
        )

        player_hitbox = pygame.Rect(
            player.x + player.hitbox_offset_x,
            player.y + player.hitbox_offset_y,
            player.hitbox_width,
            player.hitbox_height,
        )

        dx = player_hitbox.centerx - boss_hitbox.centerx
        dy = player_hitbox.centery - boss_hitbox.centery
        dist = math.hypot(dx, dy) or 1.0  # evitar división por 0

        # --------------------------------------------------
        # Dirección a la que mira EL DIABLO
        # --------------------------------------------------
        if abs(dx) > abs(dy):
            new_dir = "right" if dx > 0 else "left"
        else:
            new_dir = "down" if dy > 0 else "up"
        self.set_direction(new_dir)

        now = pygame.time.get_ticks() / 1000.0

        # --------------------------------------------------
        # ¿Está en rango para atacar? (usando el área real de ataque)
        # --------------------------------------------------
        attack_area = self.get_attack_hitbox()   # usa self.direction + self.rect
        in_range = attack_area is not None and attack_area.colliderect(player_hitbox)

        can_attack = (
            in_range and (now - self.last_attack_time) >= self.attack_cooldown
        )

        if can_attack:
            self.set_state("attack")
            self.last_attack_time = now
            self.attack_executed = False

        # --------------------------------------------------
        # SI ESTÁ ATACANDO → NO MOVER, SOLO ANIM Y DAÑO
        # --------------------------------------------------
        if self.state == "attack":
            self.update_animation(dt)
            total = len(self.current_frames)
            if total == 0:
                return
            mid = total // 2

            # Frame donde "conecta" el golpe
            if self.current_frame_index == mid and not self.attack_executed:
                if self.sound_manager:
                    self.sound_manager.play("diablo_attack")

                atk_rect = self.get_attack_hitbox()
                if atk_rect is not None and atk_rect.colliderect(player_hitbox):
                    player.take_damage(self.damage)

                self.attack_executed = True

            # Cuando termina animación de ataque, volver a idle
            if self.current_frame_index == total - 1:
                self.set_state("idle")

            return  # 🔴 IMPORTANTE: no seguir con lógica de caminar

        # --------------------------------------------------
        # SI NO ESTÁ ATACANDO:
        #   - si está muy cerca, quedarse quieto (idle)
        #   - si está más lejos, caminar hacia Octavio
        # --------------------------------------------------
        MIN_SEPARATION = 16  # para que respete hitboxes y no empuje tanto

        if dist <= max(self.attack_range * 0.9, MIN_SEPARATION) or in_range:
            # Muy cerca o ya dentro del área de ataque → quieto, mirando al jugador
            self.set_state("idle")
            self.update_animation(dt)
        else:
            # Perseguir caminando
            self.set_state("walk")
            speed = self.speed
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed

            # No salir del mapa
            self.clamp_to_map()

            # Animación de caminar
            self.update_animation(dt)

        # Actualizar rect global
        self._rect.x = int(self.x)
        self._rect.y = int(self.y)

    # ==========================================================
    # Campo de ataque del jefe (similar al Enemy)
    # ==========================================================
    def get_attack_hitbox(self):
        """
        Área de ataque del Diablo, basada en su hitbox real (rect).
        Ajustada para que hacia abajo quede pegada a los pies y no tan ancha.
        """

        base = self.rect  # usamos la hitbox del cuerpo como referencia

        # Márgenes finos
        side_margin = 4   # más pequeño → más cerca del cuerpo
        vertical_range = int(self.hitbox_height * 0.7)
        horizontal_range = int(self.hitbox_width * 0.7)

        if self.direction == "up":
            return pygame.Rect(
                base.left - side_margin,
                base.top - vertical_range,
                base.width + side_margin * 2,
                vertical_range,
            )

        elif self.direction == "down":
            # 🔥 Pegado justo a los pies del Diablo
            return pygame.Rect(
                base.left - side_margin,
                base.bottom,                  # sin hueco, justo debajo del cuerpo
                base.width + side_margin * 2,
                vertical_range,
            )

        elif self.direction == "left":
            return pygame.Rect(
                base.left - horizontal_range,
                base.top - side_margin,
                horizontal_range,
                base.height + side_margin * 2,
            )

        else:  # "right"
            return pygame.Rect(
                base.right,
                base.top - side_margin,
                horizontal_range,
                base.height + side_margin * 2,
            )
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