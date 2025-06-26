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

def resolve_attack(attacker, defender):
    """
    Resolves an attack from attacker to defender.
    Returns a list of messages describing the outcome.
    """
    messages = []
    if not attacker or not defender:
        messages.append("Debug: Attacker or defender is missing.")
        return messages

    # Get attacker's details
    attack_bonus = 0
    damage_dice_str = "1d4" # Default unarmed
    damage_type = "bludgeoning"
    attack_stat_mod = 0
    crit_range = [20] # Standard critical hit range

    if hasattr(attacker, 'get_attack_details'): # Player
        attack_details = attacker.get_attack_details()
        attack_bonus = attack_details["attack_bonus"]
        damage_dice_str = attack_details["damage_dice"]
        damage_type = attack_details["damage_type"]
        attack_stat_mod = attack_details["stat_modifier"] # For damage bonus
        # TODO: Add crit_range to attack_details if player has features that expand it
    elif hasattr(attacker, 'attack_bonus') and hasattr(attacker, 'damage_dice'): # Mob
        attack_bonus = attacker.attack_bonus
        damage_dice_str = attacker.damage_dice # Mobs use damage_dice directly
        damage_type = getattr(attacker, 'damage_type', 'physical') # Default if not specified
        # Mobs typically don't add stat mod to damage unless it's part of their damage_dice string or flat value
    else:
        messages.append(f"Debug: {attacker.name} has no means to attack.")
        return messages

    # Get defender's AC
    defender_ac = getattr(defender, 'ac', 10) # Default AC if not specified

    # Attack roll
    roll = random.randint(1, 20)
    total_attack_roll = roll + attack_bonus

    is_critical_hit = (roll in crit_range)
    is_critical_miss = (roll == 1) # Natural 1 is always a miss for attacks

    messages.append(f"{attacker.name} attacks {defender.name} (Roll: {roll} + Bonus: {attack_bonus} = {total_attack_roll} vs AC: {defender_ac})")

    if is_critical_miss:
        messages.append(f"{ANSI_RED}Critical Miss!{ANSI_RESET} {attacker.name} misses {defender.name} spectacularly.")
        return messages

    if total_attack_roll >= defender_ac or is_critical_hit: # Hit
        damage = roll_dice(damage_dice_str)

        # Add stat modifier to damage for players if applicable (usually STR or DEX for melee/finesse/ranged)
        # Mobs typically have this baked into their damage_dice or have a flat damage value.
        if hasattr(attacker, 'get_attack_details'): # Player
            damage += attack_stat_mod

        if is_critical_hit:
            messages.append(f"{ANSI_YELLOW}Critical Hit!{ANSI_RESET}")
            # For D&D 5e style crits, roll damage dice twice
            # This means rolling the dice part of damage_dice_str again and adding it.
            # The modifier is only added once.
            crit_damage_bonus = roll_dice(damage_dice_str.split('+')[0].split('-')[0]) # Roll only the XdY part
            damage += crit_damage_bonus
            messages.append(f"Extra critical damage: {crit_damage_bonus}!")

        damage = max(0, damage) # Ensure damage is not negative

        messages.append(f"{attacker.name} hits {defender.name} for {ANSI_RED}{damage}{ANSI_RESET} {damage_type} damage.")

        if hasattr(defender, 'take_damage'):
            defender.take_damage(damage, attacker) # Pass attacker for aggro/credit
            if not defender.is_alive():
                messages.append(f"{ANSI_GREEN}{defender.name} has been defeated!{ANSI_RESET}")
                # Death handling (XP, loot, etc.) is usually managed by the game loop or calling function
                # after resolve_attack returns.
        else:
            messages.append(f"Debug: {defender.name} cannot take damage.")
    else: # Miss
        messages.append(f"{attacker.name} misses {defender.name}.")

    return messages
