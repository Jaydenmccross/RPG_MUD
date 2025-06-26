import socket
import threading
import time
import random
from server.core.user import UserManager
from server.core.player import Player, ITEMS_DATA as PLAYER_ITEMS_DATA, load_game_data as core_load_game_data
from server.core.room import Room
from server.core.content import Mob, Item, ItemInstance, MobInstance, ContainerInstance
from server.core.combat import resolve_attack

HOST = "127.0.0.1"
PORT = 4000
GAME_TICK_INTERVAL = 10

world = {}
mobs_blueprints = {}

# --- Global Combat Management ---
ACTIVE_COMBATANTS = []
combat_lock = threading.Lock()

# --- Global Player Management ---
CONNECTED_PLAYERS = []
players_lock = threading.Lock()

def add_to_active_combat(entity):
    with combat_lock:
        if entity not in ACTIVE_COMBATANTS: ACTIVE_COMBATANTS.append(entity)
def remove_from_active_combat(entity):
    with combat_lock:
        if entity in ACTIVE_COMBATANTS: ACTIVE_COMBATANTS.remove(entity)

def add_connected_player(player_instance):
    with players_lock:
        if player_instance not in CONNECTED_PLAYERS: CONNECTED_PLAYERS.append(player_instance)
def remove_connected_player(player_instance):
    with players_lock:
        if player_instance in CONNECTED_PLAYERS: CONNECTED_PLAYERS.remove(player_instance)

def get_players_in_room(room_id_to_check):
    """Returns a list of Player instances currently in the given room_id."""
    players_found = []
    with players_lock: # Ensure thread-safe access to CONNECTED_PLAYERS
        for player in CONNECTED_PLAYERS:
            # Ensure player.room is the Room object and has an id attribute
            if player.room and player.room.id == room_id_to_check and player.is_alive():
                players_found.append(player)
    return players_found
# --- End Global Management ---

ANSI_RED = "\033[91m"; ANSI_GREEN = "\033[92m"; ANSI_YELLOW = "\033[93m"; ANSI_RESET = "\033[0m"
COMMAND_ALIASES = {
    "l":"look","char":"sheet","character":"sheet","c":"sheet","score":"sheet","stats":"sheet","st":"sheet",
    "eq":"equip","wear":"equip","wield":"equip","rem":"remove","unequip":"remove",
    "i":"inventory","inv":"inventory","k":"kill","attack":"kill","g":"get","take":"get"
}
DIRECTIONS = {"n":"north","north":"north","s":"south","south":"south","e":"east","east":"east","w":"west","west":"west","ne":"northeast","northeast":"northeast","nw":"northwest","northwest":"northwest","se":"southeast","southeast":"southeast","sw":"southwest","southwest":"southwest","u":"up","up":"up","d":"down","down":"down"}
USER_FRIENDLY_SLOT_MAP = {
    "head":Player.EQUIPMENT_SLOT_HEAD,"helmet":Player.EQUIPMENT_SLOT_HEAD,"neck":Player.EQUIPMENT_SLOT_NECK,
    "amulet":Player.EQUIPMENT_SLOT_NECK,"chest":Player.EQUIPMENT_SLOT_CHEST,"body":Player.EQUIPMENT_SLOT_CHEST,
    "armor":Player.EQUIPMENT_SLOT_CHEST,"back":Player.EQUIPMENT_SLOT_BACK,"cloak":Player.EQUIPMENT_SLOT_BACK,
    "shoulders":Player.EQUIPMENT_SLOT_SHOULDERS,"wrists":Player.EQUIPMENT_SLOT_WRISTS,
    "bracers":Player.EQUIPMENT_SLOT_WRISTS,"hands":Player.EQUIPMENT_SLOT_HANDS,"gloves":Player.EQUIPMENT_SLOT_HANDS,
    "mainhand":Player.EQUIPMENT_SLOT_WEAPON_MAIN,"main hand":Player.EQUIPMENT_SLOT_WEAPON_MAIN,
    "weapon":Player.EQUIPMENT_SLOT_WEAPON_MAIN,"offhand":Player.EQUIPMENT_SLOT_WEAPON_OFF,
    "off hand":Player.EQUIPMENT_SLOT_WEAPON_OFF,"shield":Player.EQUIPMENT_SLOT_WEAPON_OFF,
    "finger 1":Player.EQUIPMENT_SLOT_RING_1,"ring 1":Player.EQUIPMENT_SLOT_RING_1,
    "left finger":Player.EQUIPMENT_SLOT_RING_1,"left ring":Player.EQUIPMENT_SLOT_RING_1,
    "finger 2":Player.EQUIPMENT_SLOT_RING_2,"ring 2":Player.EQUIPMENT_SLOT_RING_2,
    "right finger":Player.EQUIPMENT_SLOT_RING_2,"right ring":Player.EQUIPMENT_SLOT_RING_2,
    "legs":Player.EQUIPMENT_SLOT_LEGS,"pants":Player.EQUIPMENT_SLOT_LEGS,"feet":Player.EQUIPMENT_SLOT_FEET,
    "boots":Player.EQUIPMENT_SLOT_FEET,"relic":Player.EQUIPMENT_SLOT_RELIC,"light":Player.EQUIPMENT_SLOT_LIGHT_SOURCE,
    "light source":Player.EQUIPMENT_SLOT_LIGHT_SOURCE
}

def load_world_and_game_data(): # Unchanged
    global world, mobs_blueprints
    core_load_game_data()
    try: world = Room.load_rooms("server/data/world.json")
    except Exception as e: print(f"[ERROR] Failed to load world: {e}"); world = {"start": Room("start", "Default Start Room", "A void.", {})}
    try: mobs_blueprints = Mob.load_mobs()
    except Exception as e: print(f"[ERROR] Failed to load mobs: {e}"); mobs_blueprints = {}
    print("[SERVER] Spawning initial room contents...")
    for room_id, room_obj in world.items():
        try: room_obj.spawn_initial_content(mobs_blueprints, PLAYER_ITEMS_DATA)
        except Exception as e: print(f"[ERROR] Failed to spawn content in room '{room_id}': {e}")
    print("[SERVER] Initial room contents spawned.")

def game_tick(): # Will be enhanced in a later step
    global world, mobs_blueprints, ACTIVE_COMBATANTS, CONNECTED_PLAYERS, combat_lock, players_lock
    # print(f"[{time.strftime('%H:%M:%S')}] Game Tick Processing...") # Can be verbose
    try:
        # --- MOB & ITEM RESPAWN LOGIC (as before) ---
        for room_id, room in world.items():
            # Mob Respawns
            for mob_def in room.mob_definitions:
                mob_id_to_spawn=mob_def.get("mob_id");max_qty=mob_def.get("max_quantity",1);respawn_secs=mob_def.get("respawn_seconds",300)
                if not mob_id_to_spawn or respawn_secs<=0:continue
                current_live_count=sum(1 for mi in room.mob_instances if mi.mob_blueprint.id==mob_id_to_spawn and mi.is_alive())
                num_to_spawn=max_qty-current_live_count
                if num_to_spawn<=0:continue
                spawned_this_tick_for_def=0
                with combat_lock: # Protect access to defeated_mob_track if it's modified here
                    for i in range(len(room.defeated_mob_track)-1,-1,-1):
                        tracked_death=room.defeated_mob_track[i]
                        if tracked_death["mob_id"]==mob_id_to_spawn:
                            if time.time()-tracked_death["time_of_death"]>=respawn_secs:
                                blueprint=mobs_blueprints.get(mob_id_to_spawn)
                                if blueprint:
                                    new_mob = MobInstance(blueprint)
                                    room.mob_instances.append(new_mob)
                                    # print(f"[{time.strftime('%H:%M:%S')}] Respawned '{blueprint.name}' in room '{room.id}'.")
                                    # TODO: Notify players in room
                                    room.defeated_mob_track.pop(i)
                                    spawned_this_tick_for_def+=1
                                    if spawned_this_tick_for_def>=num_to_spawn:break
            # Item Respawns
            with combat_lock: # Protect access to pending_item_respawns
                for i in range(len(room.pending_item_respawns)-1,-1,-1):
                    item_respawn_entry=room.pending_item_respawns[i];original_def=item_respawn_entry["original_definition"]
                    respawn_item_id=original_def.get("item_id");respawn_qty=original_def.get("quantity",1);item_respawn_secs=original_def.get("respawn_seconds",600)
                    if not respawn_item_id or item_respawn_secs<=0:room.pending_item_respawns.pop(i);continue
                    if time.time()-item_respawn_entry["time_taken"]>=item_respawn_secs:
                        item_blueprint_dict=PLAYER_ITEMS_DATA.get(respawn_item_id) # This is a dict
                        if item_blueprint_dict:
                            # We need to create an Item object from the dict for ItemInstance constructor
                            from server.core.content import Item # Local import to avoid circular if Item needs Room
                            actual_blueprint = Item(**item_blueprint_dict) # Create Item object
                            if actual_blueprint.type=="container":new_item_instance=ContainerInstance(actual_blueprint,respawn_qty)
                            else:new_item_instance=ItemInstance(actual_blueprint,respawn_qty)
                            room.add_item_to_ground(new_item_instance)
                            # print(f"[{time.strftime('%H:%M:%S')}] Respawned '{actual_blueprint.name}' in room '{room.id}'.")
                            room.pending_item_respawns.pop(i)
                        else:print(f"Warning: Item blueprint ID '{respawn_item_id}' for respawn not found.");room.pending_item_respawns.pop(i)

        # --- COMBAT & AGGRO AI (To be added in next steps) ---

    except Exception as e:print(f"[ERROR] Exception in game_tick: {e}");import traceback;traceback.print_exc()

def game_tick_loop(): # Unchanged
    while True:game_tick();time.sleep(GAME_TICK_INTERVAL)

def handle_client(conn, addr):
    print(f"[+] Connection from {addr}")
    player_instance = None; username = None; user_data = None
    try:
        username, user_data = UserManager.authenticate_or_create(conn) # user_data is character_data
        if not username or not user_data: # Ensure user_data is also present
            if conn: conn.close()
            print(f"[-] Auth failed or no character data for {addr}")
            return

        # Extract data for Player constructor
        # UserManager now ensures these fields exist with defaults if loading older data
        player_name = user_data.get("name", username) # Fallback to username if name somehow missing
        player_class_name = user_data.get("player_class_name", "Fighter") # Default from UserManager
        player_race_name = user_data.get("race_name", "Human") # Default from UserManager, specific key
        player_base_stats = user_data.get("base_stats") # This will be a dict from UserManager

        class TempUser:
            def __init__(self, c, u): self.connection=c; self.username=u
            def send_message(self, msg):
                if self.connection:
                    try: self.connection.sendall(msg.encode()+b"\r\n")
                    except: pass
            def read_line(self):
                if self.connection:
                    try: raw=self.connection.recv(1024); return raw.decode().strip() if raw else None
                    except: return None
                return None

        temp_user_for_player = TempUser(conn, username)

        # Instantiate Player with all necessary data, including base_stats
        player_instance = Player(
            user=temp_user_for_player,
            player_class_name=player_class_name,
            race_name=player_race_name,
            name=player_name,
            base_stats=player_base_stats # Pass the loaded base_stats dictionary
        )
        # Player __init__ will now use these base_stats and then call recalculate_all_stats.

        add_connected_player(player_instance)

        # Initialize player's level, xp, current_hp from saved data *after* initial stat calculation
        player_instance.level = user_data.get("level", 1)
        player_instance.xp = user_data.get("xp", 0)
        # recalculate_all_stats (called in Player init) sets current_hp to max_hp by default.
        # Override with saved current_hp if it's valid.
        saved_hp = user_data.get("current_hp", player_instance.max_hp)
        player_instance.current_hp = min(saved_hp, player_instance.max_hp) if saved_hp > 0 else player_instance.max_hp

        player_instance.room_id = user_data.get("current_room_id", "start")
        current_room_obj = world.get(player_instance.room_id, world.get("start"))
        if not current_room_obj: player_instance.room_id = "start"; current_room_obj = world.get("start")
        player_instance.room = current_room_obj

        raw_inventory = user_data.get("inventory", []) # Load inventory
        player_instance.inventory = [] # Start with fresh inventory before loading
        for item_rep in raw_inventory: # item_rep is {'item_id': 'id', 'quantity': x}
            item_id = item_rep.get("item_id")
            quantity = item_rep.get("quantity", 1)
            if item_id and PLAYER_ITEMS_DATA:
                blueprint_dict = PLAYER_ITEMS_DATA.get(item_id)
                if blueprint_dict:
                    # We need to create ItemInstance from blueprint dict
                    from server.core.content import Item # Local import
                    blueprint_obj = Item(**blueprint_dict) # Create Item object
                    if blueprint_obj.type == "container": # Check type from blueprint object
                        # TODO: Handle loading container contents if saved
                        player_instance.inventory.append(ContainerInstance(blueprint_obj, quantity))
                    else:
                        player_instance.inventory.append(ItemInstance(blueprint_obj, quantity))
                else: print(f"Warning: Inventory item ID '{item_id}' not found for {player_name}")

        saved_equipment = user_data.get("equipment", {}) # Load equipment
        if saved_equipment:
            for slot, item_id_in_save in saved_equipment.items():
                if item_id_in_save and slot in Player.ALL_EQUIPMENT_SLOTS and PLAYER_ITEMS_DATA:
                    item_data_from_db = PLAYER_ITEMS_DATA.get(item_id_in_save)
                    if item_data_from_db: player_instance.equipment[slot] = dict(item_data_from_db)
        player_instance.recalculate_all_stats()

        temp_user_for_player.send_message("\r\nWelcome to the MUD!")
        if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())

        while player_instance.is_alive():
            temp_user_for_player.send_message("\r\n> ")
            msg = temp_user_for_player.read_line()
            if msg is None: break
            stripped_msg = msg.strip()
            if not stripped_msg: continue
            parts = stripped_msg.split(); command_word = parts[0].lower(); args = parts[1:]
            command_word = COMMAND_ALIASES.get(command_word, command_word)
            responded = False

            # ... (Existing command handlers: DIRECTIONS, go, look, sheet, equip, remove, inventory, get, drop) ...
            # These remain as they were in the previous full update of main.py
            if command_word in DIRECTIONS and not args:
                if player_instance.in_combat: temp_user_for_player.send_message("You can't move while in combat!")
                else:
                    direction_to_move = DIRECTIONS[command_word]
                    if player_instance.room and direction_to_move in player_instance.room.exits:
                        new_room_id = player_instance.room.exits[direction_to_move]
                        if new_room_id in world: player_instance.room = world[new_room_id]
                        if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                        else: temp_user_for_player.send_message("The exit leads nowhere.")
                        user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                    else: temp_user_for_player.send_message("You can't go that way.")
                responded = True
            elif command_word == "go":
                if player_instance.in_combat: temp_user_for_player.send_message("You can't move while in combat!")
                elif not args: temp_user_for_player.send_message("Go where?")
                else:
                    direction_input = " ".join(args).lower(); direction_to_move = DIRECTIONS.get(direction_input)
                    if player_instance.room and direction_to_move and direction_to_move in player_instance.room.exits:
                        new_room_id = player_instance.room.exits[direction_to_move]
                        if new_room_id in world: player_instance.room = world[new_room_id]
                        if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                        else: temp_user_for_player.send_message("The exit leads nowhere.")
                        user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                    else: temp_user_for_player.send_message(f"Unknown direction: '{direction_input}'.")
                responded = True
            elif command_word == "look":
                if not args:
                    if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                else: temp_user_for_player.send_message(f"You look at {' '.join(args)} closely.")
                responded = True
            elif command_word == "sheet":
                if not args: temp_user_for_player.send_message(player_instance.display_sheet())
                else: temp_user_for_player.send_message("Usage: sheet")
                responded = True
            elif command_word == "equip":
                if not args: temp_user_for_player.send_message("Equip what?")
                else:
                    item_ref = args[0]; target_slot=None
                    if len(args) > 1: target_slot = USER_FRIENDLY_SLOT_MAP.get(" ".join(args[1:]).lower())
                    temp_user_for_player.send_message(player_instance.equip_item(item_ref, target_slot))
                responded = True
            elif command_word == "remove":
                if not args: temp_user_for_player.send_message("Remove what?")
                else:
                    slot_input = " ".join(args).lower(); target_slot_const = USER_FRIENDLY_SLOT_MAP.get(slot_input)
                    if not target_slot_const: target_slot_const = next((s for s in Player.ALL_EQUIPMENT_SLOTS if s.lower() == slot_input), None)
                    if not target_slot_const: temp_user_for_player.send_message(f"Unknown slot: '{slot_input}'.")
                    else:
                        result = player_instance.remove_item(target_slot_const)
                        if isinstance(result, str): temp_user_for_player.send_message(result)
                        elif isinstance(result, dict): temp_user_for_player.send_message(f"You remove {result.get('name','item')}.")
                responded = True
            elif command_word == "inventory":
                if not args: temp_user_for_player.send_message(player_instance.display_inventory())
                else: temp_user_for_player.send_message("Just type 'inventory' or 'i'.")
                responded = True
            elif command_word == "get":
                if not args: temp_user_for_player.send_message("Get what?")
                elif not player_instance.room: temp_user_for_player.send_message("You aren't in a valid room.")
                else:
                    item_name_to_get = " ".join(args).lower()
                    item_instance_taken = player_instance.room.remove_item_from_ground(item_name_to_get)
                    if item_instance_taken: # This is now an ItemInstance object
                        add_message = player_instance.add_item_to_inventory(item_instance_taken)
                        temp_user_for_player.send_message(add_message)
                    else: temp_user_for_player.send_message(f"You see no '{item_name_to_get}' here.")
                responded = True
            elif command_word == "drop":
                if not args: temp_user_for_player.send_message("Drop what?")
                elif not player_instance.room: temp_user_for_player.send_message("You aren't in a valid room.")
                else:
                    item_name_to_drop = " ".join(args).lower()
                    item_to_drop_instance = player_instance.remove_item_from_inventory(item_name_to_drop, 1)
                    if isinstance(item_to_drop_instance, ItemInstance) :
                        player_instance.room.add_item_to_ground(item_to_drop_instance)
                        temp_user_for_player.send_message(f"You drop {item_to_drop_instance.item_blueprint.name}.")
                    elif isinstance(item_to_drop_instance, str):
                        temp_user_for_player.send_message(item_to_drop_instance)
                    else: temp_user_for_player.send_message(f"You don't have '{item_name_to_drop}'.")
                responded = True
            elif command_word == "kill":
                if player_instance.in_combat: temp_user_for_player.send_message("You are already fighting!")
                elif not args: temp_user_for_player.send_message("Kill what?")
                else:
                    target_name = " ".join(args).lower(); target_mob_instance = None
                    if player_instance.room and player_instance.room.mob_instances:
                        for mob_in_room in player_instance.room.mob_instances:
                            if mob_in_room.name.lower() == target_name and mob_in_room.is_alive():
                                target_mob_instance = mob_in_room; break
                    if target_mob_instance:
                        player_instance.target = target_mob_instance; player_instance.in_combat = True
                        target_mob_instance.target = player_instance; target_mob_instance.in_combat = True
                        add_to_active_combat(player_instance); add_to_active_combat(target_mob_instance)
                        temp_user_for_player.send_message(f"You attack the {target_mob_instance.name}!")
                        attack_messages = resolve_attack(player_instance, target_mob_instance)
                        for line in attack_messages: temp_user_for_player.send_message(line)
                        if not target_mob_instance.is_alive():
                            temp_user_for_player.send_message(f"{ANSI_GREEN}You have defeated the {target_mob_instance.name}!{ANSI_RESET}")
                            player_instance.add_xp(target_mob_instance.xp_value)
                            if player_instance.room: player_instance.room.record_defined_mob_death(target_mob_instance)
                            if player_instance.room and target_mob_instance in player_instance.room.mob_instances:
                                player_instance.room.mob_instances.remove(target_mob_instance)
                            player_instance.target = None; player_instance.in_combat = False
                            remove_from_active_combat(player_instance); remove_from_active_combat(target_mob_instance)
                        elif player_instance.is_alive():
                            temp_user_for_player.send_message(f"The {target_mob_instance.name} retaliates!")
                            mob_attack_messages = resolve_attack(target_mob_instance, player_instance)
                            for line in mob_attack_messages: temp_user_for_player.send_message(line)
                            if not player_instance.is_alive():
                                target_mob_instance.target = None; target_mob_instance.in_combat = False
                                remove_from_active_combat(target_mob_instance)
                                # Player removal from ACTIVE_COMBATANTS handled by finally block or game tick
                    else: temp_user_for_player.send_message(f"There is no living '{target_name}' here.")
                responded = True
            elif command_word == "reload":
                if not args:
                    load_world_and_game_data(); player_instance.recalculate_all_stats(full_heal=True)
                    if player_instance.room_id not in world: player_instance.room_id = "start"
                    player_instance.room = world.get(player_instance.room_id, world.get("start"))
                    temp_user_for_player.send_message("Game data reloaded. Stats refreshed.")
                    if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                responded = True
            if not responded and command_word: temp_user_for_player.send_message("I don't understand that command.")
        if not player_instance.is_alive(): temp_user_for_player.send_message("You have been defeated. Your journey ends here.")
    except ConnectionResetError: print(f"[-] Connection reset by {addr}")
    except Exception as e: print(f"[ERROR] Exception in handle_client for {addr}: {e}"); import traceback; traceback.print_exc()
    finally:
        if player_instance: # Ensure player_instance was created
            remove_connected_player(player_instance) # Remove from global list
            if player_instance.in_combat : remove_from_active_combat(player_instance) # Also remove from combat list
            if player_instance.target and player_instance.target.target == player_instance : # Clear target's target
                player_instance.target.target = None
                player_instance.target.in_combat = False # If target was only fighting this player
                # remove_from_active_combat(player_instance.target) # And from combat list if its combat ends

            if username and user_data: # Save data if user was authenticated
                user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                user_data["equipment"] = {s:(d.get("id",d.get("name")) if isinstance(d,dict) else d) if d else None for s,d in player_instance.equipment.items()}
                # Save inventory: store item_id and quantity for each ItemInstance
                user_data["inventory"] = [
                    {"item_id": inv_item.item_blueprint.id, "quantity": inv_item.quantity}
                    for inv_item in player_instance.inventory if hasattr(inv_item, 'item_blueprint')
                ]
                user_data["level"]=player_instance.level
                user_data["xp"]=player_instance.xp
                user_data["current_hp"]=player_instance.current_hp
                user_data["base_stats"] = player_instance.base_stats # Ensure base stats are saved
                user_data["race_name"] = player_instance.race_name # Ensure race name is saved
                user_data["player_class_name"] = player_instance.player_class_name # Ensure class name is saved
                UserManager.save_user_data(username, user_data)
                print(f"[*] Player {player_instance.name} data saved for user {username}.")
        try:
            if conn: conn.close()
        except: pass
        print(f"[-] Connection closed: {addr}")

def main(): # Unchanged
    print("[SERVER] Starting MUD server..."); load_world_and_game_data()
    tick_thread = threading.Thread(target=game_tick_loop, daemon=True)
    tick_thread.start()
    print(f"[SERVER] Game tick thread started (interval: {GAME_TICK_INTERVAL}s).")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: s.bind((HOST, PORT))
        except OSError as e: print(f"[FATAL] Bind failed: {e}"); return
        s.listen(); print(f"[*] MUD server listening on {HOST}:{PORT}")
        try:
            while True:
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt: print("\n[SERVER] Shutting down MUD server...")
        finally:
            if s: s.close()

if __name__ == "__main__":
    main()
