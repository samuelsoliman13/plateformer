# Configuration du jeu
import pygame

WIDTH = 1000
HEIGHT = 700
FPS = 60

# Physique
GRAVITY = 0.8
PLAYER_SPEED = 5
JUMP_STRENGTH = 16
GROUND_CHECK_OFFSET = 2

# Combat
BULLET_SPEED = 10
BULLET_SIZE = 4
SHOOT_COOLDOWN = 500  # ms
BULLET_DAMAGE_BODY = 1
BULLET_DAMAGE_HEAD = 4
MAX_HP = 4

# Score
KILL_SCORE = 100
HEADSHOT_SCORE = 25
WIN_SCORE = 1000

# Respawn
RESPAWN_DELAY = 3 * FPS

# Durée d'invincibilité après tir sur la tête
INVINCIBILITY_FRAMES = 60

# Réseau
DEFAULT_PORT = 5000
MAX_PLAYERS = 4

# Couleurs disponibles
PLAYER_COLORS = {
    "Red": (255, 0, 0),
    "Blue": (0, 0, 255),
    "Green": (0, 255, 0),
    "Yellow": (255, 255, 0),
    "Purple": (255, 0, 255),
    "Cyan": (0, 255, 255),
}

# Couleurs UI
BG_COLOR = (135, 206, 235)
PLATFORM_COLOR = (110, 62, 10)
TEXT_COLOR = (0, 0, 0)
UI_BG_COLOR = (200, 200, 200)

# Tailles
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 60
HEAD_HEIGHT = 20  # Zone de la tête
