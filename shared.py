import json
import pygame
from dataclasses import dataclass, field, asdict
from typing import List, Dict
from constants import *

@dataclass
class Player:
    """Représente un joueur dans le jeu"""
    player_id: int
    name: str
    color: str
    x: float
    y: float
    vel_x: float = 0
    vel_y: float = 0
    hp: int = MAX_HP
    alive: bool = True
    score: int = 0
    respawn_timer: int = 0
    shooting: bool = False
    shoot_cooldown: int = 0
    invincibility_frames: int = 0
    
    def to_dict(self):
        return asdict(self)
    
    @staticmethod
    def from_dict(data):
        return Player(**data)
    
    def get_rect(self):
        """Retourne le rect du corps du joueur"""
        return pygame.Rect(self.x, self.y + HEAD_HEIGHT, PLAYER_WIDTH, PLAYER_HEIGHT - HEAD_HEIGHT)
    
    def get_head_rect(self):
        """Retourne le rect de la tête"""
        return pygame.Rect(self.x, self.y, PLAYER_WIDTH, HEAD_HEIGHT)
    
    def get_full_rect(self):
        """Retourne le rect complet du joueur"""
        return pygame.Rect(self.x, self.y, PLAYER_WIDTH, PLAYER_HEIGHT)

@dataclass
class Bullet:
    """Représente un projectile"""
    bullet_id: int
    owner_id: int
    x: float
    y: float
    vel_x: float
    vel_y: float
    age: int = 0
    
    def to_dict(self):
        return asdict(self)
    
    @staticmethod
    def from_dict(data):
        return Bullet(**data)
    
    def get_rect(self):
        return pygame.Rect(self.x - BULLET_SIZE // 2, self.y - BULLET_SIZE // 2, BULLET_SIZE, BULLET_SIZE)

@dataclass
class GameState:
    """État du jeu à synchroniser entre serveur et clients"""
    players: Dict[int, dict] = field(default_factory=dict)
    bullets: Dict[int, dict] = field(default_factory=dict)
    game_running: bool = False
    
    def to_json(self):
        return json.dumps({
            'players': self.players,
            'bullets': self.bullets,
            'game_running': self.game_running
        })
    
    @staticmethod
    def from_json(data):
        obj = json.loads(data)
        return GameState(
            players=obj.get('players', {}),
            bullets=obj.get('bullets', {}),
            game_running=obj.get('game_running', False)
        )

# Messages réseau
@dataclass
class NetworkMessage:
    """Structure pour les messages réseau"""
    msg_type: str  # "join", "input", "shoot", "state", "player_dead", etc.
    data: dict = field(default_factory=dict)
    
    def to_json(self):
        return json.dumps({
            'msg_type': self.msg_type,
            'data': self.data
        })
    
    @staticmethod
    def from_json(data):
        obj = json.loads(data)
        return NetworkMessage(
            msg_type=obj.get('msg_type'),
            data=obj.get('data', {})
        )
