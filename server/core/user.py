import os
import json
import traceback

# Assuming Player class and its constants are not directly needed here for UserManager,
# as UserManager primarily deals with raw data dictionaries.
# from .player import Player

USERS_FILE = "server/data/users.json"

# Default starting values for new characters, aligned with Player class expectations
DEFAULT_START_ROOM = "start"
DEFAULT_CLASS = "Fighter" # Player can choose this during a more detailed char creation
DEFAULT_RACE = "Human"   # Player can choose this
DEFAULT_BASE_STATS_ARRAY = [15, 14, 13, 12, 10, 8]
DEFAULT_STAT_ASSIGNMENT = { # Default assignment, player should assign during creation
    "STR": DEFAULT_BASE_STATS_ARRAY[0], "DEX": DEFAULT_BASE_STATS_ARRAY[1],
    "CON": DEFAULT_BASE_STATS_ARRAY[2], "INT": DEFAULT_BASE_STATS_ARRAY[3],
    "WIS": DEFAULT_BASE_STATS_ARRAY[4], "CHA": DEFAULT_BASE_STATS_ARRAY[5]
}
# Default equipment slots structure (all empty)
# This requires Player.ALL_EQUIPMENT_SLOTS to be accessible if we want to use it here.
# For simplicity, if Player is not imported, an empty dict for equipment is also fine,
# as main.py's player loading logic can default it if missing.
# from .player import Player # To get Player.ALL_EQUIPMENT_SLOTS
# DEFAULT_EQUIPMENT = {slot: None for slot in Player.ALL_EQUIPMENT_SLOTS}
DEFAULT_EQUIPMENT = {} # Player class init in main.py will handle this better

class UserManager:
    @staticmethod
    def load_users():
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"[ERROR] Failed to decode {USERS_FILE}. Returning empty users dict.")
                return {}
            except Exception as e:
                print(f"[ERROR] Failed to load {USERS_FILE}: {e}. Returning empty users dict.")
                return {}
        return {}

    @staticmethod
    def save_users(users):
        try:
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save users to {USERS_FILE}: {e}")

    @staticmethod
    def authenticate_or_create(conn):
        def send(msg):
            try: conn.sendall((msg + "\r\n").encode())
            except: pass
        def recv_line():
            buffer = ""; MAX_BUFFER_SIZE = 4096
            try:
                while True:
                    data = conn.recv(1024)
                    if not data: return None
                    buffer += data.decode(errors='ignore')
                    if len(buffer) > MAX_BUFFER_SIZE: print("Error: Recv buffer overflow"); return None
                    if "\n" in buffer or "\r" in buffer: break
                return buffer.splitlines()[0].strip()
            except: return None

        try:
            users = UserManager.load_users()
            send("Welcome!")
            while True:
                send("Enter account name, or type 'NEW' to create one:")
                name_input = recv_line()
                if name_input is None: return None, None
                name_input = name_input.strip()
                if not name_input: continue

                if name_input.upper() == "NEW":
                    send("Creating a new account.")
                    account_name = ""
                    while True:
                        send("Choose a new account name (3-15 alphanumeric chars):")
                        account_name_candidate = recv_line()
                        if account_name_candidate is None: return None, None
                        account_name_candidate = account_name_candidate.strip()
                        if not (3 <= len(account_name_candidate) <= 15 and account_name_candidate.isalnum()):
                            send("Invalid account name. Must be 3-15 alphanumeric characters.")
                            continue
                        if account_name_candidate.lower() in (k.lower() for k in users.keys()):
                            send("That account name is already taken. Please choose another.")
                            continue
                        account_name = account_name_candidate # Use the chosen casing
                        break

                    password = ""; confirm_password = "-"
                    while password != confirm_password:
                        send("Enter a password (min 5 chars):")
                        password = recv_line()
                        if password is None: return None, None
                        password = password.strip()
                        if len(password) < 5: send("Password too short."); password=""; continue # Reset for loop
                        send("Confirm password:")
                        confirm_password = recv_line()
                        if confirm_password is None: return None, None
                        confirm_password = confirm_password.strip()
                        if password != confirm_password: send("Passwords do not match. Try again.")

                    send(f"Choose a name for your first character on account '{account_name}':")
                    character_name_input = recv_line()
                    if character_name_input is None: return None, None # Connection lost
                    character_name = character_name_input.strip()
                    if not character_name:
                        character_name = f"{account_name}Hero"
                        send(f"No name entered, defaulting to '{character_name}'.")

                    # TODO: Prompt for Race and Class selection here.
                    # For now, using defaults.
                    chosen_race = DEFAULT_RACE
                    chosen_class = DEFAULT_CLASS
                    # TODO: Prompt for stat assignment from DEFAULT_BASE_STATS_ARRAY.
                    # For now, using default assignment.
                    chosen_base_stats = DEFAULT_STAT_ASSIGNMENT.copy()

                    new_character_data = {
                        "name": character_name,
                        "player_class_name": chosen_class,
                        "race_name": chosen_race,
                        "level": 1,
                        "xp": 0,
                        "base_stats": chosen_base_stats,
                        "current_hp": 0, # Player.__init__ will calculate max and set current
                        "current_room_id": DEFAULT_START_ROOM,
                        "inventory": [],
                        "equipment": {} # Player.__init__ will populate with Player.ALL_EQUIPMENT_SLOTS: None
                    }

                    users[account_name] = {
                        "password": password, # IMPORTANT: Store hashed password in a real system
                        "characters": {
                            character_name: new_character_data
                        }
                    }
                    UserManager.save_users(users)
                    send(f"Account '{account_name}' and character '{character_name}' created. Welcome!")
                    return account_name, new_character_data

                login_account_name_key = None
                for k_stored in users.keys():
                    if k_stored.lower() == name_input.lower():
                        login_account_name_key = k_stored
                        break

                if login_account_name_key:
                    user_account_data = users[login_account_name_key]
                    for attempt in range(3):
                        send(f"Password for {login_account_name_key}:")
                        password_input = recv_line()
                        if password_input is None: return None, None
                        if password_input.strip() == user_account_data.get("password"): # IMPORTANT: Compare hashed passwords
                            characters = user_account_data.get("characters", {})
                            if not characters:
                                # This case should ideally not happen if new accounts always create a char.
                                # If it does, could prompt for new character creation here.
                                send("Error: No characters found for this account. Please contact an admin.")
                                return None, None

                            # TODO: Implement character selection if multiple characters exist.
                            # For now, load the first character found.
                            character_name_to_load = list(characters.keys())[0]
                            character_data = characters[character_name_to_load]

                            # Ensure essential fields for Player class are present, using defaults if missing
                            character_data.setdefault("name", character_name_to_load)
                            character_data.setdefault("player_class_name", DEFAULT_CLASS)
                            character_data.setdefault("race_name", DEFAULT_RACE)
                            character_data.setdefault("level", 1)
                            character_data.setdefault("xp", 0)
                            character_data.setdefault("base_stats", DEFAULT_STAT_ASSIGNMENT.copy())
                            # current_hp will be set by Player class based on max_hp calculation
                            character_data.setdefault("current_hp", 0)
                            character_data.setdefault("current_room_id", DEFAULT_START_ROOM)
                            character_data.setdefault("inventory", [])
                            character_data.setdefault("equipment", {}) # Player init will ensure all slots

                            send(f"Welcome back, {character_data['name']}!")
                            return login_account_name_key, character_data
                        else:
                            send(f"Incorrect password. Attempts remaining: {2-attempt}")
                    send("Too many failed password attempts. Disconnecting.")
                    return None, None
                else:
                    send("Account not found. Type 'NEW' to create one.")
        except ConnectionResetError:
            print("[INFO] Client disconnected during authentication.")
            return None, None
        except Exception as e:
            print(f"[ERROR] Exception in authenticate_or_create: {e}")
            traceback.print_exc()
            try: send("An error occurred during authentication. Please try again later.") # Try to send error
            except: pass # If send also fails
            return None, None

    @staticmethod
    def save_user_data(account_name_key, character_data_to_save):
        """
        Saves the provided character_data for the given account_name (using its stored casing).
        The character_name is derived from character_data_to_save["name"].
        """
        if not account_name_key or not character_data_to_save or "name" not in character_data_to_save:
            print("[ERROR] UserManager.save_user_data: Missing account_name_key or character data/name.")
            return

        character_name = character_data_to_save["name"]
        users = UserManager.load_users()

        if account_name_key in users:
            if "characters" not in users[account_name_key]:
                users[account_name_key]["characters"] = {}
            users[account_name_key]["characters"][character_name] = character_data_to_save
            UserManager.save_users(users)
        else:
            print(f"[ERROR] UserManager.save_user_data: Account key '{account_name_key}' not found for saving character '{character_name}'.")
