import json
from server.core.content import ItemInstance, ContainerInstance

class Player:
    def __init__(self, name, conn, room, inventory=None):
        self.name = name
        self.conn = conn
        self.room = room
        self.inventory = inventory if inventory is not None else []

    def send(self, text):
        try:
            self.conn.sendall(text.encode())
        except:
            pass

    def send_line(self, text):
        self.send(text + "\r\n")

    def read_line(self):
        buffer = ""
        while True:
            try:
                char = self.conn.recv(1).decode(errors='ignore')
                if not char:
                    return None
                if char in ['\n', '\r']:
                    break
                buffer += char
            except:
                return None
        return buffer.strip()

    def look(self):
        self.send_line(f"\r\n{self.room.description}")

        # Show mobs in room
        if self.room.mob_instances:
            self.send_line("\r\nCreatures here:")
            for mob in self.room.mob_instances:
                self.send_line(f" - {mob.mob_blueprint.name} x{mob.quantity}")

        # Show items in room
        if self.room.item_instances:
            self.send_line("\r\nItems on the ground:")
            for item in self.room.item_instances:
                name = item.item_blueprint.name
                qty = item.quantity
                if hasattr(item, 'contents'):
                    self.send_line(f" - {name} x{qty} (container with {len(item.contents)} items)")
                else:
                    self.send_line(f" - {name} x{qty}")

        # Show exits
        if self.room.exits:
            exits = ", ".join(self.room.exits.keys())
            self.send_line(f"\r\nExits: {exits}")

    # Inventory management

    def add_item(self, item_instance):
        for inv_item in self.inventory:
            if (inv_item.item_blueprint.id == item_instance.item_blueprint.id
                and not hasattr(inv_item, 'contents')):
                inv_item.quantity += item_instance.quantity
                return
        self.inventory.append(item_instance)

    def remove_item(self, item_id, quantity=1):
        for inv_item in self.inventory:
            if inv_item.item_blueprint.id == item_id:
                if inv_item.quantity >= quantity:
                    inv_item.quantity -= quantity
                    if inv_item.quantity <= 0:
                        self.inventory.remove(inv_item)
                    return True
        return False

    def list_inventory(self):
        if not self.inventory:
            self.send_line("Your inventory is empty.")
            return
        self.send_line("Your inventory contains:")
        for idx, inv_item in enumerate(self.inventory, start=1):
            name = inv_item.item_blueprint.name
            qty = inv_item.quantity
            if hasattr(inv_item, 'contents'):
                self.send_line(f"{idx}. {name} x{qty} (container with {len(inv_item.contents)} items)")
            else:
                self.send_line(f"{idx}. {name} x{qty}")

    def save_inventory(self):
        def serialize_item(inst):
            data = {
                "item_id": inst.item_blueprint.id,
                "quantity": inst.quantity
            }
            if hasattr(inst, 'contents'):
                data["contents"] = [serialize_item(c) for c in inst.contents]
            return data

        return [serialize_item(i) for i in self.inventory]

    def load_inventory(self, data, items_dict):
        def deserialize_item(d):
            blueprint = items_dict.get(d["item_id"])
            if not blueprint:
                return None
            if "contents" in d:
                container = ContainerInstance(blueprint, d["quantity"])
                for c in d["contents"]:
                    ci = deserialize_item(c)
                    if ci:
                        container.add_item(ci)
                return container
            else:
                return ItemInstance(blueprint, d["quantity"])

        self.inventory = []
        for item_data in data:
            inst = deserialize_item(item_data)
            if inst:
                self.inventory.append(inst)

    # === New Container Commands ===

    def find_inventory_item(self, name):
        for item in self.inventory:
            if item.item_blueprint.name.lower() == name.lower():
                return item
        return None

    def put_item_into_container(self, item_name, container_name):
        item = self.find_inventory_item(item_name)
        container = self.find_inventory_item(container_name)
        if not item:
            self.send_line(f"You don't have an item named '{item_name}'.")
            return
        if not container or not isinstance(container, ContainerInstance):
            self.send_line(f"You don't have a container named '{container_name}'.")
            return
        if item == container:
            self.send_line("You can't put a container inside itself.")
            return

        # Remove one from inventory and put into container
        if item.quantity <= 0:
            self.send_line(f"You have no {item_name} left.")
            return

        item.quantity -= 1
        container.add_item(ItemInstance(item.item_blueprint, 1))
        self.send_line(f"You place one {item.item_blueprint.name} into the {container.item_blueprint.name}.")

        if item.quantity == 0:
            self.inventory.remove(item)

    def take_item_from_container(self, item_name, container_name):
        container = self.find_inventory_item(container_name)
        if not container or not isinstance(container, ContainerInstance):
            self.send_line(f"You don't have a container named '{container_name}'.")
            return
        taken = container.remove_item(item_name)
        if taken:
            self.add_item(taken)
            self.send_line(f"You take the {item_name} out of the {container.item_blueprint.name}.")
        else:
            self.send_line(f"The {container.item_blueprint.name} doesn't contain any '{item_name}'.")

    def inspect_container(self, container_name):
        container = self.find_inventory_item(container_name)
        if not container or not isinstance(container, ContainerInstance):
            self.send_line(f"You don't have a container named '{container_name}'.")
            return
        self.send_line(f"\r\nContents of {container.item_blueprint.name}:")
        if not container.contents:
            self.send_line(" - (empty)")
            return
        for item in container.contents:
            line = f" - {item.item_blueprint.name} x{item.quantity}"
            if hasattr(item, "contents"):
                line += f" (container with {len(item.contents)} items)"
            self.send_line(line)
