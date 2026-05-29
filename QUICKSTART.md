# Quick Start - Platformer Multiplayer

A fast guide to running the networked platformer game.

## 1. Install Dependencies

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

## 2. Start the Game

```bash
python main.py
```

## 3. Host a Game (Server)

1. Press `1` to create a server
2. Press `ENTER`
3. Enter your player name
4. Press `ENTER`
5. Choose your color using `LEFT` / `RIGHT`
6. Press `ENTER`
7. Wait in the lobby until all players connect
8. Press `SPACE` to start

## 4. Join a Game (Client)

1. Press `2` to join a server
2. Enter the server address
   - `localhost` or `127.0.0.1` for local testing
   - `192.168.x.x` for a LAN connection
3. Press `ENTER`
4. Enter your player name
5. Press `ENTER`
6. Choose your color using `LEFT` / `RIGHT`
7. Press `ENTER`

> The default port is `5000`.

## 5. Controls

- Move left: `A` or `LEFT ARROW`
- Move right: `D` or `RIGHT ARROW`
- Jump: `W`, `SPACE`, or `UP ARROW`
- Aim: Mouse cursor
- Shoot: Left mouse button
- Menu confirm: `ENTER`
- Back / cancel: `ESC`

## 6. Simple Local Test

Run one host and one or more clients on the same machine:

**Host terminal:**

```bash
python main.py
```

Choose `1`, then follow prompts.

**Client terminal:**

```bash
python main.py
```

Choose `2`, enter `localhost`, then follow prompts.

## 7. LAN Test

1. On the host machine, find the local IP address using `ipconfig`
2. On each client, enter that IP when joining
3. Make sure clients use port `5000`

## 8. Notes and Troubleshooting

- Each player must choose a unique color
- Max players: `4`
- If a player sees `Server full`, wait for someone to disconnect
- If connection fails, check the server is running and the IP/port are correct
- Use `ESC` to return to the menu

## 9. Project Files

- `main.py` — game launcher and menu
- `server.py` — server logic and game updates
- `client.py` — client networking and rendering
- `shared.py` — shared game classes and message types
- `constants.py` — configuration values
- `requirements.txt` — dependency list

Enjoy the game! 🎮
