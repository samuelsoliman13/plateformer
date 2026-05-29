import pygame
import socket
import threading
import json
import math
from constants import *
from shared import Player, Bullet, GameState, NetworkMessage

class GameClient:
    def __init__(self, server_host, server_port, player_name, player_color):
        self.server_host = server_host
        self.server_port = server_port
        self.player_name = player_name
        self.player_color = player_color
        
        self.socket = None
        self.player_id = None
        self.my_player = None
        self.players = {}
        self.platforms = []
        self.game_running = False
        self.connected = False
        self.lobby_players = {}
        self.chat_messages = []
        self.chat_input = ""
        self.start_notice = ""
        self.start_button_rect = None
        
        self.lock = threading.Lock()
        
        # Input client
        self.keys_pressed = {}
        self.mouse_pos = (0, 0)
        self.last_shoot_time = 0
        
    def connect(self):
        """Se connecte au serveur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Définir le timeout pour éviter de bloquer indéfiniment
            self.socket.settimeout(10)  # 10 secondes
            # Réutiliser l'adresse en cas de reconnexion rapide
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            print(f"[CLIENT] Tentative de connexion à {self.server_host}:{self.server_port}...")
            self.socket.connect((self.server_host, self.server_port))
            self.socket.settimeout(None)  # Retirer le timeout après connexion réussie
            self.connected = True
            print(f"[CLIENT] Connecté à {self.server_host}:{self.server_port}")
            
            # Envoyer les infos de jointure
            msg = NetworkMessage("join", {
                'name': self.player_name,
                'color': self.player_color
            })
            self.socket.send((msg.to_json() + "\n").encode())
            
            # Thread de réception
            threading.Thread(target=self._receive_messages, daemon=True).start()
            
            return True
        except socket.timeout:
            print(f"[CLIENT] Erreur de connexion: Timeout - Le serveur n'a pas répondu dans les 10 secondes")
            print(f"[CLIENT] Vérifiez que le serveur est lancé sur {self.server_host}:{self.server_port}")
            self.connected = False
            return False
        except ConnectionRefusedError:
            print(f"[CLIENT] Erreur de connexion: Connexion refusée")
            print(f"[CLIENT] Le serveur n'écoute pas sur {self.server_host}:{self.server_port}")
            self.connected = False
            return False
        except Exception as e:
            print(f"[CLIENT] Erreur de connexion: {e}")
            print(f"[CLIENT] Impossible de joindre {self.server_host}:{self.server_port}")
            self.connected = False
            return False
    
    def _receive_messages(self):
        """Reçoit les messages du serveur"""
        buffer = ""
        try:
            while self.connected:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._process_server_message(line)
        except Exception as e:
            print(f"[CLIENT] Erreur réception: {e}")
        finally:
            self.connected = False
    
    def _process_server_message(self, message_str):
        """Traite un message du serveur"""
        try:
            msg = NetworkMessage.from_json(message_str)
            
            if msg.msg_type == "join_success":
                self._handle_join_success(msg.data)
            elif msg.msg_type == "join_failed":
                print(f"[CLIENT] Échec jointure: {msg.data.get('reason')}")
                self.connected = False
            elif msg.msg_type == "game_started":
                self._handle_game_started(msg.data)
            elif msg.msg_type == "state_update":
                self._handle_state_update(msg.data)
            elif msg.msg_type == "lobby_state":
                self._handle_lobby_state(msg.data)
            elif msg.msg_type == "chat_message":
                self._handle_chat_message(msg.data)
            elif msg.msg_type == "server_full":
                print("[CLIENT] Serveur plein!")
                self.connected = False
        except Exception as e:
            print(f"[CLIENT] Erreur traitement message: {e}")
    
    def _handle_join_success(self, data):
        """Traite la confirmation de jointure"""
        with self.lock:
            self.player_id = data['player_id']
            player_dict = data['player']
            self.my_player = Player(**player_dict)
            self.players[self.player_id] = player_dict
            
            # Recréer les rects des plateformes
            for plat_data in data.get('platforms', []):
                self.platforms.append(pygame.Rect(plat_data[0], plat_data[1], plat_data[2], plat_data[3]))
        
        print(f"[CLIENT] Jointure réussie! ID: {self.player_id}")

    def _handle_game_started(self, data):
        """Affiche une notification de lancement de partie"""
        with self.lock:
            self.start_notice = data.get('notice', '')

    def _handle_lobby_state(self, data):
        """Met à jour l'état du lobby"""
        with self.lock:
            self.lobby_players = data.get('players', {})
            self.chat_messages = data.get('chat_messages', [])[-20:]

    def _handle_chat_message(self, data):
        """Ajoute un message de chat reçu"""
        message = data.get('message')
        if not message:
            return
        with self.lock:
            self.chat_messages.append(message)
            self.chat_messages = self.chat_messages[-20:]

    def send_chat_message(self, text):
        if not self.connected or not text.strip():
            return
        msg = NetworkMessage("chat_message", {'text': text.strip()})
        try:
            self.socket.send((msg.to_json() + "\n").encode())
        except:
            pass
    
    def _handle_state_update(self, data):
        """Met à jour l'état du jeu"""
        state = data.get('state', {})
        with self.lock:
            self.players = state.get('players', {})
            self.bullets = state.get('bullets', {})
    
    def send_input(self, vel_x, jump):
        """Envoie les inputs du joueur"""
        if not self.connected:
            return
        
        msg = NetworkMessage("input", {
            'vel_x': vel_x,
            'jump': jump
        })
        try:
            self.socket.send((msg.to_json() + "\n").encode())
        except:
            pass
    
    def send_shoot(self):
        """Envoie un tir"""
        if not self.connected:
            return
        
        msg = NetworkMessage("shoot", {
            'mouse_x': self.mouse_pos[0],
            'mouse_y': self.mouse_pos[1]
        })
        try:
            self.socket.send((msg.to_json() + "\n").encode())
        except:
            pass
    
    def start_game(self):
        """Demande le démarrage du jeu"""
        if not self.connected:
            return
        
        msg = NetworkMessage("start_game", {})
        try:
            self.socket.send((msg.to_json() + "\n").encode())
        except:
            pass

class GameRenderer:
    def __init__(self, client):
        self.client = client
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Platformer Multijoueur")
        self.font_small = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 36)
        self.clock = pygame.time.Clock()
        self.lobby_screen = True
        
    def run(self):
        """Boucle de rendu"""
        running = True
        
        while running and self.client.connected:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.lobby_screen and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        self.client.chat_input = self.client.chat_input[:-1]
                    elif event.key == pygame.K_RETURN:
                        if self.client.chat_input.strip():
                            self.client.send_chat_message(self.client.chat_input)
                            self.client.chat_input = ""
                    elif event.unicode and event.unicode.isprintable():
                        self.client.chat_input += event.unicode
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.lobby_screen:
                    if self.client.start_button_rect and self.client.start_button_rect.collidepoint(event.pos):
                        with self.client.lock:
                            if self.client.player_id == 0:
                                self.client.start_game()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.lobby_screen:
                    self.client.send_shoot()
            
            if self.lobby_screen and self.client.game_running:
                self.lobby_screen = False
            
            if self.lobby_screen:
                self._render_lobby()
            else:
                self._render_game()
            
            self.clock.tick(FPS)
        
        pygame.quit()
    
    def _render_lobby(self):
        """Affiche le lobby"""
        self.screen.fill(UI_BG_COLOR)
        
        # Titre
        title = self.font_large.render("Lobby de jeu", True, TEXT_COLOR)
        self.screen.blit(title, (50, 30))
        
        # Panel des joueurs
        panel_rect = pygame.Rect(50, 100, 400, 500)
        pygame.draw.rect(self.screen, (240, 240, 240), panel_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, panel_rect, 2)
        players_title = self.font_small.render("Joueurs connectés", True, TEXT_COLOR)
        self.screen.blit(players_title, (60, 110))
        
        y = 150
        with self.client.lock:
            lobby_players = self.client.lobby_players or self.client.players
            for pid, player_dict in lobby_players.items():
                player_name = player_dict['name']
                player_color_str = player_dict['color']
                color_tuple = PLAYER_COLORS.get(player_color_str, (128, 128, 128))
                pygame.draw.rect(self.screen, color_tuple, (70, y, 30, 30))
                text = self.font_small.render(f"{player_name} ({player_color_str})", True, TEXT_COLOR)
                self.screen.blit(text, (110, y + 5))
                y += 45
                if y > panel_rect.bottom - 40:
                    break
        
        # Panel chat
        chat_rect = pygame.Rect(500, 100, 440, 470)
        pygame.draw.rect(self.screen, (240, 240, 240), chat_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, chat_rect, 2)
        chat_title = self.font_small.render("Chat du lobby", True, TEXT_COLOR)
        self.screen.blit(chat_title, (510, 110))
        
        with self.client.lock:
            messages = list(self.client.chat_messages)[-12:]
        chat_y = 150
        for msg in messages:
            color_tuple = PLAYER_COLORS.get(msg.get('color', ''), (100, 100, 100))
            sender_text = self.font_small.render(f"{msg.get('sender')}: ", True, color_tuple)
            self.screen.blit(sender_text, (520, chat_y))
            message_text = self.font_small.render(msg.get('text', ''), True, TEXT_COLOR)
            self.screen.blit(message_text, (520 + sender_text.get_width(), chat_y))
            chat_y += 30
            if chat_y > chat_rect.bottom - 60:
                break
        
        input_rect = pygame.Rect(500, 590, 440, 40)
        pygame.draw.rect(self.screen, (255, 255, 255), input_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, input_rect, 2)
        input_text = self.font_small.render(self.client.chat_input or "Tapez un message...", True, TEXT_COLOR)
        self.screen.blit(input_text, (510, 600))
        
        with self.client.lock:
            is_host = self.client.player_id == 0
            start_notice = self.client.start_notice
        if is_host:
            button_color = (0, 120, 0)
            self.client.start_button_rect = pygame.Rect(60, HEIGHT - 160, 260, 50)
            pygame.draw.rect(self.screen, button_color, self.client.start_button_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, self.client.start_button_rect, 2)
            button_text = self.font_small.render("START (host seulement)", True, (255, 255, 255))
            self.screen.blit(button_text, (self.client.start_button_rect.x + 10, self.client.start_button_rect.y + 14))
            instr = self.font_small.render("Cliquez sur START pour envoyer l'annonce de démarrage.", True, TEXT_COLOR)
        else:
            self.client.start_button_rect = None
            instr = self.font_small.render("En attente du host...", True, TEXT_COLOR)
        self.screen.blit(instr, (WIDTH // 2 - instr.get_width() // 2, HEIGHT - 100))

        if start_notice:
            notice_rect = pygame.Rect(500, HEIGHT - 160, 440, 80)
            pygame.draw.rect(self.screen, (255, 230, 230), notice_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, notice_rect, 2)
            notice_text = self.font_small.render(start_notice, True, (120, 0, 0))
            self.screen.blit(notice_text, (notice_rect.x + 10, notice_rect.y + 10))

        pygame.display.flip()
    
    def _render_game(self):
        """Affiche le jeu"""
        # Gestion des inputs
        keys = pygame.key.get_pressed()
        vel_x = 0
        jump = False
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vel_x = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vel_x = PLAYER_SPEED
        if keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]:
            jump = True
        
        self.client.mouse_pos = pygame.mouse.get_pos()
        
        # Envoyer les inputs
        self.client.send_input(vel_x, jump)
        
        # Rendu
        self.screen.fill(BG_COLOR)
        
        # Plateformes
        for plat in self.client.platforms:
            pygame.draw.rect(self.screen, PLATFORM_COLOR, plat)
        
        # Balles
        with self.client.lock:
            for bullet_dict in self.client.bullets.values():
                bullet = Bullet(**bullet_dict)
                pygame.draw.circle(self.screen, (0, 0, 0), (int(bullet.x), int(bullet.y)), BULLET_SIZE)
            
            # Joueurs
            for pid, player_dict in self.client.players.items():
                player = Player(**player_dict)
                if not player.alive:
                    continue
                
                color_tuple = PLAYER_COLORS.get(player.color, (128, 128, 128))
                
                # Tête
                head_rect = player.get_head_rect()
                pygame.draw.rect(self.screen, color_tuple, (player.x, player.y, PLAYER_WIDTH, HEAD_HEIGHT))
                
                # Corps
                body_rect = player.get_rect()
                pygame.draw.rect(self.screen, color_tuple, body_rect)
                
                # Contour si c'est notre joueur
                with self.client.lock:
                    is_my_player = (pid == self.client.player_id)
                if is_my_player:
                    pygame.draw.rect(self.screen, (255, 255, 255), (int(player.x), int(player.y), PLAYER_WIDTH, PLAYER_HEIGHT), 2)
                
                # Afficher les infos du joueur
                hp_text = self.font_small.render(f"{player.name} ({player.hp}HP)", True, TEXT_COLOR)
                self.screen.blit(hp_text, (player.x, player.y - 30))
        
        # Viseur à la souris
        mx, my = pygame.mouse.get_pos()
        pygame.draw.circle(self.screen, (255, 0, 0), (mx, my), 5, 1)
        
        # Afficher le cooldown de tir
        if self.client.my_player:
            cooldown_text = self.font_small.render(f"Tir: {'Prêt' if self.client.my_player.shoot_cooldown <= 0 else chr(int(self.client.my_player.shoot_cooldown))}",
                                                    True, TEXT_COLOR)
            self.screen.blit(cooldown_text, (10, 10))
        
        pygame.display.flip()

def run_game(server_host, server_port, player_name, player_color):
    """Fonction utilitaire pour lancer le jeu client"""
    pygame.init()
    
    client = GameClient(server_host, server_port, player_name, player_color)
    
    if not client.connect():
        print("Impossible de se connecter au serveur")
        return
    
    # Attendre la confirmation de jointure (avec lock pour éviter race condition)
    import time
    timeout = time.time() + 10
    while time.time() < timeout:
        with client.lock:
            if client.player_id is not None:
                break
        time.sleep(0.05)
    
    with client.lock:
        if client.player_id is None:
            print("[ERREUR] Timeout de connexion au serveur")
            return
    
    renderer = GameRenderer(client)
    renderer.run()
