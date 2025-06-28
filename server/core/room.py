import json
import os
import time # For defeated_mob_track
from server.core.content import MobInstance, ItemInstance, ContainerInstance, Item # Item needed for spawn

# mobs_blueprints and PLAYER_ITEMS_DATA are not directly accessible here.
# They will be passed to spawn_initial_content.

class Room:
    def __init__(self, room_id, name, description, exits,
                 mob_definitions=None, item_definitions=None):
        self.id = room_id
        self.name = name
        self.description = description
        self.exits = exits if exits is not None else {}

        # Definitions for what *should* spawn in this room
        self.mob_definitions = mob_definitions if mob_definitions is not None else []
        self.item_definitions = item_definitions if item_definitions is not None else []

        # Live instances currently in the room
        self.mob_instances = []  # List of MobInstance objects
        self.items_on_ground = [] # List of ItemInstance objects

        # For respawn tracking
        self.defeated_mob_track = [] # Stores {"mob_id": "id", "time_of_death": timestamp}
        self.pending_item_respawns = [] # Stores {"item_id": "id", "time_taken": timestamp, "original_definition": dict}

        # For Admin tool, to link mobs back to their room when editing instances
        for mob_inst in self.mob_instances:
            mob_inst.room = self


    def display(self):
        """Returns a string representation of the room for the player."""
        display_text = [f"{self.name}", f"  {self.description}"]

        visible_exits = [direction for direction, room_id in self.exits.items() if room_id]
        if visible_exits:
            display_text.append(f"Exits: [{', '.join(sorted(visible_exits))}]")
        else:
            display_text.append("Exits: [None]")

        if self.items_on_ground:
            display_text.append("You see on the ground:")
            for item_instance in self.items_on_ground:
                display_text.append(f"  - {item_instance.item_blueprint.name} (x{item_instance.quantity})")

        live_mob_instances = [mob for mob in self.mob_instances if mob.is_alive()]
        if live_mob_instances:
            display_text.append("Creatures present:")
            for mob_instance in live_mob_instances:
                display_text.append(f"  - {mob_instance.name}")

        return "\n".join(display_text)

    def spawn_initial_content(self, mobs_master_list, items_master_list):
        """
        Spawns initial mobs and items based on definitions.
        mobs_master_list: The global dictionary of Mob blueprints.
        items_master_list: The global dictionary of Item blueprints (PLAYER_ITEMS_DATA).
        """
        self.mob_instances = [] # Clear any existing live mobs before spawning
        for mob_def in self.mob_definitions:
            mob_id = mob_def.get("mob_id")
            quantity = mob_def.get("quantity", mob_def.get("max_quantity", 1)) # Use quantity or max_quantity

            mob_blueprint = mobs_master_list.get(mob_id)
            if mob_blueprint:
                for _ in range(quantity):
                    new_mob = MobInstance(mob_blueprint)
                    new_mob.room = self # Link mob instance to this room
                    self.mob_instances.append(new_mob)
            else:
                print(f"Warning: Mob blueprint ID '{mob_id}' not found for room '{self.id}'.")

        self.items_on_ground = [] # Clear any existing ground items
        for item_def in self.item_definitions:
            item_id = item_def.get("item_id")
            quantity = item_def.get("quantity", 1)

            item_blueprint_dict = items_master_list.get(item_id)
            if item_blueprint_dict:
                actual_blueprint = Item(**item_blueprint_dict) # Create Item object from dict
                if actual_blueprint.type == "container":
                    new_item = ContainerInstance(actual_blueprint, quantity)
                    # TODO: Handle spawning items *inside* this container if definition supports it
                else:
                    new_item = ItemInstance(actual_blueprint, quantity)
                self.items_on_ground.append(new_item)
            else:
                print(f"Warning: Item blueprint ID '{item_id}' not found for room '{self.id}'.")

    def add_item_to_ground(self, item_instance):
        # TODO: Consider stacking if item_instance of same type already on ground
        self.items_on_ground.append(item_instance)

    def remove_item_from_ground(self, item_name_or_id_to_remove, quantity=1):
        item_to_remove_idx = -1
        item_instance_found = None

        for i, inst in enumerate(self.items_on_ground):
            if inst.item_blueprint.name.lower() == item_name_or_id_to_remove.lower() or \
               inst.item_blueprint.id.lower() == item_name_or_id_to_remove.lower():

                if inst.quantity >= quantity:
                    # Create a new instance for the taken item(s)
                    item_instance_found = ItemInstance(inst.item_blueprint, quantity)
                    inst.quantity -= quantity
                    if inst.quantity <= 0:
                        item_to_remove_idx = i
                    break
                else: # Not enough quantity in this specific stack
                    return None # Or could signal partial take, more complex

        if item_to_remove_idx != -1:
            self.items_on_ground.pop(item_to_remove_idx)

        if item_instance_found:
             # Record that item was taken for respawn purposes, if it was from a definition
            original_def_found = None
            for item_def in self.item_definitions:
                if item_def.get("item_id") == item_instance_found.item_blueprint.id:
                    original_def_found = item_def
                    break
            if original_def_found and original_def_found.get("respawn_seconds", 0) > 0:
                self.pending_item_respawns.append({
                    "item_id": item_instance_found.item_blueprint.id,
                    "time_taken": time.time(),
                    "original_definition": original_def_found # Store the whole original definition
                })
            return item_instance_found
        return None


    def record_defined_mob_death(self, mob_instance):
        """Records the death of a mob that was spawned from a definition for respawn tracking."""
        mob_id = mob_instance.mob_blueprint.id
        # Check if this mob_id is part of this room's definitions and should respawn
        for mob_def in self.mob_definitions:
            if mob_def.get("mob_id") == mob_id and mob_def.get("respawn_seconds", 0) > 0:
                self.defeated_mob_track.append({
                    "mob_id": mob_id,
                    "time_of_death": mob_instance.time_of_death # time_of_death set in MobInstance.handle_death
                })
                # print(f"DEBUG: Recorded death of {mob_id} in room {self.id} for respawn. Track: {self.defeated_mob_track}")
                break


    def to_dict_for_save(self): # For saving world file definition
        return {
            "name": self.name,
            "description": self.description,
            "exits": self.exits,
            "mob_definitions": self.mob_definitions, # Save the definitions
            "item_definitions": self.item_definitions # Save the definitions
        }

    @staticmethod
    def load_rooms(file_path="server/data/world.json"): # Default path added
        if not os.path.exists(file_path):
            print(f"Warning: World data file not found at {file_path}. Creating default room.")
            default_room = Room("start", "The Void", "An empty, featureless void.", {}, [], [])
            return {"start": default_room}
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_path}. Creating default room.")
            default_room = Room("start", "The Void", "An empty, featureless void.", {}, [], [])
            return {"start": default_room}
        except Exception as e:
            print(f"Error loading {file_path}: {e}. Creating default room.")
            default_room = Room("start", "The Void", "An empty, featureless void.", {}, [], [])
            return {"start": default_room}

        rooms = {}
        for room_id, room_data in data.items():
            if not isinstance(room_data, dict):
                print(f"Warning: Skipping malformed room data for ID '{room_id}' in {file_path}.")
                continue

            rooms[room_id] = Room(
                room_id=room_id,
                name=room_data.get("name", room_id),
                description=room_data.get("description", "A non-descript location."),
                exits=room_data.get("exits", {}),
                mob_definitions=room_data.get("mob_definitions", []), # Load definitions
                item_definitions=room_data.get("item_definitions", [])  # Load definitions
            )
        if not rooms: # If file was empty or all entries malformed
            print(f"Warning: No valid rooms loaded from {file_path}. Creating default room.")
            default_room = Room("start", "The Void", "An empty, featureless void.", {}, [], [])
            return {"start": default_room}

        return rooms

    @staticmethod
    def save_rooms(rooms_dict, file_path="server/data/world.json"): # Default path added
        data_to_save = {room_id: room.to_dict_for_save() for room_id, room in rooms_dict.items()}
        try:
            with open(file_path, "w") as f:
                json.dump(data_to_save, f, indent=2)
            print(f"World data saved to {file_path}")
        except Exception as e:
            print(f"Error saving world data to {file_path}: {e}")
