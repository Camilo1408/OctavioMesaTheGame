import os
import pygame
from sprite_sheet import SpriteSheet


class Player:
    def __init__(self, x, y, sprite_path=None, sprite_size=64, unarmed_row=39, armed_row=10, frames_per_direction=None, row_index_base=0):
        """Player with configurable sprite sheet layout."""
        self.x = x
        self.y = y
        self.width = sprite_size
        self.height = sprite_size
        self.speed = 5
        self.is_armed = False
        self.is_attacking = False
        self.attack_duration = 0.35
        self.attack_timer = 0.0
        self.movement = {'up': False, 'down': False, 'left': False, 'right': False}

        # Hitbox más pequeña (centrada)
        self.hitbox_width = int(self.width * 0.5) # 50% del ancho → ~32 px
        self.hitbox_height = int(self.height * 0.75)  # 75% de la altura → ~48 px
        self.hitbox_offset_x = (self.width - self.hitbox_width) // 2
        self.hitbox_offset_y = self.height - self.hitbox_height


        # Sprite sheet setup
        if sprite_path is None:
            sprite_path = os.path.join('assets', 'sprites', 'Octavio Mesa.png')
        sprite_path = sprite_path.replace('\\', '/')
        self.sprite_size = sprite_size
        self.unarmed_row = unarmed_row
        self.armed_row = armed_row
        self.frames_per_direction = frames_per_direction
        self.row_index_base = row_index_base

        # Animation speeds
        self.walk_animation_speed = 0.10
        self.idle_animation_speed = 0.25
        self.linger_time = 0.05
        self.linger_timer = 0.0
        self.animation_speed = self.walk_animation_speed

        # Load sprite sheet
        try:
            self.sprite_sheet = SpriteSheet(sprite_path)
        except Exception:
            raise FileNotFoundError(f"No se pudo cargar el sprite sheet en: {sprite_path}")

        # Animations
        self.animations = {
            'unarmed': {'idle': [], 'walk_up': [], 'walk_left': [], 'walk_down': [], 'walk_right': [],
                        'attack_up': [], 'attack_left': [], 'attack_down': [], 'attack_right': []},
            'armed': {'idle': [], 'walk_up': [], 'walk_left': [], 'walk_down': [], 'walk_right': [],
                      'attack_up': [], 'attack_left': [], 'attack_down': [], 'attack_right': []},
            'idle': {'unarmed': {}, 'armed': {}}
        }

        # Load all animations
        self.load_animations()

        # Animation state
        self.current_animation = 'idle_down'
        self.animation_frame = 0
        self.animation_timer = 0.0
        self.facing = 'down'

        # Default image
        default_set = 'armed' if self.is_armed else 'unarmed'
        if len(self.animations[default_set]['idle']) > 0:
            self.image = self.animations[default_set]['idle'][0]
        else:
            surf = pygame.Surface((self.sprite_size, self.sprite_size), pygame.SRCALPHA)
            surf.fill((255, 0, 255))
            self.image = surf

    def load_animations(self):
        """Carga animaciones de caminar, estar quieto y ataque (armado y sin arma)."""
        ss = self.sprite_sheet.sprite_sheet
        sheet_w, sheet_h = ss.get_width(), ss.get_height()
        cell = self.sprite_size
        cols = max(1, sheet_w // cell)
        frames_per_dir = self.frames_per_direction or cols

        def load_from_row(row, num_frames, is_attack=False, direction=None, armed=False):
            frames = []
            y = (row - self.row_index_base) * cell
            for f in range(num_frames):
                x = f * cell
                width = cell
                # ⚔️ Si es ataque armado hacia arriba o abajo, ampliar solo el último frame
                if is_attack and armed and direction in ['up', 'down'] and f == num_frames - 1:
                    width = int(cell * 1.5)  # 96px si cell = 64
                if x + width > sheet_w:
                    break
                frame = self.sprite_sheet.get_sprite(x, y, width, cell)
                frames.append(frame)
            return frames

        # 🔹 Animaciones de caminar
        directions = ['walk_up', 'walk_left', 'walk_down', 'walk_right']
        for i, direction in enumerate(directions):
            row_unarmed = self.unarmed_row + i
            row_armed = self.armed_row + i
            self.animations['unarmed'][direction] = load_from_row(row_unarmed, frames_per_dir)
            self.animations['armed'][direction] = load_from_row(row_armed, frames_per_dir)

        # 🔹 Animaciones de estar quieto
        idle_rows_unarmed = {'up': 23, 'left': 24, 'down': 25, 'right': 26}
        idle_rows_armed = {'up': 59, 'left': 60, 'down': 61, 'right': 62}

        for direction, row in idle_rows_unarmed.items():
            self.animations['idle']['unarmed'][direction] = load_from_row(row, num_frames=2)
        for direction, row in idle_rows_armed.items():
            self.animations['idle']['armed'][direction] = load_from_row(row, num_frames=2)

        # 🔹 Animaciones de ataque sin arma (6 frames)
        attack_rows_unarmed = {'up': 51, 'left': 52, 'down': 53, 'right': 54}
        for direction, row in attack_rows_unarmed.items():
            self.animations['unarmed'][f'attack_{direction}'] = load_from_row(row, num_frames=6)

        # 🔹 Animaciones de ataque con arma (5 frames)
        attack_rows_armed = {'up': 55, 'left': 56, 'down': 57, 'right': 58}
        for direction, row in attack_rows_armed.items():
            self.animations['armed'][f'attack_{direction}'] = load_from_row(
                row, num_frames=6, is_attack=True, direction=direction, armed=True)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.movement = {'up': False, 'down': False, 'left': False, 'right': False}

        if not self.is_attacking:
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.movement['up'] = True
                self.facing = 'up'
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.movement['down'] = True
                self.facing = 'down'
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.movement['left'] = True
                self.facing = 'left'
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.movement['right'] = True
                self.facing = 'right'

            # Iniciar ataque con clic izquierdo o tecla J
            if keys[pygame.K_j] or pygame.mouse.get_pressed()[0]:
                self.start_attack()

    def start_attack(self):
        """Inicia animación de ataque (se bloquea movimiento mientras dura)."""
        self.is_attacking = True
        self.attack_timer = 0.0
        self.animation_frame = 0
        self.current_animation = f'attack_{self.facing}'

    def update(self, dt=1/60):
        self.handle_input()

        # ⚔️ ATAQUE
        if self.is_attacking:
            set_key = 'armed' if self.is_armed else 'unarmed'
            anim_set = self.animations[set_key]
            frames = anim_set.get(self.current_animation, [])

            attack_duration = 0.45 if self.is_armed else 0.35
            self.attack_timer += dt
            self.animation_timer += dt
            frame_time = attack_duration / max(1, len(frames))

            if len(frames) > 0 and self.animation_timer >= frame_time:
                self.animation_timer = 0.0
                self.animation_frame += 1

                if self.animation_frame >= len(frames):
                    self.is_attacking = False
                    self.animation_frame = 0
                    self.current_animation = f"idle_{self.facing}"
                    self.animation_timer = 0.0
                    idle_set = self.animations['idle']['armed'] if self.is_armed else self.animations['idle']['unarmed']
                    frames = idle_set.get(self.facing, [])
                    if frames:
                        self.image = frames[0]
                    return
                else:
                    self.image = frames[self.animation_frame]
            return

        # 🚶 MOVIMIENTO
        dx, dy = 0, 0

        # Movimiento vertical (cancelar opuestos)
        if self.movement['up'] and not self.movement['down']:
            dy = -1
            self.facing = 'up'
        elif self.movement['down'] and not self.movement['up']:
            dy = 1
            self.facing = 'down'

        # Movimiento horizontal (cancelar opuestos)
        if self.movement['left'] and not self.movement['right']:
            dx = -1
            self.facing = 'left'
        elif self.movement['right'] and not self.movement['left']:
            dx = 1
            self.facing = 'right'

        # Normalizar velocidad en diagonal
        if dx != 0 and dy != 0:
            norm = 0.7071
            dx *= norm
            dy *= norm

        # Guardar posición previa
        old_x, old_y = self.x, self.y

        # Calcular nueva posición tentativa
        self.x += dx * self.speed
        self.y += dy * self.speed

        # 🧱 LIMITES DEL MAPA
        map_width = 50 * 32
        map_height = 50 * 32
        collided = not self.clamp_to_map(map_width, map_height)

        # Determinar si realmente se movió
        moved = (self.x != old_x or self.y != old_y) and not collided

        # Actualizar animación solo si se movió efectivamente
        moving = moved and (dx != 0 or dy != 0)
        if moving:
            self.current_animation = f'walk_{self.facing}'
        else:
            # ⏸️ mantener último frame de caminar unos ms antes de idle
            if "walk" in self.current_animation:
                if self.linger_timer < self.linger_time:
                    self.linger_timer += dt
                    return
                else:
                    self.linger_timer = 0.0
            self.current_animation = f"idle_{self.facing}"

        # 🕒 VELOCIDAD SEGÚN ESTADO
        self.animation_speed = self.walk_animation_speed if moving else self.idle_animation_speed
        if moving:
            self.linger_timer = 0.0

        # 🔄 Selección de frames
        set_key = 'armed' if self.is_armed else 'unarmed'
        anim_set = self.animations.get(set_key, {})

        if 'idle' in self.current_animation:
            idle_set = self.animations['idle']['armed'] if self.is_armed else self.animations['idle']['unarmed']
            frames = idle_set.get(self.facing, [])
        else:
            frames = anim_set.get(self.current_animation, [])

        # ⏱️ Avance de animación
        self.animation_timer += dt
        if len(frames) > 0 and self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.animation_frame = (self.animation_frame + 1) % len(frames)
            self.image = frames[self.animation_frame]

        # 🕒 Mostrar primer frame de idle inmediatamente si no se mueve
        if not moving and 'idle' in self.current_animation and frames:
            self.image = frames[self.animation_frame % len(frames)]

    def clamp_to_map(self, map_width, map_height):
        """Evita que el jugador salga del mapa respetando la hitbox.
        Retorna True si sigue dentro de los límites, False si tocó el borde."""
        old_x, old_y = self.x, self.y

        if self.x + self.hitbox_offset_x < 0:
            self.x = -self.hitbox_offset_x
        elif self.x + self.hitbox_offset_x + self.hitbox_width > map_width:
            self.x = map_width - self.hitbox_width - self.hitbox_offset_x

        if self.y + self.hitbox_offset_y < 0:
            self.y = -self.hitbox_offset_y
        elif self.y + self.hitbox_offset_y + self.hitbox_height > map_height:
            self.y = map_height - self.hitbox_height - self.hitbox_offset_y

        # True = dentro, False = tocó borde
        return (self.x == old_x and self.y == old_y)


    def toggle_weapon(self):
        self.is_armed = not self.is_armed
