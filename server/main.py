import socket
import threading
import time
import random
import traceback # Added for detailed exception logging
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
players_lock = threading.RLock() # Changed to RLock
CURRENT_GAME_ROUND = 0

def add_to_active_combat(entity):
    with combat_lock:
        if entity not in ACTIVE_COMBATANTS: ACTIVE_COMBATANTS.append(entity)
def remove_from_active_combat(entity):
    with combat_lock:
        if entity in ACTIVE_COMBATANTS: ACTIVE_COMBATANTS.remove(entity)

def add_connected_player(player_instance):
    player_name_for_log = player_instance.name if player_instance else "None"
    print(f"[ADD_PLAYER_DIAG] Entered add_connected_player for {player_name_for_log}")
    try:
        print(f"[ADD_PLAYER_DIAG] Attempting to acquire players_lock for {player_name_for_log}")
        with players_lock:
            print(f"[ADD_PLAYER_DIAG] Acquired players_lock for {player_name_for_log}")
            print(f"[ADD_PLAYER_DIAG] Checking if {player_name_for_log} in CONNECTED_PLAYERS. Current length: {len(CONNECTED_PLAYERS)}")
            if player_instance not in CONNECTED_PLAYERS:
                print(f"[ADD_PLAYER_DIAG] Appending {player_name_for_log} to CONNECTED_PLAYERS")
                CONNECTED_PLAYERS.append(player_instance)
            else:
                print(f"[ADD_PLAYER_DIAG] {player_name_for_log} already in CONNECTED_PLAYERS.")
    except Exception as e_add_player:
        print(f"!!! ERROR in add_connected_player for {player_name_for_log} !!!")
        print(traceback.format_exc())
    print(f"[ADD_PLAYER_DIAG] Exiting add_connected_player for {player_name_for_log}")

def remove_connected_player(player_instance):
    with players_lock:
        if player_instance in CONNECTED_PLAYERS: CONNECTED_PLAYERS.remove(player_instance)

def get_players_in_room(room_id_to_check):
    players_found = []
    with players_lock:
        for player in CONNECTED_PLAYERS:
            if player.room and \
               player.room.id == room_id_to_check and \
               player.is_alive() and \
               not player.is_dead and \
               not (hasattr(player, 'is_reloading') and player.is_reloading): # Check is_reloading
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
    print(f"\n{'='*20} load_world_and_game_data() CALLED {'='*20}")
    # import traceback # Already imported at top of file
    traceback.print_stack()
    print(f"{'='*50}\n")
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
                            if p.is_alive():
                                potential_target = p; break
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
                    if not entity.is_alive() or (hasattr(entity, 'is_dead') and entity.is_dead):
                        combatants_to_remove_after_processing.append(entity)
                        if entity.target and hasattr(entity.target, 'target') and entity.target.target == entity:
                            entity.target.target = None
                            if hasattr(entity.target, 'in_combat'): entity.target.in_combat = False
                        continue

                    if isinstance(entity, MobInstance):
                        # AGGRESSIVE TARGET VALIDATION AT THE START OF MOB'S TURN
                        target_still_valid = True
                        reason = ""

                        if not entity.target:
                            target_still_valid = False
                            reason = "has no target"
                        elif not hasattr(entity.target, 'is_alive'): # Should not happen with proper types
                            target_still_valid = False
                            reason = "target object lacks 'is_alive' method"
                        elif not entity.target.is_alive():
                            target_still_valid = False
                            reason = f"target '{entity.target.name if hasattr(entity.target,'name') else 'Unknown'}' is not alive (HP <= 0)"
                        elif hasattr(entity.target, 'is_dead') and entity.target.is_dead: # Specifically for players
                            target_still_valid = False
                            reason = f"target Player '{entity.target.name}' is dead"
                        elif isinstance(entity.target, Player): # Player-specific connection checks
                            if entity.target.user is None:
                                target_still_valid = False
                                reason = f"target Player '{entity.target.name}' has no user object (disconnected)"
                            elif entity.target.user.connection is None:
                                target_still_valid = False
                                reason = f"target Player '{entity.target.name}' has no connection (disconnected)"
                            elif entity.target not in CONNECTED_PLAYERS:
                                target_still_valid = False
                                reason = f"target Player '{entity.target.name}' is not in CONNECTED_PLAYERS"

                        if not target_still_valid:
                            print(f"[GAME_TICK_MOB_VALIDATION] Mob {entity.name} {reason}. Disengaging.")
                            entity.target = None
                            entity.in_combat = False
                            combatants_to_remove_after_processing.append(entity)
                            continue # Crucial: Skip the rest of this mob's turn

                        # If target is valid, proceed with the mob's turn
                        entity.tick_status_effects(CURRENT_GAME_ROUND)

                        # Now, if the mob is in combat (it should be if target is valid and it's aggressive or was already fighting)
                        if entity.in_combat: # entity.target is guaranteed to be valid here due to checks above
                            attack_messages = resolve_attack(entity, entity.target)

                            # Message the target (if player and STILL valid after attack)
                            # resolve_attack might have killed the player, Player.handle_death might have run.
                            if entity.target and isinstance(entity.target, Player) and \
                               entity.target.user and entity.target.user.connection and \
                               entity.target.is_alive() and not entity.target.is_dead: # Re-check player validity for messaging
                                for line in attack_messages: entity.target.user.send_message(line)

                            # Message other players in the room
                            # entity.target might have become None if it died AND was cleared by resolve_attack or handle_death
                            if entity.target and entity.target.room:
                                for other_player in get_players_in_room(entity.target.room.id):
                                    if other_player != entity.target: # Avoid double-messaging target
                                        if other_player.user and other_player.user.connection:
                                            for line in attack_messages: other_player.user.send_message(line)

                            # Check if target died from THIS attack sequence
                            # It's possible entity.target became None if handle_death cleared it from the mob
                            if entity.target and (not entity.target.is_alive() or (hasattr(entity.target, 'is_dead') and entity.target.is_dead)):
                                print(f"[GAME_TICK_COMBAT] Target {entity.target.name if hasattr(entity.target,'name') else 'UnknownTarget'} confirmed dead after {entity.name}'s attack.")
                                combatants_to_remove_after_processing.append(entity.target) # Add the now-dead target
                                entity.target = None # Mob disengages
                                entity.in_combat = False
                                combatants_to_remove_after_processing.append(entity) # Add the mob itself
                            elif not entity.target: # If resolve_attack or handle_death already cleared the mob's target
                                print(f"[GAME_TICK_COMBAT] Mob {entity.name}'s target was cleared during its attack. Ensuring mob disengages.")
                                entity.in_combat = False # Ensure it's not stuck in combat
                                combatants_to_remove_after_processing.append(entity)
                        # No 'else if entity.in_combat:' here, because if it was in combat but target was invalid,
                        # the top validation block would have caught it and skipped to 'continue'.

                    elif isinstance(entity, Player):
                        # Player's turn in combat (if any actions were to be automated or timed for players in game_tick)
                        target_is_invalid = False
                        if not entity.target:
                            target_is_invalid = True
                        elif not entity.target.is_alive():
                            target_is_invalid = True

                        if target_is_invalid and entity.in_combat:
                            print(f"[GAME_TICK_COMBAT] Player {entity.name}'s target is invalid. Removing player from combat.")
                            entity.target = None
                            entity.in_combat = False
                            combatants_to_remove_after_processing.append(entity)
                        elif not entity.in_combat and entity in ACTIVE_COMBATANTS:
                             combatants_to_remove_after_processing.append(entity)

            for entity_to_remove in set(combatants_to_remove_after_processing):
                remove_from_active_combat(entity_to_remove)
                if isinstance(entity_to_remove, MobInstance) and entity_to_remove.target and isinstance(entity_to_remove.target, Player):
                    if entity_to_remove.target.target == entity_to_remove:
                        entity_to_remove.target.target = None
                        entity_to_remove.target.in_combat = False
                        still_targeted = False
                        for combatant in ACTIVE_COMBATANTS:
                            if combatant != entity_to_remove and hasattr(combatant, 'target') and combatant.target == entity_to_remove.target:
                                still_targeted = True
                                break
                        if not still_targeted:
                             combatants_to_remove_after_processing.append(entity_to_remove.target)

            for entity_to_remove in set(combatants_to_remove_after_processing):
                 remove_from_active_combat(entity_to_remove)

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
            def __init__(self, c, u):
                self.connection = c
                self.username = u
                self._recv_buffer = b""
                self.MAX_BUFFER_SIZE = 4096

            def send_message(self, msg):
                if self.connection:
                    try:
                        self.connection.sendall(msg.encode() + b"\r\n")
                    except Exception as e_send:
                        print(f"[DEBUG_HANDLE_CLIENT] TempUser send_message EXCEPTION: {e_send}")
                        self.connection = None

            def read_line(self):
                if not self.connection:
                    return None
                try:
                    if b"\n" in self._recv_buffer:
                        line, self._recv_buffer = self._recv_buffer.split(b"\n", 1)
                        return line.decode(errors='ignore').strip()
                    if b"\r" in self._recv_buffer:
                        line, self._recv_buffer = self._recv_buffer.split(b"\r", 1)
                        return line.decode(errors='ignore').strip()
                except Exception as e_decode_buffer:
                     print(f"[DEBUG_HANDLE_CLIENT] TempUser read_line (buffer decode) EXCEPTION: {e_decode_buffer}")
                     self._recv_buffer = b""
                while True:
                    try:
                        data = self.connection.recv(1024)
                        if not data:
                            self.connection = None
                            if self._recv_buffer:
                                line = self._recv_buffer
                                self._recv_buffer = b""
                                return line.decode(errors='ignore').strip()
                            return None
                        self._recv_buffer += data
                        if len(self._recv_buffer) > self.MAX_BUFFER_SIZE:
                            print(f"[DEBUG_HANDLE_CLIENT] TempUser read_line: Buffer overflow for {self.username}. Clearing buffer.")
                            self._recv_buffer = b""
                            self.connection = None
                            return None
                        if b"\n" in self._recv_buffer:
                            line, self._recv_buffer = self._recv_buffer.split(b"\n", 1)
                            return line.decode(errors='ignore').strip()
                        if b"\r" in self._recv_buffer:
                            line, self._recv_buffer = self._recv_buffer.split(b"\r", 1)
                            return line.decode(errors='ignore').strip()
                    except socket.timeout:
                        return ""
                    except Exception as e_recv:
                        print(f"[DEBUG_HANDLE_CLIENT] TempUser read_line (socket recv) EXCEPTION: {e_recv}")
                        self.connection = None
                        if self._recv_buffer:
                            line = self._recv_buffer
                            self._recv_buffer = b""
                            return line.decode(errors='ignore').strip()
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
        print(f"[EARLY_DIAG] Player object returned from constructor. Name: {player_instance.name if player_instance else 'None'}")
        print(f"[DEBUG_HANDLE_CLIENT] Player object created: {player_instance.name}")

        try:
            add_connected_player(player_instance)
            print(f"[DEBUG_HANDLE_CLIENT] Player {player_instance.name} added to CONNECTED_PLAYERS.")

            player_instance.level = user_data.get("level", 1)
            player_instance.xp = user_data.get("xp", 0)
            saved_hp = user_data.get("current_hp", player_instance.max_hp)
            player_instance.current_hp = min(saved_hp, player_instance.max_hp) if saved_hp > 0 else player_instance.max_hp

            if player_instance.current_hp <= 0:
                player_instance.is_dead = True
                player_instance.current_hp = 0
                player_instance.in_combat = False
                player_instance.target = None
                print(f"[DEBUG_HANDLE_CLIENT] Player {player_instance.name} loaded in a dead state.")
            else:
                player_instance.is_dead = False

            # Explicitly reset combat state for all logins to ensure a clean slate
            player_instance.in_combat = False
            player_instance.target = None
            # If player was in ACTIVE_COMBATANTS from a previous session (unlikely but possible if server didn't clear), remove them.
            if player_instance in ACTIVE_COMBATANTS:
                remove_from_active_combat(player_instance)


            player_instance.used_abilities_this_rest = set(user_data.get("used_abilities_this_rest", []))
            print(f"[DEBUG_HANDLE_CLIENT] Player stats set: Level={player_instance.level}, HP={player_instance.current_hp}/{player_instance.max_hp}, Dead: {player_instance.is_dead}, Combat: {player_instance.in_combat}")

            player_instance.room_id = user_data.get("current_room_id", "start")
            print(f"[DEBUG_HANDLE_CLIENT] Player initial room_id: {player_instance.room_id}")
            current_room_obj = world.get(player_instance.room_id)
            if not current_room_obj:
                print(f"[DEBUG_HANDLE_CLIENT] Initial room_id '{player_instance.room_id}' not found in world. Defaulting to 'start'.")
                player_instance.room_id = "start"
                current_room_obj = world.get("start")

            if current_room_obj:
                player_instance.room = current_room_obj
                print(f"[DEBUG_HANDLE_CLIENT] Player assigned to room: {player_instance.room.name if player_instance.room else 'None'}")
            else:
                print(f"[DEBUG_HANDLE_CLIENT] CRITICAL: Default 'start' room not found. Player has no room.")
                player_instance.room = None

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

            if not player_instance.is_dead:
                if player_instance.room:
                    print(f"[DIAGNOSTIC_LOG] Attempting to display room for alive player. ID: '{player_instance.room.id}', Name: '{player_instance.room.name}'")
                    room_display_content = player_instance.room.display()
                    print(f"[DIAGNOSTIC_LOG] Content from player_instance.room.display():\n{room_display_content}")
                    temp_user_for_player.send_message(room_display_content)
                    print(f"[DIAGNOSTIC_LOG] Attempted to send room display to client.")
                else:
                    print("[DEBUG_HANDLE_CLIENT] Player has no room, not sending room display.")
                    temp_user_for_player.send_message("You are in a featureless void. (Error: Room not found)")
                    print(f"[DIAGNOSTIC_LOG] Player has no room. Sent 'featureless void' message.")
            elif player_instance.is_dead:
                 if hasattr(player_instance.user, 'send_message'):
                    player_instance.user.send_message(f"{ANSI_YELLOW}Your soul lingers from a previous demise. Type 'respawn' to return to the Church of Testing, or 'quit' to embrace the void.{ANSI_RESET}")

            socket_timeout = conn.gettimeout()
            print(f"[DEBUG_HANDLE_CLIENT] Socket timeout for {username}: {socket_timeout}")

            print(f"[DIAGNOSTIC_LOG] Entering main client loop for {player_instance.name}. HP: {player_instance.current_hp}, Dead: {player_instance.is_dead}. About to send first prompt and wait for command.")

        except Exception as e_setup:
            print(f"!!! CRITICAL ERROR in handle_client post-Player instantiation for {username} !!!")
            print(f"Exception Type: {type(e_setup)}")
            print(f"Exception Args: {e_setup.args}")
            print(traceback.format_exc())
            player_instance = None

        connection_active = True
        while player_instance and connection_active:
            if temp_user_for_player.connection is None:
                print(f"[DEBUG_HANDLE_CLIENT] Connection marked as closed for {username}. Breaking main client loop.")
                connection_active = False
                break

            # Read command input once at the beginning of the loop iteration
            current_prompt = "\r\n> " if (player_instance and not player_instance.is_dead) else f"{ANSI_RED}[DEAD]{ANSI_RESET} > "
            temp_user_for_player.send_message(current_prompt)
            msg = temp_user_for_player.read_line()

            if msg is None:
                print(f"[HC_DIAG_MAIN_LOOP_MSG_NONE] Connection lost (msg is None) for {player_instance.name if player_instance else username}.")
                connection_active = False
                break # Exit main while loop

            # Universal log for raw and stripped message
            print(f"[HC_DIAG_MAIN_LOOP_CMD_RAW] Raw command for {player_instance.name if player_instance else username} (Dead={player_instance.is_dead if player_instance else 'N/A'}): '{msg}'")
            stripped_msg = msg.strip()
            # It's okay if stripped_msg is empty, the respective loops will handle it (e.g. continue)
            print(f"[HC_DIAG_MAIN_LOOP_CMD_STRIPPED] Stripped command for {player_instance.name if player_instance else username}: '{stripped_msg}'")

            if player_instance.is_dead:
                print(f"[HC_DIAG_BRANCH] Player {player_instance.name} IS DEAD. Processing dead commands.")
                # Dead Player Command Loop Logic
                command_word_dead = stripped_msg.lower() # Process the command read at the start of the iteration

                if command_word_dead == "respawn":
                    print(f"[HC_DIAG_DEAD_CMD] 'respawn' command received. Attempting respawn for {player_instance.name}.")
                    if hasattr(player_instance, 'attempt_respawn'):
                        respawned = player_instance.attempt_respawn()
                        print(f"[HC_DIAG_DEAD_CMD] player_instance.attempt_respawn() returned: {respawned} for {player_instance.name}")
                        if respawned:
                            print(f"[HC_DIAG_DEAD_CMD] Player {player_instance.name} successfully respawned in player object.")
                            print(f"[HC_DIAG_DEAD_CMD] Post-Respawn State (Player Obj): Name={player_instance.name}, Dead={player_instance.is_dead}, HP={player_instance.current_hp}, Combat={player_instance.in_combat}, Target={player_instance.target}, RoomID={player_instance.room_id}")
                            player_instance.room = world.get(player_instance.room_id)
                            if player_instance.room:
                                print(f"[HC_DIAG_DEAD_CMD] Sending room display for '{player_instance.room.name}' to {player_instance.name}")
                                temp_user_for_player.send_message(player_instance.room.display())
                            else:
                                temp_user_for_player.send_message("You respawn into a strange void. (Error: Respawn room not found)")
                            # No break here, the main loop condition 'player_instance.is_dead' will be false next iteration
                        # else: No specific message if respawn failed here, attempt_respawn sends its own.
                    else:
                        temp_user_for_player.send_message("Respawn system not fully implemented on player object.")
                elif command_word_dead == "quit" or command_word_dead == "exit":
                    print(f"[HC_DIAG_DEAD_CMD] '{command_word_dead}' command received. Closing connection for {player_instance.name}.")
                    temp_user_for_player.send_message("You embrace the void...")
                    connection_active = False # This will break the main while loop
                elif not command_word_dead: # Empty command
                    pass # Just loop again for prompt
                else:
                    print(f"[HC_DIAG_DEAD_CMD] Unknown dead command '{command_word_dead}' for {player_instance.name}.")
                    temp_user_for_player.send_message("Your spirit is too weak to do that. Type 'respawn' to return to life or 'quit' to depart.")

            else: # Player is ALIVE
                print(f"[HC_DIAG_BRANCH] Player {player_instance.name} IS ALIVE. Processing alive commands.")
                print(f"[HC_DIAG_ALIVE_LOOP_REENTRY] Player {player_instance.name} ALIVE LOOP ITERATION. State: Dead={player_instance.is_dead}, HP={player_instance.current_hp}, Combat={player_instance.in_combat}, Target={player_instance.target}, RoomID={player_instance.room_id if player_instance.room else 'None'}")

                player_instance.reset_turn_actions()

                if not stripped_msg: # Empty command from alive player
                    continue

                parts = stripped_msg.split(); command_word = parts[0].lower(); args = parts[1:]
                command_word = COMMAND_ALIASES.get(command_word, command_word)
                print(f"[HC_DIAG_ALIVE_CMD_PARSED] Parsed alive command: '{command_word}', Args: {args}")
                responded = False

                if command_word in DIRECTIONS and not args:
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
                    if not args:
                        if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                        else: temp_user_for_player.send_message("You are in a void. There is nothing to see.")
                    else: temp_user_for_player.send_message(f"You look at {' '.join(args)} closely.")
                    responded = True
                elif command_word == "sheet":
                    if not args: temp_user_for_player.send_message(player_instance.display_sheet())
                    else: temp_user_for_player.send_message("Usage: sheet")
                    responded = True
                elif command_word == "equip":
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
                    if not args: temp_user_for_player.send_message(player_instance.display_inventory())
                    else: temp_user_for_player.send_message("Just type 'inventory' or 'i'.")
                    responded = True
                elif command_word == "get":
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
                    print(f"[HC_KILL_CMD_START] {player_instance.name} processing 'kill {args}'")
                    print(f"[HC_KILL_CMD_CHECK_ACTION_TURN] Before check has_taken_action_this_turn. Value: {player_instance.has_taken_action_this_turn}")
                    if player_instance.has_taken_action_this_turn:
                        temp_user_for_player.send_message("You have already taken an action this turn.")
                    elif player_instance.in_combat:
                        print(f"[HC_KILL_CMD_ALREADY_IN_COMBAT] Player {player_instance.name} is already in combat.")
                        temp_user_for_player.send_message("You are already fighting!")
                    elif not args: temp_user_for_player.send_message("Kill what?")
                    else:
                        target_name = " ".join(args).lower()
                        print(f"[HC_KILL_CMD_FIND_MOB_START] Searching for mob: {target_name}")
                        target_mob_instance = None
                        if player_instance.room and player_instance.room.mob_instances:
                            for mob_in_room in player_instance.room.mob_instances:
                                print(f"[HC_KILL_CMD_FIND_MOB_CHECKING] Checking mob: {mob_in_room.name} (Alive: {mob_in_room.is_alive()})")
                                if mob_in_room.name.lower() == target_name and mob_in_room.is_alive():
                                    target_mob_instance = mob_in_room; break
                        print(f"[HC_KILL_CMD_FIND_MOB_RESULT] Found mob: {target_mob_instance.name if target_mob_instance else 'None'}")
                        if target_mob_instance:
                            print(f"[HC_KILL_CMD_MOB_FOUND] Mob {target_mob_instance.name} found. Setting combat states.")
                            player_instance.target = target_mob_instance; player_instance.in_combat = True
                            target_mob_instance.target = player_instance; target_mob_instance.in_combat = True
                            print(f"[HC_KILL_CMD_ADD_TO_COMBAT] Adding {player_instance.name} and {target_mob_instance.name} to active combat.")
                            add_to_active_combat(player_instance); add_to_active_combat(target_mob_instance)
                            temp_user_for_player.send_message(f"You attack the {target_mob_instance.name}!")

                            print(f"[HC_KILL_CMD_BEFORE_RESOLVE_ATTACK] About to call resolve_attack for {player_instance.name} vs {target_mob_instance.name}")
                            attack_messages = resolve_attack(player_instance, target_mob_instance)
                            print(f"[HC_KILL_CMD_AFTER_RESOLVE_ATTACK] After resolve_attack. Player alive: {player_instance.is_alive()}. Attack messages: {attack_messages}")
                            for line in attack_messages: temp_user_for_player.send_message(line)

                            player_instance.has_taken_action_this_turn = True
                            print(f"[HC_KILL_CMD_CHECK_PLAYER_DEATH_BREAK] Before 'if not player_instance.is_alive(): break'. Player alive: {player_instance.is_alive()}")
                            if not player_instance.is_alive():
                                print(f"[HC_KILL_CMD_PLAYER_DIED_DURING_ATTACK] Player {player_instance.name} died during their own attack sequence. Breaking from command processing.")
                                break # Break from main while player_instance and connection_active loop

                            if not target_mob_instance.is_alive():
                                print(f"[HC_KILL_CMD_TARGET_DEFEATED] Target {target_mob_instance.name} defeated by player.")
                                player_instance.add_xp(target_mob_instance.xp_value)
                                if player_instance.room:
                                    player_instance.room.record_defined_mob_death(target_mob_instance)
                                if player_instance.target == target_mob_instance:
                                    player_instance.target = None
                                    player_instance.in_combat = False
                                remove_from_active_combat(player_instance)
                                remove_from_active_combat(target_mob_instance)
                                print(f"[COMBAT_LOG] Player {player_instance.name} defeated {target_mob_instance.name}. Player combat state cleared.")
                            elif player_instance.is_alive(): # Check player alive again before mob retaliates
                                print(f"[HC_KILL_CMD_MOB_RETALIATION_START] Mob {target_mob_instance.name} retaliating.")
                                temp_user_for_player.send_message(f"The {target_mob_instance.name} retaliates!")
                                mob_attack_messages = resolve_attack(target_mob_instance, player_instance)
                                print(f"[HC_KILL_CMD_MOB_RETALIATION_END] After mob retaliation. Player alive: {player_instance.is_alive()}. Mob attack messages: {mob_attack_messages}")
                                for line in mob_attack_messages: temp_user_for_player.send_message(line)
                                # Player might die here, death will be handled by main loop check or game_tick
                        else: temp_user_for_player.send_message(f"There is no living '{target_name}' here.")
                    print(f"[HC_KILL_CMD_END] End of 'kill' command processing for {player_instance.name}.")
                    responded = True
                elif command_word == "dash":
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
                            elif isinstance(dash_result, dict) and not dash_result.get("success"):
                                 temp_user_for_player.send_message(dash_result.get("message", "You cannot dash right now."))
                            else:
                                temp_user_for_player.send_message("An unexpected error occurred with dashing.")
                    responded = True
                elif command_word == "cast":
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
                            elif not spell_name_input and not spell_name_buffer and not target_name_parts:
                                spell_name_input = ""
                                target_name_parts = args[1:]
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
                                    if not player_instance.is_alive():
                                        print(f"[HC_CAST_PLAYER_DIED] Player {player_instance.name} died during spell cast. Breaking.")
                                        break # Break from main while
                                    if not target_mob_instance.is_alive() and any("hits" in m.lower() or "critical hit" in m.lower() for m in cast_messages):
                                        player_instance.add_xp(target_mob_instance.xp_value)
                                        if player_instance.room:
                                            player_instance.room.record_defined_mob_death(target_mob_instance)
                                        if player_instance.target == target_mob_instance:
                                            player_instance.target = None
                                            player_instance.in_combat = False
                                        remove_from_active_combat(target_mob_instance)
                                        if not any(e for e in ACTIVE_COMBATANTS if hasattr(e, 'target') and e.target == player_instance):
                                             remove_from_active_combat(player_instance)
                                        print(f"[COMBAT_LOG] Player {player_instance.name} defeated {target_mob_instance.name} with a spell. Player combat state cleared.")
                    responded = True
                elif command_word == "reload":
                    if not args:
                        player_instance.is_reloading = True # Set flag before operations
                        load_world_and_game_data()
                        player_instance.recalculate_all_stats(full_heal=True)

                        # Clear combat state BEFORE room change and messages
                        player_instance.in_combat = False
                        player_instance.target = None
                        if player_instance in ACTIVE_COMBATANTS: # Check before removing
                            remove_from_active_combat(player_instance)
                        print(f"[DEBUG_RELOAD] Cleared combat state for {player_instance.name} during reload.")

                        target_room_id = player_instance.room_id if player_instance.room_id in world else "start"
                        player_instance.room_id = target_room_id
                        player_instance.room = world.get(target_room_id)

                        temp_user_for_player.send_message("Game data reloaded. Stats refreshed.")
                        if player_instance.room:
                            temp_user_for_player.send_message(player_instance.room.display())
                        player_instance.is_reloading = False # Clear flag after all operations
                    else:
                        temp_user_for_player.send_message("Usage: reload")
                    responded = True
                elif command_word == "rest":
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
                    if not args:
                        message = player_instance.use_second_wind()
                        temp_user_for_player.send_message(message)
                    else:
                        temp_user_for_player.send_message("Usage: secondwind")
                    responded = True

                if not responded and command_word:
                    print(f"[DEBUG_HANDLE_CLIENT] Unknown command: '{command_word}'")
                    temp_user_for_player.send_message("I don't understand that command.")

            if temp_user_for_player.connection is None:
                print(f"[DEBUG_HANDLE_CLIENT] Connection lost for {username} during alive loop (pre-death check). Breaking.")
                connection_active = False

            elif player_instance and player_instance.is_dead:
                print(f"[HC_DEAD_LOOP_ENTRY] Player {player_instance.name} entering dead loop. HP: {player_instance.current_hp}, Dead: {player_instance.is_dead}, Combat: {player_instance.in_combat}")
                while player_instance and player_instance.is_dead:
                    if temp_user_for_player.connection is None:
                        print(f"[HC_DEAD_LOOP_CONN_LOST] Connection lost for {username} at start of dead loop iteration.")
                        connection_active = False; break

                    temp_user_for_player.send_message(f"{ANSI_RED}[DEAD]{ANSI_RESET} > ")
                    msg = temp_user_for_player.read_line()
                    print(f"[HC_DEAD_LOOP_MSG_RAW] Raw dead command for {player_instance.name}: '{msg}'")
                    if msg is None:
                        print(f"[HC_DEAD_LOOP_MSG_NONE] Connection lost (msg is None) while player {player_instance.name} was dead.")
                        connection_active = False; break

                    stripped_msg = msg.strip().lower()
                    print(f"[HC_DEAD_LOOP_MSG_STRIPPED] Stripped dead command for {player_instance.name}: '{stripped_msg}'")

                    if stripped_msg == "respawn":
                        print(f"[HC_DEAD_LOOP_RESPAWN_CMD] '{stripped_msg}' command received. Attempting respawn for {player_instance.name}.")
                        if hasattr(player_instance, 'attempt_respawn'):
                            respawned = player_instance.attempt_respawn()
                            print(f"[HC_DEAD_LOOP_RESPAWN_RESULT] player_instance.attempt_respawn() returned: {respawned} for {player_instance.name}")
                            if respawned:
                                print(f"[HC_DEAD_LOOP_RESPAWN_SUCCESS] Player {player_instance.name} successfully respawned in player object.")
                                print(f"[HC_DEAD_LOOP_POST_RESPAWN_STATE] Player {player_instance.name} state: Dead={player_instance.is_dead}, HP={player_instance.current_hp}, Combat={player_instance.in_combat}, Target={player_instance.target}")
                                player_instance.room = world.get(player_instance.room_id)
                                if player_instance.room:
                                    print(f"[HC_DEAD_LOOP_RESPAWN_ROOM_DISPLAY] Sending room display for {player_instance.room.name} to {player_instance.name}")
                                    temp_user_for_player.send_message(player_instance.room.display())
                                else:
                                    temp_user_for_player.send_message("You respawn into a strange void. (Error: Respawn room not found)")
                                print(f"[HC_DEAD_LOOP_BREAKING] Breaking from dead loop for {player_instance.name}.")
                                break # Exit the 'while player_instance.is_dead'
                        else:
                             temp_user_for_player.send_message("Respawn system not fully implemented on player object.")
                    elif stripped_msg == "quit" or stripped_msg == "exit":
                        print(f"[HC_DEAD_LOOP_QUIT_CMD] '{stripped_msg}' command received. Closing connection for {player_instance.name}.")
                        temp_user_for_player.send_message("You embrace the void...")
                        connection_active = False; break
                    else:
                        print(f"[HC_DEAD_LOOP_UNKNOWN_CMD] Unknown dead command '{stripped_msg}' for {player_instance.name}.")
                        temp_user_for_player.send_message("Your spirit is too weak to do that. Type 'respawn' to return to life or 'quit' to depart.")
                print(f"[HC_DEAD_LOOP_EXIT] Exited dead loop for {player_instance.name}. Player state: Dead={player_instance.is_dead}, HP={player_instance.current_hp}")

            elif not player_instance:
                 print(f"[ERROR_HC] player_instance became None for {username}. Breaking client loop.")
                 connection_active = False

        player_name_for_log = player_instance.name if player_instance else (username or "unknown")
        print(f"[DEBUG_HANDLE_CLIENT] Exited main client loop for {player_name_for_log}.")

    except ConnectionResetError: print(f"[-] Connection reset by {addr}")
    except Exception as e:
        print(f"[ERROR] Outer Exception in handle_client for {addr}: {e}")
        traceback.print_exc()
    finally:
        print(f"[DEBUG_HANDLE_CLIENT] Finally block for {username or 'unknown user'}.")
        if player_instance:
            # Combat Logging: If player was alive and in combat when connection dropped / loop exited
            if player_instance.in_combat and player_instance.is_alive() and not player_instance.is_dead: # Check is_alive and not is_dead
                print(f"[COMBAT_LOG] Player {player_instance.name} disconnected/exited loop during combat. Marking as defeated.")
                player_instance.current_hp = 0
                player_instance.is_dead = True
                player_instance.in_combat = False # Ensure this is false before save

                mob_they_were_fighting = player_instance.target
                if mob_they_were_fighting and hasattr(mob_they_were_fighting, 'target') and mob_they_were_fighting.target == player_instance:
                    mob_they_were_fighting.target = None
                    if hasattr(mob_they_were_fighting, 'in_combat'): mob_they_were_fighting.in_combat = False
                    if mob_they_were_fighting in ACTIVE_COMBATANTS: remove_from_active_combat(mob_they_were_fighting)

                player_instance.target = None

            # Standard cleanup
            if player_instance in CONNECTED_PLAYERS: remove_connected_player(player_instance) # Use the function
            if player_instance in ACTIVE_COMBATANTS: remove_from_active_combat(player_instance)


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
                # Do NOT save player_instance.is_reloading or player_instance.is_dead directly from the flag.
                # is_dead is inferred from current_hp for saving.
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
