import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

WORLD_FILE = "server/data/world.json"
ITEMS_FILE = "server/data/items.json"

EQUIP_SLOTS = [
    "Head", "Neck", "Back", "Shoulders", "Chest", "Wrists",
    "Hands", "Ring Left", "Ring Right", "Legs", "Feet",
    "Relic", "Light Source"
]

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
    DIRECTIONS = ["north", "south", "east", "west", "up", "down"]

    def __init__(self, master):
        super().__init__(master)
        self.world = {}
        self.selected_room_id = None
        self.autosave_after_id = None

        # Left side - room list
        self.room_listbox = tk.Listbox(self, width=30)
        self.room_listbox.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.room_listbox.bind("<<ListboxSelect>>", self.on_room_select)

        # Right side frame
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.id_label = ttk.Label(right_frame, text="Room ID:")
        self.id_label.pack(anchor="w")
        self.id_entry = ttk.Entry(right_frame, state=tk.DISABLED)
        self.id_entry.pack(fill=tk.X, padx=5)
        ToolTip(self.id_entry, "Unique room identifier. Cannot be changed after creation.")

        self.desc_label = ttk.Label(right_frame, text="Room Description:")
        self.desc_label.pack(anchor="w")
        self.desc_text = tk.Text(right_frame, height=5, undo=True)
        self.desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ToolTip(self.desc_text, "Describe the room here.")
        self.desc_text.bind("<<Modified>>", self.on_text_modified)

        self.exits_label = ttk.Label(right_frame, text="Exits (direction -> room ID):")
        self.exits_label.pack(anchor="w")

        exits_frame = ttk.Frame(right_frame)
        exits_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        self.exits_listbox = tk.Listbox(exits_frame, height=6)
        self.exits_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        exit_controls = ttk.Frame(exits_frame)
        exit_controls.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        self.exit_dir_var = tk.StringVar(value="north")
        self.exit_dir_menu = ttk.OptionMenu(exit_controls, self.exit_dir_var, "north", *self.DIRECTIONS)
        self.exit_dir_menu.pack(pady=2)
        ToolTip(self.exit_dir_menu, "Select exit direction")

        self.exit_room_var = tk.StringVar()
        self.exit_room_entry = ttk.Entry(exit_controls, textvariable=self.exit_room_var)
        self.exit_room_entry.pack(pady=2)
        ToolTip(self.exit_room_entry, "Enter destination room ID")

        self.add_exit_btn = ttk.Button(exit_controls, text="Add/Update Exit", command=self.add_or_update_exit)
        self.add_exit_btn.pack(pady=2)

        self.remove_exit_btn = ttk.Button(exit_controls, text="Remove Exit", command=self.remove_exit)
        self.remove_exit_btn.pack(pady=2)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(pady=5)

        self.new_btn = ttk.Button(btn_frame, text="New Room", command=self.new_room)
        self.new_btn.grid(row=0, column=0, padx=2)

        self.save_btn = ttk.Button(btn_frame, text="Save Room", command=self.save_room)
        self.save_btn.grid(row=0, column=1, padx=2)

        self.delete_btn = ttk.Button(btn_frame, text="Delete Room", command=self.delete_room)
        self.delete_btn.grid(row=0, column=2, padx=2)

        self.status_label = ttk.Label(right_frame, text="", foreground="green")
        self.status_label.pack(pady=2)

        self.load_world()

    def on_text_modified(self, event):
        widget = event.widget
        if widget.edit_modified():
            widget.edit_modified(False)
            if self.autosave_after_id:
                self.after_cancel(self.autosave_after_id)
            self.autosave_after_id = self.after(1000, self.save_room)
            self.status_label.config(text="Auto-saving...", foreground="orange")

    def add_or_update_exit(self):
        direction = self.exit_dir_var.get()
        destination = self.exit_room_var.get().strip()

        if not self.selected_room_id:
            messagebox.showerror("Error", "No room selected.")
            return

        if not direction or not destination:
            messagebox.showerror("Error", "Please provide both direction and destination room ID.")
            return

        direction = direction.strip().lower()

        exits = self.world[self.selected_room_id].setdefault("exits", {})
        exits[direction] = destination

        self.refresh_exits_list()
        self.status_label.config(text=f"Exit {direction}:{destination} added.", foreground="blue")
        self.exit_room_var.set("")
        self.save_room()

    def remove_exit(self):
        selected = self.exits_listbox.curselection()
        if selected and self.selected_room_id:
            line = self.exits_listbox.get(selected[0])
            if ":" in line:
                direction = line.split(":")[0]
                self.world[self.selected_room_id].get("exits", {}).pop(direction, None)
            self.refresh_exits_list()
            self.status_label.config(text="Exit removed.", foreground="red")
            self.save_room()

    def refresh_exits_list(self):
        self.exits_listbox.delete(0, tk.END)
        for direction, dest in self.world[self.selected_room_id].get("exits", {}).items():
            self.exits_listbox.insert(tk.END, f"{direction}:{dest}")

    def load_world(self):
        if os.path.exists(WORLD_FILE):
            try:
                with open(WORLD_FILE, "r") as f:
                    self.world = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Could not load world:\n{e}")
                self.world = {}
        else:
            self.world = {}
        self.refresh_room_list()

    def refresh_room_list(self):
        self.room_listbox.delete(0, tk.END)
        for room_id in sorted(self.world.keys()):
            self.room_listbox.insert(tk.END, room_id)

    def on_room_select(self, event):
        selection = self.room_listbox.curselection()
        if selection:
            index = selection[0]
            room_id = self.room_listbox.get(index)
            self.selected_room_id = room_id
            room = self.world[room_id]

            self.id_entry.config(state=tk.NORMAL)
            self.id_entry.delete(0, tk.END)
            self.id_entry.insert(0, room_id)
            self.id_entry.config(state=tk.DISABLED)

            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert(tk.END, room.get("description", ""))

            self.refresh_exits_list()

    def new_room(self):
        new_id = simpledialog.askstring("New Room", "Enter new room ID:")
        if new_id:
            new_id = new_id.strip()
            if not new_id:
                messagebox.showerror("Error", "Room ID cannot be empty.")
                return
            if new_id in self.world:
                messagebox.showerror("Error", "Room ID already exists.")
                return
            self.world[new_id] = {"description": "", "exits": {}}
            self.refresh_room_list()
            # Select new room
            idx = list(sorted(self.world.keys())).index(new_id)
            self.room_listbox.selection_clear(0, tk.END)
            self.room_listbox.selection_set(idx)
            self.room_listbox.event_generate("<<ListboxSelect>>")

    def save_room(self):
        if not self.selected_room_id:
            return

        desc = self.desc_text.get("1.0", tk.END).strip()
        exits = self.world[self.selected_room_id].get("exits", {})

        self.world[self.selected_room_id] = {
            "description": desc,
            "exits": exits
        }

        try:
            with open(WORLD_FILE, "w") as f:
                json.dump(self.world, f, indent=2)
            self.status_label.config(text="World saved.", foreground="green")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save world:\n{e}")

    def delete_room(self):
        if not self.selected_room_id:
            return
        confirm = messagebox.askyesno("Delete Room", f"Delete room '{self.selected_room_id}'?")
        if confirm:
            self.world.pop(self.selected_room_id, None)
            self.selected_room_id = None
            self.refresh_room_list()
            self.save_room()

class ItemEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.items = self.load_items()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tabs = {}
        categories = ["Weapons", "Armor", "Consumables", "Containers", "Lights", "Misc"]
        self.category_types = {
            "Weapons": "weapon",
            "Armor": "armor",
            "Consumables": "consumable",
            "Containers": "container",
            "Lights": "light",
            "Misc": "misc"
        }

        for category in categories:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=category)
            self.tabs[category] = frame
            self.build_item_form(frame, self.category_types[category])

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
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save items:\n{e}")

    def build_item_form(self, frame, default_type):
        frame.entries = {}

        # Row tracker to allow dynamic row placement
        row = 0

        # Item ID
        tk.Label(frame, text="Item ID:").grid(row=row, column=0, sticky="w")
        id_entry = tk.Entry(frame)
        id_entry.grid(row=row, column=1, sticky="ew")
        id_entry.bind("<FocusOut>", lambda e: self.load_item_into_form(frame))
        id_entry.bind("<Return>", lambda e: self.load_item_into_form(frame))
        row += 1

        # Name
        tk.Label(frame, text="Name:").grid(row=row, column=0, sticky="w")
        name_entry = tk.Entry(frame)
        name_entry.grid(row=row, column=1, sticky="ew")
        row += 1

        # Description
        tk.Label(frame, text="Description:").grid(row=row, column=0, sticky="nw")
        desc_text = tk.Text(frame, height=3)
        desc_text.grid(row=row, column=1, sticky="ew")
        row += 1

        import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

WORLD_FILE = "server/data/world.json"
ITEMS_FILE = "server/data/items.json"

EQUIP_SLOTS = [
    "Head", "Neck", "Back", "Shoulders", "Chest", "Wrists",
    "Hands", "Ring Left", "Ring Right", "Legs", "Feet",
    "Relic", "Light Source"
]

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
    DIRECTIONS = ["north", "south", "east", "west", "up", "down"]

    def __init__(self, master):
        super().__init__(master)
        self.world = {}
        self.selected_room_id = None
        self.autosave_after_id = None

        # Left side - room list
        self.room_listbox = tk.Listbox(self, width=30)
        self.room_listbox.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.room_listbox.bind("<<ListboxSelect>>", self.on_room_select)

        # Right side frame
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.id_label = ttk.Label(right_frame, text="Room ID:")
        self.id_label.pack(anchor="w")
        self.id_entry = ttk.Entry(right_frame, state=tk.DISABLED)
        self.id_entry.pack(fill=tk.X, padx=5)
        ToolTip(self.id_entry, "Unique room identifier. Cannot be changed after creation.")

        self.desc_label = ttk.Label(right_frame, text="Room Description:")
        self.desc_label.pack(anchor="w")
        self.desc_text = tk.Text(right_frame, height=5, undo=True)
        self.desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ToolTip(self.desc_text, "Describe the room here.")
        self.desc_text.bind("<<Modified>>", self.on_text_modified)

        self.exits_label = ttk.Label(right_frame, text="Exits (direction -> room ID):")
        self.exits_label.pack(anchor="w")

        exits_frame = ttk.Frame(right_frame)
        exits_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        self.exits_listbox = tk.Listbox(exits_frame, height=6)
        self.exits_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        exit_controls = ttk.Frame(exits_frame)
        exit_controls.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        self.exit_dir_var = tk.StringVar(value="north")
        self.exit_dir_menu = ttk.OptionMenu(exit_controls, self.exit_dir_var, "north", *self.DIRECTIONS)
        self.exit_dir_menu.pack(pady=2)
        ToolTip(self.exit_dir_menu, "Select exit direction")

        self.exit_room_var = tk.StringVar()
        self.exit_room_entry = ttk.Entry(exit_controls, textvariable=self.exit_room_var)
        self.exit_room_entry.pack(pady=2)
        ToolTip(self.exit_room_entry, "Enter destination room ID")

        self.add_exit_btn = ttk.Button(exit_controls, text="Add/Update Exit", command=self.add_or_update_exit)
        self.add_exit_btn.pack(pady=2)

        self.remove_exit_btn = ttk.Button(exit_controls, text="Remove Exit", command=self.remove_exit)
        self.remove_exit_btn.pack(pady=2)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(pady=5)

        self.new_btn = ttk.Button(btn_frame, text="New Room", command=self.new_room)
        self.new_btn.grid(row=0, column=0, padx=2)

        self.save_btn = ttk.Button(btn_frame, text="Save Room", command=self.save_room)
        self.save_btn.grid(row=0, column=1, padx=2)

        self.delete_btn = ttk.Button(btn_frame, text="Delete Room", command=self.delete_room)
        self.delete_btn.grid(row=0, column=2, padx=2)

        self.status_label = ttk.Label(right_frame, text="", foreground="green")
        self.status_label.pack(pady=2)

        self.load_world()

    def on_text_modified(self, event):
        widget = event.widget
        if widget.edit_modified():
            widget.edit_modified(False)
            if self.autosave_after_id:
                self.after_cancel(self.autosave_after_id)
            self.autosave_after_id = self.after(1000, self.save_room)
            self.status_label.config(text="Auto-saving...", foreground="orange")

    def add_or_update_exit(self):
        direction = self.exit_dir_var.get()
        destination = self.exit_room_var.get().strip()

        if not self.selected_room_id:
            messagebox.showerror("Error", "No room selected.")
            return

        if not direction or not destination:
            messagebox.showerror("Error", "Please provide both direction and destination room ID.")
            return

        direction = direction.strip().lower()

        exits = self.world[self.selected_room_id].setdefault("exits", {})
        exits[direction] = destination

        self.refresh_exits_list()
        self.status_label.config(text=f"Exit {direction}:{destination} added.", foreground="blue")
        self.exit_room_var.set("")
        self.save_room()

    def remove_exit(self):
        selected = self.exits_listbox.curselection()
        if selected and self.selected_room_id:
            line = self.exits_listbox.get(selected[0])
            if ":" in line:
                direction = line.split(":")[0]
                self.world[self.selected_room_id].get("exits", {}).pop(direction, None)
            self.refresh_exits_list()
            self.status_label.config(text="Exit removed.", foreground="red")
            self.save_room()

    def refresh_exits_list(self):
        self.exits_listbox.delete(0, tk.END)
        for direction, dest in self.world[self.selected_room_id].get("exits", {}).items():
            self.exits_listbox.insert(tk.END, f"{direction}:{dest}")

    def load_world(self):
        if os.path.exists(WORLD_FILE):
            try:
                with open(WORLD_FILE, "r") as f:
                    self.world = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Could not load world:\n{e}")
                self.world = {}
        else:
            self.world = {}
        self.refresh_room_list()

    def refresh_room_list(self):
        self.room_listbox.delete(0, tk.END)
        for room_id in sorted(self.world.keys()):
            self.room_listbox.insert(tk.END, room_id)

    def on_room_select(self, event):
        selection = self.room_listbox.curselection()
        if selection:
            index = selection[0]
            room_id = self.room_listbox.get(index)
            self.selected_room_id = room_id
            room = self.world[room_id]

            self.id_entry.config(state=tk.NORMAL)
            self.id_entry.delete(0, tk.END)
            self.id_entry.insert(0, room_id)
            self.id_entry.config(state=tk.DISABLED)

            self.desc_text.delete("1.0", tk.END)
            self.desc_text.insert(tk.END, room.get("description", ""))

            self.refresh_exits_list()

    def new_room(self):
        new_id = simpledialog.askstring("New Room", "Enter new room ID:")
        if new_id:
            new_id = new_id.strip()
            if not new_id:
                messagebox.showerror("Error", "Room ID cannot be empty.")
                return
            if new_id in self.world:
                messagebox.showerror("Error", "Room ID already exists.")
                return
            self.world[new_id] = {"description": "", "exits": {}}
            self.refresh_room_list()
            # Select new room
            idx = list(sorted(self.world.keys())).index(new_id)
            self.room_listbox.selection_clear(0, tk.END)
            self.room_listbox.selection_set(idx)
            self.room_listbox.event_generate("<<ListboxSelect>>")

    def save_room(self):
        if not self.selected_room_id:
            return

        desc = self.desc_text.get("1.0", tk.END).strip()
        exits = self.world[self.selected_room_id].get("exits", {})

        self.world[self.selected_room_id] = {
            "description": desc,
            "exits": exits
        }

        try:
            with open(WORLD_FILE, "w") as f:
                json.dump(self.world, f, indent=2)
            self.status_label.config(text="World saved.", foreground="green")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save world:\n{e}")

    def delete_room(self):
        if not self.selected_room_id:
            return
        confirm = messagebox.askyesno("Delete Room", f"Delete room '{self.selected_room_id}'?")
        if confirm:
            self.world.pop(self.selected_room_id, None)
            self.selected_room_id = None
            self.refresh_room_list()
            self.save_room()

class ItemEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.items = self.load_items()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tabs = {}
        categories = ["Weapons", "Armor", "Consumables", "Containers", "Lights", "Misc"]
        self.category_types = {
            "Weapons": "weapon",
            "Armor": "armor",
            "Consumables": "consumable",
            "Containers": "container",
            "Lights": "light",
            "Misc": "misc"
        }

        for category in categories:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=category)
            self.tabs[category] = frame
            self.build_item_form(frame, self.category_types[category])

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
            self.refresh_all_item_lists()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save items:\n{e}")

    def build_item_form(self, frame, default_type):
        frame.entries = {}

        # Row tracker to allow dynamic row placement
        row = 0

        # Item ID
        tk.Label(frame, text="Item ID:").grid(row=row, column=0, sticky="w")
        id_entry = tk.Entry(frame)
        id_entry.grid(row=row, column=1, sticky="ew")
        id_entry.bind("<FocusOut>", lambda e: self.load_item_into_form(frame))
        id_entry.bind("<Return>", lambda e: self.load_item_into_form(frame))
        row += 1

        # Name
        tk.Label(frame, text="Name:").grid(row=row, column=0, sticky="w")
        name_entry = tk.Entry(frame)
        name_entry.grid(row=row, column=1, sticky="ew")
        row += 1

        # Description
        tk.Label(frame, text="Description:").grid(row=row, column=0, sticky="nw")
        desc_text = tk.Text(frame, height=3)
        desc_text.grid(row=row, column=1, sticky="ew")
        row += 1

        # Type
        tk.Label(frame, text="Type:").grid(row=row, column=0, sticky="w")
        type_var = tk.StringVar(value=default_type)
        type_entry = tk.Entry(frame, textvariable=type_var)
        type_entry.grid(row=row, column=1, sticky="ew")
        type_entry.bind("<FocusOut>", lambda e: self.update_dynamic_fields(frame))
        type_entry.bind("<Return>", lambda e: self.update_dynamic_fields(frame))
        row += 1

        # Weight
        tk.Label(frame, text="Weight:").grid(row=row, column=0, sticky="w")
        weight_entry = tk.Entry(frame)
        weight_entry.grid(row=row, column=1, sticky="ew")
        row += 1

        # Min Damage & Max Damage (only for weapons)
        min_dmg_label = tk.Label(frame, text="Min Damage:")
        min_dmg_entry = tk.Entry(frame)
        max_dmg_label = tk.Label(frame, text="Max Damage:")
        max_dmg_entry = tk.Entry(frame)

        # Equip Slots (multi-select Listbox)
        tk.Label(frame, text="Equip Slots:").grid(row=row, column=0, sticky="nw")
        equip_listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=6, exportselection=0)
        for slot in EQUIP_SLOTS:
            equip_listbox.insert(tk.END, slot)
        equip_listbox.grid(row=row, column=1, sticky="ew")
        row += 1

        # Capacity (only for containers)
        capacity_label = tk.Label(frame, text="Capacity (if container):")
        capacity_entry = tk.Entry(frame)

        # Effects
        tk.Label(frame, text="Effects (JSON):").grid(row=row, column=0, sticky="nw")
        effects_text = tk.Text(frame, height=4)
        effects_text.grid(row=row, column=1, sticky="ew")

        # Help button
        help_btn = ttk.Button(frame, text="Help", command=self.show_item_help)
        help_btn.grid(row=row, column=2, sticky="w", padx=3)
        row += 1

        # Save button
        save_button = tk.Button(frame, text="Save Item", command=lambda: self.save_item(
            frame.entries["id"].get(),
            frame.entries["name"].get(),
            frame.entries["description"].get("1.0", tk.END).strip(),
            frame.entries["type"].get(),
            frame.entries["weight"].get(),
            [equip_listbox.get(i) for i in equip_listbox.curselection()],
            frame.entries.get("capacity", None).get() if frame.entries.get("capacity", None) else "",
            frame.entries["effects"].get("1.0", tk.END).strip(),
            frame.entries.get("min_dmg", None).get() if frame.entries.get("min_dmg", None) else "",
            frame.entries.get("max_dmg", None).get() if frame.entries.get("max_dmg", None) else ""
        ))
        save_button.grid(row=row, column=1, sticky="e", pady=5)

        frame.columnconfigure(1, weight=1)

        # Save widgets references
        frame.entries = {
            "id": id_entry,
            "name": name_entry,
            "description": desc_text,
            "type": type_var,
            "weight": weight_entry,
            "equip_slots": equip_listbox,
            "effects": effects_text,
            "save_button": save_button,
            "help_button": help_btn,
            # The following will be added conditionally:
            # "min_dmg", "max_dmg", "capacity"
        }

        # Place Min/Max Damage and Capacity based on type
        def place_min_max_and_capacity():
            current_type = type_var.get().strip().lower()
            # Remove if already placed (from prior calls)
            for widget in (min_dmg_label, min_dmg_entry, max_dmg_label, max_dmg_entry, capacity_label, capacity_entry):
                widget.grid_forget()

            if current_type == "weapon":
                # Place Min Damage and Max Damage fields before equip slots
                min_dmg_label.grid(row=5, column=0, sticky="w")
                min_dmg_entry.grid(row=5, column=1, sticky="ew")
                max_dmg_label.grid(row=6, column=0, sticky="w")
                max_dmg_entry.grid(row=6, column=1, sticky="ew")
                # Capacity not needed for weapons
                if "capacity" in frame.entries:
                    del frame.entries["capacity"]

                frame.entries["min_dmg"] = min_dmg_entry
                frame.entries["max_dmg"] = max_dmg_entry
            else:
                # Remove min/max if present
                frame.entries.pop("min_dmg", None)
                frame.entries.pop("max_dmg", None)

                if current_type == "container":
                    # Place Capacity below equip slots
                    capacity_label.grid(row=7, column=0, sticky="w")
                    capacity_entry.grid(row=7, column=1, sticky="ew")
                    frame.entries["capacity"] = capacity_entry
                else:
                    # Remove capacity if present
                    frame.entries.pop("capacity", None)

        # Initial placement
        place_min_max_and_capacity()

        # Save the function for later calls
        self.update_dynamic_fields = place_min_max_and_capacity

        # -- New code: Add item listbox below all fields --
        # Add separator
        sep = ttk.Separator(frame, orient='horizontal')
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1

        # Label for item list
        tk.Label(frame, text="Existing Items:").grid(row=row, column=0, sticky="w")
        row += 1

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(frame)
        listbox_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        row += 1

        item_listbox = tk.Listbox(listbox_frame, height=8)
        item_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=item_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        item_listbox.config(yscrollcommand=scrollbar.set)

        # Allow frame to expand vertically with listbox
        frame.rowconfigure(row - 1, weight=1)

        # Save reference
        frame.entries["item_listbox"] = item_listbox

        # Populate listbox for this tab's category
        def populate_listbox():
            item_listbox.delete(0, tk.END)
            typ = default_type
            filtered = [(iid, it) for iid, it in self.items.items() if it.get("type", "").lower() == typ]
            for iid, it in sorted(filtered, key=lambda x: x[0]):
                display_name = it.get("name", "")
                item_listbox.insert(tk.END, f"{iid} - {display_name}")

        populate_listbox()

        # Click handler to load item into form
        def on_listbox_select(event):
            sel = item_listbox.curselection()
            if sel:
                index = sel[0]
                item_text = item_listbox.get(index)
                item_id = item_text.split(" - ")[0]
                id_entry.delete(0, tk.END)
                id_entry.insert(0, item_id)
                self.load_item_into_form(frame)

        item_listbox.bind("<<ListboxSelect>>", on_listbox_select)

        # Save function to refresh listboxes in all tabs after save
        def refresh_all_lists():
            for cat, f in self.tabs.items():
                if "item_listbox" in f.entries:
                    f.entries["item_listbox"].delete(0, tk.END)
                    typ = self.category_types[cat]
                    filtered = [(iid, it) for iid, it in self.items.items() if it.get("type", "").lower() == typ]
                    for iid, it in sorted(filtered, key=lambda x: x[0]):
                        display_name = it.get("name", "")
                        f.entries["item_listbox"].insert(tk.END, f"{iid} - {display_name}")

        self.refresh_all_item_lists = refresh_all_lists

    def show_item_help(self):
        help_text = (
            "Item Editor Help:\n\n"
            "- Item ID: Unique identifier for the item.\n"
            "- Name: Display name.\n"
            "- Description: Text description.\n"
            "- Type: One of weapon, armor, consumable, container, light, misc.\n"
            "- Weight: Numeric weight (non-negative).\n"
            "- Equip Slots: Select one or more slots where the item can be equipped.\n"
            "  Available slots: " + ", ".join(EQUIP_SLOTS) + "\n"
            "- Min Damage / Max Damage: Only for weapons; min should be ≤ max.\n"
            "- Capacity: Only for containers; numeric capacity.\n"
            "- Effects: JSON encoded effects data.\n\n"
            "Use the Save button to save changes.\n"
            "Leave fields empty or 0 if not applicable."
        )
        messagebox.showinfo("Item Editor Help", help_text)

    def load_item_into_form(self, frame):
        item_id = frame.entries["id"].get().strip()
        if not item_id:
            return
        item = self.items.get(item_id)
        if not item:
            # Clear fields if no such item
            frame.entries["name"].delete(0, tk.END)
            frame.entries["description"].delete("1.0", tk.END)
            frame.entries["type"].set("")
            frame.entries["weight"].delete(0, tk.END)
            frame.entries["equip_slots"].selection_clear(0, tk.END)
            if "min_dmg" in frame.entries:
                frame.entries["min_dmg"].delete(0, tk.END)
            if "max_dmg" in frame.entries:
                frame.entries["max_dmg"].delete(0, tk.END)
            if "capacity" in frame.entries:
                frame.entries["capacity"].delete(0, tk.END)
            frame.entries["effects"].delete("1.0", tk.END)
            return

        frame.entries["name"].delete(0, tk.END)
        frame.entries["name"].insert(0, item.get("name", ""))

        frame.entries["description"].delete("1.0", tk.END)
        frame.entries["description"].insert(tk.END, item.get("description", ""))

        item_type = item.get("type", "")
        frame.entries["type"].set(item_type)

        frame.entries["weight"].delete(0, tk.END)
        frame.entries["weight"].insert(0, str(item.get("weight", "")))

        # Update dynamic fields based on type (show/hide min/max/capacity)
        self.update_dynamic_fields()

        # Equip slots - clear then select indices that match
        frame.entries["equip_slots"].selection_clear(0, tk.END)
        item_slots = item.get("equip_slots", [])
        if not isinstance(item_slots, list):
            item_slots = []
        for idx, slot in enumerate(EQUIP_SLOTS):
            if slot in item_slots:
                frame.entries["equip_slots"].selection_set(idx)

        # Min/Max Damage if weapon
        if item_type.lower() == "weapon":
            if "min_dmg" in frame.entries:
                frame.entries["min_dmg"].delete(0, tk.END)
                frame.entries["min_dmg"].insert(0, str(item.get("min_damage", 0)))
            if "max_dmg" in frame.entries:
                frame.entries["max_dmg"].delete(0, tk.END)
                frame.entries["max_dmg"].insert(0, str(item.get("max_damage", 0)))
        else:
            if "min_dmg" in frame.entries:
                frame.entries["min_dmg"].delete(0, tk.END)
            if "max_dmg" in frame.entries:
                frame.entries["max_dmg"].delete(0, tk.END)

        # Capacity if container
        if item_type.lower() == "container":
            if "capacity" in frame.entries:
                frame.entries["capacity"].delete(0, tk.END)
                frame.entries["capacity"].insert(0, str(item.get("capacity", 0)))
        else:
            if "capacity" in frame.entries:
                frame.entries["capacity"].delete(0, tk.END)

        # Effects JSON
        effects = item.get("effects", "")
        if isinstance(effects, dict):
            effects = json.dumps(effects, indent=2)
        frame.entries["effects"].delete("1.0", tk.END)
        frame.entries["effects"].insert(tk.END, effects)

    def save_item(self, item_id, name, description, item_type, weight, equip_slots,
                  capacity, effects_json, min_damage, max_damage):
        item_id = item_id.strip()
        if not item_id:
            messagebox.showerror("Error", "Item ID is required.")
            return
        if not name.strip():
            messagebox.showerror("Error", "Name is required.")
            return
        item_type = item_type.strip().lower()
        if item_type not in ("weapon", "armor", "consumable", "container", "light", "misc"):
            messagebox.showerror("Error", f"Invalid item type: {item_type}")
            return
        try:
            weight_val = float(weight)
            if weight_val < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Weight must be a non-negative number.")
            return

        # Validate min/max damage if weapon
        if item_type == "weapon":
            try:
                min_dmg_val = int(min_damage)
                max_dmg_val = int(max_damage)
                if min_dmg_val < 0 or max_dmg_val < 0:
                    raise ValueError
                if min_dmg_val > max_dmg_val:
                    messagebox.showerror("Error", "Min Damage cannot be greater than Max Damage.")
                    return
            except ValueError:
                messagebox.showerror("Error", "Min and Max Damage must be non-negative integers.")
                return
        else:
            min_dmg_val = 0
            max_dmg_val = 0

        # Validate capacity if container
        if item_type == "container":
            try:
                capacity_val = int(capacity)
                if capacity_val < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Capacity must be a non-negative integer.")
                return
        else:
            capacity_val = 0

        # Parse effects JSON
        if effects_json.strip():
            try:
                effects_obj = json.loads(effects_json)
            except Exception as e:
                messagebox.showerror("Error", f"Effects JSON invalid:\n{e}")
                return
        else:
            effects_obj = {}

        # Save item
        self.items[item_id] = {
            "name": name.strip(),
            "description": description.strip(),
            "type": item_type,
            "weight": weight_val,
            "equip_slots": equip_slots,
            "min_damage": min_dmg_val,
            "max_damage": max_dmg_val,
            "capacity": capacity_val,
            "effects": effects_obj
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
