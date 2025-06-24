import json
import os

MOBS_FILE = "server/data/mobs.json"
ITEMS_FILE = "server/data/items.json"

EQUIP_SLOTS = [
    "Head", "Neck", "Back", "Shoulders", "Chest", "Wrists", "Hands",
    "Ring Left", "Ring Right", "Legs", "Feet", "Relic", "Light Source",
    "Main Hand", "Off Hand"
]

class Mob:
    def __init__(self, mob_id, name, hp, attack, description):
        self.id = mob_id
        self.name = name
        self.hp = hp
        self.attack = attack
        self.description = description

    @staticmethod
    def load_mobs():
        if not os.path.exists(MOBS_FILE):
            return {}
        with open(MOBS_FILE, "r") as f:
            data = json.load(f)
        mobs = {}
        for mob_id, mob_data in data.items():
            mobs[mob_id] = Mob(
                mob_id,
                mob_data.get("name", mob_id),
                mob_data.get("hp", 10),
                mob_data.get("attack", 1),
                mob_data.get("description", "An unremarkable creature.")
            )
        return mobs

class MobInstance:
    def __init__(self, mob_blueprint: Mob, quantity=1, current_hp=None):
        self.mob_blueprint = mob_blueprint
        self.quantity = quantity
        self.current_hp = current_hp if current_hp is not None else mob_blueprint.hp

    def is_alive(self):
        return self.current_hp > 0

    def take_damage(self, amount):
        self.current_hp = max(0, self.current_hp - amount)

    def __repr__(self):
        return f"<MobInstance {self.mob_blueprint.name} x{self.quantity} HP:{self.current_hp}>"

class Item:
    def __init__(self, item_id, name, item_type, effects, description,
                 weight=0.0, equip_slot=None, container_capacity=0):
        self.id = item_id
        self.name = name
        self.type = item_type
        self.effects = effects
        self.description = description
        self.weight = weight
        self.equip_slot = equip_slot if equip_slot in EQUIP_SLOTS else None
        self.container_capacity = container_capacity  # max weight if container

    @staticmethod
    def load_items():
        if not os.path.exists(ITEMS_FILE):
            return {}
        with open(ITEMS_FILE, "r") as f:
            data = json.load(f)
        items = {}
        for item_id, item_data in data.items():
            items[item_id] = Item(
                item_id,
                item_data.get("name", item_id),
                item_data.get("type", "misc"),
                item_data.get("effects", {}),
                item_data.get("description", ""),
                item_data.get("weight", 0.0),
                item_data.get("equip_slot"),
                item_data.get("container_capacity", 0)
            )
        return items

class ItemInstance:
    def __init__(self, item_blueprint: Item, quantity=1):
        self.item_blueprint = item_blueprint
        self.quantity = quantity

    def total_weight(self):
        return self.quantity * self.item_blueprint.weight

    def use(self):
        if self.quantity > 0:
            self.quantity -= 1
            return True
        return False

    def __repr__(self):
        return f"<ItemInstance {self.item_blueprint.name} x{self.quantity}>"

class ContainerInstance(ItemInstance):
    def __init__(self, item_blueprint: Item, quantity=1):
        super().__init__(item_blueprint, quantity)
        self.contents = []

    def current_capacity_used(self):
        return sum(item.total_weight() for item in self.contents)

    def add_item(self, item_instance):
        if self.item_blueprint.container_capacity > 0:
            if self.current_capacity_used() + item_instance.total_weight() > self.item_blueprint.container_capacity:
                return False  # too heavy
        for existing in self.contents:
            if (existing.item_blueprint.id == item_instance.item_blueprint.id
                and not hasattr(existing, 'contents')):
                existing.quantity += item_instance.quantity
                return True
        self.contents.append(item_instance)
        return True

    def remove_item(self, item_name, quantity=1):
        for i, item in enumerate(self.contents):
            if item.item_blueprint.name.lower() == item_name.lower():
                if item.quantity >= quantity:
                    item.quantity -= quantity
                    if item.quantity <= 0:
                        return self.contents.pop(i)
                    return ItemInstance(item.item_blueprint, quantity)
        return None

    def list_contents(self, depth=0):
        lines = []
        prefix = "  " * depth
        for item in self.contents:
            line = f"{prefix}- {item.item_blueprint.name} x{item.quantity}"
            lines.append(line)
            if hasattr(item, 'contents'):
                lines += item.list_contents(depth + 1)
        return lines

    def __repr__(self):
        return f"<ContainerInstance {self.item_blueprint.name} x{self.quantity} [{len(self.contents)} items]>"
