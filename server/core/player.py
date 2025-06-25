import json
import math # For floor

# Globals populated by load_game_data()
CLASSES_DATA = {}
RACES_DATA = {}
ITEMS_DATA = {}

# ANSI Color Codes
ANSI_BLUE = "\033[94m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_RESET = "\033[0m"


def load_game_data():
    global CLASSES_DATA, RACES_DATA, ITEMS_DATA
    try:
        with open("server/data/classes.json", "r") as f: CLASSES_DATA = json.load(f)
    except Exception as e: print(f"ERROR loading classes.json: {e}")
    try:
        with open("server/data/races.json", "r") as f: RACES_DATA = json.load(f)
    except Exception as e: print(f"ERROR loading races.json: {e}")
    try:
        with open("server/data/items.json", "r") as f: ITEMS_DATA = json.load(f)
    except FileNotFoundError: ITEMS_DATA = {}; print("INFO: server/data/items.json not found.")
    except Exception as e: print(f"ERROR loading items.json: {e}")

class Player:
    EQUIPMENT_SLOT_HEAD = "Head"; EQUIPMENT_SLOT_NECK = "Neck"; EQUIPMENT_SLOT_CHEST = "Chest"
    EQUIPMENT_SLOT_BACK = "Back"; EQUIPMENT_SLOT_SHOULDERS = "Shoulders"; EQUIPMENT_SLOT_WRISTS = "Wrists"
    EQUIPMENT_SLOT_HANDS = "Hands"; EQUIPMENT_SLOT_WEAPON_MAIN = "Weapon (Main Hand)"
    EQUIPMENT_SLOT_WEAPON_OFF = "Weapon (Off Hand)"; EQUIPMENT_SLOT_RING_1 = "Finger 1"
    EQUIPMENT_SLOT_RING_2 = "Finger 2"; EQUIPMENT_SLOT_LEGS = "Legs"; EQUIPMENT_SLOT_FEET = "Feet"
    EQUIPMENT_SLOT_RELIC = "Relic"; EQUIPMENT_SLOT_LIGHT_SOURCE = "Light Source"
    ALL_EQUIPMENT_SLOTS = [
        EQUIPMENT_SLOT_HEAD, EQUIPMENT_SLOT_NECK, EQUIPMENT_SLOT_CHEST, EQUIPMENT_SLOT_BACK,
        EQUIPMENT_SLOT_SHOULDERS, EQUIPMENT_SLOT_WRISTS, EQUIPMENT_SLOT_HANDS,
        EQUIPMENT_SLOT_WEAPON_MAIN, EQUIPMENT_SLOT_WEAPON_OFF, EQUIPMENT_SLOT_RING_1,
        EQUIPMENT_SLOT_RING_2, EQUIPMENT_SLOT_LEGS, EQUIPMENT_SLOT_FEET, EQUIPMENT_SLOT_RELIC,
        EQUIPMENT_SLOT_LIGHT_SOURCE
    ]
    STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

    def __init__(self, user, player_class_name="Fighter", race_name="Human", name="Adventurer"):
        self.user = user; self.name = name; self.player_class_name = player_class_name
        self.race_name = race_name; self.level = 1; self.xp = 0; self.next_level_xp = 300
        self.base_stats = {"STR":10,"DEX":10,"CON":10,"INT":10,"WIS":10,"CHA":10}
        self.current_hp = 0; self.max_hp = 0; self.temporary_hp = 0
        self.current_mp = 0; self.max_mp = 0; self.spell_slots = {}
        self.equipment = {slot: None for slot in Player.ALL_EQUIPMENT_SLOTS}
        self.inventory = [] # List of item data dictionaries or item IDs
        self.room_id = "STARTING_ROOM_ID"
        self.assign_standard_array({"STR":15,"DEX":14,"CON":13,"INT":12,"WIS":10,"CHA":8}, initial_setup=True)
        self.recalculate_all_stats(full_heal=True)

    def get_stat_score_racial_and_base(self, stat_name):
        stat_name_upper = stat_name.upper(); score = self.base_stats.get(stat_name_upper, 10)
        if RACES_DATA:
            race_data = RACES_DATA.get(self.race_name)
            if race_data: score += race_data.get("ability_score_increase", {}).get(stat_name_upper, 0)
        return score

    def get_stat_score(self, stat_name):
        score = self.get_stat_score_racial_and_base(stat_name)
        stat_name_upper = stat_name.upper()
        for item_data in self.equipment.values():
            if item_data: score += item_data.get("effects", {}).get("bonus_stats", {}).get(stat_name_upper, 0)
        return min(score, 50)

    def get_stat_modifier(self, stat_name):
        return math.floor((self.get_stat_score(stat_name) - 10) / 2)

    def calculate_proficiency_bonus(self):
        if self.level < 5: return 2;
        if self.level < 9: return 3;
        if self.level < 13: return 4;
        if self.level < 17: return 5;
        if self.level < 21: return 6;
        if self.level < 25: return 7;
        if self.level < 30: return 8;
        if self.level < 40: return 9;
        if self.level < 50: return 10;
        if self.level < 60: return 11;
        if self.level < 70: return 12;
        if self.level < 80: return 13;
        if self.level < 90: return 14;
        return 15;

    def calculate_max_hp(self):
        if not CLASSES_DATA: return 10 + self.get_stat_modifier("CON")
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return 10 + self.get_stat_modifier("CON")
        hit_die = class_data.get("hit_die", 6); con_modifier = self.get_stat_modifier("CON"); max_hp_val = 0
        if self.level == 1: max_hp_val = hit_die + con_modifier
        else:
            hp_per_level = max(1, math.ceil(hit_die / 2) + con_modifier)
            max_hp_val = (hit_die + con_modifier) + (hp_per_level * (self.level - 1))
        if RACES_DATA:
            race_data = RACES_DATA.get(self.race_name, {})
            if race_data and any(trait.get("name") == "Dwarven Toughness" for trait in race_data.get("traits",[])): max_hp_val += self.level
        for item_data in self.equipment.values():
            if item_data: max_hp_val += item_data.get("effects", {}).get("bonus_hp", 0)
        return max(1, max_hp_val)

    def calculate_ac(self):
        dex_modifier = self.get_stat_modifier("DEX")
        calculated_ac = 10 + dex_modifier
        equipped_armor_data = self.equipment.get(Player.EQUIPMENT_SLOT_CHEST)
        if equipped_armor_data:
            props = equipped_armor_data.get("properties", {}); armor_type = props.get("armor_type")
            base_ac_value = props.get("base_ac_value", 0)
            if armor_type == "light": calculated_ac = base_ac_value + dex_modifier
            elif armor_type == "medium": calculated_ac = base_ac_value + min(dex_modifier, props.get("dex_cap_bonus", 2))
            elif armor_type == "heavy": calculated_ac = base_ac_value
        total_bonus_ac_from_effects = 0
        for item_data in self.equipment.values():
            if item_data: total_bonus_ac_from_effects += item_data.get("effects", {}).get("bonus_ac", 0)
        calculated_ac += total_bonus_ac_from_effects
        return calculated_ac

    def get_attack_bonus(self, ability_stat_name, is_proficient_with_weapon=True):
        prof_bonus = self.proficiency_bonus if is_proficient_with_weapon else 0
        return self.get_stat_modifier(ability_stat_name) + prof_bonus

    def get_saving_throw_bonus(self, ability_stat_name):
        if not CLASSES_DATA: return self.get_stat_modifier(ability_stat_name)
        class_data = CLASSES_DATA.get(self.player_class_name)
        is_proficient = class_data and ability_stat_name.upper() in class_data.get("saving_throw_proficiencies", [])
        prof_bonus = self.proficiency_bonus if is_proficient else 0
        return self.get_stat_modifier(ability_stat_name) + prof_bonus

    def get_spell_save_dc(self):
        if not CLASSES_DATA: return 8
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data or not class_data.get("spellcasting_ability"): return 0
        spell_mod = self.get_stat_modifier(class_data["spellcasting_ability"])
        return 8 + self.proficiency_bonus + spell_mod

    def recalculate_all_stats(self, full_heal=False):
        if not (CLASSES_DATA and RACES_DATA and ITEMS_DATA): load_game_data()
        self.proficiency_bonus = self.calculate_proficiency_bonus()
        old_max_hp = self.max_hp; self.max_hp = self.calculate_max_hp()
        if full_heal or self.current_hp <= 0: self.current_hp = self.max_hp
        else:
            hp_increase = self.max_hp - old_max_hp; self.current_hp = min(self.max_hp, self.current_hp + hp_increase)
            if self.current_hp <= 0 and self.max_hp > 0: self.current_hp = 1
        self.ac = self.calculate_ac()

    def assign_standard_array(self, assignment_map, initial_setup=False):
        if sorted(assignment_map.values())==sorted(self.STANDARD_ARRAY) and set(assignment_map.keys())==set(self.base_stats.keys()):
            self.base_stats = assignment_map.copy()
            if not initial_setup: self.recalculate_all_stats(full_heal=True)
        else: print(f"Error: Invalid standard array assignment for {self.name}.")

    def add_xp(self, amount):
        self.xp += amount
        if self.xp >= self.next_level_xp: self.level_up()

    def level_up(self):
        self.level += 1; self.next_level_xp = self.next_level_xp * 2
        self.recalculate_all_stats(full_heal=True)
        print(f"Ding! {self.name} reached level {self.level}!")

    def equip_item(self, item_to_equip_ref, target_slot_key=None):
        item_data=None; found_in_inventory_ref=None
        if isinstance(item_to_equip_ref,dict) and "name" in item_to_equip_ref: item_data=item_to_equip_ref
        elif isinstance(item_to_equip_ref,str):
            item_data_from_db=ITEMS_DATA.get(item_to_equip_ref)
            if item_data_from_db:
                for i,inv_item in enumerate(self.inventory):
                    if (isinstance(inv_item,str) and inv_item==item_to_equip_ref) or \
                       (isinstance(inv_item,dict) and (inv_item.get("id")==item_to_equip_ref or inv_item.get("name","").lower()==item_to_equip_ref.lower())):
                        item_data=dict(item_data_from_db) if isinstance(inv_item,str) else inv_item; found_in_inventory_ref=inv_item; break
                if not found_in_inventory_ref and item_data_from_db : return f"You don't have '{item_data_from_db.get('name',item_to_equip_ref)}' in inventory."
                elif not item_data_from_db:
                    for inv_item_dict in self.inventory:
                        if isinstance(inv_item_dict,dict) and inv_item_dict.get("name","").lower()==item_to_equip_ref.lower():
                            item_data=inv_item_dict;found_in_inventory_ref=inv_item_dict;break
                    if not item_data: return f"Item ID or Name '{item_to_equip_ref}' not found."
            else:
                for inv_item_dict in self.inventory:
                    if isinstance(inv_item_dict,dict) and inv_item_dict.get("name","").lower()==item_to_equip_ref.lower():
                        item_data=inv_item_dict;found_in_inventory_ref=inv_item_dict;break
                if not item_data: return f"Cannot find item named '{item_to_equip_ref}'."
        else: return "Invalid item reference."
        if not item_data: return "Could not identify item."
        item_name=item_data.get("name","Item"); item_slots=item_data.get("equip_slots",[])
        if isinstance(item_slots,str):item_slots=[item_slots]
        if not item_slots: return f"'{item_name}' cannot be equipped."
        chosen_slot=None
        if target_slot_key and target_slot_key in item_slots and target_slot_key in Player.ALL_EQUIPMENT_SLOTS: chosen_slot=target_slot_key
        else:
            for s in item_slots:
                if s in Player.ALL_EQUIPMENT_SLOTS and not self.equipment.get(s):chosen_slot=s;break
            if not chosen_slot:chosen_slot=item_slots[0]
        if chosen_slot not in Player.ALL_EQUIPMENT_SLOTS:return f"Invalid slot '{chosen_slot}' for '{item_name}'."
        if self.equipment.get(chosen_slot): self.remove_item(chosen_slot,_called_from_equip=True)
        self.equipment[chosen_slot]=item_data
        if found_in_inventory_ref and found_in_inventory_ref in self.inventory: self.inventory.remove(found_in_inventory_ref)
        self.recalculate_all_stats()
        msg=f"You equip {item_name} on your {chosen_slot}."
        if hasattr(self.user,'send_message'):self.user.send_message(msg)
        return msg

    def remove_item(self, slot_name, _called_from_equip=False):
        if slot_name not in Player.ALL_EQUIPMENT_SLOTS:
            msg=f"Invalid slot: {slot_name}.";
            if not _called_from_equip and hasattr(self.user,'send_message'):self.user.send_message(msg)
            return msg
        item_to_remove=self.equipment.get(slot_name)
        if not item_to_remove:
            msg=f"Nothing equipped on {slot_name}."
            if not _called_from_equip and hasattr(self.user,'send_message'):self.user.send_message(msg)
            return msg
        self.inventory.append(item_to_remove); self.equipment[slot_name]=None
        self.recalculate_all_stats()
        msg=f"You remove {item_to_remove.get('name','item')} from {slot_name}."
        # For remove command, message is handled by command handler based on return type.
        # if not _called_from_equip and hasattr(self.user,'send_message'):self.user.send_message(msg)
        # print(f"INFO: {self.name} unequipped {item_to_remove.get('name', 'item')} from {slot_name}.") # Server log
        return item_to_remove

    def display_sheet(self):
        if not (CLASSES_DATA and RACES_DATA and ITEMS_DATA): load_game_data()
        sheet = [f"{ANSI_GREEN}--- Character Sheet: {self.name} ---{ANSI_RESET}",
                 f"Race: {self.race_name:<15} Class: {self.player_class_name:<15} Level: {self.level}",
                 f"XP: {self.xp}/{self.next_level_xp}", f"{ANSI_GREEN}{'-' * 30}{ANSI_RESET}",
                 f"HP: {self.current_hp}/{self.max_hp} (Temp HP: {self.temporary_hp})",
                 f"AC: {self.ac:<4} Proficiency Bonus: +{self.proficiency_bonus}",
                 f"{ANSI_GREEN}{'-' * 30}{ANSI_RESET}", "Stats: (Score/Modifier) [Bonus from Gear]",
                 f"{ANSI_GREEN}{'-' * 30}{ANSI_RESET}"]
        for stat_key in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            base_plus_racial_score = self.get_stat_score_racial_and_base(stat_key)
            final_score = self.get_stat_score(stat_key)
            modifier = self.get_stat_modifier(stat_key)
            gear_bonus = 0
            for item_data in self.equipment.values():
                if item_data: gear_bonus += item_data.get("effects", {}).get("bonus_stats", {}).get(stat_key, 0)
            mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
            stat_display = f"  {stat_key}: {final_score:>2} ({mod_str})"
            if gear_bonus > 0: stat_display = f"  {stat_key}: {ANSI_BLUE}{final_score:>2}{ANSI_RESET} ({mod_str}) [{ANSI_BLUE}+{gear_bonus}{ANSI_RESET}]"
            elif gear_bonus < 0: stat_display = f"  {stat_key}: {ANSI_RED}{final_score:>2}{ANSI_RESET} ({mod_str}) [{ANSI_RED}{gear_bonus}{ANSI_RESET}]"
            sheet.append(stat_display)
        sheet.append(f"{ANSI_GREEN}{'-' * 30}{ANSI_RESET}"); sheet.append("Equipment:")
        for slot in Player.ALL_EQUIPMENT_SLOTS:
            item = self.equipment.get(slot)
            item_name = item.get('name', 'Nothing') if item else f"{ANSI_RED}Nothing{ANSI_RESET}"
            if item and item_name != f"{ANSI_RED}Nothing{ANSI_RESET}": item_name = f"{ANSI_GREEN}{item_name}{ANSI_RESET}"
            sheet.append(f"  {slot:<20}: {item_name}")
        sheet.append(f"{ANSI_GREEN}--- End of Sheet ---{ANSI_RESET}")
        return "\n".join(sheet)

    def display_inventory(self):
        """Formats and returns the player's inventory listing."""
        if not self.inventory:
            return "Your inventory is empty."

        inventory_list = [f"{ANSI_GREEN}--- Your Inventory ---{ANSI_RESET}"]
        # Current inventory stores item data dicts or item_ids (if loaded from save)
        # A more robust system would use ItemInstance objects with quantity
        # For now, list names, assuming quantity 1 for each entry if not specified
        for item_ref in self.inventory:
            item_name = "Unknown Item"
            if isinstance(item_ref, dict): # Item data dict
                item_name = item_ref.get("name", "Unnamed Item")
            elif isinstance(item_ref, str): # Item ID
                # Try to look up in ITEMS_DATA if inventory stores IDs
                master_item_data = ITEMS_DATA.get(item_ref)
                if master_item_data:
                    item_name = master_item_data.get("name", item_ref)
                else:
                    item_name = item_ref # Show ID if not found
            inventory_list.append(f"- {item_name}")

        inventory_list.append(f"{ANSI_GREEN}--------------------{ANSI_RESET}")
        return "\n".join(inventory_list)

```
**Changes made to `player.py`:**
1.  **`display_inventory()` method added**:
    *   Checks if `self.inventory` is empty.
    *   If not, it iterates through `self.inventory`.
    *   It handles two cases for items in inventory:
        *   If an item is a dictionary (as it would be if unequipped), it gets the "name".
        *   If an item is a string (placeholder for if inventory stores item IDs from a save file), it tries to look up the name in `ITEMS_DATA`, defaulting to showing the ID.
    *   Formats the list with a header and footer.
    *   (Note: This basic version doesn't handle item quantities or stacking explicitly. A more advanced inventory would use `ItemInstance` objects.)

Now, for the `main.py` part.
