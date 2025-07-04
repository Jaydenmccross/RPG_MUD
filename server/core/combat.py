import random

# ANSI Color Codes (consistent with player.py and main.py)
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_BLUE = "\033[94m"
ANSI_RESET = "\033[0m"

def roll_dice(dice_string):
    """
    Rolls dice based on a string like "XdY[+/-Z]" or a flat number.
    Examples: "1d6", "2d4+1", "10".
    Returns the total result of the roll.
    """
    if not isinstance(dice_string, str): # If it's already a number (e.g. flat damage for mobs)
        try: return int(dice_string)
        except ValueError: print(f"Error: Invalid flat damage value: {dice_string}"); return 0

    dice_string = dice_string.replace(" ", "")
    parts = dice_string.split('d')
    num_dice = 1
    modifier = 0

    if len(parts) == 1: # Flat number, e.g., "10" or "5+1"
        if '+' in parts[0]:
            val_part, mod_part = parts[0].split('+')
            try: base_val = int(val_part); modifier = int(mod_part)
            except ValueError: print(f"Error: Invalid dice string format for flat number with modifier: {dice_string}"); return 0
            return base_val + modifier
        elif '-' in parts[0]:
            val_part, mod_part = parts[0].split('-')
            try: base_val = int(val_part); modifier = -int(mod_part)
            except ValueError: print(f"Error: Invalid dice string format for flat number with modifier: {dice_string}"); return 0
            return base_val + modifier
        else:
            try: return int(parts[0])
            except ValueError: print(f"Error: Invalid dice string format for flat number: {dice_string}"); return 0

    try: num_dice = int(parts[0])
    except ValueError: print(f"Error: Invalid number of dice: {parts[0]} in {dice_string}"); return 0

    dice_sides_part = parts[1]
    if '+' in dice_sides_part:
        sub_parts = dice_sides_part.split('+')
        try: dice_sides = int(sub_parts[0]); modifier = int(sub_parts[1])
        except ValueError: print(f"Error: Invalid dice sides/modifier: {dice_sides_part} in {dice_string}"); return 0
    elif '-' in dice_sides_part:
        sub_parts = dice_sides_part.split('-')
        try: dice_sides = int(sub_parts[0]); modifier = -int(sub_parts[1])
        except ValueError: print(f"Error: Invalid dice sides/modifier: {dice_sides_part} in {dice_string}"); return 0
    else:
        try: dice_sides = int(dice_sides_part)
        except ValueError: print(f"Error: Invalid dice sides: {dice_sides_part} in {dice_string}"); return 0

    if num_dice <= 0 or dice_sides <= 0: print(f"Error: Number of dice and sides must be positive: {dice_string}"); return 0

    total_roll = sum(random.randint(1, dice_sides) for _ in range(num_dice))
    return total_roll + modifier

def roll_d20_with_advantage_disadvantage(advantage=False, disadvantage=False):
    """Rolls a d20, applying advantage or disadvantage if specified."""
    roll1 = random.randint(1, 20)
    if advantage and disadvantage: # If both, they cancel out
        return roll1, "normal"
    if advantage:
        roll2 = random.randint(1, 20)
        return max(roll1, roll2), "advantage"
    if disadvantage:
        roll2 = random.randint(1, 20)
        return min(roll1, roll2), "disadvantage"
    return roll1, "normal"

def resolve_attack(attacker, defender,
                   attack_bonus_override=None,
                   damage_dice_override=None,
                   damage_type_override=None,
                   attack_stat_mod_override=None):
    """
    Resolves an attack from attacker to defender.
    Can use override parameters for spell attacks or special abilities.
    Returns a list of messages describing the outcome.
    """
    messages = []
    if not attacker or not defender:
        messages.append("Debug: Attacker or defender is missing.")
        return messages

    # Determine crit range from attacker, default to [20] if not specified
    crit_range = getattr(attacker, 'crit_range', [20])

    # Determine attack parameters
    if attack_bonus_override is not None: # Spell/ability attack
        attack_bonus = attack_bonus_override
        damage_dice_str = damage_dice_override if damage_dice_override is not None else "1d4" # Default if not provided
        damage_type = damage_type_override if damage_type_override is not None else "unknown"
        # For spells, attack_stat_mod_override is the mod to add to damage (often 0 for cantrips)
        attack_stat_mod_for_damage = attack_stat_mod_override if attack_stat_mod_override is not None else 0
        is_spell_attack = True
    else: # Standard weapon attack
        is_spell_attack = False
        if hasattr(attacker, 'get_attack_details'): # Player weapon attack
            attack_details = attacker.get_attack_details()
            attack_bonus = attack_details["attack_bonus"]
            damage_dice_str = attack_details["damage_dice"]
            damage_type = attack_details["damage_type"]
            attack_stat_mod_for_damage = attack_details["stat_modifier"]
        elif hasattr(attacker, 'attack_bonus') and hasattr(attacker, 'damage_dice'): # Mob attack
            attack_bonus = attacker.attack_bonus
            damage_dice_str = attacker.damage_dice
            damage_type = getattr(attacker, 'damage_type', 'physical')
            attack_stat_mod_for_damage = 0 # Mobs usually have full damage in dice_string
        else:
            messages.append(f"Debug: {attacker.name} has no means to attack.")
            return messages

    # Get defender's AC
    defender_ac = getattr(defender, 'ac', 10) # Default AC if not specified

    # Attack roll
    # Determine if attacker has advantage or disadvantage
    # TODO: This logic will become much more complex based on conditions, features, spells.
    has_advantage = False
    has_disadvantage = False

    # --- Reckless Attack Advantage for Attacker ---
    if hasattr(attacker, 'is_reckless_attacking_this_turn') and attacker.is_reckless_attacking_this_turn:
        # Reckless Attack applies to melee weapon attacks using Strength.
        # Assuming 'is_spell_attack' is False for weapon attacks.
        # And 'attack_details' (from get_attack_details) would contain 'attack_ability_stat' for players.
        is_melee_strength_attack = False
        if not is_spell_attack and hasattr(attacker, 'get_attack_details'): # Player attacking
            attack_details_for_reckless = attacker.get_attack_details()
            if attack_details_for_reckless.get("weapon_category") == "melee" and \
               attack_details_for_reckless.get("attack_ability_stat") == "STR":
                is_melee_strength_attack = True

        if is_melee_strength_attack:
            has_advantage = True
            messages.append(f"{ANSI_YELLOW}(Attacking recklessly - Advantage!){ANSI_RESET}")

    # Attacker conditions
    if hasattr(attacker, 'has_condition'):
        if attacker.has_condition("Blinded"): has_disadvantage = True
        if attacker.has_condition("Frightened"): has_disadvantage = True # Simplified: assumes source is visible
        if attacker.has_condition("Poisoned"): has_disadvantage = True
        if attacker.has_condition("Prone"): has_disadvantage = True
        if attacker.has_condition("Restrained"): has_disadvantage = True

        if attacker.has_condition("Invisible") or attacker.has_condition("Hidden"):
            has_advantage = True
            if attacker.has_condition("Hidden") and hasattr(attacker, 'remove_condition'):
                attacker.remove_condition("Hidden")
                if hasattr(attacker, 'user') and hasattr(attacker.user, 'send_message'):
                    attacker.user.send_message(f"{ANSI_YELLOW}You are no longer hidden.{ANSI_RESET}")

    # Defender conditions that affect attacker's roll
    is_melee_attack = hasattr(attacker, 'weapon_category') and attacker.weapon_category == "melee" # Approx

    # --- Reckless Attack Advantage against Defender ---
    if hasattr(defender, 'reckless_attack_active_until_next_turn') and defender.reckless_attack_active_until_next_turn:
        has_advantage = True # Attacker gets advantage if defender was reckless
        messages.append(f"{ANSI_YELLOW}(Target was reckless - Advantage!){ANSI_RESET}")

    if hasattr(defender, 'has_condition'):
        if defender.has_condition("Blinded"): pass # Doesn't directly affect attacker's roll, but defender's attacks
        if defender.has_condition("Paralyzed"): has_advantage = True
        if defender.has_condition("Petrified"): has_advantage = True
        if defender.has_condition("Prone"):
            if is_melee_attack: has_advantage = True
            else: has_disadvantage = True # Ranged attacks
        if defender.has_condition("Restrained"): has_advantage = True
        if defender.has_condition("Stunned"): has_advantage = True
        if defender.has_condition("Unconscious"): has_advantage = True

        if defender.has_condition("Invisible") or defender.has_condition("Hidden"):
            # Attacking an unseen target (assuming attacker cannot see them)
            if not (hasattr(attacker, 'has_condition') and attacker.has_condition("Blinded")): # If attacker isn't also blind
                 has_disadvantage = True


    roll, roll_type_str = roll_d20_with_advantage_disadvantage(advantage=has_advantage, disadvantage=has_disadvantage)

    # Handle bonus dice from effects like Bless
    bonus_dice_value = 0
    if hasattr(attacker, 'get_bonus_dice_for_roll_type'):
        bonus_dice_list = attacker.get_bonus_dice_for_roll_type("attack")
        for dice_str in bonus_dice_list:
            bonus_dice_value += roll_dice(dice_str) # roll_dice is in this file

    total_attack_roll = roll + attack_bonus + bonus_dice_value

    is_critical_hit = (roll in crit_range) # Natural roll in crit_range (e.g. 20, or 19-20)

    # Check for auto-crit conditions (e.g., attacking a Paralyzed or Unconscious target from melee)
    if not is_critical_hit and is_melee_attack: # Only apply if not already a natural crit
        if hasattr(defender, 'has_condition') and \
           (defender.has_condition("Paralyzed") or defender.has_condition("Unconscious")):
            is_critical_hit = True # Auto-crit
            messages.append(f"{ANSI_YELLOW}Attacking a helpless target - it's a critical hit!{ANSI_RESET}")

    is_critical_miss = (roll == 1) # Natural 1 is always a miss for attacks (original d20 roll)

    roll_description = f"Roll: {roll}"
    if roll_type_str != "normal":
        roll_description += f" ({roll_type_str})"

    messages.append(f"{attacker.name} attacks {defender.name} ({roll_description} + Bonus: {attack_bonus} = {total_attack_roll} vs AC: {defender_ac})")

    if is_critical_miss and not is_critical_hit: # A nat 1 on an advantaged roll that also rolled a 20 should still be a crit hit.
        # However, 5e rules: "If the d20 roll for an attack is a 1, the attack misses regardless of any modifiers or the target's AC."
        # So a nat 1 is always a miss. A nat 20 is always a hit (and crit).
        messages.append(f"{ANSI_RED}Critical Miss! (Rolled a 1){ANSI_RESET} {attacker.name} misses {defender.name} spectacularly.")
        return messages

    if total_attack_roll >= defender_ac or is_critical_hit: # Hit
        damage = roll_dice(damage_dice_str)
        damage += attack_stat_mod_for_damage # Apply the determined stat mod for damage

        if is_critical_hit:
            messages.append(f"{ANSI_YELLOW}Critical Hit!{ANSI_RESET}")
            # For D&D 5e style crits, roll damage dice an additional time.
            # The attack_stat_mod_for_damage is only added once to the total.
            # So, we roll the dice part again and add it to the already calculated damage (which includes the first roll + modifier).

            # Extract only the dice part (e.g., "2d6" from "2d6+3")
            dice_only_str = damage_dice_str
            if '+' in dice_only_str: dice_only_str = dice_only_str.split('+')[0]
            if '-' in dice_only_str: dice_only_str = dice_only_str.split('-')[0]

            crit_damage_roll = roll_dice(dice_only_str)
            damage += crit_damage_roll
            messages.append(f"Standard critical damage dice roll: {crit_damage_roll}!")

            # Brutal Critical and similar features
            if hasattr(attacker, 'on_critical_hit_effects'):
                for crit_effect in attacker.on_critical_hit_effects:
                    if crit_effect.get("type") == "ADD_CRIT_DICE":
                        # Check weapon category if specified by the effect
                        weapon_cat_req = crit_effect.get("weapon_category")
                        attacker_weapon_cat = ""
                        if hasattr(attacker, 'get_attack_details') and not is_spell_attack: # Check if player and has weapon details
                            attacker_weapon_cat = attacker.get_attack_details().get("weapon_category", "unknown")

                        if not weapon_cat_req or weapon_cat_req == attacker_weapon_cat:
                            num_extra_dice = crit_effect.get("dice_count", 0)
                            # The dice type for Brutal Critical is the weapon's damage die.
                            # dice_only_str already holds this (e.g., "1d12", "2d6").
                            # We need to roll `num_extra_dice` of these.
                            brutal_crit_val = 0
                            if num_extra_dice > 0 and dice_only_str:
                                # If dice_only_str is "2d6", and num_extra_dice is 1, we roll "1d6" (one of the weapon's dice)
                                # If dice_only_str is "1d12", and num_extra_dice is 1, we roll "1d12"
                                # The PHB says "roll one additional weapon damage die". If weapon is 2d6, it means one d6.
                                # So we need to parse the weapon's individual die type.
                                weapon_die_type_for_brutal = dice_only_str # Default to full string if not XdY
                                if 'd' in dice_only_str:
                                    parts = dice_only_str.split('d')
                                    if len(parts) == 2: # Format like "1d12" or "2d6"
                                        weapon_die_type_for_brutal = f"1d{parts[1]}" # Take the "dY" part

                                for _ in range(num_extra_dice):
                                    brutal_crit_val += roll_dice(weapon_die_type_for_brutal)
                                if brutal_crit_val > 0:
                                    damage += brutal_crit_val
                                    messages.append(f"{ANSI_YELLOW}Brutal Critical! Extra {brutal_crit_val} damage from {num_extra_dice} additional {weapon_die_type_for_brutal} dice!{ANSI_RESET}")
                        else:
                            messages.append(f"(Brutal Critical effect did not apply due to weapon category mismatch: required {weapon_cat_req}, used {attacker_weapon_cat})")


        damage = max(0, damage) # Ensure damage is not negative

        messages.append(f"{attacker.name} hits {defender.name} for {ANSI_RED}{damage}{ANSI_RESET} {damage_type} damage.")

        if hasattr(defender, 'take_damage'):
            defender.take_damage(damage, attacker=attacker, damage_type=damage_type)
            if not defender.is_alive():
                messages.append(f"{ANSI_GREEN}{defender.name} has been defeated!{ANSI_RESET}")
                # Death handling (XP, loot, etc.) is usually managed by the game loop or calling function
                # after resolve_attack returns.
        else:
            messages.append(f"Debug: {defender.name} cannot take damage.")
    else: # Miss
        messages.append(f"{attacker.name} misses {defender.name}.")

    return messages
