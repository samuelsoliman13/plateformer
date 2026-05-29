# Platformer Multiplayer Game

This project is a local multiplayer 2D platformer built with Python and Pygame.
It uses a client-server network model so multiple players can connect over a local network.

## Features

- Local multiplayer with TCP client-server architecture
- Up to 4 players
- Player movement, jumping, and shooting
- Health system with body/head damage
- Color-based player selection in the lobby
- Simple lobby and game state synchronization
- Configurable settings in `constants.py`

## Requirements

- Python 3.8 or newer
- Pygame 2.0 or newer

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run the Game

```bash
python main.py
```

## How to Play

The game starts with a menu where you can choose to host or join a game.

### Host a Game

1. Run `python main.py`
2. Press `1` to create a server
3. Press `ENTER` to continue
4. Enter your player name
5. Press `ENTER`
6. Choose your color with `LEFT` / `RIGHT`
7. Press `ENTER` to join the lobby
8. When all players are connected, press `SPACE` to start

### Join a Game

1. Run `python main.py`
2. Press `2` to join a server
3. Enter the server address: `localhost`, `127.0.0.1`, or `192.168.x.x`
4. Press `ENTER`
5. Enter your player name
6. Press `ENTER`
7. Choose your color with `LEFT` / `RIGHT`
8. Press `ENTER` to join the lobby

> The default server port is `5000`.

## Controls

- Move left: `A` or `LEFT ARROW`
- Move right: `D` or `RIGHT ARROW`
- Jump: `W`, `SPACE`, or `UP ARROW`
- Aim: mouse cursor
- Shoot: left mouse button
- In menus: `ENTER` to confirm, `ESC` to go back

## Game Rules

- Each player has 4 health points
- Body hits deal 1 damage
- Head hits deal 4 damage (instant elimination)
- After taking damage, players gain temporary invincibility for a short time

## Network Details

- Server listens on `0.0.0.0:5000`
- Clients connect using TCP
- Messages are sent as JSON strings
- Supported message types: `join`, `input`, `shoot`, `chat_message`, `start_game`, `state_update`

## Configuration

Configure game settings in `constants.py`:

- `WIDTH`, `HEIGHT`: window size
- `FPS`: frames per second
- `GRAVITY`: gravity strength
- `PLAYER_SPEED`: movement speed
- `JUMP_STRENGTH`: jump force
- `BULLET_SPEED`: bullet speed
- `SHOOT_COOLDOWN`: cooldown between shots (ms)
- `MAX_HP`: player health
- `DEFAULT_PORT`: network port

## Project Structure

```
plateformer/
├── main.py          # Menu and game launcher
├── constants.py     # Game and network configuration
├── shared.py        # Shared classes and message objects
├── server.py        # Server logic and physics updates
├── client.py        # Client networking and rendering
├── requirements.txt # Python dependencies
├── Readme.md        # This file
└── QUICKSTART.md    # Quick start guide
```

## Common Issues

- "Color taken": choose a different color, because each player must have a unique color
- "Server full": the server already has 4 players connected
- Connection refused: verify the server IP, port `5000`, and that the server is running
- Local test: use `localhost` or `127.0.0.1` to connect from the same machine

## Quick Start Example

**Host:**

```bash
python main.py
```

Choose `1`, then follow the prompts to host.

**Clients:**

```bash
python main.py
```

Choose `2`, enter the host IP, then follow the prompts.

## Notes

- Use a different color for each player
- Press `ESC` to return to the menu at any time
- The host must start the game once all players have joined

## License

Free to use and modify.
