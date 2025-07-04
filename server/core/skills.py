import random
from server.core.combat import roll_d20_with_advantage_disadvantage, ANSI_GREEN, ANSI_RED, ANSI_RESET, ANSI_YELLOW

# Could potentially move SKILL_TO_ABILITY_MAP here if it's primarily skill-related
# from server.core.player import Player

def resolve_skill_check(player, skill_name, dc, advantage=False, disadvantage=False, situational_bonus=0, situational_dc_adjustment=0,
                        check_type="Skill Check", target_description="the challenge", success_msg_player=None, failure_msg_player=None,
                        success_msg_room=None, failure_msg_room=None):
    """
    Resolves a skill check for a player.

    Args:
        player: The player instance making the check.
        skill_name (str): The name of the skill being used (e.g., "Stealth", "Athletics").
        dc (int): The base difficulty class for the check.
        advantage (bool): Whether the player has advantage on the roll.
        disadvantage (bool): Whether the player has disadvantage on the roll.
        situational_bonus (int): Any one-time bonus to this specific roll.
        situational_dc_adjustment (int): Any one-time adjustment to the DC for this check.
        check_type (str): A descriptive name for the type of check (e.g., "Stealth Check", "Athletics to Climb").
        target_description (str): A brief description of what is being attempted.
        success_msg_player (str): Custom message for player on success.
        failure_msg_player (str): Custom message for player on failure.
        success_msg_room (str): Custom message for room on success.
        failure_msg_room (str): Custom message for room on failure.

    Returns:
        dict: {
            "success": bool,
            "roll": int (the d20 roll),
            "bonus": int (player's skill bonus),
            "total_roll": int,
            "dc": int (final DC),
            "messages_player": list[str],
            "messages_room": list[str]
        }
    """
    if not hasattr(player, 'get_skill_bonus') or not hasattr(player, 'user') or not hasattr(player.user, 'send_message'):
        return {"success": False, "roll": 0, "bonus": 0, "total_roll": 0, "dc": dc,
                "messages_player": ["Error: Invalid player object for skill check."], "messages_room": []}

    skill_bonus = player.get_skill_bonus(skill_name)

    # TODO: Incorporate Bardic Inspiration or other consumable bonus dice here
    # For example, check player.active_effects for a buff that grants bonus dice to skill checks.
    # inspiration_die_val = 0
    # if player.has_bardic_inspiration_active_for_skill_check(skill_name): # Fictional method
    #    inspiration_die_val = player.use_bardic_inspiration_die() # Returns roll and consumes

    d20_roll, roll_type_str = roll_d20_with_advantage_disadvantage(advantage=advantage, disadvantage=disadvantage)

    total_roll = d20_roll + skill_bonus + situational_bonus
    final_dc = dc + situational_dc_adjustment

    success = total_roll >= final_dc

    # Construct messages
    messages_player = []
    messages_room = []

    roll_desc_player = f"{check_type} vs DC {final_dc} (Target: {target_description}):\n"
    roll_desc_player += f"  Your d20 roll: {d20_roll}"
    if roll_type_str != "normal":
        roll_desc_player += f" ({roll_type_str})"
    roll_desc_player += f"\n  Your {skill_name} bonus: +{skill_bonus}"
    if situational_bonus != 0:
        roll_desc_player += f"\n  Situational bonus: {'+' if situational_bonus > 0 else ''}{situational_bonus}"
    roll_desc_player += f"\n  Total: {total_roll}"
    messages_player.append(roll_desc_player)

    room_roll_desc = f"{player.name} attempts {check_type.lower()} ({target_description})."

    if success:
        messages_player.append(f"{ANSI_GREEN}Success!{ANSI_RESET} {success_msg_player or f'You succeed at {target_description}.'}")
        messages_room.append(f"{room_roll_desc} {ANSI_GREEN}They succeed!{ANSI_RESET} {success_msg_room or ''}")
    else:
        messages_player.append(f"{ANSI_RED}Failure.{ANSI_RESET} {failure_msg_player or f'You fail at {target_description}.'}")
        messages_room.append(f"{room_roll_desc} {ANSI_RED}They fail.{ANSI_RESET} {failure_msg_room or ''}")

    # Filter out empty room messages
    messages_room = [m.strip() for m in messages_room if m.strip()]

    return {
        "success": success,
        "roll": d20_roll,
        "bonus": skill_bonus,
        "total_roll": total_roll,
        "dc": final_dc,
        "messages_player": messages_player,
        "messages_room": messages_room
    }

[end of server/core/skills.py]
