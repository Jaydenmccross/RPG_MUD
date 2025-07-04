import json
import math # For floor
import traceback # For detailed exception logging
import random # For death messages
from server.core.combat import roll_dice # Assuming roll_d20_with_advantage_disadvantage is in combat.py

# Globals populated by load_game_data()
CLASSES_DATA = {}
RACES_DATA = {}
ITEMS_DATA = {}
SPELLS_DATA = {}
CLASS_SPELL_LISTS_DATA = {}

CASTER_SPELL_SLOTS_PROGRESSION = {
    "full": {
        1:  [2,0,0,0,0,0,0,0,0], 2:  [3,0,0,0,0,0,0,0,0], 3:  [4,2,0,0,0,0,0,0,0], 4:  [4,3,0,0,0,0,0,0,0],
        5:  [4,3,2,0,0,0,0,0,0], 6:  [4,3,3,0,0,0,0,0,0], 7:  [4,3,3,1,0,0,0,0,0], 8:  [4,3,3,2,0,0,0,0,0],
        9:  [4,3,3,3,1,0,0,0,0], 10: [4,3,3,3,2,0,0,0,0], 11: [4,3,3,3,2,1,0,0,0], 12: [4,3,3,3,2,1,0,0,0],
        13: [4,3,3,3,2,1,1,0,0], 14: [4,3,3,3,2,1,1,0,0], 15: [4,3,3,3,2,1,1,1,0], 16: [4,3,3,3,2,1,1,1,0],
        17: [4,3,3,3,2,1,1,1,1], 18: [4,3,3,3,3,1,1,1,1], 19: [4,3,3,3,3,2,1,1,1], 20: [4,3,3,3,3,2,2,1,1]
    },
    "half": {
        1:  [0,0,0,0,0], 2:  [2,0,0,0,0], 3:  [3,0,0,0,0], 4:  [3,0,0,0,0],
        5:  [4,2,0,0,0], 6:  [4,2,0,0,0], 7:  [4,3,0,0,0], 8:  [4,3,0,0,0],
        9:  [4,3,2,0,0], 10: [4,3,2,0,0], 11: [4,3,3,0,0], 12: [4,3,3,0,0],
        13: [4,3,3,1,0], 14: [4,3,3,1,0], 15: [4,3,3,2,0], 16: [4,3,3,2,0],
        17: [4,3,3,3,1], 18: [4,3,3,3,1], 19: [4,3,3,3,2], 20: [4,3,3,3,2]
    },
    "third": {
        1: [0,0,0,0], 2: [0,0,0,0], 3: [2,0,0,0], 4: [3,0,0,0], 5: [3,0,0,0], 6: [3,0,0,0],
        7: [4,2,0,0], 8: [4,2,0,0], 9: [4,2,0,0], 10:[4,3,0,0], 11:[4,3,0,0], 12:[4,3,0,0],
        13:[4,3,2,0], 14:[4,3,2,0], 15:[4,3,2,0], 16:[4,3,3,0], 17:[4,3,3,0], 18:[4,3,3,0],
        19:[4,3,3,1], 20:[4,3,3,1]
    }
}

ANSI_BLUE = "\033[94m"; ANSI_RED = "\033[91m"; ANSI_GREEN = "\033[92m"; ANSI_YELLOW = "\033[93m"; ANSI_RESET = "\033[0m"

def load_game_data():
    global CLASSES_DATA, RACES_DATA, ITEMS_DATA, SPELLS_DATA, CLASS_SPELL_LISTS_DATA
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
    try:
        with open("server/data/spells.json", "r") as f: SPELLS_DATA = json.load(f)
    except FileNotFoundError: SPELLS_DATA = {}; print("INFO: server/data/spells.json not found.")
    except Exception as e: print(f"ERROR loading spells.json: {e}")
    try:
        with open("server/data/class_spell_lists.json", "r") as f: CLASS_SPELL_LISTS_DATA = json.load(f)
    except FileNotFoundError: CLASS_SPELL_LISTS_DATA = {}; print("INFO: server/data/class_spell_lists.json not found.")
    except Exception as e: print(f"ERROR loading class_spell_lists.json: {e}")

class Player:
    EQUIPMENT_SLOT_HEAD = "Head"; EQUIPMENT_SLOT_NECK = "Neck"; EQUIPMENT_SLOT_CHEST = "Chest"; EQUIPMENT_SLOT_BACK = "Back";
    EQUIPMENT_SLOT_SHOULDERS = "Shoulders"; EQUIPMENT_SLOT_WRISTS = "Wrists"; EQUIPMENT_SLOT_HANDS = "Hands";
    EQUIPMENT_SLOT_WEAPON_MAIN = "Weapon (Main Hand)"; EQUIPMENT_SLOT_WEAPON_OFF = "Weapon (Off Hand)";
    EQUIPMENT_SLOT_RING_1 = "Finger 1"; EQUIPMENT_SLOT_RING_2 = "Finger 2"; EQUIPMENT_SLOT_LEGS = "Legs";
    EQUIPMENT_SLOT_FEET = "Feet"; EQUIPMENT_SLOT_RELIC = "Relic"; EQUIPMENT_SLOT_LIGHT_SOURCE = "Light Source"
    ALL_EQUIPMENT_SLOTS = [
        EQUIPMENT_SLOT_HEAD, EQUIPMENT_SLOT_NECK, EQUIPMENT_SLOT_CHEST, EQUIPMENT_SLOT_BACK, EQUIPMENT_SLOT_SHOULDERS,
        EQUIPMENT_SLOT_WRISTS, EQUIPMENT_SLOT_HANDS, EQUIPMENT_SLOT_WEAPON_MAIN, EQUIPMENT_SLOT_WEAPON_OFF,
        EQUIPMENT_SLOT_RING_1, EQUIPMENT_SLOT_RING_2, EQUIPMENT_SLOT_LEGS, EQUIPMENT_SLOT_FEET, EQUIPMENT_SLOT_RELIC,
        EQUIPMENT_SLOT_LIGHT_SOURCE
    ]
    ALL_SKILLS = [
        "Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception", "History", "Insight", "Intimidation",
        "Investigation", "Medicine", "Nature", "Perception", "Performance", "Persuasion", "Religion",
        "Sleight of Hand", "Stealth", "Survival"
    ]
    SKILL_TO_ABILITY_MAP = {
        "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT", "Athletics": "STR", "Deception": "CHA",
        "History": "INT", "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT", "Medicine": "WIS",
        "Nature": "INT", "Perception": "WIS", "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT",
        "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS"
    }
    CONDITION_BLINDED = "Blinded"; CONDITION_CHARMED = "Charmed"; CONDITION_DEAFENED = "Deafened";
    CONDITION_FRIGHTENED = "Frightened"; CONDITION_GRAPPLED = "Grappled"; CONDITION_INCAPACITATED = "Incapacitated";
    CONDITION_INVISIBLE = "Invisible"; CONDITION_PARALYZED = "Paralyzed"; CONDITION_PETRIFIED = "Petrified";
    CONDITION_POISONED = "Poisoned"; CONDITION_PRONE = "Prone"; CONDITION_RESTRAINED = "Restrained";
    CONDITION_STUNNED = "Stunned"; CONDITION_UNCONSCIOUS = "Unconscious"; CONDITION_EXHAUSTION = "Exhaustion";
    CONDITION_HIDDEN = "Hidden";
    ALL_CONDITIONS = [
        CONDITION_BLINDED, CONDITION_CHARMED, CONDITION_DEAFENED, CONDITION_FRIGHTENED, CONDITION_GRAPPLED,
        CONDITION_INCAPACITATED, CONDITION_INVISIBLE, CONDITION_PARALYZED, CONDITION_PETRIFIED, CONDITION_POISONED,
        CONDITION_PRONE, CONDITION_RESTRAINED, CONDITION_STUNNED, CONDITION_UNCONSCIOUS, CONDITION_EXHAUSTION, CONDITION_HIDDEN
    ]

    def __init__(self, user, player_class_name="Fighter", race_name="Human", name="Adventurer", base_stats=None):
        self.user = user; self.name = name; self.player_class_name = player_class_name
        self.race_name = race_name
        self.level = 1; self.xp = 0; self.next_level_xp = 300
        self.base_stats = base_stats.copy() if base_stats else {"STR":10,"DEX":10,"CON":10,"INT":10,"WIS":10,"CHA":10}
        self.current_hp = 0; self.max_hp = 0; self.temporary_hp = 0
        self.spellcasting_ability = None; self.known_spells = set(); self.prepared_spells = set()
        self.current_spell_slots = {}; self.max_spell_slots = {}
        self.concentration = {"spell_id": None, "target_ids": [], "remaining_rounds": 0}
        self.weapon_proficiencies = set(); self.armor_proficiencies = set(); self.tool_proficiencies = set()
        self.languages = set(); self.saving_throw_proficiencies = set()
        self.base_speed = 30
        self.equipment = {slot: None for slot in Player.ALL_EQUIPMENT_SLOTS}; self.inventory = []
        self.room_id = "start"; self.skill_proficiencies = set()
        self.used_abilities_this_rest = {}
        self.active_effects = {}
        self.has_taken_action_this_turn = False; self.has_taken_bonus_action_this_turn = False; self.has_taken_reaction_this_turn = False

        # Attributes managed by the effects system
        self.extra_attacks = 0; self.crit_range = [20]; self.bonus_hp_per_level = 0
        self.static_ac_bonus = 0; self.conditional_ac_bonuses = []
        self.roll_bonuses = {"attack": [], "damage": [], "skill_check": [], "saving_throw": [], "ability_check": []}
        self.reroll_rules = []; self.action_granted_abilities = {}; self.passive_granted_abilities = {}
        self.has_darkvision = False; self.darkvision_range = 0
        self.advantage_rules = []; self.disadvantage_rules = []
        self.resistances = {}; self.immunities = {}; self.vulnerabilities = {}
        self.condition_immunities = set()
        self.pending_proficiency_choices = []; self.conditional_expertise_rules = []
        self.pending_spell_choices = []; self.pending_feat_choices = []; self.pending_feature_choices = []
        self.triggered_abilities_effects = []; self.on_critical_hit_effects = []
        self.triggered_room_flags = set(); self.stat_maximums = {}
        self.speed_bonuses = []
        self.active_restrictions = [] # For things like "cannot cast spells while raging"

        # Barbarian specific states
        self.is_raging = False
        self.unarmored_defense_ac_formula = None
        self.unarmored_defense_allows_shield = False
        # For Reckless Attack toggle
        self.is_reckless_attacking_this_turn = False
        self.reckless_attack_active_until_next_turn = False
        self._relentless_rage_successes_since_rest = 0 # For Relentless Rage DC scaling

        # Bard specific
        self.has_jack_of_all_trades = False
        self.song_of_rest_die = None
        self.pending_expertise_choices = []
        self.expertise_skills = set()

        # Cleric specific
        self.domain_spells = set() # Spells always prepared due to domain


        self.in_combat = False; self.target = None; self.is_dead = False; self.is_reloading = False
        self.conditions = {}; self.hit_dice = {}; self.max_hit_dice = {}
        self.fighting_styles = set(); self.subclass_name = None

        try:
            if not (CLASSES_DATA and RACES_DATA): load_game_data()
            class_data = CLASSES_DATA.get(self.player_class_name)
            if class_data:
                self.spellcasting_ability = class_data.get("spellcasting_ability")
                hd_type = f"d{class_data.get('hit_die', 6)}"
                self.hit_dice[hd_type] = self.level; self.max_hit_dice[hd_type] = self.level
                if class_data.get("known_cantrips"):
                    for cantrip_info in class_data["known_cantrips"]:
                        spell_name = cantrip_info.get("name")
                        if spell_name: self.known_spells.add(spell_name.lower().replace(" ", "_"))
            base_race_data, sub_race_data = self._get_race_data_parts()
            if base_race_data:
                self.base_speed = base_race_data.get("speed", 30)
                for lang in base_race_data.get("languages", []):
                    if "one extra of your choice" not in lang: self.languages.add(lang)
                    else: self.languages.add("Common");
            if sub_race_data:
                 self.base_speed = sub_race_data.get("speed", self.base_speed)
                 for lang in sub_race_data.get("languages", []):
                     if "one extra of your choice" not in lang: self.languages.add(lang)
            self.recalculate_all_stats(full_heal=True)
        except Exception as e:
            print(f"!!! CRITICAL ERROR in Player.__init__ for {self.name} !!!"); print(traceback.format_exc())

    def _get_race_data_parts(self):
        if not RACES_DATA: return None, None
        for r_name, r_info in RACES_DATA.items():
            if r_name == self.race_name: return r_info, None
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
            if item_data:
                score += item_data.get("effects", {}).get("bonus_stats", {}).get(stat_name_upper, 0)
        max_score = self.stat_maximums.get(stat_name_upper, 50)
        return min(score, max_score)

    def get_stat_modifier(self, stat_name):
        return math.floor((self.get_stat_score(stat_name) - 10) / 2)

    def get_skill_bonus(self, skill_name):
        if skill_name not in Player.SKILL_TO_ABILITY_MAP: return 0
        ability_stat = Player.SKILL_TO_ABILITY_MAP[skill_name]
        modifier = self.get_stat_modifier(ability_stat)

        is_proficient_base = skill_name in self.skill_proficiencies
        prof_bonus_multiplier = 1

        if skill_name in self.expertise_skills: # Check general expertise first
            prof_bonus_multiplier = 2
            is_proficient_base = True # Expertise implies proficiency
        else: # Check conditional expertise if not generally expert
            for rule in self.conditional_expertise_rules:
                if rule.get("skill") == skill_name:
                    # TODO: Add condition check for conditional expertise if rule.get("condition_applies_func")
                    prof_bonus_multiplier = 2; is_proficient_base = True; break

        prof_bonus_value = self.proficiency_bonus if is_proficient_base else 0
        total_bonus = modifier + (prof_bonus_value * prof_bonus_multiplier)

        remarkable_athlete_data = self.passive_granted_abilities.get("Remarkable Athlete")
        if remarkable_athlete_data and prof_bonus_multiplier == 1 and not is_proficient_base and ability_stat in ["STR", "DEX", "CON"]:
            # Remarkable Athlete adds half prof bonus (ceil) if not already proficient.
            total_bonus += math.ceil(self.proficiency_bonus / 2)
        elif self.has_jack_of_all_trades and prof_bonus_multiplier == 1 and not is_proficient_base:
            # Jack of All Trades adds half prof bonus (floor) if not already proficient.
            # It should not stack with Remarkable Athlete if a character somehow had both.
            total_bonus += math.floor(self.proficiency_bonus / 2)


        for effect_list_key in ["skill_check", "ability_check"]:
            for effect in self.roll_bonuses.get(effect_list_key, []):
                applies = True
                if effect.get("skill") and effect.get("skill") != skill_name: applies = False
                if effect.get("ability") and effect.get("ability") != ability_stat: applies = False
                if effect.get("condition") == "while_raging" and not self.is_raging(): applies = False
                if applies: total_bonus += effect.get("value", 0)
        return total_bonus

    def _process_effect_durations(self):
        expired_effects_this_tick = []
        for effect_name, data in list(self.active_effects.items()):
            if effect_name not in self.active_effects: continue
            if "duration_rounds" in data:
                data["duration_rounds"] -= 1
                if data["duration_rounds"] <= 0:
                    if effect_name not in expired_effects_this_tick: expired_effects_this_tick.append(effect_name)
                    continue
            if effect_name == "Raging":
                end_conditions = data.get("end_conditions", [])
                if "knocked_unconscious" in end_conditions and self.has_condition(Player.CONDITION_UNCONSCIOUS):
                    if effect_name not in expired_effects_this_tick: expired_effects_this_tick.append(effect_name)
                # TODO: Implement 'did_attack_or_take_damage_last_round' flag, set by main loop/combat
                # This flag should be set to True if the Barbarian attacks a hostile creature or takes damage since their last turn.
                # It should be reset to False at the beginning of the Barbarian's turn.
                # if "turn_ends_and_no_attack_or_damage_since_last_turn" in end_conditions and \
                #    not getattr(self, 'did_attack_or_take_damage_this_round', True): # Check this flag
                #     if effect_name not in expired_effects_this_tick: expired_effects_this_tick.append(effect_name)

        for name in expired_effects_this_tick:
            if name in self.active_effects:
                self.remove_effect(name, ended_by_condition=True)
                if hasattr(self.user, "send_message"):
                    self.user.send_message(f"The effect of {name} fades from you.")


    def _on_effect_added(self, effect_name_being_added, main_effect_data):
        main_effect_data.setdefault("_transient_sub_effects_applied", [])
        sub_effects_list = main_effect_data.get("active_effects", [])
        if not sub_effects_list and "applied_effects_list" in main_effect_data:
            sub_effects_list = main_effect_data["applied_effects_list"]

        for sub_effect_def in sub_effects_list:
            sub_effect_instance = sub_effect_def.copy()
            sub_effect_instance["_source_active_effect"] = effect_name_being_added
            applied_record = {"type": sub_effect_def.get("type"), "signature": sub_effect_instance}
            effect_type = sub_effect_def.get("type")

            # Apply sub-effect based on its type
            condition_for_sub_effect = sub_effect_instance.get("condition", "always_true")
            can_apply_sub_effect = True
            if condition_for_sub_effect == "not_wearing_heavy_armor":
                equipped_chest = self.equipment.get(Player.EQUIPMENT_SLOT_CHEST)
                if equipped_chest and equipped_chest.get("properties", {}).get("armor_type") == "heavy":
                    can_apply_sub_effect = False

            if not can_apply_sub_effect: continue

            if effect_type == "ADVANTAGE":
                self.advantage_rules.append(sub_effect_instance)
                applied_record["list_name"] = "advantage_rules"
            elif effect_type == "BONUS_ROLL":
                roll_type = sub_effect_instance.get("roll_type")
                if roll_type in self.roll_bonuses:
                    self.roll_bonuses[roll_type].append(sub_effect_instance)
                    applied_record["list_name"] = f"roll_bonuses.{roll_type}"
            elif effect_type == "RESISTANCE":
                damage_type = sub_effect_instance.get("damage_type")
                if damage_type:
                    if damage_type not in self.resistances or self.resistances[damage_type] != sub_effect_instance.get("notes", True):
                        applied_record["was_new_or_overwritten"] = True
                    self.resistances[damage_type] = sub_effect_instance.get("notes", True)
                    applied_record["damage_type"] = damage_type
            elif effect_type == "RESTRICTION":
                self.active_restrictions.append(sub_effect_instance)
                applied_record["list_name"] = "active_restrictions"

            if "list_name" in applied_record or applied_record.get("was_new_or_overwritten"):
                main_effect_data["_transient_sub_effects_applied"].append(applied_record)

        if effect_name_being_added == "Raging": self.is_raging = True

    def _on_effect_removed(self, effect_name_being_removed, main_effect_data):
        transient_sub_effects = main_effect_data.get("_transient_sub_effects_applied", [])
        for eff_info in reversed(transient_sub_effects):
            list_name_full = eff_info.get("list_name")
            signature_to_remove = eff_info.get("signature")
            sub_effect_type = eff_info.get("type")
            target_list = None

            if list_name_full == "advantage_rules": target_list = self.advantage_rules
            elif list_name_full == "active_restrictions": target_list = self.active_restrictions
            elif list_name_full and list_name_full.startswith("roll_bonuses."):
                roll_type_key = list_name_full.split('.')[1]
                if roll_type_key in self.roll_bonuses: target_list = self.roll_bonuses[roll_type_key]

            if target_list is not None and signature_to_remove:
                try: target_list.remove(signature_to_remove)
                except ValueError: pass

            elif sub_effect_type == "RESISTANCE" and eff_info.get("was_new_or_overwritten"):
                damage_type = eff_info.get("damage_type")
                current_source_note = signature_to_remove.get("notes", True) if signature_to_remove else True
                if damage_type and self.resistances.get(damage_type) == current_source_note:
                    del self.resistances[damage_type]

        if "_transient_sub_effects_applied" in main_effect_data:
             main_effect_data["_transient_sub_effects_applied"] = []

        if effect_name_being_removed == "Raging": self.is_raging = False

    def add_effect(self, effect_name, effect_data):
        if effect_name in self.active_effects: self.remove_effect(effect_name)
        effect_data_to_store = effect_data.copy() if isinstance(effect_data, dict) else {}
        self.active_effects[effect_name] = effect_data_to_store
        self._on_effect_added(effect_name, effect_data_to_store)
        self.recalculate_all_stats()

    def remove_effect(self, effect_name, ended_by_condition=False): # Added ended_by_condition
        if effect_name in self.active_effects:
            effect_data_removed = self.active_effects.pop(effect_name)
            self._on_effect_removed(effect_name, effect_data_removed)
            self.recalculate_all_stats()
            if ended_by_condition and hasattr(self.user, "send_message"): # Message handled by _process_effect_durations
                pass
            return True
        return False

    def is_raging(self):
        return "Raging" in self.active_effects

    def enter_rage(self):
        if not self.can_use_ability("Rage"): return "You can't enter a rage right now (no uses left)."
        if self.is_raging(): return "You are already raging!"
        equipped_armor = self.equipment.get(Player.EQUIPMENT_SLOT_CHEST)
        if equipped_armor and equipped_armor.get("properties", {}).get("armor_type") == "heavy":
            return "You cannot rage while wearing heavy armor."
        if not self.mark_ability_used("Rage"): return "Failed to use Rage (tracking error)."

        rage_grant_data = self.action_granted_abilities.get("Rage")
        if not rage_grant_data or not rage_grant_data.get("effect_details"):
            print("ERROR: Rage GRANT_ACTION_ABILITY data not found or malformed for Player.enter_rage.")
            return "Rage ability not defined correctly for activation."

        rage_effect_details = rage_grant_data["effect_details"].copy()

        # Modify for Persistent Rage if applicable
        persistent_rage_mods = self.passive_granted_abilities.get("_modification_for_Rage", [])
        for mod in persistent_rage_mods:
            if mod.get("target_active_effect_name") == "Raging" and mod.get("remove_end_condition"):
                condition_to_remove = mod.get("remove_end_condition")
                if condition_to_remove in rage_effect_details.get("end_conditions", []):
                    rage_effect_details["end_conditions"].remove(condition_to_remove)
                    if hasattr(self.user, "send_message"):
                        self.user.send_message(f"(Persistent Rage active!)")

        self.add_effect("Raging", rage_effect_details)
        return f"{ANSI_RED}You fly into a RAGE!{ANSI_RESET}"

    def end_rage(self, manual_end=False): # removed ended_by_condition, handled by _process_effect_durations
        if not self.is_raging(): return "You are not raging." if manual_end else ""

        current_rage_effect_data = self.active_effects.get("Raging")
        if manual_end:
            if not current_rage_effect_data or not current_rage_effect_data.get("can_be_ended_by_bonus_action"):
                 return "You cannot end this rage voluntarily."

        self.remove_effect("Raging")
        msg = f"{ANSI_YELLOW}Your rage subsides.{ANSI_RESET}"
        # TODO: Handle Frenzy exhaustion
        # if current_rage_effect_data and current_rage_effect_data.get("frenzy_active"):
        #    self.add_condition(Player.CONDITION_EXHAUSTION, source="Frenzy")
        #    msg += f" {ANSI_RED}You feel a wave of exhaustion wash over you.{ANSI_RESET}"
        return msg if manual_end else "" # Only return message if manually ended

    def calculate_proficiency_bonus(self):
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
            hp_per_level_from_class = max(1, avg_roll_plus_one + con_modifier)
            max_hp_val = (hit_die + con_modifier) + (hp_per_level_from_class * (self.level - 1))
        max_hp_val += self.bonus_hp_per_level * self.level
        for item_data in self.equipment.values():
            if item_data: max_hp_val += item_data.get("effects", {}).get("bonus_hp", 0)
        return max(1, max_hp_val)

    def calculate_ac(self):
        dex_modifier = self.get_stat_modifier("DEX")
        base_ac_value_from_armor = 10 + dex_modifier
        equipped_armor_item_data = self.equipment.get(Player.EQUIPMENT_SLOT_CHEST)
        is_wearing_armor = equipped_armor_item_data is not None

        if equipped_armor_item_data:
            props = equipped_armor_item_data.get("properties", {})
            armor_type = props.get("armor_type")
            armor_base_ac = props.get("base_ac_value", 0)
            if armor_type == "light": base_ac_value_from_armor = armor_base_ac + dex_modifier
            elif armor_type == "medium": base_ac_value_from_armor = armor_base_ac + min(dex_modifier, props.get("dex_cap_bonus", 2))
            elif armor_type == "heavy": base_ac_value_from_armor = armor_base_ac

        calculated_ac = base_ac_value_from_armor

        if not is_wearing_armor and self.unarmored_defense_ac_formula:
            ac_ud = 10
            # This is a simplified parser. A real one would be more robust.
            if "DEX_mod" in self.unarmored_defense_ac_formula: ac_ud += self.get_stat_modifier("DEX")
            if "CON_mod" in self.unarmored_defense_ac_formula: ac_ud += self.get_stat_modifier("CON")
            if "WIS_mod" in self.unarmored_defense_ac_formula: ac_ud += self.get_stat_modifier("WIS")
            calculated_ac = ac_ud

        calculated_ac += self.static_ac_bonus
        for ac_bonus_effect in self.conditional_ac_bonuses:
            condition_met = False
            if ac_bonus_effect.get("condition") == "is_wearing_armor":
                condition_met = is_wearing_armor and not (not is_wearing_armor and self.unarmored_defense_ac_formula) # True only if wearing actual armor
            if condition_met:
                calculated_ac += ac_bonus_effect.get("value", 0)

        shield = self.equipment.get(Player.EQUIPMENT_SLOT_WEAPON_OFF)
        if shield and shield.get("properties", {}).get("armor_type") == "shield":
            can_use_shield_with_ud = not is_wearing_armor and self.unarmored_defense_ac_formula and self.unarmored_defense_allows_shield
            if is_wearing_armor or can_use_shield_with_ud :
                 calculated_ac += shield.get("effects", {}).get("bonus_ac", 0)
        return calculated_ac

    def get_attack_bonus(self, ability_stat_name, is_proficient_with_weapon=True, weapon_category=None):
        prof_bonus = self.proficiency_bonus if is_proficient_with_weapon else 0
        base_attack_bonus = self.get_stat_modifier(ability_stat_name) + prof_bonus
        for effect in self.roll_bonuses.get("attack", []):
            applies = True
            if "weapon_category" in effect and effect["weapon_category"] != weapon_category: applies = False
            if effect.get("condition") == "while_raging" and not self.is_raging(): applies = False
            if applies: base_attack_bonus += effect.get("value", 0)
        return base_attack_bonus

    def get_damage_bonus(self, ability_stat_name, weapon_category=None, is_one_handed_melee_no_other_weapon=False, is_two_handed_or_versatile_melee_weapon=False):
        base_damage_bonus = self.get_stat_modifier(ability_stat_name)
        for effect in self.roll_bonuses.get("damage", []):
            applies = True
            if "weapon_category" in effect and effect["weapon_category"] != weapon_category: applies = False
            if effect.get("condition") == "one_handed_melee_no_other_weapon" and not is_one_handed_melee_no_other_weapon: applies = False

            # Rage damage bonus specific check
            is_rage_damage_effect = "Rage Damage Bonus" in effect.get("notes", "")
            if is_rage_damage_effect and not self.is_raging():
                applies = False
            elif is_rage_damage_effect and self.is_raging(): # Apply scaling rage damage
                level_scale = effect.get("value_scaling_by_level", {})
                current_bonus = 0
                for lvl_thresh_str, val in level_scale.items():
                    if self.level >= int(lvl_thresh_str): current_bonus = max(current_bonus, val)
                base_damage_bonus += current_bonus
                continue # Skip generic value if scaling applied and conditions met

            if applies: base_damage_bonus += effect.get("value", 0)
        return base_damage_bonus

    def get_saving_throw_bonus(self, ability_stat_name):
        if not CLASSES_DATA: return self.get_stat_modifier(ability_stat_name)
        class_data = CLASSES_DATA.get(self.player_class_name)
        is_proficient = ability_stat_name.upper() in self.saving_throw_proficiencies or \
                        (class_data and ability_stat_name.upper() in class_data.get("saving_throw_proficiencies", []))
        prof_bonus = self.proficiency_bonus if is_proficient else 0
        base_bonus = self.get_stat_modifier(ability_stat_name) + prof_bonus
        for effect in self.roll_bonuses.get("saving_throw", []):
            applies = True
            if "ability" in effect and effect.get("ability") != ability_stat_name.upper(): applies = False
            if effect.get("condition") == "while_raging" and not self.is_raging(): applies = False
            if applies: base_bonus += effect.get("value",0)
        return base_bonus

    def get_bonus_dice_for_roll_type(self, roll_type_str):
        bonus_dice_list = []
        for effect_name, data in self.active_effects.items():
            # Check if the active effect itself directly grants bonus dice (e.g. Bless's main data structure)
            if data.get("bonus_to_" + roll_type_str + "_rolls_dice"): # Generic way
                 bonus_dice_list.append(data["bonus_to_" + roll_type_str + "_rolls_dice"])
            elif effect_name == "Bless" and data.get("effect_details"): # Specific for Bless structure
                if roll_type_str == "attack" and data["effect_details"].get("bonus_to_attack_rolls"):
                    bonus_dice_list.append(data["effect_details"]["bonus_to_attack_rolls"])
                elif roll_type_str == "save" and data["effect_details"].get("bonus_to_saving_throws"):
                     bonus_dice_list.append(data["effect_details"]["bonus_to_saving_throws"])
            # Check sub-effects if the main effect is structured to apply them (like how Rage's sub-effects are handled)
            elif "_transient_sub_effects_applied" in data:
                for sub_eff_info in data["_transient_sub_effects_applied"]:
                    sub_sig = sub_eff_info.get("signature", {})
                    if sub_sig.get("type") == "BONUS_ROLL" and sub_sig.get("roll_type") == roll_type_str and "dice" in sub_sig:
                        # TODO: Add condition checks for these sub-effects if necessary
                        bonus_dice_list.append(sub_sig["dice"])
        # Check passive roll_bonuses (less common for dice, usually flat values)
        for effect in self.roll_bonuses.get(roll_type_str, []):
            if "_source_active_effect" in effect: continue # Already handled by active_effects iteration
            if "dice" in effect:
                applies = True
                if effect.get("condition") == "while_raging" and not self.is_raging(): applies = False
                if applies: bonus_dice_list.append(effect["dice"])
        return bonus_dice_list
    # ... (rest of the file is identical to the version from the last successful read_files call)
    def get_spell_save_dc(self):
        if not self.spellcasting_ability: return 8
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data : return 8
        spell_mod = self.get_stat_modifier(self.spellcasting_ability)
        return 8 + self.proficiency_bonus + spell_mod

    def _initialize_spell_slots(self):
        self.max_spell_slots = {}
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data or not self.spellcasting_ability:
            self.current_spell_slots = {}; return

        pact_magic_data = class_data.get("pact_magic_slots_by_level")
        slot_progression_type = class_data.get("spell_slots_by_level") # For regular casters

        if pact_magic_data and isinstance(pact_magic_data, dict): # Warlock Pact Magic
            # Determine current pact slot level and count
            current_pact_slot_level = 0
            current_pact_slot_count = 0
            # Iterate through sorted character levels in pact_magic_data
            for char_lvl_str in sorted(pact_magic_data.keys(), key=int):
                if self.level >= int(char_lvl_str):
                    current_pact_slot_level = pact_magic_data[char_lvl_str].get("slot_level", 0)
                    current_pact_slot_count = pact_magic_data[char_lvl_str].get("slots", 0)
                else:
                    break # Stop if we've passed the player's current level

            if current_pact_slot_level > 0 and current_pact_slot_count > 0:
                self.max_spell_slots = {current_pact_slot_level: current_pact_slot_count}
            else: # Should not happen if data is correct, but fallback
                self.max_spell_slots = {}

        elif isinstance(slot_progression_type, str) and slot_progression_type in CASTER_SPELL_SLOTS_PROGRESSION:
            # Standard caster progression (Full, Half, Third)
            progression_table = CASTER_SPELL_SLOTS_PROGRESSION[slot_progression_type]
            level_slots_list = progression_table.get(self.level, [])
            temp_max_slots = {}
            for i, num_slots in enumerate(level_slots_list):
                if num_slots > 0: temp_max_slots[i + 1] = num_slots
            self.max_spell_slots = temp_max_slots
        elif isinstance(slot_progression_type, dict): # Direct dict for spell slots by level (less common now)
            level_slots_str_keys = slot_progression_type.get(str(self.level), [])
            temp_max_slots = {}
            if isinstance(level_slots_str_keys, list):
                 for i, num_slots in enumerate(level_slots_str_keys):
                    if num_slots > 0: temp_max_slots[i + 1] = num_slots
            self.max_spell_slots = temp_max_slots
        else: # No spellcasting or unrecognized format
            self.max_spell_slots = {}

        # Initialize current_spell_slots based on newly calculated max_spell_slots
        # This preserves existing slots if recalculating mid-session (e.g. level up)
        # and ensures they don't exceed new maximums.
        new_current_slots = {}
        for slot_lvl_key, max_c in self.max_spell_slots.items():
            # Ensure keys are integers for current_spell_slots access
            slot_lvl_int = int(slot_lvl_key)
            new_current_slots[slot_lvl_int] = self.current_spell_slots.get(slot_lvl_int, max_c)
            if new_current_slots[slot_lvl_int] > max_c:
                new_current_slots[slot_lvl_int] = max_c
        self.current_spell_slots = new_current_slots

        # Ensure all max_spell_slots levels are present in current_spell_slots, initialized to max if new
        for slot_lvl_key in self.max_spell_slots.keys():
            slot_lvl_int = int(slot_lvl_key)
            if slot_lvl_int not in self.current_spell_slots:
                 self.current_spell_slots[slot_lvl_int] = self.max_spell_slots[slot_lvl_key]


    def get_max_prepared_spells(self):
        if not self.spellcasting_ability: return 0
        class_data = CLASSES_DATA.get(self.player_class_name);
        if not class_data: return 0
        modifier = self.get_stat_modifier(self.spellcasting_ability)
        max_prepared = 0
        if self.player_class_name in ["Wizard", "Cleric", "Druid"]: max_prepared = self.level + modifier
        elif self.player_class_name in ["Paladin", "Artificer"]:
            caster_level_for_prep = math.floor(self.level / 2) if self.player_class_name in ["Paladin", "Artificer"] else self.level
            if self.player_class_name == "Artificer" and self.level == 1: caster_level_for_prep = 1
            max_prepared = caster_level_for_prep + modifier
        else: max_prepared = self.level + modifier
        return max(1, max_prepared)

    def can_prepare_spells(self):
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return False
        return self.player_class_name in ["Wizard", "Cleric", "Druid", "Paladin", "Artificer"]

    def get_available_spells_for_preparation(self):
        if not self.spellcasting_ability: return []
        available_spell_ids = set(); class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return []
        max_castable_level = 0
        for i in range(1, 10):
            if self.max_spell_slots.get(i, 0) > 0: max_castable_level = i
            else: break
        if self.player_class_name == "Wizard":
            for spell_id in self.known_spells:
                spell_data = SPELLS_DATA.get(spell_id)
                if spell_data and spell_data.get("level", 0) > 0 and spell_data.get("level", 0) <= max_castable_level:
                    available_spell_ids.add(spell_id)
            return list(available_spell_ids)
        if self.player_class_name in CLASS_SPELL_LISTS_DATA and \
           self.player_class_name in ["Cleric", "Druid", "Paladin", "Artificer"]:
            class_spell_list_ids = CLASS_SPELL_LISTS_DATA.get(self.player_class_name, [])
            for spell_id in class_spell_list_ids:
                spell_data = SPELLS_DATA.get(spell_id)
                if spell_data and spell_data.get("level", 0) > 0 and \
                   spell_data.get("level", 0) <= max_castable_level:
                    available_spell_ids.add(spell_id)
            return list(available_spell_ids)
        return []

    def prepare_spell(self, spell_id):
        if not self.can_prepare_spells(): return f"{self.player_class_name}s do not prepare spells in this manner."
        spell_data = SPELLS_DATA.get(spell_id)
        if not spell_data: return f"Spell '{spell_id}' not found."
        if spell_data.get("level", 0) == 0: return "Cantrips are known automatically and don't need to be prepared."
        if self.player_class_name == "Wizard" and spell_id not in self.known_spells:
            return f"You do not know the spell '{spell_data.get('name', spell_id)}' to prepare it."
        if len(self.prepared_spells) >= self.get_max_prepared_spells():
            return "Cannot prepare more spells. Max prepared limit reached."
        self.prepared_spells.add(spell_id)
        return f"'{spell_data.get('name', spell_id)}' prepared."

    def unprepare_spell(self, spell_id):
        if not self.can_prepare_spells(): return f"{self.player_class_name}s do not prepare spells in this manner."
        spell_data = SPELLS_DATA.get(spell_id)
        spell_name_to_show = spell_data.get("name", spell_id) if spell_data else spell_id
        if spell_id in self.prepared_spells:
            self.prepared_spells.remove(spell_id)
            return f"'{spell_name_to_show}' unprepared."
        return f"'{spell_name_to_show}' was not prepared."

    def is_spell_prepared(self, spell_id):
        spell_data = SPELLS_DATA.get(spell_id);
        if not spell_data: return False
        if spell_id in self.domain_spells: # Domain spells are always prepared
            # Check if player level is high enough for this specific domain spell
            # This check is implicitly handled by only adding them to self.domain_spells if level is sufficient.
            return True
        if spell_data.get("level", 0) == 0: return spell_id in self.known_spells # Cantrips
        if not self.can_prepare_spells(): return spell_id in self.known_spells # For classes that don't prepare (e.g. Sorcerer)
        return spell_id in self.prepared_spells

    def get_available_spells_for_preparation(self):
        if not self.spellcasting_ability: return []
        available_spell_ids = set(); class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return []

        max_castable_level = 0
        # Determine max spell level player can cast based on their slots
        # This includes pact magic slots for Warlocks correctly now.
        if self.max_spell_slots:
            # Filter out level 0 slots if any, then find max. If no slots > 0, max_castable_level remains 0.
            castable_levels = [lvl for lvl, count in self.max_spell_slots.items() if lvl > 0 and count > 0]
            if castable_levels:
                max_castable_level = max(castable_levels)

        if self.player_class_name == "Wizard":
            # Wizards prepare from their spellbook (known_spells)
            for spell_id in self.known_spells:
                spell_data = SPELLS_DATA.get(spell_id)
                # Spell must be leveled (not cantrip) and not exceed max castable level for preparation
                if spell_data and spell_data.get("level", 0) > 0 and \
                   spell_data.get("level", 0) <= max_castable_level and \
                   spell_id not in self.domain_spells: # Exclude already auto-prepared domain spells
                    available_spell_ids.add(spell_id)
            return list(available_spell_ids)

        # For Clerics, Druids, Paladins, Artificers (Prepared Casters who know their whole list)
        if self.player_class_name in CLASS_SPELL_LISTS_DATA and \
           self.player_class_name in ["Cleric", "Druid", "Paladin", "Artificer"]:
            class_spell_list_ids = CLASS_SPELL_LISTS_DATA.get(self.player_class_name, [])
            for spell_id in class_spell_list_ids:
                spell_data = SPELLS_DATA.get(spell_id)
                if spell_data and spell_data.get("level", 0) > 0 and \
                   spell_data.get("level", 0) <= max_castable_level and \
                   spell_id not in self.domain_spells: # Exclude already auto-prepared domain spells
                    available_spell_ids.add(spell_id)
            return list(available_spell_ids)

        return [] # Default for other classes or if no spells found

    def _apply_effect(self, effect_data, feature_name="Unknown Feature"):
        effect_type = effect_data.get("type")
        notes = effect_data.get("notes", "")
        if effect_type == "SET_EXTRA_ATTACKS": self.extra_attacks = max(self.extra_attacks, effect_data.get("value", 0))
        elif effect_type == "SET_CRITICAL_RANGE":
            new_crit_range = effect_data.get("range", [20])
            if new_crit_range and new_crit_range[0] < self.crit_range[0]: self.crit_range = new_crit_range
        elif effect_type == "BONUS_HP_PER_LEVEL": self.bonus_hp_per_level += effect_data.get("value", 0)
        elif effect_type == "BONUS_AC":
            if "condition" in effect_data: self.conditional_ac_bonuses.append(effect_data.copy())
            else: self.static_ac_bonus += effect_data.get("value", 0)
        elif effect_type == "BONUS_ROLL":
            roll_type = effect_data.get("roll_type")
            if roll_type in self.roll_bonuses: self.roll_bonuses[roll_type].append(effect_data.copy())
            else: print(f"Warning: Unknown roll_type '{roll_type}' in BONUROLL effect from {feature_name} ({notes})")
        elif effect_type == "REROLL_DICE" or effect_type == "REROLL_DICE_SPECIFIC":
            self.reroll_rules.append(effect_data.copy())
        elif effect_type == "GRANT_ACTION_ABILITY":
            min_level = effect_data.get("level_requirement", 0)
            if self.level >= min_level:
                ability_name = effect_data.get("name")
                if ability_name: self.action_granted_abilities[ability_name] = effect_data.copy()
                else: print(f"Warning: GRANT_ACTION_ABILITY missing name from {feature_name} ({notes})")
        elif effect_type == "ENABLE_ABILITY_MOD_OFFHAND_DAMAGE":
            self.passive_granted_abilities["two_weapon_fighting_style_active"] = True
        elif effect_type == "GRANT_REACTION_ABILITY":
             ability_name = effect_data.get("name")
             if ability_name: self.action_granted_abilities[ability_name] = effect_data.copy()
             else: print(f"Warning: GRANT_REACTION_ABILITY missing name from {feature_name} ({notes})")
        elif effect_type == "SET_DARKVISION":
            self.has_darkvision = True; self.darkvision_range = max(self.darkvision_range, effect_data.get("range", 0))
        elif effect_type == "ADVANTAGE": self.advantage_rules.append(effect_data.copy())
        elif effect_type == "DISADVANTAGE": self.disadvantage_rules.append(effect_data.copy())
        elif effect_type == "RESISTANCE":
            damage_type_key = effect_data.get("damage_type")
            ancestry_key_ref = effect_data.get("damage_type_from_ancestry")
            if ancestry_key_ref and self.draconic_ancestry_type:
                ancestry_options = RACES_DATA.get("Dragonborn", {}).get("draconic_ancestry_options", [])
                chosen_ancestry_info = next((opt for opt in ancestry_options if opt.get("choice_value") == self.draconic_ancestry_type), None)
                if chosen_ancestry_info: damage_type_key = chosen_ancestry_info.get("damage_type")
                else: print(f"Warning: Could not find ancestry details for '{self.draconic_ancestry_type}' to determine resistance type.")
            if damage_type_key: self.resistances[damage_type_key] = effect_data.get("notes", True)
            elif not ancestry_key_ref: print(f"Warning: RESISTANCE effect missing damage_type from {feature_name} ({notes})")
        elif effect_type == "IMMUNITY":
            damage_type = effect_data.get("damage_type")
            if damage_type: self.immunities[damage_type] = effect_data.get("notes", True)
        elif effect_type == "VULNERABILITY":
            damage_type = effect_data.get("damage_type")
            if damage_type: self.vulnerabilities[damage_type] = effect_data.get("notes", True)
        elif effect_type == "CONDITION_IMMUNITY":
            condition_or_list = effect_data.get("condition", effect_data.get("conditions")) # Accept "condition" or "conditions"
            if isinstance(condition_or_list, str): self.condition_immunities.add(condition_or_list)
            elif isinstance(condition_or_list, list): self.condition_immunities.update(condition_or_list)
        elif effect_type == "GRANT_PROFICIENCY":
            category = effect_data.get("category"); name = effect_data.get("name")
            if not category or not name: print(f"Warning: GRANT_PROFICIENCY missing category or name from {feature_name} ({notes})"); return
            if category == "skill": self.skill_proficiencies.add(name)
            elif category == "weapon": self.weapon_proficiencies.add(name)
            elif category == "armor": self.armor_proficiencies.add(name)
            elif category == "tool": self.tool_proficiencies.add(name)
            elif category == "saving_throw": self.saving_throw_proficiencies.add(name.upper())
            elif category == "weapon_group": self.weapon_proficiencies.add(name)
            elif category == "armor_group": self.armor_proficiencies.add(name)
            else: print(f"Warning: Unknown proficiency category '{category}' in GRANT_PROFICIENCY from {feature_name}")
        elif effect_type == "GRANT_PROFICIENCY_CHOICE": self.pending_proficiency_choices.append(effect_data.copy())
        elif effect_type == "EXPERTISE_CONDITIONAL": self.conditional_expertise_rules.append(effect_data.copy())
        elif effect_type == "GRANT_SPELL_CHOICE": self.pending_spell_choices.append(effect_data.copy())
        elif effect_type == "SET_BASE_SPEED": self.base_speed = effect_data.get("value", self.base_speed)
        elif effect_type == "CUSTOM_MECHANIC":
            custom_name = effect_data.get("name")
            if custom_name: self.passive_granted_abilities[custom_name] = effect_data.copy()
            else: print(f"Warning: CUSTOM_MECHANIC missing name from {feature_name} ({notes})")
        elif effect_type == "GRANT_FEAT_CHOICE": self.pending_feat_choices.append(effect_data.copy())
        elif effect_type == "GRANT_SPELL":
            spell_id = effect_data.get("spell_id")
            if spell_id: self.known_spells.add(spell_id)
            else: print(f"Warning: GRANT_SPELL effect missing spell_id from {feature_name} ({notes})")
        elif effect_type == "PASSIVE_ABILITY":
            ability_name = effect_data.get("name")
            if ability_name: self.passive_granted_abilities[ability_name] = effect_data.copy()
            else: print(f"Warning: PASSIVE_ABILITY missing name from {feature_name} ({notes})")
        elif effect_type == "GRANT_CHOICE": self.pending_feature_choices.append(effect_data.copy())
        elif effect_type == "TRIGGERED_ABILITY": self.triggered_abilities_effects.append(effect_data.copy())
        elif effect_type == "ADD_CRIT_DICE": self.on_critical_hit_effects.append(effect_data.copy())
        elif effect_type == "UNARMORED_DEFENSE_AC":
            self.unarmored_defense_ac_formula = effect_data.get("formula")
            self.unarmored_defense_allows_shield = effect_data.get("allows_shield", False)
            self.passive_granted_abilities["Unarmored Defense AC"] = effect_data.copy()
        elif effect_type == "RESTRICTION": pass
        elif effect_type == "GRANT_ACTION_MODIFIER_ABILITY":
             ability_name = effect_data.get("name")
             if ability_name: self.action_granted_abilities[ability_name] = effect_data.copy()
             else: print(f"Warning: GRANT_ACTION_MODIFIER_ABILITY missing name from {feature_name} ({notes})")
        elif effect_type == "BONUS_SPEED": self.speed_bonuses.append(effect_data.copy())
        elif effect_type == "MODIFY_GRANTED_ABILITY_EFFECT":
            target_ability = effect_data.get("target_ability_name")
            if target_ability:
                mod_key = f"_modification_for_{target_ability}"
                if mod_key not in self.passive_granted_abilities: self.passive_granted_abilities[mod_key] = []
                self.passive_granted_abilities[mod_key].append(effect_data.copy())
            else: print(f"Warning: MODIFY_GRANTED_ABILITY_EFFECT missing target_ability_name from {feature_name} ({notes})")
        elif effect_type == "SET_STAT_MAXIMUM":
            stat = effect_data.get("stat"); value = effect_data.get("value")
            if stat and value is not None: self.stat_maximums[stat.upper()] = value
            else: print(f"Warning: SET_STAT_MAXIMUM missing stat or value from {feature_name} ({notes})")
        elif effect_type == "ADVANTAGE_ON_SAVE_VS_VISIBLE_EFFECT": # For Danger Sense
            self.passive_granted_abilities["Danger Sense"] = effect_data.copy()
        elif effect_type == "ADVANTAGE_ON_INITIATIVE":
            self.passive_granted_abilities["Feral Instinct Initiative"] = effect_data.copy() # Stores the rule
            # Actual advantage application would be handled by an initiative rolling system.
        elif effect_type == "SET_MINIMUM_ABILITY_CHECK_RESULT_TO_SCORE": # For Indomitable Might
            self.passive_granted_abilities["Indomitable Might"] = effect_data.copy()
        elif effect_type == "JACK_OF_ALL_TRADES":
            self.has_jack_of_all_trades = True
        elif effect_type == "SONG_OF_REST":
            self.song_of_rest_die = effect_data.get("dice")
        elif effect_type == "GRANT_EXPERTISE_CHOICE":
            self.pending_expertise_choices.append(effect_data.copy())
        elif effect_type == "GRANT_SPELL_CHOICE": # Modified to handle max_level_formula
            choice_data = effect_data.copy()
            if "max_level_formula" in choice_data:
                formula = choice_data["max_level_formula"]
                # Resolve formula, e.g., "bard_max_castable_spell_level"
                # This requires knowing the class's max spell slot level at current player level
                # For simplicity, we'll calculate it here based on self.max_spell_slots
                # A more robust solution might involve a dedicated function or class data lookup.
                resolved_max_level = 0
                if self.max_spell_slots:
                    resolved_max_level = max(k for k in self.max_spell_slots.keys() if self.max_spell_slots[k] > 0)

                if formula == "bard_max_castable_spell_level": # Example, can be more generic
                     choice_data["max_level"] = resolved_max_level
                # Potentially delete max_level_formula after resolving, or keep for reference
                # del choice_data["max_level_formula"]
            self.pending_spell_choices.append(choice_data)
        else: print(f"Warning: Unknown effect type '{effect_type}' from {feature_name} ({notes}). Effect data: {effect_data}")

    def get_minimum_strength_check_result(self):
        """Checks for features like Indomitable Might."""
        if "Indomitable Might" in self.passive_granted_abilities:
            indomitable_might_data = self.passive_granted_abilities["Indomitable Might"]
            if indomitable_might_data.get("ability") == "STR":
                return self.get_stat_score("STR")
        return 0 # No minimum, or feature not applicable

    def has_advantage_on_dex_save(self, source_tags=None):
        """
        Checks if the player has advantage on a Dexterity saving throw.
        'source_tags' could be a list of strings like ["trap", "spell", "visible_source_xyz"]
        to check against feature conditions.
        """
        if not source_tags: source_tags = []

        if "Danger Sense" in self.passive_granted_abilities:
            danger_sense_data = self.passive_granted_abilities["Danger Sense"]
            # Danger Sense: advantage on Dexterity saving throws against effects that you can see,
            # such as traps and spells. To benefit from this trait, you can’t be blinded, deafened, or incapacitated.
            if not (self.has_condition(Player.CONDITION_BLINDED) or \
                    self.has_condition(Player.CONDITION_DEAFENED) or \
                    self.is_incapacitated()):
                # Assuming 'visible_source' tag will be passed for relevant effects
                if "visible_source" in source_tags or \
                   (danger_sense_data.get("applies_to_tags") and \
                    any(tag in source_tags for tag in danger_sense_data.get("applies_to_tags", []))):
                    return True

        # TODO: Check other sources of advantage on DEX saves from self.advantage_rules
        for rule in self.advantage_rules:
            if rule.get("type") == "saving_throw" and rule.get("ability") == "DEX":
                # Add more condition checks for the rule if necessary
                return True
        return False

    def recalculate_all_stats(self, full_heal=False):
        if not (CLASSES_DATA and RACES_DATA and ITEMS_DATA): load_game_data()
        self.extra_attacks = 0; self.crit_range = [20]; self.bonus_hp_per_level = 0
        self.static_ac_bonus = 0; self.conditional_ac_bonuses = []
        self.roll_bonuses = {"attack": [], "damage": [], "skill_check": [], "saving_throw": [], "ability_check": []}
        self.reroll_rules = []; self.action_granted_abilities = {}; self.passive_granted_abilities = {}
        self.fighting_styles = set(); self.has_darkvision = False; self.darkvision_range = 0
        self.advantage_rules = []; self.disadvantage_rules = []; self.resistances = {}; self.immunities = {}
        self.vulnerabilities = {}; self.condition_immunities = set()
        self.skill_proficiencies.clear(); self.weapon_proficiencies.clear()
        self.armor_proficiencies.clear(); self.tool_proficiencies.clear(); self.saving_throw_proficiencies.clear()
        self.pending_proficiency_choices = []; self.conditional_expertise_rules = []
        self.pending_spell_choices = []; self.pending_feat_choices = []; self.pending_feature_choices = []
        self.triggered_abilities_effects = []; self.on_critical_hit_effects = []
        self.stat_maximums = {}; self.speed_bonuses = []
        self.has_jack_of_all_trades = False # Reset Bard's Jack of All Trades
        self.song_of_rest_die = None # Reset Bard's Song of Rest die
        self.pending_expertise_choices = [] # Reset Bard's pending expertise choices
        self.expertise_skills = set() # Reset Bard's chosen expertise skills
        self.domain_spells = set() # Reset Cleric's domain spells

        self.unarmored_defense_ac_formula = None
        self.unarmored_defense_allows_shield = False
        self.active_restrictions = []

        class_data_for_base_profs = CLASSES_DATA.get(self.player_class_name, {})
        for prof_type, prof_list_attr in [
            ("skill_proficiencies", self.skill_proficiencies), ("armor_proficiencies", self.armor_proficiencies),
            ("weapon_proficiencies", self.weapon_proficiencies), ("tool_proficiencies", self.tool_proficiencies),
            ("saving_throw_proficiencies", self.saving_throw_proficiencies)]:
            for prof in class_data_for_base_profs.get(prof_type, []):
                prof_list_attr.add(prof.upper() if prof_type == "saving_throw_proficiencies" else prof)

        base_race_data, sub_race_data = self._get_race_data_parts()
        if base_race_data and "traits" in base_race_data:
            for trait in base_race_data["traits"]:
                if "effects" in trait and isinstance(trait["effects"], list):
                    for effect_data in trait["effects"]: self._apply_effect(effect_data, feature_name=trait.get("name", "Unknown Racial Trait"))
        if sub_race_data and "traits" in sub_race_data:
            for trait in sub_race_data["traits"]:
                if "effects" in trait and isinstance(trait["effects"], list):
                    for effect_data in trait["effects"]: self._apply_effect(effect_data, feature_name=trait.get("name", "Unknown Subrace Trait"))

        class_data = CLASSES_DATA.get(self.player_class_name)
        if class_data:
            all_features_to_apply = []
            for level_int in range(1, self.level + 1):
                level_str = str(level_int)
                features_at_level = class_data.get("features_by_level", {}).get(level_str, [])
                all_features_to_apply.extend(features_at_level)
                if self.subclass_name and "subclasses" in class_data and self.subclass_name in class_data["subclasses"]:
                    subclass_features = class_data["subclasses"][self.subclass_name].get("features_by_level", {}).get(level_str, [])
                    all_features_to_apply.extend(subclass_features)
            for feature_data in all_features_to_apply:
                feature_name = feature_data.get("name", "Unknown Feature")
                if feature_data.get("choices_feature_type") == "fighting_style":
                    chosen_style_name = getattr(self, 'chosen_fighting_style', None)
                    if chosen_style_name:
                        for choice in feature_data.get("available_choices", []):
                            if choice.get("name") == chosen_style_name:
                                self.fighting_styles.add(chosen_style_name)
                                if "effects" in choice and isinstance(choice["effects"], list):
                                    for effect_data in choice["effects"]: self._apply_effect(effect_data, feature_name=f"{feature_name}: {chosen_style_name}")
                                break
                if "effects" in feature_data and isinstance(feature_data["effects"], list):
                    for effect_data in feature_data["effects"]: self._apply_effect(effect_data, feature_name=feature_name)

        self.proficiency_bonus = self.calculate_proficiency_bonus()
        old_max_hp = self.max_hp; self.max_hp = self.calculate_max_hp()
        if full_heal or self.current_hp <= 0: self.current_hp = self.max_hp
        else:
            hp_increase = self.max_hp - old_max_hp
            self.current_hp = min(self.max_hp, self.current_hp + hp_increase)
            if self.current_hp <= 0 and self.max_hp > 0: self.current_hp = 1
        self.ac = self.calculate_ac()
        self._initialize_spell_slots() # This needs to run before we determine domain spells if max_learnable based on slots

        # Populate Domain Spells for Clerics (and potentially other classes with similar mechanics)
        if class_data and self.subclass_name:
            subclass_data = class_data.get("subclasses", {}).get(self.subclass_name, {})
            if "domain_spells" in subclass_data:
                domain_spells_by_level = subclass_data["domain_spells"]
                for level_key, spell_ids in domain_spells_by_level.items():
                    if self.level >= int(level_key):
                        for spell_id in spell_ids:
                            self.domain_spells.add(spell_id)
                            # Also add to known_spells if they are not automatically known through other means
                            # For clerics, domain spells are 'always prepared' and thus 'known'.
                            self.known_spells.add(spell_id)


    def add_xp(self, amount): # ... (rest of file)
        self.xp += amount
        if self.xp >= self.next_level_xp: self.level_up()

    def level_up(self):
        old_level = self.level; self.level += 1
        self.next_level_xp = self.next_level_xp * 2
        class_data = CLASSES_DATA.get(self.player_class_name)
        if class_data:
            hd_type = f"d{class_data.get('hit_die', 6)}"
            new_dice_to_add = self.level - old_level
            self.hit_dice[hd_type] = self.hit_dice.get(hd_type, 0) + new_dice_to_add
            self.max_hit_dice[hd_type] = self.level
            self.hit_dice[hd_type] = min(self.hit_dice[hd_type], self.max_hit_dice[hd_type])

        # Handle Wizards learning spells on level up
        if class_data and self.player_class_name == "Wizard":
            spells_to_learn_count = class_data.get("spells_learned_on_level_up")
            if isinstance(spells_to_learn_count, int) and spells_to_learn_count > 0:
                # Max spell level they can learn is based on their new level's spell slots
                max_learnable_spell_level = 0
                # Temporarily calculate new max slots for the new level to determine learnable spell level
                # This is a bit of a look-ahead; recalculate_all_stats will solidify this.
                temp_max_slots = {}
                slot_prog_type = class_data.get("spell_slots_by_level")
                if isinstance(slot_prog_type, str) and slot_prog_type in CASTER_SPELL_SLOTS_PROGRESSION:
                    prog_table = CASTER_SPELL_SLOTS_PROGRESSION[slot_prog_type]
                    lvl_slots_list = prog_table.get(self.level, []) # Use new level
                    for i, num_s in enumerate(lvl_slots_list):
                        if num_s > 0: temp_max_slots[i+1] = num_s

                for i in range(1,10): # Check up to 9th level spells
                    if temp_max_slots.get(i,0) > 0 : max_learnable_spell_level = i
                    else: break

                if max_learnable_spell_level > 0:
                    choice_effect = {
                        "type": "GRANT_SPELL_CHOICE",
                        "count": spells_to_learn_count,
                        "max_level": max_learnable_spell_level,
                        "from_class_list": "Wizard",
                        "notes": f"Spells learned at level {self.level}"
                    }
                    self.pending_spell_choices.append(choice_effect)
                    if hasattr(self.user, 'send_message'):
                        self.user.send_message(f"{ANSI_YELLOW}You can learn {spells_to_learn_count} new wizard spell(s) of level {max_learnable_spell_level} or lower.{ANSI_RESET}")
                        self.user.send_message(f"{ANSI_YELLOW}Use the 'learnspell' command to make your selections.{ANSI_RESET}")
                        # Placeholder for actual command name

        # Handle Known Casters (Sorcerer, Bard, etc.) learning spells on level up
        elif class_data and "spells_known_by_level" in class_data:
            spells_known_table = class_data["spells_known_by_level"]
            spells_known_now = spells_known_table.get(str(self.level), 0)
            spells_known_before = spells_known_table.get(str(self.level - 1), 0)
            new_spells_to_choose = spells_known_now - spells_known_before

            if new_spells_to_choose > 0:
                max_learnable_spell_level = 0
                temp_max_slots = {}
                slot_prog_type = class_data.get("spell_slots_by_level")
                pact_magic_table = class_data.get("pact_magic_slots_by_level")

                if pact_magic_table: # Warlock logic
                    for char_lvl_str in sorted(pact_magic_table.keys(), key=int):
                        if self.level >= int(char_lvl_str):
                            max_learnable_spell_level = pact_magic_table[char_lvl_str].get("slot_level",0)
                elif isinstance(slot_prog_type, str) and slot_prog_type in CASTER_SPELL_SLOTS_PROGRESSION:
                    prog_table = CASTER_SPELL_SLOTS_PROGRESSION[slot_prog_type]
                    lvl_slots_list = prog_table.get(self.level, []) # Use new level
                    for i, num_s in enumerate(lvl_slots_list):
                        if num_s > 0: temp_max_slots[i+1] = num_s
                    for i in range(1,10):
                        if temp_max_slots.get(i,0) > 0 : max_learnable_spell_level = i
                        else: break

                if max_learnable_spell_level > 0:
                    choice_effect = {
                        "type": "GRANT_SPELL_CHOICE",
                        "count": new_spells_to_choose,
                        "max_level": max_learnable_spell_level,
                        "from_class_list": self.player_class_name, # Use current class name
                        "notes": f"Spells chosen at level {self.level} for {self.player_class_name}"
                    }
                    self.pending_spell_choices.append(choice_effect)
                    if hasattr(self.user, 'send_message'):
                        self.user.send_message(f"{ANSI_YELLOW}You can choose {new_spells_to_choose} new {self.player_class_name.lower()} spell(s) of level {max_learnable_spell_level} or lower.{ANSI_RESET}")
                        self.user.send_message(f"{ANSI_YELLOW}Use a 'choosespell' or similar command to make your selections.{ANSI_RESET}")


        self.recalculate_all_stats(full_heal=True)
        if hasattr(self.user, 'send_message'):
             self.user.send_message(f"{ANSI_GREEN}Ding! You reached level {self.level}!{ANSI_RESET}")

    def get_class_feature(self, feature_name):
        if not CLASSES_DATA: load_game_data()
        if feature_name in self.action_granted_abilities:
            granted_ability_data = self.action_granted_abilities[feature_name].copy()
            granted_ability_data.setdefault("name", feature_name)
            granted_ability_data["source_type"] = "action_granted_ability"
            return granted_ability_data
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return None
        best_raw_feature_match = None
        for level_int in range(1, self.level + 1):
            level_str = str(level_int)
            features_at_level = class_data.get("features_by_level", {}).get(level_str, [])
            for raw_feature_data_item in features_at_level:
                is_direct_match = raw_feature_data_item.get("name") == feature_name
                is_override_match = raw_feature_data_item.get("override_feature_name") == feature_name
                if is_direct_match or is_override_match:
                    if best_raw_feature_match is None or is_override_match or \
                       (is_direct_match and not best_raw_feature_match.get("override_feature_name")) or \
                       level_int > best_raw_feature_match.get("granted_at_level", 0):
                        temp_copy = raw_feature_data_item.copy()
                        temp_copy["granted_at_level"] = level_int
                        if is_override_match: temp_copy["original_name_for_tracking"] = feature_name
                        best_raw_feature_match = temp_copy
        if self.subclass_name and class_data and "subclasses" in class_data and \
           self.subclass_name in class_data["subclasses"]:
            subclass_data_raw = class_data["subclasses"][self.subclass_name]
            if "features_by_level" in subclass_data_raw:
                for level_int in range(1, self.level + 1):
                    level_str = str(level_int)
                    sub_features_at_level_raw = subclass_data_raw["features_by_level"].get(level_str, [])
                    for sub_feature_item_raw in sub_features_at_level_raw:
                        is_direct_match = sub_feature_item_raw.get("name") == feature_name
                        is_override_match = sub_feature_item_raw.get("override_feature_name") == feature_name
                        if is_direct_match or is_override_match:
                            if best_raw_feature_match is None or is_override_match or \
                               (is_direct_match and not best_raw_feature_match.get("override_feature_name")) or \
                               level_int > best_raw_feature_match.get("granted_at_level", 0):
                                temp_copy = sub_feature_item_raw.copy()
                                temp_copy["granted_at_level"] = level_int
                                if is_override_match: temp_copy["original_name_for_tracking"] = feature_name
                                best_raw_feature_match = temp_copy
        if best_raw_feature_match:
             best_raw_feature_match["source_type"] = "raw_class_json"
        return best_raw_feature_match

    def can_use_ability(self, ability_name):
        feature_data = self.get_class_feature(ability_name)
        if not feature_data: return False

        max_uses = feature_data.get("uses")
        uses_based_on_stat = feature_data.get("uses_based_on_stat")
        minimum_uses = feature_data.get("minimum_uses", 0)

        if uses_based_on_stat:
            stat_mod = self.get_stat_modifier(uses_based_on_stat)
            max_uses = max(minimum_uses, stat_mod)
        elif "uses_by_level" in feature_data and isinstance(feature_data["uses_by_level"], dict):
            current_max_uses_by_level = 0
            for lvl_thresh_str, num_uses in feature_data["uses_by_level"].items():
                if self.level >= int(lvl_thresh_str): current_max_uses_by_level = max(current_max_uses_by_level, num_uses)
            max_uses = current_max_uses_by_level

        refresh_on = feature_data.get("refresh_on")
        if max_uses is None or refresh_on is None: return True # Passive or always available

        resource_to_use = feature_data.get("uses_resource")
        name_to_track_for_uses = resource_to_use if resource_to_use else feature_data.get("original_name_for_tracking", ability_name)

        # If it uses a shared resource, get the definition of that resource for its max uses
        if resource_to_use:
            resource_feature_data = self.get_class_feature(resource_to_use)
            if not resource_feature_data:
                print(f"Warning: Resource '{resource_to_use}' for ability '{ability_name}' not found.")
                return False # Cannot determine max uses
            max_uses = resource_feature_data.get("uses") # Assuming shared resource has its own 'uses' defined
            if "uses_by_level" in resource_feature_data: # Handle scaling uses for the resource itself
                 current_max_for_resource = 0
                 for r_lvl_str, r_num_uses in resource_feature_data["uses_by_level"].items():
                     if self.level >= int(r_lvl_str): current_max_for_resource = max(current_max_for_resource, r_num_uses)
                 max_uses = current_max_for_resource
            # Add uses_based_on_stat for the resource if applicable
            res_uses_stat = resource_feature_data.get("uses_based_on_stat")
            res_min_uses = resource_feature_data.get("minimum_uses", 0)
            if res_uses_stat:
                res_stat_mod = self.get_stat_modifier(res_uses_stat)
                max_uses = max(res_min_uses, res_stat_mod)

        current_spent_uses = self.used_abilities_this_rest.get(name_to_track_for_uses, 0)
        return current_spent_uses < max_uses

    def mark_ability_used(self, ability_name):
        feature_data = self.get_class_feature(ability_name)
        if not feature_data: return False

        max_uses = feature_data.get("uses")
        uses_based_on_stat = feature_data.get("uses_based_on_stat")
        minimum_uses = feature_data.get("minimum_uses", 0)
        resource_to_use = feature_data.get("uses_resource")
        name_to_track_for_uses = resource_to_use if resource_to_use else feature_data.get("original_name_for_tracking", ability_name)

        if resource_to_use:
            resource_feature_data = self.get_class_feature(resource_to_use)
            if not resource_feature_data:
                print(f"Warning: Resource '{resource_to_use}' for ability '{ability_name}' not found during mark_ability_used.")
                return False
            max_uses = resource_feature_data.get("uses")
            if "uses_by_level" in resource_feature_data:
                 current_max_for_resource = 0
                 for r_lvl_str, r_num_uses in resource_feature_data["uses_by_level"].items():
                     if self.level >= int(r_lvl_str): current_max_for_resource = max(current_max_for_resource, r_num_uses)
                 max_uses = current_max_for_resource
            res_uses_stat = resource_feature_data.get("uses_based_on_stat")
            res_min_uses = resource_feature_data.get("minimum_uses", 0)
            if res_uses_stat:
                res_stat_mod = self.get_stat_modifier(res_uses_stat)
                max_uses = max(res_min_uses, res_stat_mod)
        elif uses_based_on_stat: # If not using a shared resource, but uses its own stat-based count
            stat_mod = self.get_stat_modifier(uses_based_on_stat)
            max_uses = max(minimum_uses, stat_mod)
        elif "uses_by_level" in feature_data and isinstance(feature_data["uses_by_level"], dict): # Own scaling uses
            current_max_uses_by_level = 0
            for lvl_thresh_str, num_uses in feature_data["uses_by_level"].items():
                if self.level >= int(lvl_thresh_str): current_max_uses_by_level = max(current_max_uses_by_level, num_uses)
            max_uses = current_max_uses_by_level

        refresh_on = feature_data.get("refresh_on")
        # If it uses a shared resource, its refresh is governed by the resource's refresh_on.
        # If it has its own uses, its own refresh_on applies.
        # If it's passive/at-will (max_uses is None), it can't be "marked used" in this way.
        if max_uses is None or (not resource_to_use and refresh_on is None) : return False

        current_spent_uses = self.used_abilities_this_rest.get(name_to_track_for_uses, 0)
        if current_spent_uses < max_uses:
            self.used_abilities_this_rest[name_to_track_for_uses] = current_spent_uses + 1
            return True
        return False

    def regain_ability_use(self, ability_name_to_regain, count=1):
        """Regains a specified number of uses for an ability, up to its maximum."""
        feature_data = self.get_class_feature(ability_name_to_regain)
        if not feature_data:
            print(f"Warning: Cannot regain use for unknown ability '{ability_name_to_regain}'.")
            return False

        tracked_name = feature_data.get("original_name_for_tracking", ability_name_to_regain)
        current_uses = self.used_abilities_this_rest.get(tracked_name, 0)

        new_uses = max(0, current_uses - count) # Regaining a use means decrementing the "used" count

        if new_uses < current_uses: # Check if any uses were actually regained
            self.used_abilities_this_rest[tracked_name] = new_uses
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"{ANSI_GREEN}You regained {count} use(s) of {tracked_name}!{ANSI_RESET}")
            return True
        # No message if no uses were actually regained (e.g., already at 0 used)
        return False

    def reset_ability_uses_on_rest(self, rest_type="long"):
        abilities_to_clear_from_dict = []
        for ability_name_tracked, times_used in self.used_abilities_this_rest.items():
            feature_data = self.get_class_feature(ability_name_tracked)
            if feature_data:
                refresh_condition = feature_data.get("refresh_on")
                if refresh_condition == "short_or_long_rest" or \
                   (refresh_condition == "long_rest" and rest_type == "long") or \
                   (refresh_condition == "short_rest" and rest_type == "short"): # Added short rest specific
                    abilities_to_clear_from_dict.append(ability_name_tracked)
            else: abilities_to_clear_from_dict.append(ability_name_tracked) # Untracked abilities are also cleared
        for ab_name in abilities_to_clear_from_dict:
            if ab_name in self.used_abilities_this_rest:
                del self.used_abilities_this_rest[ab_name]

    def perform_long_rest(self):
        self.current_hp = self.max_hp; self.temporary_hp = 0
        self.reset_ability_uses_on_rest(rest_type="long")
        for hd_type, max_dice in self.max_hit_dice.items():
            dice_to_regain = math.ceil(max_dice / 2)
            self.hit_dice[hd_type] = min(max_dice, self.hit_dice.get(hd_type, 0) + dice_to_regain)
        self._restore_all_spell_slots()
        self._relentless_rage_successes_since_rest = 0 # Reset Relentless Rage DC
        if hasattr(self.user, 'send_message'):
            self.user.send_message(f"{ANSI_GREEN}You feel fully rested and revitalized. Hit dice and spell slots have been restored. Relentless Rage DC reset.{ANSI_RESET}")
        return "You feel fully rested and revitalized."

    def _restore_all_spell_slots(self):
        # This method should work for all casters, including Warlocks,
        # as _initialize_spell_slots now correctly sets self.max_spell_slots
        # for both standard and pact magic.
        for level_val, max_count in self.max_spell_slots.items():
            self.current_spell_slots[int(level_val)] = max_count # Ensure level_val is int for dictionary key consistency

    def spend_spell_slot(self, spell_level_to_spend):
        if spell_level_to_spend == 0: return True
        if self.current_spell_slots.get(spell_level_to_spend, 0) > 0:
            self.current_spell_slots[spell_level_to_spend] -= 1
            return True
        return False

    def perform_short_rest(self, dice_to_spend_list=None):
        if not dice_to_spend_list: dice_to_spend_list = []
        healed_amount = 0; con_modifier = self.get_stat_modifier("CON")
        hit_dice_spent_this_rest = False
        messages = ["You take a short rest."]

        for die_str_to_spend in dice_to_spend_list:
            if self.hit_dice.get(die_str_to_spend, 0) > 0:
                hit_dice_spent_this_rest = True
                self.hit_dice[die_str_to_spend] -= 1
                roll_result = roll_dice(f"1{die_str_to_spend}")
                heal = max(0, roll_result + con_modifier)
                self.current_hp = min(self.max_hp, self.current_hp + heal); healed_amount += heal
                messages.append(f"Spent 1{die_str_to_spend}, recovered {heal} HP (rolled {roll_result} + {con_modifier} CON).")
            else: messages.append(f"Cannot spend 1{die_str_to_spend}, none available.")

        # Song of Rest
        if hit_dice_spent_this_rest and self.song_of_rest_die:
            song_of_rest_heal = roll_dice(self.song_of_rest_die)
            self.current_hp = min(self.max_hp, self.current_hp + song_of_rest_heal)
            healed_amount += song_of_rest_heal
            messages.append(f"{ANSI_GREEN}Your Song of Rest soothes your wounds, restoring an extra {song_of_rest_heal} HP!{ANSI_RESET}")

        self.reset_ability_uses_on_rest(rest_type="short")
        self._relentless_rage_successes_since_rest = 0 # Reset Relentless Rage DC

        # Warlock Pact Magic slot recovery on short rest
        class_data = CLASSES_DATA.get(self.player_class_name)
        if class_data and class_data.get("pact_magic_slots_by_level"):
            self._restore_all_spell_slots() # Warlocks get all pact slots back
            messages.append(f"{ANSI_GREEN}Your Pact Magic spell slots are restored!{ANSI_RESET}")

        if healed_amount > 0: messages.append(f"Total HP recovered: {healed_amount}. Current HP: {self.current_hp}/{self.max_hp}.")
        else: messages.append("No hit dice spent for healing.")
        messages.append("Relentless Rage DC reset.") # This message might be redundant if no healing happened but DC still resets.
        if hasattr(self.user, 'send_message'): self.user.send_message("\n".join(messages))
        return "\n".join(messages)

    def reset_turn_actions(self):
        self.has_taken_action_this_turn = False
        self.has_taken_bonus_action_this_turn = False
        self.has_taken_reaction_this_turn = False
        self.has_action_surge_active = False
        self.is_reckless_attacking_this_turn = False # Player decides this at the start of their attack on their turn

        # If Reckless Attack was used last turn, the "advantage against player" effect ends now.
        if self.reckless_attack_active_until_next_turn:
            self.reckless_attack_active_until_next_turn = False
            # Potentially remove a temporary "vulnerability" or "easier_to_hit" marker if we implement it that way
            # For now, combat.py will just check this flag directly.
            if hasattr(self.user, "send_message"): # Check if user object exists and has send_message
                self.send_message("The openings from your reckless assault fade.")


    def add_condition(self, condition_name, duration_rounds=None, source=None, save_dc=None, save_ends=False, save_stat=None):
        if condition_name in self.condition_immunities:
            if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_GREEN}You are immune to the {condition_name} condition!{ANSI_RESET}")
            return False
        if condition_name not in Player.ALL_CONDITIONS:
            print(f"Warning: Unknown condition '{condition_name}' cannot be added to {self.name}."); return False
        condition_details = {"source": source, "duration_rounds": duration_rounds}
        if save_ends:
            condition_details["save_dc"] = save_dc; condition_details["save_stat"] = save_stat; condition_details["save_ends"] = True
        self.conditions[condition_name] = condition_details
        if condition_name == Player.CONDITION_PRONE: pass
        elif condition_name == Player.CONDITION_UNCONSCIOUS or condition_name == Player.CONDITION_PETRIFIED:
            self.conditions[Player.CONDITION_PRONE] = {"source": condition_name, "duration_rounds": None}
            self.target = None; self.in_combat = False
        if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_YELLOW}You are now affected by {condition_name}.{ANSI_RESET}")
        print(f"[CONDITION] {self.name} is now {condition_name}."); return True

    def remove_condition(self, condition_name):
        if condition_name in self.conditions:
            removed_condition_details = self.conditions.pop(condition_name)
            if condition_name == Player.CONDITION_PRONE and removed_condition_details.get("source") in [Player.CONDITION_UNCONSCIOUS, Player.CONDITION_PETRIFIED]:
                if self.has_condition(Player.CONDITION_UNCONSCIOUS) or self.has_condition(Player.CONDITION_PETRIFIED):
                    self.conditions[Player.CONDITION_PRONE] = removed_condition_details; return False
            if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_GREEN}You are no longer affected by {condition_name}.{ANSI_RESET}")
            print(f"[CONDITION] {self.name} is no longer {condition_name}."); return True
        return False

    def has_condition(self, condition_name): return condition_name in self.conditions
    def get_active_conditions(self): return list(self.conditions.keys())
    def is_incapacitated(self):
        return any(self.has_condition(c) for c in [Player.CONDITION_INCAPACITATED, Player.CONDITION_PARALYZED, Player.CONDITION_PETRIFIED, Player.CONDITION_STUNNED, Player.CONDITION_UNCONSCIOUS])
    def can_take_actions(self): return not self.is_incapacitated()
    def can_take_bonus_actions(self): return not self.is_incapacitated()
    def can_take_reactions(self): return not self.is_incapacitated()

    def get_effective_speed(self):
        calculated_speed = self.base_speed
        for speed_bonus_effect in self.speed_bonuses:
            condition = speed_bonus_effect.get("condition"); condition_met = True
            if condition == "not_wearing_heavy_armor":
                equipped_armor = self.equipment.get(Player.EQUIPMENT_SLOT_CHEST)
                if equipped_armor and equipped_armor.get("properties", {}).get("armor_type") == "heavy": condition_met = False
            if condition_met: calculated_speed += speed_bonus_effect.get("value", 0)
        for effect_name, effect_data in self.active_effects.items():
            if "bonus_speed" in effect_data: calculated_speed += effect_data.get("bonus_speed",0)
            if "speed_multiplier" in effect_data: calculated_speed *= effect_data.get("speed_multiplier",1)
            if "speed_reduction_flat" in effect_data: calculated_speed -= effect_data.get("speed_reduction_flat",0)
            if "speed_set_to_value" in effect_data: calculated_speed = min(calculated_speed, effect_data.get("speed_set_to_value"))
        if any(self.has_condition(c) for c in [Player.CONDITION_RESTRAINED, Player.CONDITION_GRAPPLED, Player.CONDITION_PARALYZED, Player.CONDITION_PETRIFIED, Player.CONDITION_STUNNED, Player.CONDITION_UNCONSCIOUS]):
            return 0
        return max(0, calculated_speed)

    def get_climbing_movement_multiplier(self):
        second_story_work = self.get_class_feature("Second-Story Work")
        if second_story_work and second_story_work.get("effects", {}).get("ignore_climbing_extra_movement_cost"): return 1.0
        return 2.0

    def use_indomitable(self, original_save_stat, original_dc):
        if self.player_class_name != "Fighter" or self.level < 9: return {"success": False, "message": "Ability not available."}
        if not self.can_use_ability("Indomitable"): return {"success": False, "message": "No uses left."}
        if not self.mark_ability_used("Indomitable"): return {"success": False, "message": "Error using Indomitable."}
        new_d20_roll = random.randint(1, 20); save_bonus = self.get_saving_throw_bonus(original_save_stat)
        new_total_roll = new_d20_roll + save_bonus; success = new_total_roll >= original_dc
        message = f"You use Indomitable! New {original_save_stat} save roll: {new_d20_roll} + {save_bonus} = {new_total_roll} vs DC {original_dc}. {(ANSI_GREEN + 'Success!' + ANSI_RESET) if success else (ANSI_RED + 'Still failed.' + ANSI_RESET)}"
        if hasattr(self.user, 'send_message'): self.user.send_message(message)
        return {"success": success, "new_roll_total": new_total_roll, "message": message}

    def use_action_surge(self):
        feature_name = "Action Surge"; ability_data = self.action_granted_abilities.get(feature_name)
        if not ability_data or self.player_class_name != "Fighter": return "Ability not available."
        if not self.can_use_ability(feature_name): return "Cannot use Action Surge now."
        if self.has_action_surge_active: return "Action Surge already active this turn."
        effect_details = ability_data.get("effect_details", {})
        if effect_details.get("type") != "GAIN_EXTRA_ACTION_THIS_TURN": return "Action Surge misconfigured."
        if not self.mark_ability_used(feature_name): return "Failed to mark Action Surge used."
        self.has_action_surge_active = True; self.has_taken_action_this_turn = False
        msg = f"{ANSI_GREEN}You activate Action Surge! You gain an additional action this turn.{ANSI_RESET}"
        if hasattr(self.user, 'send_message'): self.user.send_message(msg)
        return msg

    def use_second_wind(self):
        feature_name = "Second Wind"; ability_data = self.action_granted_abilities.get(feature_name)
        if not ability_data or self.player_class_name != "Fighter": return "Ability not available."
        if self.has_taken_action_this_turn and ability_data.get("action_type") == "action": return "Action already taken."
        if not self.can_use_ability(feature_name): return "Cannot use Second Wind now."
        effect_details = ability_data.get("effect_details", {});
        if effect_details.get("type") != "HEAL": return "Second Wind misconfigured for healing."
        heal_dice_str = effect_details.get("dice", "1d10"); bonus_formula = effect_details.get("bonus_formula")
        base_heal = roll_dice(heal_dice_str); added_bonus = 0
        if bonus_formula == "fighter_level": added_bonus = self.level
        total_heal_potential = base_heal + added_bonus; actual_healed_amount = 0
        if self.current_hp < self.max_hp:
            actual_healed_amount = min(total_heal_potential, self.max_hp - self.current_hp)
            self.current_hp += actual_healed_amount
        else:
            self.mark_ability_used(feature_name)
            if ability_data.get("action_type") == "action": self.has_taken_action_this_turn = True
            return "You use Second Wind, but you are already at maximum HP!"
        self.mark_ability_used(feature_name)
        if ability_data.get("action_type") == "action": self.has_taken_action_this_turn = True
        return f"You use Second Wind and regain {actual_healed_amount} HP. (Rolled {base_heal} from {heal_dice_str}, +{added_bonus} bonus = {total_heal_potential} potential)."

    def use_dash(self, direction_name, world_ref): # Simplified, Rogues get Cunning Action: Dash
        if not (self.player_class_name == "Rogue" and self.level >= 2): return {"success": False, "message": "Only Rogues of level 2+ can Dash this way."}
        # More checks needed for Cunning Action Dash specifically
        if self.has_taken_bonus_action_this_turn: return {"success": False, "message": "Bonus action already used."} # Assuming Dash is bonus action
        if not self.room: return {"success": False, "message": "Not in a valid room."}
        # Actual movement logic for double speed needs integration with movement system
        self.has_taken_bonus_action_this_turn = True; return {"success": True, "message": "You Dash, moving with incredible speed!"}


    def get_spell_details(self, spell_id_or_name):
        if not SPELLS_DATA: load_game_data()
        spell_data = SPELLS_DATA.get(spell_id_or_name)
        if spell_data: return spell_data.copy()
        for id, data in SPELLS_DATA.items():
            if data.get("name", "").lower() == spell_id_or_name.lower(): return data.copy()
        print(f"DEBUG: Spell '{spell_id_or_name}' not found in SPELLS_DATA."); return None

    def get_spell_attack_bonus(self):
        if not self.spellcasting_ability: return self.get_stat_modifier("INT") # Default if no ability
        return self.get_stat_modifier(self.spellcasting_ability) + self.proficiency_bonus

    def cast_spell_attack(self, spell_name, target_mob, combat_resolver, current_round_counter=0):
        spell_data = self.get_spell_details(spell_name)
        if not spell_data: return [f"You do not know the spell '{spell_name}'."]
        if not self.is_spell_prepared(spell_name.lower().replace(" ", "_")) and spell_data.get("level",0) > 0 :
             return [f"You do not have {spell_name} prepared."]
        if spell_data.get("level",0) == 0 and spell_name.lower().replace(" ", "_") not in self.known_spells:
             return [f"You do not know the cantrip {spell_name}."]
        if spell_data.get("attack_type") != "spell_attack_roll": return [f"'{spell_name}' is not an attack roll spell."]
        if self.has_taken_action_this_turn: return ["You have already taken an action this turn."]
        if not target_mob or not hasattr(target_mob, 'is_alive') or not target_mob.is_alive(): return ["You need a living target."]
        spell_attack_bonus = self.get_spell_attack_bonus()
        damage_dice = spell_data.get("damage_dice", "0") # Corrected from "damage"
        if spell_data.get("level",0) == 0 and spell_data.get("damage_scaling_by_character_level"):
            scaling = spell_data["damage_scaling_by_character_level"]
            for lvl_thresh in sorted(map(int, scaling.keys()), reverse=True):
                if self.level >= lvl_thresh: damage_dice = scaling[str(lvl_thresh)]; break
        damage_type = spell_data.get("damage_type", "unknown")
        attack_stat_mod_for_damage = self.get_stat_modifier(self.spellcasting_ability) if spell_data.get("add_ability_mod_to_damage") else 0
        self.has_taken_action_this_turn = True
        messages = [f"{ANSI_YELLOW}You cast {spell_name} at {target_mob.name}!{ANSI_RESET}"]
        attack_outcome_messages = combat_resolver(attacker=self, defender=target_mob, attack_bonus_override=spell_attack_bonus,
            damage_dice_override=damage_dice, damage_type_override=damage_type, attack_stat_mod_override=attack_stat_mod_for_damage)
        messages.extend(attack_outcome_messages)
        hit_success = any(("hits" in m.lower() or "critical hit" in m.lower()) and "misses" not in m.lower() and "miss" not in m.lower() for m in attack_outcome_messages)
        if hit_success and spell_data.get("effects_on_hit"):
            for effect_data_on_hit in spell_data["effects_on_hit"]:
                eff_to_apply = effect_data_on_hit.copy(); eff_to_apply["applied_round"] = current_round_counter
                if hasattr(target_mob, 'apply_status_effect'):
                    target_mob.apply_status_effect(eff_to_apply)
                    messages.append(f"{target_mob.name} is affected by {eff_to_apply.get('type')} ({eff_to_apply.get('amount')})!")
        return messages

    def cast_fire_bolt(self, target_mob, combat_resolver, current_round_counter=0):
        return self.cast_spell_attack("Fire Bolt", target_mob, combat_resolver, current_round_counter)

    def cast_ray_of_frost(self, target_mob, combat_resolver, current_round_counter=0):
        return self.cast_spell_attack("Ray of Frost", target_mob, combat_resolver, current_round_counter)

    def _handle_spell_concentration(self, spell_data):
        if self.concentration["spell_id"]:
            old_spell_data = SPELLS_DATA.get(self.concentration["spell_id"])
            old_spell_name = old_spell_data.get("name", self.concentration["spell_id"]) if old_spell_data else self.concentration["spell_id"]
            if hasattr(self.user, 'send_message'): self.user.send_message(f"Your concentration on {old_spell_name} breaks.")
            self.concentration = {"spell_id": None, "target_ids": [], "remaining_rounds": 0}
        if spell_data.get("requires_concentration"):
            duration_str = spell_data.get("duration", "0 rounds"); rounds = 0
            if "minute" in duration_str:
                try: rounds = int(duration_str.split(" minute")[0].split("up to ")[-1]) * 10
                except: rounds = 10
            elif "round" in duration_str:
                try: rounds = int(duration_str.split(" round")[0].split("up to ")[-1])
                except: rounds = 1
            self.concentration["spell_id"] = spell_data.get("id", spell_data.get("name").lower().replace(" ","_"))
            self.concentration["remaining_rounds"] = rounds
            if hasattr(self.user, 'send_message'): self.user.send_message(f"You begin concentrating on {spell_data.get('name')}.")
            return True
        return False

    def cast_spell(self, spell_id, target_mob=None, chosen_spell_level=None, combat_resolver=None, current_round_counter=0, all_mobs_in_room=None):
        if all_mobs_in_room is None: all_mobs_in_room = []
        spell_data = self.get_spell_details(spell_id)
        if not spell_data: return [f"You do not know how to cast '{spell_id}'."]
        spell_name = spell_data.get("name", spell_id); base_spell_level = spell_data.get("level", 0)

        for restriction in self.active_restrictions:
            if restriction.get("activity") == "spellcasting":
                return [f"You cannot cast spells while {restriction.get('details', 'under an effect that prevents it')}."]

        if not self.is_spell_prepared(spell_id) and base_spell_level > 0 : return [f"You do not have '{spell_name}' prepared."]
        actual_cast_level = base_spell_level
        if base_spell_level > 0 and chosen_spell_level is not None and chosen_spell_level > base_spell_level:
            actual_cast_level = chosen_spell_level

        messages = []
        if base_spell_level > 0:
            slot_spent_successfully = False
            if self.spend_spell_slot(actual_cast_level): slot_spent_successfully = True
            else:
                if chosen_spell_level is None or chosen_spell_level == base_spell_level:
                    for higher_slot_level in range(base_spell_level + 1, 10):
                        if self.spend_spell_slot(higher_slot_level):
                            actual_cast_level = higher_slot_level; slot_spent_successfully = True
                            messages.append(f"(No L{base_spell_level} slots, automatically cast at L{actual_cast_level})")
                            break
            if not slot_spent_successfully: return [f"Not enough spell slots for '{spell_name}' (tried L{chosen_spell_level if chosen_spell_level else base_spell_level})."]

        casting_time = spell_data.get("casting_time", "1 action").lower()
        if "1 action" in casting_time:
            if self.has_taken_action_this_turn and not self.has_action_surge_active: return ["Action already taken."]
            self.has_taken_action_this_turn = True
        elif "1 bonus action" in casting_time:
            if self.has_taken_bonus_action_this_turn: return ["Bonus action already taken."]
            self.has_taken_bonus_action_this_turn = True
        elif "reaction" in casting_time:
            if self.has_taken_reaction_this_turn: return ["Reaction already taken."]
            self.has_taken_reaction_this_turn = True

        self._handle_spell_concentration(spell_data)
        cast_message = f"{ANSI_YELLOW}You cast {spell_name}{ANSI_RESET}"
        if actual_cast_level > base_spell_level: cast_message += f" (at level {actual_cast_level})"
        cast_message += "!"
        messages.insert(0, cast_message)

        spell_type = spell_data.get("type")
        if spell_type == "attack_roll":
            if not target_mob or not target_mob.is_alive(): return ["Invalid target for attack roll spell."]
            spell_attack_bonus = self.get_spell_attack_bonus()
            current_damage_dice = spell_data.get("damage_dice", "0")
            if base_spell_level == 0 and spell_data.get("damage_scaling_by_character_level"):
                scaling = spell_data["damage_scaling_by_character_level"]
                for lvl_thresh in sorted(map(int, scaling.keys()), reverse=True):
                    if self.level >= lvl_thresh: current_damage_dice = scaling[str(lvl_thresh)]; break
            add_mod_to_dmg = spell_data.get("add_ability_mod_to_damage", False)
            attack_stat_mod_for_damage = self.get_stat_modifier(self.spellcasting_ability) if add_mod_to_dmg else 0
            if combat_resolver:
                messages.extend(combat_resolver(attacker=self, defender=target_mob, attack_bonus_override=spell_attack_bonus,
                    damage_dice_override=current_damage_dice, damage_type_override=spell_data.get("damage_type", "unknown"),
                    attack_stat_mod_override=attack_stat_mod_for_damage))
        elif spell_type == "saving_throw_damage" or spell_type == "area_control_save":
            targets = []
            if spell_data.get("aoe_shape") and all_mobs_in_room: targets.extend(all_mobs_in_room)
            elif target_mob: targets.append(target_mob)
            if not targets and not (spell_data.get("range","").lower()=="self" and spell_type != "area_control_save"):
                messages.append("No valid targets for the spell effect."); return messages
            save_dc = self.get_spell_save_dc(); save_stat = spell_data.get("save_stat", "DEX").upper()
            base_damage_dice = spell_data.get("damage_dice_on_fail", "0"); damage_type = spell_data.get("damage_type", "unknown")
            half_on_success = spell_data.get("half_damage_on_success", False)
            damage_dice_to_roll = base_damage_dice
            if actual_cast_level > base_spell_level and spell_data.get("damage_dice_per_level_above_base"):
                for _ in range(actual_cast_level - base_spell_level): damage_dice_to_roll += f"+{spell_data['damage_dice_per_level_above_base']}"
            for target in targets:
                if not target.is_alive(): continue
                target_save_bonus = target.get_saving_throw_bonus(save_stat) if hasattr(target, 'get_saving_throw_bonus') else 0
                succeeded_save = False; actual_roll_performed = False
                if save_stat in ["STR", "DEX"] and hasattr(target, 'has_condition'):
                    auto_fail_conds = [Player.CONDITION_PARALYZED, Player.CONDITION_PETRIFIED, Player.CONDITION_STUNNED, Player.CONDITION_UNCONSCIOUS]
                    for cond in auto_fail_conds:
                        if target.has_condition(cond): messages.append(f"{target.name} automatically fails {save_stat} save due to {cond}!"); break
                    else: actual_roll_performed = True
                else: actual_roll_performed = True
                if actual_roll_performed:
                    save_roll_d20, r_type = roll_d20_with_advantage_disadvantage()
                    s_bonus_dice_val = 0
                    total_save = save_roll_d20 + target_save_bonus + s_bonus_dice_val
                    succeeded_save = total_save >= save_dc
                    messages.append(f"{target.name} attempts {save_stat} save (DC {save_dc}): rolled {save_roll_d20} + {target_save_bonus} = {total_save}.")
                if succeeded_save:
                    messages.append(f"{target.name} succeeds!")
                    if half_on_success and spell_type == "saving_throw_damage":
                        dmg = math.floor(roll_dice(damage_dice_to_roll) / 2)
                        if dmg > 0: messages.append(f"Takes {ANSI_RED}{dmg}{ANSI_RESET} {damage_type} (half)."); target.take_damage(dmg, self, damage_type)
                else:
                    messages.append(f"{target.name} {ANSI_RED}fails!{ANSI_RESET}")
                    if spell_type == "saving_throw_damage":
                        dmg = roll_dice(damage_dice_to_roll)
                        if dmg > 0: messages.append(f"Takes {ANSI_RED}{dmg}{ANSI_RESET} {damage_type}."); target.take_damage(dmg, self, damage_type)
                    effect_on_fail = spell_data.get("effect_on_fail")
                    if effect_on_fail and effect_on_fail.get("type") == "APPLY_CONDITION":
                        cond_name = effect_on_fail.get("condition")
                        cond_dur = self.concentration.get("remaining_rounds") if spell_data.get("requires_concentration") else effect_on_fail.get("duration_rounds", 5)
                        if hasattr(target, 'add_condition') and cond_name: target.add_condition(cond_name, cond_dur, spell_name); messages.append(f"{target.name} is now {cond_name}!")
                if hasattr(target,"is_alive") and not target.is_alive(): messages.append(f"{ANSI_GREEN}{target.name} defeated!{ANSI_RESET}")
        elif spell_type == "healing":
            target_to_heal = target_mob if target_mob else self
            if not target_to_heal or not hasattr(target_to_heal, 'current_hp'): target_to_heal = self
            if not target_to_heal: return ["Invalid target for healing."]
            total_heal_dice_str = spell_data.get("heal_dice", "0")
            if actual_cast_level > base_spell_level and spell_data.get("heal_dice_per_level_above_base"):
                for _ in range(actual_cast_level - base_spell_level): total_heal_dice_str += f"+{spell_data['heal_dice_per_level_above_base']}"

            healed_amount = roll_dice(total_heal_dice_str)

            if spell_data.get("add_spellcasting_modifier_to_heal"):
                healed_amount += self.get_stat_modifier(self.spellcasting_ability)

            # Check for Disciple of Life (Cleric - Life Domain)
            disciple_of_life_data = self.passive_granted_abilities.get("Disciple of Life")
            if disciple_of_life_data and actual_cast_level >= disciple_of_life_data.get("trigger_spell_level_min", 1):
                bonus_flat = disciple_of_life_data.get("bonus_hp_flat", 0)
                bonus_per_level = disciple_of_life_data.get("bonus_hp_per_spell_level", 0)
                extra_healing = bonus_flat + (bonus_per_level * actual_cast_level)
                if extra_healing > 0:
                    healed_amount += extra_healing
                    messages.append(f"{ANSI_YELLOW}Disciple of Life empowers your healing by an extra {extra_healing} HP!{ANSI_RESET}")

            healed_amount = max(0, healed_amount)
            target_to_heal.current_hp = min(target_to_heal.max_hp, target_to_heal.current_hp + healed_amount)
            messages.append(f"{target_to_heal.name} healed for {ANSI_GREEN}{healed_amount}{ANSI_RESET} HP. HP: {target_to_heal.current_hp}/{target_to_heal.max_hp}.")

            if target_to_heal != self and hasattr(target_to_heal, 'user') and hasattr(target_to_heal.user, 'send_message'):
                 target_to_heal.user.send_message(f"{self.name} heals you for {healed_amount} HP.")

            # Check for Blessed Healer (Cleric - Life Domain L6)
            blessed_healer_data = self.passive_granted_abilities.get("Blessed Healer")
            if blessed_healer_data and target_to_heal != self and actual_cast_level >= blessed_healer_data.get("trigger_spell_level_min", 1):
                bh_bonus_flat = blessed_healer_data.get("self_heal_flat", 0)
                bh_bonus_per_level = blessed_healer_data.get("self_heal_per_spell_level", 0)
                bh_self_heal = bh_bonus_flat + (bh_bonus_per_level * actual_cast_level)
                if bh_self_heal > 0:
                    self.current_hp = min(self.max_hp, self.current_hp + bh_self_heal)
                    messages.append(f"{ANSI_GREEN}Blessed Healer also restores {bh_self_heal} HP to you! Current HP: {self.current_hp}/{self.max_hp}{ANSI_RESET}")

        elif spell_type == "buff" or spell_type == "utility_sense" or spell_type == "buff_self_reaction":
            targets_for_buff = []
            if spell_data.get("range","").lower() == "self" or not target_mob : targets_for_buff.append(self)
            elif target_mob: targets_for_buff.append(target_mob)
            if not targets_for_buff: messages.append("No valid targets for buff."); return messages
            effect_details = spell_data.get("effect_details")
            if not effect_details: messages.append(f"No effect_details for {spell_name}."); return messages
            duration_r = self.concentration.get("remaining_rounds") if spell_data.get("requires_concentration") else 0
            if not duration_r and "duration" in spell_data:
                dur_str = spell_data.get("duration","");
                if "minute" in dur_str: duration_r = int(dur_str.split(" minute")[0].split()[-1]) * 10
                elif "hour" in dur_str: duration_r = int(dur_str.split(" hour")[0].split()[-1]) * 600
                elif "round" in dur_str: duration_r = int(dur_str.split(" round")[0].split()[-1])
            for target_buff in targets_for_buff:
                eff_to_apply = effect_details.copy()
                eff_to_apply["source_caster_id"] = self.name; eff_to_apply["duration_rounds"] = duration_r
                eff_to_apply["spell_id"] = spell_id
                target_buff.add_effect(effect_name=effect_details.get("name", spell_name), effect_data=eff_to_apply)
                messages.append(f"{target_buff.name} is now affected by {effect_details.get('name', spell_name)}.")
                if spell_data.get("requires_concentration") and target_buff.name not in self.concentration["target_ids"]:
                    self.concentration["target_ids"].append(target_buff.name)
        elif spell_type == "single_target_save_condition":
            if not target_mob or not target_mob.is_alive(): return ["Invalid target."]
            save_dc = self.get_spell_save_dc(); save_stat = spell_data.get("save_stat", "WIS").upper()
            effect_on_fail = spell_data.get("effect_on_fail")
            target_save_bonus = target_mob.get_saving_throw_bonus(save_stat) if hasattr(target_mob, 'get_saving_throw_bonus') else 0
            adv_for_save = False
            save_roll, _ = roll_d20_with_advantage_disadvantage(advantage=adv_for_save)
            total_save_roll = save_roll + target_save_bonus
            messages.append(f"{target_mob.name} attempts {save_stat} save (DC {save_dc}): rolled {save_roll} + {target_save_bonus} = {total_save_roll}.")
            if total_save_roll >= save_dc: messages.append(f"{target_mob.name} succeeds.")
            else:
                messages.append(f"{target_mob.name} {ANSI_RED}fails!{ANSI_RESET}")
                if effect_on_fail and effect_on_fail.get("type") == "APPLY_CONDITION":
                    cond_name = effect_on_fail.get("condition")
                    dur_hours = effect_on_fail.get("duration_hours",0); cond_dur_rounds = dur_hours * 600 if dur_hours else (self.concentration.get("remaining_rounds") if spell_data.get("requires_concentration") else 5)
                    if hasattr(target_mob, 'add_condition') and cond_name:
                        cond_details = {"source": spell_name}
                        if effect_on_fail.get("charmed_by_caster_id"): cond_details["charmed_by_caster_name"] = self.name
                        if effect_on_fail.get("end_condition_on_harm"): cond_details["end_on_harm_from_caster_allies"] = True
                        target_mob.add_condition(cond_name, duration_rounds=cond_dur_rounds, **cond_details)
                        messages.append(f"{target_mob.name} is now {cond_name} by you!")
        elif spell_type == "auto_hit_damage":
            if not target_mob: return [f"Spell {spell_name} requires a target."]
            num_missiles = spell_data.get("num_missiles_base", 1)
            if actual_cast_level > base_spell_level:
                num_missiles += (actual_cast_level - base_spell_level) * spell_data.get("num_missiles_per_level_above_base", 0)
            damage_per_missile_str = spell_data.get("damage_dice_per_missile", "0"); damage_type = spell_data.get("damage_type", "unknown")
            total_damage_this_spell = 0
            for i in range(num_missiles):
                missile_damage = roll_dice(damage_per_missile_str)
                total_damage_this_spell += missile_damage
                messages.append(f"A missile hits {target_mob.name} for {ANSI_RED}{missile_damage}{ANSI_RESET} {damage_type} damage.")
            if total_damage_this_spell > 0 and hasattr(target_mob, 'take_damage'):
                target_mob.take_damage(total_damage_this_spell, attacker=self, damage_type=damage_type)
                if not target_mob.is_alive(): messages.append(f"{ANSI_GREEN}{target_mob.name} has been defeated!{ANSI_RESET}")
            elif total_damage_this_spell == 0: messages.append("The missiles deal no damage.")
        else: messages.append(f"Spell type '{spell_type}' handling not yet implemented.")
        return messages

    def equip_item(self, item_to_equip_ref, target_slot_key=None): # ... (rest of file)
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
        return self.current_hp > 0 and not self.has_condition(Player.CONDITION_PETRIFIED) # Petrified characters are objects

    def take_damage(self, amount, attacker=None, damage_type="unknown"):
        if not self.is_alive(): return
        actual_damage_taken = amount
        if damage_type in self.immunities:
            actual_damage_taken = 0
            if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_GREEN}You are immune to {damage_type}! No damage taken.{ANSI_RESET}")
            if actual_damage_taken == 0: return
        if damage_type in self.vulnerabilities:
            actual_damage_taken = math.floor(actual_damage_taken * 2)
            if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_RED}You are vulnerable to {damage_type}! Damage increased!{ANSI_RESET}")
        if damage_type in self.resistances:
            actual_damage_taken = math.floor(actual_damage_taken / 2)
            if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_YELLOW}You resist {damage_type}! Damage halved.{ANSI_RESET}")
        if self.temporary_hp > 0:
            if actual_damage_taken <= self.temporary_hp:
                self.temporary_hp -= actual_damage_taken; actual_damage_taken = 0
            else:
                actual_damage_taken -= self.temporary_hp; self.temporary_hp = 0
        if actual_damage_taken > 0: self.current_hp -= actual_damage_taken
        if hasattr(self.user, 'send_message'):
            attacker_name = attacker.name if attacker and hasattr(attacker, 'name') else "something"
            self.user.send_message(f"{ANSI_RED}You take {amount} {damage_type} damage from {attacker_name}! (Reduced to {actual_damage_taken} after temp HP and resistances){ANSI_RESET}")
        if self.current_hp <= 0 and actual_damage_taken > 0 :
            relentless_endurance_used_this_time = False
            for triggered_ability in self.triggered_abilities_effects: # Check Relentless Endurance (Half-Orc)
                if triggered_ability.get("name") == "Relentless Endurance" and triggered_ability.get("trigger_condition") == "on_reduce_to_zero_hp_not_killed_outright":
                    if self.can_use_ability("Relentless Endurance"):
                        if self.mark_ability_used("Relentless Endurance"):
                            self.current_hp = triggered_ability.get("effect_details", {}).get("value", 1)
                            if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_GREEN}Relentless Endurance kicks in! You drop to {self.current_hp} HP instead of falling unconscious!{ANSI_RESET}")
                            relentless_endurance_used_this_time = True; break
            # Check Relentless Rage (Barbarian)
            if not relentless_endurance_used_this_time and self.is_raging():
                 for triggered_ability in self.triggered_abilities_effects:
                    if triggered_ability.get("name") == "Relentless Rage" and triggered_ability.get("trigger_condition") == "on_reduce_to_zero_hp_while_raging_not_killed_outright":
                        # Relentless Rage uses its own use tracking / DC scaling, not can_use_ability/mark_ability_used in the same way.
                        # This needs a dedicated counter for its DC. For now, conceptual.
                        # dc = triggered_ability.get("effect_details",{}).get("initial_dc", 10) + (getattr(self, "_relentless_rage_uses_since_rest",0) * triggered_ability.get("effect_details",{}).get("dc_increase_on_success",5) )
                        # con_save_roll = roll_dice("1d20") + self.get_saving_throw_bonus("CON")
                        # if con_save_roll >= dc:
                        #    self.current_hp = 1
                        #    # increment self._relentless_rage_uses_since_rest
                        #    if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_GREEN}Relentless Rage keeps you standing!{ANSI_RESET}")
                        #    relentless_endurance_used_this_time = True; break # Using same flag to prevent double death call
                        pass # Placeholder for Relentless Rage full logic

            # Check Relentless Rage (Barbarian)
            if not relentless_endurance_used_this_time and self.is_raging(): # Only if raging and Relentless Endurance didn't save them
                relentless_rage_feature_data = None
                for triggered_ability in self.triggered_abilities_effects:
                    if triggered_ability.get("name") == "Relentless Rage" and \
                       triggered_ability.get("trigger_condition") == "on_reduce_to_zero_hp_while_raging_not_killed_outright":
                        relentless_rage_feature_data = triggered_ability
                        break

                if relentless_rage_feature_data:
                    effect_details = relentless_rage_feature_data.get("effect_details", {})
                    initial_dc = effect_details.get("initial_dc", 10)
                    dc_increase = effect_details.get("dc_increase_on_success", 5)
                    current_dc = initial_dc + (self._relentless_rage_successes_since_rest * dc_increase)

                    con_save_bonus = self.get_saving_throw_bonus("CON")
                    # For saving throws, we need the d20 roll + bonus.
                    # We don't have advantage/disadvantage rules for this specific save type defined yet.
                    # So, a simple d20 roll.
                    save_roll_d20, _ = roll_d20_with_advantage_disadvantage() # from combat.py, defaults to normal roll

                    total_con_save = save_roll_d20 + con_save_bonus

                    save_message = f"Relentless Rage: CON Save (DC {current_dc}): Rolled {save_roll_d20} + {con_save_bonus} = {total_con_save}."
                    if hasattr(self.user, 'send_message'):
                        self.user.send_message(save_message)

                    if total_con_save >= current_dc:
                        self.current_hp = 1
                        self._relentless_rage_successes_since_rest += 1
                        if hasattr(self.user, 'send_message'):
                            self.user.send_message(f"{ANSI_GREEN}Relentless Rage keeps you standing at 1 HP! (DC for next time: {current_dc + dc_increase}){ANSI_RESET}")
                        relentless_endurance_used_this_time = True # Use same flag to prevent double death call / falling unconscious.
                    else:
                        if hasattr(self.user, 'send_message'):
                            self.user.send_message(f"{ANSI_RED}Your rage isn't enough to keep you conscious this time.{ANSI_RESET}")

            if not relentless_endurance_used_this_time: # If neither Relentless Endurance nor Relentless Rage saved them
                self.current_hp = 0; self.handle_death(attacker)
        elif self.current_hp <= 0 and not self.is_dead : self.handle_death(attacker)

    def handle_death(self, killer=None): # ... (rest of file)
        if self.is_dead: return
        self.is_dead = True; self.current_hp = 0; self.in_combat = False
        if self.target and hasattr(self.target, 'target') and self.target.target == self:
            self.target.target = None; self.target.in_combat = False
        self.target = None
        killer_name = killer.name if killer and hasattr(killer, 'name') else "unknown causes"
        print(f"[INFO] Player {self.name} has died (killed by {killer_name}).")
        death_messages = [
            f"{ANSI_RED}Darkness envelops you... You have been slain by {killer_name}.{ANSI_RESET}",
            f"{ANSI_RED}A final breath escapes your lips. {killer_name} is victorious.{ANSI_RESET}",
            f"{ANSI_RED}Your vision blurs... {killer_name}'s blow was fatal.{ANSI_RESET}"
        ]
        if hasattr(self.user, 'send_message'):
            self.user.send_message(random.choice(death_messages))
            self.user.send_message(f"{ANSI_YELLOW}Type 'respawn', 'wait', or 'quit'.{ANSI_RESET}")

    def attempt_respawn(self):
        if not self.is_dead:
            if hasattr(self.user, 'send_message'): self.user.send_message("You are already among the living!")
            return False
        if hasattr(self.user, 'send_message'):
            self.user.send_message(f"{ANSI_YELLOW}Respawn at the Church of Testing? (yes/no){ANSI_RESET}")
        response = None
        if hasattr(self.user, 'read_line'): response = self.user.read_line()
        if response and response.strip().lower() == "yes":
            self.is_dead = False; self.current_hp = max(1, self.max_hp // 4)
            self.room_id = "start"; self.in_combat = False; self.target = None
            res_msgs = [f"{ANSI_GREEN}A divine light envelops you... You are alive!{ANSI_RESET}", f"{ANSI_GREEN}Life surges back into your form!{ANSI_RESET}"]
            if hasattr(self.user, 'send_message'): self.user.send_message(random.choice(res_msgs))
            return True
        else:
            if hasattr(self.user, 'send_message'): self.user.send_message(f"{ANSI_YELLOW}You linger in the spirit world.{ANSI_RESET}")
            return False

    def add_item_to_inventory(self, item_instance_or_dict):
        self.inventory.append(item_instance_or_dict)
        name_to_show = item_instance_or_dict.get("name", "item") if isinstance(item_instance_or_dict, dict) else item_instance_or_dict.item_blueprint.name
        return f"You pick up {name_to_show}."

    def remove_item_from_inventory(self, item_name_or_id, quantity=1):
        item_to_remove_idx = -1
        for i, item_ref in enumerate(self.inventory):
            name_matches = False
            if isinstance(item_ref, dict):
                name_matches = item_ref.get("name","").lower() == item_name_or_id.lower() or \
                               item_ref.get("item_id","").lower() == item_name_or_id.lower()
            elif hasattr(item_ref, 'item_blueprint'):
                name_matches = item_ref.item_blueprint.name.lower() == item_name_or_id.lower() or \
                               item_ref.item_blueprint.id.lower() == item_name_or_id.lower()
            if name_matches: item_to_remove_idx = i; break
        if item_to_remove_idx != -1:
            removed_item = self.inventory.pop(item_to_remove_idx)
            return removed_item
        return f"You don't have '{item_name_or_id}'."

    def get_attack_details(self):
        attack_stat = "STR"; damage_dice = "1d4"; damage_type = "bludgeoning"
        weapon = self.equipment.get(Player.EQUIPMENT_SLOT_WEAPON_MAIN)
        is_proficient_with_weapon = True
        weapon_category = "melee"
        if weapon:
            props = weapon.get("properties", {})
            damage_dice = props.get("damage_dice", weapon.get("min_damage",0))
            if isinstance(damage_dice, int): damage_dice = f"1d{weapon.get('max_damage', 4)}"
            damage_type = props.get("damage_type", "bludgeoning")
            weapon_category = props.get("category", "melee")
            weapon_type_name = props.get("weapon_type", "")
            is_proficient_with_weapon = weapon_type_name in self.weapon_proficiencies or \
                                        props.get("weapon_group") in self.weapon_proficiencies or \
                                        "simple" in self.weapon_proficiencies or \
                                        ("martial" in self.weapon_proficiencies and "martial" in weapon_type_name)
            if props.get("finesse"):
                if self.get_stat_score("DEX") > self.get_stat_score("STR"): attack_stat = "DEX"
            elif weapon_category == "ranged": attack_stat = "DEX"
        else:
            attack_stat = "STR"
            if self.player_class_name == "Monk" and self.level > 0:
                if self.get_stat_score("DEX") > self.get_stat_score("STR"): attack_stat = "DEX"
                ma_dice = self.passive_granted_abilities.get("Martial Arts", {}).get("unarmed_strike_dice_by_level", {})
                current_ma_dice = "1d4"
                for lvl_thresh in sorted(map(int, ma_dice.keys()), reverse=True):
                    if self.level >= lvl_thresh: current_ma_dice = ma_dice[str(lvl_thresh)]; break
                damage_dice = current_ma_dice
        attack_bonus = self.get_attack_bonus(attack_stat, is_proficient_with_weapon, weapon_category)
        damage_stat_mod = self.get_damage_bonus(attack_stat, weapon_category, False, False)
        return {
            "attack_bonus": attack_bonus, "damage_dice": damage_dice, "damage_type": damage_type,
            "stat_modifier_for_damage": damage_stat_mod, "weapon_category": weapon_category,
            "attack_ability_stat": attack_stat
        }

[end of server/core/player.py]
