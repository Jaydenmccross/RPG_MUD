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
] # Standardized with Player.ALL_EQUIPMENT_SLOTS

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
            idx = list(sorted(self.world.keys())).index(new_id)
            self.room_listbox.selection_clear(0, tk.END)
            self.room_listbox.selection_set(idx)
            self.room_listbox.event_generate("<<ListboxSelect>>")

    def save_room(self):
        if not self.selected_room_id:
            return
        desc = self.desc_text.get("1.0", tk.END).strip()
        exits = self.world[self.selected_room_id].get("exits", {})
        self.world[self.selected_room_id] = {"description": desc, "exits": exits}
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
            "Weapons": "weapon", "Armor": "armor", "Consumables": "consumable",
            "Containers": "container", "Lights": "light", "Misc": "misc"
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
            if hasattr(self, 'refresh_all_item_lists'): # Check if method is defined
                self.refresh_all_item_lists()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save items:\n{e}")

    def update_dynamic_fields(self, frame):
        current_type = frame.entries["type_var"].get().strip().lower()
        row = frame.dynamic_fields_start_row

        def forget_grid(widget_key):
            if widget_key in frame.entries and frame.entries[widget_key].winfo_exists():
                frame.entries[widget_key].grid_forget()

        forget_grid("min_dmg_label")
        forget_grid("min_dmg_entry")
        forget_grid("max_dmg_label")
        forget_grid("max_dmg_entry")
        forget_grid("equip_slots_label")
        forget_grid("equip_listbox_widget")
        forget_grid("capacity_label")
        forget_grid("capacity_entry")

        frame.entries.pop("min_dmg", None)
        frame.entries.pop("max_dmg", None)
        frame.entries.pop("equip_slots", None)
        frame.entries.pop("capacity", None)

        if current_type == "weapon":
            frame.entries["min_dmg_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["min_dmg_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["min_dmg"] = frame.entries["min_dmg_entry"]
            row += 1
            frame.entries["max_dmg_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["max_dmg_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["max_dmg"] = frame.entries["max_dmg_entry"]
            row += 1

        if current_type in ["weapon", "armor"]:
            frame.entries["equip_slots_label"].grid(row=row, column=0, sticky="nw", padx=2, pady=1)
            frame.entries["equip_listbox_widget"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["equip_slots"] = frame.entries["equip_listbox_widget"]
            row += 1

        if current_type == "container":
            frame.entries["capacity_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["capacity_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["capacity"] = frame.entries["capacity_entry"]
            row += 1

        frame.entries["effects_label"].grid(row=row, column=0, sticky="nw", padx=2, pady=1)
        frame.entries["effects_text_widget"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
        frame.entries["effects"] = frame.entries["effects_text_widget"]

        frame.entries["help_button_widget"].grid(row=row, column=2, sticky="w", padx=3, pady=1)
        row += 1

        frame.entries["save_button_widget"].grid(row=row, column=1, sticky="e", pady=5, padx=2)
        row += 1

        frame.entries["item_list_separator"].grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1
        frame.entries["item_list_title_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
        row += 1
        frame.entries["item_listbox_frame"].grid(row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

        frame.rowconfigure(row, weight=1)

    def build_item_form(self, frame, default_type):
        frame.entries = {}
        current_layout_row = 0

        tk.Label(frame, text="Item ID:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        id_entry = tk.Entry(frame)
        id_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        id_entry.bind("<FocusOut>", lambda e, f=frame: self.load_item_into_form(f))
        id_entry.bind("<Return>", lambda e, f=frame: self.load_item_into_form(f))
        current_layout_row += 1

        tk.Label(frame, text="Name:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        name_entry = tk.Entry(frame)
        name_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        current_layout_row += 1

        tk.Label(frame, text="Description:").grid(row=current_layout_row, column=0, sticky="nw", padx=2, pady=1)
        desc_text = tk.Text(frame, height=3)
        desc_text.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        current_layout_row += 1

        tk.Label(frame, text="Type:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        type_var = tk.StringVar(value=default_type)
        frame.entries["type_var"] = type_var
        type_entry = tk.Entry(frame, textvariable=type_var)
        type_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        type_entry.bind("<FocusOut>", lambda e, f=frame: self.update_dynamic_fields(f))
        type_entry.bind("<Return>", lambda e, f=frame: self.update_dynamic_fields(f))
        current_layout_row += 1

        tk.Label(frame, text="Weight:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        weight_entry = tk.Entry(frame)
        weight_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        current_layout_row += 1
        frame.dynamic_fields_start_row = current_layout_row

        min_dmg_label = tk.Label(frame, text="Min Damage:")
        min_dmg_entry = tk.Entry(frame)
        max_dmg_label = tk.Label(frame, text="Max Damage:")
        max_dmg_entry = tk.Entry(frame)
        equip_slots_label = tk.Label(frame, text="Equip Slots:")
        equip_listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=6, exportselection=0)
        for slot in EQUIP_SLOTS: equip_listbox.insert(tk.END, slot)
        capacity_label = tk.Label(frame, text="Capacity:")
        capacity_entry = tk.Entry(frame)
        effects_label = tk.Label(frame, text="Effects (JSON):")
        effects_text = tk.Text(frame, height=4)
        help_btn = ttk.Button(frame, text="Help", command=self.show_item_help)

        save_button = tk.Button(frame, text="Save Item", command=lambda f=frame: self.save_item(
            f.entries["id"].get(),
            f.entries["name"].get(),
            f.entries["description"].get("1.0", tk.END).strip(),
            f.entries["type_var"].get(),
            f.entries["weight"].get(),
            [f.entries["equip_listbox_widget"].get(i) for i in f.entries["equip_listbox_widget"].curselection()] if "equip_listbox_widget" in f.entries and f.entries["equip_listbox_widget"].winfo_exists() and f.entries["equip_listbox_widget"].winfo_ismapped() else [],
            f.entries["capacity_entry"].get() if "capacity_entry" in f.entries and f.entries["capacity_entry"].winfo_exists() and f.entries["capacity_entry"].winfo_ismapped() else "",
            f.entries["effects_text_widget"].get("1.0", tk.END).strip() if "effects_text_widget" in f.entries and f.entries["effects_text_widget"].winfo_exists() else "",
            f.entries["min_dmg_entry"].get() if "min_dmg_entry" in f.entries and f.entries["min_dmg_entry"].winfo_exists() and f.entries["min_dmg_entry"].winfo_ismapped() else "",
            f.entries["max_dmg_entry"].get() if "max_dmg_entry" in f.entries and f.entries["max_dmg_entry"].winfo_exists() and f.entries["max_dmg_entry"].winfo_ismapped() else ""
        ))

        item_list_separator = ttk.Separator(frame, orient='horizontal')
        item_list_title_label = tk.Label(frame, text="Existing Items:")
        listbox_frame_widget = ttk.Frame(frame)
        item_listbox_widget = tk.Listbox(listbox_frame_widget, height=8, exportselection=0)
        item_listbox_scrollbar = ttk.Scrollbar(listbox_frame_widget, orient=tk.VERTICAL, command=item_listbox_widget.yview)
        item_listbox_widget.config(yscrollcommand=item_listbox_scrollbar.set)
        item_listbox_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        item_listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        frame.entries.update({
            "id": id_entry, "name": name_entry, "description": desc_text, "weight": weight_entry,
            "min_dmg_label": min_dmg_label, "min_dmg_entry": min_dmg_entry,
            "max_dmg_label": max_dmg_label, "max_dmg_entry": max_dmg_entry,
            "equip_slots_label": equip_slots_label, "equip_listbox_widget": equip_listbox,
            "capacity_label": capacity_label, "capacity_entry": capacity_entry,
            "effects_label": effects_label, "effects_text_widget": effects_text,
            "help_button_widget": help_btn, "save_button_widget": save_button,
            "item_list_separator": item_list_separator,
            "item_list_title_label": item_list_title_label,
            "item_listbox_frame": listbox_frame_widget,
            "item_listbox": item_listbox_widget
        })
        frame.columnconfigure(1, weight=1)
        self.update_dynamic_fields(frame)

        def populate_listbox():
            listbox_widget = frame.entries["item_listbox"] # Use a more descriptive name
            listbox_widget.delete(0, tk.END)
            # Use consistent and descriptive variable names
            filtered_items = [
                (item_id, item_data)
                for item_id, item_data in self.items.items()
                if item_data.get("type", "").lower() == default_type
            ]
            for item_id, item_data in sorted(filtered_items, key=lambda x: x[0]):
                display_name = item_data.get("name", "")
                listbox_widget.insert(tk.END, f"{item_id} - {display_name}")
        populate_listbox()

        def on_listbox_select(event):
            widget = event.widget
            selection = widget.curselection()
            if selection:
                index = selection[0]
                item_text = widget.get(index)
                item_id_selected = item_text.split(" - ")[0]
                frame.entries["id"].delete(0, tk.END)
                frame.entries["id"].insert(0, item_id_selected)
                self.load_item_into_form(frame)
        frame.entries["item_listbox"].bind("<<ListboxSelect>>", on_listbox_select)

        if not hasattr(self, 'refresh_all_item_lists_defined_flag'):
            self.refresh_all_item_lists_defined_flag = True
            def refresh_all_lists_function(): # Renamed for clarity from the outer scope 'refresh_all_item_lists' attribute
                for category_name, tab_frame in self.tabs.items(): # Use descriptive names
                    if "item_listbox" in tab_frame.entries: # Corrected f_t to tab_frame
                        listbox_widget = tab_frame.entries["item_listbox"]
                        listbox_widget.delete(0, tk.END)
                        item_type_for_tab = self.category_types[category_name]

                        # Use consistent and descriptive variable names
                        filtered_items = [
                            (item_id, item_data)
                            for item_id, item_data in self.items.items()
                            if item_data.get("type", "").lower() == item_type_for_tab
                        ]
                        for item_id, item_data in sorted(filtered_items, key=lambda x: x[0]):
                            display_name = item_data.get("name", "")
                            listbox_widget.insert(tk.END, f"{item_id} - {display_name}")
            self.refresh_all_item_lists = refresh_all_lists_function # Assign the correctly named function

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
            "- Min Damage / Max Damage: Only for weapons; min should be ≤ max. Set directly in these fields.\n" # Added note
            "- Capacity: Only for containers; numeric capacity.\n"
            "- Effects: JSON encoded effects data. For weapons, do NOT use 'damage' here; use Min/Max Damage fields instead.\n\n" # Added note
            "Use the Save button to save changes.\n"
            "Leave fields empty or 0 if not applicable."
        )
        messagebox.showinfo("Item Editor Help", help_text)

    def load_item_into_form(self, frame):
        item_id = frame.entries["id"].get().strip()
        if not item_id: # If ID cleared, clear form
            frame.entries["name"].delete(0, tk.END)
            frame.entries["description"].delete("1.0", tk.END)
            # frame.entries["type_var"].set("") # Keep type for current tab, or set to ""? Let's clear.
            frame.entries["type_var"].set(self.category_types.get(self.notebook.tab(self.notebook.select(), "text"), ""))

            frame.entries["weight"].delete(0, tk.END)
            if "equip_listbox_widget" in frame.entries and frame.entries["equip_listbox_widget"].winfo_exists():
                 frame.entries["equip_listbox_widget"].selection_clear(0, tk.END)
            if "min_dmg_entry" in frame.entries and frame.entries["min_dmg_entry"].winfo_exists():
                frame.entries["min_dmg_entry"].delete(0, tk.END)
            if "max_dmg_entry" in frame.entries and frame.entries["max_dmg_entry"].winfo_exists():
                frame.entries["max_dmg_entry"].delete(0, tk.END)
            if "capacity_entry" in frame.entries and frame.entries["capacity_entry"].winfo_exists():
                frame.entries["capacity_entry"].delete(0, tk.END)
            if "effects_text_widget" in frame.entries and frame.entries["effects_text_widget"].winfo_exists():
                frame.entries["effects_text_widget"].delete("1.0", tk.END)
            self.update_dynamic_fields(frame) # Update visibility based on new empty type
            return

        item = self.items.get(item_id)
        if not item: # If ID not found, clear form (except ID)
            frame.entries["name"].delete(0, tk.END)
            frame.entries["description"].delete("1.0", tk.END)
            # frame.entries["type_var"].set("") # Or current tab type?
            frame.entries["type_var"].set(self.category_types.get(self.notebook.tab(self.notebook.select(), "text"), ""))
            frame.entries["weight"].delete(0, tk.END)
            if "equip_listbox_widget" in frame.entries and frame.entries["equip_listbox_widget"].winfo_exists():
                 frame.entries["equip_listbox_widget"].selection_clear(0, tk.END)
            if "min_dmg_entry" in frame.entries and frame.entries["min_dmg_entry"].winfo_exists():
                frame.entries["min_dmg_entry"].delete(0, tk.END)
            if "max_dmg_entry" in frame.entries and frame.entries["max_dmg_entry"].winfo_exists():
                frame.entries["max_dmg_entry"].delete(0, tk.END)
            if "capacity_entry" in frame.entries and frame.entries["capacity_entry"].winfo_exists():
                frame.entries["capacity_entry"].delete(0, tk.END)
            if "effects_text_widget" in frame.entries and frame.entries["effects_text_widget"].winfo_exists():
                frame.entries["effects_text_widget"].delete("1.0", tk.END)
            self.update_dynamic_fields(frame) # Update visibility
            return

        frame.entries["name"].delete(0, tk.END)
        frame.entries["name"].insert(0, item.get("name", ""))
        frame.entries["description"].delete("1.0", tk.END)
        frame.entries["description"].insert(tk.END, item.get("description", ""))
        item_type = item.get("type", "")
        frame.entries["type_var"].set(item_type)
        frame.entries["weight"].delete(0, tk.END)
        frame.entries["weight"].insert(0, str(item.get("weight", "")))

        self.update_dynamic_fields(frame) # Crucial: Call with frame to correctly show/hide fields

        if "equip_listbox_widget" in frame.entries and frame.entries["equip_listbox_widget"].winfo_exists():
            frame.entries["equip_listbox_widget"].selection_clear(0, tk.END)
            item_slots = item.get("equip_slots", [])
            if not isinstance(item_slots, list): item_slots = []
            for idx, slot_name in enumerate(EQUIP_SLOTS):
                if slot_name in item_slots:
                    frame.entries["equip_listbox_widget"].selection_set(idx)

        if item_type.lower() == "weapon":
            if "min_dmg_entry" in frame.entries and frame.entries["min_dmg_entry"].winfo_exists():
                frame.entries["min_dmg_entry"].delete(0, tk.END)
                frame.entries["min_dmg_entry"].insert(0, str(item.get("min_damage", 0)))
            if "max_dmg_entry" in frame.entries and frame.entries["max_dmg_entry"].winfo_exists():
                frame.entries["max_dmg_entry"].delete(0, tk.END)
                frame.entries["max_dmg_entry"].insert(0, str(item.get("max_damage", 0)))
        else: # Clear if not weapon
            if "min_dmg_entry" in frame.entries and frame.entries["min_dmg_entry"].winfo_exists():
                frame.entries["min_dmg_entry"].delete(0, tk.END)
            if "max_dmg_entry" in frame.entries and frame.entries["max_dmg_entry"].winfo_exists():
                frame.entries["max_dmg_entry"].delete(0, tk.END)

        if item_type.lower() == "container":
            if "capacity_entry" in frame.entries and frame.entries["capacity_entry"].winfo_exists():
                frame.entries["capacity_entry"].delete(0, tk.END)
                frame.entries["capacity_entry"].insert(0, str(item.get("capacity", 0)))
        else: # Clear if not container
             if "capacity_entry" in frame.entries and frame.entries["capacity_entry"].winfo_exists():
                frame.entries["capacity_entry"].delete(0, tk.END)

        effects_data = item.get("effects", "")
        if isinstance(effects_data, dict): effects_data = json.dumps(effects_data, indent=2)
        if "effects_text_widget" in frame.entries and frame.entries["effects_text_widget"].winfo_exists():
            frame.entries["effects_text_widget"].delete("1.0", tk.END)
            frame.entries["effects_text_widget"].insert(tk.END, effects_data)

    def save_item(self, item_id, name, description, item_type, weight, equip_slots,
                  capacity_str, effects_json, min_damage_str, max_damage_str):
        item_id = item_id.strip()
        if not item_id: messagebox.showerror("Error", "Item ID is required."); return
        if not name.strip(): messagebox.showerror("Error", "Name is required."); return

        item_type = item_type.strip().lower()
        if item_type not in ("weapon", "armor", "consumable", "container", "light", "misc"):
            messagebox.showerror("Error", f"Invalid item type: {item_type}"); return
        try:
            weight_val = float(weight)
            if weight_val < 0: raise ValueError
        except ValueError: messagebox.showerror("Error", "Weight must be a non-negative number."); return

        min_dmg_val, max_dmg_val = 0, 0
        if item_type == "weapon":
            try:
                min_dmg_val = int(min_damage_str) if min_damage_str else 0
                max_dmg_val = int(max_damage_str) if max_damage_str else 0
                if min_dmg_val < 0 or max_dmg_val < 0: raise ValueError("Damage cannot be negative.")
                if min_dmg_val > max_dmg_val: messagebox.showerror("Error", "Min Damage cannot be greater than Max Damage."); return
            except ValueError: messagebox.showerror("Error", "Min and Max Damage must be non-negative integers."); return

        capacity_val = 0
        if item_type == "container":
            try:
                capacity_val = int(capacity_str) if capacity_str else 0
                if capacity_val < 0: raise ValueError
            except ValueError: messagebox.showerror("Error", "Capacity must be a non-negative integer."); return

        effects_obj = {}
        if effects_json.strip():
            try: effects_obj = json.loads(effects_json)
            except Exception as e: messagebox.showerror("Error", f"Effects JSON invalid:\n{e}"); return

        # Ensure min_damage and max_damage are not saved for non-weapons
        # and capacity is not saved for non-containers.
        item_data = {
            "name": name.strip(), "description": description.strip(), "type": item_type,
            "weight": weight_val, "equip_slots": equip_slots, "effects": effects_obj
        }
        if item_type == "weapon":
            item_data["min_damage"] = min_dmg_val
            item_data["max_damage"] = max_dmg_val
        if item_type == "container":
            item_data["capacity"] = capacity_val

        self.items[item_id] = item_data
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
