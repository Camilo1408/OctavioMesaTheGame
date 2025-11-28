import os
import pygame


class SoundManager:
    """Gestor centralizado de todos los sonidos del juego."""
    
    def __init__(self):
        """Inicializa el gestor y carga todos los sonidos."""
        self.sounds = {}
        self.sound_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds")
        
        # Cargar todos los sonidos
        self._load_sounds()
        
    def _load_sounds(self):
        """Carga todos los archivos de audio."""
        # Definir todos los sonidos a cargar con sus volúmenes
        sound_files = {
            # Diablo
            "diablo_attack": ("diablo-attack.wav", 0.4),
            "diablo_death": ("diablo-death.wav", 0.4),
            "diablo_hurt": ("diablo-hurt.mp3", 0.4),
            "diablo_roar": ("diablo-roar.mp3", 0.9),
            
            # Octavio (jugador)
            "octavio_attack": ("octavio-attack.mp3", 0.1),
            "octavio_death": ("octavio-death.mp3", 0.8),
            "octavio_hurt": ("octavio-hurt.mp3", 0.1),
            
            # Orcos (enemigos)
            "orc_attack": ("orc-attack.mp3", 0.1),
            "orc_death": ("orc-death.mp3", 0.3),
            "orc_hurt": ("orc-hurt.mp3", 0.1),
        }
        
        # Cargar cada sonido
        for key, (filename, volume) in sound_files.items():
            file_path = os.path.join(self.sound_path, filename)
            try:
                sound = pygame.mixer.Sound(file_path)
                sound.set_volume(volume)
                self.sounds[key] = sound
                print(f"[SOUND] Cargado: {filename}")
            except pygame.error as e:
                print(f"[WARN] No se pudo cargar {filename}: {e}")
                self.sounds[key] = None
    
    def play(self, sound_key):
        """
        Reproduce un sonido por su clave.
        
        Args:
            sound_key: Clave del sonido (ej: "octavio_attack", "diablo_roar")
        """
        if sound_key in self.sounds and self.sounds[sound_key] is not None:
            self.sounds[sound_key].play()
        else:
            print(f"[WARN] Sonido '{sound_key}' no encontrado o no cargado")
    
    def stop(self, sound_key):
        """Detiene un sonido específico."""
        if sound_key in self.sounds and self.sounds[sound_key] is not None:
            self.sounds[sound_key].stop()
    
    def stop_all(self):
        """Detiene todos los sonidos."""
        pygame.mixer.stop()
    
    def set_volume(self, sound_key, volume):
        """
        Ajusta el volumen de un sonido específico.
        
        Args:
            sound_key: Clave del sonido
            volume: Volumen entre 0.0 y 1.0
        """
        if sound_key in self.sounds and self.sounds[sound_key] is not None:
            self.sounds[sound_key].set_volume(volume)
    
    def set_master_volume(self, volume):
        """
        Ajusta el volumen maestro de todos los sonidos.
        
        Args:
            volume: Volumen entre 0.0 y 1.0
        """
        for sound in self.sounds.values():
            if sound is not None:
                current_volume = sound.get_volume()
                sound.set_volume(current_volume * volume)