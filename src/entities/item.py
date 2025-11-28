import pygame
import math
import os


class Item:
    """Clase base para ítems coleccionables."""
    
    def __init__(self, x, y, item_type="aguardiente"):
        self.x = x
        self.y = y
        self.item_type = item_type
        self.width = 32
        self.height = 32
        self.alive = True  # Para mantener compatibilidad con sistema de entidades
        self.collected = False
        
        # Animación de flotación
        self.float_offset = 0.0
        self.float_speed = 2.0  # velocidad del movimiento
        self.float_amplitude = 8  # píxeles arriba/abajo
        
        # Cargar sprite
        sprite_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "assets", 
            "sprites", 
            "Aguardiente.png"
        )
        try:
            self.image = pygame.image.load(sprite_path).convert_alpha()
            # Escalar a tamaño deseado
            self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except Exception as e:
            print(f"[WARN] No se pudo cargar Aguardiente.png: {e}")
            # Imagen de respaldo (cuadrado verde)
            self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.image.fill((0, 255, 0, 200))
    
    @property
    def rect(self):
        """Hitbox para colisión con el jugador."""
        return pygame.Rect(int(self.x), int(self.y + self.float_offset), self.width, self.height)
    
    def update(self, dt):
        """Actualiza la animación de flotación."""
        if self.collected:
            return
        
        # Movimiento sinusoidal arriba/abajo
        self.float_offset = math.sin(pygame.time.get_ticks() / 1000.0 * self.float_speed) * self.float_amplitude
    
    def collect(self, player):
        """Aplica el efecto del ítem al jugador."""
        if self.collected:
            return False
        
        self.collected = True
        self.alive = False
        
        # Aplicar efecto de inmunidad
        player.activate_immunity(duration=10.0)
        
        return True
    
    def draw(self, screen, camera_offset):
        """Dibuja el ítem con su animación de flotación."""
        if self.collected:
            return
        
        pos_x = self.x - camera_offset[0]
        pos_y = self.y + self.float_offset - camera_offset[1]
        
        screen.blit(self.image, (pos_x, pos_y))
        
        # Efecto de brillo/aura opcional
        glow_surface = pygame.Surface((self.width + 8, self.height + 8), pygame.SRCALPHA)
        alpha = int(100 + 50 * math.sin(pygame.time.get_ticks() / 200.0))
        pygame.draw.circle(
            glow_surface,
            (255, 255, 150, alpha),
            (glow_surface.get_width() // 2, glow_surface.get_height() // 2),
            self.width // 2 + 4,
            3
        )
        screen.blit(glow_surface, (pos_x - 4, pos_y - 4))