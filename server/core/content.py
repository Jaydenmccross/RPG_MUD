import json
import os
import time # For MobInstance time_of_death

MOBS_FILE = "server/data/mobs.json"
ITEMS_FILE = "server/data/items.json"

# EQUIP_SLOTS is not used in this file after ItemEditor changes, can be removed if not used elsewhere.
# For now, keeping it in case other modules might import it, though ideally they wouldn't.
EQUIP_SLOTS = [
    "Head", "Neck", "Back", "Shoulders", "Chest", "Wrists", "Hands",
    "Ring Left", "Ring Right", "Legs", "Feet", "Relic", "Light Source",
    "Main Hand", "Off Hand"
]

class Mob:
    def __init__(self, mob_id, name, description, max_hp=10, speed=30, ac=10,
                 attack_bonus=0, damage_dice="1d4", damage_type="physical",
                 xp_value=10, is_aggressive=False, loot_table=None):
        self.id = mob_id
        self.name = name
        self.description = description
        self.max_hp = max_hp
        self.speed = speed # Base speed
        self.ac = ac
        self.attack_bonus = attack_bonus
        self.damage_dice = damage_dice
        self.damage_type = damage_type
        self.xp_value = xp_value
        self.is_aggressive = is_aggressive
        self.loot_table = loot_table if loot_table is not None else {}

    @staticmethod
    def load_mobs():
        if not os.path.exists(MOBS_FILE):
            print(f"Warning: Mob data file not found at {MOBS_FILE}")
            return {}
        try:
            with open(MOBS_FILE, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {MOBS_FILE}")
            return {}
        except Exception as e:
            print(f"Error loading {MOBS_FILE}: {e}")
            return {}

        mobs = {}
        for mob_id, mob_data in data.items():
            if not isinstance(mob_data, dict):
                print(f"Warning: Skipping malformed mob data for ID '{mob_id}' in {MOBS_FILE}.")
                continue

            mobs[mob_id] = Mob(
                mob_id=mob_id,
                name=mob_data.get("name", mob_id),
                description=mob_data.get("description", "An unremarkable creature."),
                max_hp=int(mob_data.get("max_hp", mob_data.get("hp", 10))), # Support legacy "hp", ensure int
                speed=int(mob_data.get("speed", 30)),
                ac=int(mob_data.get("ac", 10)),
                attack_bonus=int(mob_data.get("attack_bonus", mob_data.get("attack",0))), # Support legacy "attack"
                damage_dice=mob_data.get("damage_dice", "1d4"),
                damage_type=mob_data.get("damage_type", "physical"),
                xp_value=int(mob_data.get("xp_value", 0)),
                is_aggressive=mob_data.get("is_aggressive", False),
                loot_table=mob_data.get("loot_table")
            )
        return mobs

class MobInstance:
    def __init__(self, mob_blueprint: Mob):
        self.mob_blueprint = mob_blueprint
        self.name = mob_blueprint.name
        self.max_hp = mob_blueprint.max_hp
        self.current_hp = mob_blueprint.max_hp

        self.ac = mob_blueprint.ac
        self.attack_bonus = mob_blueprint.attack_bonus
        self.damage_dice = mob_blueprint.damage_dice
        self.damage_type = mob_blueprint.damage_type
        self.xp_value = mob_blueprint.xp_value
        self.is_aggressive = mob_blueprint.is_aggressive
        self.loot_table = mob_blueprint.loot_table

        self.base_speed = mob_blueprint.speed # Store the blueprint's speed
        self.current_speed = mob_blueprint.speed # Initial current speed
        self.status_effects = [] # List of dicts: {"type": "reduce_speed", "amount": 10, "duration_rounds": 1, "applied_round": X}

        self.in_combat = False
        self.target = None
        self.time_of_death = None
        self.room = None # Will be set when mob is spawned into a room

    def is_alive(self):
        return self.current_hp > 0

    def take_damage(self, amount, attacker=None): # Added attacker for consistency
        self.current_hp = max(0, self.current_hp - amount)
        if not self.is_alive():
            self.handle_death(killer=attacker)

    def handle_death(self, killer=None):
        self.in_combat = False
        self.target = None
        self.time_of_death = time.time()
        # Note: Actual removal from room.mob_instances and ACTIVE_COMBATANTS is handled by main.py or game_tick
        print(f"[INFO] MobInstance {self.name} (ID: {self.mob_blueprint.id}) has died.")

    def recalculate_derived_stats(self):
        """Recalculates stats based on status effects. Currently only speed."""
        self.current_speed = self.base_speed
        speed_reduction = 0
        for effect in self.status_effects:
            if effect.get("type") == "reduce_speed":
                speed_reduction += effect.get("amount", 0)

        self.current_speed = max(5, self.base_speed - speed_reduction) # Ensure speed doesn't drop too low (e.g., min 5)

    def apply_status_effect(self, effect_to_apply):
        """
        Applies a status effect to the mob.
        effect_to_apply is a dict like:
        {"type": "reduce_speed", "amount": 10, "duration_rounds": 1, "applied_round": current_round_counter}
        """
        # TODO: Handle stacking of same effect types (e.g., does new speed reduction replace or add?)
        # For now, assume new effects of the same type might stack or override based on external logic.
        # Simple append for now.

        # Check if an effect of the same type already exists, if so, perhaps refresh or stack.
        # For "reduce_speed", let's make it so the largest reduction applies, or they stack if from different sources (not handled yet)
        # Simple approach: remove existing effect of same type, add new one. Or, only add if new is stronger/longer.
        # For Ray of Frost, it's a fixed duration and amount, so multiple hits might just refresh duration.

        existing_effect_index = -1
        for i, eff in enumerate(self.status_effects):
            if eff.get("type") == effect_to_apply.get("type"):
                 # If new effect is stronger or has longer duration (or just refresh)
                if effect_to_apply.get("amount",0) >= eff.get("amount",0): # Basic override if stronger/equal
                    existing_effect_index = i
                break # Assuming one active effect of this type for now for simplicity

        if existing_effect_index != -1:
            self.status_effects[existing_effect_index] = effect_to_apply.copy()
        else:
            self.status_effects.append(effect_to_apply.copy())

        self.recalculate_derived_stats()
        # print(f"DEBUG: Applied status {effect_to_apply['type']} to {self.name}. Effects: {self.status_effects}, Speed: {self.current_speed}")


    def tick_status_effects(self, current_round_counter):
        """
        Ticks down duration of status effects. Removes expired ones.
        Called periodically (e.g., each game round or mob's turn).
        """
        expired_effects = False
        active_effects = []
        for effect in self.status_effects:
            duration = effect.get("duration_rounds")
            applied_round = effect.get("applied_round")
            if duration is not None and applied_round is not None:
                if current_round_counter >= applied_round + duration:
                    expired_effects = True
                    # print(f"DEBUG: Effect {effect['type']} expired for {self.name}")
                    continue # Skip adding to active_effects
            active_effects.append(effect)

        if expired_effects:
            self.status_effects = active_effects
            self.recalculate_derived_stats()
            # print(f"DEBUG: Effects updated for {self.name}. Effects: {self.status_effects}, Speed: {self.current_speed}")


    def __repr__(self):
        return f"<MobInstance '{self.mob_blueprint.name}' HP:{self.current_hp}/{self.max_hp}>"

class Item: # Item class remains largely unchanged from previous correct version
    def __init__(self, item_id, name, item_type="misc",
                 effects=None, description="", weight=0.0,
                 equip_slots=None, properties=None, value=0):
        self.id = item_id
        self.name = name
        self.type = item_type # E.g., "weapon", "armor", "potion", "container", "misc"
        self.effects = effects if effects is not None else {}
        self.description = description
        self.weight = weight
        # equip_slots should be a list or None
        self.equip_slots = equip_slots if isinstance(equip_slots, list) else ([equip_slots] if equip_slots else [])
        self.properties = properties if properties is not None else {} # For type-specific data like damage, AC
        self.value = value # Gold piece value

    @staticmethod
    def load_items():
        if not os.path.exists(ITEMS_FILE):
            print(f"Warning: Item data file not found at {ITEMS_FILE}")
            return {}
        try:
            with open(ITEMS_FILE, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {ITEMS_FILE}")
            return {}
        except Exception as e:
            print(f"Error loading {ITEMS_FILE}: {e}")
            return {}

        items = {}
        for item_id, item_data in data.items():
            if not isinstance(item_data, dict):
                print(f"Warning: Skipping malformed item data for ID '{item_id}' in {ITEMS_FILE}.")
                continue
            items[item_id] = Item(
                item_id=item_id,
                name=item_data.get("name", item_id),
                item_type=item_data.get("type", "misc"),
                effects=item_data.get("effects"), # None will become {} in __init__
                description=item_data.get("description", ""),
                weight=float(item_data.get("weight", 0.0)),
                equip_slots=item_data.get("equip_slots"), # None will become []
                properties=item_data.get("properties"), # None will become {}
                value=int(item_data.get("value",0))
            )
        return items

class ItemInstance:
    def __init__(self, item_blueprint: Item, quantity=1):
        self.item_blueprint = item_blueprint
        self.quantity = quantity
        # Instance-specific properties like current_charges, specific_mods could go here
        # For now, they are mostly on the blueprint.

    def total_weight(self):
        return self.quantity * self.item_blueprint.weight

    def __repr__(self):
        return f"<ItemInstance '{self.item_blueprint.name}' x{self.quantity}>"

class ContainerInstance(ItemInstance):
    def __init__(self, item_blueprint: Item, quantity=1): # Quantity for containers is usually 1
        super().__init__(item_blueprint, quantity)
        self.contents = [] # List of ItemInstance objects
        # Max capacity is on item_blueprint.properties.get("container_capacity_weight") or similar

    def current_capacity_used(self):
        return sum(item.total_weight() for item in self.contents)

    def add_item(self, item_to_add: ItemInstance):
        max_cap = self.item_blueprint.properties.get("container_capacity_weight", 0)
        if max_cap > 0: # 0 or no property means infinite capacity
            if self.current_capacity_used() + item_to_add.total_weight() > max_cap:
                return False, "It won't fit."

        # Check for stacking
        for existing_item in self.contents:
            if existing_item.item_blueprint.id == item_to_add.item_blueprint.id:
                # Assuming non-unique items stack. Unique items (e.g. with specific mods) would need different handling.
                existing_item.quantity += item_to_add.quantity
                return True, f"Added to existing stack of {existing_item.item_blueprint.name}."

        self.contents.append(item_to_add)
        return True, f"{item_to_add.item_blueprint.name} added to {self.item_blueprint.name}."

    def remove_item(self, item_name_or_id_to_remove, quantity_to_remove=1):
        item_found_instance = None
        idx_to_remove_from = -1

        for idx, item_in_container in enumerate(self.contents):
            if (item_in_container.item_blueprint.name.lower() == item_name_or_id_to_remove.lower() or
                item_in_container.item_blueprint.id == item_name_or_id_to_remove):

                if item_in_container.quantity >= quantity_to_remove:
                    item_found_instance = ItemInstance(item_in_container.item_blueprint, quantity_to_remove)
                    item_in_container.quantity -= quantity_to_remove
                    if item_in_container.quantity <= 0:
                        idx_to_remove_from = idx
                    break
                else: # Not enough quantity
                    return None, f"Not enough {item_in_container.item_blueprint.name} in the {self.item_blueprint.name}."

        if idx_to_remove_from != -1:
            self.contents.pop(idx_to_remove_from)

        if item_found_instance:
            return item_found_instance, f"Removed {item_found_instance.item_blueprint.name} from {self.item_blueprint.name}."
        return None, f"Could not find '{item_name_or_id_to_remove}' in {self.item_blueprint.name}."


    def list_contents(self, depth=0): # For display
        lines = []
        prefix = "  " * depth
        for item in self.contents:
            line = f"{prefix}- {item.item_blueprint.name} (x{item.quantity})"
            lines.append(line)
            if isinstance(item, ContainerInstance): # If a container is inside another
                lines.append(f"{prefix}  Contents of {item.item_blueprint.name}:")
                lines.extend(item.list_contents(depth + 2))
        return lines

    def __repr__(self):
        return f"<ContainerInstance '{self.item_blueprint.name}' x{self.quantity} [{len(self.contents)} item types]>"

# Ensure ITEMS_DATA is loaded for ItemInstance context if needed directly
# if not ITEMS_DATA:
#     ITEMS_DATA = Item.load_items()
# This is usually handled by main.py or core_load_game_data()
