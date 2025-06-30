import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

WORLD_FILE = "server/data/world.json"
ITEMS_FILE = "server/data/items.json"
MOBS_FILE = "server/data/mobs.json"

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
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') and callable(self.widget.bbox) else (0,0,0,0)
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
        self.mobs = self.load_mobs_data()

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.list_frame = ttk.Frame(self.main_frame)
        self.list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(self.list_frame, text="Mobs:").pack(anchor="w")
        self.mob_listbox = tk.Listbox(self.list_frame, width=30, exportselection=0)
        self.mob_listbox.pack(fill=tk.Y, expand=True)
        self.mob_listbox.bind("<<ListboxSelect>>", self.on_mob_select)

        self.form_frame = ttk.Frame(self.main_frame)
        self.form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.entries = {}
        fields = [
            ("Mob ID:", "mob_id", True),
            ("Name:", "name", False),
            ("Description:", "description", False, {"type": "text", "height": 3}),
            ("Max HP:", "max_hp", False),
            ("Speed:", "speed", False),
            ("AC:", "ac", False),
            ("Attack Bonus:", "attack_bonus", False),
            ("Damage Dice:", "damage_dice", False),
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
            if key == "mob_id":
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

    def load_mobs_data(self):
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

    def save_mobs_data(self):
        try:
            with open(MOBS_FILE, "w") as f:
                json.dump(self.mobs, f, indent=2)
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
            self.entries["mob_id"].config(state=tk.NORMAL)
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
            self.clear_form()
            return

        mob_data = self.mobs.get(mob_id)
        if not mob_data:
            for key, entry_widget in self.entries.items():
                if key != "mob_id":
                    if isinstance(entry_widget, tk.Text): entry_widget.delete("1.0", tk.END)
                    else: entry_widget.delete(0, tk.END)
            self.entries["mob_id"].config(state=tk.NORMAL) # Allow editing if mob not found
            return

        self.entries["mob_id"].config(state=tk.DISABLED)

        for key, entry_widget in self.entries.items():
            if key == "mob_id": continue
            value = mob_data.get(key, "")
            if isinstance(entry_widget, tk.Text):
                entry_widget.delete("1.0", tk.END)
                if isinstance(value, dict) or isinstance(value, list):
                    entry_widget.insert(tk.END, json.dumps(value, indent=2))
                else:
                    entry_widget.insert(tk.END, str(value))
            else:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, str(value))

    def save_mob(self):
        # Mob ID must be enabled to get it, then can be disabled again if it exists
        self.entries["mob_id"].config(state=tk.NORMAL)
        mob_id = self.entries["mob_id"].get().strip()
        self.entries["mob_id"].config(state=tk.DISABLED if mob_id in self.mobs else tk.NORMAL)

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
                        mob_data_to_save[key] = {}
                else:
                     mob_data_to_save[key] = value_str
            else:
                value_str = entry_widget.get().strip()
                if key in ["max_hp", "speed", "ac", "attack_bonus", "xp_value"]:
                    try: mob_data_to_save[key] = int(value_str) if value_str else 0
                    except ValueError: messagebox.showerror("Error", f"{key.replace('_', ' ').title()} must be an integer."); return
                elif key == "is_aggressive":
                    mob_data_to_save[key] = value_str.lower() == 'true'
                else:
                    mob_data_to_save[key] = value_str

        is_new_mob = mob_id not in self.mobs
        self.mobs[mob_id] = mob_data_to_save
        self.save_mobs_data()
        self.entries["mob_id"].config(state=tk.DISABLED) # Ensure it's disabled after save if it's an existing mob
        messagebox.showinfo("Saved", f"Mob '{mob_id}' saved.")
        if is_new_mob:
            self.refresh_mob_list() # Ensure list is up-to-date
            # Try to select the new mob in the listbox
            for i, item_text in enumerate(self.mob_listbox.get(0, tk.END)):
                if item_text.startswith(mob_id):
                    self.mob_listbox.selection_clear(0, tk.END)
                    self.mob_listbox.selection_set(i)
                    self.mob_listbox.see(i)
                    break


    def delete_mob(self):
        self.entries["mob_id"].config(state=tk.NORMAL) # Enable to get ID
        mob_id = self.entries["mob_id"].get().strip()

        if not mob_id:
            messagebox.showerror("Error", "No Mob ID specified to delete.")
            self.entries["mob_id"].config(state=tk.DISABLED if self.mob_listbox.curselection() else tk.NORMAL) # Re-disable if one was selected
            return
        if mob_id not in self.mobs:
            messagebox.showerror("Error", f"Mob ID '{mob_id}' not found.")
            self.entries["mob_id"].config(state=tk.DISABLED if self.mob_listbox.curselection() else tk.NORMAL)
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete mob '{mob_id}' - {self.mobs[mob_id].get('name', '')}?"):
            del self.mobs[mob_id]
            self.save_mobs_data()
            self.clear_form() # This also enables mob_id field
            messagebox.showinfo("Deleted", f"Mob '{mob_id}' deleted.")
        else: # If user says no, re-disable mob_id if it was loaded from selection
            self.entries["mob_id"].config(state=tk.DISABLED if self.mob_listbox.curselection() else tk.NORMAL)


class WorldEditor(ttk.Frame):
    DIRECTIONS = ["north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest"]

    def __init__(self, master):
        super().__init__(master)
        self.world_data = {}
        self.items_data = self.load_json_data(ITEMS_FILE, "items")
        self.mobs_data = self.load_json_data(MOBS_FILE, "mobs")

        self.selected_room_id = None
        self.autosave_after_id = None

        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

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

        self.room_editor_frame_container = ttk.Frame(self.paned_window)
        self.paned_window.add(self.room_editor_frame_container, weight=3)

        self.current_room_editor = None

        self.bottom_button_frame = ttk.Frame(self)
        self.bottom_button_frame.pack(fill=tk.X, pady=5)
        self.new_room_btn = ttk.Button(self.bottom_button_frame, text="New Room", command=self.new_room)
        self.new_room_btn.pack(side=tk.LEFT, padx=5)
        self.save_all_btn = ttk.Button(self.bottom_button_frame, text="Save World", command=self.save_world_data_to_file)
        self.save_all_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(self.bottom_button_frame, text="", foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.load_world_data_from_file()

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
        if self.room_listbox.size() > 0:
            self.room_listbox.selection_set(0)
            self.on_room_select(None)

    def save_world_data_to_file(self):
        if self.current_room_editor and self.selected_room_id:
            self.current_room_editor.apply_changes_to_world_data()

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
        current_selection = self.room_listbox.curselection()
        current_selected_id = None
        if current_selection:
            current_selected_id = self.room_listbox.get(current_selection[0])

        self.room_listbox.delete(0, tk.END)
        sorted_room_ids = sorted(self.world_data.keys())
        for room_id in sorted_room_ids:
            self.room_listbox.insert(tk.END, room_id)

        if current_selected_id and current_selected_id in sorted_room_ids:
            try:
                idx = sorted_room_ids.index(current_selected_id)
                self.room_listbox.selection_set(idx)
                self.room_listbox.see(idx)
            except ValueError:
                pass # Should not happen if logic is correct

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
             if self.selected_room_id and self.current_room_editor:
                self.current_room_editor.apply_changes_to_world_data()

        self.selected_room_id = room_id

        if self.current_room_editor:
            self.current_room_editor.destroy()

        self.current_room_editor = RoomEditorFrame(
            self.room_editor_frame_container,
            room_id,
            self.world_data,
            self.mobs_data,
            self.items_data,
            self.save_world_data_to_file
        )
        self.current_room_editor.pack(fill=tk.BOTH, expand=True)

    def new_room(self):
        new_id = simpledialog.askstring("New Room", "Enter new unique room ID:", parent=self)
        if new_id:
            new_id = new_id.strip().replace(" ", "_")
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
                "mob_definitions": [],
                "item_definitions": []
            }
            self.refresh_room_list()
            try:
                idx = list(sorted(self.world_data.keys())).index(new_id)
                self.room_listbox.selection_clear(0, tk.END)
                self.room_listbox.selection_set(idx)
                self.room_listbox.see(idx)
                self.on_room_select(None)
                self.save_world_data_to_file()
            except ValueError:
                pass

class RoomEditorFrame(ttk.Frame):
    DIRECTIONS = ["north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest"]
    def __init__(self, master, room_id, world_data_ref, mobs_data_ref, items_data_ref, save_callback):
        super().__init__(master)
        self.room_id = room_id
        self.world_data = world_data_ref
        self.mobs_data = mobs_data_ref
        self.items_data = items_data_ref
        self.save_world_callback = save_callback

        self.room_data_dict = self.world_data.setdefault(self.room_id, {})

        self.room_data_dict.setdefault("exits", {})
        self.room_data_dict.setdefault("mob_definitions", [])
        self.room_data_dict.setdefault("item_definitions", [])

        self.available_mob_ids = sorted(list(self.mobs_data.keys())) # For Mob ID Combobox

        self.autosave_after_id = None
        self.selected_mob_def_index = None # To track which mob definition is being edited
        self._build_ui()
        self._load_room_data()

    def _build_ui(self):
        id_frame = ttk.Frame(self)
        id_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(id_frame, text="Room ID:").pack(side=tk.LEFT)
        self.id_display = ttk.Label(id_frame, text=self.room_id)
        self.id_display.pack(side=tk.LEFT, padx=5)
        ttk.Button(id_frame, text="Delete This Room", command=self.confirm_delete_room).pack(side=tk.RIGHT)

        name_frame = ttk.Frame(self)
        name_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT, anchor='w')
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.pack(fill=tk.X, expand=True)
        self.name_entry.bind("<<Modified>>", self.schedule_autosave)
        ToolTip(self.name_entry, "Display name for the room.")

        ttk.Label(self, text="Description:").pack(anchor="w", padx=5, pady=(5,0))
        self.desc_text = tk.Text(self, height=5, width=70, wrap=tk.WORD, undo=True)
        self.desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.desc_text.bind("<<Modified>>", self.schedule_autosave)
        ToolTip(self.desc_text, "Full description of the room. Use multiple lines.")

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

        # Mob Definitions UI
        mobs_main_frame = ttk.LabelFrame(self, text="Mob Spawns (Definitions)")
        mobs_main_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        mob_list_container = ttk.Frame(mobs_main_frame)
        mob_list_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.mob_defs_listbox = tk.Listbox(mob_list_container, height=5, exportselection=0)
        self.mob_defs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mob_defs_scrollbar = ttk.Scrollbar(mob_list_container, orient=tk.VERTICAL, command=self.mob_defs_listbox.yview)
        self.mob_defs_listbox.config(yscrollcommand=mob_defs_scrollbar.set)
        mob_defs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.mob_defs_listbox.bind("<<ListboxSelect>>", self._on_mob_def_select)

        mob_controls_frame = ttk.Frame(mobs_main_frame)
        mob_controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        ttk.Label(mob_controls_frame, text="Mob ID:").grid(row=0, column=0, sticky="w", pady=2)
        self.mob_def_id_var = tk.StringVar()
        self.mob_def_id_combobox = ttk.Combobox(mob_controls_frame, textvariable=self.mob_def_id_var, values=self.available_mob_ids, state="readonly", width=20)
        self.mob_def_id_combobox.grid(row=0, column=1, sticky="ew", pady=2)
        ToolTip(self.mob_def_id_combobox, "Select Mob ID from defined mobs.")
        ttk.Label(mob_controls_frame, text="Max Quantity:").grid(row=1, column=0, sticky="w", pady=2)
        self.mob_def_qty_var = tk.StringVar(value="1")
        self.mob_def_qty_spinbox = ttk.Spinbox(mob_controls_frame, from_=1, to=100, textvariable=self.mob_def_qty_var, width=5)
        self.mob_def_qty_spinbox.grid(row=1, column=1, sticky="w", pady=2)
        ToolTip(self.mob_def_qty_spinbox, "Max number of this mob to spawn.")
        ttk.Label(mob_controls_frame, text="Respawn (sec):").grid(row=2, column=0, sticky="w", pady=2)
        self.mob_def_respawn_var = tk.StringVar(value="300")
        self.mob_def_respawn_spinbox = ttk.Spinbox(mob_controls_frame, from_=0, to=36000, increment=30, textvariable=self.mob_def_respawn_var, width=7)
        self.mob_def_respawn_spinbox.grid(row=2, column=1, sticky="w", pady=2)
        ToolTip(self.mob_def_respawn_spinbox, "Seconds until respawn. 0 for no timer-based respawn.")
        mob_buttons_frame = ttk.Frame(mob_controls_frame)
        mob_buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)
        self.add_mob_def_button = ttk.Button(mob_buttons_frame, text="Add/Update Mob", command=self._add_or_update_mob_definition)
        self.add_mob_def_button.pack(side=tk.LEFT, padx=2)
        ToolTip(self.add_mob_def_button, "Add new mob spawn or update selected one.")
        self.remove_mob_def_button = ttk.Button(mob_buttons_frame, text="Remove Mob", command=self._remove_selected_mob_definition)
        self.remove_mob_def_button.pack(side=tk.LEFT, padx=2)
        ToolTip(self.remove_mob_def_button, "Remove selected mob spawn from this room.")
        self.clear_mob_def_fields_button = ttk.Button(mob_controls_frame, text="Clear Fields", command=self._clear_mob_def_fields)
        self.clear_mob_def_fields_button.grid(row=4, column=0, columnspan=2, pady=2)


        items_frame = ttk.LabelFrame(self, text="Item Spawns (Definitions)")
        items_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        self.item_defs_listbox = tk.Listbox(items_frame, height=4, exportselection=0)
        self.item_defs_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

    def _load_room_data(self):
        self.name_var.set(self.room_data_dict.get("name", self.room_id.replace("_", " ").title()))
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", self.room_data_dict.get("description", ""))
        self.desc_text.edit_modified(False)
        self._refresh_exits_listbox()
        self._refresh_mob_defs_listbox()
        self._refresh_item_defs_listbox()
        self._clear_mob_def_fields() # Start with clean fields for mob defs

    def _refresh_exits_listbox(self):
        self.exits_listbox.delete(0, tk.END)
        for direction, dest_id in sorted(self.room_data_dict.get("exits", {}).items()):
            self.exits_listbox.insert(tk.END, f"{direction}: {dest_id}")

    def _refresh_mob_defs_listbox(self):
        self.mob_defs_listbox.delete(0, tk.END)
        # Ensure "mob_definitions" exists and is a list
        mob_defs_list = self.room_data_dict.get("mob_definitions", [])
        if not isinstance(mob_defs_list, list): # Defensive check
            mob_defs_list = []
            self.room_data_dict["mob_definitions"] = mob_defs_list

        for i, mob_def in enumerate(mob_defs_list):
            mob_id = mob_def.get("mob_id", "Unknown ID")
            mob_name = self.mobs_data.get(mob_id, {}).get("name", mob_id)
            qty = mob_def.get("max_quantity", mob_def.get("quantity",1)) # Prioritize max_quantity
            respawn = mob_def.get("respawn_seconds",0)
            self.mob_defs_listbox.insert(tk.END, f"{mob_name} (ID: {mob_id}) x{qty} [Respawn: {respawn}s]")
        self._clear_mob_def_fields() # Clear fields after refresh unless one is selected


    def _refresh_item_defs_listbox(self):
        self.item_defs_listbox.delete(0, tk.END)
        item_defs_list = self.room_data_dict.get("item_definitions", [])
        if not isinstance(item_defs_list, list):
            item_defs_list = []
            self.room_data_dict["item_definitions"] = item_defs_list

        for item_def in item_defs_list:
            item_name = self.items_data.get(item_def.get("item_id"), {}).get("name", item_def.get("item_id"))
            qty = item_def.get("quantity",1)
            respawn = item_def.get("respawn_seconds",0)
            self.item_defs_listbox.insert(tk.END, f"{item_name} (ID: {item_def.get('item_id')}) x{qty} [Respawn: {respawn}s]")

    def _on_mob_def_select(self, event):
        selection = self.mob_defs_listbox.curselection()
        if not selection:
            self.selected_mob_def_index = None
            self._clear_mob_def_fields() # Clear if selection lost
            return

        self.selected_mob_def_index = selection[0]
        mob_def_data = self.room_data_dict["mob_definitions"][self.selected_mob_def_index]

        self.mob_def_id_var.set(mob_def_data.get("mob_id", ""))
        self.mob_def_qty_var.set(str(mob_def_data.get("max_quantity", mob_def_data.get("quantity", "1"))))
        self.mob_def_respawn_var.set(str(mob_def_data.get("respawn_seconds", "300")))

    def _clear_mob_def_fields(self):
        self.mob_def_id_var.set("")
        if self.available_mob_ids: # Set to first if available, else empty
            self.mob_def_id_combobox.set(self.available_mob_ids[0] if self.available_mob_ids else "")
        else:
            self.mob_def_id_combobox.set("")

        self.mob_def_qty_var.set("1")
        self.mob_def_respawn_var.set("300")
        self.mob_defs_listbox.selection_clear(0, tk.END) # Clear listbox selection
        self.selected_mob_def_index = None


    def _add_or_update_mob_definition(self):
        mob_id = self.mob_def_id_var.get()
        if not mob_id:
            messagebox.showerror("Input Error", "Mob ID must be selected.", parent=self)
            return
        try:
            quantity = int(self.mob_def_qty_var.get())
            if quantity < 1: raise ValueError("Quantity must be at least 1.")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid quantity: {e}", parent=self)
            return
        try:
            respawn_seconds = int(self.mob_def_respawn_var.get())
            if respawn_seconds < 0: raise ValueError("Respawn seconds cannot be negative.")
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid respawn seconds: {e}", parent=self)
            return

        new_mob_def = {
            "mob_id": mob_id,
            "max_quantity": quantity, # Consistently use max_quantity
            "respawn_seconds": respawn_seconds
        }

        mob_definitions = self.room_data_dict.setdefault("mob_definitions", [])

        # Check if this mob_id already exists for update logic (simple version: only one entry per mob_id)
        # A more complex version might allow multiple definitions for the same mob_id if that's desired.
        # For now, assume we update if selected, or add if new mob_id (or no selection)

        updated_existing = False
        if self.selected_mob_def_index is not None and self.selected_mob_def_index < len(mob_definitions):
            # If the mob_id is changing for the selected entry, or if it's the same mob_id
            # This logic implicitly updates the selected entry.
            mob_definitions[self.selected_mob_def_index] = new_mob_def
            updated_existing = True
        else:
            # If no selection, or selection is somehow invalid, try to find by mob_id to update, or add new
            # This makes the "Add/Update" button more robust.
            found_and_updated = False
            for i, existing_def in enumerate(mob_definitions):
                if existing_def.get("mob_id") == mob_id:
                    mob_definitions[i] = new_mob_def
                    found_and_updated = True
                    break
            if not found_and_updated:
                mob_definitions.append(new_mob_def)

        self._refresh_mob_defs_listbox()
        self.schedule_autosave()
        # self._clear_mob_def_fields() # Optionally clear after add/update

    def _remove_selected_mob_definition(self):
        if self.selected_mob_def_index is None : # Check if any item is selected
            messagebox.showwarning("Selection Error", "No mob definition selected to remove.", parent=self)
            return

        # Ensure the index is valid before trying to delete
        mob_definitions = self.room_data_dict.get("mob_definitions", [])
        if self.selected_mob_def_index >= len(mob_definitions):
            messagebox.showerror("Internal Error", "Selected mob definition index out of bounds. Please re-select.", parent=self)
            self._clear_mob_def_fields() # Clear selection and fields
            self._refresh_mob_defs_listbox()
            return

        # Confirmation dialog
        selected_mob_text = self.mob_defs_listbox.get(self.selected_mob_def_index) # Get text for confirmation
        if not messagebox.askyesno("Confirm Remove", f"Are you sure you want to remove this mob spawn?\n\n{selected_mob_text}", parent=self):
            return

        del mob_definitions[self.selected_mob_def_index]
        self.room_data_dict["mob_definitions"] = mob_definitions # Ensure the main dict is updated

        self._refresh_mob_defs_listbox() # This will also call _clear_mob_def_fields, resetting selected_mob_def_index
        self.schedule_autosave()
        messagebox.showinfo("Removed", "Mob definition removed.", parent=self)


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

    def schedule_autosave(self, event=None):
        if event and hasattr(event.widget, 'edit_modified') and event.widget.edit_modified():
             event.widget.edit_modified(False)

        if self.autosave_after_id:
            self.after_cancel(self.autosave_after_id)
        self.autosave_after_id = self.after(1000, self.apply_changes_to_world_data_and_save)

    def apply_changes_to_world_data(self):
        self.room_data_dict["name"] = self.name_var.get()
        self.room_data_dict["description"] = self.desc_text.get("1.0", tk.END).strip()

    def apply_changes_to_world_data_and_save(self):
        self.apply_changes_to_world_data()
        if self.save_world_callback:
            self.save_world_callback()
            if hasattr(self.master.master, 'status_label'):
                 self.master.master.status_label.config(text=f"Room '{self.room_id}' auto-saved.", foreground="blue")

    def confirm_delete_room(self):
        if messagebox.askyesno("Delete Room", f"Are you sure you want to delete room '{self.room_id}'?\nThis cannot be undone.", parent=self):
            if self.room_id in self.world_data:
                del self.world_data[self.room_id]
                self.master.master.refresh_room_list()
                self.master.master.selected_room_id = None
                if self.master.master.current_room_editor == self:
                    self.master.master.current_room_editor.destroy()
                    self.master.master.current_room_editor = None
                self.save_world_callback()
                messagebox.showinfo("Room Deleted", f"Room '{self.room_id}' has been deleted.", parent=self.master.master)
            self.destroy()


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
            if hasattr(self, 'refresh_all_item_lists'):
                self.refresh_all_item_lists()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save items:\n{e}")

    def update_dynamic_fields(self, frame):
        current_type = frame.entries["type_var"].get().strip().lower()
        row = frame.dynamic_fields_start_row

        for key in ["min_dmg_label", "min_dmg_entry", "max_dmg_label", "max_dmg_entry",
                    "equip_slots_label", "equip_listbox_widget", "capacity_label", "capacity_entry"]:
            if key in frame.entries and frame.entries[key].winfo_exists():
                frame.entries[key].grid_forget()

        if "min_dmg" in frame.entries and frame.entries["min_dmg"].winfo_exists(): frame.entries["min_dmg"].delete(0, tk.END)
        if "max_dmg" in frame.entries and frame.entries["max_dmg"].winfo_exists(): frame.entries["max_dmg"].delete(0, tk.END)
        if "equip_slots" in frame.entries and frame.entries["equip_slots"].winfo_exists(): frame.entries["equip_slots"].selection_clear(0, tk.END)
        if "capacity" in frame.entries and frame.entries["capacity"].winfo_exists(): frame.entries["capacity"].delete(0, tk.END)

        if current_type == "weapon":
            frame.entries["min_dmg_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["min_dmg_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["min_dmg"] = frame.entries["min_dmg_entry"]
            row += 1
            frame.entries["max_dmg_label"].grid(row=row, column=0, sticky="w", padx=2, pady=1)
            frame.entries["max_dmg_entry"].grid(row=row, column=1, sticky="ew", padx=2, pady=1)
            frame.entries["max_dmg"] = frame.entries["max_dmg_entry"]
            row += 1

        if current_type in ["weapon", "armor", "light"]:
            frame.entries["equip_slots_label"].grid(row=row, column=0, sticky="nw", padx=2, pady=1)
            frame.entries["equip_listbox_widget"].grid(row=row, column=1, sticky="ew", rowspan=2, padx=2, pady=1)
            frame.entries["equip_slots"] = frame.entries["equip_listbox_widget"]
            row += 2

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
        frame.entries["type_var"] = type_var
        frame.entries["type_entry"] = type_entry
        current_layout_row += 1

        tk.Label(frame, text="Weight:").grid(row=current_layout_row, column=0, sticky="w", padx=2, pady=1)
        weight_entry = tk.Entry(frame)
        weight_entry.grid(row=current_layout_row, column=1, sticky="ew", padx=2, pady=1)
        frame.entries["weight"] = weight_entry
        current_layout_row += 1

        frame.dynamic_fields_start_row = current_layout_row

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
        self.update_dynamic_fields(frame)

        def populate_listbox_for_tab(tab_frame, item_type_filter):
            listbox = tab_frame.entries["item_listbox"]
            listbox.delete(0, tk.END)
            filtered = [(item_id, data) for item_id, data in self.items.items() if data.get("type","").lower() == item_type_filter]
            for item_id, data_val in sorted(filtered, key=lambda x: x[0]):
                listbox.insert(tk.END, f"{item_id} - {data_val.get('name', item_id)}")

        populate_listbox_for_tab(frame, default_type)

        frame.entries["item_listbox"].bind("<<ListboxSelect>>", lambda e, fr=frame: self.on_listbox_item_select(e, fr))

        if not hasattr(self, '_refresh_all_item_lists_func'):
            def _refresh_all_lists_func():
                self.items = self.load_items()
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
            # ... (rest of help text)
        )
        messagebox.showinfo("Item Editor Help", help_text, parent=self)

    def load_item_into_form(self, frame):
        item_id = frame.entries["id"].get().strip()
        if not item_id:
            current_type = frame.entries["type_var"].get()
            frame.entries["name"].delete(0, tk.END)
            frame.entries["description"].delete("1.0", tk.END)
            frame.entries["weight"].delete(0, tk.END)
            frame.entries["effects_text_widget"].delete("1.0", tk.END)
            self.update_dynamic_fields(frame)
            return

        item_data = self.items.get(item_id)
        if not item_data:
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
        frame.entries["type_var"].set(item_type)
        frame.entries["weight"].delete(0, tk.END)
        frame.entries["weight"].insert(0, str(item_data.get("weight", "")))
        self.update_dynamic_fields(frame)

        if item_type == "weapon":
            props = item_data.get("properties", {})
            frame.entries["min_dmg_entry"].delete(0, tk.END)
            frame.entries["min_dmg_entry"].insert(0, str(props.get("min_damage", "")))
            frame.entries["max_dmg_entry"].delete(0, tk.END)
            frame.entries["max_dmg_entry"].insert(0, str(props.get("max_damage", "")))

        if item_type in ["weapon", "armor", "light"]:
            frame.entries["equip_listbox_widget"].selection_clear(0, tk.END)
            item_slots = item_data.get("equip_slots", [])
            if not isinstance(item_slots, list): item_slots = []
            for i, slot_name_option in enumerate(EQUIP_SLOTS):
                if slot_name_option in item_slots:
                    frame.entries["equip_listbox_widget"].selection_set(i)

        if item_type == "container":
            props = item_data.get("properties", {})
            frame.entries["capacity_entry"].delete(0, tk.END)
            frame.entries["capacity_entry"].insert(0, str(props.get("container_capacity_weight", "")))

        effects_data = item_data.get("effects", {})
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
        effects_json_str = frame.entries["effects_text_widget"].get("1.0", tk.END).strip()
        final_effects_and_props = {}
        if effects_json_str:
            try:
                final_effects_and_props = json.loads(effects_json_str)
                if not isinstance(final_effects_and_props, dict):
                    raise json.JSONDecodeError("Effects must be a JSON object.", effects_json_str, 0)
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON in Effects field: {e}", parent=self); return
        if item_type == "weapon":
            min_d = frame.entries["min_dmg_entry"].get().strip()
            max_d = frame.entries["max_dmg_entry"].get().strip()
            if min_d or max_d:
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
            "effects": final_effects_and_props
        }
        self.items[item_id] = item_data
        self.save_items()

class MudAdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MUD Admin Editor")
        self.geometry("950x650")
        self.notebook = ttk.Notebook(self)
        self.world_editor_tab = WorldEditor(self.notebook)
        self.notebook.add(self.world_editor_tab, text="World Editor")
        self.item_editor_tab = ItemEditor(self.notebook)
        self.notebook.add(self.item_editor_tab, text="Item Editor")
        self.mob_editor_tab = MobEditor(self.notebook)
        self.notebook.add(self.mob_editor_tab, text="Mob Editor")
        self.notebook.pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = MudAdminApp()
    app.mainloop()
