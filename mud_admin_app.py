import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

WORLD_FILE = "server/data/world.json"
ITEMS_FILE = "server/data/items.json"
MOBS_FILE = "server/data/mobs.json" # Added Mobs file

EQUIP_SLOTS = [
    "Head", "Neck", "Chest", "Back", "Shoulders", "Wrists",
    "Hands", "Weapon (Main Hand)", "Weapon (Off Hand)",
    "Finger 1", "Finger 2", "Legs", "Feet",
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
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') and callable(self.widget.bbox) else (0,0,0,0) # Added check for bbox
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

class MobEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.mobs = self.load_mobs_data() # Renamed to avoid conflict

        # Main frame structure
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Left: List of mobs
        self.list_frame = ttk.Frame(self.main_frame)
        self.list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(self.list_frame, text="Mobs:").pack(anchor="w")
        self.mob_listbox = tk.Listbox(self.list_frame, width=30, exportselection=0)
        self.mob_listbox.pack(fill=tk.Y, expand=True)
        self.mob_listbox.bind("<<ListboxSelect>>", self.on_mob_select)

        # Right: Mob details form
        self.form_frame = ttk.Frame(self.main_frame)
        self.form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.entries = {}
        fields = [
            ("Mob ID:", "mob_id", True), # Field Name, internal key, is_disabled_after_load
            ("Name:", "name", False),
            ("Description:", "description", False, {"type": "text", "height": 3}),
            ("Max HP:", "max_hp", False),
            ("Speed:", "speed", False),
            ("AC:", "ac", False),
            ("Attack Bonus:", "attack_bonus", False),
            ("Damage Dice:", "damage_dice", False), # e.g., 1d6+2
            ("Damage Type:", "damage_type", False),
            ("XP Value:", "xp_value", False),
            ("Aggressive (True/False):", "is_aggressive", False),
            ("Loot Table (JSON):", "loot_table", False, {"type": "text", "height": 4})
        ]

        for i, (text, key, disabled, *widget_options) in enumerate(fields):
            label = ttk.Label(self.form_frame, text=text)
            label.grid(row=i, column=0, sticky="w", padx=2, pady=2)

            options = widget_options[0] if widget_options else {}
            if options.get("type") == "text":
                entry = tk.Text(self.form_frame, height=options.get("height", 3), width=40)
            else:
                entry = ttk.Entry(self.form_frame, width=40)

            entry.grid(row=i, column=1, sticky="ew", padx=2, pady=2)
            self.entries[key] = entry
            if key == "mob_id": # Mob ID is special
                entry.bind("<FocusOut>", lambda e: self.load_mob_to_form())
                entry.bind("<Return>", lambda e: self.load_mob_to_form())


        self.save_button = ttk.Button(self.form_frame, text="Save Mob", command=self.save_mob)
        self.save_button.grid(row=len(fields), column=1, sticky="e", pady=10, padx=2)

        self.new_button = ttk.Button(self.form_frame, text="New Mob", command=self.new_mob_clear_form)
        self.new_button.grid(row=len(fields), column=0, sticky="w", pady=10, padx=2)

        self.delete_button = ttk.Button(self.form_frame, text="Delete Mob", command=self.delete_mob)
        self.delete_button.grid(row=len(fields)+1, column=0, sticky="w", pady=5, padx=2)


        self.form_frame.columnconfigure(1, weight=1)
        self.refresh_mob_list()

    def load_mobs_data(self): # Renamed
        if not os.path.exists(MOBS_FILE):
            return {}
        with open(MOBS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                messagebox.showerror("Error", f"Failed to load {MOBS_FILE} - file may be corrupted or not valid JSON.")
                return {}
            except Exception as e:
                 messagebox.showerror("Error", f"Failed to load {MOBS_FILE}:\n{e}")
                 return {}


    def save_mobs_data(self): # Renamed
        try:
            with open(MOBS_FILE, "w") as f:
                json.dump(self.mobs, f, indent=2)
            # messagebox.showinfo("Saved", "Mobs saved successfully!") # Can be too noisy
            print("Mobs data saved.")
            self.refresh_mob_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save mobs:\n{e}")

    def refresh_mob_list(self):
        self.mob_listbox.delete(0, tk.END)
        for mob_id, mob_data in sorted(self.mobs.items()):
            self.mob_listbox.insert(tk.END, f"{mob_id} - {mob_data.get('name', mob_id)}")

    def on_mob_select(self, event):
        selection = self.mob_listbox.curselection()
        if selection:
            index = selection[0]
            item_text = self.mob_listbox.get(index)
            mob_id_selected = item_text.split(" - ")[0]
            self.entries["mob_id"].delete(0, tk.END)
            self.entries["mob_id"].insert(0, mob_id_selected)
            self.load_mob_to_form()

    def clear_form(self):
        for key, entry_widget in self.entries.items():
            if isinstance(entry_widget, tk.Text):
                entry_widget.delete("1.0", tk.END)
            else:
                entry_widget.delete(0, tk.END)
        self.entries["mob_id"].config(state=tk.NORMAL)


    def new_mob_clear_form(self):
        self.clear_form()
        self.entries["mob_id"].focus_set()


    def load_mob_to_form(self):
        mob_id = self.entries["mob_id"].get().strip()
        if not mob_id:
            self.clear_form() # Clear if ID is removed
            return

        mob_data = self.mobs.get(mob_id)
        if not mob_data:
            # Clear other fields if mob_id not found, but keep mob_id entry
            for key, entry_widget in self.entries.items():
                if key != "mob_id":
                    if isinstance(entry_widget, tk.Text): entry_widget.delete("1.0", tk.END)
                    else: entry_widget.delete(0, tk.END)
            return

        self.entries["mob_id"].config(state=tk.DISABLED) # Disable ID field after loading

        for key, entry_widget in self.entries.items():
            if key == "mob_id": continue # Already handled

            value = mob_data.get(key, "")
            if isinstance(entry_widget, tk.Text):
                entry_widget.delete("1.0", tk.END)
                if isinstance(value, dict) or isinstance(value, list): # For loot_table
                    entry_widget.insert(tk.END, json.dumps(value, indent=2))
                else:
                    entry_widget.insert(tk.END, str(value))
            else: # tk.Entry or ttk.Entry
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, str(value))

    def save_mob(self):
        mob_id = self.entries["mob_id"].get().strip()
        if not mob_id:
            messagebox.showerror("Error", "Mob ID is required.")
            return

        mob_data_to_save = {}
        for key, entry_widget in self.entries.items():
            if key == "mob_id": continue

            if isinstance(entry_widget, tk.Text):
                value_str = entry_widget.get("1.0", tk.END).strip()
                if key == "loot_table":
                    if value_str:
                        try:
                            mob_data_to_save[key] = json.loads(value_str)
                        except json.JSONDecodeError:
                            messagebox.showerror("Error", f"Invalid JSON in {key}.")
                            return
                    else:
                        mob_data_to_save[key] = {} # Default to empty dict
                else: # Description
                     mob_data_to_save[key] = value_str
            else: # Entry widgets
                value_str = entry_widget.get().strip()
                # Attempt to convert to int for numeric fields, float for others if needed
                if key in ["max_hp", "speed", "ac", "attack_bonus", "xp_value"]:
                    try: mob_data_to_save[key] = int(value_str) if value_str else 0
                    except ValueError: messagebox.showerror("Error", f"{key.replace('_', ' ').title()} must be an integer."); return
                elif key == "is_aggressive":
                    mob_data_to_save[key] = value_str.lower() == 'true'
                else: # name, damage_dice, damage_type
                    mob_data_to_save[key] = value_str

        self.mobs[mob_id] = mob_data_to_save
        self.save_mobs_data() # This will also refresh the list
        self.entries["mob_id"].config(state=tk.NORMAL) # Re-enable after save
        messagebox.showinfo("Saved", f"Mob '{mob_id}' saved.")


    def delete_mob(self):
        mob_id = self.entries["mob_id"].get().strip()
        if not mob_id:
            messagebox.showerror("Error", "No Mob ID specified to delete.")
            return
        if mob_id not in self.mobs:
            messagebox.showerror("Error", f"Mob ID '{mob_id}' not found.")
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete mob '{mob_id}' - {self.mobs[mob_id].get('name', '')}?"):
            del self.mobs[mob_id]
            self.save_mobs_data()
            self.clear_form()
            messagebox.showinfo("Deleted", f"Mob '{mob_id}' deleted.")


class WorldEditor(ttk.Frame): # ... (WorldEditor class as before, will need changes later for room content) ...
    DIRECTIONS = ["north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest"]

    def __init__(self, master):
        super().__init__(master)
        self.world_data = {} # Stores the raw dicts from world.json
        self.items_data = self.load_json_data(ITEMS_FILE, "items")
        self.mobs_data = self.load_json_data(MOBS_FILE, "mobs")

        self.selected_room_id = None
        self.autosave_after_id = None

        # Main PanedWindow
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Left frame - room list
        self.room_list_frame = ttk.Frame(self.paned_window, width=200)
        self.room_list_label = ttk.Label(self.room_list_frame, text="Rooms:")
        self.room_list_label.pack(anchor="w")
        self.room_listbox = tk.Listbox(self.room_list_frame, exportselection=0)
        self.room_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.room_list_scrollbar = ttk.Scrollbar(self.room_list_frame, orient=tk.VERTICAL, command=self.room_listbox.yview)
        self.room_listbox.config(yscrollcommand=self.room_list_scrollbar.set)
        self.room_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.room_listbox.bind("<<ListboxSelect>>", self.on_room_select)
        self.paned_window.add(self.room_list_frame, weight=1)

        # Right frame - Room Editor (placeholder for now)
        self.room_editor_frame_container = ttk.Frame(self.paned_window)
        self.paned_window.add(self.room_editor_frame_container, weight=3)

        self.current_room_editor = None # To hold the RoomEditorFrame instance

        # Bottom buttons
        self.bottom_button_frame = ttk.Frame(self)
        self.bottom_button_frame.pack(fill=tk.X, pady=5)
        self.new_room_btn = ttk.Button(self.bottom_button_frame, text="New Room", command=self.new_room)
        self.new_room_btn.pack(side=tk.LEFT, padx=5)
        self.save_all_btn = ttk.Button(self.bottom_button_frame, text="Save World", command=self.save_world_data_to_file)
        self.save_all_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(self.bottom_button_frame, text="", foreground="green") # Moved status here
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.load_world_data_from_file() # Initial load

    def load_json_data(self, file_path, data_type_name, is_optional=False):
        if not os.path.exists(file_path):
            if not is_optional:
                messagebox.showwarning("File Not Found", f"{data_type_name.capitalize()} data file not found: {file_path}")
            return {}
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("JSON Error", f"Error decoding {data_type_name} data from {file_path}.")
            return {}
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load {data_type_name} data from {file_path}: {e}")
            return {}

    def load_world_data_from_file(self):
        self.world_data = self.load_json_data(WORLD_FILE, "world")
        self.refresh_room_list()
        if self.room_listbox.size() > 0: # Select first room if any
            self.room_listbox.selection_set(0)
            self.on_room_select(None) # Trigger selection

    def save_world_data_to_file(self):
        # First, if a room is being edited, save its current state from editor to self.world_data
        if self.current_room_editor and self.selected_room_id:
            self.current_room_editor.apply_changes_to_world_data() # This method needs to be in RoomEditorFrame

        if not self.world_data:
            messagebox.showinfo("Save World", "No world data to save.")
            return
        try:
            with open(WORLD_FILE, "w") as f:
                json.dump(self.world_data, f, indent=2)
            self.status_label.config(text="World saved successfully!", foreground="green")
            print("World data saved.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save world data to {WORLD_FILE}: {e}")
            self.status_label.config(text="Error saving world!", foreground="red")


    def refresh_room_list(self):
        self.room_listbox.delete(0, tk.END)
        for room_id in sorted(self.world_data.keys()):
            self.room_listbox.insert(tk.END, room_id)

    def on_room_select(self, event):
        selection = self.room_listbox.curselection()
        if not selection:
            if self.current_room_editor:
                self.current_room_editor.destroy()
                self.current_room_editor = None
            self.selected_room_id = None
            return

        index = selection[0]
        room_id = self.room_listbox.get(index)

        if self.current_room_editor and self.selected_room_id != room_id:
            # Save previous room before switching
             if self.selected_room_id and self.current_room_editor:
                self.current_room_editor.apply_changes_to_world_data()

        self.selected_room_id = room_id

        if self.current_room_editor:
            self.current_room_editor.destroy() # Remove old editor frame

        # Create and pack new RoomEditorFrame for the selected room
        self.current_room_editor = RoomEditorFrame(
            self.room_editor_frame_container,
            room_id,
            self.world_data, # Pass the main world_data dict
            self.mobs_data,  # Pass all loaded mob blueprints
            self.items_data, # Pass all loaded item blueprints
            self.save_world_data_to_file # Pass save callback for auto-save/manual save from editor
        )
        self.current_room_editor.pack(fill=tk.BOTH, expand=True)


    def new_room(self):
        new_id = simpledialog.askstring("New Room", "Enter new unique room ID:", parent=self)
        if new_id:
            new_id = new_id.strip().replace(" ", "_") # Sanitize
            if not new_id:
                messagebox.showerror("Error", "Room ID cannot be empty.", parent=self)
                return
            if new_id in self.world_data:
                messagebox.showerror("Error", "Room ID already exists.", parent=self)
                return

            self.world_data[new_id] = {
                "name": new_id.replace("_", " ").title(),
                "description": "A new, undescribed room.",
                "exits": {},
                "mob_definitions": [], # Initialize for room content editor
                "item_definitions": []  # Initialize for room content editor
            }
            self.refresh_room_list()
            # Find index of new_id to select it
            try:
                idx = list(sorted(self.world_data.keys())).index(new_id)
                self.room_listbox.selection_clear(0, tk.END)
                self.room_listbox.selection_set(idx)
                self.room_listbox.see(idx) # Ensure it's visible
                self.on_room_select(None) # Trigger display of the new room
                self.save_world_data_to_file() # Save immediately
            except ValueError:
                pass # Should not happen if id was added

class RoomEditorFrame(ttk.Frame): # Placeholder for actual Room Editor UI
    DIRECTIONS = ["north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest"]
    def __init__(self, master, room_id, world_data_ref, mobs_data_ref, items_data_ref, save_callback):
        super().__init__(master)
        self.room_id = room_id
        self.world_data = world_data_ref # Reference to the main world_data dict
        self.mobs_data = mobs_data_ref   # Reference to all mob blueprints
        self.items_data = items_data_ref # Reference to all item blueprints
        self.save_world_callback = save_callback

        self.room_data_dict = self.world_data.setdefault(self.room_id, {}) # Get or create if somehow missing

        # Ensure necessary lists exist
        self.room_data_dict.setdefault("exits", {})
        self.room_data_dict.setdefault("mob_definitions", [])
        self.room_data_dict.setdefault("item_definitions", [])

        self.autosave_after_id = None
        self._build_ui()
        self._load_room_data()

    def _build_ui(self):
        # Room ID (display only)
        id_frame = ttk.Frame(self)
        id_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(id_frame, text="Room ID:").pack(side=tk.LEFT)
        self.id_display = ttk.Label(id_frame, text=self.room_id)
        self.id_display.pack(side=tk.LEFT, padx=5)
        ttk.Button(id_frame, text="Delete This Room", command=self.confirm_delete_room).pack(side=tk.RIGHT)


        # Name
        name_frame = ttk.Frame(self)
        name_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT, anchor='w')
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.pack(fill=tk.X, expand=True)
        self.name_entry.bind("<<Modified>>", self.schedule_autosave)
        ToolTip(self.name_entry, "Display name for the room.")


        # Description
        ttk.Label(self, text="Description:").pack(anchor="w", padx=5, pady=(5,0))
        self.desc_text = tk.Text(self, height=5, width=70, wrap=tk.WORD, undo=True)
        self.desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.desc_text.bind("<<Modified>>", self.schedule_autosave)
        ToolTip(self.desc_text, "Full description of the room. Use multiple lines.")

        # Exits
        exits_main_frame = ttk.LabelFrame(self, text="Exits")
        exits_main_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)

        self.exits_listbox = tk.Listbox(exits_main_frame, height=4, exportselection=0)
        self.exits_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        exits_controls_frame = ttk.Frame(exits_main_frame)
        exits_controls_frame.pack(side=tk.LEFT, padx=5, pady=5)

        self.exit_dir_var = tk.StringVar()
        self.exit_dir_combobox = ttk.Combobox(exits_controls_frame, textvariable=self.exit_dir_var, values=self.DIRECTIONS, state="readonly", width=10)
        self.exit_dir_combobox.pack(pady=2)
        self.exit_dest_var = tk.StringVar()
        self.exit_dest_entry = ttk.Entry(exits_controls_frame, textvariable=self.exit_dest_var, width=15)
        self.exit_dest_entry.pack(pady=2)
        ttk.Button(exits_controls_frame, text="Add/Set Exit", command=self.add_update_exit).pack(pady=2)
        ttk.Button(exits_controls_frame, text="Remove Exit", command=self.remove_selected_exit).pack(pady=2)

        # Mob Definitions
        mobs_frame = ttk.LabelFrame(self, text="Mob Spawns (Definitions)")
        mobs_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        self.mob_defs_listbox = tk.Listbox(mobs_frame, height=4, exportselection=0)
        self.mob_defs_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        # ... (Add, Remove controls for mobs) ...

        # Item Definitions
        items_frame = ttk.LabelFrame(self, text="Item Spawns (Definitions)")
        items_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        self.item_defs_listbox = tk.Listbox(items_frame, height=4, exportselection=0)
        self.item_defs_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        # ... (Add, Remove controls for items) ...

    def _load_room_data(self):
        self.name_var.set(self.room_data_dict.get("name", self.room_id.replace("_", " ").title()))
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", self.room_data_dict.get("description", ""))
        self.desc_text.edit_modified(False) # Reset modified flag after loading
        self._refresh_exits_listbox()
        self._refresh_mob_defs_listbox()
        self._refresh_item_defs_listbox()


    def _refresh_exits_listbox(self):
        self.exits_listbox.delete(0, tk.END)
        for direction, dest_id in sorted(self.room_data_dict.get("exits", {}).items()):
            self.exits_listbox.insert(tk.END, f"{direction}: {dest_id}")

    def _refresh_mob_defs_listbox(self):
        self.mob_defs_listbox.delete(0, tk.END)
        for mob_def in self.room_data_dict.get("mob_definitions", []):
            mob_name = self.mobs_data.get(mob_def.get("mob_id"), {}).get("name", mob_def.get("mob_id"))
            qty = mob_def.get("quantity",1)
            respawn = mob_def.get("respawn_seconds",0)
            self.mob_defs_listbox.insert(tk.END, f"{mob_name} (ID: {mob_def.get('mob_id')}) x{qty} [Respawn: {respawn}s]")

    def _refresh_item_defs_listbox(self):
        self.item_defs_listbox.delete(0, tk.END)
        for item_def in self.room_data_dict.get("item_definitions",[]):
            item_name = self.items_data.get(item_def.get("item_id"), {}).get("name", item_def.get("item_id"))
            qty = item_def.get("quantity",1)
            respawn = item_def.get("respawn_seconds",0)
            self.item_defs_listbox.insert(tk.END, f"{item_name} (ID: {item_def.get('item_id')}) x{qty} [Respawn: {respawn}s]")


    def add_update_exit(self):
        direction = self.exit_dir_var.get()
        destination_id = self.exit_dest_var.get().strip()
        if not direction or not destination_id:
            messagebox.showerror("Input Error", "Both direction and destination ID are required.", parent=self)
            return
        self.room_data_dict.setdefault("exits", {})[direction] = destination_id
        self._refresh_exits_listbox()
        self.schedule_autosave()

    def remove_selected_exit(self):
        selected_idx = self.exits_listbox.curselection()
        if not selected_idx: return
        selected_text = self.exits_listbox.get(selected_idx[0])
        direction = selected_text.split(":")[0]
        if direction in self.room_data_dict.get("exits", {}):
            del self.room_data_dict["exits"][direction]
            self._refresh_exits_listbox()
            self.schedule_autosave()

    def schedule_autosave(self, event=None): # Modified to handle event
        if hasattr(event.widget, 'edit_modified') and event.widget.edit_modified(): # Check if modified
             event.widget.edit_modified(False) # Reset flag

        if self.autosave_after_id:
            self.after_cancel(self.autosave_after_id)
        self.autosave_after_id = self.after(1000, self.apply_changes_to_world_data_and_save)


    def apply_changes_to_world_data(self): # Called by WorldEditor before switching rooms or global save
        self.room_data_dict["name"] = self.name_var.get()
        self.room_data_dict["description"] = self.desc_text.get("1.0", tk.END).strip()
        # Exits, mob_defs, item_defs are modified directly in self.room_data_dict by their respective UI methods

    def apply_changes_to_world_data_and_save(self):
        self.apply_changes_to_world_data()
        if self.save_world_callback:
            self.save_world_callback() # This calls WorldEditor.save_world_data_to_file
            if hasattr(self.master.master, 'status_label'): # Access status label on WorldEditor if possible
                 self.master.master.status_label.config(text=f"Room '{self.room_id}' auto-saved.", foreground="blue")


    def confirm_delete_room(self):
        if messagebox.askyesno("Delete Room", f"Are you sure you want to delete room '{self.room_id}'?\nThis cannot be undone.", parent=self):
            if self.room_id in self.world_data:
                del self.world_data[self.room_id]
                # Notify parent (WorldEditor) to refresh its list and save
                self.master.master.refresh_room_list()
                self.master.master.selected_room_id = None # Clear selection
                if self.master.master.current_room_editor == self:
                    self.master.master.current_room_editor.destroy()
                    self.master.master.current_room_editor = None
                self.save_world_callback() # Save the change
                messagebox.showinfo("Room Deleted", f"Room '{self.room_id}' has been deleted.", parent=self.master.master) # Show info on main window
            self.destroy() # Destroy this editor frame


class ItemEditor(ttk.Frame): # ... (ItemEditor class as before) ...
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
            if hasattr(self, 'refresh_all_item_lists'):
                self.refresh_all_item_lists()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save items:\n{e}")

    def update_dynamic_fields(self, frame):
        current_type = frame.entries["type_var"].get().strip().lower()
        row = frame.dynamic_fields_start_row

        # Simplified hiding: just grid_forget everything that might be dynamic
        for key in ["min_dmg_label", "min_dmg_entry", "max_dmg_label", "max_dmg_entry",
                    "equip_slots_label", "equip_listbox_widget", "capacity_label", "capacity_entry"]:
            if key in frame.entries and frame.entries[key].winfo_exists():
                frame.entries[key].grid_forget()

        # Clear data from entries that are about to be hidden or reconfigured
        if "min_dmg" in frame.entries and frame.entries["min_dmg"].winfo_exists(): frame.entries["min_dmg"].delete(0, tk.END)
        if "max_dmg" in frame.entries and frame.entries["max_dmg"].winfo_exists(): frame.entries["max_dmg"].delete(0, tk.END)
        if "equip_slots" in frame.entries and frame.entries["equip_slots"].winfo_exists(): frame.entries["equip_slots"].selection_clear(0, tk.END)
        if "capacity" in frame.entries and frame.entries["capacity"].winfo_exists(): frame.entries["capacity"].delete(0, tk.END)


        if current_type == "weapon":
            frame.entries["min_dmg_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["min_dmg_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["min_dmg"] = frame.entries["min_dmg_entry"] # Ensure key exists
            row += 1
            frame.entries["max_dmg_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["max_dmg_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["max_dmg"] = frame.entries["max_dmg_entry"] # Ensure key exists
            row += 1

        if current_type in ["weapon", "armor", "light"]: # Lights can be equipped
            frame.entries["equip_slots_label"].grid(row=row, column=0, sticky="nw", padx=2, pady=1)
            frame.entries["equip_listbox_widget"].grid(row=row, column=1, sticky="ew", rowspan=2, padx=2, pady=1) # rowspan for listbox
            frame.entries["equip_slots"] = frame.entries["equip_listbox_widget"]
            row += 2 # Account for rowspan

        if current_type == "container":
            frame.entries["capacity_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["capacity_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["capacity"] = frame.entries["capacity_entry"]
            row += 1

        frame.entries["effects_label"].grid(row=row, column=0, sticky="nw", padx=2, pady=1)
        frame.entries["effects_text_widget"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
        frame.entries["effects"] = frame.entries["effects_text_widget"] # Ensure key exists

        frame.entries["help_button_widget"].grid(row=row, column=2, sticky="w", padx=3, pady=1)
        row += 1

        frame.entries["save_button_widget"].grid(row=row, column=1, sticky="e", pady=5, padx=2)
        row += 1

        frame.entries["item_list_separator"].grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1
        frame.entries["item_list_title_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
        row += 1
        frame.entries["item_listbox_frame"].grid(row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

        frame.rowconfigure(row, weight=1) # Make the listbox frame expand

    def build_item_form(self, frame, default_type):
        frame.entries = {}
        current_layout_row = 0

        tk.Label(frame, text="Item ID:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        id_entry = tk.Entry(frame)
        id_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        id_entry.bind("<FocusOut>", lambda e, fr=frame: self.load_item_into_form(fr))
        id_entry.bind("<Return>", lambda e, fr=frame: self.load_item_into_form(fr))
        frame.entries["id"] = id_entry
        current_layout_row += 1

        tk.Label(frame, text="Name:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        name_entry = tk.Entry(frame)
        name_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        frame.entries["name"] = name_entry
        current_layout_row += 1

        tk.Label(frame, text="Description:").grid(row=current_layout_row, column=0, sticky="nw", padx=2, pady=1)
        desc_text = tk.Text(frame, height=3)
        desc_text.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        frame.entries["description"] = desc_text
        current_layout_row += 1

        tk.Label(frame, text="Type:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        type_var = tk.StringVar(value=default_type)
        type_entry = ttk.Combobox(frame, textvariable=type_var, values=list(self.category_types.values()), state="readonly")
        type_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        type_entry.bind("<<ComboboxSelected>>", lambda e, fr=frame: self.update_dynamic_fields(fr))
        frame.entries["type_var"] = type_var # Store var for getting value
        frame.entries["type_entry"] = type_entry # Store widget if needed
        current_layout_row += 1

        tk.Label(frame, text="Weight:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        weight_entry = tk.Entry(frame)
        weight_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        frame.entries["weight"] = weight_entry
        current_layout_row += 1

        frame.dynamic_fields_start_row = current_layout_row

        # Define all dynamic fields here so they exist for update_dynamic_fields
        frame.entries["min_dmg_label"] = tk.Label(frame, text="Min Damage:")
        frame.entries["min_dmg_entry"] = tk.Entry(frame)
        frame.entries["max_dmg_label"] = tk.Label(frame, text="Max Damage:")
        frame.entries["max_dmg_entry"] = tk.Entry(frame)
        frame.entries["equip_slots_label"] = tk.Label(frame, text="Equip Slots:")
        frame.entries["equip_listbox_widget"] = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=len(EQUIP_SLOTS)//2 +1, exportselection=0)
        for slot in EQUIP_SLOTS: frame.entries["equip_listbox_widget"].insert(tk.END, slot)
        frame.entries["capacity_label"] = tk.Label(frame, text="Capacity (Weight):")
        frame.entries["capacity_entry"] = tk.Entry(frame)
        frame.entries["effects_label"] = tk.Label(frame, text="Effects (JSON):")
        frame.entries["effects_text_widget"] = tk.Text(frame, height=4)
        frame.entries["help_button_widget"] = ttk.Button(frame, text="Help", command=self.show_item_help)

        frame.entries["save_button_widget"] = tk.Button(frame, text="Save Item", command=lambda fr=frame: self.save_item_from_form(fr))

        frame.entries["item_list_separator"] = ttk.Separator(frame, orient='horizontal')
        frame.entries["item_list_title_label"] = tk.Label(frame, text=f"Existing {default_type.capitalize()}s:")

        listbox_frame_widget = ttk.Frame(frame)
        item_listbox_widget = tk.Listbox(listbox_frame_widget, height=8, exportselection=0)
        item_listbox_scrollbar = ttk.Scrollbar(listbox_frame_widget, orient=tk.VERTICAL, command=item_listbox_widget.yview)
        item_listbox_widget.config(yscrollcommand=item_listbox_scrollbar.set)
        item_listbox_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        item_listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        frame.entries["item_listbox_frame"] = listbox_frame_widget
        frame.entries["item_listbox"] = item_listbox_widget

        frame.columnconfigure(1, weight=1)
        self.update_dynamic_fields(frame) # Initial layout based on default_type

        def populate_listbox_for_tab(tab_frame, item_type_filter):
            listbox = tab_frame.entries["item_listbox"]
            listbox.delete(0, tk.END)
            filtered = [(item_id, data) for item_id, data in self.items.items() if data.get("type","").lower() == item_type_filter]
            for item_id, data_val in sorted(filtered, key=lambda x: x[0]):
                listbox.insert(tk.END, f"{item_id} - {data_val.get('name', item_id)}")

        populate_listbox_for_tab(frame, default_type) # Populate for current tab

        frame.entries["item_listbox"].bind("<<ListboxSelect>>", lambda e, fr=frame: self.on_listbox_item_select(e, fr))


        if not hasattr(self, '_refresh_all_item_lists_func'): # Define only once
            def _refresh_all_lists_func():
                self.items = self.load_items() # Reload items before refreshing lists
                for cat_name, tab_fr in self.tabs.items():
                    item_type_for_this_tab = self.category_types[cat_name]
                    populate_listbox_for_tab(tab_fr, item_type_for_this_tab)
            self._refresh_all_item_lists_func = _refresh_all_lists_func
        self.refresh_all_item_lists = self._refresh_all_item_lists_func


    def on_listbox_item_select(self, event, frame):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            item_text = widget.get(index)
            item_id_selected = item_text.split(" - ")[0]
            frame.entries["id"].delete(0, tk.END)
            frame.entries["id"].insert(0, item_id_selected)
            self.load_item_into_form(frame)


    def show_item_help(self):
        help_text = (
            "Item Editor Help:\n\n"
            "- Item ID: Unique identifier (e.g., 'short_sword', 'potion_healing'). Cannot be changed after creation.\n"
            "- Name: Display name (e.g., 'Short Sword', 'Potion of Healing').\n"
            "- Description: In-game description.\n"
            "- Type: Select from dropdown (weapon, armor, consumable, container, light, misc).\n"
            "- Weight: Numeric weight.\n"
            "- Equip Slots (for weapon/armor/light): Select where it can be equipped.\n"
            "- Min/Max Damage (for weapon): Base damage values.\n"
            "- Capacity (for container): Max weight it can hold.\n"
            "- Effects (JSON): Advanced properties. Examples:\n"
            "  Stats: {\"bonus_stats\": {\"STR\": 2, \"DEX\": -1}}\n"
            "  AC Bonus: {\"bonus_ac\": 1}\n"
            "  HP Bonus: {\"bonus_hp\": 10}\n"
            "  Weapon Properties: {\"finesse\": true, \"damage_dice\": \"1d8\", \"damage_type\": \"slashing\"}\n"
            "  Armor Properties: {\"armor_type\": \"heavy\", \"base_ac_value\": 16, \"dex_cap_bonus\": 0}\n"
            "  Container: {\"container_capacity_weight\": 50}\n"
            "  Light: {\"light_radius\": 5, \"light_color\": \"yellow\"}\n"
            "IMPORTANT: For WEAPONS, 'damage_dice' and 'damage_type' should be in 'properties' (within Effects JSON), NOT Min/Max Damage fields.\n"
            "Min/Max Damage fields are for a simpler damage model if 'damage_dice' is not used."
        )
        messagebox.showinfo("Item Editor Help", help_text, parent=self)


    def load_item_into_form(self, frame):
        item_id = frame.entries["id"].get().strip()
        if not item_id:
            current_type = frame.entries["type_var"].get() # Preserve current type for new item
            frame.entries["name"].delete(0, tk.END)
            frame.entries["description"].delete("1.0", tk.END)
            frame.entries["weight"].delete(0, tk.END)
            frame.entries["effects_text_widget"].delete("1.0", tk.END)
            self.update_dynamic_fields(frame) # Update visibility based on current type
            return

        item_data = self.items.get(item_id)
        if not item_data:
            # Keep ID, clear other fields, set type to current tab's default
            current_tab_name = self.notebook.tab(self.notebook.select(), "text")
            default_type_for_tab = self.category_types.get(current_tab_name, "misc")
            frame.entries["type_var"].set(default_type_for_tab)

            frame.entries["name"].delete(0, tk.END)
            frame.entries["description"].delete("1.0", tk.END)
            frame.entries["weight"].delete(0, tk.END)
            frame.entries["effects_text_widget"].delete("1.0", tk.END)
            self.update_dynamic_fields(frame)
            return

        frame.entries["name"].delete(0, tk.END)
        frame.entries["name"].insert(0, item_data.get("name", ""))
        frame.entries["description"].delete("1.0", tk.END)
        frame.entries["description"].insert(tk.END, item_data.get("description", ""))

        item_type = item_data.get("type", "")
        frame.entries["type_var"].set(item_type) # This should trigger update_dynamic_fields via FocusOut/Return or ComboboxSelected

        frame.entries["weight"].delete(0, tk.END)
        frame.entries["weight"].insert(0, str(item_data.get("weight", "")))

        self.update_dynamic_fields(frame) # Call explicitly to ensure layout is correct after type set

        # Populate dynamic fields based on the now-set type
        if item_type == "weapon":
            props = item_data.get("properties", {})
            frame.entries["min_dmg_entry"].delete(0, tk.END) # min_damage is no longer primary
            frame.entries["min_dmg_entry"].insert(0, str(props.get("min_damage", ""))) # Keep for legacy or simple view
            frame.entries["max_dmg_entry"].delete(0, tk.END) # max_damage is no longer primary
            frame.entries["max_dmg_entry"].insert(0, str(props.get("max_damage", "")))

        if item_type in ["weapon", "armor", "light"]:
            frame.entries["equip_listbox_widget"].selection_clear(0, tk.END)
            item_slots = item_data.get("equip_slots", [])
            if not isinstance(item_slots, list): item_slots = [] # Ensure it's a list
            for i, slot_name_option in enumerate(EQUIP_SLOTS):
                if slot_name_option in item_slots:
                    frame.entries["equip_listbox_widget"].selection_set(i)

        if item_type == "container":
            props = item_data.get("properties", {})
            frame.entries["capacity_entry"].delete(0, tk.END)
            frame.entries["capacity_entry"].insert(0, str(props.get("container_capacity_weight", "")))

        effects_data = item_data.get("effects", {}) # Effects are now the primary store for properties too
        frame.entries["effects_text_widget"].delete("1.0", tk.END)
        frame.entries["effects_text_widget"].insert(tk.END, json.dumps(effects_data, indent=2))


    def save_item_from_form(self, frame):
        item_id = frame.entries["id"].get().strip()
        if not item_id: messagebox.showerror("Error", "Item ID is required.", parent=self); return

        name = frame.entries["name"].get().strip()
        if not name: messagebox.showerror("Error", "Name is required.", parent=self); return

        description = frame.entries["description"].get("1.0", tk.END).strip()
        item_type = frame.entries["type_var"].get().strip().lower()

        try: weight = float(frame.entries["weight"].get().strip() or 0)
        except ValueError: messagebox.showerror("Error", "Weight must be a number.", parent=self); return
        if weight < 0: messagebox.showerror("Error", "Weight cannot be negative.", parent=self); return

        equip_slots = []
        if item_type in ["weapon", "armor", "light"] and "equip_listbox_widget" in frame.entries and frame.entries["equip_listbox_widget"].winfo_exists():
            equip_slots = [frame.entries["equip_listbox_widget"].get(i) for i in frame.entries["equip_listbox_widget"].curselection()]

        properties = {} # Will be part of effects dict for simplicity now
        effects_json_str = frame.entries["effects_text_widget"].get("1.0", tk.END).strip()
        final_effects_and_props = {}
        if effects_json_str:
            try:
                final_effects_and_props = json.loads(effects_json_str)
                if not isinstance(final_effects_and_props, dict):
                    raise json.JSONDecodeError("Effects must be a JSON object.", effects_json_str, 0)
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON in Effects field: {e}", parent=self); return

        # Specific handling for weapon/container properties if not in JSON, or to override JSON
        if item_type == "weapon":
            min_d = frame.entries["min_dmg_entry"].get().strip()
            max_d = frame.entries["max_dmg_entry"].get().strip()
            if min_d or max_d: # If these fields are used, they are for a simpler model
                final_effects_and_props.setdefault("properties", {})
                try:
                    final_effects_and_props["properties"]["min_damage"] = int(min_d) if min_d else 0
                    final_effects_and_props["properties"]["max_damage"] = int(max_d) if max_d else 0
                    if final_effects_and_props["properties"]["min_damage"] < 0 or \
                       final_effects_and_props["properties"]["max_damage"] < 0:
                        raise ValueError("Damage cannot be negative")
                    if final_effects_and_props["properties"]["min_damage"] > final_effects_and_props["properties"]["max_damage"]:
                         messagebox.showerror("Error", "Min Damage cannot exceed Max Damage.", parent=self); return
                except ValueError:
                     messagebox.showerror("Error", "Min/Max Damage must be valid non-negative integers.", parent=self); return
            # Damage dice and type should be in properties within effects JSON for D&D model

        if item_type == "container":
            cap_str = frame.entries["capacity_entry"].get().strip()
            if cap_str:
                try:
                    final_effects_and_props.setdefault("properties", {})["container_capacity_weight"] = int(cap_str)
                    if final_effects_and_props["properties"]["container_capacity_weight"] < 0: raise ValueError()
                except ValueError:
                    messagebox.showerror("Error", "Capacity must be a non-negative integer.", parent=self); return

        item_data = {
            "name": name, "description": description, "type": item_type,
            "weight": weight, "equip_slots": equip_slots,
            "effects": final_effects_and_props # This now includes properties
            # "value" field could be added here if there's a UI for it
        }

        self.items[item_id] = item_data
        self.save_items() # This calls refresh_all_item_lists

class MudAdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MUD Admin Editor") # Changed title
        self.geometry("950x650") # Slightly larger

        self.notebook = ttk.Notebook(self) # Renamed from tab_control for clarity

        self.world_editor_tab = WorldEditor(self.notebook)
        self.notebook.add(self.world_editor_tab, text="World Editor")

        self.item_editor_tab = ItemEditor(self.notebook)
        self.notebook.add(self.item_editor_tab, text="Item Editor")

        # Add MobEditor Tab
        self.mob_editor_tab = MobEditor(self.notebook)
        self.notebook.add(self.mob_editor_tab, text="Mob Editor")

        self.notebook.pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = MudAdminApp()
    app.mainloop()

# RoomEditorFrame needs to be defined for WorldEditor to work fully
# For now, this is a simplified placeholder.
# A full implementation would involve listboxes for mob_definitions and item_definitions,
# with controls to add/remove/edit them, linking to Mob IDs and Item IDs.
# It would also need to handle saving these definitions back to self.world_data[self.room_id].

# The current WorldEditor saves only description and exits.
# The MobEditor is a basic structure.
# The ItemEditor has been significantly refactored for dynamic fields.

[end of mud_admin_app.py]
