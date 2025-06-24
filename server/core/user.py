import os
import json
import traceback
from server.core.content import ItemInstance, ContainerInstance

USERS_FILE = "server/data/users.json"

class UserManager:
    @staticmethod
    def load_users():
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        return {}

    @staticmethod
    def save_users(users):
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)

    @staticmethod
    def serialize_inventory(inventory):
        def serialize_item(inst):
            data = {
                "item_id": inst.item_blueprint.id,
                "quantity": inst.quantity
            }
            if hasattr(inst, "contents"):
                data["contents"] = [serialize_item(i) for i in inst.contents]
            return data
        return [serialize_item(item) for item in inventory]

    @staticmethod
    def deserialize_inventory(data):
        def deserialize_item(d):
            blueprint = items.get(d["item_id"])
            if not blueprint:
                return None
            if "contents" in d:
                container = ContainerInstance(blueprint, d["quantity"])
                for sub in d["contents"]:
                    item = deserialize_item(sub)
                    if item:
                        container.add_item(item)
                return container
            return ItemInstance(blueprint, d["quantity"])
        return [deserialize_item(item) for item in data if deserialize_item(item)]

    @staticmethod
    def authenticate_or_create(conn):
        def send(msg):
            try:
                conn.sendall((msg + "\r\n").encode())
            except:
                pass

        def recv_line():
            buffer = ""
            try:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        return None
                    buffer += data.decode(errors='ignore')
                    if "\n" in buffer or "\r" in buffer:
                        break
                return buffer.splitlines()[0].strip()
            except:
                return None

        try:
            users = UserManager.load_users()

            while True:
                send("Please enter your account name, or type NEW to create one:")
                name = recv_line()
                if name is None:
                    return None, None
                name = name.strip()
                if not name:
                    continue

                if name.upper() == "NEW":
                    while True:
                        send("Choose a new account name:")
                        account_name = recv_line()
                        if account_name is None or not account_name.strip():
                            continue
                        if account_name in users:
                            send("That account already exists.")
                            continue

                        send("Enter a password:")
                        password = recv_line()
                        if password is None or not password.strip():
                            continue

                        send("Confirm password:")
                        confirm = recv_line()
                        if confirm is None or confirm.strip() != password.strip():
                            send("Passwords did not match. Start over.")
                            continue

                        send("Choose a character name:")
                        character_name = recv_line()
                        if character_name is None or not character_name.strip():
                            continue

                        users[account_name] = {
                            "password": password,
                            "characters": {
                                character_name: {
                                    "name": character_name,
                                    "current_room_id": "start",
                                    "class": "Newbie",
                                    "stats": {
                                        "HP": 20,
                                        "Mana": 10,
                                        "STR": 5,
                                        "DEX": 5,
                                        "INT": 5,
                                        "CON": 5,
                                        "WIS": 5,
                                        "CHA": 5
                                    },
                                    "inventory": []
                                }
                            }
                        }
                        UserManager.save_users(users)
                        return account_name, users[account_name]["characters"][character_name]

                elif name in users:
                    for _ in range(3):
                        send("Enter your password:")
                        password = recv_line()
                        if password is None:
                            return None, None
                        if password == users[name].get("password"):
                            characters = users[name].get("characters", {})
                            if not characters:
                                send("No characters found. Creating default...")
                                characters["Default"] = {
                                    "name": "Default",
                                    "current_room_id": "start",
                                    "class": "Newbie",
                                    "stats": {
                                        "HP": 20,
                                        "Mana": 10,
                                        "STR": 5,
                                        "DEX": 5,
                                        "INT": 5,
                                        "CON": 5,
                                        "WIS": 5,
                                        "CHA": 5
                                    },
                                    "inventory": []
                                }
                                users[name]["characters"] = characters
                                UserManager.save_users(users)

                            character_name = list(characters.keys())[0]
                            return name, characters[character_name]
                        else:
                            send("Incorrect password. Try again.")
                    send("Too many failed attempts. Connection closing.")
                    return None, None
                else:
                    send("Account does not exist. Please try again or type NEW to create a new account.")

        except Exception as e:
            print(f"[ERROR] Exception in authenticate_or_create: {e}")
            traceback.print_exc()
            return None, None

    @staticmethod
    def save_character_data(account_name, character_name, updated_data):
        users = UserManager.load_users()
        if account_name in users and character_name in users[account_name].get("characters", {}):
            users[account_name]["characters"][character_name].update(updated_data)
            UserManager.save_users(users)
