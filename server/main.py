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
GAME_TICK_INTERVAL = 2

world = {}
mobs_blueprints = {}

ACTIVE_COMBATANTS = []
combat_lock = threading.Lock()
CONNECTED_PLAYERS = []
players_lock = threading.Lock()
CURRENT_GAME_ROUND = 0

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
    players_found = []
    with players_lock:
        for player in CONNECTED_PLAYERS:
            if player.room and player.room.id == room_id_to_check and player.is_alive():
                players_found.append(player)
    return players_found

ANSI_RED = "\033[91m"; ANSI_GREEN = "\033[92m"; ANSI_YELLOW = "\033[93m"; ANSI_RESET = "\033[0m"
COMMAND_ALIASES = {
    "l":"look","char":"sheet","character":"sheet","c":"sheet","score":"sheet","stats":"sheet","st":"sheet",
    "eq":"equip","wear":"equip","wield":"equip","rem":"remove","unequip":"remove",
    "i":"inventory","inv":"inventory","k":"kill","attack":"kill","g":"get","take":"get",
    "secondwind": "secondwind", "rest": "rest", "dash": "dash", "cast": "cast"
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

def load_world_and_game_data():
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

def game_tick():
    global world, mobs_blueprints, ACTIVE_COMBATANTS, CONNECTED_PLAYERS, combat_lock, players_lock, CURRENT_GAME_ROUND

    CURRENT_GAME_ROUND += 1
    try:
        for room_id, room in world.items():
            for mob_def in room.mob_definitions:
                mob_id_to_spawn=mob_def.get("mob_id");max_qty=mob_def.get("max_quantity",1);respawn_secs=mob_def.get("respawn_seconds",300)
                if not mob_id_to_spawn or respawn_secs<=0:continue
                current_live_count=sum(1 for mi in room.mob_instances if mi.mob_blueprint.id==mob_id_to_spawn and mi.is_alive())
                num_to_spawn=max_qty-current_live_count
                if num_to_spawn<=0:continue
                spawned_this_tick_for_def=0
                with combat_lock:
                    for i in range(len(room.defeated_mob_track)-1,-1,-1):
                        tracked_death=room.defeated_mob_track[i]
                        if tracked_death["mob_id"]==mob_id_to_spawn:
                            if time.time()-tracked_death["time_of_death"]>=respawn_secs:
                                blueprint=mobs_blueprints.get(mob_id_to_spawn)
                                if blueprint:
                                    new_mob = MobInstance(blueprint)
                                    new_mob.room = room
                                    room.mob_instances.append(new_mob)
                                    room.defeated_mob_track.pop(i)
                                    spawned_this_tick_for_def+=1
                                    if spawned_this_tick_for_def>=num_to_spawn:break
            with combat_lock:
                for i in range(len(room.pending_item_respawns)-1,-1,-1):
                    item_respawn_entry=room.pending_item_respawns[i];original_def=item_respawn_entry["original_definition"]
                    respawn_item_id=original_def.get("item_id");respawn_qty=original_def.get("quantity",1);item_respawn_secs=original_def.get("respawn_seconds",600)
                    if not respawn_item_id or item_respawn_secs<=0:room.pending_item_respawns.pop(i);continue
                    if time.time()-item_respawn_entry["time_taken"]>=item_respawn_secs:
                        item_blueprint_dict=PLAYER_ITEMS_DATA.get(respawn_item_id)
                        if item_blueprint_dict:
                            from server.core.content import Item
                            actual_blueprint = Item(**item_blueprint_dict)
                            if actual_blueprint.type=="container":new_item_instance=ContainerInstance(actual_blueprint,respawn_qty)
                            else:new_item_instance=ItemInstance(actual_blueprint,respawn_qty)
                            room.add_item_to_ground(new_item_instance)
                            room.pending_item_respawns.pop(i)
                        else:print(f"Warning: Item blueprint ID '{respawn_item_id}' for respawn not found.");room.pending_item_respawns.pop(i)

        with players_lock, combat_lock:
            for room_id, room in world.items():
                players_in_room = get_players_in_room(room_id)
                if not players_in_room: continue
                for mob_instance in list(room.mob_instances):
                    if mob_instance.is_alive() and mob_instance.is_aggressive and not mob_instance.in_combat:
                        potential_target = None
                        for p in players_in_room:
                            if p.is_alive(): potential_target = p; break
                        if potential_target:
                            mob_instance.target = potential_target; mob_instance.in_combat = True
                            if not potential_target.in_combat or not potential_target.target:
                                potential_target.target = mob_instance
                            potential_target.in_combat = True
                            add_to_active_combat(mob_instance); add_to_active_combat(potential_target)
                            if hasattr(potential_target.user, 'send_message'):
                                potential_target.user.send_message(f"{ANSI_RED}{mob_instance.name} suddenly attacks you!{ANSI_RESET}")
                            for p_other in players_in_room:
                                if p_other != potential_target and hasattr(p_other.user, 'send_message'):
                                    p_other.user.send_message(f"{mob_instance.name} attacks {potential_target.name}!")

        combatants_to_remove_after_processing = []
        with combat_lock:
            if ACTIVE_COMBATANTS:
                for entity in list(ACTIVE_COMBATANTS):
                    if not entity.is_alive():
                        combatants_to_remove_after_processing.append(entity)
                        if entity.target and entity.target.target == entity:
                            entity.target.target = None; entity.target.in_combat = False
                        continue
                    if isinstance(entity, MobInstance):
                        entity.tick_status_effects(CURRENT_GAME_ROUND)
                        if entity.target and entity.target.is_alive() and entity.in_combat:
                            attack_messages = resolve_attack(entity, entity.target)
                            if hasattr(entity.target.user, 'send_message'):
                                for line in attack_messages: entity.target.user.send_message(line)
                            if entity.target.room:
                                for other_player in get_players_in_room(entity.target.room.id):
                                    if other_player != entity.target and hasattr(other_player.user, 'send_message'):
                                        for line in attack_messages: other_player.user.send_message(line)
                            if not entity.target.is_alive():
                                entity.target = None; entity.in_combat = False
                                combatants_to_remove_after_processing.append(entity.target)
                                combatants_to_remove_after_processing.append(entity)
                        elif not entity.target or not entity.target.is_alive():
                            entity.target = None; entity.in_combat = False
                            combatants_to_remove_after_processing.append(entity)
                    elif isinstance(entity, Player):
                        if not entity.target or not entity.target.is_alive() or not entity.in_combat:
                             entity.target = None; entity.in_combat = False
                             combatants_to_remove_after_processing.append(entity)
            for entity_to_remove in set(combatants_to_remove_after_processing):
                remove_from_active_combat(entity_to_remove)
                if isinstance(entity_to_remove, MobInstance) and entity_to_remove.target:
                    if entity_to_remove.target.target == entity_to_remove:
                        entity_to_remove.target.target = None
    except Exception as e:print(f"[ERROR] Exception in game_tick: {e}");import traceback;traceback.print_exc()

def game_tick_loop():
    while True:game_tick();time.sleep(GAME_TICK_INTERVAL)

def handle_client(conn, addr):
    print(f"[DEBUG_HANDLE_CLIENT] New connection from {addr}")
    player_instance = None; username = None; user_data = None
    try:
        print("[DEBUG_HANDLE_CLIENT] Attempting UserManager.authenticate_or_create...")
        username, user_data = UserManager.authenticate_or_create(conn)
        print(f"[DEBUG_HANDLE_CLIENT] UserManager.authenticate_or_create returned: username='{username}', user_data keys: {list(user_data.keys()) if user_data else 'None'}")

        if not username or not user_data:
            if conn: conn.close()
            print(f"[DEBUG_HANDLE_CLIENT] Auth failed or no character data for {addr}. Closing connection.")
            return

        player_name = user_data.get("name", username)
        player_class_name = user_data.get("player_class_name", "Fighter")
        player_race_name = user_data.get("race_name", "Human")
        player_base_stats = user_data.get("base_stats")
        print(f"[DEBUG_HANDLE_CLIENT] Preparing Player: name='{player_name}', class='{player_class_name}', race='{player_race_name}', base_stats='{player_base_stats}'")

        class TempUser:
            def __init__(self, c, u): self.connection=c; self.username=u
            def send_message(self, msg):
                print(f"[DEBUG_HANDLE_CLIENT] TempUser sending to {self.username}: '{msg[:100].replace('\r\n', ' ')}...'") # Log snippet
                if self.connection:
                    try: self.connection.sendall(msg.encode()+b"\r\n")
                    except Exception as e_send: print(f"[DEBUG_HANDLE_CLIENT] TempUser send_message EXCEPTION: {e_send}")
            def read_line(self):
                if self.connection:
                    try:
                        raw=self.connection.recv(1024)
                        # print(f"[DEBUG_HANDLE_CLIENT] TempUser raw recv: {raw}")
                        return raw.decode().strip() if raw else None
                    except socket.timeout: # Expected if client is idle
                        # print("[DEBUG_HANDLE_CLIENT] TempUser read_line: socket timeout")
                        return "" # Return empty string on timeout, not None, to keep loop alive if desired
                    except Exception as e_recv:
                        print(f"[DEBUG_HANDLE_CLIENT] TempUser read_line EXCEPTION: {e_recv}")
                        return None
                return None

        temp_user_for_player = TempUser(conn, username)

        print("[DEBUG_HANDLE_CLIENT] Instantiating Player object...")
        player_instance = Player(
            user=temp_user_for_player,
            player_class_name=player_class_name,
            race_name=player_race_name,
            name=player_name,
            base_stats=player_base_stats
        )
        print(f"[DEBUG_HANDLE_CLIENT] Player object created: {player_instance.name}")

        add_connected_player(player_instance)
        print(f"[DEBUG_HANDLE_CLIENT] Player {player_instance.name} added to CONNECTED_PLAYERS.")

        player_instance.level = user_data.get("level", 1)
        player_instance.xp = user_data.get("xp", 0)
        saved_hp = user_data.get("current_hp", player_instance.max_hp)
        player_instance.current_hp = min(saved_hp, player_instance.max_hp) if saved_hp > 0 else player_instance.max_hp
        player_instance.used_abilities_this_rest = set(user_data.get("used_abilities_this_rest", []))
        print(f"[DEBUG_HANDLE_CLIENT] Player stats set: Level={player_instance.level}, HP={player_instance.current_hp}/{player_instance.max_hp}")

        player_instance.room_id = user_data.get("current_room_id", "start")
        print(f"[DEBUG_HANDLE_CLIENT] Player initial room_id: {player_instance.room_id}")
        current_room_obj = world.get(player_instance.room_id) # Use .get for safety
        if not current_room_obj:
            print(f"[DEBUG_HANDLE_CLIENT] Initial room_id '{player_instance.room_id}' not found in world. Defaulting to 'start'.")
            player_instance.room_id = "start"
            current_room_obj = world.get("start") # Get 'start' room object

        if current_room_obj:
            player_instance.room = current_room_obj
            print(f"[DEBUG_HANDLE_CLIENT] Player assigned to room: {player_instance.room.name if player_instance.room else 'None'}")
        else:
            print(f"[DEBUG_HANDLE_CLIENT] CRITICAL: Default 'start' room not found. Player has no room.")
            # This is a critical state, player might not be able to interact
            player_instance.room = None # Ensure it's None

        # ... (inventory and equipment loading as before) ...
        raw_inventory = user_data.get("inventory", [])
        player_instance.inventory = []
        for item_rep in raw_inventory:
            item_id = item_rep.get("item_id")
            quantity = item_rep.get("quantity", 1)
            if item_id and PLAYER_ITEMS_DATA:
                blueprint_dict = PLAYER_ITEMS_DATA.get(item_id)
                if blueprint_dict:
                    from server.core.content import Item
                    blueprint_obj = Item(**blueprint_dict)
                    if blueprint_obj.type == "container":
                        player_instance.inventory.append(ContainerInstance(blueprint_obj, quantity))
                    else:
                        player_instance.inventory.append(ItemInstance(blueprint_obj, quantity))
                else: print(f"Warning: Inventory item ID '{item_id}' not found for {player_name}")
        saved_equipment = user_data.get("equipment", {})
        if saved_equipment:
            for slot, item_id_in_save in saved_equipment.items():
                if item_id_in_save and slot in Player.ALL_EQUIPMENT_SLOTS and PLAYER_ITEMS_DATA:
                    item_data_from_db = PLAYER_ITEMS_DATA.get(item_id_in_save)
                    if item_data_from_db: player_instance.equipment[slot] = dict(item_data_from_db)

        print("[DEBUG_HANDLE_CLIENT] Sending 'Welcome to the MUD!'")
        temp_user_for_player.send_message("\r\nWelcome to the MUD!")
        if player_instance.room:
            print(f"[DEBUG_HANDLE_CLIENT] Sending initial room display for {player_instance.room.name}")
            temp_user_for_player.send_message(player_instance.room.display())
        else:
            print("[DEBUG_HANDLE_CLIENT] Player has no room, not sending room display.")
            temp_user_for_player.send_message("You are in a featureless void. (Error: Room not found)")


        print(f"[DEBUG_HANDLE_CLIENT] Entering command loop for {player_instance.name}. HP: {player_instance.current_hp}")
        while player_instance.is_alive():
            player_instance.reset_turn_actions()
            # print(f"[DEBUG_HANDLE_CLIENT] Top of command loop. Player action reset. Prompting...")
            temp_user_for_player.send_message("\r\n> ")
            msg = temp_user_for_player.read_line()
            print(f"[DEBUG_HANDLE_CLIENT] Received from client: '{msg}'")
            if msg is None:
                print("[DEBUG_HANDLE_CLIENT] msg is None, breaking command loop.")
                break

            stripped_msg = msg.strip()
            if not stripped_msg:
                # print("[DEBUG_HANDLE_CLIENT] Empty message, continuing.")
                continue

            parts = stripped_msg.split(); command_word = parts[0].lower(); args = parts[1:]
            command_word = COMMAND_ALIASES.get(command_word, command_word)
            print(f"[DEBUG_HANDLE_CLIENT] Processing command: '{command_word}' with args: {args}")
            responded = False

            if command_word in DIRECTIONS and not args:
                print("[DEBUG_HANDLE_CLIENT] Matched directional command.")
                # ... (rest of directional command logic) ...
                if player_instance.has_taken_action_this_turn:
                    temp_user_for_player.send_message("You have already taken an action this turn.")
                elif player_instance.in_combat:
                    temp_user_for_player.send_message("You can't move like that while in combat!")
                else:
                    direction_to_move = DIRECTIONS[command_word]
                    if player_instance.room and direction_to_move in player_instance.room.exits:
                        new_room_id = player_instance.room.exits[direction_to_move]
                        if new_room_id in world:
                            player_instance.room = world[new_room_id]
                            player_instance.has_taken_action_this_turn = True
                        if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                        else: temp_user_for_player.send_message("The exit leads nowhere.")
                        user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                    else: temp_user_for_player.send_message("You can't go that way.")
                responded = True
            elif command_word == "go":
                print("[DEBUG_HANDLE_CLIENT] Matched 'go' command.")
                # ... (rest of go command logic) ...
                if player_instance.has_taken_action_this_turn:
                     temp_user_for_player.send_message("You have already taken an action this turn.")
                elif player_instance.in_combat:
                    temp_user_for_player.send_message("You can't move like that while in combat!")
                elif not args: temp_user_for_player.send_message("Go where?")
                else:
                    direction_input = " ".join(args).lower(); direction_to_move = DIRECTIONS.get(direction_input)
                    if player_instance.room and direction_to_move and direction_to_move in player_instance.room.exits:
                        new_room_id = player_instance.room.exits[direction_to_move]
                        if new_room_id in world:
                            player_instance.room = world[new_room_id]
                            player_instance.has_taken_action_this_turn = True
                        if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                        else: temp_user_for_player.send_message("The exit leads nowhere.")
                        user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                    else: temp_user_for_player.send_message(f"Unknown direction: '{direction_input}'.")
                responded = True
            elif command_word == "look":
                print("[DEBUG_HANDLE_CLIENT] Matched 'look' command.")
                if not args:
                    if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                    else: temp_user_for_player.send_message("You are in a void. There is nothing to see.") # Handle no room
                else: temp_user_for_player.send_message(f"You look at {' '.join(args)} closely.")
                responded = True
            elif command_word == "sheet":
                print("[DEBUG_HANDLE_CLIENT] Matched 'sheet' command.")
                if not args: temp_user_for_player.send_message(player_instance.display_sheet())
                else: temp_user_for_player.send_message("Usage: sheet")
                responded = True
            # ... (other command handlers with similar debug prints) ...
            elif command_word == "equip":
                print("[DEBUG_HANDLE_CLIENT] Matched 'equip' command.")
                if player_instance.has_taken_action_this_turn:
                    temp_user_for_player.send_message("You have already taken an action this turn.")
                elif not args: temp_user_for_player.send_message("Equip what?")
                else:
                    item_ref = args[0]; target_slot=None
                    if len(args) > 1: target_slot = USER_FRIENDLY_SLOT_MAP.get(" ".join(args[1:]).lower())
                    result = player_instance.equip_item(item_ref, target_slot)
                    temp_user_for_player.send_message(result)
                    if not result.startswith(("Cannot","You don't have","Invalid","Could not")):
                        player_instance.has_taken_action_this_turn = True
                responded = True
            elif command_word == "remove":
                print("[DEBUG_HANDLE_CLIENT] Matched 'remove' command.")
                if player_instance.has_taken_action_this_turn:
                    temp_user_for_player.send_message("You have already taken an action this turn.")
                elif not args: temp_user_for_player.send_message("Remove what?")
                else:
                    slot_input = " ".join(args).lower(); target_slot_const = USER_FRIENDLY_SLOT_MAP.get(slot_input)
                    if not target_slot_const: target_slot_const = next((s for s in Player.ALL_EQUIPMENT_SLOTS if s.lower() == slot_input), None)
                    if not target_slot_const: temp_user_for_player.send_message(f"Unknown slot: '{slot_input}'.")
                    else:
                        result = player_instance.remove_item(target_slot_const)
                        if isinstance(result, str): temp_user_for_player.send_message(result)
                        elif isinstance(result, dict):
                            temp_user_for_player.send_message(f"You remove {result.get('name','item')}.")
                            player_instance.has_taken_action_this_turn = True
                responded = True
            elif command_word == "inventory":
                print("[DEBUG_HANDLE_CLIENT] Matched 'inventory' command.")
                if not args: temp_user_for_player.send_message(player_instance.display_inventory())
                else: temp_user_for_player.send_message("Just type 'inventory' or 'i'.")
                responded = True
            elif command_word == "get":
                print("[DEBUG_HANDLE_CLIENT] Matched 'get' command.")
                if player_instance.has_taken_action_this_turn:
                    temp_user_for_player.send_message("You have already taken an action this turn.")
                elif not args: temp_user_for_player.send_message("Get what?")
                elif not player_instance.room: temp_user_for_player.send_message("You aren't in a valid room.")
                else:
                    item_name_to_get = " ".join(args).lower()
                    item_instance_taken = player_instance.room.remove_item_from_ground(item_name_to_get)
                    if item_instance_taken:
                        add_message = player_instance.add_item_to_inventory(item_instance_taken)
                        temp_user_for_player.send_message(add_message)
                        player_instance.has_taken_action_this_turn = True
                    else: temp_user_for_player.send_message(f"You see no '{item_name_to_get}' here.")
                responded = True
            elif command_word == "drop":
                print("[DEBUG_HANDLE_CLIENT] Matched 'drop' command.")
                if player_instance.has_taken_action_this_turn:
                    temp_user_for_player.send_message("You have already taken an action this turn.")
                elif not args: temp_user_for_player.send_message("Drop what?")
                elif not player_instance.room: temp_user_for_player.send_message("You aren't in a valid room.")
                else:
                    item_name_to_drop = " ".join(args).lower()
                    item_to_drop_instance = player_instance.remove_item_from_inventory(item_name_to_drop, 1)
                    if isinstance(item_to_drop_instance, ItemInstance) :
                        player_instance.room.add_item_to_ground(item_to_drop_instance)
                        temp_user_for_player.send_message(f"You drop {item_to_drop_instance.item_blueprint.name}.")
                        player_instance.has_taken_action_this_turn = True
                    elif isinstance(item_to_drop_instance, str):
                        temp_user_for_player.send_message(item_to_drop_instance)
                    else: temp_user_for_player.send_message(f"You don't have '{item_name_to_drop}'.")
                responded = True
            elif command_word == "kill":
                print("[DEBUG_HANDLE_CLIENT] Matched 'kill' command.")
                # ... (kill logic with has_taken_action_this_turn set if attack occurs) ...
                if player_instance.has_taken_action_this_turn:
                    temp_user_for_player.send_message("You have already taken an action this turn.")
                elif player_instance.in_combat: temp_user_for_player.send_message("You are already fighting!")
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
                        player_instance.has_taken_action_this_turn = True
                        if not target_mob_instance.is_alive():
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
                    else: temp_user_for_player.send_message(f"There is no living '{target_name}' here.")
                responded = True
            elif command_word == "dash":
                print("[DEBUG_HANDLE_CLIENT] Matched 'dash' command.")
                # ... (dash logic with has_taken_action_this_turn set by Player.use_dash) ...
                if not args:
                    temp_user_for_player.send_message("Dash where? (e.g., dash north)")
                else:
                    direction_input = " ".join(args).lower()
                    direction_to_dash = DIRECTIONS.get(direction_input)
                    if not direction_to_dash:
                        temp_user_for_player.send_message(f"Unknown direction: '{direction_input}'.")
                    else:
                        dash_result = player_instance.use_dash(direction_to_dash, world)
                        if isinstance(dash_result, str):
                            temp_user_for_player.send_message(dash_result)
                        elif isinstance(dash_result, dict) and dash_result.get("success"):
                            if dash_result.get("rooms_moved", 0) > 0 and dash_result.get("final_room_id") in world:
                                player_instance.room = world[dash_result["final_room_id"]]
                                user_data["current_room_id"] = player_instance.room.id
                                temp_user_for_player.send_message(player_instance.room.display())
                            temp_user_for_player.send_message(dash_result.get("message", "You dash."))
                            # player_instance.has_taken_action_this_turn is set in Player.use_dash
                        elif isinstance(dash_result, dict) and not dash_result.get("success"):
                             temp_user_for_player.send_message(dash_result.get("message", "You cannot dash right now."))
                        else:
                            temp_user_for_player.send_message("An unexpected error occurred with dashing.")
                responded = True
            elif command_word == "cast":
                print("[DEBUG_HANDLE_CLIENT] Matched 'cast' command.")
                # ... (cast logic with has_taken_action_this_turn set by Player methods) ...
                if len(args) < 2:
                    temp_user_for_player.send_message("Usage: cast \"<spell name>\" <target_name>")
                else:
                    spell_name_input = ""
                    target_name_parts = []
                    if args[0].startswith("\""):
                        spell_name_buffer = []
                        in_quote = False
                        for i, part in enumerate(args):
                            if part.startswith("\""):
                                in_quote = True
                                spell_name_buffer.append(part[1:])
                            elif in_quote:
                                if part.endswith("\""):
                                    spell_name_buffer.append(part[:-1])
                                    in_quote = False
                                    target_name_parts = args[i+1:]
                                    break
                                else:
                                    spell_name_buffer.append(part)
                            else:
                                spell_name_input = args[0]
                                target_name_parts = args[1:]
                                break
                        if not spell_name_input and spell_name_buffer:
                             spell_name_input = " ".join(spell_name_buffer)
                    else:
                        spell_name_input = args[0]
                        target_name_parts = args[1:]

                    if not target_name_parts:
                        temp_user_for_player.send_message("Who do you want to cast that on?")
                    else:
                        target_name = " ".join(target_name_parts).lower()
                        target_mob_instance = None
                        if player_instance.room and player_instance.room.mob_instances:
                            for mob_in_room in player_instance.room.mob_instances:
                                if mob_in_room.name.lower() == target_name and mob_in_room.is_alive():
                                    target_mob_instance = mob_in_room
                                    break

                        if not target_mob_instance:
                            temp_user_for_player.send_message(f"You don't see '{target_name}' here or they are not a valid target.")
                        else:
                            cast_messages = []
                            if spell_name_input.lower() == "fire bolt":
                                cast_messages = player_instance.cast_spell_attack("Fire Bolt", target_mob_instance, resolve_attack, CURRENT_GAME_ROUND)
                            elif spell_name_input.lower() == "ray of frost":
                                cast_messages = player_instance.cast_spell_attack("Ray of Frost", target_mob_instance, resolve_attack, CURRENT_GAME_ROUND)
                            else:
                                temp_user_for_player.send_message(f"You don't know how to cast '{spell_name_input}'.")

                            if cast_messages:
                                for line in cast_messages:
                                    temp_user_for_player.send_message(line)
                                if not target_mob_instance.is_alive() and any("hits" in m.lower() or "critical hit" in m.lower() for m in cast_messages):
                                    player_instance.add_xp(target_mob_instance.xp_value)
                                    if player_instance.room: player_instance.room.record_defined_mob_death(target_mob_instance)
                                    if player_instance.room and target_mob_instance in player_instance.room.mob_instances:
                                        player_instance.room.mob_instances.remove(target_mob_instance)
                                    if player_instance.target == target_mob_instance:
                                        player_instance.target = None
                                        player_instance.in_combat = False
                                    remove_from_active_combat(player_instance)
                                    remove_from_active_combat(target_mob_instance)
                responded = True
            elif command_word == "reload":
                print("[DEBUG_HANDLE_CLIENT] Matched 'reload' command.")
                if not args:
                    load_world_and_game_data()
                    player_instance.recalculate_all_stats(full_heal=True)
                    if player_instance.room_id not in world:
                        player_instance.room_id = "start"
                    player_instance.room = world.get(player_instance.room_id, world.get("start"))
                    temp_user_for_player.send_message("Game data reloaded. Stats refreshed.")
                    if player_instance.room:
                        temp_user_for_player.send_message(player_instance.room.display())
                else:
                    temp_user_for_player.send_message("Usage: reload")
                responded = True
            elif command_word == "rest":
                print("[DEBUG_HANDLE_CLIENT] Matched 'rest' command.")
                if player_instance.has_taken_action_this_turn:
                     temp_user_for_player.send_message("You have already taken an action this turn.")
                elif player_instance.in_combat:
                    temp_user_for_player.send_message("You cannot rest while in combat!")
                elif args:
                    temp_user_for_player.send_message("Usage: rest")
                else:
                    message = player_instance.perform_long_rest()
                    temp_user_for_player.send_message(message)
                    player_instance.has_taken_action_this_turn = True
                responded = True
            elif command_word == "secondwind":
                print("[DEBUG_HANDLE_CLIENT] Matched 'secondwind' command.")
                if not args:
                    message = player_instance.use_second_wind()
                    temp_user_for_player.send_message(message)
                else:
                    temp_user_for_player.send_message("Usage: secondwind")
                responded = True

            if not responded and command_word:
                print(f"[DEBUG_HANDLE_CLIENT] Unknown command: '{command_word}'")
                temp_user_for_player.send_message("I don't understand that command.")

            # print(f"[DEBUG_HANDLE_CLIENT] End of command processing for '{command_word}'. Responded: {responded}")

        if not player_instance.is_alive():
            print(f"[DEBUG_HANDLE_CLIENT] Player {player_instance.name} is no longer alive. Sending defeat message.")
            temp_user_for_player.send_message("You have been defeated. Your journey ends here.")
        print(f"[DEBUG_HANDLE_CLIENT] Exited command loop for {player_instance.name}.")

    except ConnectionResetError: print(f"[-] Connection reset by {addr}")
    except Exception as e: print(f"[ERROR] Exception in handle_client for {addr}: {e}"); import traceback; traceback.print_exc()
    finally:
        print(f"[DEBUG_HANDLE_CLIENT] Finally block for {username or 'unknown user'}.")
        if player_instance:
            remove_connected_player(player_instance)
            if player_instance.in_combat : remove_from_active_combat(player_instance)
            if player_instance.target and hasattr(player_instance.target, 'target') and player_instance.target.target == player_instance :
                player_instance.target.target = None
                player_instance.target.in_combat = False

            if username and user_data:
                user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                user_data["equipment"] = {s:(d.get("id",d.get("name")) if isinstance(d,dict) else d) if d else None for s,d in player_instance.equipment.items()}
                user_data["inventory"] = [
                    {"item_id": inv_item.item_blueprint.id, "quantity": inv_item.quantity}
                    for inv_item in player_instance.inventory if hasattr(inv_item, 'item_blueprint')
                ]
                user_data["level"]=player_instance.level
                user_data["xp"]=player_instance.xp
                user_data["current_hp"]=player_instance.current_hp
                user_data["base_stats"] = player_instance.base_stats
                user_data["race_name"] = player_instance.race_name
                user_data["player_class_name"] = player_instance.player_class_name
                user_data["used_abilities_this_rest"] = list(player_instance.used_abilities_this_rest)
                UserManager.save_user_data(username, user_data)
                print(f"[*] Player {player_instance.name} data saved for user {username}.")
        try:
            if conn: conn.close()
        except: pass
        print(f"[-] Connection closed: {addr}")

def main():
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
