import pygame
from core.settings import MAP_WIDTH_PX, MAP_HEIGHT_PX


class Minimap:
    def __init__(self, screen_width, screen_height, minimap_size):
        """
        Inicializa el minimapa.
        
        Args:
            screen_width: Ancho de la pantalla
            screen_height: Alto de la pantalla
            minimap_size: Tamaño del minimapa (ancho y alto)
        """
        self.minimap_size = minimap_size
        self.margin = 15  # Margen desde el borde de la pantalla
        
        # Posición del minimapa (abajo a la derecha)
        self.x = screen_width - minimap_size - self.margin
        self.y = screen_height - minimap_size - self.margin
        
        # Superficie del minimapa
        self.surface = pygame.Surface((minimap_size, minimap_size), pygame.SRCALPHA)
        
        # Factores de escala (mapa del mundo -> minimapa)
        self.scale_x = minimap_size / MAP_WIDTH_PX
        self.scale_y = minimap_size / MAP_HEIGHT_PX
        
        # Colores
        self.bg_color = (30, 30, 40, 200)  # Fondo semitransparente
        self.border_color = (255, 255, 255, 255)  # Borde blanco
        self.player_color = (0, 255, 0, 255)  # Verde para jugador
        self.enemy_color = (255, 50, 50, 255)  # Rojo para enemigos
        self.boss_color = (255, 150, 0, 255)  # Naranja para jefe
        self.item_color = (255, 215, 0, 255)  # Dorado para ítems
        
    def world_to_minimap(self, world_x, world_y):
        """Convierte coordenadas del mundo a coordenadas del minimapa."""
        mini_x = int(world_x * self.scale_x)
        mini_y = int(world_y * self.scale_y)
        return mini_x, mini_y
    
    def draw(self, screen, player, enemies, items=None):
        """
        Dibuja el minimapa en la pantalla.
        
        Args:
            screen: Superficie de pygame donde dibujar
            player: Objeto del jugador
            enemies: Lista de enemigos
        """
        # Limpiar superficie
        self.surface.fill(self.bg_color)
        
        # Dibujar borde
        pygame.draw.rect(
            self.surface,
            self.border_color,
            (0, 0, self.minimap_size, self.minimap_size),
            2
        )
        
        # Dibujar enemigos primero (para que el jugador quede encima)
        for enemy in enemies:
            if not enemy.alive:
                continue
                
            # Posición del enemigo en el minimapa
            enemy_x = enemy.x + enemy.width // 2
            enemy_y = enemy.y + enemy.height // 2
            mini_x, mini_y = self.world_to_minimap(enemy_x, enemy_y)
            
            # Determinar si es jefe
            is_boss = hasattr(enemy, "is_boss") and enemy.is_boss
            color = self.boss_color if is_boss else self.enemy_color
            size = 5 if is_boss else 3
            
            # Dibujar punto del enemigo
            pygame.draw.circle(
                self.surface,
                color,
                (mini_x, mini_y),
                size
            )
        # Dibujar ítems (antes del jugador para que quede debajo)
        if items:
            for item in items:
                if item.collected:
                    continue
                
                # Posición del ítem en el minimapa
                item_x = item.x + item.width // 2
                item_y = item.y + item.height // 2
                mini_x, mini_y = self.world_to_minimap(item_x, item_y)
                
                # Dibujar punto del ítem con efecto pulsante
                import math
                pulse = math.sin(pygame.time.get_ticks() / 300.0)
                size = int(4 + pulse * 1.5)  # tamaño entre 2.5 y 5.5
                
                # Borde negro
                pygame.draw.circle(
                    self.surface,
                    (0, 0, 0, 255),
                    (mini_x, mini_y),
                    size + 1
                )
                # Centro dorado
                pygame.draw.circle(
                    self.surface,
                    self.item_color,
                    (mini_x, mini_y),
                    size
                )
        
        # Dibujar jugador
        player_x = player.x + player.width // 2
        player_y = player.y + player.height // 2
        mini_x, mini_y = self.world_to_minimap(player_x, player_y)
        
        # Dibujar punto del jugador (más grande y con borde)
        pygame.draw.circle(
            self.surface,
            (0, 0, 0, 255),  # Borde negro
            (mini_x, mini_y),
            5
        )
        pygame.draw.circle(
            self.surface,
            self.player_color,
            (mini_x, mini_y),
            4
        )
        
        # Indicador de dirección del jugador
        direction_offsets = {
            'up': (0, -6),
            'down': (0, 6),
            'left': (-6, 0),
            'right': (6, 0)
        }
        
        if hasattr(player, 'facing') and player.facing in direction_offsets:
            dx, dy = direction_offsets[player.facing]
            pygame.draw.line(
                self.surface,
                self.player_color,
                (mini_x, mini_y),
                (mini_x + dx, mini_y + dy),
                2
            )
        
        # Dibujar el minimapa en la pantalla
        screen.blit(self.surface, (self.x, self.y))
        
        # Etiqueta opcional
        font = pygame.font.SysFont("arial", 12)
        label = font.render("Mapa", True, (200, 200, 200))
        screen.blit(label, (self.x + 5, self.y - 18))