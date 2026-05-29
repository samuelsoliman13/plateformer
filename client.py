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
        self.bullets = {}
        self.platforms = []
        self.game_running = False
        self.connected = False
        self.lobby_players = {}
        self.chat_messages = []
        self.chat_input = ""
        self.start_notice = ""
        self.start_button_rect = None
        self.game_over = False
        self.winner_message = ""
        
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
            print("[CLIENT] Thread de réception démarré")
            while self.connected:
                data = self.socket.recv(4096).decode()
                if not data:
                    print("[CLIENT] _receive_messages: connexion fermée par le serveur")
                    break
                
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._process_server_message(line)
        except Exception as e:
            print(f"[CLIENT] Erreur réception: {e}")
        finally:
            print("[CLIENT] Thread de réception terminé")
            self.connected = False
    
    def _process_server_message(self, message_str):
        """Traite un message du serveur"""
        try:
            msg = NetworkMessage.from_json(message_str)
            print(f"[CLIENT] Reçu msg serveur: {msg.msg_type} {msg.data}")
            
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
            elif msg.msg_type == "game_over":
                self._handle_game_over(msg.data)
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
        print(f"[CLIENT] game_started reçu: {data}")
        with self.lock:
            self.game_running = True
            self.start_notice = data.get('notice', '')
            self.game_over = False
            self.winner_message = ""

    def _handle_game_over(self, data):
        print(f"[CLIENT] game_over reçu: {data}")
        with self.lock:
            self.game_running = False
            self.lobby_players = self.lobby_players or self.players
            self.game_over = True
            self.winner_message = f"Victoire de {data.get('winner_name', 'un joueur')} !"
            self.start_notice = ""
            self.lobby_screen = True

    def _handle_lobby_state(self, data):
        """Met à jour l'état du lobby"""
        with self.lock:
            players = data.get('players', {})
            self.lobby_players = {int(pid): p for pid, p in players.items()}
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
            self.players = {int(pid): p for pid, p in state.get('players', {}).items()}
            self.bullets = {int(bid): b for bid, b in state.get('bullets', {}).items()}
            if self.player_id in self.players:
                self.my_player = Player(**self.players[self.player_id])
    
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
            print("[CLIENT] Tentative de start_game alors que le client n'est pas connecté")
            return
        print("[CLIENT] Envoi de la requête start_game au serveur")
        msg = NetworkMessage("start_game", {})
        try:
            self.socket.send((msg.to_json() + "\n").encode())
            print("[CLIENT] Requête start_game envoyée")
        except Exception as e:
            print(f"[CLIENT] Erreur en envoyant start_game: {e}")

class GameRenderer:
    def __init__(self, client):
        self.client = client
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Platformer Multijoueur")
        self.font_small = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 36)
        self.clock = pygame.time.Clock()
        self.lobby_screen = True
        self._game_started_logged = False
        print("[CLIENT] Renderer initialisé, lobby_screen=True")
        
    def run(self):
        """Boucle de rendu"""
        running = True
        print("[CLIENT] Entrée dans la boucle renderer")

        while running and self.client.connected:
            try:
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
                        elif (event.key == pygame.K_s or event.key == pygame.K_SPACE) and not self.client.chat_input:
                            print("[CLIENT] Touche de démarrage pressée dans le lobby, tentative de démarrage")
                            with self.client.lock:
                                if self.client.player_id == 0:
                                    self.client.start_game()
                                    self.client.game_running = True
                                    self.lobby_screen = False
                        elif event.unicode and event.unicode.isprintable():
                            self.client.chat_input += event.unicode
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.lobby_screen:
                        print(f"[CLIENT] Clic lobby détecté à {event.pos}")
                        if self.client.start_button_rect and self.client.start_button_rect.collidepoint(event.pos):
                            print("[CLIENT] Bouton START cliqué")
                            with self.client.lock:
                                if self.client.player_id == 0:
                                    self.client.start_game()
                                    self.client.game_running = True
                                    self.lobby_screen = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.lobby_screen:
                        self.client.send_shoot()

                if self.client.game_over:
                    self.lobby_screen = True

                if self.lobby_screen and self.client.game_running:
                    self.lobby_screen = False

                if self.lobby_screen:
                    self._render_lobby()
                else:
                    if not self._game_started_logged:
                        print("[CLIENT] Passage en mode jeu")
                    self._render_game()

                self.clock.tick(FPS)
            except Exception as e:
                import traceback
                print(f"[CLIENT] Exception dans la boucle renderer: {e}")
                traceback.print_exc()
                running = False

        print(f"[CLIENT] Sortie boucle renderer connected={self.client.connected} running={running} lobby_screen={self.lobby_screen} game_running={self.client.game_running}")
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
                score = player_dict.get('score', 0)
                status = f"{player_name} ({player_color_str}) - {score} pts"
                text = self.font_small.render(status, True, TEXT_COLOR)
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
            instr = self.font_small.render("Cliquez sur START ou appuyez sur SPACE/S pour démarrer.", True, TEXT_COLOR)
        else:
            self.client.start_button_rect = None
            instr = self.font_small.render("En attente du host...", True, TEXT_COLOR)
        self.screen.blit(instr, (WIDTH // 2 - instr.get_width() // 2, HEIGHT - 100))

        if self.client.game_over and self.client.winner_message:
            winner_rect = pygame.Rect(500, HEIGHT - 160, 440, 80)
            pygame.draw.rect(self.screen, (230, 255, 230), winner_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, winner_rect, 2)
            winner_text = self.font_small.render(self.client.winner_message, True, (0, 120, 0))
            self.screen.blit(winner_text, (winner_rect.x + 10, winner_rect.y + 10))

        if start_notice:
            notice_rect = pygame.Rect(500, HEIGHT - 260, 440, 80)
            pygame.draw.rect(self.screen, (255, 230, 230), notice_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, notice_rect, 2)
            notice_text = self.font_small.render(start_notice, True, (120, 0, 0))
            self.screen.blit(notice_text, (notice_rect.x + 10, notice_rect.y + 10))

        pygame.display.flip()
    
    def _render_game(self):
        """Affiche le jeu"""
        if not self._game_started_logged:
            print(f"[CLIENT] _render_game() appelé players={len(self.client.players)} game_running={self.client.game_running} lobby_screen={self.lobby_screen}")
            self._game_started_logged = True
        try:
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
            all_players = []
            with self.client.lock:
                for bullet_dict in self.client.bullets.values():
                    try:
                        bullet = Bullet(**bullet_dict)
                        pygame.draw.circle(self.screen, (0, 0, 0), (int(bullet.x), int(bullet.y)), BULLET_SIZE)
                    except Exception as e:
                        print(f"[CLIENT] Erreur rendu bullet: {e}")
                
                # Joueurs
                for pid, player_dict in self.client.players.items():
                    try:
                        player = Player(**player_dict)
                        all_players.append(player)
                        if not player.alive:
                            continue
                        
                        color_tuple = PLAYER_COLORS.get(player.color, (128, 128, 128))
                        head_color = tuple(min(255, c + 80) for c in color_tuple)
                        
                        # Tête
                        head_rect = player.get_head_rect()
                        pygame.draw.rect(self.screen, head_color, head_rect)
                        pygame.draw.rect(self.screen, (0, 0, 0), head_rect, 1)
                        
                        # Corps
                        body_rect = player.get_rect()
                        pygame.draw.rect(self.screen, color_tuple, body_rect)
                        pygame.draw.rect(self.screen, (0, 0, 0), body_rect, 1)
                        
                        # Contour si c'est notre joueur
                        is_my_player = (pid == self.client.player_id)
                        if is_my_player:
                            pygame.draw.rect(self.screen, (255, 255, 255), (int(player.x), int(player.y), PLAYER_WIDTH, PLAYER_HEIGHT), 2)
                        
                        # Afficher les infos du joueur
                        hp_text = self.font_small.render(f"{player.name} ({player.hp}HP) - {player.score} pts", True, TEXT_COLOR)
                        self.screen.blit(hp_text, (player.x, player.y - 30))
                    except Exception as e:
                        print(f"[CLIENT] Erreur rendu joueur {pid}: {e}")

                # Affichage du tableau des scores et des respawns
                score_y = 50
                for player in all_players:
                    status = f"{player.name}: {player.score} pts"
                    if not player.alive:
                        seconds = max(0, player.respawn_timer // FPS)
                        status += f" - Respawn dans {seconds}s"
                    score_text = self.font_small.render(status, True, TEXT_COLOR)
                    self.screen.blit(score_text, (10, score_y))
                    score_y += 20

            # Debug overlay
            debug_text = self.font_small.render(
                f"GAME ACTIVE | joueurs={len(self.client.players)} | id={self.client.player_id}", True, (255, 0, 0)
            )
            self.screen.blit(debug_text, (10, 10))

            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(self.screen, (255, 0, 0), (mx, my), 5, 1)

            # Afficher le cooldown de tir
            if self.client.my_player:
                cooldown_text = self.font_small.render(
                    f"Tir: {'Prêt' if self.client.my_player.shoot_cooldown <= 0 else str(self.client.my_player.shoot_cooldown)}",
                    True, TEXT_COLOR)
                self.screen.blit(cooldown_text, (10, score_y + 10))

            pygame.display.flip()
        except Exception as e:
            import traceback
            print(f"[CLIENT] ERREUR DANS _render_game(): {e}")
            traceback.print_exc()
            raise

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


def _create_local_platforms():
    return [
        pygame.Rect(0, HEIGHT - 20, WIDTH, 20),
        pygame.Rect(150, HEIGHT - 150, 250, 20),
        pygame.Rect(500, HEIGHT - 250, 250, 20),
        pygame.Rect(300, HEIGHT - 350, 200, 20),
        pygame.Rect(700, HEIGHT - 200, 200, 20),
    ]


class SoloGame:
    def __init__(self, player_name, player_color):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Platformer Solo")
        self.font_small = pygame.font.Font(None, 24)
        self.clock = pygame.time.Clock()
        self.player = Player(
            player_id=0,
            name=player_name,
            color=player_color,
            x=50.0,
            y=HEIGHT - 200,
        )
        self.players = {0: self.player}
        self.bullets = {}
        self.platforms = _create_local_platforms()
        self.running = True
        self.mouse_pos = (0, 0)
        self.next_bullet_id = 0

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._shoot()
            keys = pygame.key.get_pressed()
            vel_x = 0
            jump = False
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                vel_x = -PLAYER_SPEED
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                vel_x = PLAYER_SPEED
            if keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]:
                jump = True
                if self._is_on_ground():
                    self.player.vel_y = -JUMP_STRENGTH
            self.player.vel_x = vel_x
            self.mouse_pos = pygame.mouse.get_pos()
            self._update_state()
            self._render()
            self.clock.tick(FPS)
        pygame.quit()

    def _is_on_ground(self):
        rect = self.player.get_rect()
        rect.y += GROUND_CHECK_OFFSET
        for plat in self.platforms:
            if rect.colliderect(plat):
                return True
        return False

    def _shoot(self):
        if self.player.shoot_cooldown > 0 or not self.player.alive:
            return
        bullet_x = self.player.x + PLAYER_WIDTH // 2
        bullet_y = self.player.y + PLAYER_HEIGHT // 2
        mx, my = self.mouse_pos
        dx = mx - bullet_x
        dy = my - bullet_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            dx /= dist
            dy /= dist
        bullet = Bullet(
            bullet_id=self.next_bullet_id,
            owner_id=0,
            x=bullet_x,
            y=bullet_y,
            vel_x=dx * BULLET_SPEED,
            vel_y=dy * BULLET_SPEED,
        )
        self.next_bullet_id += 1
        self.bullets[bullet.bullet_id] = bullet
        self.player.shoot_cooldown = SHOOT_COOLDOWN // (1000 // FPS)

    def _update_state(self):
        p = self.player
        if not p.alive:
            return
        p.vel_y += GRAVITY
        p.x += p.vel_x
        rect = p.get_full_rect()
        for plat in self.platforms:
            if rect.colliderect(plat):
                if p.vel_x > 0:
                    p.x = plat.left - PLAYER_WIDTH
                elif p.vel_x < 0:
                    p.x = plat.right
        p.y += p.vel_y
        rect = p.get_full_rect()
        for plat in self.platforms:
            if rect.colliderect(plat):
                if p.vel_y > 0:
                    p.y = plat.top - PLAYER_HEIGHT
                    p.vel_y = 0
                elif p.vel_y < 0:
                    p.y = plat.bottom
                    p.vel_y = 0
        if p.x < 0:
            p.x = 0
        if p.x + PLAYER_WIDTH > WIDTH:
            p.x = WIDTH - PLAYER_WIDTH
        if p.y > HEIGHT:
            p.alive = False
        if p.shoot_cooldown > 0:
            p.shoot_cooldown -= 1
        if p.invincibility_frames > 0:
            p.invincibility_frames -= 1
        bullets_to_remove = []
        for bullet_id, bullet in list(self.bullets.items()):
            bullet.x += bullet.vel_x
            bullet.y += bullet.vel_y
            bullet.age += 1
            if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT or bullet.age > 300:
                bullets_to_remove.append(bullet_id)
        for bid in bullets_to_remove:
            self.bullets.pop(bid, None)

    def _render(self):
        self.screen.fill(BG_COLOR)
        for plat in self.platforms:
            pygame.draw.rect(self.screen, PLATFORM_COLOR, plat)
        for bullet in self.bullets.values():
            pygame.draw.circle(self.screen, (0, 0, 0), (int(bullet.x), int(bullet.y)), BULLET_SIZE)
        if self.player.alive:
            color_tuple = PLAYER_COLORS.get(self.player.color, (128, 128, 128))
            pygame.draw.rect(self.screen, color_tuple, (self.player.x, self.player.y, PLAYER_WIDTH, HEAD_HEIGHT))
            pygame.draw.rect(self.screen, color_tuple, self.player.get_rect())
            hp_text = self.font_small.render(f"{self.player.name} ({self.player.hp}HP)", True, TEXT_COLOR)
            self.screen.blit(hp_text, (self.player.x, self.player.y - 30))
        mx, my = pygame.mouse.get_pos()
        pygame.draw.circle(self.screen, (255, 0, 0), (mx, my), 5, 1)
        cooldown_text = self.font_small.render(
            f"Tir: {'Prêt' if self.player.shoot_cooldown <= 0 else str(self.player.shoot_cooldown)}", True, TEXT_COLOR)
        self.screen.blit(cooldown_text, (10, 10))
        pygame.display.flip()


def run_local_solo(player_name, player_color):
    pygame.init()
    solo = SoloGame(player_name, player_color)
    solo.run()
