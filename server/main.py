import socket
import threading
from server.core.user import UserManager
from server.core.player import Player
from server.core.room import Room
from server.core.content import Mob, Item, ItemInstance

HOST = "127.0.0.1"
PORT = 4000

world = {}
mobs = {}
items = {}

COMMAND_ALIASES = {
    "l": "look",
    "char": "stats",
    "character": "stats",
    "c": "stats",
}

DIRECTIONS = {
    "n": "north", "north": "north",
    "s": "south", "south": "south",
    "e": "east", "east": "east",
    "w": "west", "west": "west",
    "ne": "northeast", "northeast": "northeast",
    "nw": "northwest", "northwest": "northwest",
    "se": "southeast", "southeast": "southeast",
    "sw": "southwest", "southwest": "southwest",
    "u": "up", "up": "up",
    "d": "down", "down": "down"
}

def load_world():
    global world, mobs, items
    try:
        world = Room.load_rooms("server/data/world.json")
    except Exception as e:
        print(f"[ERROR] Failed to load world: {e}")
        world = {
            "start": Room(
                "start",
                "Forest Clearing",
                "You stand in a quiet forest clearing. Birds chirp overhead. Exits lead north and east.",
                {}
            )
        }

    try:
        mobs = Mob.load_mobs()
    except Exception as e:
        print(f"[ERROR] Failed to load mobs: {e}")
        mobs = {}

    try:
        items = Item.load_items()
    except Exception as e:
        print(f"[ERROR] Failed to load items: {e}")
        items = {}

def handle_client(conn, addr):
    print(f"[+] Connection from {addr}")
    try:
        username, user_data = UserManager.authenticate_or_create(conn)
        if not username:
            conn.close()
            print(f"[-] Connection closed: {addr}")
            return

        current_room_id = user_data.get("current_room_id", "start")
        room = world.get(current_room_id, world.get("start"))
        player = Player(user_data["name"], conn, room)

        # Load inventory
        player.load_inventory(user_data.get("inventory", []), items)

        player.send_line("\r\nWelcome to the MUD!")
        player.look()

        while True:
            player.send("\r\n> ")
            msg = player.read_line()
            if msg is None:
                user_data["current_room_id"] = player.room.id
                user_data["inventory"] = player.save_inventory()
                UserManager.save_character_data(username, player.name, user_data)
                break

            command = msg.strip().lower()
            if not command:
                continue

            command = COMMAND_ALIASES.get(command, command)

            responded = False

            if command in DIRECTIONS:
                dir = DIRECTIONS[command]
                if dir in player.room.exits:
                    new_room_id = player.room.exits[dir]
                    if new_room_id in world:
                        player.room = world[new_room_id]
                        player.look()
                        user_data["current_room_id"] = player.room.id
                        UserManager.save_character_data(username, player.name, user_data)
                    else:
                        player.send_line("The exit leads nowhere.")
                    responded = True
                else:
                    player.send_line("You can't go that way.")
                    responded = True

            elif command.startswith("go "):
                dir = command[3:].strip()
                dir = DIRECTIONS.get(dir)
                if dir and dir in player.room.exits:
                    new_room_id = player.room.exits[dir]
                    if new_room_id in world:
                        player.room = world[new_room_id]
                        player.look()
                        user_data["current_room_id"] = player.room.id
                        UserManager.save_character_data(username, player.name, user_data)
                    else:
                        player.send_line("The exit leads nowhere.")
                    responded = True
                else:
                    player.send_line("Unknown direction.")
                    responded = True

            elif command == "look":
                player.look()
                responded = True

            elif command == "stats":
                stats = user_data.get("stats", {})
                player.send_line(f"\r\n{user_data['name']} the {user_data.get('class', 'Adventurer')}")
                player.send_line("-------------------------")
                for key in ["HP", "Mana", "STR", "DEX", "INT", "CON", "WIS", "CHA"]:
                    player.send_line(f"{key}: {stats.get(key, 0)}")
                player.send_line("\r\nEquipment: (coming soon)")
                player.send_line("Inventory: (coming soon)")
                responded = True

            elif command in ("inventory", "inv"):
                player.list_inventory()
                responded = True

            elif command.startswith("use "):
                item_name = command[4:].strip()
                for inv_item in player.inventory:
                    if inv_item.item_blueprint.name.lower() == item_name:
                        if inv_item.use():
                            player.send_line(f"You use the {inv_item.item_blueprint.name}.")
                            if inv_item.quantity == 0:
                                player.inventory.remove(inv_item)
                        else:
                            player.send_line(f"You have no {item_name} left.")
                        responded = True
                        break
                if not responded:
                    player.send_line(f"You don't have a {item_name}.")
                    responded = True

            elif command.startswith("drop "):
                item_name = command[5:].strip()
                for inv_item in player.inventory:
                    if inv_item.item_blueprint.name.lower() == item_name:
                        if inv_item.quantity > 0:
                            inv_item.quantity -= 1
                            player.room.item_instances.append(
                                ItemInstance(inv_item.item_blueprint, 1)
                            )
                            player.send_line(f"You drop the {inv_item.item_blueprint.name}.")
                            if inv_item.quantity == 0:
                                player.inventory.remove(inv_item)
                        responded = True
                        break
                if not responded:
                    player.send_line(f"You don't have a {item_name}.")
                    responded = True

            elif command.startswith("take "):
                item_name = command[5:].strip().lower()
                if " from " in item_name:
                    item_part, container_part = item_name.split(" from ", 1)
                    player.take_item_from_container(item_part.strip(), container_part.strip())
                else:
                    for item in player.room.item_instances:
                        if item.item_blueprint.name.lower() == item_name:
                            if item.quantity > 1:
                                item.quantity -= 1
                            else:
                                player.room.item_instances.remove(item)
                            player.add_item(ItemInstance(item.item_blueprint, 1))
                            player.send_line(f"You pick up the {item.item_blueprint.name}.")
                            break
                    else:
                        player.send_line(f"There is no {item_name} here.")
                    responded = True

            elif command.startswith("put "):
                try:
                    parts = command[4:].split(" in ", 1)
                    if len(parts) == 2:
                        item_name, container_name = parts
                        player.put_item_into_container(item_name.strip(), container_name.strip())
                    else:
                        player.send_line("Use: put [item] in [container]")
                except:
                    player.send_line("Something went wrong putting the item in.")
                responded = True

            elif command.startswith("inspect "):
                container_name = command[8:].strip()
                player.inspect_container(container_name)
                responded = True

            elif command == "reload":
                load_world()
                player.send_line("World reloaded.")
                responded = True

            if not responded:
                if command:  # avoid extra prompt for blank input
                    player.send_line("I don't understand that command.")

    except Exception as e:
        print(f"[ERROR] Exception handling client {addr}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except:
            pass
        print(f"[-] Connection closed: {addr}")

def main():
    load_world()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"[*] MUD server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
