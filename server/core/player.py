import json
import math # For floor
import traceback # For detailed exception logging
import random # For death messages
from server.core.combat import roll_dice

# Globals populated by load_game_data()
CLASSES_DATA = {}
RACES_DATA = {}
ITEMS_DATA = {}
SPELLS_DATA = {}
CLASS_SPELL_LISTS_DATA = {}

CASTER_SPELL_SLOTS_PROGRESSION = {
    "full": {
        # Char Level: [1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th]
        1:  [2, 0, 0, 0, 0, 0, 0, 0, 0], 2:  [3, 0, 0, 0, 0, 0, 0, 0, 0],
        3:  [4, 2, 0, 0, 0, 0, 0, 0, 0], 4:  [4, 3, 0, 0, 0, 0, 0, 0, 0],
        5:  [4, 3, 2, 0, 0, 0, 0, 0, 0], 6:  [4, 3, 3, 0, 0, 0, 0, 0, 0],
        7:  [4, 3, 3, 1, 0, 0, 0, 0, 0], 8:  [4, 3, 3, 2, 0, 0, 0, 0, 0],
        9:  [4, 3, 3, 3, 1, 0, 0, 0, 0], 10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
        11: [4, 3, 3, 3, 2, 1, 0, 0, 0], 12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
        13: [4, 3, 3, 3, 2, 1, 1, 0, 0], 14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
        15: [4, 3, 3, 3, 2, 1, 1, 1, 0], 16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
        17: [4, 3, 3, 3, 2, 1, 1, 1, 1], 18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
        19: [4, 3, 3, 3, 3, 2, 1, 1, 1], 20: [4, 3, 3, 3, 3, 2, 2, 1, 1]
    },
    "half": {
        # Char Level: [1st, 2nd, 3rd, 4th, 5th]
        1:  [0,0,0,0,0], 2:  [2,0,0,0,0], 3:  [3,0,0,0,0], 4:  [3,0,0,0,0],
        5:  [4,2,0,0,0], 6:  [4,2,0,0,0], 7:  [4,3,0,0,0], 8:  [4,3,0,0,0],
        9:  [4,3,2,0,0], 10: [4,3,2,0,0], 11: [4,3,3,0,0], 12: [4,3,3,0,0],
        13: [4,3,3,1,0], 14: [4,3,3,1,0], 15: [4,3,3,2,0], 16: [4,3,3,2,0],
        17: [4,3,3,3,1], 18: [4,3,3,3,1], 19: [4,3,3,3,2], 20: [4,3,3,3,2]
    },
    "third": { # Eldritch Knight / Arcane Trickster (PHB table)
        # Char Level: [1st, 2nd, 3rd, 4th]
        1: [0,0,0,0], 2: [0,0,0,0],
        3: [2,0,0,0], 4: [3,0,0,0], 5: [3,0,0,0], 6: [3,0,0,0],
        7: [4,2,0,0], 8: [4,2,0,0], 9: [4,2,0,0],
        10:[4,3,0,0], 11:[4,3,0,0], 12:[4,3,0,0],
        13:[4,3,2,0], 14:[4,3,2,0], 15:[4,3,2,0],
        16:[4,3,3,0], 17:[4,3,3,0], 18:[4,3,3,0],
        19:[4,3,3,1], 20:[4,3,3,1]
    }
    # Warlock Pact Magic and Artificer infusions are handled separately due to unique mechanics.
}


# ANSI Color Codes
ANSI_BLUE = "\033[94m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m" # Added ANSI_YELLOW
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
    global SPELLS_DATA
    try:
        with open("server/data/spells.json", "r") as f: SPELLS_DATA = json.load(f)
        print(f"INFO: Loaded {len(SPELLS_DATA)} spells from spells.json.")
    except FileNotFoundError: SPELLS_DATA = {}; print("INFO: server/data/spells.json not found.")
    except Exception as e: print(f"ERROR loading spells.json: {e}")

    global CLASS_SPELL_LISTS_DATA
    try:
        with open("server/data/class_spell_lists.json", "r") as f: CLASS_SPELL_LISTS_DATA = json.load(f)
        print(f"INFO: Loaded spell lists for {len(CLASS_SPELL_LISTS_DATA)} classes from class_spell_lists.json.")
    except FileNotFoundError: CLASS_SPELL_LISTS_DATA = {}; print("INFO: server/data/class_spell_lists.json not found.")
    except Exception as e: print(f"ERROR loading class_spell_lists.json: {e}")


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

    # D&D 5e Conditions
    CONDITION_BLINDED = "Blinded"
    CONDITION_CHARMED = "Charmed"
    CONDITION_DEAFENED = "Deafened"
    CONDITION_FRIGHTENED = "Frightened"
    CONDITION_GRAPPLED = "Grappled"
    CONDITION_INCAPACITATED = "Incapacitated"
    CONDITION_INVISIBLE = "Invisible"
    CONDITION_PARALYZED = "Paralyzed"
    CONDITION_PETRIFIED = "Petrified"
    CONDITION_POISONED = "Poisoned"
    CONDITION_PRONE = "Prone"
    CONDITION_RESTRAINED = "Restrained"
    CONDITION_STUNNED = "Stunned"
    CONDITION_UNCONSCIOUS = "Unconscious"
    CONDITION_EXHAUSTION = "Exhaustion" # Often tracked in levels
    CONDITION_HIDDEN = "Hidden" # For hide skill check

    ALL_CONDITIONS = [
        CONDITION_BLINDED, CONDITION_CHARMED, CONDITION_DEAFENED, CONDITION_FRIGHTENED,
        CONDITION_GRAPPLED, CONDITION_INCAPACITATED, CONDITION_INVISIBLE, CONDITION_PARALYZED,
        CONDITION_PETRIFIED, CONDITION_POISONED, CONDITION_PRONE, CONDITION_RESTRAINED,
        CONDITION_STUNNED, CONDITION_UNCONSCIOUS, CONDITION_EXHAUSTION, CONDITION_HIDDEN
    ]


    def __init__(self, user, player_class_name="Fighter", race_name="Human", name="Adventurer", base_stats=None):
        self.user = user; self.name = name; self.player_class_name = player_class_name
        self.race_name = race_name
        self.level = 1; self.xp = 0; self.next_level_xp = 300

        if base_stats: self.base_stats = base_stats.copy()
        else: self.base_stats = {"STR":10,"DEX":10,"CON":10,"INT":10,"WIS":10,"CHA":10}

        self.current_hp = 0; self.max_hp = 0; self.temporary_hp = 0

        # Spellcasting related
        self.spellcasting_ability = None # e.g. "INT", "WIS", "CHA"
        self.known_spells = set() # Set of spell_ids the player knows
        self.prepared_spells = set() # Set of spell_ids player has prepared (for classes that prepare)
        self.current_spell_slots = {} # Dict mapping spell_level (int) to current_slots (int)
        self.max_spell_slots = {} # Dict mapping spell_level (int) to max_slots (int)
        self.concentration = {"spell_id": None, "target_ids": [], "remaining_rounds": 0} # Basic concentration tracking

        # Proficiencies & Languages (often granted by race/class)
        self.weapon_proficiencies = set()
        self.armor_proficiencies = set()
        self.tool_proficiencies = set()
        self.languages = set()

        # Racial trait flags / properties
        self.base_speed = 30 # Will be set by race / traits
        self.has_darkvision = False
        self.darkvision_range = 0 # e.g. 60
        self.has_fey_ancestry = False
        # Other specific trait flags can be added as needed e.g. self.is_halfling_lucky = False

        self.equipment = {slot: None for slot in Player.ALL_EQUIPMENT_SLOTS}
        self.inventory = []
        self.room_id = "start"
        self.skill_proficiencies = set()
        self.weapon_proficiencies = set() # e.g., {"simple", "martial", "longsword"}
        self.armor_proficiencies = set() # e.g., {"light", "medium", "shields"}
        self.tool_proficiencies = set()
        self.languages = set()

        self.used_abilities_this_rest = set() # For abilities like Second Wind
        self.active_effects = {} # For storing temporary effects like Bless, Bane, spell durations etc.
                                 # Example: {"Bless": {"caster": "cleric_name", "duration_rounds": 10},
                                 #           "Ray of Frost Slow": {"duration_rounds": 1}}

        # Racial trait flags
        self.has_darkvision = False
        self.has_fey_ancestry = False
        # Other specific trait flags can be added as needed e.g. self.is_halfling_lucky = False

        self.has_taken_action_this_turn = False
        self.has_taken_bonus_action_this_turn = False
        self.has_taken_reaction_this_turn = False # In a round

        # Attributes to be managed by the new effects system
        self.extra_attacks = 0
        self.crit_range = [20]
        self.bonus_hp_per_level = 0
        self.static_ac_bonus = 0
        self.conditional_ac_bonuses = []
        self.roll_bonuses = {"attack": [], "damage": [], "skill_check": [], "saving_throw": [], "ability_check": []}
        self.reroll_rules = []
        self.action_granted_abilities = {}
        self.passive_granted_abilities = {}

        # For racial traits and similar effects
        self.has_darkvision = False
        self.darkvision_range = 0
        self.advantage_rules = [] # Stores ADVANTAGE effect dicts
        self.disadvantage_rules = [] # Stores DISADVANTAGE effect dicts
        self.resistances = {} # e.g. {"fire": "Source of resistance"}
        self.immunities = {} # e.g. {"poison": "Source of immunity"}
        self.vulnerabilities = {} # e.g. {"cold": "Source of vulnerability"}
        self.condition_immunities = set() # e.g. {"charmed"}

        self.saving_throw_proficiencies = set()
        self.pending_proficiency_choices = []
        self.conditional_expertise_rules = []
        self.pending_spell_choices = []
        self.pending_feat_choices = []
        self.draconic_ancestry_type = None
        self.triggered_abilities_effects = []
        self.on_critical_hit_effects = []
        self.pending_feature_choices = []
        self.triggered_room_flags = set() # For one-time room interactions like investigated objects

        self.spellcasting_ability = None

        self.in_combat = False
        self.target = None
        self.is_dead = False
        self.is_reloading = False # Flag for when player is using reload command

        # Core Combat States & Conditions
        self.conditions = {} # Stores active conditions and their details (e.g., {"Blinded": {"duration_rounds": 10, "source": "Spell: Blindness"}})
        self.hit_dice = {} # e.g. {"d10": 1} for a level 1 Fighter
        self.max_hit_dice = {}
        self.fighting_styles = set() # Stores chosen fighting styles, e.g., "Defense"
        self.subclass_name = None # e.g., "Champion"


        try:
            if not (CLASSES_DATA and RACES_DATA): load_game_data()

            class_data = CLASSES_DATA.get(self.player_class_name)
            if class_data:
                for skill in class_data.get("skill_proficiencies", []):
                    self.skill_proficiencies.add(skill)
                self.spellcasting_ability = class_data.get("spellcasting_ability")
                # Initialize Hit Dice
                hd_type = f"d{class_data.get('hit_die', 6)}"
                self.hit_dice[hd_type] = self.level
                self.max_hit_dice[hd_type] = self.level

                # Auto-learn pre-defined known cantrips (e.g., Wizard)
                # Assumes spell_id in spells.json matches the lowercase, space-replaced name.
                if class_data.get("known_cantrips"):
                    for cantrip_info in class_data["known_cantrips"]:
                        spell_name = cantrip_info.get("name")
                        if spell_name:
                            spell_id = spell_name.lower().replace(" ", "_")
                            self.known_spells.add(spell_id)
                            # print(f"DEBUG: Auto-learned cantrip: {spell_id} for {self.name}")


            base_race_data, sub_race_data = self._get_race_data_parts()
            if base_race_data:
                # Base speed
                self.base_speed = base_race_data.get("speed", 30)
                # Languages
                for lang in base_race_data.get("languages", []):
                    if "one extra of your choice" not in lang: # Handle specific languages
                        self.languages.add(lang)
                    else:
                        # TODO: Game logic for player to choose extra language
                        self.languages.add("Common") # Default if choice mechanism not present
                        print(f"INFO: {self.name} ({self.race_name}) needs to choose an extra language.")

                # Process traits
                for trait in base_race_data.get("traits", []):
                    trait_name = trait.get("name")
                    if trait_name == "Keen Senses" and "Perception" in Player.ALL_SKILLS :
                        self.skill_proficiencies.add("Perception")
                    if trait_name == "Menacing" and "Intimidation" in Player.ALL_SKILLS: # Half-Orc
                        self.skill_proficiencies.add("Intimidation")
                    if trait_name == "Darkvision":
                        self.has_darkvision = True
                        # Assuming darkvision range is typically 60ft unless specified otherwise in description
                        # Example: "dim light within 60 feet"
                        try:
                            self.darkvision_range = int(trait.get("description", "").split("within ")[1].split(" feet")[0])
                        except:
                            self.darkvision_range = 60 # Default if parsing fails
                    if trait_name == "Fey Ancestry":
                        self.has_fey_ancestry = True
                    # TODO: Add processing for other base racial traits here (e.g. Dwarven Resilience, Halfling Lucky)

            if sub_race_data:
                 # Process subrace traits (e.g. High Elf Cantrip, Wood Elf Fleet of Foot, Hill Dwarf Toughness)
                if sub_race_data.get("ability_score_increase"): # Already handled by get_stat_score_racial_and_base
                    pass
                self.base_speed = sub_race_data.get("speed", self.base_speed) # Subrace might override speed (e.g. Wood Elf)
                for lang in sub_race_data.get("languages", []):
                     if "one extra of your choice" not in lang: self.languages.add(lang)

                for trait in sub_race_data.get("traits", []):
                    trait_name = trait.get("name")
                    if trait_name == "Elf Weapon Training": # High Elf, Wood Elf
                        for weapon_prof in ["longsword", "shortsword", "shortbow", "longbow"]:
                            self.weapon_proficiencies.add(weapon_prof)
                    # Dwarven Toughness is handled in calculate_max_hp
                    # High Elf Cantrip - complex, needs spell learning choice.
                    # Wood Elf Mask of the Wild - passive flag for game logic.
                    # TODO: Add processing for other sub-racial traits.
                    pass

            # Add proficiencies from class
            if class_data:
                for prof_type_key, player_attr_set_name in [
                    ("armor_proficiencies", "armor_proficiencies"),
                    ("weapon_proficiencies", "weapon_proficiencies"),
                    ("tool_proficiencies", "tool_proficiencies")]:

                    class_profs = class_data.get(prof_type_key, [])
                    player_attr_set = getattr(self, player_attr_set_name)
                    for prof in class_profs:
                        player_attr_set.add(prof)


            self.recalculate_all_stats(full_heal=True)
            print(f"[PLAYER_INIT_DEBUG] {self.name} __init__ completed successfully.")

        except Exception as e:
            print(f"!!! CRITICAL ERROR in Player.__init__ for {self.name} !!!")
            print(f"Exception Type: {type(e)}")
            print(f"Exception Args: {e.args}")
            print(traceback.format_exc())
            # Optionally, re-raise or handle more gracefully depending on how critical this is
            # For now, just logging. The object might be in an inconsistent state.
            # If self.user is set, could try to inform user, but that might also fail.

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

        is_proficient = skill_name in self.skill_proficiencies
        prof_bonus_multiplier = 1
        is_proficient_base = skill_name in self.skill_proficiencies # Base proficiency check

        # Check for conditional expertise (like Stonecunning)
        # This requires context for the check (e.g. "is this a History check about stonework?")
        # For now, we can't fully implement the conditional part here without more arguments to get_skill_bonus
        # Let's assume if a conditional expertise rule exists for the skill, we might apply it if a hypothetical
        # 'context' argument matches the rule's condition.
        # For Stonecunning: {"type": "EXPERTISE_CONDITIONAL", "skill": "History", "condition": "history_check_stonework_origin"}
        for rule in self.conditional_expertise_rules:
            if rule.get("skill") == skill_name:
                # TODO: Add context checking here. If rule.get("condition") matches current context...
                # For demonstration, let's assume if the rule exists for the skill, it applies for now.
                # This will need refinement when skill checks are actually performed with context.
                # print(f"DEBUG: Applying conditional expertise for {skill_name} due to rule: {rule}")
                prof_bonus_multiplier = 2
                is_proficient_base = True # Conditional expertise implies proficiency for that check
                break

        # Check for standard Expertise (TODO: to be added as an effect type like "EXPERTISE", "skill": "Perception")
        # if self.has_expertise_in_skill(skill_name): # Imaginary helper
        #    prof_bonus_multiplier = 2
        #    is_proficient_base = True


        prof_bonus_value = self.proficiency_bonus if is_proficient_base else 0
        total_bonus = modifier + (prof_bonus_value * prof_bonus_multiplier)

        # Apply Remarkable Athlete for STR, DEX, CON checks if not already proficient (and no expertise applied)
        # Remarkable Athlete adds half proficiency, it doesn't double it like expertise.
        remarkable_athlete_feature_data = self.get_class_feature("Remarkable Athlete") # Checks processed abilities
        if remarkable_athlete_feature_data and \
           remarkable_athlete_feature_data.get("effects", {}).get("remarkable_athlete") and \
           prof_bonus_multiplier == 1 and not is_proficient_base: # Only if not already proficient or expertised

            # The effect in classes.json for Remarkable Athlete is just: "effects": {"remarkable_athlete": True}
            # We need to ensure _apply_effect sets a flag or the logic here correctly identifies it.
            # For now, assuming get_class_feature correctly finds the "Remarkable Athlete" feature if player has it.
            # The specific effect definition {"remarkable_athlete": True} needs to be handled by _apply_effect
            # perhaps by setting a flag like self.has_remarkable_athlete = True.
            # Let's assume self.passive_granted_abilities['remarkable_athlete'] = True is set by _apply_effect.

            if self.passive_granted_abilities.get("remarkable_athlete"):
                 if ability_stat in ["STR", "DEX", "CON"]: # Check if it's a STR, DEX, or CON check
                    remarkable_bonus = math.ceil(self.proficiency_bonus / 2)
                    total_bonus += remarkable_bonus
                    # print(f"DEBUG: Remarkable Athlete added +{remarkable_bonus} to {skill_name}")

        # Apply BONUROLL effects for "skill_check" or "ability_check"
        # This is generic; specific skill bonuses could be a separate list or have more context.
        for effect_list_key in ["skill_check", "ability_check"]:
            for effect in self.roll_bonuses.get(effect_list_key, []):
                applies = True
                if effect.get("skill") and effect.get("skill") != skill_name:
                    applies = False
                if effect.get("ability") and effect.get("ability") != ability_stat: # ability_stat is STR, DEX etc.
                    applies = False
                # Add other conditions if needed

                if applies:
                    total_bonus += effect.get("value", 0)
                    # TODO: Handle dice bonuses if effect["dice"] exists

        return total_bonus

    def add_effect(self, effect_name, effect_data):
        """Adds a temporary effect to the player."""
        # effect_data should include 'duration_rounds', 'source_caster_id', etc.
        # Potentially 'bonus_to_attack_rolls', 'bonus_to_saving_throws', 'bonus_stat', etc.
        self.active_effects[effect_name] = effect_data
        # print(f"DEBUG: {self.name} gained effect: {effect_name} for {effect_data.get('duration_rounds')} rounds.")

    def remove_effect(self, effect_name):
        """Removes an active effect."""
        if effect_name in self.active_effects:
            # print(f"DEBUG: {self.name} lost effect: {effect_name}.")
            del self.active_effects[effect_name]
            return True
        return False

    def _process_effect_durations(self):
        """Called each round to decrement effect durations and remove expired ones."""
        expired_effects = []
        for effect_name, data in self.active_effects.items():
            if "duration_rounds" in data:
                data["duration_rounds"] -= 1
                if data["duration_rounds"] <= 0:
                    expired_effects.append(effect_name)
        for name in expired_effects:
            self.remove_effect(name)
            if hasattr(self.user, "send_message"):
                self.user.send_message(f"The effect of {name} fades from you.")


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

        # Add bonus HP per level from effects (e.g., Dwarven Toughness)
        max_hp_val += self.bonus_hp_per_level * self.level

        # Add flat bonus HP from items/effects (this part might be redundant if recalculate_all_stats handles item effects directly)
        for item_data in self.equipment.values():
            if item_data: max_hp_val += item_data.get("effects", {}).get("bonus_hp", 0) # Keep for now, might be refactored

        # TODO: Add flat BONMAX_HP from parsed effects if any.
        # Example: if an effect {"type": "BONUS_MAX_HP", "value": 10} is active.
        # This would likely be handled in recalculate_all_stats by applying to a self.bonus_max_hp_flat attribute,
        # and then added here: max_hp_val += self.bonus_max_hp_flat

        return max(1, max_hp_val)

    def calculate_ac(self):
        dex_modifier = self.get_stat_modifier("DEX")
        base_ac_value_from_armor = 10 + dex_modifier # Unarmored AC by default

        equipped_armor_item_data = self.equipment.get(Player.EQUIPMENT_SLOT_CHEST)
        is_wearing_armor = equipped_armor_item_data is not None

        if equipped_armor_item_data:
            props = equipped_armor_item_data.get("properties", {})
            armor_type = props.get("armor_type")
            armor_base_ac = props.get("base_ac_value", 0)

            if armor_type == "light":
                base_ac_value_from_armor = armor_base_ac + dex_modifier
            elif armor_type == "medium":
                base_ac_value_from_armor = armor_base_ac + min(dex_modifier, props.get("dex_cap_bonus", 2))
            elif armor_type == "heavy":
                base_ac_value_from_armor = armor_base_ac
            # Note: Unarmored Defense (Barbarian/Monk) will be handled by effects setting base_ac_value_from_armor too.

        calculated_ac = base_ac_value_from_armor

        # Add static AC bonuses from effects (e.g. Ring of Protection, or Defense fighting style if always on)
        calculated_ac += self.static_ac_bonus

        # Add conditional AC bonuses (like Defense fighting style if condition is "is_wearing_armor")
        for ac_bonus_effect in self.conditional_ac_bonuses:
            condition_met = False
            if ac_bonus_effect.get("condition") == "is_wearing_armor" and is_wearing_armor:
                condition_met = True
            # Add other conditions here if needed

            if condition_met:
                calculated_ac += ac_bonus_effect.get("value", 0)

        # Add AC from equipped shield (shields usually provide a direct AC bonus in their item effects)
        shield = self.equipment.get(Player.EQUIPMENT_SLOT_WEAPON_OFF)
        if shield and shield.get("properties", {}).get("armor_type") == "shield":
            calculated_ac += shield.get("effects", {}).get("bonus_ac", 0) # Assuming shield's bonus_ac is flat

        # TODO: Consider if item effects (like Ring of Protection's bonus_ac) should be handled by the generic
        # static_ac_bonus accumulation in recalculate_all_stats, or if they are summed up here from equipment.
        # For now, static_ac_bonus is for class/race features, and item bonuses are added separately.
        # This might need consolidation.
        # Example: Ring of Protection might have {"type": "BONUS_AC", "value": 1} in its item effects.
        # If that's parsed into self.static_ac_bonus, then no need to sum equipment here.
        # If not, then this existing sum is needed:
        # total_bonus_ac_from_non_armor_item_effects = sum(
        #     item_data.get("effects", {}).get("bonus_ac", 0)
        #     for slot, item_data in self.equipment.items()
        #     if item_data and slot != Player.EQUIPMENT_SLOT_CHEST and
        #        (slot != Player.EQUIPMENT_SLOT_WEAPON_OFF or item_data.get("properties", {}).get("armor_type") != "shield")
        # )
        # calculated_ac += total_bonus_ac_from_non_armor_item_effects
        # For now, let's assume recalculate_all_stats will populate self.static_ac_bonus correctly from all sources.

        return calculated_ac

    def get_attack_bonus(self, ability_stat_name, is_proficient_with_weapon=True, weapon_category=None):
        prof_bonus = self.proficiency_bonus if is_proficient_with_weapon else 0
        base_attack_bonus = self.get_stat_modifier(ability_stat_name) + prof_bonus

        # Apply BONUROLL effects of type "attack"
        for effect in self.roll_bonuses.get("attack", []):
            applies = True
            if "weapon_category" in effect and effect["weapon_category"] != weapon_category:
                applies = False
            # Add other conditions like "weapon_type", "spell_school" etc. if needed

            if applies:
                base_attack_bonus += effect.get("value", 0)
                # TODO: Handle dice bonuses if effect["dice"] exists

        return base_attack_bonus

    def get_damage_bonus(self, ability_stat_name, weapon_category=None, is_one_handed_melee_no_other_weapon=False, is_two_handed_or_versatile_melee_weapon=False):
        # Standard ability modifier to damage (for weapon attacks)
        # For spells, this is usually handled differently (spell might specify if mod is added)
        base_damage_bonus = self.get_stat_modifier(ability_stat_name)

        # Apply BONUROLL effects of type "damage"
        for effect in self.roll_bonuses.get("damage", []):
            applies = True
            if "weapon_category" in effect and effect["weapon_category"] != weapon_category:
                applies = False
            if "condition" in effect:
                if effect["condition"] == "one_handed_melee_no_other_weapon" and not is_one_handed_melee_no_other_weapon:
                    applies = False
                # Add other conditions for damage bonuses

            if applies:
                base_damage_bonus += effect.get("value", 0)
                # TODO: Handle dice bonuses if effect["dice"] exists

        return base_damage_bonus


    def get_saving_throw_bonus(self, ability_stat_name):
        if not CLASSES_DATA: return self.get_stat_modifier(ability_stat_name)
        class_data = CLASSES_DATA.get(self.player_class_name)
        is_proficient = class_data and ability_stat_name.upper() in class_data.get("saving_throw_proficiencies", [])
        prof_bonus = self.proficiency_bonus if is_proficient else 0
        base_bonus = self.get_stat_modifier(ability_stat_name) + prof_bonus
        # Saving throws don't typically add dice like Bless directly to the bonus,
        # but rather the d4 is rolled and added to the d20 result.
        # So this method itself doesn't change much, the calling code will use get_bonus_dice_for_roll_type.
        return base_bonus

    def get_bonus_dice_for_roll_type(self, roll_type_str): # roll_type_str can be "attack" or "save"
        """Checks active_effects for bonuses like Bless and returns a list of dice strings (e.g., ['1d4'])."""
        bonus_dice_list = []
        if "Bless" in self.active_effects:
            bless_effect = self.active_effects["Bless"]
            if roll_type_str == "attack" and bless_effect.get("bonus_to_attack_rolls"):
                bonus_dice_list.append(bless_effect["bonus_to_attack_rolls"]) # Should be "1d4"
            elif roll_type_str == "save" and bless_effect.get("bonus_to_saving_throws"):
                bonus_dice_list.append(bless_effect["bonus_to_saving_throws"]) # Should be "1d4"
        # Add other effects here (Bane for penalties, etc.)
        return bonus_dice_list


    def get_spell_save_dc(self):
        if not self.spellcasting_ability: return 8
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data : return 8
        spell_mod = self.get_stat_modifier(self.spellcasting_ability)
        return 8 + self.proficiency_bonus + spell_mod

    def _initialize_spell_slots(self):
        self.max_spell_slots = {} # Reset
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data or not self.spellcasting_ability:
            self.current_spell_slots = {} # No spellcasting ability, no slots
            return

        slot_progression_type = class_data.get("spell_slots_by_level")

        if isinstance(slot_progression_type, str) and slot_progression_type in CASTER_SPELL_SLOTS_PROGRESSION:
            # Full, Half, Third caster based on generic tables
            progression_table = CASTER_SPELL_SLOTS_PROGRESSION[slot_progression_type]
            level_slots = progression_table.get(self.level, [])
            for i, num_slots in enumerate(level_slots):
                if num_slots > 0:
                    self.max_spell_slots[i + 1] = num_slots
        elif isinstance(slot_progression_type, dict):
            # Specific table for the class itself (e.g., Artificer)
            # Here, the key in the dict is the character level as a string
            level_slots_str_keys = slot_progression_type.get(str(self.level), [])
            if isinstance(level_slots_str_keys, list): # Artificer example: [2,0,0,0,0]
                 for i, num_slots in enumerate(level_slots_str_keys):
                    if num_slots > 0:
                        self.max_spell_slots[i + 1] = num_slots
            # TODO: Handle Warlock pact magic - it's usually structured differently, e.g. {"slots": X, "slot_level": Y}
            # For now, Warlocks won't get slots from this generic method until their specific logic is added.

        # Initialize current_spell_slots (or preserve if some were used and this is just a level up)
        new_current_slots = {}
        for slot_level, max_count in self.max_spell_slots.items():
            # Preserve existing used slots if possible, otherwise set to max
            new_current_slots[slot_level] = self.current_spell_slots.get(slot_level, max_count)
            if new_current_slots[slot_level] > max_count: # Cap at new max if old current was higher
                new_current_slots[slot_level] = max_count
        self.current_spell_slots = new_current_slots

        # Ensure all levels present in max_slots are also in current_slots, even if 0
        for level_val in self.max_spell_slots.keys():
            if level_val not in self.current_spell_slots:
                 self.current_spell_slots[level_val] = self.max_spell_slots[level_val]

    def get_max_prepared_spells(self):
        """Calculates the maximum number of spells a character can prepare."""
        if not self.spellcasting_ability:
            return 0 # Non-casters or classes without spellcasting ability defined cannot prepare.

        # Most prepared casters (Wizard, Cleric, Druid) use ClassLevel + SpellcastingAbilityModifier
        # Paladins prepare ClassLevel/2 + ChaMod. Artificers are also ClassLevel/2 + IntMod.
        # This needs to be specified in class_data.json potentially, or handled with class-specific logic.

        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return 0

        preparation_type = class_data.get("preparation_type", "level_plus_modifier") # Default

        modifier = self.get_stat_modifier(self.spellcasting_ability)
        max_prepared = 0

        if self.player_class_name in ["Wizard", "Cleric", "Druid"]: # Standard preparers
            max_prepared = self.level + modifier
        elif self.player_class_name in ["Paladin", "Artificer"]:
            # For Paladin & Artificer, it's half their class level (rounded down) + modifier
            # However, Paladins get spellcasting at L2, Artificers at L1.
            # The PHB states Paladin: Cha mod + half paladin level, rounded down.
            # Artificer: Int mod + half artificer level, rounded down.
            caster_level_for_prep = math.floor(self.level / 2) if self.player_class_name in ["Paladin", "Artificer"] else self.level
            if self.player_class_name == "Artificer" and self.level == 1: caster_level_for_prep = 1 # Artificer L1 exception

            max_prepared = caster_level_for_prep + modifier
        else: # Default for any other (future) prepared casters, or if not specified
             max_prepared = self.level + modifier


        return max(1, max_prepared) # Minimum of 1 prepared spell

    def can_prepare_spells(self):
        """Checks if the character's class prepares spells."""
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return False
        # Based on PHB: Wizards, Clerics, Druids, Paladins, Artificers prepare spells.
        # Sorcerers, Bards, Rangers, Warlocks, EKs, ATs have "Spells Known".
        return self.player_class_name in ["Wizard", "Cleric", "Druid", "Paladin", "Artificer"]

    def get_available_spells_for_preparation(self):
        """
        Returns a list of spell_ids that the player can choose from when preparing spells.
        Wizards: from their known_spells (spellbook).
        Clerics, Druids, Paladins: Their entire class spell list up to the max spell level they can cast.
        Artificers: Also their class spell list.
        """
        if not self.spellcasting_ability: return []

        available_spell_ids = set()
        class_data = CLASSES_DATA.get(self.player_class_name)
        if not class_data: return []

        if self.player_class_name == "Wizard":
            # Wizards prepare from their spellbook (self.known_spells)
            # Filter known_spells to those they have slots for.
            max_castable_level = 0
            for i in range(1,10): # Spell levels 1-9
                if self.max_spell_slots.get(i,0) > 0:
                    max_castable_level = i
                else: # No higher slots
                    break

            for spell_id in self.known_spells:
                spell_data = SPELLS_DATA.get(spell_id)
                if spell_data and spell_data.get("level", 0) <= max_castable_level and spell_data.get("level",0) > 0: # Only leveled spells
                    available_spell_ids.add(spell_id)
            return list(available_spell_ids)

        # For Cleric, Druid, Paladin, Artificer - they have access to their full class spell list.
        if self.player_class_name in CLASS_SPELL_LISTS_DATA and \
           self.player_class_name in ["Cleric", "Druid", "Paladin", "Artificer"]:

            class_spell_list_ids = CLASS_SPELL_LISTS_DATA.get(self.player_class_name, [])
            max_castable_level = 0
            for i in range(1, 10): # Spell levels 1-9
                if self.max_spell_slots.get(i, 0) > 0:
                    max_castable_level = i
                else: # No higher slots
                    break

            for spell_id in class_spell_list_ids:
                spell_data = SPELLS_DATA.get(spell_id)
                if spell_data and spell_data.get("level", 0) > 0 and \
                   spell_data.get("level", 0) <= max_castable_level:
                    available_spell_ids.add(spell_id)
            return list(available_spell_ids)

        return [] # Default for classes that don't prepare this way (Bards, Sorcs etc.) or if list not found

    def prepare_spell(self, spell_id):
        if not self.can_prepare_spells():
            return f"{self.player_class_name}s do not prepare spells in this manner."

        spell_data = SPELLS_DATA.get(spell_id)
        if not spell_data:
            return f"Spell '{spell_id}' not found."
        if spell_data.get("level", 0) == 0: # Cantrips are not "prepared" in the same way
            return "Cantrips are known automatically and don't need to be prepared."

        # Check if player can prepare this spell (e.g. Wizard knows it, or it's on Cleric list)
        # This requires more sophisticated logic for "known" vs "available on class list"
        # For Wizards:
        if self.player_class_name == "Wizard" and spell_id not in self.known_spells:
            return f"You do not know the spell '{spell_data.get('name', spell_id)}' to prepare it."
        # For Clerics/Druids/Paladins - check against their class list (TODO)
        # For now, assume if they try to prepare it, it's on their list for testing purposes.

        if len(self.prepared_spells) >= self.get_max_prepared_spells():
            return "Cannot prepare more spells. Max prepared limit reached."

        self.prepared_spells.add(spell_id)
        return f"'{spell_data.get('name', spell_id)}' prepared."

    def unprepare_spell(self, spell_id):
        if not self.can_prepare_spells():
            return f"{self.player_class_name}s do not prepare spells in this manner."

        spell_data = SPELLS_DATA.get(spell_id)
        spell_name_to_show = spell_data.get("name", spell_id) if spell_data else spell_id

        if spell_id in self.prepared_spells:
            self.prepared_spells.remove(spell_id)
            return f"'{spell_name_to_show}' unprepared."
        return f"'{spell_name_to_show}' was not prepared."

    def is_spell_prepared(self, spell_id):
        spell_data = SPELLS_DATA.get(spell_id)
        if not spell_data: return False

        if spell_data.get("level", 0) == 0: # Cantrips are always "prepared" if known
            return spell_id in self.known_spells

        if not self.can_prepare_spells(): # Spells Known casters (Bard, Sorc) always have their known spells "prepared"
            return spell_id in self.known_spells

        return spell_id in self.prepared_spells


    def _apply_effect(self, effect_data, feature_name="Unknown Feature"):
        """Helper function to apply a single effect dictionary to the player."""
        effect_type = effect_data.get("type")
        notes = effect_data.get("notes", "") # For debugging or richer descriptions later

        if effect_type == "SET_EXTRA_ATTACKS":
            self.extra_attacks = max(self.extra_attacks, effect_data.get("value", 0))
        elif effect_type == "SET_CRITICAL_RANGE":
            new_crit_range = effect_data.get("range", [20])
            if new_crit_range and new_crit_range[0] < self.crit_range[0]: # Assumes lower is better
                self.crit_range = new_crit_range
        elif effect_type == "BONUS_HP_PER_LEVEL":
            self.bonus_hp_per_level += effect_data.get("value", 0)
        elif effect_type == "BONUS_AC":
            if "condition" in effect_data:
                self.conditional_ac_bonuses.append(effect_data.copy())
            else:
                self.static_ac_bonus += effect_data.get("value", 0)
        elif effect_type == "BONUS_ROLL":
            roll_type = effect_data.get("roll_type") # "attack", "damage", "skill_check", "saving_throw", "ability_check"
            if roll_type in self.roll_bonuses:
                self.roll_bonuses[roll_type].append(effect_data.copy())
            else:
                print(f"Warning: Unknown roll_type '{roll_type}' in BONUROLL effect from {feature_name} ({notes})")
        elif effect_type == "REROLL_DICE" or effect_type == "REROLL_DICE_SPECIFIC": # Combined handler
            self.reroll_rules.append(effect_data.copy())
        elif effect_type == "GRANT_ACTION_ABILITY":
            min_level = effect_data.get("level_requirement", 0)
            if self.level >= min_level:
                ability_name = effect_data.get("name")
                if ability_name:
                    self.action_granted_abilities[ability_name] = effect_data.copy()
                else:
                    print(f"Warning: GRANT_ACTION_ABILITY missing name from {feature_name} ({notes})")
            # else: feature not granted yet due to level requirement
        elif effect_type == "ENABLE_ABILITY_MOD_OFFHAND_DAMAGE": # For Two-Weapon Fighting Style
            # This might be a flag the combat system checks, or influences get_damage_bonus logic for offhand.
            # For now, let's add it to passive_granted_abilities.
            self.passive_granted_abilities["two_weapon_fighting_style_active"] = True
        elif effect_type == "GRANT_REACTION_ABILITY": # E.g. Protection Fighting Style
             ability_name = effect_data.get("name")
             if ability_name:
                self.action_granted_abilities[ability_name] = effect_data.copy() # Reactions are still abilities
             else:
                print(f"Warning: GRANT_REACTION_ABILITY missing name from {feature_name} ({notes})")

        # TODO: Add more effect types here:
        # GRANT_PROFICIENCY (skill, weapon, armor, tool, saving_throw)
        # EXPERTISE
        # RESISTANCE, IMMUNITY, VULNERABILITY
        # CONDITION_IMMUNITY
        # UNARMORED_DEFENSE
        elif effect_type == "SET_DARKVISION":
            self.has_darkvision = True
            self.darkvision_range = max(self.darkvision_range, effect_data.get("range", 0))
        elif effect_type == "ADVANTAGE":
            self.advantage_rules.append(effect_data.copy())
        elif effect_type == "DISADVANTAGE": # Assuming we might add this type
            self.disadvantage_rules.append(effect_data.copy())
        elif effect_type == "RESISTANCE":
            damage_type_key = effect_data.get("damage_type")
            ancestry_key_ref = effect_data.get("damage_type_from_ancestry")

            if ancestry_key_ref and self.draconic_ancestry_type:
                # Find the chosen ancestry details
                ancestry_options = RACES_DATA.get("Dragonborn", {}).get("draconic_ancestry_options", [])
                chosen_ancestry_info = next((opt for opt in ancestry_options if opt.get("choice_value") == self.draconic_ancestry_type), None)
                if chosen_ancestry_info:
                    damage_type_key = chosen_ancestry_info.get("damage_type")
                else:
                    print(f"Warning: Could not find ancestry details for '{self.draconic_ancestry_type}' to determine resistance type.")

            if damage_type_key:
                self.resistances[damage_type_key] = effect_data.get("notes", True)
            elif not ancestry_key_ref: # Only print warning if it wasn't meant to be from ancestry
                print(f"Warning: RESISTANCE effect missing damage_type from {feature_name} ({notes})")

        elif effect_type == "IMMUNITY": # Assuming we might add this type
            damage_type = effect_data.get("damage_type")
            if damage_type:
                self.immunities[damage_type] = effect_data.get("notes", True)
        elif effect_type == "VULNERABILITY": # Assuming we might add this type
            damage_type = effect_data.get("damage_type")
            if damage_type:
                self.vulnerabilities[damage_type] = effect_data.get("notes", True)
        elif effect_type == "CONDITION_IMMUNITY":
            condition = effect_data.get("condition")
            if condition:
                self.condition_immunities.add(condition)
        elif effect_type == "GRANT_PROFICIENCY":
            category = effect_data.get("category")
            name = effect_data.get("name")
            if not category or not name:
                print(f"Warning: GRANT_PROFICIENCY missing category or name from {feature_name} ({notes})")
                return
            if category == "skill": self.skill_proficiencies.add(name)
            elif category == "weapon": self.weapon_proficiencies.add(name) # Assumes individual weapon names
            elif category == "armor": self.armor_proficiencies.add(name)   # Assumes individual armor names
            elif category == "tool": self.tool_proficiencies.add(name)
            elif category == "saving_throw": self.saving_throw_proficiencies.add(name.upper())
            elif category == "weapon_group": # e.g. "simple", "martial"
                # This would require expanding self.weapon_proficiencies to understand groups
                # or having a predefined list of weapons per group. For now, just add the group name.
                self.weapon_proficiencies.add(name)
            elif category == "armor_group": # e.g. "light", "medium", "heavy", "shields"
                self.armor_proficiencies.add(name)
            else: print(f"Warning: Unknown proficiency category '{category}' in GRANT_PROFICIENCY from {feature_name}")
        elif effect_type == "GRANT_PROFICIENCY_CHOICE":
            # Store the choice request. Actual choice resolution will happen elsewhere (e.g. char creation).
            self.pending_proficiency_choices.append(effect_data.copy())
        elif effect_type == "EXPERTISE_CONDITIONAL":
            self.conditional_expertise_rules.append(effect_data.copy())
        elif effect_type == "GRANT_SPELL_CHOICE":
            self.pending_spell_choices.append(effect_data.copy())
        elif effect_type == "SET_BASE_SPEED":
            self.base_speed = effect_data.get("value", self.base_speed)
        elif effect_type == "CUSTOM_MECHANIC":
            custom_name = effect_data.get("name")
            if custom_name:
                self.passive_granted_abilities[custom_name] = effect_data.copy()
            else:
                print(f"Warning: CUSTOM_MECHANIC missing name from {feature_name} ({notes})")
        elif effect_type == "GRANT_FEAT_CHOICE":
            self.pending_feat_choices.append(effect_data.copy())
        elif effect_type == "GRANT_SPELL":
            spell_id = effect_data.get("spell_id")
            if spell_id:
                self.known_spells.add(spell_id)
                # TODO: Handle spellcasting_ability_override if present, potentially storing it in
                # a dict like self.spell_specific_casting_stats[spell_id] = {"ability": "INT"}
                # For now, granted spells will use the player's default class spellcasting ability.
            else:
                print(f"Warning: GRANT_SPELL effect missing spell_id from {feature_name} ({notes})")
        elif effect_type == "PASSIVE_ABILITY":
            ability_name = effect_data.get("name")
            if ability_name:
                # Store the whole effect_data dict as it might contain details needed by other systems
                self.passive_granted_abilities[ability_name] = effect_data.copy()
            else:
                print(f"Warning: PASSIVE_ABILITY missing name from {feature_name} ({notes})")
        elif effect_type == "GRANT_CHOICE": # For feature choices like Fighting Style
            self.pending_feature_choices.append(effect_data.copy())
        elif effect_type == "TRIGGERED_ABILITY":
            self.triggered_abilities_effects.append(effect_data.copy())
        elif effect_type == "ADD_CRIT_DICE":
            self.on_critical_hit_effects.append(effect_data.copy())
        # etc.
        else:
            print(f"Warning: Unknown effect type '{effect_type}' from {feature_name} ({notes}). Effect data: {effect_data}")


    def recalculate_all_stats(self, full_heal=False):
        if not (CLASSES_DATA and RACES_DATA and ITEMS_DATA): load_game_data()

        # Reset effect-derived attributes to defaults or empty
        self.extra_attacks = 0
        self.crit_range = [20]
        self.bonus_hp_per_level = 0
        self.static_ac_bonus = 0
        self.conditional_ac_bonuses = []
        self.roll_bonuses = {"attack": [], "damage": [], "skill_check": [], "saving_throw": [], "ability_check": []}
        self.reroll_rules = []
        self.action_granted_abilities = {}
        self.passive_granted_abilities = {}
        self.fighting_styles = set()

        # Reset racial/general effect attributes
        self.has_darkvision = False
        self.darkvision_range = 0
        self.advantage_rules = []
        self.disadvantage_rules = []
        self.resistances = {}
        self.immunities = {}
        self.vulnerabilities = {}
        self.condition_immunities = set()

        # Reset proficiencies that can be granted by effects (base class profs are added directly in __init__)
        # However, if class features can grant more profs, they should also be reset here and reapplied.
        # For now, assuming __init__ handles initial set and effects add to them.
        # Let's clear and rebuild all profs here for consistency.
        self.skill_proficiencies.clear()
        self.weapon_proficiencies.clear()
        self.armor_proficiencies.clear()
        self.tool_proficiencies.clear()
        self.saving_throw_proficiencies.clear() # New set for saving throw profs from effects

        self.pending_proficiency_choices = []
        self.conditional_expertise_rules = []
        self.pending_spell_choices = []
        self.pending_feat_choices = []
        self.pending_feature_choices = [] # For GRANT_CHOICE like fighting styles
        self.triggered_abilities_effects = []
        self.on_critical_hit_effects = []


        # --- Apply Base Class Proficiencies (before other effects might modify/add to them) ---
        # This ensures base proficiencies are always there even if no explicit GRANT_PROFICIENCY effect exists for them.
        # These were originally set in __init__ but are better handled here for centralization.
        class_data_for_base_profs = CLASSES_DATA.get(self.player_class_name, {})
        for skill_prof in class_data_for_base_profs.get("skill_proficiencies", []): # Default skills for class
            self.skill_proficiencies.add(skill_prof)
        for armor_prof in class_data_for_base_profs.get("armor_proficiencies", []):
            self.armor_proficiencies.add(armor_prof)
        for weapon_prof in class_data_for_base_profs.get("weapon_proficiencies", []):
            self.weapon_proficiencies.add(weapon_prof)
        for tool_prof in class_data_for_base_profs.get("tool_proficiencies", []):
            self.tool_proficiencies.add(tool_prof)
        for st_prof in class_data_for_base_profs.get("saving_throw_proficiencies", []): # From class definition
            self.saving_throw_proficiencies.add(st_prof.upper())


        # --- Apply Racial Effects ---
        base_race_data, sub_race_data = self._get_race_data_parts()
        if base_race_data and "traits" in base_race_data:
            for trait in base_race_data["traits"]:
                if "effects" in trait and isinstance(trait["effects"], list):
                    for effect_data in trait["effects"]:
                        self._apply_effect(effect_data, feature_name=trait.get("name", "Unknown Racial Trait"))
        if sub_race_data and "traits" in sub_race_data:
            for trait in sub_race_data["traits"]:
                if "effects" in trait and isinstance(trait["effects"], list):
                    for effect_data in trait["effects"]:
                        self._apply_effect(effect_data, feature_name=trait.get("name", "Unknown Subrace Trait"))

        # --- Apply Class and Subclass Feature Effects ---
        class_data = CLASSES_DATA.get(self.player_class_name)
        if class_data:
            # Collect all applicable features (base class + subclass)
            all_features_to_apply = []
            for level_int in range(1, self.level + 1):
                level_str = str(level_int)
                # Base class features
                features_at_level = class_data.get("features_by_level", {}).get(level_str, [])
                all_features_to_apply.extend(features_at_level)

                # Subclass features
                if self.subclass_name and "subclasses" in class_data and self.subclass_name in class_data["subclasses"]:
                    subclass_data = class_data["subclasses"][self.subclass_name]
                    sub_features_at_level = subclass_data.get("features_by_level", {}).get(level_str, [])
                    all_features_to_apply.extend(sub_features_at_level)

            # Process collected features
            # Handle choices like Fighting Style first if they grant other effects
            for feature_data in all_features_to_apply:
                feature_name = feature_data.get("name", "Unknown Feature")
                if feature_data.get("choices_feature_type") == "fighting_style":
                    # Assume player.chosen_fighting_style is set during character creation or level up choice
                    chosen_style_name = getattr(self, 'chosen_fighting_style', None) # TODO: Need to store this choice
                    if chosen_style_name:
                        for choice in feature_data.get("available_choices", []):
                            if choice.get("name") == chosen_style_name:
                                self.fighting_styles.add(chosen_style_name) # Add to set of known styles
                                if "effects" in choice and isinstance(choice["effects"], list):
                                    for effect_data in choice["effects"]:
                                        self._apply_effect(effect_data, feature_name=f"{feature_name}: {chosen_style_name}")
                                break # Found and applied chosen style

                # Apply direct effects of the feature itself
                if "effects" in feature_data and isinstance(feature_data["effects"], list):
                    # Handle overrides: if this feature overrides another, its effects might replace/modify
                    # For now, simple application; overrides might need smarter logic in _apply_effect
                    # or by processing features in a specific order.
                    # The get_class_feature handles overrides for ability usage, but recalculate_all_stats
                    # needs to ensure the *correct version* of an effect is applied if overridden.
                    # This simple loop might apply older versions then newer ones.
                    # A better way: use get_class_feature for each effect type to ensure only the highest level override applies.
                    # For now, this linear application will mostly work if overrides fully replace prior values (e.g. SET_EXTRA_ATTACKS)
                    for effect_data in feature_data["effects"]:
                         self._apply_effect(effect_data, feature_name=feature_name)

        # --- Apply Item Effects ---
        # TODO: Iterate through self.equipment. For each item, if it has an "effects" list,
        # call self._apply_effect(effect_data_from_item). This needs care to avoid double-applying
        # things like AC bonuses if calculate_ac already handles them from items.
        # For now, focusing on class/race effects.

        # --- Recalculate Core Derived Stats using the now-populated effect attributes ---
        self.proficiency_bonus = self.calculate_proficiency_bonus()

        old_max_hp = self.max_hp
        self.max_hp = self.calculate_max_hp() # Uses self.bonus_hp_per_level now

        if full_heal or self.current_hp <= 0:
            self.current_hp = self.max_hp
        else:
            hp_increase = self.max_hp - old_max_hp
            self.current_hp = min(self.max_hp, self.current_hp + hp_increase)
            if self.current_hp <= 0 and self.max_hp > 0: # Ensure not dead if HP increased above 0
                self.current_hp = 1

        self.ac = self.calculate_ac() # Uses self.static_ac_bonus and self.conditional_ac_bonuses

        self._initialize_spell_slots() # Initialize/update spell slots (mostly independent of effects list for now)

        # print(f"DEBUG Player {self.name} recalculate_all_stats complete. extra_attacks: {self.extra_attacks}, crit_range: {self.crit_range}, bonus_hp_per_level: {self.bonus_hp_per_level}, static_ac_bonus: {self.static_ac_bonus}")
        # print(f"DEBUG conditional_ac_bonuses: {self.conditional_ac_bonuses}")
        # print(f"DEBUG roll_bonuses (attack): {self.roll_bonuses['attack']}")


    def add_xp(self, amount):
        self.xp += amount
        if self.xp >= self.next_level_xp: self.level_up()

    def level_up(self):
        old_level = self.level
        self.level += 1
        self.next_level_xp = self.next_level_xp * 2 # Consider revising this for 1-100 scale later

        # Update hit dice before recalculating stats (which might heal)
        class_data = CLASSES_DATA.get(self.player_class_name)
        if class_data:
            hd_type = f"d{class_data.get('hit_die', 6)}"
            new_dice_to_add = self.level - old_level
            self.hit_dice[hd_type] = self.hit_dice.get(hd_type, 0) + new_dice_to_add
            self.max_hit_dice[hd_type] = self.level
            self.hit_dice[hd_type] = min(self.hit_dice[hd_type], self.max_hit_dice[hd_type])

        self.recalculate_all_stats(full_heal=True) # Full heal on level up is common
        if hasattr(self.user, 'send_message'):
             self.user.send_message(f"{ANSI_GREEN}Ding! You reached level {self.level}!{ANSI_RESET}")

    def get_class_feature(self, feature_name):
        """
        Retrieves the definition of a class feature.
        This can be from the raw class JSON or from the processed action_granted_abilities.
        Priority is given to action_granted_abilities if the feature is found there,
        as it represents the processed form of the ability.
        """
        if not CLASSES_DATA: load_game_data()

        # Check processed abilities first (populated by recalculate_all_stats)
        if feature_name in self.action_granted_abilities:
            # The structure in action_granted_abilities IS the feature data for usage.
            # It should contain "uses", "refresh_on", "effect_details" etc.
            # Ensure it has a "name" field if not already the key.
            granted_ability_data = self.action_granted_abilities[feature_name].copy()
            granted_ability_data.setdefault("name", feature_name) # Ensure name is present
            # Add a marker to indicate it's from the processed list, if needed for debugging.
            granted_ability_data["source_type"] = "action_granted_ability"
            return granted_ability_data

        # Fallback to searching raw class/subclass JSON (original method)
        # This part is important for features that aren't "granted abilities" via the effect system,
        # or for looking up the original definition if needed.
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
                    if best_raw_feature_match is None or \
                       is_override_match or \
                       (is_direct_match and not best_raw_feature_match.get("override_feature_name")) or \
                       level_int > best_raw_feature_match.get("granted_at_level", 0):

                        temp_copy = raw_feature_data_item.copy()
                        temp_copy["granted_at_level"] = level_int
                        if is_override_match:
                             temp_copy["original_name_for_tracking"] = feature_name
                        best_raw_feature_match = temp_copy

        # Subclass check for raw features
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
                            if best_raw_feature_match is None or \
                               is_override_match or \
                               (is_direct_match and not best_raw_feature_match.get("override_feature_name")) or \
                               level_int > best_raw_feature_match.get("granted_at_level", 0):

                                temp_copy = sub_feature_item_raw.copy()
                                temp_copy["granted_at_level"] = level_int
                                if is_override_match:
                                    temp_copy["original_name_for_tracking"] = feature_name
                                best_raw_feature_match = temp_copy

        if best_raw_feature_match:
             best_raw_feature_match["source_type"] = "raw_class_json" # Mark source for clarity
        return best_raw_feature_match


    def can_use_ability(self, ability_name):
        feature_data = self.get_class_feature(ability_name)
        if not feature_data:
            # print(f"DEBUG: No feature data found for {ability_name} in can_use_ability")
            return False

        max_uses = feature_data.get("uses")
        refresh_on = feature_data.get("refresh_on")

        # If uses or refresh_on is not defined, assume it's a passive or always available ability (not tracked)
        if max_uses is None or refresh_on is None:
            # print(f"DEBUG: {ability_name} is passive or not tracked for uses.")
            return True

        # Use the original name for tracking if it's an override feature
        tracked_name = feature_data.get("original_name_for_tracking", ability_name)

        current_uses = self.used_abilities_this_rest.get(tracked_name, 0)
        # print(f"DEBUG: Checking {tracked_name}: current_uses={current_uses}, max_uses={max_uses}")

        if current_uses < max_uses:
            return True

        # print(f"DEBUG: {tracked_name} has no uses left ({current_uses}/{max_uses}).")
        return False

    def mark_ability_used(self, ability_name):
        feature_data = self.get_class_feature(ability_name)
        if not feature_data: return False

        max_uses = feature_data.get("uses")
        refresh_on = feature_data.get("refresh_on")

        if max_uses is None or refresh_on is None: # Not a usage-tracked ability
            return False

        tracked_name = feature_data.get("original_name_for_tracking", ability_name)

        current_uses = self.used_abilities_this_rest.get(tracked_name, 0)
        if current_uses < max_uses:
            self.used_abilities_this_rest[tracked_name] = current_uses + 1
            # print(f"DEBUG: Marked {tracked_name} used. New count: {self.used_abilities_this_rest[tracked_name]}")
            return True
        # print(f"DEBUG: Could not mark {tracked_name} used, already at max uses.")
        return False # Already at max uses or not trackable

    def reset_ability_uses_on_rest(self, rest_type="long"):
        abilities_to_clear_from_dict = []
        for ability_name_tracked, times_used in self.used_abilities_this_rest.items():
            # We need to get feature data for the actual ability name,
            # which might be different from the tracked_name if it was an override.
            # This assumes tracked_name is usually the base ability name.
            feature_data = self.get_class_feature(ability_name_tracked) # Get data for the key we stored

            if feature_data:
                refresh_condition = feature_data.get("refresh_on")
                if refresh_condition == "short_or_long_rest": # Clears on short or long
                    abilities_to_clear_from_dict.append(ability_name_tracked)
                elif refresh_condition == "long_rest" and rest_type == "long": # Only clears on long
                    abilities_to_clear_from_dict.append(ability_name_tracked)
                # If refresh_condition is "short_rest" and rest_type is "short", it's also covered by "short_or_long_rest"
            else:
                # If no feature data found (e.g. old ability removed from class), clear it anyway.
                abilities_to_clear_from_dict.append(ability_name_tracked)

        for ab_name in abilities_to_clear_from_dict:
            if ab_name in self.used_abilities_this_rest:
                del self.used_abilities_this_rest[ab_name]
                # print(f"DEBUG: Reset uses for {ab_name} on {rest_type} rest.")

    def perform_long_rest(self):
        self.current_hp = self.max_hp
        self.temporary_hp = 0 # Temp HP is lost on a long rest
        self.reset_ability_uses_on_rest(rest_type="long")

        # Restore half of max hit dice (minimum 1)
        for hd_type, max_dice in self.max_hit_dice.items():
            dice_to_regain = math.ceil(max_dice / 2) # PHB: at least one die
            self.hit_dice[hd_type] = min(max_dice, self.hit_dice.get(hd_type, 0) + dice_to_regain)

        # TODO: Reduce exhaustion levels if implemented
        # self.remove_condition(Player.CONDITION_EXHAUSTION, levels=1)

        self._restore_all_spell_slots() # Restore spell slots on long rest

        if hasattr(self.user, 'send_message'):
            self.user.send_message(f"{ANSI_GREEN}You feel fully rested and revitalized. Hit dice and spell slots have been restored.{ANSI_RESET}")
        return "You feel fully rested and revitalized."

    def _restore_all_spell_slots(self):
        """Restores all spell slots to their maximums. Called on a long rest for most casters."""
        # Warlocks will need special handling for Pact Magic recovery on short rests.
        if self.player_class_name == "Warlock": # Placeholder for Warlock logic
            # print(f"DEBUG: Warlock {self.name} would regain pact slots on short/long rest here.")
            # For now, let them also regen on long rest like others for simplicity until short rest pact magic is built.
            pass # Fall through to general restoration for now.

        for level_val, max_count in self.max_spell_slots.items():
            self.current_spell_slots[level_val] = max_count
        # print(f"DEBUG: Spell slots restored for {self.name}: {self.current_spell_slots}")


    def spend_spell_slot(self, spell_level_to_spend):
        """
        Attempts to spend a spell slot of the given level.
        Returns True if successful, False otherwise.
        Handles casting lower level spells with higher level slots implicitly if needed by caller.
        This method just validates if a slot of *at least* spell_level_to_spend is available and spends the lowest possible.
        Actual upcasting logic (choosing which higher slot to use) is more complex and handled by cast_spell.
        For now, this just spends a slot of the exact level.
        """
        if spell_level_to_spend == 0: # Cantrips don't use slots
            return True

        if self.current_spell_slots.get(spell_level_to_spend, 0) > 0:
            self.current_spell_slots[spell_level_to_spend] -= 1
            # print(f"DEBUG: Spent L{spell_level_to_spend} slot. Remaining: {self.current_spell_slots.get(spell_level_to_spend)}")
            return True
        else:
            # print(f"DEBUG: No L{spell_level_to_spend} slots available for {self.name}.")
            # TODO: Implement upcasting: check for higher level slots if an L_spell_level_to_spend slot is not available.
            # For now, strict slot level spending.
            return False


    def perform_short_rest(self, dice_to_spend_list=None):
        """
        Performs a short rest.
        dice_to_spend_list: A list of strings like ["d10", "d10"] indicating dice to spend.
        """
        if not dice_to_spend_list: dice_to_spend_list = []

        healed_amount = 0
        con_modifier = self.get_stat_modifier("CON")
        messages = ["You take a short rest."]

        for die_str_to_spend in dice_to_spend_list:
            if self.hit_dice.get(die_str_to_spend, 0) > 0:
                self.hit_dice[die_str_to_spend] -= 1
                roll_result = roll_dice(f"1{die_str_to_spend}") # e.g. "1d10"
                heal = max(0, roll_result + con_modifier) # Cannot heal less than 0 from a die
                self.current_hp = min(self.max_hp, self.current_hp + heal)
                healed_amount += heal
                messages.append(f"Spent 1{die_str_to_spend}, recovered {heal} HP (rolled {roll_result} + {con_modifier} CON).")
            else:
                messages.append(f"Cannot spend 1{die_str_to_spend}, none available.")

        self.reset_ability_uses_on_rest(rest_type="short") # For features that refresh on short or long rest

        if healed_amount > 0:
            messages.append(f"Total HP recovered: {healed_amount}. Current HP: {self.current_hp}/{self.max_hp}.")
        else:
            messages.append("No hit dice spent for healing.")

        if hasattr(self.user, 'send_message'):
            self.user.send_message("\n".join(messages))
        return "\n".join(messages)


    def reset_turn_actions(self):
        self.has_taken_action_this_turn = False
        self.has_taken_bonus_action_this_turn = False
        # Reaction is typically once per round, not per turn, so it might be reset at start of player's turn in combat loop
        # For now, let's assume it's reset here for simplicity until a full round manager is in place.
        self.has_taken_reaction_this_turn = False
        self.has_action_surge_active = False # Flag for Action Surge effect


    # --- Condition Management ---
    def add_condition(self, condition_name, duration_rounds=None, source=None, save_dc=None, save_ends=False, save_stat=None):
        if condition_name in self.condition_immunities:
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"{ANSI_GREEN}You are immune to the {condition_name} condition!{ANSI_RESET}")
            return False # Immune to the condition

        if condition_name not in Player.ALL_CONDITIONS:
            print(f"Warning: Unknown condition '{condition_name}' cannot be added to {self.name}.")
            return False

        condition_details = {"source": source, "duration_rounds": duration_rounds}
        if save_ends:
            condition_details["save_dc"] = save_dc
            condition_details["save_stat"] = save_stat
            condition_details["save_ends"] = True

        self.conditions[condition_name] = condition_details

        # Handle immediate effects of certain conditions
        if condition_name == Player.CONDITION_PRONE:
            # Movement speed becomes 0 if not already. Actual movement cost is handled elsewhere.
            pass # No immediate stat change, but affects attacks and movement cost
        elif condition_name == Player.CONDITION_UNCONSCIOUS or condition_name == Player.CONDITION_PETRIFIED:
            # Drop everything, fall prone (handled by unconscious status)
            self.conditions[Player.CONDITION_PRONE] = {"source": condition_name, "duration_rounds": None} # Add prone if unconscious/petrified
            # Clear target, etc.
            self.target = None
            self.in_combat = False # Usually

        if hasattr(self.user, 'send_message'):
            self.user.send_message(f"{ANSI_YELLOW}You are now affected by {condition_name}.{ANSI_RESET}")
        print(f"[CONDITION] {self.name} is now {condition_name}.")
        return True

    def remove_condition(self, condition_name):
        if condition_name in self.conditions:
            removed_condition_details = self.conditions.pop(condition_name)
            # Handle effects of removal
            if condition_name == Player.CONDITION_PRONE and removed_condition_details.get("source") in [Player.CONDITION_UNCONSCIOUS, Player.CONDITION_PETRIFIED]:
                # If prone was due to unconsciousness/petrification, don't remove it if the source condition is still there
                if self.has_condition(Player.CONDITION_UNCONSCIOUS) or self.has_condition(Player.CONDITION_PETRIFIED):
                    self.conditions[Player.CONDITION_PRONE] = removed_condition_details # Put it back
                    return False # Prone not truly removed as underlying cause persists

            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"{ANSI_GREEN}You are no longer affected by {condition_name}.{ANSI_RESET}")
            print(f"[CONDITION] {self.name} is no longer {condition_name}.")
            return True
        return False

    def has_condition(self, condition_name):
        return condition_name in self.conditions

    def get_active_conditions(self):
        return list(self.conditions.keys())

    def is_incapacitated(self):
        return self.has_condition(Player.CONDITION_INCAPACITATED) or \
               self.has_condition(Player.CONDITION_PARALYZED) or \
               self.has_condition(Player.CONDITION_PETRIFIED) or \
               self.has_condition(Player.CONDITION_STUNNED) or \
               self.has_condition(Player.CONDITION_UNCONSCIOUS)

    def can_take_actions(self):
        return not self.is_incapacitated()

    def can_take_bonus_actions(self): # Specific bonus actions might have other restrictions
        return not self.is_incapacitated()

    def can_take_reactions(self):
         return not self.is_incapacitated() # And haven't used one this round

    def get_effective_speed(self):
        current_speed = self.base_speed # Start with base speed from race

        # Check for specific racial traits modifying speed (e.g. Wood Elf's Fleet of Foot)
        # This is already incorporated into self.base_speed by __init__ if subrace provides a speed.
        # However, if a trait provides a *bonus* to speed rather than setting it, it would be handled here.
        # Example: if a "Mobile" feat existed and granted +10 speed.
        # for effect_name, effect_data in self.active_effects.items():
        #     current_speed += effect_data.get("bonus_speed", 0)

        # Apply condition effects
        if self.has_condition(Player.CONDITION_RESTRAINED) or \
           self.has_condition(Player.CONDITION_GRAPPLED) or \
           self.has_condition(Player.CONDITION_PARALYZED) or \
           self.has_condition(Player.CONDITION_PETRIFIED) or \
           self.has_condition(Player.CONDITION_STUNNED) or \
           self.has_condition(Player.CONDITION_UNCONSCIOUS):
            return 0

        # TODO: Add effects from spells like Slow or Haste from self.active_effects
        # For example, if "Ray of Frost Slow" in self.active_effects, reduce speed.
        if "Ray of Frost Slow" in self.active_effects: # Example, effect needs to be applied by spell
            base_speed = max(0, base_speed - 10)

        return base_speed
    # --- End Condition Management ---

    def get_climbing_movement_multiplier(self):
        """ Returns the movement cost multiplier for climbing. Normally 2, but 1 for Thief with Second-Story Work."""
        second_story_work = self.get_class_feature("Second-Story Work")
        if second_story_work and second_story_work.get("effects", {}).get("ignore_climbing_extra_movement_cost"):
            return 1.0 # Normal movement cost
        return 2.0 # Climbing normally costs double


    def use_indomitable(self, original_save_stat, original_dc):
        """
        Allows the Fighter to reroll a failed saving throw.
        original_save_stat: The stat used for the save (e.g., "DEX", "WIS").
        original_dc: The DC of the save they failed.
        Returns: A dict {"success": bool, "new_roll_total": int, "message": str}
        """
        if self.player_class_name != "Fighter":
            return {"success": False, "new_roll_total": 0, "message": "Only Fighters can use Indomitable."}
        if self.level < 9:
            return {"success": False, "new_roll_total": 0, "message": "You must be level 9 or higher to use Indomitable."}

        feature_name = "Indomitable"
        if not self.can_use_ability(feature_name):
            return {"success": False, "new_roll_total": 0, "message": "You have no uses of Indomitable left."}

        if not self.mark_ability_used(feature_name):
            return {"success": False, "new_roll_total": 0, "message": "Error marking Indomitable as used."} # Should not happen

        # Perform the reroll
        # For now, assume no advantage/disadvantage on the Indomitable reroll itself
        # In 5e, Indomitable is just a reroll, not explicitly with advantage/disadvantage unless another source grants it.
        new_d20_roll = random.randint(1, 20)
        save_bonus = self.get_saving_throw_bonus(original_save_stat)
        new_total_roll = new_d20_roll + save_bonus

        success = new_total_roll >= original_dc

        message = f"You use Indomitable! New {original_save_stat} save roll: {new_d20_roll} + {save_bonus} = {new_total_roll} vs DC {original_dc}. "
        if success:
            message += f"{ANSI_GREEN}Success!{ANSI_RESET}"
        else:
            message += f"{ANSI_RED}Still failed.{ANSI_RESET}"

        if hasattr(self.user, 'send_message'):
            self.user.send_message(message)

        return {"success": success, "new_roll_total": new_total_roll, "message": message}


    def use_action_surge(self):
        feature_name = "Action Surge"
        ability_data = self.action_granted_abilities.get(feature_name)

        if not ability_data:
            return "You do not have the Action Surge ability prepared/active."

        if self.player_class_name != "Fighter": # Class check
            return "Only Fighters can use Action Surge."
        # Level check could be implicitly handled by when GRANT_ACTION_ABILITY is given,
        # but an explicit check based on self.level vs a potential ability_data.get("min_level", 0)
        # could be added if features are granted before level in JSON for some reason.
        # For now, assume recalculate_all_stats only grants it at appropriate levels.

        if not self.can_use_ability(feature_name):
            return "You cannot use Action Surge right now (no uses left or other restriction)."

        if self.has_action_surge_active: # Prevent using if already active this turn
             return "You have already gained an action from Action Surge this turn."

        effect_details = ability_data.get("effect_details", {})
        if effect_details.get("type") != "GAIN_EXTRA_ACTION_THIS_TURN":
            return "Action Surge is not configured correctly."

        if not self.mark_ability_used(feature_name):
            # This should ideally be caught by can_use_ability
            return "Failed to mark Action Surge as used (should not happen if can_use_ability passed)."

        self.has_action_surge_active = True # Game loop/command handler will check this
        self.has_taken_action_this_turn = False # Reset to allow another action

        msg = f"{ANSI_GREEN}You activate Action Surge! You gain an additional action this turn.{ANSI_RESET}"
        if hasattr(self.user, 'send_message'):
            self.user.send_message(msg)

        # Note: The game's main command processing loop (in main.py handle_client)
        # will need to check `player.has_action_surge_active`. After the player takes their
        # additional action, that loop should set `player.has_action_surge_active = False`.
        # The current `player.reset_turn_actions()` also sets `has_action_surge_active = False`,
        # which is called at the start of the player's turn processing in `handle_client`.
        # This should correctly limit it to one extra action per Action Surge use.
        # The L17 Fighter ability to use Action Surge twice per rest (but still only one extra action per turn)
        # is handled by the `uses: 2` in the JSON and the `can_use_ability/mark_ability_used` logic.

        return msg

    def use_second_wind(self):
        # Retrieve the ability definition from processed abilities
        feature_name = "Second Wind"
        ability_data = self.action_granted_abilities.get(feature_name)

        if not ability_data:
            return "You do not have the Second Wind ability prepared/active."

        if self.player_class_name != "Fighter": # Still good to keep a class check for some core abilities
            return "Only Fighters can use Second Wind."

        if self.has_taken_action_this_turn and ability_data.get("action_type") == "action":
            return "You have already taken your action this turn."
        # Add checks for bonus action if ability_data.action_type == "bonus_action"

        if not self.can_use_ability(feature_name): # Uses get_class_feature which now checks action_granted_abilities
            return "You cannot use Second Wind right now (no uses left or other restriction)."

        effect_details = ability_data.get("effect_details", {})
        if effect_details.get("type") != "HEAL":
            return "Second Wind is not configured correctly for healing."

        heal_dice_str = effect_details.get("dice", "1d10")
        bonus_formula = effect_details.get("bonus_formula") # e.g., "fighter_level"

        base_heal = roll_dice(heal_dice_str)
        added_bonus = 0
        if bonus_formula == "fighter_level": # Could expand to "class_level" or specific stat mods
            added_bonus = self.level # Assuming fighter level is player level for now
        # elif bonus_formula == "CON_mod": added_bonus = self.get_stat_modifier("CON")

        total_heal_potential = base_heal + added_bonus
        actual_healed_amount = 0

        if self.current_hp < self.max_hp:
            actual_healed_amount = min(total_heal_potential, self.max_hp - self.current_hp)
            self.current_hp += actual_healed_amount
        else: # Already at max HP
            self.mark_ability_used(feature_name) # Still consumes the use
            if ability_data.get("action_type") == "action": self.has_taken_action_this_turn = True
            # elif ability_data.get("action_type") == "bonus_action": self.has_taken_bonus_action_this_turn = True
            return "You use Second Wind, but you are already at maximum HP!"

        self.mark_ability_used(feature_name)
        if ability_data.get("action_type") == "action": self.has_taken_action_this_turn = True
        # elif ability_data.get("action_type") == "bonus_action": self.has_taken_bonus_action_this_turn = True

        return f"You use Second Wind and regain {actual_healed_amount} HP. (Rolled {base_heal} from {heal_dice_str}, +{added_bonus} bonus = {total_heal_potential} potential)."

    def use_dash(self, direction_name, world_ref):
        if not (self.player_class_name == "Rogue" and self.level >= 2):
            return {"success": False, "message": "Only Rogues of level 2 or higher can Dash."}
        cunning_action_feature = self.get_class_feature("Cunning Action")
        if not cunning_action_feature or "Dash" not in cunning_action_feature.get("grants_abilities", []):
            return {"success": False, "message": "You do not have the Cunning Action: Dash ability."}
        if self.has_taken_action_this_turn:
            return {"success": False, "message": "You have already taken an action this turn."}
        if not self.room:
            return {"success": False, "message": "You are not in a valid room to dash from."}

        current_room_obj = self.room
        room1_id = current_room_obj.exits.get(direction_name)
        if not room1_id:
            return {"success": False, "message": f"You cannot dash {direction_name} - there is no exit there."}
        room1_obj = world_ref.get(room1_id)
        if not room1_obj:
            self.has_taken_action_this_turn = True
            return {"success": True, "rooms_moved": 1, "final_room_id": room1_id, "message": f"You dash {direction_name} into an unfamiliar passage..."}
        room2_id = room1_obj.exits.get(direction_name)
        room2_obj = world_ref.get(room2_id) if room2_id else None
        self.has_taken_action_this_turn = True
        if room2_obj:
            return {"success": True, "rooms_moved": 2, "final_room_id": room2_id, "message": f"You swiftly dash {direction_name} two rooms ahead!"}
        else:
            return {"success": True, "rooms_moved": 1, "final_room_id": room1_id, "message": f"You dash {direction_name} one room ahead."}

    def get_spell_details(self, spell_id_or_name):
        """
        Retrieves spell data from SPELLS_DATA.
        spell_id_or_name: The key of the spell in spells.json (e.g., "fire_bolt") or its display name.
        """
        if not SPELLS_DATA: load_game_data() # Ensure spell data is loaded

        # First, try direct lookup by ID (key in spells.json)
        spell_data = SPELLS_DATA.get(spell_id_or_name)
        if spell_data:
            return spell_data.copy() # Return a copy to prevent modification of global data

        # If not found by ID, try searching by name (case-insensitive)
        for id, data in SPELLS_DATA.items():
            if data.get("name", "").lower() == spell_id_or_name.lower():
                return data.copy()

        print(f"DEBUG: Spell '{spell_id_or_name}' not found in SPELLS_DATA.")
        return None

    def get_spell_attack_bonus(self):
        if not self.spellcasting_ability:
            print(f"Warning: Player {self.name} has no spellcasting_ability for class {self.player_class_name}.")
            return self.get_stat_modifier("INT")
        modifier = self.get_stat_modifier(self.spellcasting_ability)
        return modifier + self.proficiency_bonus

    def cast_spell_attack(self, spell_name, target_mob, combat_resolver, current_round_counter=0):
        """Generic handler for spell attacks like Fire Bolt, Ray of Frost."""
        spell_data = self.get_spell_details(spell_name)
        if not spell_data: return [f"You do not know the spell '{spell_name}'."]

        # Check if the class can cast this specific spell (e.g. Wizard for Fire Bolt/Ray of Frost)
        # This is a simple check; a more robust system would check a player's actual known/prepared spell list.
        if self.player_class_name == "Wizard" and spell_name not in [c.get("name") for c in CLASSES_DATA.get("Wizard", {}).get("known_cantrips", [])]:
             return [f"As a {self.player_class_name}, you don't know '{spell_name}' directly."]
        # Add similar checks for other classes if they get these spells.

        if spell_data.get("attack_type") != "spell_attack_roll":
            return [f"'{spell_name}' is not an attack roll spell you can cast this way."]

        if self.has_taken_action_this_turn: return ["You have already taken an action this turn."]
        if not target_mob or not hasattr(target_mob, 'is_alive') or not target_mob.is_alive(): return ["You need a living target."]

        spell_range_type = spell_data.get("range", "same_room")
        if spell_range_type == "same_room":
            if not self.room or not hasattr(target_mob, 'room') or self.room.id != target_mob.room.id:
                return [f"{target_mob.name} is not in range for {spell_name}."]

        spell_attack_bonus = self.get_spell_attack_bonus()
        damage_dice = spell_data.get("damage", "0")
        damage_type = spell_data.get("damage_type", "unknown")

        attack_stat_mod_override_for_damage = 0 # Default for most cantrips
        if spell_data.get("add_ability_mod_to_damage", False):
            if self.spellcasting_ability:
                attack_stat_mod_override_for_damage = self.get_stat_modifier(self.spellcasting_ability)
            else: # Should not happen if can cast
                attack_stat_mod_override_for_damage = self.get_stat_modifier("INT")


        self.has_taken_action_this_turn = True

        messages = [f"{ANSI_YELLOW}You cast {spell_name} at {target_mob.name}!{ANSI_RESET}"]

        attack_outcome_messages = combat_resolver(
            attacker=self, defender=target_mob,
            attack_bonus_override=spell_attack_bonus,
            damage_dice_override=damage_dice,
            damage_type_override=damage_type,
            attack_stat_mod_override=attack_stat_mod_override_for_damage
        )
        messages.extend(attack_outcome_messages)

        hit_success = False
        if attack_outcome_messages:
            # Check if any message indicates a hit or crit, but not a miss.
            # This is a bit fragile; ideally resolve_attack would return structured hit status.
            for msg_line in attack_outcome_messages:
                msg_line_lower = msg_line.lower()
                if ("hits" in msg_line_lower or "critical hit" in msg_line_lower) and \
                   "misses" not in msg_line_lower and "miss" not in msg_line_lower:
                    hit_success = True
                    break

        if hit_success and spell_data.get("effects_on_hit"):
            for effect_data in spell_data["effects_on_hit"]:
                effect_to_apply = effect_data.copy()
                effect_to_apply["applied_round"] = current_round_counter
                if hasattr(target_mob, 'apply_status_effect'):
                    target_mob.apply_status_effect(effect_to_apply)
                    messages.append(f"{target_mob.name} is affected by {effect_data.get('type')} ({effect_data.get('amount')})!")
        return messages

    def cast_fire_bolt(self, target_mob, combat_resolver, current_round_counter=0):
        if self.player_class_name != "Wizard":
            return ["Only Wizards can cast Fire Bolt this way currently."]
        return self.cast_spell_attack("Fire Bolt", target_mob, combat_resolver, current_round_counter)

    def cast_ray_of_frost(self, target_mob, combat_resolver, current_round_counter=0):
        if self.player_class_name != "Wizard":
            return ["Only Wizards can cast Ray of Frost this way currently."]
        return self.cast_spell_attack("Ray of Frost", target_mob, combat_resolver, current_round_counter)


    def _handle_spell_concentration(self, spell_data):
        """Checks and manages concentration for a new spell."""
        if self.concentration["spell_id"]:
            old_spell_data = SPELLS_DATA.get(self.concentration["spell_id"])
            old_spell_name = old_spell_data.get("name", self.concentration["spell_id"]) if old_spell_data else self.concentration["spell_id"]
            # TODO: Remove effects of old_spell_name from targets if applicable
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"Your concentration on {old_spell_name} breaks.")
            self.concentration = {"spell_id": None, "target_ids": [], "remaining_rounds": 0}

        if spell_data.get("requires_concentration"):
            duration_str = spell_data.get("duration", "0 rounds") # e.g. "Concentration, up to 1 minute"
            # Simple parsing for now, assuming "X minute(s)" means X*10 rounds (1 min = 10 rounds of 6s)
            # A more robust duration parser would be needed for "1 hour", "until dispelled", etc.
            rounds = 0
            if "minute" in duration_str:
                try: rounds = int(duration_str.split(" minute")[0].split("up to ")[-1]) * 10
                except: rounds = 10 # Default 1 minute if parsing fails
            elif "round" in duration_str:
                try: rounds = int(duration_str.split(" round")[0].split("up to ")[-1])
                except: rounds = 1 # Default 1 round

            self.concentration["spell_id"] = spell_data.get("id", spell_data.get("name").lower().replace(" ","_")) # Store spell_id
            self.concentration["remaining_rounds"] = rounds
            # Target IDs will be populated by the specific spell effect logic
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"You begin concentrating on {spell_data.get('name')}.")
            return True
        return False # Did not start new concentration

    def cast_spell(self, spell_id, target_mob=None, chosen_spell_level=None, combat_resolver=None, current_round_counter=0, all_mobs_in_room=None):
        if all_mobs_in_room is None: all_mobs_in_room = []

        spell_data = self.get_spell_details(spell_id)
        if not spell_data:
            return [f"You do not know how to cast '{spell_id}'."]

        spell_name = spell_data.get("name", spell_id)
        base_spell_level = spell_data.get("level", 0)

        # 1. Check if known/prepared
        if not self.is_spell_prepared(spell_id) and base_spell_level > 0 : # Cantrips are fine if known via is_spell_prepared
             # Spells Known casters are covered by is_spell_prepared returning true if known
            return [f"You do not have '{spell_name}' prepared."]

        # 2. Determine cast level and spend slot
        actual_cast_level = base_spell_level
        if base_spell_level > 0 and chosen_spell_level is not None and chosen_spell_level > base_spell_level:
            actual_cast_level = chosen_spell_level

        if base_spell_level > 0: # Leveled spells require slots
            slot_spent_successfully = False
            # Try to spend the intended (possibly upcast) slot first
            if self.spend_spell_slot(actual_cast_level):
                slot_spent_successfully = True
            else:
                # If intended slot failed (e.g. player chose L3 but has no L3),
                # OR if casting at base level and no base level slots are available,
                # try to find the lowest available higher-level slot to auto-upcast into.
                # This is only for auto-upcasting if the base slot is missing.
                # If chosen_spell_level was specified and failed, we don't fish for other higher slots here.
                if chosen_spell_level is None or chosen_spell_level == base_spell_level:
                    for higher_slot_level in range(base_spell_level + 1, 10): # Check L+1 up to L9
                        if self.spend_spell_slot(higher_slot_level):
                            actual_cast_level = higher_slot_level # Update to the level of the slot actually used
                            slot_spent_successfully = True
                            messages.append(f"(No L{base_spell_level} slots, automatically cast at L{actual_cast_level})")
                            break

            if not slot_spent_successfully:
                 return [f"Not enough spell slots to cast '{spell_name}' (tried level {chosen_spell_level if chosen_spell_level else base_spell_level}, and auto-upcasting if applicable)."]

        # 3. Casting Time & Action Economy
        casting_time = spell_data.get("casting_time", "1 action").lower()
        if "1 action" in casting_time:
            if self.has_taken_action_this_turn and not self.has_action_surge_active: # Action surge allows another action
                return ["You have already taken your action this turn."]
            self.has_taken_action_this_turn = True
        elif "1 bonus action" in casting_time:
            if self.has_taken_bonus_action_this_turn:
                return ["You have already taken your bonus action this turn."]
            self.has_taken_bonus_action_this_turn = True
        elif "reaction" in casting_time:
            # Reaction spell casting needs specific trigger conditions, handled by game loop usually.
            if self.has_taken_reaction_this_turn: # Per round
                 return ["You have already taken your reaction this round."]
            self.has_taken_reaction_this_turn = True
        # Other casting times (1 minute, 10 minutes, etc.) are for non-combat mostly.

        # 4. Handle Concentration
        concentrating_on_new_spell = self._handle_spell_concentration(spell_data)

        messages = [f"{ANSI_YELLOW}You cast {spell_name}{ANSI_RESET}"]
        if actual_cast_level > base_spell_level:
            messages[0] += f" (at level {actual_cast_level})"
        messages[0] += "!"


        # 5. Dispatch to effect handlers based on spell_data.type
        spell_type = spell_data.get("type")

        if spell_type == "attack_roll":
            # This reuses some logic from the old cast_spell_attack, but integrated here
            if not target_mob or not hasattr(target_mob, 'is_alive') or not target_mob.is_alive():
                return ["You need a living target for an attack roll spell."]

            # Range check (simplified)
            # spell_range = spell_data.get("range", "self").lower() # TODO: Proper range parsing
            # if "feet" in spell_range or "touch" in spell_range or "self" in spell_range:
            #    if not self.room or not hasattr(target_mob, 'room') or self.room.id != target_mob.room.id:
            #        return [f"{target_mob.name} is not in range for {spell_name}."]

            spell_attack_bonus = self.get_spell_attack_bonus()

            # Handle damage scaling for cantrips
            current_damage_dice = spell_data.get("damage_dice", "0")
            if base_spell_level == 0:
                scaling_data = spell_data.get("damage_scaling_by_character_level")
                if scaling_data:
                    # Iterate downwards to find the highest applicable level for scaling
                    for lvl_threshold in sorted(map(int, scaling_data.keys()), reverse=True):
                        if self.level >= lvl_threshold:
                            current_damage_dice = scaling_data[str(lvl_threshold)]
                            break
            # TODO: Handle damage upscaling for leveled attack_roll spells based on actual_cast_level

            add_mod_to_dmg = spell_data.get("add_ability_mod_to_damage", False)
            attack_stat_mod_for_damage = self.get_stat_modifier(self.spellcasting_ability) if add_mod_to_dmg else 0

            if combat_resolver:
                attack_outcome_messages = combat_resolver(
                    attacker=self, defender=target_mob,
                    attack_bonus_override=spell_attack_bonus,
                    damage_dice_override=current_damage_dice, # Use potentially scaled cantrip damage
                    damage_type_override=spell_data.get("damage_type", "unknown"),
                    attack_stat_mod_override=attack_stat_mod_for_damage
                )
                messages.extend(attack_outcome_messages)
                # TODO: Apply on-hit effects from spell_data (like Ray of Frost slow)
            else: messages.append("DEBUG: Combat resolver not provided for attack roll spell.")
            # TODO: Apply on-hit effects from spell_data (like Ray of Frost slow) after successful hit

        elif spell_type == "saving_throw_damage":
            # Determine targets (simplified for now)
            targets = []
            if spell_data.get("aoe_shape") and all_mobs_in_room: # Simplified AoE
                targets.extend(all_mobs_in_room)
                messages.append(f"The spell affects the area, targeting {len(targets)} creatures.")
            elif target_mob:
                targets.append(target_mob)

            if not targets:
                messages.append("No valid targets for the spell effect.")
                # Note: Should probably not expend slot if no targets, but current logic spends slot before this.
                # This might need adjustment: check for targets before spending slot for AoE/targeted non-self spells.
                return messages

            save_dc = self.get_spell_save_dc()
            save_stat = spell_data.get("save_stat", "DEX").upper() # Default to DEX if not specified
            base_damage_dice = spell_data.get("damage_dice_on_fail", "0")
            damage_type = spell_data.get("damage_type", "unknown")
            half_on_success = spell_data.get("half_damage_on_success", False)

            # Handle upcasting damage
            damage_dice_to_roll = base_damage_dice
            if actual_cast_level > base_spell_level:
                dmg_dice_per_level = spell_data.get("damage_dice_per_level_above_base") # e.g. "1d6"
                if dmg_dice_per_level:
                    num_extra_dice_groups = actual_cast_level - base_spell_level
                    # Crude addition of dice strings. A better dice roller would parse "3d6 + 2d6"
                    for _ in range(num_extra_dice_groups): damage_dice_to_roll += f"+{dmg_dice_per_level}"

            for target in targets:
                if not hasattr(target, 'is_alive') or not target.is_alive():
                    messages.append(f"{target.name} is already defeated or invalid.")
                    continue

                target_save_bonus = target.get_saving_throw_bonus(save_stat) if hasattr(target, 'get_saving_throw_bonus') else 0
                succeeded_save = False
                actual_roll_performed = False

                # Check for auto-fail conditions on STR/DEX saves
                if save_stat in ["STR", "DEX"] and hasattr(target, 'has_condition'):
                    auto_fail_conditions = [Player.CONDITION_PARALYZED, Player.CONDITION_PETRIFIED, Player.CONDITION_STUNNED, Player.CONDITION_UNCONSCIOUS]
                    for cond in auto_fail_conditions:
                        if target.has_condition(cond):
                            succeeded_save = False # Explicitly fail
                            messages.append(f"{target.name} automatically fails the {save_stat} save due to being {cond}!")
                            break
                    else: # No auto-fail condition met, proceed to roll
                        actual_roll_performed = True
                else: # Not a STR/DEX save, or target has no 'has_condition'
                    actual_roll_performed = True

                if actual_roll_performed:
                    # TODO: Integrate adv/disadv for saving throws (pass adv/disadv to a d20 roller from combat.py)
                    save_roll_d20_result, roll_type_str = roll_d20_with_advantage_disadvantage() # No adv/disadv passed yet

                    save_bonus_dice_value = 0
                    if hasattr(target, 'get_bonus_dice_for_roll_type'):
                        bonus_dice_list = target.get_bonus_dice_for_roll_type("save")
                        for dice_str in bonus_dice_list:
                            save_bonus_dice_value += roll_dice(dice_str)

                    total_save_roll = save_roll_d20_result + target_save_bonus + save_bonus_dice_value
                    succeeded_save = total_save_roll >= save_dc

                    roll_msg_part = f"rolled {save_roll_d20_result}"
                    if roll_type_str != "normal": roll_msg_part += f" ({roll_type_str})"
                    messages.append(f"{target.name} attempts a {save_stat} save (DC {save_dc}): {roll_msg_part} + {target_save_bonus} (mod) + {save_bonus_dice_value} (dice) = {total_save_roll}.")

                # succeeded_save is now set
                damage_to_deal = 0
                if succeeded_save:
                    messages.append(f"{target.name} succeeds on the save!")
                    if half_on_success:
                        damage_to_deal = math.floor(roll_dice(damage_dice_to_roll) / 2)
                        messages.append(f"Takes {ANSI_RED}{damage_to_deal}{ANSI_RESET} {damage_type} damage (half on success).")
                    else:
                        messages.append("Takes no damage.")
                else:
                    messages.append(f"{target.name} {ANSI_RED}fails the save!{ANSI_RESET}")
                    damage_to_deal = roll_dice(damage_dice_to_roll) # For damage component
                    messages.append(f"Takes {ANSI_RED}{damage_to_deal}{ANSI_RESET} {damage_type} damage.")

                    # Apply condition if defined for save failure
                    effect_on_fail = spell_data.get("effect_on_fail")
                    if effect_on_fail and effect_on_fail.get("type") == "APPLY_CONDITION":
                        condition_name = effect_on_fail.get("condition")
                        # Duration logic for conditions needs to be more robust based on spell's duration field.
                        # For now, simple fixed duration or concentration based.
                        cond_duration = self.concentration.get("remaining_rounds") if spell_data.get("requires_concentration") else effect_on_fail.get("duration_rounds", 5) # Default 5 rounds if not concentration

                        if hasattr(target, 'add_condition') and condition_name:
                            target.add_condition(condition_name, duration_rounds=cond_duration, source=spell_name)
                            messages.append(f"{target.name} is now {condition_name}!")
                        else:
                            messages.append(f"Could not apply {condition_name} to {target.name}.")


                if damage_to_deal > 0 and hasattr(target, 'take_damage'):
                    target.take_damage(damage_to_deal, attacker=self, damage_type=damage_type)
                    if not target.is_alive():
                        messages.append(f"{ANSI_GREEN}{target.name} has been defeated!{ANSI_RESET}")

        elif spell_type == "area_control_save": # For spells like Entangle
            # Targeting for AoE needs proper implementation based on shape and origin point.
            # For now, assume all_mobs_in_room are potential targets if spell is AoE.
            # This is a placeholder for actual AoE targeting logic.
            targets_in_area = []
            if spell_data.get("aoe_shape") and all_mobs_in_room:
                 # TODO: Implement actual geometric targeting based on player position, spell range, AoE shape/size.
                 # For now, affects all mobs in room for simplicity if it's an AoE.
                targets_in_area.extend(all_mobs_in_room)
                if not targets_in_area and not target_mob: # If no mobs and no primary target, maybe target player if self-castable AoE
                    pass # Or message "No targets in area."
                elif target_mob and target_mob not in targets_in_area: # If a primary target was specified, ensure it's included
                    targets_in_area.append(target_mob) # This might double-add if target_mob was already in all_mobs_in_room

            if not targets_in_area and target_mob: # Single target specified for a potential AoE spell
                targets_in_area.append(target_mob)

            if not targets_in_area:
                messages.append("No valid targets in the area of effect.")
                return messages

            save_dc = self.get_spell_save_dc()
            save_stat = spell_data.get("save_stat", "DEX").upper()
            effect_on_fail = spell_data.get("effect_on_fail")

            for target in targets_in_area:
                if not hasattr(target, 'is_alive') or not target.is_alive(): continue

                target_save_bonus = target.get_saving_throw_bonus(save_stat) if hasattr(target, 'get_saving_throw_bonus') else 0
                save_roll = random.randint(1,20)
                # TODO: Advantage/Disadvantage on save
                total_save_roll = save_roll + target_save_bonus

                messages.append(f"{target.name} attempts a {save_stat} save (DC {save_dc}): rolled {save_roll} + {target_save_bonus} = {total_save_roll}.")
                if total_save_roll >= save_dc:
                    messages.append(f"{target.name} succeeds on the save.")
                    # Handle half damage or other effects on success if applicable
                else:
                    messages.append(f"{target.name} {ANSI_RED}fails the save!{ANSI_RESET}")
                    if effect_on_fail and effect_on_fail.get("type") == "APPLY_CONDITION":
                        condition_name = effect_on_fail.get("condition")
                        cond_duration = self.concentration.get("remaining_rounds") if spell_data.get("requires_concentration") else effect_on_fail.get("duration_rounds", 5)
                        if hasattr(target, 'add_condition') and condition_name:
                            target.add_condition(condition_name, duration_rounds=cond_duration, source=spell_name)
                            messages.append(f"{target.name} is now {condition_name}!")
            # Difficult terrain for Entangle is a persistent room effect, not handled here yet.

        elif spell_type == "healing":
            # Simplified: target is self or target_mob
            target_to_heal = target_mob
            if not target_mob and "Touch" in spell_data.get("range","") or "Self" in spell_data.get("range", ""):
                target_to_heal = self # Default to self if touch/self and no target

            if not target_to_heal or not hasattr(target_to_heal, 'current_hp'):
                # Check if it's a self-cast heal where target_mob might be None
                if spell_data.get("range", "").lower() == "self" and not target_mob:
                    target_to_heal = self
                else:
                    return ["Invalid target for healing."]

            base_heal_dice = spell_data.get("heal_dice", "0")
            total_heal_dice_str = base_heal_dice

            # Upcasting for healing spells
            if actual_cast_level > base_spell_level:
                dice_per_level_up = spell_data.get("heal_dice_per_level_above_base")
                if dice_per_level_up: # e.g. "1d4"
                    num_extra_dice = actual_cast_level - base_spell_level
                    # This is a crude way to add dice strings. A proper dice roller should handle multiple dice types.
                    for _ in range(num_extra_dice): total_heal_dice_str += f"+{dice_per_level_up}"


            healed_amount = roll_dice(total_heal_dice_str)
            if spell_data.get("add_spellcasting_modifier_to_heal", False):
                healed_amount += self.get_stat_modifier(self.spellcasting_ability)

            healed_amount = max(0, healed_amount)
            target_to_heal.current_hp = min(target_to_heal.max_hp, target_to_heal.current_hp + healed_amount)
            messages.append(f"{target_to_heal.name} is healed for {ANSI_GREEN}{healed_amount}{ANSI_RESET} HP. Current HP: {target_to_heal.current_hp}/{target_to_heal.max_hp}.")
            if target_to_heal != self and hasattr(target_to_heal, 'user') and hasattr(target_to_heal.user, 'send_message'): # If healing other player
                 target_to_heal.user.send_message(f"{self.name} heals you for {healed_amount} HP.")

        elif spell_type == "buff":
            targets_for_buff = []
            # Determine how many targets based on spell_data and actual_cast_level
            max_targets = spell_data.get("max_targets_base", 1)
            if actual_cast_level > base_spell_level:
                targets_per_level = spell_data.get("max_targets_per_level_above_base", 0)
                max_targets += (actual_cast_level - base_spell_level) * targets_per_level

            # Simplified targeting: if target_mob is provided, it's the primary.
            # If more targets allowed, could try to pick from all_mobs_in_room or player's party.
            # For now, just target_mob or self if no target_mob for single target buffs.
            # For multi-target like Bless, this needs better target selection UI/logic.
            # TEMP: For Bless, if target_mob is None, target self and up to X allies in room (not implemented yet)
            #       or if target_mob is given, target it and X-1 allies.
            #       For initial test, if it's Bless, just target 'self' if no target_mob

            if target_mob: targets_for_buff.append(target_mob)
            elif spell_data.get("range","").lower() == "self" or not target_mob : targets_for_buff.append(self)
            # TODO: Proper multi-targeting for spells like Bless based on `max_targets`

            if not targets_for_buff:
                 messages.append("No valid targets for the buff.")
                 return messages # Should not happen if self is default

            effect_details = spell_data.get("effect_details")
            if not effect_details:
                messages.append(f"No effect details defined for buff spell {spell_name}.")
                return messages

            duration_rounds = self.concentration.get("remaining_rounds", 0) if spell_data.get("requires_concentration") else 0
            if not spell_data.get("requires_concentration") and "duration" in spell_data: # Non-concentration timed buff
                 # Basic duration parsing if not concentration (e.g. "1 hour")
                duration_str = spell_data.get("duration", "0 rounds")
                if "minute" in duration_str: duration_rounds = int(duration_str.split(" minute")[0]) * 10
                elif "hour" in duration_str: duration_rounds = int(duration_str.split(" hour")[0]) * 600
                elif "round" in duration_str: duration_rounds = int(duration_str.split(" round")[0])


            for target in targets_for_buff: # Currently only one target unless expanded
                if hasattr(target, 'active_effects') and hasattr(target, 'add_effect'): # Check if target can receive effects
                    effect_to_apply = effect_details.copy()
                    effect_to_apply["source_caster_id"] = self.name # Or a unique ID
                    effect_to_apply["duration_rounds"] = duration_rounds
                    effect_to_apply["spell_id"] = spell_id # Link back to the spell

                    # For Bless, store who it applies to for concentration management
                    if spell_data.get("requires_concentration"):
                        if target.name not in self.concentration["target_ids"]: # Avoid duplicates
                            self.concentration["target_ids"].append(target.name) # Store by name for simplicity

                    target.add_effect(effect_name=effect_details["name"], effect_data=effect_to_apply)
                    messages.append(f"{target.name} is now affected by {effect_details['name']}.")
                else:
                    messages.append(f"Cannot apply buff to {target.name}.")

        elif spell_type == "utility_sense": # For spells like Detect Magic
            effect_details = spell_data.get("effect_details")
            if not effect_details:
                messages.append(f"No effect details defined for utility spell {spell_name}.")
                return messages

            # Apply to self
            effect_to_apply = effect_details.copy()
            effect_to_apply["source_caster_id"] = self.name
            effect_to_apply["duration_rounds"] = self.concentration.get("remaining_rounds", 0) if spell_data.get("requires_concentration") else 0
            if not spell_data.get("requires_concentration") and "duration" in spell_data:
                 duration_str = spell_data.get("duration", "0 rounds")
                 if "minute" in duration_str: effect_to_apply["duration_rounds"] = int(duration_str.split(" minute")[0].split("up to ")[-1]) * 10 # up to X minute(s)
                 elif "hour" in duration_str: effect_to_apply["duration_rounds"] = int(duration_str.split(" hour")[0].split("up to ")[-1]) * 600
                 elif "round" in duration_str: effect_to_apply["duration_rounds"] = int(duration_str.split(" round")[0].split("up to ")[-1])

            self.add_effect(effect_name=effect_details.get("name", spell_name), effect_data=effect_to_apply)
            messages.append(f"You are now under the effect of {effect_details.get('name', spell_name)}.")
            # Actual mechanics of SENSE_MAGIC etc. would be polled by relevant commands/systems.

        elif spell_type == "single_target_save_condition": # For Charm Person
            if not target_mob or not hasattr(target_mob, 'is_alive') or not target_mob.is_alive():
                return ["You need a living target for this spell."]
            # TODO: Add target_type check (e.g., "humanoid") from spell_data

            save_dc = self.get_spell_save_dc()
            save_stat = spell_data.get("save_stat", "WIS").upper()
            effect_on_fail = spell_data.get("effect_on_fail")

            target_save_bonus = target_mob.get_saving_throw_bonus(save_stat) if hasattr(target_mob, 'get_saving_throw_bonus') else 0

            # Handle save advantage for Charm Person if target is hostile
            adv_for_save = False
            if spell_data.get("save_advantage_condition") == "target_is_hostile_or_in_combat_with_caster_allies":
                if target_mob.in_combat and (target_mob.target == self or (target_mob.target and target_mob.target.user in self.user.get_allies() ) ): # Simplified: needs party/ally system
                    adv_for_save = True
                    messages.append(f"({target_mob.name} gets advantage on the save as you are fighting it!)")

            save_roll, _ = roll_d20_with_advantage_disadvantage(advantage=adv_for_save) # Target gets advantage
            total_save_roll = save_roll + target_save_bonus

            messages.append(f"{target_mob.name} attempts a {save_stat} save (DC {save_dc}): rolled {save_roll} + {target_save_bonus} = {total_save_roll}.")
            if total_save_roll >= save_dc:
                messages.append(f"{target_mob.name} succeeds on the save and is unaffected.")
            else:
                messages.append(f"{target_mob.name} {ANSI_RED}fails the save!{ANSI_RESET}")
                if effect_on_fail and effect_on_fail.get("type") == "APPLY_CONDITION":
                    condition_name = effect_on_fail.get("condition")
                    # Duration parsing for "1 hour"
                    duration_hours = effect_on_fail.get("duration_hours", 0)
                    cond_duration_rounds = duration_hours * 600 # 1 hour = 600 rounds (6s/round * 10round/min * 60min/hr)

                    if hasattr(target_mob, 'add_condition') and condition_name:
                        # Pass additional details for Charmed condition if needed
                        condition_details_for_add = {"source": spell_name}
                        if effect_on_fail.get("charmed_by_caster_id"):
                             condition_details_for_add["charmed_by_caster_name"] = self.name # Store who charmed it
                        if effect_on_fail.get("end_condition_on_harm"):
                             condition_details_for_add["end_on_harm_from_caster_allies"] = True

                        target_mob.add_condition(condition_name, duration_rounds=cond_duration_rounds, **condition_details_for_add)
                        messages.append(f"{target_mob.name} is now {condition_name} by you!")
            # Handle multi-target for higher levels
            # TODO: Implement target selection for additional targets if actual_cast_level > base_spell_level


        elif spell_type == "auto_hit_damage":
            if not target_mob: # Requires at least one target
                # Could potentially target self if spell allows, but Magic Missile doesn't.
                messages.append(f"Spell {spell_name} requires a target.")
                return messages # Or don't spend slot - this needs careful review of when slot is spent vs target validation.

            num_missiles = spell_data.get("num_missiles_base", 1)
            if actual_cast_level > base_spell_level:
                num_extra_missiles_per_level = spell_data.get("num_missiles_per_level_above_base", 0)
                num_missiles += (actual_cast_level - base_spell_level) * num_extra_missiles_per_level

            damage_per_missile_str = spell_data.get("damage_dice_per_missile", "0")
            damage_type = spell_data.get("damage_type", "unknown")

            # Simplified: all missiles hit the single target_mob for now.
            # TODO: Implement logic for distributing missiles among multiple targets if desired by player.
            total_damage_this_spell = 0
            for i in range(num_missiles):
                missile_damage = roll_dice(damage_per_missile_str)
                total_damage_this_spell += missile_damage
                messages.append(f"A missile hits {target_mob.name} for {ANSI_RED}{missile_damage}{ANSI_RESET} {damage_type} damage.")

            if total_damage_this_spell > 0 and hasattr(target_mob, 'take_damage'):
                target_mob.take_damage(total_damage_this_spell, attacker=self, damage_type=damage_type)
                if not target_mob.is_alive():
                    messages.append(f"{ANSI_GREEN}{target_mob.name} has been defeated!{ANSI_RESET}")
            elif total_damage_this_spell == 0:
                 messages.append("The missiles deal no damage.")


        else:
            messages.append(f"Spell type '{spell_type}' handling not yet implemented.")

        return messages


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
        return self.current_hp > 0 and not self.has_condition(Player.CONDITION_PETRIFIED) # Petrified characters are objects

    def take_damage(self, amount, attacker=None, damage_type="unknown"):
        if not self.is_alive(): return # Cannot damage what is already dead or petrified

        actual_damage_taken = amount

        # Account for resistances, vulnerabilities, and immunities
        if damage_type in self.immunities:
            actual_damage_taken = 0
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"{ANSI_GREEN}You are immune to {damage_type}! No damage taken.{ANSI_RESET}")
            # Early exit if immune, unless there's a reason to continue (e.g. "still takes X effect on immune")
            # For now, immunity means no damage and no further processing of this damage instance.
            # However, other effects from the same attack might still apply if handled separately.
            if actual_damage_taken == 0: # If immunity made it zero
                 # We might still want to record the "hit" for 0 damage for some log/trigger purposes
                 # but the player's HP doesn't change.
                 # If there are on-hit effects that bypass immunity (rare), they'd need special handling.
                 return # Exit if immune and damage is zeroed.

        if damage_type in self.vulnerabilities: # Apply vulnerability first as per some D&D rulings
            actual_damage_taken = math.floor(actual_damage_taken * 2) # Or actual_damage_taken *= 2
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"{ANSI_RED}You are vulnerable to {damage_type}! Damage increased!{ANSI_RESET}")

        if damage_type in self.resistances:
            actual_damage_taken = math.floor(actual_damage_taken / 2)
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"{ANSI_YELLOW}You resist {damage_type}! Damage halved.{ANSI_RESET}")


        # Temporary HP is lost first
        if self.temporary_hp > 0:
            if actual_damage_taken <= self.temporary_hp:
                self.temporary_hp -= actual_damage_taken
                actual_damage_taken = 0
            else:
                actual_damage_taken -= self.temporary_hp
                self.temporary_hp = 0

        if actual_damage_taken > 0:
            self.current_hp -= actual_damage_taken

        # Send damage message to player
        if hasattr(self.user, 'send_message'):
            attacker_name = attacker.name if attacker and hasattr(attacker, 'name') else "something"
            self.user.send_message(f"{ANSI_RED}You take {amount} {damage_type} damage from {attacker_name}! (Reduced to {actual_damage_taken} after temp HP and resistances){ANSI_RESET}")

        if self.current_hp <= 0 and actual_damage_taken > 0 : # Only trigger if actual damage was dealt and HP is 0 or less
            # Check for Relentless Endurance before calling handle_death
            relentless_endurance_used_this_time = False
            for triggered_ability in self.triggered_abilities_effects:
                if triggered_ability.get("name") == "Relentless Endurance" and \
                   triggered_ability.get("trigger_condition") == "on_reduce_to_zero_hp_not_killed_outright":
                    # Check if the ability can be used (uses, refresh)
                    if self.can_use_ability("Relentless Endurance"):
                        if self.mark_ability_used("Relentless Endurance"):
                            hp_to_set = triggered_ability.get("effect_details", {}).get("value", 1)
                            self.current_hp = hp_to_set
                            if hasattr(self.user, 'send_message'):
                                self.user.send_message(f"{ANSI_GREEN}Relentless Endurance kicks in! You drop to {self.current_hp} HP instead of falling unconscious!{ANSI_RESET}")
                            relentless_endurance_used_this_time = True
                            break # Relentless Endurance used

            if not relentless_endurance_used_this_time:
                self.current_hp = 0
                self.handle_death(attacker)
        elif self.current_hp <= 0 and not self.is_dead : # HP is 0 but no damage was taken (e.g. effect set HP to 0)
            self.handle_death(attacker)


    def handle_death(self, killer=None):
        if self.is_dead: # Already processed death
            return

        self.is_dead = True
        self.current_hp = 0 # Ensure HP is 0
        self.in_combat = False

        # Clear target from the mob's perspective if the mob was targeting this player
        if self.target and hasattr(self.target, 'target') and self.target.target == self:
            self.target.target = None
            self.target.in_combat = False # Mob should leave combat if its target dies

        self.target = None # Clear player's target

        killer_name = "unknown causes"
        if killer:
            killer_name = killer.name if hasattr(killer, 'name') else str(killer)

        print(f"[INFO] Player {self.name} has died (killed by {killer_name}).")

        death_messages = [
            f"{ANSI_RED}Darkness envelops you as your life force fades away... You have been slain by {killer_name}.{ANSI_RESET}",
            f"{ANSI_RED}A final, ragged breath escapes your lips. {killer_name} stands victorious over your fallen form.{ANSI_RESET}",
            f"{ANSI_RED}Your vision blurs and the world spins... {killer_name}'s blow was fatal.{ANSI_RESET}",
            f"{ANSI_RED}You have fallen in battle, your spirit torn from its mortal shell by {killer_name}.{ANSI_RESET}",
            f"{ANSI_RED}The cold grip of death takes you. Your journey ends here, thanks to {killer_name}.{ANSI_RESET}"
        ]
        message_to_send = random.choice(death_messages)
        if hasattr(self.user, 'send_message'):
            self.user.send_message(message_to_send)
            self.user.send_message(f"{ANSI_YELLOW}Your soul lingers. Type 'respawn' to return to the Church of Testing, or 'wait' to await help (you will automatically respawn after 5 minutes if no help arrives). Type 'quit' to embrace the void.{ANSI_RESET}")

    def attempt_respawn(self):
        if not self.is_dead:
            if hasattr(self.user, 'send_message'):
                self.user.send_message("You are already among the living!")
            return False

        if hasattr(self.user, 'send_message'):
            self.user.send_message(f"{ANSI_YELLOW}You feel a pull back to the mortal coil. Do you wish to respawn at the Church of Testing? (yes/no){ANSI_RESET}")

        response = None
        if hasattr(self.user, 'read_line'):
            response = self.user.read_line() # This assumes TempUser has read_line

        if response and response.strip().lower() == "yes":
            self.is_dead = False
            self.current_hp = max(1, self.max_hp // 4)
            self.room_id = "start" # Respawn to the starting room (Church of Testing)
            self.in_combat = False # Explicitly clear combat state on respawn
            self.target = None     # Explicitly clear target on respawn

            resurrection_messages = [
                f"{ANSI_GREEN}A divine light envelops you, and you feel warmth return to your limbs! You find yourself in a holy place.{ANSI_RESET}",
                f"{ANSI_GREEN}You gasp as life surges back into your form, the spectral cold receding. You are alive!{ANSI_RESET}",
                f"{ANSI_GREEN}With a shudder, your spirit reattaches to your form. You awaken, weakened but alive, in the Church of Testing.{ANSI_RESET}"
            ]
            if hasattr(self.user, 'send_message'):
                self.user.send_message(random.choice(resurrection_messages))
            return True
        else:
            if hasattr(self.user, 'send_message'):
                self.user.send_message(f"{ANSI_YELLOW}You decide to linger in the spirit world a while longer.{ANSI_RESET}")
            return False

    def add_item_to_inventory(self, item_instance_or_dict):
        self.inventory.append(item_instance_or_dict)
        name_to_show = "item"
        if hasattr(item_instance_or_dict, 'item_blueprint'):
            name_to_show = item_instance_or_dict.item_blueprint.name
        elif isinstance(item_instance_or_dict, dict):
            name_to_show = item_instance_or_dict.get("name", "item")
        return f"You pick up {name_to_show}."

    def remove_item_from_inventory(self, item_name_or_id, quantity=1):
        item_to_remove_idx = -1
        item_instance_found = None
        for i, inst in enumerate(self.inventory):
            current_item_name = ""; current_item_id = ""
            if hasattr(inst, 'item_blueprint'):
                current_item_name = inst.item_blueprint.name.lower()
                current_item_id = inst.item_blueprint.id.lower()
            elif isinstance(inst, dict):
                current_item_name = inst.get("name", "").lower()
                current_item_id = inst.get("id", "").lower()
            if current_item_name == item_name_or_id.lower() or current_item_id == item_name_or_id.lower():
                item_to_remove_idx = i
                item_instance_found = inst
                break
        if item_instance_found:
            self.inventory.pop(item_to_remove_idx)
            return item_instance_found
        return f"You don't have '{item_name_or_id}'."

    def get_attack_details(self):
        attack_stat = "STR"; damage_dice = "1d4"; damage_type = "bludgeoning"
        weapon = self.equipment.get(Player.EQUIPMENT_SLOT_WEAPON_MAIN)
        is_proficient = True
        weapon_category = "melee" # Default to melee (e.g. unarmed)
        if weapon:
            props = weapon.get("properties", {})
            damage_dice = props.get("damage_dice", damage_dice)
            damage_type = props.get("damage_type", damage_type)
            weapon_category = props.get("category", "melee") # Get category, default melee

            if props.get("finesse"):
                if self.get_stat_score("DEX") > self.get_stat_score("STR"):
                    attack_stat = "DEX"
            elif weapon_category == "ranged": # Ranged weapons typically use DEX unless they have a special property
                attack_stat = "DEX"
        else: # Unarmed strike
            attack_stat = "STR" # Default for unarmed
            if self.player_class_name == "Monk" and self.level > 0:
                # Monk unarmed strikes can use DEX
                if self.get_stat_score("DEX") > self.get_stat_score("STR"):
                    attack_stat = "DEX"
                # Monk damage dice scaling
                if self.level < 5: damage_dice = "1d4"
                elif self.level < 11: damage_dice = "1d6"
                elif self.level < 17: damage_dice = "1d8"
                else: damage_dice = "1d10"
                if self.get_stat_score("DEX") > self.get_stat_score("STR"):
                    attack_stat = "DEX"
            is_proficient = True
        attack_bonus_mod = self.get_stat_modifier(attack_stat)
        attack_bonus = attack_bonus_mod
        if is_proficient: attack_bonus += self.proficiency_bonus

        # Apply Archery fighting style bonus
        if "Archery" in self.fighting_styles and weapon_category == "ranged":
            attack_bonus += 2

        return {
            "attack_bonus": attack_bonus,
            "damage_dice": damage_dice,
            "damage_type": damage_type,
            "stat_modifier": attack_bonus_mod,
            "weapon_category": weapon_category
        }
