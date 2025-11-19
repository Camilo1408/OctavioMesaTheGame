import os
import pygame
from graphics.sprite_sheet import SpriteSheet
from core.settings import MAP_WIDTH_PX, MAP_HEIGHT_PX, PLAYER_MAX_HEALTH, BANDAGE_HEAL_AMOUNT, MAX_BANDAGES



class Player:
    def __init__(self, x, y, sprite_path=None, sprite_size=64, unarmed_row=39, armed_row=10, frames_per_direction=None, row_index_base=0):
        """Player with configurable sprite sheet layout."""
        self.max_health = PLAYER_MAX_HEALTH
        self.health = self.max_health

        # --- Sprint 4: inventario simple de vendas ---
        self.bandages = 0

        # --- Sprint 4: contador de bajas para habilidades especiales ---
        self.special_kill_counter = 0

        self.x = x
        self.y = y
        self.width = sprite_size
        self.height = sprite_size
        self.speed = 5
        self.is_armed = False
        self.is_attacking = False
        self.attack_duration = 0.35
        self.attack_timer = 0.0
        self.attack_damage = 25   # puedes tunear esto

                # --- Sprint 2: stats base de combate ---
        from core.settings import (
            FIST_BASE_DAMAGE, MACHETE_BASE_DAMAGE,
            FIST_BASE_RANGE, MACHETE_BASE_RANGE,
        )

        # Daños base de cada arma
        self.base_attack_damage_unarmed = FIST_BASE_DAMAGE
        self.base_attack_damage_armed = MACHETE_BASE_DAMAGE

        # Rango base de cada arma (multiplicador sobre la hitbox)
        self.base_range_unarmed = FIST_BASE_RANGE
        self.base_range_armed = MACHETE_BASE_RANGE

        # Multiplicador de rango actual (se recalcula según arma y stats)
        self.attack_range_multiplier = self.base_range_unarmed

                # --- Sprint 3: progresión y árbol de habilidades ---
        from core.settings import PLAYER_XP_BASE

        # Nivel general del jugador
        self.level = 1
        self.xp = 0
        self.xp_to_next = PLAYER_XP_BASE

        # Niveles de cada stat (1 a 3)
        self.move_level = 1
        self.strength_level = 1
        self.range_level = 1
        self.resistance_level = 1

        # Stats base de movimiento y defensa
        self.base_speed = self.speed          # 5, de arriba
        self.damage_taken_multiplier = 1.0    # 1.0 = daño normal

        # Inicializar stats derivados
        self.recalculate_stats()


        self.movement = {'up': False, 'down': False, 'left': False, 'right': False}

        # Hitbox más pequeña (centrada)
        self.hitbox_width = int(self.width * 0.5) # 50% del ancho → ~32 px
        self.hitbox_height = int(self.height * 0.75)  # 75% de la altura → ~48 px
        self.hitbox_offset_x = (self.width - self.hitbox_width) // 2
        self.hitbox_offset_y = self.height - self.hitbox_height


        # Sprite sheet setup
        if sprite_path is None:
            sprite_path = os.path.join('..','assets', 'sprites', 'Octavio Mesa.png')
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
        map_width = MAP_WIDTH_PX
        map_height = MAP_HEIGHT_PX
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
        self.recalculate_stats() 

        # Actualizar daño y rango según arma actual
        if self.is_armed:
            base_damage = self.base_attack_damage_armed
            base_range = self.base_range_armed
        else:
            base_damage = self.base_attack_damage_unarmed
            base_range = self.base_range_unarmed

        self.attack_damage = base_damage
        self.attack_range_multiplier = base_range

    def recalculate_stats(self):
        """Recalcula velocidad, daño, rango y resistencia según niveles y arma."""
        # --- MOVIMIENTO ---
        # +15% de velocidad por nivel de movimiento
        speed_bonus = 0.15 * (self.move_level - 1)
        self.speed = self.base_speed * (1.0 + speed_bonus)

        # --- DAÑO Y RANGO BASE SEGÚN ARMA ACTUAL ---
        if self.is_armed:
            base_damage = self.base_attack_damage_armed
            base_range = self.base_range_armed
        else:
            base_damage = self.base_attack_damage_unarmed
            base_range = self.base_range_unarmed

        # --- FUERZA ---
        # +20% daño por nivel de fuerza
        strength_bonus = 0.20 * (self.strength_level - 1)
        self.attack_damage = base_damage * (1.0 + strength_bonus)

        # --- RANGO ---
        # +15% rango por nivel de rango
        range_bonus = 0.15 * (self.range_level - 1)
        self.attack_range_multiplier = base_range * (1.0 + range_bonus)

        # --- RESISTENCIA ---
        # -15% daño recibido por nivel de resistencia
        resistance_bonus = 0.15 * (self.resistance_level - 1)
        self.damage_taken_multiplier = max(0.4, 1.0 - resistance_bonus)


    def get_attack_hitbox(self):
        """Devuelve un Rect con el área de impacto del ataque (o None si no hay ataque activo)."""
        if not self.is_attacking:
            return None

        import pygame

        # Usamos la hitbox reducida como base
        base_rect = pygame.Rect(
            self.x + self.hitbox_offset_x,
            self.y + self.hitbox_offset_y,
            self.hitbox_width,
            self.hitbox_height,
        )

        range_mult = getattr(self, "attack_range_multiplier", 1.0)
        atk_width = int(self.hitbox_width * range_mult)
        atk_height = int(self.hitbox_height * range_mult) 

        if self.facing == 'up':
            return pygame.Rect(
                base_rect.centerx - atk_width // 2,
                base_rect.top - atk_height,
                atk_width,
                atk_height,
            )
        elif self.facing == 'down':
            return pygame.Rect(
                base_rect.centerx - atk_width // 2,
                base_rect.bottom,
                atk_width,
                atk_height,
            )
        elif self.facing == 'left':
            return pygame.Rect(
                base_rect.left - atk_width,
                base_rect.centery - atk_height // 2,
                atk_width,
                atk_height,
            )
        elif self.facing == 'right':
            return pygame.Rect(
                base_rect.right,
                base_rect.centery - atk_height // 2,
                atk_width,
                atk_height,
            )
        return None

    def take_damage(self, amount: float):
        # Aplicar resistencia (daño reducido)
        factor = getattr(self, "damage_taken_multiplier", 1.0)
        self.health -= amount * factor
        if self.health < 0:
            self.health = 0

    def use_bandage(self):
        """Usa una venda para curarse si es posible."""
        if self.bandages <= 0:
            return  # no hay vendas

        if self.health >= self.max_health:
            return  # ya está full

        self.health = min(self.max_health, self.health + BANDAGE_HEAL_AMOUNT)
        self.bandages -= 1

    def reset_special_counter(self):
        self.special_kill_counter = 0

    def can_use_special_frontal(self):
        from core.settings import SPECIAL_FRONTAL_KILLS
        return self.special_kill_counter >= SPECIAL_FRONTAL_KILLS

    def can_use_special_spiral(self):
        from core.settings import SPECIAL_SPIRAL_KILLS
        return self.special_kill_counter >= SPECIAL_SPIRAL_KILLS
