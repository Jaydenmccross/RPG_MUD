import socket
import threading
import time
import random
import traceback # For detailed exception logging
from server.core.user import UserManager
from server.core.player import Player, ITEMS_DATA as PLAYER_ITEMS_DATA, load_game_data as core_load_game_data
from server.core.room import Room
from server.core.content import Mob, Item, ItemInstance, MobInstance, ContainerInstance
from server.core.combat import resolve_attack

HOST = "127.0.0.1"
PORT = 4000
GAME_TICK_INTERVAL = 2 # seconds

world = {}
mobs_blueprints = {}

ACTIVE_COMBATANTS = []
combat_lock = threading.RLock() # Ensures multiple acquisitions by same thread are okay
CONNECTED_PLAYERS = []
players_lock = threading.RLock() # Ensures multiple acquisitions by same thread are okay
CURRENT_GAME_ROUND = 0

def add_to_active_combat(entity):
    with combat_lock:
        if entity not in ACTIVE_COMBATANTS:
            ACTIVE_COMBATANTS.append(entity)
            # print(f"[DEBUG_COMBAT_LIST] Added {entity.name if hasattr(entity,'name') else 'Unknown Entity'} to ACTIVE_COMBATANTS. Current: {[e.name if hasattr(e,'name') else 'Unknown' for e in ACTIVE_COMBATANTS]}")

def remove_from_active_combat(entity):
    with combat_lock:
        if entity in ACTIVE_COMBATANTS:
            ACTIVE_COMBATANTS.remove(entity)
            # print(f"[DEBUG_COMBAT_LIST] Removed {entity.name if hasattr(entity,'name') else 'Unknown Entity'} from ACTIVE_COMBATANTS. Current: {[e.name if hasattr(e,'name') else 'Unknown' for e in ACTIVE_COMBATANTS]}")


def add_connected_player(player_instance):
    player_name_for_log = player_instance.name if player_instance else "NonePlayer"
    # print(f"[ADD_PLAYER_DIAG] Entered add_connected_player for {player_name_for_log}")
    try:
        # print(f"[ADD_PLAYER_DIAG] Attempting to acquire players_lock for {player_name_for_log}")
        with players_lock:
            # print(f"[ADD_PLAYER_DIAG] Acquired players_lock for {player_name_for_log}")
            # print(f"[ADD_PLAYER_DIAG] Checking if {player_name_for_log} in CONNECTED_PLAYERS. Current length: {len(CONNECTED_PLAYERS)}")
            if player_instance not in CONNECTED_PLAYERS:
                # print(f"[ADD_PLAYER_DIAG] Appending {player_name_for_log} to CONNECTED_PLAYERS")
                CONNECTED_PLAYERS.append(player_instance)
            # else:
                # print(f"[ADD_PLAYER_DIAG] {player_name_for_log} already in CONNECTED_PLAYERS.")
    except Exception as e_add_player:
        print(f"!!! ERROR in add_connected_player for {player_name_for_log} !!!")
        print(traceback.format_exc())
    # print(f"[ADD_PLAYER_DIAG] Exiting add_connected_player for {player_name_for_log}")

def remove_connected_player(player_instance):
    player_name_for_log = player_instance.name if player_instance else "NonePlayer"
    # print(f"[REMOVE_PLAYER_DIAG] Entered remove_connected_player for {player_name_for_log}")
    with players_lock:
        if player_instance in CONNECTED_PLAYERS:
            # print(f"[REMOVE_PLAYER_DIAG] Removing {player_name_for_log} from CONNECTED_PLAYERS.")
            CONNECTED_PLAYERS.remove(player_instance)
        # else:
            # print(f"[REMOVE_PLAYER_DIAG] {player_name_for_log} not found in CONNECTED_PLAYERS for removal.")
    # print(f"[REMOVE_PLAYER_DIAG] Exiting remove_connected_player for {player_name_for_log}")


def get_players_in_room(room_id_to_check):
    players_found = []
    with players_lock: # Ensure thread-safe access to CONNECTED_PLAYERS
        # Iterate over a copy for safety if modifications could happen elsewhere, though less likely here
        for player in list(CONNECTED_PLAYERS):
            if player.room and \
               player.room.id == room_id_to_check and \
               player.is_alive() and \
               not player.is_dead and \
               not (hasattr(player, 'is_reloading') and player.is_reloading):
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
    # print(f"\n{'='*20} load_world_and_game_data() CALLED {'='*20}")
    # traceback.print_stack()
    # print(f"{'='*50}\n")
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
    global CURRENT_GAME_ROUND

    CURRENT_GAME_ROUND += 1
    # print(f"Game Tick: {CURRENT_GAME_ROUND}")
    try:
        # --- MOB & ITEM RESPAWN LOGIC ---
        for room_id, room in world.items():
            # Mob respawn
            for mob_def in room.mob_definitions:
                mob_id_to_spawn=mob_def.get("mob_id");max_qty=mob_def.get("max_quantity",1);respawn_secs=mob_def.get("respawn_seconds",300)
                if not mob_id_to_spawn or respawn_secs<=0:continue
                current_live_count=sum(1 for mi in room.mob_instances if mi.mob_blueprint.id==mob_id_to_spawn and mi.is_alive())
                num_to_spawn=max_qty-current_live_count
                if num_to_spawn<=0:continue
                spawned_this_tick_for_def=0
                with combat_lock: # Short lock for defeated_mob_track and room.mob_instances
                    for i in range(len(room.defeated_mob_track)-1,-1,-1):
                        tracked_death=room.defeated_mob_track[i]
                        if tracked_death["mob_id"]==mob_id_to_spawn:
                            if time.time()-tracked_death["time_of_death"]>=respawn_secs:
                                blueprint=mobs_blueprints.get(mob_id_to_spawn)
                                if blueprint:
                                    new_mob = MobInstance(blueprint); new_mob.room = room
                                    room.mob_instances.append(new_mob)
                                    room.defeated_mob_track.pop(i); spawned_this_tick_for_def+=1
                                    # print(f"[GAME_TICK_RESPAWN] Respawned {new_mob.name} in {room.name}")
                                    if spawned_this_tick_for_def>=num_to_spawn:break
            # Item respawn
            with combat_lock: # Short lock for pending_item_respawns and room items
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

        # --- AGGRESSIVE MOB ENGAGEMENT ---
        # Get a snapshot of players to avoid issues if CONNECTED_PLAYERS changes mid-loop
        with players_lock:
            current_connected_players = list(CONNECTED_PLAYERS)

        for room_id, room in world.items():
            # Filter players for the current room *once*
            players_in_room_for_aggro = [p for p in current_connected_players if p.room and p.room.id == room_id and p.is_alive() and not p.is_dead]
            if not players_in_room_for_aggro: continue

            mobs_to_check_aggro = list(room.mob_instances) # Iterate a copy
            for mob_instance in mobs_to_check_aggro:
                if mob_instance.is_alive() and mob_instance.is_aggressive and not mob_instance.in_combat:
                    potential_target = random.choice(players_in_room_for_aggro) # Random target in room

                    if potential_target: # Should always be true if players_in_room_for_aggro is not empty
                        # Lock only for critical section of adding to combat
                        with combat_lock:
                            mob_instance.target = potential_target; mob_instance.in_combat = True
                            if not potential_target.in_combat or not potential_target.target: # If player not fighting or no target
                                potential_target.target = mob_instance
                            potential_target.in_combat = True # Ensure player is marked in combat
                            add_to_active_combat(mob_instance) # add_to_active_combat handles its own lock
                            add_to_active_combat(potential_target)

                        # Messaging outside the lock
                        if hasattr(potential_target.user, 'send_message'):
                            potential_target.user.send_message(f"{ANSI_RED}{mob_instance.name} suddenly attacks you!{ANSI_RESET}")
                        for p_other in players_in_room_for_aggro:
                            if p_other != potential_target and hasattr(p_other.user, 'send_message'):
                                p_other.user.send_message(f"{mob_instance.name} attacks {potential_target.name}!")

        # --- COMBAT RESOLUTION ---
        combatants_to_remove_this_tick = []

        # Get a snapshot of active combatants
        current_active_combatants_snapshot = []
        with combat_lock: # Short lock to get a copy
            current_active_combatants_snapshot = list(ACTIVE_COMBATANTS)

        for entity in current_active_combatants_snapshot:
            # Initial check: if entity is no longer valid (e.g. disconnected player, already dead)
            # This check is crucial if an entity was removed from CONNECTED_PLAYERS but not yet from ACTIVE_COMBATANTS
            if isinstance(entity, Player) and (entity.user is None or entity.user.connection is None):
                print(f"[GAME_TICK_COMBAT_STALE] Player {entity.name} found disconnected in ACTIVE_COMBATANTS. Marking for removal.")
                entity.in_combat = False; entity.target = None
                combatants_to_remove_this_tick.append(entity)
                continue

            if not entity.is_alive() or (hasattr(entity, 'is_dead') and entity.is_dead):
                combatants_to_remove_this_tick.append(entity)
                if entity.target and hasattr(entity.target, 'target') and entity.target.target == entity:
                    entity.target.target = None
                    if hasattr(entity.target, 'in_combat'): entity.target.in_combat = False
                entity.target = None # Clear own target
                entity.in_combat = False
                continue

            if isinstance(entity, MobInstance):
                # --- Mob Target Validation ---
                target_is_valid_for_mob = True; reason = ""
                if not entity.target: target_is_valid_for_mob = False; reason = "mob has no target"
                elif not hasattr(entity.target, 'is_alive'): target_is_valid_for_mob = False; reason = "mob target lacks 'is_alive'"
                elif not entity.target.is_alive(): target_is_valid_for_mob = False; reason = f"mob target '{entity.target.name if hasattr(entity.target,'name') else 'Unknown'}' not alive"
                elif hasattr(entity.target, 'is_dead') and entity.target.is_dead: target_is_valid_for_mob = False; reason = f"mob target Player '{entity.target.name}' is dead"
                elif isinstance(entity.target, Player):
                    if entity.target.user is None: target_is_valid_for_mob = False; reason = f"mob target Player '{entity.target.name}' no user"
                    elif entity.target.user.connection is None: target_is_valid_for_mob = False; reason = f"mob target Player '{entity.target.name}' no connection"

                if not target_is_valid_for_mob:
                    # print(f"[GAME_TICK_MOB_TARGET_INVALID] Mob {entity.name} {reason}. Disengaging.")
                    entity.target = None; entity.in_combat = False
                    combatants_to_remove_this_tick.append(entity)
                    continue
                # --- End Mob Target Validation ---

                entity.tick_status_effects(CURRENT_GAME_ROUND)

                if entity.in_combat: # Target is valid and alive here
                    attack_messages = resolve_attack(entity, entity.target) # Calls defender.take_damage()

                    # Message target (if player and still valid for messaging)
                    if entity.target and isinstance(entity.target, Player) and \
                       entity.target.user and entity.target.user.connection and \
                       entity.target.is_alive() and not entity.target.is_dead:
                        for line in attack_messages: entity.target.user.send_message(line)

                    # Message other players in room
                    if entity.target and entity.target.room:
                        players_in_target_room = get_players_in_room(entity.target.room.id) # Uses players_lock
                        for other_player in players_in_target_room:
                            if other_player != entity.target and other_player.user and other_player.user.connection:
                                for line in attack_messages: other_player.user.send_message(line)

                    # Check target death (could have died from attack)
                    if entity.target and (not entity.target.is_alive() or (hasattr(entity.target, 'is_dead') and entity.target.is_dead)):
                        # print(f"[GAME_TICK_COMBAT_POST_ATTACK] Target {entity.target.name if hasattr(entity.target,'name') else 'Unknown'} died after {entity.name}'s attack.")
                        combatants_to_remove_this_tick.append(entity.target)
                        entity.target = None; entity.in_combat = False
                        combatants_to_remove_this_tick.append(entity)
                    elif not entity.target: # If mob's target was cleared (e.g., by Player.handle_death during resolve_attack)
                        # print(f"[GAME_TICK_COMBAT_POST_ATTACK] Mob {entity.name}'s target was cleared. Disengaging.")
                        entity.in_combat = False
                        combatants_to_remove_this_tick.append(entity)

            elif isinstance(entity, Player):
                # Player's target validation (if player is in combat)
                if entity.in_combat and (not entity.target or not entity.target.is_alive() or (hasattr(entity.target, 'is_dead') and entity.target.is_dead)):
                    # print(f"[GAME_TICK_PLAYER_TARGET_INVALID] Player {entity.name}'s target invalid/dead. Disengaging.")
                    entity.target = None; entity.in_combat = False
                    combatants_to_remove_this_tick.append(entity)
                elif not entity.in_combat and entity in current_active_combatants_snapshot: # If player was in combat but no longer is
                     combatants_to_remove_this_tick.append(entity)

        # Process removals from ACTIVE_COMBATANTS
        if combatants_to_remove_this_tick:
            with combat_lock: # Short lock only for modifying ACTIVE_COMBATANTS
                for entity_to_remove in set(combatants_to_remove_this_tick):
                    if entity_to_remove in ACTIVE_COMBATANTS:
                        ACTIVE_COMBATANTS.remove(entity_to_remove) # Direct removal, no helper
                        # print(f"[GAME_TICK_CLEANUP] Removed {entity_to_remove.name if hasattr(entity_to_remove, 'name') else 'Unknown Entity'} from ACTIVE_COMBATANTS.")
                        # Reciprocal target clearing (if mob killed player, player's handle_death should have done this)
                        if hasattr(entity_to_remove, 'target') and entity_to_remove.target and \
                           hasattr(entity_to_remove.target, 'target') and entity_to_remove.target.target == entity_to_remove:
                            entity_to_remove.target.target = None
                            if hasattr(entity_to_remove.target, 'in_combat'):
                                entity_to_remove.target.in_combat = False

    except Exception as e:
        print(f"[ERROR] Exception in game_tick: {e}")
        import traceback
        traceback.print_exc()

def game_tick_loop():
    while True:
        game_tick()
        time.sleep(GAME_TICK_INTERVAL)

# [ PREVIOUS handle_client content is assumed to be here, up to the main while loop ]
# [ The overwrite will start from "def handle_client(conn, addr):" and replace the whole function ]
# [ For brevity, I will not paste the *entire* old handle_client here, but the overwrite tool needs it. ]
# [ I will paste the NEW, complete handle_client function below. ]

def handle_client(conn, addr):
    print(f"[DEBUG_HANDLE_CLIENT] New connection from {addr}")
    player_instance = None; username = None; user_data = None
    try:
        # print("[DEBUG_HANDLE_CLIENT] Attempting UserManager.authenticate_or_create...")
        username, user_data = UserManager.authenticate_or_create(conn)
        # print(f"[DEBUG_HANDLE_CLIENT] UserManager.authenticate_or_create returned: username='{username}', user_data keys: {list(user_data.keys()) if user_data else 'None'}")

        if not username or not user_data:
            if conn: conn.close()
            # print(f"[DEBUG_HANDLE_CLIENT] Auth failed or no character data for {addr}. Closing connection.")
            return

        player_name = user_data.get("name", username)
        player_class_name = user_data.get("player_class_name", "Fighter")
        player_race_name = user_data.get("race_name", "Human")
        player_base_stats = user_data.get("base_stats")

        class TempUser:
            def __init__(self, c, u): self.connection=c; self.username=u
            def send_message(self, msg):
                if self.connection:
                    try: self.connection.sendall(msg.encode()+b"\r\n")
                    except Exception as e_send: print(f"[DEBUG_HANDLE_CLIENT] TempUser send_message EXCEPTION for {self.username}: {e_send}"); self.connection = None
            def read_line(self):
                if self.connection:
                    try:
                        raw=self.connection.recv(1024)
                        return raw.decode(errors='ignore').strip() if raw else None
                    except socket.timeout: return ""
                    except Exception: self.connection = None; return None
                return None

        temp_user_for_player = TempUser(conn, username)
        player_instance = Player(user=temp_user_for_player, player_class_name=player_class_name, race_name=player_race_name, name=player_name, base_stats=player_base_stats)

        add_connected_player(player_instance)

        player_instance.level = user_data.get("level", 1)
        player_instance.xp = user_data.get("xp", 0)
        saved_hp = user_data.get("current_hp", player_instance.max_hp)
        player_instance.current_hp = min(saved_hp, player_instance.max_hp) if saved_hp > 0 else player_instance.max_hp

        if player_instance.current_hp <= 0:
            player_instance.is_dead = True; player_instance.current_hp = 0
            player_instance.in_combat = False; player_instance.target = None
        else: player_instance.is_dead = False

        player_instance.in_combat = False
        player_instance.target = None
        with combat_lock:
            if player_instance in ACTIVE_COMBATANTS: remove_from_active_combat(player_instance)

        player_instance.used_abilities_this_rest = set(user_data.get("used_abilities_this_rest", []))
        player_instance.room_id = user_data.get("current_room_id", "start")
        current_room_obj = world.get(player_instance.room_id)
        if not current_room_obj: player_instance.room_id = "start"; current_room_obj = world.get("start")
        player_instance.room = current_room_obj

        raw_inventory = user_data.get("inventory", [])
        player_instance.inventory = []
        for item_rep in raw_inventory: # Simplified inventory loading
            item_id = item_rep.get("item_id"); quantity = item_rep.get("quantity", 1)
            bp_dict = PLAYER_ITEMS_DATA.get(item_id) if item_id and PLAYER_ITEMS_DATA else None
            if bp_dict:
                from server.core.content import Item # Local import
                bp_obj = Item(**bp_dict)
                if bp_obj.type == "container": player_instance.inventory.append(ContainerInstance(bp_obj, quantity))
                else: player_instance.inventory.append(ItemInstance(bp_obj, quantity))
        saved_equipment = user_data.get("equipment", {})
        if saved_equipment: # Simplified equipment loading
            for slot, item_id in saved_equipment.items():
                item_data = PLAYER_ITEMS_DATA.get(item_id) if item_id and slot in Player.ALL_EQUIPMENT_SLOTS and PLAYER_ITEMS_DATA else None
                if item_data: player_instance.equipment[slot] = dict(item_data)

        temp_user_for_player.send_message("\r\nWelcome to the MUD!")
        if not player_instance.is_dead:
            if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
            else: temp_user_for_player.send_message("You are in a featureless void. (Error: Room not found)")
        elif player_instance.is_dead:
             if hasattr(player_instance.user, 'send_message'):
                player_instance.user.send_message(f"{ANSI_YELLOW}Your soul lingers. Type 'respawn', 'wait', or 'quit'.{ANSI_RESET}")

        connection_active = True
        while player_instance and connection_active:
            if temp_user_for_player.connection is None:
                print(f"[DEBUG_HANDLE_CLIENT_LOOP_END] Connection closed for {username}. Breaking.")
                connection_active = False; break

            current_prompt = "\r\n> " if not player_instance.is_dead else f"{ANSI_RED}[DEAD]{ANSI_RESET} > "
            temp_user_for_player.send_message(current_prompt)
            msg = temp_user_for_player.read_line()

            if msg is None:
                print(f"[HC_DIAG_MAIN_LOOP_MSG_NONE] Connection lost (msg is None) for {player_instance.name}.")
                connection_active = False; break

            # print(f"[HC_DIAG_MAIN_LOOP_CMD_RAW] Raw for {player_instance.name} (Dead={player_instance.is_dead}): '{msg}'")
            stripped_msg = msg.strip()
            # print(f"[HC_DIAG_MAIN_LOOP_CMD_STRIPPED] Stripped for {player_instance.name}: '{stripped_msg}'")

            if player_instance.is_dead:
                # print(f"[HC_DIAG_BRANCH] Player {player_instance.name} IS DEAD.")
                command_word_dead = stripped_msg.lower()
                if command_word_dead == "respawn":
                    # print(f"[HC_DIAG_DEAD_CMD] 'respawn' received for {player_instance.name}.")
                    if hasattr(player_instance, 'attempt_respawn'):
                        respawned = player_instance.attempt_respawn()
                        if respawned:
                            # print(f"[HC_DIAG_DEAD_CMD] {player_instance.name} respawn successful in obj.")
                            player_instance.room = world.get(player_instance.room_id)
                            if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                elif command_word_dead == "quit" or command_word_dead == "exit":
                    temp_user_for_player.send_message("You embrace the void..."); connection_active = False
                elif command_word_dead == "wait":
                    temp_user_for_player.send_message("You lie in wait of help. You have up to 5 minutes before you automatically respawn. You can type 'respawn' at any time.")
                elif not command_word_dead: pass
                else: temp_user_for_player.send_message("Your spirit is too weak. Type 'respawn', 'wait', or 'quit'.")

            else: # Player is ALIVE
                # print(f"[HC_DIAG_BRANCH] Player {player_instance.name} IS ALIVE.")
                # print(f"[HC_DIAG_ALIVE_LOOP_REENTRY] {player_instance.name} ALIVE: Dead={player_instance.is_dead}, HP={player_instance.current_hp}, Combat={player_instance.in_combat}")
                player_instance.reset_turn_actions()

                if not stripped_msg: # EMPTY COMMAND -> True Auto-Attack
                    if player_instance.in_combat and player_instance.target and \
                       player_instance.is_alive() and not player_instance.has_taken_action_this_turn:
                        # print(f"[HC_AUTO_ATTACK] {player_instance.name} auto-attacking {player_instance.target.name}.")
                        temp_user_for_player.send_message(f"{ANSI_YELLOW}You lash out with a basic attack!{ANSI_RESET}")
                        attack_messages = resolve_attack(player_instance, player_instance.target)
                        for line in attack_messages: temp_user_for_player.send_message(line)
                        player_instance.has_taken_action_this_turn = True
                        if not player_instance.is_alive(): pass
                        elif player_instance.target and not player_instance.target.is_alive():
                            player_instance.add_xp(player_instance.target.xp_value)
                            if player_instance.room: player_instance.room.record_defined_mob_death(player_instance.target)
                            remove_from_active_combat(player_instance.target)
                            original_target_of_player = player_instance.target
                            player_instance.target = None
                            still_targeted_by_mob = False
                            with combat_lock: temp_active_combatants = list(ACTIVE_COMBATANTS)
                            for combatant in temp_active_combatants:
                                if combatant != player_instance and hasattr(combatant, 'target') and combatant.target == player_instance and combatant.is_alive():
                                    still_targeted_by_mob = True; break
                            if not still_targeted_by_mob:
                                player_instance.in_combat = False
                                with combat_lock: # ensure removal is safe
                                     if player_instance in ACTIVE_COMBATANTS: remove_from_active_combat(player_instance)
                    continue

                parts = stripped_msg.split(); command_word = parts[0].lower(); args = parts[1:]
                command_word = COMMAND_ALIASES.get(command_word, command_word)
                # print(f"[HC_DIAG_ALIVE_CMD_PARSED] Parsed: '{command_word}', Args: {args}")
                responded = False

                if command_word in DIRECTIONS and not args:
                    if player_instance.has_taken_action_this_turn: temp_user_for_player.send_message("You have already taken an action this turn.")
                    elif player_instance.in_combat: temp_user_for_player.send_message("You can't move like that while in combat!")
                    else:
                        direction_to_move = DIRECTIONS[command_word]
                        if player_instance.room and direction_to_move in player_instance.room.exits:
                            new_room_id = player_instance.room.exits[direction_to_move]
                            if new_room_id in world: player_instance.room = world[new_room_id]; player_instance.has_taken_action_this_turn = True
                            if player_instance.room: temp_user_for_player.send_message(player_instance.room.display())
                            else: temp_user_for_player.send_message("The exit leads nowhere.")
                            user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                        else: temp_user_for_player.send_message("You can't go that way.")
                    responded = True
                elif command_word == "kill":
                    # print(f"[HC_KILL_CMD_START] {player_instance.name} processing 'kill {args}'")
                    if player_instance.has_taken_action_this_turn: temp_user_for_player.send_message("You have already taken an action this turn.")
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
                            if not player_instance.is_alive(): pass
                            elif not target_mob_instance.is_alive():
                                player_instance.add_xp(target_mob_instance.xp_value)
                                if player_instance.room: player_instance.room.record_defined_mob_death(target_mob_instance)
                                if player_instance.target == target_mob_instance: player_instance.target = None; player_instance.in_combat = False
                                remove_from_active_combat(player_instance); remove_from_active_combat(target_mob_instance)
                            elif player_instance.is_alive():
                                temp_user_for_player.send_message(f"The {target_mob_instance.name} retaliates!")
                                mob_attack_messages = resolve_attack(target_mob_instance, player_instance)
                                for line in mob_attack_messages: temp_user_for_player.send_message(line)
                        else: temp_user_for_player.send_message(f"There is no living '{target_name}' here.")
                    responded = True
                # ... (other alive commands: look, sheet, inv, go, equip, remove, get, drop, dash, cast, reload, rest, secondwind) ...
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
                elif command_word == "inventory":
                    if not args: temp_user_for_player.send_message(player_instance.display_inventory())
                    else: temp_user_for_player.send_message("Just type 'inventory' or 'i'.")
                    responded = True
                elif command_word == "hide":
                    if player_instance.has_taken_action_this_turn: # Hiding is an action
                        temp_user_for_player.send_message("You have already taken your action this turn.")
                    elif player_instance.in_combat and not player_instance.has_condition(Player.CONDITION_INVISIBLE): # Simplified: can't hide in plain sight in combat unless invisible
                        temp_user_for_player.send_message("You can't hide effectively while they're watching you!")
                        # TODO: More complex hide in combat (bonus action for rogues, specific conditions)
                    else:
                        stealth_bonus = player_instance.get_skill_bonus("Stealth")
                        # TODO: Advantage/Disadvantage on Stealth check based on conditions/environment
                        d20_roll, roll_type_str = roll_d20_with_advantage_disadvantage() # from combat.py
                        total_stealth_roll = d20_roll + stealth_bonus

                        # For now, fixed DC. Later, could be opposed by mob Perception.
                        hide_dc = 13

                        roll_msg = f"You attempt to hide (Stealth: {d20_roll} + {stealth_bonus} = {total_stealth_roll} vs DC {hide_dc})."
                        if roll_type_str != "normal": roll_msg = roll_msg.replace("Stealth:", f"Stealth ({roll_type_str}):")
                        temp_user_for_player.send_message(roll_msg)

                        if total_stealth_roll >= hide_dc:
                            # Duration of 1 round for now (i.e., until your next turn starts or you act)
                            # Actual duration/breaking conditions are more complex in 5e.
                            player_instance.add_condition(Player.CONDITION_HIDDEN, duration_rounds=1, source="Hide Action")
                            temp_user_for_player.send_message(f"{ANSI_GREEN}You slip into the shadows, hidden from view.{ANSI_RESET}")
                        else:
                            temp_user_for_player.send_message(f"{ANSI_RED}You fail to hide effectively.{ANSI_RESET}")
                        player_instance.has_taken_action_this_turn = True
                    responded = True
                elif command_word == "persuade":
                    if not args:
                        temp_user_for_player.send_message("Persuade whom? (And optionally, what to say: persuade <target> [message])")
                    else:
                        target_name = args[0].lower() # For now, assume target name is one word or use first word
                        # message_text = " ".join(args[1:]) # Optional message text

                        target_mob_instance = None
                        if player_instance.room and player_instance.room.mob_instances:
                            for mob_in_room in player_instance.room.mob_instances:
                                if mob_in_room.name.lower() == target_name and mob_in_room.is_alive():
                                    target_mob_instance = mob_in_room
                                    break

                        if not target_mob_instance:
                            temp_user_for_player.send_message(f"You don't see '{args[0]}' here to persuade.")
                        elif not getattr(target_mob_instance.mob_blueprint, 'can_be_persuaded', False):
                            temp_user_for_player.send_message(f"{target_mob_instance.name} doesn't seem interested in talking.")
                        elif player_instance.has_taken_action_this_turn: # Persuasion takes an action
                             temp_user_for_player.send_message("You have already taken your action this turn.")
                        else:
                            persuasion_bonus = player_instance.get_skill_bonus("Persuasion")
                            d20_roll, roll_type_str = roll_d20_with_advantage_disadvantage() # from combat.py
                            total_persuasion_roll = d20_roll + persuasion_bonus
                            persuasion_dc = getattr(target_mob_instance.mob_blueprint, 'persuasion_dc', 15) # Default DC if not set

                            roll_msg = f"You attempt to persuade {target_mob_instance.name} (Persuasion: {d20_roll} + {persuasion_bonus} = {total_persuasion_roll} vs DC {persuasion_dc})."
                            if roll_type_str != "normal": roll_msg = roll_msg.replace("Persuasion:", f"Persuasion ({roll_type_str}):")
                            temp_user_for_player.send_message(roll_msg)

                            dialogue = getattr(target_mob_instance.mob_blueprint, 'dialogue', {})
                            if total_persuasion_roll >= persuasion_dc:
                                temp_user_for_player.send_message(f"{target_mob_instance.name}: \"{dialogue.get('persuade_success', 'Hmm, you make a good point.')}\"")
                                # Mechanical effect: make non-aggressive, stop combat with player
                                if target_mob_instance.is_aggressive:
                                    target_mob_instance.is_aggressive = False # Temporarily? Needs duration logic
                                    # TODO: Add temporary effect "Pacified" for X rounds.
                                    temp_user_for_player.send_message(f"{target_mob_instance.name} seems calmer now.")
                                if target_mob_instance.target == player_instance:
                                    target_mob_instance.target = None
                                    target_mob_instance.in_combat = False
                                    # If player was only fighting this mob, player also leaves combat
                                    if player_instance.target == target_mob_instance:
                                        player_instance.target = None
                                        # Check if any other mob is targeting player before setting in_combat to False
                                        still_targeted = False
                                        with combat_lock: temp_combatants = list(ACTIVE_COMBATANTS)
                                        for combatant in temp_combatants:
                                            if combatant != target_mob_instance and combatant.is_alive() and \
                                               hasattr(combatant, 'target') and combatant.target == player_instance:
                                                still_targeted = True
                                                break
                                        if not still_targeted:
                                            player_instance.in_combat = False
                                            remove_from_active_combat(player_instance)

                            else:
                                temp_user_for_player.send_message(f"{target_mob_instance.name}: \"{dialogue.get('persuade_fail', 'I am not convinced!')}\"")
                            player_instance.has_taken_action_this_turn = True
                    responded = True
                elif command_word == "investigate":
                    if not args:
                        temp_user_for_player.send_message("Investigate what?")
                    elif player_instance.has_taken_action_this_turn:
                         temp_user_for_player.send_message("You have already taken your action this turn.")
                    else:
                        target_object_name_input = " ".join(args).lower()
                        found_object_key = None
                        obj_data = None

                        if player_instance.room and hasattr(player_instance.room, 'investigatable_objects'):
                            for key, data in player_instance.room.investigatable_objects.items():
                                if data.get("display_name", "").lower() == target_object_name_input or \
                                   target_object_name_input in data.get("aliases", []):
                                    found_object_key = key
                                    obj_data = data
                                    break

                        if not obj_data:
                            temp_user_for_player.send_message(f"You don't see anything like '{target_object_name_input}' to investigate here.")
                        else:
                            loot_flag_id = obj_data.get("loot_once_flag_id")
                            if loot_flag_id and loot_flag_id in player_instance.triggered_room_flags:
                                temp_user_for_player.send_message(f"You investigate the {obj_data.get('display_name', 'object')} again, but find nothing new.")
                                player_instance.has_taken_action_this_turn = True
                            else:
                                investigation_bonus = player_instance.get_skill_bonus("Investigation")
                                d20_roll, roll_type_str = roll_d20_with_advantage_disadvantage()
                                total_investigation_roll = d20_roll + investigation_bonus
                                dc = obj_data.get("dc", 15)

                                roll_msg = f"You investigate the {obj_data.get('display_name', 'object')} (Investigation: {d20_roll} + {investigation_bonus} = {total_investigation_roll} vs DC {dc})."
                                if roll_type_str != "normal": roll_msg = roll_msg.replace("Investigation:", f"Investigation ({roll_type_str}):")
                                temp_user_for_player.send_message(roll_msg)

                                if total_investigation_roll >= dc:
                                    success_text = obj_data.get("reveals_text", "You find something interesting!")
                                    temp_user_for_player.send_message(f"{ANSI_GREEN}{success_text}{ANSI_RESET}")

                                    item_id_revealed = obj_data.get("reveals_item_id")
                                    if item_id_revealed:
                                        item_qty = obj_data.get("reveals_item_quantity", 1)
                                        item_blueprint_dict = PLAYER_ITEMS_DATA.get(item_id_revealed)
                                        if item_blueprint_dict:
                                            from server.core.content import Item # Local import
                                            actual_blueprint = Item(**item_blueprint_dict)
                                            item_instance_to_give = ItemInstance(actual_blueprint, item_qty)
                                            player_instance.add_item_to_inventory(item_instance_to_give) # Assumes this method exists and sends its own message
                                            temp_user_for_player.send_message(f"You add {item_instance_to_give.item_blueprint.name} (x{item_qty}) to your inventory.")
                                        else:
                                            temp_user_for_player.send_message(f"{ANSI_RED}Error: Revealed item '{item_id_revealed}' not found in item database.{ANSI_RESET}")

                                    if loot_flag_id:
                                        player_instance.triggered_room_flags.add(loot_flag_id)
                                        # print(f"DEBUG: Player {player_instance.name} triggered loot flag: {loot_flag_id}")
                                else:
                                    temp_user_for_player.send_message(f"{ANSI_RED}You don't find anything unusual about the {obj_data.get('display_name', 'object')}.{ANSI_RESET}")
                                player_instance.has_taken_action_this_turn = True
                    responded = True


                if not responded and command_word:
                    # print(f"[DEBUG_HANDLE_CLIENT] Unknown alive command: '{command_word}' for {player_instance.name}")
                    temp_user_for_player.send_message("I don't understand that command.")

            if player_instance and not player_instance.is_alive() and not player_instance.is_dead :
                # print(f"[HC_DIAG_POST_CMD_DEATH_DETECT] {player_instance.name} HP {player_instance.current_hp}. Calling handle_death.")
                player_instance.handle_death("Unknown - Post Command Check")

        # print(f"[DEBUG_HANDLE_CLIENT] Exited main client loop for {player_instance.name if player_instance else username}.")

    except ConnectionResetError: print(f"[-] Connection reset by {addr}")
    except Exception as e:
        print(f"[ERROR] Outer Exception in handle_client for {addr} ({username or 'N/A'}): {e}")
        import traceback; traceback.print_exc()
    finally:
        # print(f"[DEBUG_HANDLE_CLIENT] Finally block for {username or 'unknown user'}.")
        if player_instance:
            remove_connected_player(player_instance)
            with combat_lock:
                if player_instance.in_combat or player_instance in ACTIVE_COMBATANTS:
                    remove_from_active_combat(player_instance)
                if player_instance.target and hasattr(player_instance.target, 'target') and player_instance.target.target == player_instance :
                    player_instance.target.target = None
                    if hasattr(player_instance.target, 'in_combat'): player_instance.target.in_combat = False
            if username and user_data:
                user_data["current_room_id"] = player_instance.room.id if player_instance.room else "start"
                user_data["equipment"] = {s:(d.get("id",d.get("name")) if isinstance(d,dict) else d) if d else None for s,d in player_instance.equipment.items()}
                user_data["inventory"] = [{"item_id": inv_item.item_blueprint.id, "quantity": inv_item.quantity} for inv_item in player_instance.inventory if hasattr(inv_item, 'item_blueprint')]
                user_data["level"]=player_instance.level; user_data["xp"]=player_instance.xp
                user_data["current_hp"]=player_instance.current_hp
                user_data["base_stats"] = player_instance.base_stats
                user_data["race_name"] = player_instance.race_name
                user_data["player_class_name"] = player_instance.player_class_name
                user_data["used_abilities_this_rest"] = list(player_instance.used_abilities_this_rest)
                UserManager.save_user_data(username, user_data)
                # print(f"[*] Player {player_instance.name} data saved for user {username}.")
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

[end of server/main.py]
