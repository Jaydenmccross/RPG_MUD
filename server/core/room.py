import json
from server.core.content import MobInstance, ItemInstance

class Room:
    def __init__(self, room_id, name, description, exits, mob_instances=None, item_instances=None):
        self.id = room_id
        self.name = name
        self.description = description
        self.exits = exits
        self.mob_instances = mob_instances if mob_instances else []
        self.item_instances = item_instances if item_instances else []

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "exits": self.exits,
            # Save mobs as list of dicts with blueprint id, quantity, current_hp
            "mobs": [mob.to_dict() for mob in self.mob_instances],
            # Save items as list of dicts (including nested containers)
            "items": [item.to_dict() for item in self.item_instances]
        }

    @staticmethod
    def load_rooms(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        rooms = {}
        for room_id, room_data in data.items():
            mob_list = []
            for mob_data in room_data.get("mobs", []):
                mob_id = mob_data.get("id")
                quantity = mob_data.get("quantity", 1)
                current_hp = mob_data.get("current_hp")
                template = mobs.get(mob_id)
                if template:
                    mob_list.append(MobInstance(template, quantity, current_hp))

            item_list = []
            for item_data in room_data.get("items", []):
                # Recursive load for containers inside items
                def load_item_recursive(d):
                    template = items.get(d["item_id"] if "item_id" in d else d["id"])
                    if not template:
                        return None
                    quantity = d.get("quantity", 1)
                    if "contents" in d:
                        container = ContainerInstance(template, quantity)
                        for c in d["contents"]:
                            ci = load_item_recursive(c)
                            if ci:
                                container.add_item(ci)
                        return container
                    else:
                        return ItemInstance(template, quantity)

                inst = load_item_recursive(item_data)
                if inst:
                    item_list.append(inst)

            rooms[room_id] = Room(
                room_id,
                room_data.get("name", room_id),
                room_data.get("description", ""),
                room_data.get("exits", {}),
                mob_list,
                item_list
            )
        return rooms

    @staticmethod
    def save_rooms(rooms_dict, file_path):
        data = {room_id: room.to_dict() for room_id, room in rooms_dict.items()}
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
