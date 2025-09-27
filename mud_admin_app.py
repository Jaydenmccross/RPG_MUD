import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

WORLD_FILE = "server/data/world.json"
ITEMS_FILE = "server/data/items.json"

EQUIP_SLOTS = [
    "Head", "Neck", "Chest", "Back", "Shoulders", "Wrists",
    "Hands", "Weapon (Main Hand)", "Weapon (Off Hand)",
    "Finger 1", "Finger 2", "Legs", "Feet",
    "Relic", "Light Source"
]

ITEM_TYPES = ["weapon", "armor", "consumable", "container", "light", "misc", "accessory"]

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") or (0,0,0,0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
        self.tipwindow = None

class WorldEditor(ttk.Frame):
    # [Unchanged, as before]
    # ... All room editing code remains the same ...
    # For brevity, not repeated here since only item editor needs update for equip_slots/accessory

    DIRECTIONS = ["north", "south", "east", "west", "up", "down"]

    def __init__(self, master):
        super().__init__(master)
        # ... (Room editor code unchanged, see earlier file for details) ...
        # Only ItemEditor below is updated for accessory/equip_slots logic

class ItemEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.items = self.load_items()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.tabs = {}
        categories = [
            ("Weapons", "weapon"),
            ("Armor", "armor"),
            ("Consumables", "consumable"),
            ("Containers", "container"),
            ("Lights", "light"),
            ("Misc", "misc"),
            ("Accessories", "accessory"),
        ]
        self.category_types = {cat: typ for cat, typ in categories}
        for category, default_type in categories:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=category)
            self.tabs[category] = frame
            self.build_item_form(frame, default_type)

    def load_items(self):
        if not os.path.exists(ITEMS_FILE):
            return {}
        with open(ITEMS_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                messagebox.showerror("Error", "Failed to load items.json — file may be corrupted.")
                return {}

    def save_items(self):
        try:
            with open(ITEMS_FILE, "w") as f:
                json.dump(self.items, f, indent=2)
            messagebox.showinfo("Saved", "Items saved successfully!")
            if hasattr(self, 'refresh_all_item_lists'):
                self.refresh_all_item_lists()
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
        type_menu = ttk.Combobox(frame, textvariable=type_var, values=ITEM_TYPES, state="readonly")
        type_menu.grid(row=3, column=1, sticky="ew")

        tk.Label(frame, text="Weight:").grid(row=4, column=0, sticky="w")
        weight_entry = tk.Entry(frame)
        weight_entry.grid(row=4, column=1, sticky="ew")

        tk.Label(frame, text="Equip Slots:").grid(row=5, column=0, sticky="nw")
        equip_slots_listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=6, exportselection=0)
        for idx, slot in enumerate(EQUIP_SLOTS):
            equip_slots_listbox.insert(tk.END, slot)
        equip_slots_listbox.grid(row=5, column=1, sticky="ew")

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
            [equip_slots_listbox.get(i) for i in equip_slots_listbox.curselection()],
            capacity_entry.get(),
            effects_text.get("1.0", tk.END).strip()
        ))
        save_button.grid(row=8, column=1, sticky="e", pady=5)

        frame.columnconfigure(1, weight=1)

    def save_item(self, item_id, name, description, item_type, weight, equip_slots, capacity, effects_json):
        if not item_id or not name:
            messagebox.showerror("Error", "Item ID and Name are required.")
            return

        if item_type not in ITEM_TYPES:
            messagebox.showerror("Error", f"Invalid item type: {item_type}")
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
            "equip_slots": equip_slots,
            "capacity": capacity,
            "effects": effects
        }

        self.save_items()

class MudAdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MUD World & Item Editor")
        self.geometry("900x600")
        tab_control = ttk.Notebook(self)
        tab_control.pack(fill=tk.BOTH, expand=True)
        self.world_editor = WorldEditor(tab_control)
        tab_control.add(self.world_editor, text="World Editor")
        self.item_editor = ItemEditor(tab_control)
        tab_control.add(self.item_editor, text="Item Editor")

if __name__ == "__main__":
    app = MudAdminApp()
    app.mainloop()
