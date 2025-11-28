import math
import random
from enum import Enum, auto

import pygame

from entities.entity import Entity
from core.settings import (
    TILE_SIZE,
    ENEMY_BASE_HEALTH,
    ENEMY_ATTACK_COOLDOWN,
    ENEMY_ATTACK_RANGE,
    ENEMY_SPRITES,
)
from graphics.sprite_sheet import SpriteSheet


class EnemyState(Enum):
    IDLE = auto()
    WALK = auto()
    RUN = auto()
    ATTACK = auto()
    HURT = auto()
    DEATH = auto()


class Enemy(Entity):
    def __init__(
        self,
        x,
        y,
        enemy_type: str | None = None,
        health: float | None = None,
        damage: float | None = None,
        sound_manager = None
    ):
        # Tipo de enemigo (orc1, orc2, orc3)
        if enemy_type is None:
            enemy_type = random.choice(list(ENEMY_SPRITES.keys()))
        self.enemy_type = enemy_type

        # Físicas base
        super().__init__(x, y, TILE_SIZE, TILE_SIZE, speed=2.0)

        # Vida y daño
        self.health = health if health is not None else ENEMY_BASE_HEALTH
        self.damage = damage if damage is not None else 10

        self.sound_manager = sound_manager

        # Variación ligera de velocidad
        self.speed_variation = random.uniform(0.9, 1.1)

        # Combate
        self.attack_range = ENEMY_ATTACK_RANGE
        self.attack_cooldown = ENEMY_ATTACK_COOLDOWN
        self.last_attack_time = 0.0
        self.attack_executed = False

        # Estados / dirección
        self.state = EnemyState.IDLE
        self.direction = "down"  # "down", "up", "left", "right"

        # Animaciones: animations[state_name][direction] -> [frames]
        self.animations = self._load_animations()

        self.current_anim_name = "idle"
        self.current_frames = self.animations["idle"]["down"]
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_frame_time = 0.12
        self.animation_finished = False

        # --- Hitbox del enemigo (centrada respecto al sprite escalado) ---
        base_frame = self.current_frames[0]
        self.sprite_width = base_frame.get_width()
        self.sprite_height = base_frame.get_height()

        # Hitbox más pequeña que el sprite
        self.hitbox_width = int(self.sprite_width * 0.3)    # 30% del ancho
        self.hitbox_height = int(self.sprite_height * 0.5)  # 50% de la altura

        # Centrada y un poco subida
        self.hitbox_offset_x = (self.sprite_width - self.hitbox_width) // 2
        self.hitbox_offset_y = self.sprite_height - self.hitbox_height - 32

    # ----------------------
    # CARGA DE SPRITES 4x8
    # ----------------------
    def _load_strip(self, image_path: str):
        """
        Carga una hoja con 4 filas (direcciones) y N columnas:
        - fila 0: down
        - fila 1: up
        - fila 2: left
        - fila 3: right
        Asume frames cuadrados (cell_w = cell_h).
        Devuelve dict[direction] -> [frames]
        """
        sheet = SpriteSheet(image_path)
        full_surface = sheet.sprite_sheet
        sheet_width, sheet_height = full_surface.get_size()

        rows = 4
        cell_h = sheet_height // rows
        cell_w = cell_h                 # frames cuadrados
        frames_per_row = sheet_width // cell_w

        SCALE = 1.5  # ajusta si quieres enemigos más grandes o más pequeños

        dir_rows = {
            "down": 0,
            "up": 1,
            "left": 2,
            "right": 3,
        }

        directional_frames: dict[str, list[pygame.Surface]] = {}

        for dir_name, row_idx in dir_rows.items():
            frames: list[pygame.Surface] = []
            y = row_idx * cell_h

            for col in range(frames_per_row):
                x = col * cell_w
                frame = sheet.get_sprite(x, y, cell_w, cell_h)

                # Escalamos UNA vez aquí
                new_w = int(cell_w * SCALE)
                new_h = int(cell_h * SCALE)
                frame = pygame.transform.scale(frame, (new_w, new_h))

                frames.append(frame)

            directional_frames[dir_name] = frames

        return directional_frames

    def _load_animations(self):
        """Carga todas las animaciones definidas en settings para este tipo."""
        paths = ENEMY_SPRITES[self.enemy_type]
        animations = {}
        for key, path in paths.items():
            animations[key] = self._load_strip(path)  # dict[direction] -> [frames]
        return animations


    # ----------------------
    # UTIL estado / anim
    # ----------------------
    def _state_name(self, state: EnemyState | None = None) -> str:
        if state is None:
            state = self.state
        if state == EnemyState.IDLE:
            return "idle"
        if state == EnemyState.WALK:
            return "walk"
        if state == EnemyState.RUN:
            return "run"
        if state == EnemyState.ATTACK:
            return "attack"
        if state == EnemyState.HURT:
            return "hurt"
        if state == EnemyState.DEATH:
            return "death"
        return "idle"

    def _set_animation_for(self, state: EnemyState):
        """
        Selecciona frames según estado + dirección actual.
        IMPORTANTE: solo resetea si el estado cambió, para no romper la animación.
        """
        state_name = self._state_name(state)

        # 🔑 Clave del bug que tenías:
        # si el estado es el mismo y ya estamos en esa animación, NO reseteamos.
        if self.state == state and self.current_anim_name == state_name:
            return

        self.state = state
        self.current_anim_name = state_name

        anims_for_state = self.animations.get(state_name, {})
        frames = anims_for_state.get(self.direction)

        if not frames:
            if anims_for_state:
                frames = next(iter(anims_for_state.values()))
            else:
                frames = []

        self.current_frames = frames
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_finished = False

    # ----------------------
    # HITBOX
    # ----------------------
    @property
    def rect(self):
        from pygame import Rect
        return Rect(
            int(self.x + self.hitbox_offset_x),
            int(self.y + self.hitbox_offset_y),
            self.hitbox_width,
            self.hitbox_height,
        )
    
    # ----------------------
    # CAMPO DE ATAQUE
    # ----------------------
    def get_attack_hitbox(self):
        """
        Devuelve un Rect (en coordenadas del mundo) con el área de ataque del enemigo.
        Solo existe mientras está en estado ATTACK.
        """
        if self.state != EnemyState.ATTACK:
            return None

        import pygame

        # Usamos la hitbox reducida como base
        base_rect = pygame.Rect(
            self.x + self.hitbox_offset_x,
            self.y + self.hitbox_offset_y,
            self.hitbox_width,
            self.hitbox_height,
        )

        range_px = int(self.attack_range)

        if self.direction == "up":
            return pygame.Rect(
                base_rect.centerx - base_rect.width // 2,
                base_rect.top - range_px,
                base_rect.width,
                range_px,
            )
        elif self.direction == "down":
            return pygame.Rect(
                base_rect.centerx - base_rect.width // 2,
                base_rect.bottom,
                base_rect.width,
                range_px,
            )
        elif self.direction == "left":
            return pygame.Rect(
                base_rect.left - range_px,
                base_rect.centery - base_rect.height // 2,
                range_px,
                base_rect.height,
            )
        else:  # "right"
            return pygame.Rect(
                base_rect.right,
                base_rect.centery - base_rect.height // 2,
                range_px,
                base_rect.height,
            )

    # ----------------------
    # ANIMACIÓN
    # ----------------------
    def _update_animation(self, dt: float, loop: bool = True):
        if not self.current_frames:
            return

        self.animation_timer += dt
        if self.animation_timer < self.animation_frame_time:
            return

        self.animation_timer -= self.animation_frame_time
        self.current_frame_index += 1

        if self.current_frame_index >= len(self.current_frames):
            if loop:
                self.current_frame_index = 0
                self.animation_finished = False
            else:
                self.current_frame_index = len(self.current_frames) - 1
                self.animation_finished = True

    # ----------------------
    # COMBATE
    # ----------------------
    def take_damage(self, amount: float):
        if not self.alive or self.state == EnemyState.DEATH:
            return

        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self._set_animation_for(EnemyState.DEATH)
            # Sonido de muerte
            if self.sound_manager:
                self.sound_manager.play("orc_death")
        else:
            self._set_animation_for(EnemyState.HURT)
            # Sonido de daño
            if self.sound_manager:
                self.sound_manager.play("orc_hurt")

    def _start_attack(self):
        self._set_animation_for(EnemyState.ATTACK)
        self.last_attack_time = pygame.time.get_ticks() / 1000.0
        self.attack_executed = False

    # ----------------------
    # DIRECCIÓN
    # ----------------------
    def _update_direction_from_vector(self, dx: float, dy: float):
        if dx == 0 and dy == 0:
            return

        new_dir = self.direction

        if abs(dx) > abs(dy):
            new_dir = "right" if dx > 0 else "left"
        else:
            new_dir = "down" if dy > 0 else "up"

        if new_dir != self.direction:
            self.direction = new_dir
            # Cambiar solo frames, pero NO estado ni reiniciar
            state_name = self._state_name(self.state)
            anims_for_state = self.animations.get(state_name, {})
            frames = anims_for_state.get(self.direction)
            if frames:
                idx = min(self.current_frame_index, len(frames) - 1)
                self.current_frames = frames
                self.current_frame_index = idx

    # ----------------------
    # UPDATE (IA + ESTADOS)
    # ----------------------
    def update(self, dt: float, player):
        if not self.alive:
            return

        # Estados que ignoran movimiento
        if self.state == EnemyState.DEATH:
            self._update_animation(dt, loop=False)
            if self.animation_finished:
                self.alive = False
            return

        if self.state == EnemyState.HURT:
            self._update_animation(dt, loop=False)
            if self.animation_finished:
                self._set_animation_for(EnemyState.RUN)
            return

        # Distancia al jugador
        dx = player.x - self.x
        dy = player.y - self.y
        dist_sq = dx * dx + dy * dy
        dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0

        dir_x = dx / dist if dist > 0 else 0.0
        dir_y = dy / dist if dist > 0 else 0.0

        # Dirección según vector al jugador
        self._update_direction_from_vector(dx, dy)

        now = pygame.time.get_ticks() / 1000.0

        # ¿Puede atacar?
        can_attack = (
            dist <= self.attack_range
            and (now - self.last_attack_time) >= self.attack_cooldown
        )

        if can_attack:
            self._start_attack()

        # Ataque
        if self.state == EnemyState.ATTACK:
            self._update_animation(dt, loop=False)

            frames = self.current_frames
            mid_index = len(frames) // 2 if frames else 0

            # Solo pegamos una vez, en la mitad de la animación
            if not self.attack_executed and self.current_frame_index >= mid_index:
                # Sonido de ataque del orco
                if self.sound_manager:
                    self.sound_manager.play("orc_attack")

                atk_rect = self.get_attack_hitbox()

                if atk_rect is not None:
                    # Hitbox del jugador (reducida si existe, si no usamos rect/width/height)
                    if hasattr(player, "hitbox_width"):
                        player_rect = pygame.Rect(
                            player.x + player.hitbox_offset_x,
                            player.y + player.hitbox_offset_y,
                            player.hitbox_width,
                            player.hitbox_height,
                        )
                    elif hasattr(player, "rect"):
                        player_rect = player.rect
                    else:
                        player_rect = pygame.Rect(
                            player.x,
                            player.y,
                            getattr(player, "width", 32),
                            getattr(player, "height", 32),
                        )

                    if atk_rect.colliderect(player_rect) and hasattr(player, "take_damage"):
                        player.take_damage(self.damage)

                self.attack_executed = True

            if self.animation_finished:
                self._set_animation_for(EnemyState.RUN)

            return

        # Movimiento
        if dist > 5:
            if dist > self.attack_range * 1.5:
                desired_state = EnemyState.RUN
            else:
                desired_state = EnemyState.WALK

            if self.state != desired_state:
                self._set_animation_for(desired_state)

            move_speed = self.speed * (1.5 if desired_state == EnemyState.RUN else 1.0)
            move_speed *= self.speed_variation

            self.x += dir_x * move_speed
            self.y += dir_y * move_speed
        else:
            if self.state != EnemyState.IDLE:
                self._set_animation_for(EnemyState.IDLE)

        self._update_animation(dt, loop=True)

    # ----------------------
    # DIBUJADO
    # ----------------------
    def draw(self, screen, camera_offset):
        if not self.alive:
            return

        if not self.current_frames:
            return

        frame = self.current_frames[self.current_frame_index]

        screen.blit(
            frame,
            (self.x - camera_offset[0], self.y - camera_offset[1])
        )
