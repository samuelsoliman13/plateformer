import socket
import json
import threading
import time
from typing import Dict, List
import math
import pygame
from constants import *
from shared import Player, Bullet, GameState, NetworkMessage

# Initialiser pygame (sans afficher de fenêtre)
pygame.init(), pygame

class GameServer:
    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.server_socket = None
        self.clients = {}  # {client_id: {'socket': socket, 'player': Player}}
        self.players = {}  # {player_id: Player}
        self.bullets = {}  # {bullet_id: Bullet}
        self.chat_messages = []  # Liste des messages du lobby
        self.next_client_id = 0
        self.next_bullet_id = 0
        self.game_running = False
        self.max_players = MAX_PLAYERS
        self.platforms = self._create_platforms()
        self.lock = threading.Lock()
        
    def _create_platforms(self):
        """Crée les plateformes du jeu"""
        return [
            pygame.Rect(0, HEIGHT - 20, WIDTH, 20),  # Sol
            pygame.Rect(150, HEIGHT - 150, 250, 20),
            pygame.Rect(500, HEIGHT - 250, 250, 20),
            pygame.Rect(300, HEIGHT - 350, 200, 20),
            pygame.Rect(700, HEIGHT - 200, 200, 20),
        ]
    
    def start(self):
        """Démarre le serveur"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(5)
        print(f"[SERVEUR] Démarré sur {socket.gethostbyname('localhost')}:{self.port}")
        
        # Thread d'acceptation des connexions
        threading.Thread(target=self._accept_connections, daemon=True).start()
        
        # Thread de mise à jour du jeu
        threading.Thread(target=self._game_loop, daemon=True).start()
    
    def _accept_connections(self):
        """Accepte les connexions des clients"""
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                client_id = self.next_client_id
                self.next_client_id += 1
                
                if len(self.clients) >= self.max_players:
                    msg = NetworkMessage("server_full", {})
                    client_socket.send((msg.to_json() + "\n").encode())
                    client_socket.close()
                    continue
                
                print(f"[SERVEUR] Client {client_id} connecté depuis {addr}")
                with self.lock:
                    self.clients[client_id] = {
                        'socket': client_socket,
                        'player': None,
                        'address': addr,
                        'connected': True
                    }
                
                # Handler client dans un thread
                threading.Thread(target=self._handle_client, args=(client_id,), daemon=True).start()
            except Exception as e:
                print(f"[SERVEUR] Erreur connexion: {e}")
    
    def _handle_client(self, client_id):
        """Gère les messages d'un client"""
        try:
            client_info = self.clients[client_id]
            client_socket = client_info['socket']
            buffer = ""
            
            while True:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._process_message(client_id, line)
        except Exception as e:
            print(f"[SERVEUR] Erreur client {client_id}: {e}")
        finally:
            with self.lock:
                if client_id in self.clients:
                    # Retirer le joueur et nettoyer
                    if self.clients[client_id]['player']:
                        player_id = self.clients[client_id]['player'].player_id
                        if player_id in self.players:
                            del self.players[player_id]
                    del self.clients[client_id]
                    print(f"[SERVEUR] Client {client_id} déconnecté")
                    self._broadcast_lobby_state()
    
    def _process_message(self, client_id, message_str):
        """Traite un message d'un client"""
        try:
            msg = NetworkMessage.from_json(message_str)
            
            if msg.msg_type == "join":
                self._handle_join(client_id, msg.data)
            elif msg.msg_type == "input":
                self._handle_input(client_id, msg.data)
            elif msg.msg_type == "shoot":
                self._handle_shoot(client_id, msg.data)
            elif msg.msg_type == "chat_message":
                self._handle_chat_message(client_id, msg.data)
            elif msg.msg_type == "start_game":
                self._handle_start_game(client_id)
        except Exception as e:
            print(f"[SERVEUR] Erreur traitement message: {e}")
    
    def _handle_join(self, client_id, data):
        """Traite l'arrivée d'un nouveau joueur"""
        name = data.get('name', 'Player')
        color = data.get('color', 'Red')
        
        with self.lock:
            # Vérifier que la couleur est disponible
            taken_colors = [p.color for p in self.players.values()]
            if color in taken_colors:
                msg = NetworkMessage("join_failed", {'reason': 'Color taken'})
                self.clients[client_id]['socket'].send((msg.to_json() + "\n").encode())
                return
            
            # Créer le joueur
            player = Player(
                player_id=client_id,
                name=name,
                color=color,
                x=50.0 + len(self.players) * 150,
                y=HEIGHT - 200,
            )
            
            self.players[client_id] = player
            self.clients[client_id]['player'] = player
            
            # Confirmer au client
            msg = NetworkMessage("join_success", {
                'player_id': client_id,
                'player': player.to_dict(),
                'platforms': [list(p) for p in self.platforms]
            })
            self.clients[client_id]['socket'].send((msg.to_json() + "\n").encode())
            
            print(f"[SERVEUR] Joueur {name} ({color}) rejoint (ID: {client_id})")
            self._broadcast_lobby_state()
    
    def _handle_input(self, client_id, data):
        """Traite l'input d'un joueur"""
        with self.lock:
            if client_id in self.players:
                self.players[client_id].vel_x = data.get('vel_x', 0)
                if data.get('jump'):
                    if self._is_on_ground(self.players[client_id]):
                        self.players[client_id].vel_y = -JUMP_STRENGTH
    
    def _handle_shoot(self, client_id, data):
        """Traite un tir d'un joueur"""
        with self.lock:
            if client_id not in self.players:
                return
            
            player = self.players[client_id]
            if player.shoot_cooldown > 0 or not player.alive:
                return
            
            mouse_x = data.get('mouse_x', player.x)
            mouse_y = data.get('mouse_y', player.y)
            
            # Calculer la direction
            bullet_x = player.x + PLAYER_WIDTH // 2
            bullet_y = player.y + PLAYER_HEIGHT // 2
            
            dx = mouse_x - bullet_x
            dy = mouse_y - bullet_y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist > 0:
                dx /= dist
                dy /= dist
            
            # Créer la balle
            bullet = Bullet(
                bullet_id=self.next_bullet_id,
                owner_id=client_id,
                x=bullet_x,
                y=bullet_y,
                vel_x=dx * BULLET_SPEED,
                vel_y=dy * BULLET_SPEED
            )
            
            self.next_bullet_id += 1
            self.bullets[bullet.bullet_id] = bullet
            player.shoot_cooldown = SHOOT_COOLDOWN // (1000 // FPS)  # Convertir en frames
    
    def _handle_chat_message(self, client_id, data):
        """Traite un message de chat du lobby"""
        text = data.get('text', '').strip()
        if not text:
            return
        with self.lock:
            client_info = self.clients.get(client_id)
            if not client_info or not client_info['player']:
                return
            sender = client_info['player'].name
            color = client_info['player'].color
            chat_message = {
                'sender': sender,
                'color': color,
                'text': text
            }
            self.chat_messages.append(chat_message)
            self.chat_messages = self.chat_messages[-20:]
            self._broadcast_chat_message(chat_message)

    def _broadcast_chat_message(self, chat_message):
        msg = NetworkMessage("chat_message", {
            'message': chat_message
        })
        serialized = msg.to_json() + "\n"
        for client_info in self.clients.values():
            try:
                client_info['socket'].send(serialized.encode())
            except:
                pass

    def _broadcast_lobby_state(self):
        """Envoie l'état du lobby à tous les clients"""
        lobby_state = {
            'players': {pid: p.to_dict() for pid, p in self.players.items()},
            'chat_messages': self.chat_messages
        }
        msg = NetworkMessage("lobby_state", lobby_state)
        serialized = msg.to_json() + "\n"
        for client_info in self.clients.values():
            try:
                client_info['socket'].send(serialized.encode())
            except:
                pass

    def _handle_start_game(self, client_id=None):
        """Envoie un message de début de partie sans lancer le jeu réel"""
        with self.lock:
            if client_id is not None and client_id != 0:
                return
            msg = NetworkMessage("game_started", {
                'notice': "La partie va commencer - rien ne va se passer, le jeu est en cours de développement"
            })
            for client_info in self.clients.values():
                try:
                    client_info['socket'].send((msg.to_json() + "\n").encode())
                except:
                    pass
    
    def _is_on_ground(self, player):
        """Vérifie si un joueur est au sol"""
        rect = player.get_rect()
        rect.y += GROUND_CHECK_OFFSET
        for plat in self.platforms:
            if rect.colliderect(plat):
                return True
        return False
    
    def _game_loop(self):
        """Boucle principale du jeu sur le serveur"""
        clock = pygame.time.Clock()
        
        while True:
            with self.lock:
                if self.game_running:
                    # Mise à jour physique
                    self._update_game_state()
                    
                    # Synchroniser l'état avec les clients
                    self._broadcast_game_state()
            
            clock.tick(FPS)
    
    def _update_game_state(self):
        """Met à jour l'état du jeu (physique, collisions)"""
        # Mise à jour des joueurs
        for player in self.players.values():
            if not player.alive:
                continue
            
            # Physique
            player.vel_y += GRAVITY
            
            # Collision horizontale
            player.x += player.vel_x
            rect = player.get_full_rect()
            for plat in self.platforms:
                if rect.colliderect(plat):
                    if player.vel_x > 0:
                        player.x = plat.left - PLAYER_WIDTH
                    elif player.vel_x < 0:
                        player.x = plat.right
            
            # Collision verticale
            player.y += player.vel_y
            rect = player.get_full_rect()
            for plat in self.platforms:
                if rect.colliderect(plat):
                    if player.vel_y > 0:
                        player.y = plat.top - PLAYER_HEIGHT
                        player.vel_y = 0
                    elif player.vel_y < 0:
                        player.y = plat.bottom
                        player.vel_y = 0
            
            # Limites de la map
            if player.x < 0:
                player.x = 0
            if player.x + PLAYER_WIDTH > WIDTH:
                player.x = WIDTH - PLAYER_WIDTH
            if player.y > HEIGHT:
                player.alive = False
            
            # Refroidissement des tirs
            if player.shoot_cooldown > 0:
                player.shoot_cooldown -= 1
            
            # Invincibilité après hit
            if player.invincibility_frames > 0:
                player.invincibility_frames -= 1
        
        # Mise à jour des balles et collisions
        bullets_to_remove = []
        for bullet_id, bullet in list(self.bullets.items()):
            bullet.x += bullet.vel_x
            bullet.y += bullet.vel_y
            bullet.age += 1
            
            # Retirer si hors limites ou trop vieux
            if (bullet.x < 0 or bullet.x > WIDTH or 
                bullet.y < 0 or bullet.y > HEIGHT or 
                bullet.age > 300):
                bullets_to_remove.append(bullet_id)
                continue
            
            # Collisions avec les joueurs
            for player in self.players.values():
                if bullet.owner_id == player.player_id or not player.alive:
                    continue
                
                head_rect = player.get_head_rect()
                body_rect = player.get_rect()
                bullet_rect = bullet.get_rect()
                
                if bullet_rect.colliderect(head_rect):
                    # Coup à la tête
                    player.hp -= BULLET_DAMAGE_HEAD
                    bullets_to_remove.append(bullet_id)
                    if player.hp <= 0:
                        player.alive = False
                    player.invincibility_frames = INVINCIBILITY_FRAMES
                    break
                elif bullet_rect.colliderect(body_rect):
                    # Coup au corps
                    player.hp -= BULLET_DAMAGE_BODY
                    bullets_to_remove.append(bullet_id)
                    if player.hp <= 0:
                        player.alive = False
                    player.invincibility_frames = INVINCIBILITY_FRAMES
                    break
        
        for bid in bullets_to_remove:
            if bid in self.bullets:
                del self.bullets[bid]
    
    def _broadcast_game_state(self):
        """Envoie l'état du jeu à tous les clients"""
        game_state = GameState(
            players={pid: p.to_dict() for pid, p in self.players.items()},
            bullets={bid: b.to_dict() for bid, b in self.bullets.items()},
            game_running=self.game_running
        )
        
        msg = NetworkMessage("state_update", {
            'state': json.loads(game_state.to_json())
        })
        
        message = msg.to_json() + "\n"
        for client_info in self.clients.values():
            try:
                client_info['socket'].send(message.encode())
            except:
                pass

def run_server(port=DEFAULT_PORT):
    """Fonction utilitaire pour lancer le serveur"""
    server = GameServer(port)
    server.start()
    
    # Garder le serveur actif
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[SERVEUR] Arrêt...")
