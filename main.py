import pygame
import threading
import sys
from constants import *
from server import run_server
from client import run_game, run_local_solo

class MenuUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Platformer Multijoueur - Menu")
        self.font_title = pygame.font.Font(None, 48)
        self.font_button = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        self.clock = pygame.time.Clock()
        
        self.state = "main_menu"  # main_menu, create_server, join_server
        self.input_text = ""
        self.player_name = ""
        self.player_color = ""
        self.selected_color_idx = 0
        self.colors_list = list(PLAYER_COLORS.keys())
        
    def run(self):
        """Boucle principale du menu"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_keydown(event)
            
            if self.state == "main_menu":
                self._render_main_menu()
            elif self.state == "create_server":
                self._render_create_server()
            elif self.state == "join_server":
                self._render_join_server()
            elif self.state == "player_setup":
                self._render_player_setup()
            
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit(0)
    
    def _handle_keydown(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.state != "main_menu":
                self.state = "main_menu"
                self.input_text = ""
                self.player_name = ""
                self.player_color = ""
                return True
            else:
                return False
        
        if self.state == "main_menu":
            if event.key == pygame.K_1:
                self.state = "create_server"
            elif event.key == pygame.K_2:
                self.state = "join_server"
            elif event.key == pygame.K_3:
                # Mode solo rapide
                self._start_solo()
        
        elif self.state == "create_server":
            if event.key == pygame.K_RETURN:
                # Lancer le serveur
                self.state = "player_setup"
        
        elif self.state == "join_server":
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_RETURN and self.input_text:
                # Se connecter au serveur
                self.state = "player_setup"
            elif event.unicode.isprintable():
                self.input_text += event.unicode
        
        elif self.state == "player_setup":
            if event.key == pygame.K_BACKSPACE:
                self.player_name = self.player_name[:-1]
            elif event.key == pygame.K_RETURN and self.player_name:
                self._start_game()
                return False
            elif event.key == pygame.K_LEFT:
                self.selected_color_idx = (self.selected_color_idx - 1) % len(self.colors_list)
            elif event.key == pygame.K_RIGHT:
                self.selected_color_idx = (self.selected_color_idx + 1) % len(self.colors_list)
            elif event.unicode.isprintable() and len(self.player_name) < 20:
                self.player_name += event.unicode
        
        return True
    
    def _render_main_menu(self):
        """Affiche le menu principal"""
        self.screen.fill(UI_BG_COLOR)
        
        # Titre
        title = self.font_title.render("PLATFORMER MULTIJOUEUR", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
        
        # Boutons
        option1 = self.font_button.render("1. Créer un serveur (HOST)", True, TEXT_COLOR)
        option2 = self.font_button.render("2. Rejoindre un serveur (CLIENT)", True, TEXT_COLOR)
        option3 = self.font_button.render("3. Solo (Jouer seul)", True, TEXT_COLOR)
        
        self.screen.blit(option1, (50, 200))
        self.screen.blit(option2, (50, 300))
        self.screen.blit(option3, (50, 400))
        
        # Instructions
        instr = self.font_small.render("Tapez 1 ou 2 pour continuer", True, (100, 100, 100))
        self.screen.blit(instr, (WIDTH // 2 - instr.get_width() // 2, HEIGHT - 100))
        instr = self.font_small.render("Tapez 1, 2 ou 3 pour continuer", True, (100, 100, 100))
        self.screen.blit(instr, (WIDTH // 2 - instr.get_width() // 2, HEIGHT - 100))
        
        pygame.display.flip()
    
    def _render_create_server(self):
        """Affiche l'écran de création de serveur"""
        self.screen.fill(UI_BG_COLOR)
        
        title = self.font_button.render("Créer un serveur", True, TEXT_COLOR)
        self.screen.blit(title, (50, 50))
        
        info1 = self.font_small.render(f"Port: {DEFAULT_PORT}", True, TEXT_COLOR)
        info2 = self.font_small.render("Appuyez sur ENTRÉE pour continuer", True, (0, 100, 0))
        
        self.screen.blit(info1, (50, 150))
        self.screen.blit(info2, (50, 250))
        
        instr = self.font_small.render("ESC pour retourner au menu", True, (100, 100, 100))
        self.screen.blit(instr, (WIDTH // 2 - instr.get_width() // 2, HEIGHT - 50))
        
        pygame.display.flip()
    
    def _render_join_server(self):
        """Affiche l'écran de connexion à un serveur"""
        self.screen.fill(UI_BG_COLOR)
        
        title = self.font_button.render("Rejoindre un serveur", True, TEXT_COLOR)
        self.screen.blit(title, (50, 50))
        
        info = self.font_small.render("Entrez l'adresse IP du serveur:", True, TEXT_COLOR)
        self.screen.blit(info, (50, 120))
        
        format_info = self.font_small.render("Format: IP ou IP:PORT (ex: 192.168.1.5:5000)", True, (100, 100, 100))
        self.screen.blit(format_info, (50, 150))
        
        # Champ d'input
        input_rect = pygame.Rect(50, 200, 400, 40)
        pygame.draw.rect(self.screen, (255, 255, 255), input_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, input_rect, 2)
        
        input_text = self.font_small.render(self.input_text or "localhost", True, TEXT_COLOR)
        self.screen.blit(input_text, (60, 210))
        
        instr = self.font_small.render("ENTRÉE pour continuer", True, (0, 100, 0))
        self.screen.blit(instr, (50, 300))
        
        esc = self.font_small.render("ESC pour retourner au menu", True, (100, 100, 100))
        self.screen.blit(esc, (WIDTH // 2 - esc.get_width() // 2, HEIGHT - 50))
        
        pygame.display.flip()
    
    def _render_player_setup(self):
        """Affiche l'écran de setup du joueur"""
        self.screen.fill(UI_BG_COLOR)
        
        title = self.font_button.render("Configuration du joueur", True, TEXT_COLOR)
        self.screen.blit(title, (50, 50))
        
        # Pseudo
        name_label = self.font_small.render("Pseudo (ENTRÉE pour continuer):", True, TEXT_COLOR)
        self.screen.blit(name_label, (50, 150))
        
        name_rect = pygame.Rect(50, 190, 300, 40)
        pygame.draw.rect(self.screen, (255, 255, 255), name_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, name_rect, 2)
        
        name_text = self.font_small.render(self.player_name or "_", True, TEXT_COLOR)
        self.screen.blit(name_text, (60, 200))
        
        # Couleur
        color_label = self.font_small.render("Couleur (← → pour changer):", True, TEXT_COLOR)
        self.screen.blit(color_label, (50, 280))
        
        self.player_color = self.colors_list[self.selected_color_idx]
        color_tuple = PLAYER_COLORS[self.player_color]
        
        # Afficher les couleurs disponibles
        x_pos = 50
        for i, color_name in enumerate(self.colors_list):
            color = PLAYER_COLORS[color_name]
            rect = pygame.Rect(x_pos, 320, 40, 40)
            pygame.draw.rect(self.screen, color, rect)
            if i == self.selected_color_idx:
                pygame.draw.rect(self.screen, (0, 0, 0), rect, 3)
            else:
                pygame.draw.rect(self.screen, TEXT_COLOR, rect, 1)
            x_pos += 50
            if x_pos > WIDTH - 100:
                x_pos = 50
        
        current_color = self.font_small.render(f"Couleur actuelle: {self.player_color}", True, TEXT_COLOR)
        self.screen.blit(current_color, (50, 400))
        
        pygame.display.flip()
    
    def _start_game(self):
        """Démarre le jeu"""
        if self.state == "create_server" or (self.state == "player_setup" and not self.input_text):
            # Mode serveur
            print(f"Démarrage du serveur...")
            server_thread = threading.Thread(target=lambda: run_server(DEFAULT_PORT), daemon=True)
            server_thread.start()
            
            import time
            time.sleep(1)  # Attendre le démarrage du serveur
            
            # Lancer le client local
            run_game("localhost", DEFAULT_PORT, self.player_name, self.player_color)
        else:
            # Mode client
            host_input = self.input_text if self.input_text else "localhost"
            
            # Parser "IP:PORT" ou juste "IP"
            if ":" in host_input:
                try:
                    host, port_str = host_input.rsplit(":", 1)
                    port = int(port_str)
                except ValueError:
                    host = host_input
                    port = DEFAULT_PORT
            else:
                host = host_input
                port = DEFAULT_PORT
            
            try:
                run_game(host, port, self.player_name, self.player_color)
            except Exception as e:
                print(f"Erreur: {e}")
                self.state = "main_menu"

    def _start_solo(self):
        """Démarre un mode solo local pour tester les mécaniques."""
        print("Démarrage du mode solo local...")
        try:
            color = self.colors_list[self.selected_color_idx]
        except Exception:
            color = list(PLAYER_COLORS.keys())[0]

        name = "Solo"
        try:
            run_local_solo(name, color)
        except Exception as e:
            print(f"Erreur en mode solo local: {e}")
        finally:
            pygame.quit()
            sys.exit(0)

def main():
    menu = MenuUI()
    menu.run()

    
def run_solo_from_menu(name="Solo", color=None):
    """Utility to start a server and run a single client for quick solo testing."""
    # This function is defined for potential external use; MenuUI._start_solo calls same logic.
    server_thread = threading.Thread(target=lambda: run_server(DEFAULT_PORT), daemon=True)
    server_thread.start()
    import time
    time.sleep(1)
    # Choose default color if not provided
    if color is None:
        try:
            color = list(PLAYER_COLORS.keys())[0]
        except Exception:
            color = "Red"
    run_game("localhost", DEFAULT_PORT, name, color)

if __name__ == "__main__":
    main()
