import pygame

class SpriteSheet:
    def __init__(self, image_path):
        self.sprite_sheet = pygame.image.load(image_path).convert_alpha()

    def get_sprite(self, x, y, width, height):
        # Create a new blank image with transparency
        sprite = pygame.Surface((width, height), pygame.SRCALPHA)
        # Copy the sprite from the sheet onto the surface
        sprite.blit(self.sprite_sheet, (0, 0), (x, y, width, height))
        return sprite