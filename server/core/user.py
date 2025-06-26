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

# --- Game Data Loading ---
CLASSES_DATA = {}
RACES_DATA = {}

def _load_game_data_if_needed():
    global CLASSES_DATA, RACES_DATA
    if not CLASSES_DATA:
        try:
            with open("server/data/classes.json", "r") as f:
                CLASSES_DATA = json.load(f)
        except Exception as e:
            print(f"[ERROR] UserManager: Failed to load classes.json: {e}")
            # Potentially raise an error or handle more gracefully if essential data fails to load
    if not RACES_DATA:
        try:
            with open("server/data/races.json", "r") as f:
                RACES_DATA = json.load(f)
        except Exception as e:
            print(f"[ERROR] UserManager: Failed to load races.json: {e}")

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
        _load_game_data_if_needed() # Load class/race data if not already loaded

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
                        if len(password) < 5: send("Password too short."); password=""; continue
                        send("Confirm password:")
                        confirm_password = recv_line()
                        if confirm_password is None: return None, None
                        confirm_password = confirm_password.strip()
                        if password != confirm_password: send("Passwords do not match. Try again.")

                    send(f"Choose a name for your first character on account '{account_name}':")
                    character_name_input = recv_line()
                    if character_name_input is None: return None, None
                    character_name = character_name_input.strip()
                    if not character_name:
                        character_name = f"{account_name}Hero"
                        send(f"No name entered, defaulting to '{character_name}'.")

                    # --- Race Selection ---
                    chosen_race_name_for_player_class = None # This will be like "High Elf" or "Human"
                    chosen_race_display_name = None # This will be like "Elf (High Elf)" for display
                    chosen_race_data_for_player_class = {} # Combined data for Player class init

                    selectable_races = {} # name_or_num_lowercase -> {display_name: "Name", data_key: "ActualKeyForRACES_DATA", subrace_key: "SubKey"}
                    race_display_list = []
                    race_counter = 1

                    for r_name, r_info in RACES_DATA.items():
                        if "subraces" in r_info and r_info["subraces"]:
                            for sr_name, sr_info in r_info["subraces"].items():
                                display_name = f"{r_name} ({sr_name})"
                                race_display_list.append(f"{race_counter}. {display_name}")
                                selectable_races[str(race_counter)] = {"display_name": display_name, "data_key": r_name, "subrace_key": sr_name}
                                selectable_races[display_name.lower()] = selectable_races[str(race_counter)]
                                race_counter += 1
                        else:
                            race_display_list.append(f"{race_counter}. {r_name}")
                            selectable_races[str(race_counter)] = {"display_name": r_name, "data_key": r_name, "subrace_key": None}
                            selectable_races[r_name.lower()] = selectable_races[str(race_counter)]
                            race_counter += 1

                    send("\n--- Race Selection ---")
                    for line in race_display_list: send(line)

                    while not chosen_race_name_for_player_class:
                        send("Choose your race by number or name (e.g., '1' or 'Human'):")
                        race_choice_input = recv_line()
                        if race_choice_input is None: return None, None

                        selected_option_meta = selectable_races.get(race_choice_input.strip().lower())
                        if not selected_option_meta:
                            send("Invalid selection. Please try again.")
                            continue

                        temp_display_name = selected_option_meta["display_name"]
                        base_race_key = selected_option_meta["data_key"]
                        subrace_key = selected_option_meta["subrace_key"]

                        current_race_info = RACES_DATA[base_race_key]
                        current_subrace_info = current_race_info.get("subraces", {}).get(subrace_key) if subrace_key else None

                        send(f"\n--- {temp_display_name} ---")
                        description = current_subrace_info.get("description") if current_subrace_info else current_race_info.get("description")
                        send(f"Description: {description or 'No description available.'}")

                        asi_texts = []
                        final_asi = {} # To correctly sum up base and subrace ASIs

                        # Base race ASI
                        for stat, val in current_race_info.get("ability_score_increase", {}).items():
                            if isinstance(val, int): final_asi[stat.upper()] = final_asi.get(stat.upper(), 0) + val
                            elif stat == "note": asi_texts.append(val) # Handle notes like Half-Elf

                        # Subrace ASI
                        if current_subrace_info:
                            for stat, val in current_subrace_info.get("ability_score_increase", {}).items():
                                if isinstance(val, int): final_asi[stat.upper()] = final_asi.get(stat.upper(), 0) + val
                                # Subrace notes could be handled too if needed

                        for stat_upper, total_val in final_asi.items():
                             asi_texts.append(f"{stat_upper}: +{total_val}")

                        send(f"Ability Score Increases: {', '.join(asi_texts) if asi_texts else 'None'}")

                        send("Traits:")
                        all_traits = list(current_race_info.get("traits", []))
                        if current_subrace_info: all_traits.extend(current_subrace_info.get("traits", []))

                        if all_traits:
                            for trait in all_traits: send(f"  - {trait.get('name', 'Unnamed Trait')}: {trait.get('description', 'No description.')}")
                        else: send("  None specific.")

                        send(f"Confirm selection of {temp_display_name}? (yes/no)")
                        confirm_input = recv_line()
                        if confirm_input and confirm_input.lower() == 'yes':
                            chosen_race_display_name = temp_display_name
                            # For Player class, we need a single name that Player class can use to fetch all data.
                            # If it's a subrace, use subrace name, Player class will know to look up base too.
                            # If not, use base race name.
                            chosen_race_name_for_player_class = subrace_key if subrace_key else base_race_key
                        else:
                            send("Selection cancelled. Please choose again.")

                    # --- Class Selection ---
                    chosen_class_name = None # This will be the key for CLASSES_DATA e.g. "Fighter"
                    chosen_class_data = None
                    selectable_classes = {}
                    class_display_list = []
                    class_counter = 1
                    send("\n--- Class Selection ---")
                    for class_name_key, class_info in CLASSES_DATA.items():
                        class_display_list.append(f"{class_counter}. {class_name_key}")
                        selectable_classes[str(class_counter)] = {"name": class_name_key, "data": class_info}
                        selectable_classes[class_name_key.lower()] = selectable_classes[str(class_counter)]
                        class_counter += 1
                    for line in class_display_list: send(line)

                    while not chosen_class_data:
                        send("Choose your class by number or name (e.g., '1' or 'Fighter'):")
                        class_choice_input = recv_line()
                        if class_choice_input is None: return None, None

                        selected_option = selectable_classes.get(class_choice_input.strip().lower())
                        if not selected_option:
                            send("Invalid selection. Please try again.")
                            continue

                        temp_class_data = selected_option["data"]
                        temp_class_name = selected_option["name"]

                        send(f"\n--- {temp_class_name} ---")
                        send(f"Description: {temp_class_data.get('description', 'No description available.')}")
                        send(f"Primary Abilities: {', '.join(temp_class_data.get('primary_ability', ['N/A']))}")
                        send(f"Ability Explanation: {temp_class_data.get('primary_ability_description', 'N/A')}")
                        send(f"Hit Die: d{temp_class_data.get('hit_die', 6)}")
                        send(f"Saving Throw Proficiencies: {', '.join(temp_class_data.get('saving_throw_proficiencies', ['N/A']))}")
                        send(f"Armor Proficiencies: {', '.join(temp_class_data.get('armor_proficiencies', ['N/A']))}")
                        send(f"Weapon Proficiencies: {', '.join(temp_class_data.get('weapon_proficiencies', ['N/A']))}")
                        send(f"Recommended Skill Proficiencies (auto-assigned): {', '.join(temp_class_data.get('skill_proficiencies', ['N/A']))}")

                        send(f"Confirm selection of {temp_class_name}? (yes/no)")
                        confirm_input = recv_line()
                        if confirm_input and confirm_input.lower() == 'yes':
                            chosen_class_name = temp_class_name
                            chosen_class_data = temp_class_data
                        else:
                            send("Selection cancelled. Please choose again.")

                    # --- Stat Assignment & Explanation ---
                    send("\n--- Stat Assignment ---")
                    assigned_base_stats = {"STR": 8, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}
                    standard_array_scores = sorted(DEFAULT_BASE_STATS_ARRAY, reverse=True) # [15, 14, 13, 12, 10, 8]

                    priority_stats = chosen_class_data.get("recommended_stat_priority", [])
                    assigned_scores_explanation = ["Your stats have been automatically assigned using the standard array (15,14,13,12,10,8) based on your class's priorities:"]

                    temp_scores_to_distribute = list(standard_array_scores)

                    used_stats_for_priority = []
                    for stat_name_priority in priority_stats:
                        stat_upper = stat_name_priority.upper()
                        if temp_scores_to_distribute and stat_upper not in used_stats_for_priority:
                            score = temp_scores_to_distribute.pop(0)
                            assigned_base_stats[stat_upper] = score
                            assigned_scores_explanation.append(f"  - {stat_upper}: {score}")
                            used_stats_for_priority.append(stat_upper)

                    all_stat_keys = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
                    remaining_stat_keys = [s for s in all_stat_keys if s not in used_stats_for_priority]

                    for stat_name_remaining in remaining_stat_keys:
                        if temp_scores_to_distribute:
                            score = temp_scores_to_distribute.pop(0)
                            assigned_base_stats[stat_name_remaining] = score
                            assigned_scores_explanation.append(f"  - {stat_name_remaining}: {score}")

                    for line in assigned_scores_explanation: send(line)
                    send("These are your base scores. Racial modifiers will be applied by the game system.")

                    # --- Skill Proficiency Explanation ---
                    send("\n--- Skill Proficiencies ---")
                    class_skills = chosen_class_data.get("skill_proficiencies", [])
                    if class_skills:
                        send(f"As a {chosen_class_name}, you are automatically proficient in: {', '.join(class_skills)}.")
                    else:
                        send("Your class does not automatically grant specific skill proficiencies at level 1 via this system.")
                    send("Racial skill proficiencies (if any) will also be applied.")

                    send("\nCharacter creation complete!")

                    new_character_data = {
                        "name": character_name,
                        "player_class_name": chosen_class_name,
                        "race_name": chosen_race_name_for_player_class, # Store the key Player class will use
                        "level": 1,
                        "xp": 0,
                        "base_stats": assigned_base_stats,
                        "current_hp": 0,
                        "current_room_id": DEFAULT_START_ROOM,
                        "inventory": [],
                        "equipment": {}
                    }

                    users[account_name] = {
                        "password": password,
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
                        if password_input.strip() == user_account_data.get("password"):
                            characters = user_account_data.get("characters", {})
                            if not characters:
                                send("Error: No characters found for this account. Please contact an admin.")
                                return None, None

                            character_name_to_load = list(characters.keys())[0]
                            character_data = characters[character_name_to_load]

                            character_data.setdefault("name", character_name_to_load)
                            character_data.setdefault("player_class_name", DEFAULT_CLASS)
                            # Use .get for race_name as older characters might not have it
                            character_data["race_name"] = character_data.get("race_name", DEFAULT_RACE)
                            character_data.setdefault("level", 1)
                            character_data.setdefault("xp", 0)

                            if "base_stats" not in character_data or not isinstance(character_data["base_stats"], dict):
                                character_data["base_stats"] = DEFAULT_STAT_ASSIGNMENT.copy()
                            else:
                                for stat_key_default in DEFAULT_STAT_ASSIGNMENT.keys():
                                    character_data["base_stats"].setdefault(stat_key_default, DEFAULT_STAT_ASSIGNMENT[stat_key_default])

                            character_data.setdefault("current_hp", 0)
                            character_data.setdefault("current_room_id", DEFAULT_START_ROOM)
                            character_data.setdefault("inventory", [])
                            character_data.setdefault("equipment", {})

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
            try: send("An error occurred during authentication. Please try again later.")
            except: pass
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
