import json
import math # For floor
from server.core.combat import roll_dice

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
    ALL_SKILLS = [
        "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
        "History", "Insight", "Intimidation", "Investigation", "Medicine",
        "Nature", "Perception", "Performance", "Persuasion", "Religion",
        "Sleight of Hand", "Stealth", "Survival"
    ]
    SKILL_TO_ABILITY_MAP = {
        "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT",
        "Athletics": "STR", "Deception": "CHA", "History": "INT",
        "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT",
        "Medicine": "WIS", "Nature": "INT", "Perception": "WIS",
        "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT",
        "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS"
    }

    def __init__(self, user, player_class_name="Fighter", race_name="Human", name="Adventurer", base_stats=None):
        self.user = user; self.name = name; self.player_class_name = player_class_name
        self.race_name = race_name
        self.level = 1; self.xp = 0; self.next_level_xp = 300

        if base_stats: self.base_stats = base_stats.copy()
        else: self.base_stats = {"STR":10,"DEX":10,"CON":10,"INT":10,"WIS":10,"CHA":10}

        self.current_hp = 0; self.max_hp = 0; self.temporary_hp = 0
        self.current_mp = 0; self.max_mp = 0; self.spell_slots = {}
        self.equipment = {slot: None for slot in Player.ALL_EQUIPMENT_SLOTS}
        self.inventory = []
        self.room_id = "start"
        self.skill_proficiencies = set()
        self.used_abilities_this_rest = set()
        self.has_taken_action_this_turn = False # For simple turn action economy

        self.in_combat = False
        self.target = None

        if not (CLASSES_DATA and RACES_DATA): load_game_data()

        class_data = CLASSES_DATA.get(self.player_class_name)
        if class_data:
            for skill in class_data.get("skill_proficiencies", []):
                self.skill_proficiencies.add(skill)

        base_race_data, sub_race_data = self._get_race_data_parts()
        if base_race_data:
            for trait in base_race_data.get("traits", []):
                if trait.get("name") == "Keen Senses" and "Perception" in Player.ALL_SKILLS :
                    self.skill_proficiencies.add("Perception")
                if trait.get("name") == "Menacing" and "Intimidation" in Player.ALL_SKILLS:
                    self.skill_proficiencies.add("Intimidation")
        if sub_race_data:
             for trait in sub_race_data.get("traits", []): pass

        self.recalculate_all_stats(full_heal=True)

    def _get_race_data_parts(self):
        if not RACES_DATA: return None, None
        for r_name, r_info in RACES_DATA.items():
            if r_name == self.race_name:
                return r_info, None
            if "subraces" in r_info and self.race_name in r_info["subraces"]:
                return r_info, r_info["subraces"][self.race_name]
        return None, None

    def get_stat_score_racial_and_base(self, stat_name):
        stat_name_upper = stat_name.upper()
        score = self.base_stats.get(stat_name_upper, 8)
        base_race_data, sub_race_data = self._get_race_data_parts()
        if base_race_data:
            score += base_race_data.get("ability_score_increase", {}).get(stat_name_upper, 0)
        if sub_race_data:
            score += sub_race_data.get("ability_score_increase", {}).get(stat_name_upper, 0)
        return score

    def get_stat_score(self, stat_name):
        score = self.get_stat_score_racial_and_base(stat_name)
        stat_name_upper = stat_name.upper()
        for item_data in self.equipment.values():
            if item_data: score += item_data.get("effects", {}).get("bonus_stats", {}).get(stat_name_upper, 0)
        return min(score, 50)

    def get_stat_modifier(self, stat_name):
        return math.floor((self.get_stat_score(stat_name) - 10) / 2)

    def get_skill_bonus(self, skill_name):
        if skill_name not in Player.SKILL_TO_ABILITY_MAP: return 0
        ability_stat = Player.SKILL_TO_ABILITY_MAP[skill_name]
        modifier = self.get_stat_modifier(ability_stat)
        prof_bonus = self.proficiency_bonus if skill_name in self.skill_proficiencies else 0
        return modifier + prof_bonus

    def calculate_proficiency_bonus(self):
        # Simplified: plateaus earlier than D&D 5e to suit 1-100 range better.
        if self.level < 5: return 2;
        if self.level < 9: return 3;
        if self.level < 13: return 4;
        if self.level < 17: return 5;
        if self.level < 25: return 6;
        if self.level < 35: return 7;
        if self.level < 45: return 8;
        if self.level < 55: return 9;
        if self.level < 65: return 10;
        if self.level < 75: return 11;
        if self.level < 85: return 12;
        return 13;

    def calculate_max_hp(self):
        if not CLASSES_DATA: return 10 + self.get_stat_modifier("CON")
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return 10 + self.get_stat_modifier("CON")
        hit_die = class_data.get("hit_die", 6); con_modifier = self.get_stat_modifier("CON"); max_hp_val = 0
        if self.level == 1: max_hp_val = hit_die + con_modifier
        else:
            avg_roll_plus_one = (hit_die // 2) + 1
            hp_per_level = max(1, avg_roll_plus_one + con_modifier)
            max_hp_val = (hit_die + con_modifier) + (hp_per_level * (self.level - 1))
        base_race_data, sub_race_data = self._get_race_data_parts()
        racial_traits = []
        if base_race_data and base_race_data.get("traits"): racial_traits.extend(base_race_data.get("traits"))
        if sub_race_data and sub_race_data.get("traits"): racial_traits.extend(sub_race_data.get("traits"))
        for trait in racial_traits:
            if trait.get("name") == "Dwarven Toughness": max_hp_val += self.level; break
        for item_data in self.equipment.values():
            if item_data: max_hp_val += item_data.get("effects", {}).get("bonus_hp", 0)
        return max(1, max_hp_val)

    def calculate_ac(self):
        dex_modifier = self.get_stat_modifier("DEX"); calculated_ac = 10 + dex_modifier
        equipped_armor_data = self.equipment.get(Player.EQUIPMENT_SLOT_CHEST)
        if equipped_armor_data:
            props = equipped_armor_data.get("properties", {}); armor_type = props.get("armor_type")
            base_ac_value = props.get("base_ac_value", 0)
            if armor_type == "light": calculated_ac = base_ac_value + dex_modifier
            elif armor_type == "medium": calculated_ac = base_ac_value + min(dex_modifier, props.get("dex_cap_bonus", 2))
            elif armor_type == "heavy": calculated_ac = base_ac_value
        total_bonus_ac_from_effects = sum(item_data.get("effects", {}).get("bonus_ac", 0) for item_data in self.equipment.values() if item_data)
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

    def add_xp(self, amount):
        self.xp += amount
        if self.xp >= self.next_level_xp: self.level_up()

    def level_up(self):
        self.level += 1; self.next_level_xp = self.next_level_xp * 2
        self.recalculate_all_stats(full_heal=True)
        if hasattr(self.user, 'send_message'):
             self.user.send_message(f"{ANSI_GREEN}Ding! You reached level {self.level}!{ANSI_RESET}")

    def get_class_feature(self, feature_name):
        if not CLASSES_DATA: load_game_data()
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return None
        found_feature = None
        for level_int in range(1, self.level + 1):
            level_str = str(level_int)
            features_at_level = class_data.get("features_by_level", {}).get(level_str, [])
            for feature in features_at_level:
                if feature.get("name") == feature_name:
                    found_feature = feature
        return found_feature

    def can_use_ability(self, ability_name): # Renamed from plan to match existing style
        feature_data = self.get_class_feature(ability_name)
        if not feature_data: return False
        uses = feature_data.get("uses")
        refresh_on = feature_data.get("refresh_on")
        if uses is not None and refresh_on is not None:
            if ability_name in self.used_abilities_this_rest: return False
        return True

    def mark_ability_used(self, ability_name): # Renamed from plan to match existing style
        feature_data = self.get_class_feature(ability_name)
        if feature_data and feature_data.get("uses") is not None and feature_data.get("refresh_on") is not None:
            self.used_abilities_this_rest.add(ability_name)

    def reset_ability_uses_on_rest(self, rest_type="long"):
        abilities_to_clear_from_set = set()
        for ability_name_used in list(self.used_abilities_this_rest):
            feature_data = self.get_class_feature(ability_name_used)
            if feature_data:
                refresh_condition = feature_data.get("refresh_on")
                if refresh_condition == "short_or_long_rest":
                    abilities_to_clear_from_set.add(ability_name_used)
                elif refresh_condition == "long_rest" and rest_type == "long":
                    abilities_to_clear_from_set.add(ability_name_used)
            else: abilities_to_clear_from_set.add(ability_name_used)
        for ab_name in abilities_to_clear_from_set:
            if ab_name in self.used_abilities_this_rest:
                 self.used_abilities_this_rest.remove(ab_name)

    def perform_long_rest(self):
        self.current_hp = self.max_hp
        self.reset_ability_uses_on_rest(rest_type="long")
        return "You feel fully rested and revitalized."

    def reset_turn_actions(self):
        """Resets flags that track actions taken within a conceptual turn."""
        self.has_taken_action_this_turn = False
        # In future, could reset bonus actions, reactions etc.

    def use_second_wind(self):
        if self.player_class_name != "Fighter": return "Only Fighters can use Second Wind."
        feature_name = "Second Wind"
        feature_data = self.get_class_feature(feature_name)
        if not feature_data: return "You do not seem to have the Second Wind ability."

        if self.has_taken_action_this_turn: # Assuming Second Wind is an action for now
            return "You have already taken your action this turn."

        if not self.can_use_ability(feature_name): # Check if it's already used this rest
            return "You have already used Second Wind. You must complete a short or long rest before using it again."

        heal_dice = feature_data.get("effect_dice", "1d10"); base_heal = roll_dice(heal_dice)
        level_bonus = self.level if feature_data.get("level_scaling_property") == "fighter_level_bonus_to_heal" else 0
        total_heal = base_heal + level_bonus; actual_healed_amount = 0

        if self.current_hp < self.max_hp:
            actual_healed_amount = min(total_heal, self.max_hp - self.current_hp)
            self.current_hp += actual_healed_amount
        else:
            self.mark_ability_used(feature_name)
            self.has_taken_action_this_turn = True
            return "You use Second Wind, but you are already at maximum HP!"

        self.mark_ability_used(feature_name)
        self.has_taken_action_this_turn = True
        return f"You use Second Wind and regain {actual_healed_amount} HP. (Rolled {base_heal} from {heal_dice}, +{level_bonus} level bonus = {total_heal} potential)."

    def use_dash(self, direction_name, world_ref): # Pass world reference for exit checking
        """Allows a Rogue (L2+) to Dash. Returns dict for main.py to handle move."""
        if not (self.player_class_name == "Rogue" and self.level >= 2):
            return {"success": False, "message": "Only Rogues of level 2 or higher can Dash."}

        cunning_action_feature = self.get_class_feature("Cunning Action")
        if not cunning_action_feature or "Dash" not in cunning_action_feature.get("grants_abilities", []):
            return {"success": False, "message": "You do not have the Cunning Action: Dash ability."}

        if self.has_taken_action_this_turn:
            return {"success": False, "message": "You have already taken an action this turn."}

        if not self.room:
            return {"success": False, "message": "You are not in a valid room to dash from."}

        # Dashing is a combat maneuver, so allow in combat for now.
        # It consumes the turn's action.

        current_room_obj = self.room # This is a Room object

        # Attempt first move
        room1_id = current_room_obj.exits.get(direction_name)
        if not room1_id:
            return {"success": False, "message": f"You cannot dash {direction_name} - there is no exit there."}

        room1_obj = world_ref.get(room1_id)
        if not room1_obj:
            self.has_taken_action_this_turn = True
            # Player moves into the 'void' if exit is bad, main.py will handle actual move.
            return {"success": True, "rooms_moved": 1, "final_room_id": room1_id, "message": f"You dash {direction_name} into an unfamiliar passage..."}

        # Attempt second move from room1
        room2_id = room1_obj.exits.get(direction_name)
        room2_obj = world_ref.get(room2_id) if room2_id else None

        self.has_taken_action_this_turn = True # Dash consumes the action
        if room2_obj:
            # Successful two-room dash
            return {"success": True, "rooms_moved": 2, "final_room_id": room2_id, "message": f"You swiftly dash {direction_name} two rooms ahead!"}
        else:
            # Only one room move possible
            return {"success": True, "rooms_moved": 1, "final_room_id": room1_id, "message": f"You dash {direction_name} one room ahead."}


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

        sheet.append(f"{ANSI_GREEN}{'-' * 30}{ANSI_RESET}")
        sheet.append("Skills: (Bonus) [* Proficient]")
        sheet.append(f"{ANSI_GREEN}{'-' * 30}{ANSI_RESET}")
        num_skills = len(Player.ALL_SKILLS)
        mid_point = (num_skills + 1) // 2
        for i in range(mid_point):
            skill1_name = Player.ALL_SKILLS[i]
            skill1_bonus = self.get_skill_bonus(skill1_name)
            skill1_prof_char = "*" if skill1_name in self.skill_proficiencies else " "
            skill1_bonus_str = f"+{skill1_bonus}" if skill1_bonus >= 0 else str(skill1_bonus)
            skill1_display = f"  {skill1_name:<18} ({Player.SKILL_TO_ABILITY_MAP.get(skill1_name, '???'):<3}) [{skill1_prof_char}] {skill1_bonus_str:>3}"
            if i + mid_point < num_skills:
                skill2_name = Player.ALL_SKILLS[i + mid_point]
                skill2_bonus = self.get_skill_bonus(skill2_name)
                skill2_prof_char = "*" if skill2_name in self.skill_proficiencies else " "
                skill2_bonus_str = f"+{skill2_bonus}" if skill2_bonus >= 0 else str(skill2_bonus)
                skill2_display = f"  {skill2_name:<18} ({Player.SKILL_TO_ABILITY_MAP.get(skill2_name, '???'):<3}) [{skill2_prof_char}] {skill2_bonus_str:>3}"
                sheet.append(f"{skill1_display.ljust(40)} {skill2_display}")
            else:
                sheet.append(skill1_display)

        sheet.append(f"{ANSI_GREEN}--- End of Sheet ---{ANSI_RESET}")
        return "\n".join(sheet)

    def display_inventory(self):
        if not self.inventory: return "Your inventory is empty."
        inventory_list = [f"{ANSI_GREEN}--- Your Inventory ---{ANSI_RESET}"]
        for item_ref in self.inventory:
            item_name = "Unknown Item"
            if isinstance(item_ref, dict):
                item_name = item_ref.get("name", "Unnamed Item")
            elif isinstance(item_ref, str):
                master_item_data = ITEMS_DATA.get(item_ref)
                if master_item_data: item_name = master_item_data.get("name", item_ref)
                else: item_name = item_ref
            inventory_list.append(f"- {item_name}")
        inventory_list.append(f"{ANSI_GREEN}--------------------{ANSI_RESET}")
        return "\n".join(inventory_list)

    def is_alive(self):
        return self.current_hp > 0

    def take_damage(self, amount, attacker=None):
        self.current_hp -= amount
        # Add combat log message here if desired, e.g., self.user.send_message(f"You take {amount} damage!")
        if self.current_hp <= 0:
            self.current_hp = 0
            self.handle_death(attacker)

    def handle_death(self, killer=None):
        self.in_combat = False
        self.target = None
        # Server-side log
        print(f"[INFO] Player {self.name} has died (killed by {killer.name if killer else 'unknown causes'}).")
        # Player message is handled by main loop after resolve_attack or other death sources

    def add_item_to_inventory(self, item_instance_or_dict):
        # For now, assuming ItemInstance objects are added.
        # If dicts are added (e.g. from old code or simple item gen), they'll just be dicts.
        self.inventory.append(item_instance_or_dict)
        name_to_show = "item"
        if hasattr(item_instance_or_dict, 'item_blueprint'): # ItemInstance
            name_to_show = item_instance_or_dict.item_blueprint.name
        elif isinstance(item_instance_or_dict, dict): # dict
            name_to_show = item_instance_or_dict.get("name", "item")
        return f"You pick up {name_to_show}."

    def remove_item_from_inventory(self, item_name_or_id, quantity=1):
        # This basic version removes the first match by name/id, and only one.
        item_to_remove_idx = -1
        item_instance_found = None
        for i, inst in enumerate(self.inventory):
            name_matches = False
            id_matches = False
            current_item_name = ""
            current_item_id = ""

            if hasattr(inst, 'item_blueprint'): # ItemInstance
                current_item_name = inst.item_blueprint.name.lower()
                current_item_id = inst.item_blueprint.id.lower()
            elif isinstance(inst, dict): # dict based item
                current_item_name = inst.get("name", "").lower()
                current_item_id = inst.get("id", "").lower()

            if current_item_name == item_name_or_id.lower() or current_item_id == item_name_or_id.lower():
                item_to_remove_idx = i
                item_instance_found = inst # This could be an ItemInstance or a dict
                break

        if item_instance_found:
            # TODO: Handle quantity if items are stackable
            self.inventory.pop(item_to_remove_idx)
            return item_instance_found # Return the actual item/dict removed
        return f"You don't have '{item_name_or_id}'."

    def get_attack_details(self):
        attack_stat = "STR"; damage_dice = "1d4"; damage_type = "bludgeoning"
        weapon = self.equipment.get(Player.EQUIPMENT_SLOT_WEAPON_MAIN)
        is_proficient = True # Default to proficient

        if weapon: # Player has a weapon equipped
            props = weapon.get("properties", {})
            damage_dice = props.get("damage_dice", damage_dice)
            damage_type = props.get("damage_type", damage_type)

            # Determine attack stat (STR or DEX for finesse)
            if props.get("finesse"):
                if self.get_stat_score("DEX") > self.get_stat_score("STR"):
                    attack_stat = "DEX"
            # TODO: Add logic for ranged weapons using DEX by default if weapon has "ranged" property

            # Check proficiency
            # class_data = CLASSES_DATA.get(self.player_class_name, {})
            # weapon_proficiencies = class_data.get("weapon_proficiencies", [])
            # weapon_category = weapon.get("category", "simple") # e.g. "simple", "martial"
            # specific_weapon_name = weapon.get("name", "").lower()
            # if not (weapon_category in weapon_proficiencies or
            #         specific_weapon_name in weapon_proficiencies or
            #         (weapon.get("id") and weapon["id"] in weapon_proficiencies) ): # Check by ID too
            #     is_proficient = False
        else: # Unarmed strike
            # Check for Monk's Martial Arts for better unarmed damage if applicable
            if self.player_class_name == "Monk" and self.level > 0: # Monk feature
                # Monk's Martial Arts die scales with level, simplified here
                if self.level < 5: damage_dice = "1d4"
                elif self.level < 11: damage_dice = "1d6"
                elif self.level < 17: damage_dice = "1d8"
                else: damage_dice = "1d10"
                # Monks can use DEX for unarmed strikes
                if self.get_stat_score("DEX") > self.get_stat_score("STR"):
                    attack_stat = "DEX"
            is_proficient = True # Always proficient with unarmed strikes

        attack_bonus_mod = self.get_stat_modifier(attack_stat)
        attack_bonus = attack_bonus_mod
        if is_proficient:
            attack_bonus += self.proficiency_bonus

        return {
            "attack_bonus": attack_bonus,
            "damage_dice": damage_dice,
            "damage_type": damage_type,
            "stat_modifier": attack_bonus_mod # Modifier from STR/DEX for damage
        }

# Ensure DIRECTIONS is defined if it's used by Player methods (it's not currently, but good practice for context)
# DIRECTIONS = {"n":"north", ...} # Copied from main.py if needed by Player logic directly
# For now, Player.use_dash will take a direction_name string.
