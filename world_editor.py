import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

ITEMS_FILE = "server/data/items.json"

class ItemEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Item Editor")
        self.items = self.load_items()

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tabs = {}
        for category in ["Weapons", "Armor", "Consumables", "Containers", "Lights", "Misc"]:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=category)
            self.tabs[category] = frame

        self.build_item_form(self.tabs["Weapons"], "weapon")
        self.build_item_form(self.tabs["Armor"], "armor")
        self.build_item_form(self.tabs["Consumables"], "consumable")
        self.build_item_form(self.tabs["Containers"], "container")
        self.build_item_form(self.tabs["Lights"], "light")
        self.build_item_form(self.tabs["Misc"], "misc")

    def load_items(self):
        if not os.path.exists(ITEMS_FILE):
            return {}
        with open(ITEMS_FILE, "r") as f:
            return json.load(f)

    def save_items(self):
        try:
            with open(ITEMS_FILE, "w") as f:
                json.dump(self.items, f, indent=2)
            messagebox.showinfo("Saved", "Items saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save items:\n{e}")

    def build_item_form(self, frame, default_type):
        tk.Label(frame, text="Item ID:").grid(row=0, column=0, sticky="w")
        id_entry = tk.Entry(frame)
        id_entry.grid(row=0, column=1, sticky="ew")

        tk.Label(frame, text="Name:").grid(row=1, column=0, sticky="w")
        name_entry = tk.Entry(frame)
        name_entry.grid(row=1, column=1, sticky="ew")

        tk.Label(frame, text="Description:").grid(row=2, column=0, sticky="nw")
        desc_text = tk.Text(frame, height=3)
        desc_text.grid(row=2, column=1, sticky="ew")

        tk.Label(frame, text="Type:").grid(row=3, column=0, sticky="w")
        type_var = tk.StringVar(value=default_type)
        type_entry = tk.Entry(frame, textvariable=type_var)
        type_entry.grid(row=3, column=1, sticky="ew")

        tk.Label(frame, text="Weight:").grid(row=4, column=0, sticky="w")
        weight_entry = tk.Entry(frame)
        weight_entry.grid(row=4, column=1, sticky="ew")

        tk.Label(frame, text="Equip Slot (if applicable):").grid(row=5, column=0, sticky="w")
        equip_entry = tk.Entry(frame)
        equip_entry.grid(row=5, column=1, sticky="ew")

        tk.Label(frame, text="Capacity (if container):").grid(row=6, column=0, sticky="w")
        capacity_entry = tk.Entry(frame)
        capacity_entry.grid(row=6, column=1, sticky="ew")

        tk.Label(frame, text="Effects (JSON):").grid(row=7, column=0, sticky="nw")
        effects_text = tk.Text(frame, height=4)
        effects_text.grid(row=7, column=1, sticky="ew")

        save_button = tk.Button(frame, text="Save Item", command=lambda: self.save_item(
            id_entry.get(),
            name_entry.get(),
            desc_text.get("1.0", tk.END).strip(),
            type_var.get(),
            weight_entry.get(),
            equip_entry.get(),
            capacity_entry.get(),
            effects_text.get("1.0", tk.END).strip()
        ))
        save_button.grid(row=8, column=1, sticky="e", pady=5)

        frame.columnconfigure(1, weight=1)

    def save_item(self, item_id, name, description, item_type, weight, equip_slot, capacity, effects_json):
        if not item_id or not name:
            messagebox.showerror("Error", "Item ID and Name are required.")
            return

        try:
            weight = float(weight) if weight else 0.0
            capacity = float(capacity) if capacity else 0.0
            effects = json.loads(effects_json) if effects_json else {}
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input:\n{e}")
            return

        self.items[item_id] = {
            "name": name,
            "description": description,
            "type": item_type,
            "weight": weight,
            "equip_slot": equip_slot,
            "capacity": capacity,
            "effects": effects
        }

        self.save_items()

if __name__ == "__main__":
    root = tk.Tk()
    editor = ItemEditor(root)
    root.mainloop()
