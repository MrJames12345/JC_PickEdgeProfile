#!/usr/bin/env python
# Dashboard.py - Select Microsoft Edge profile using a grid of tiles

import json
import os
import sys
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
from PIL import Image, ImageTk
import utils

logger = utils.setup_logger(__file__)
logger.info("Starting Dashboard...")

# Constants
TITLE = "Dashboard"
COLUMNS = 3
PADDING_X = 15  # Horizontal padding between tiles
PADDING_Y = 2   # Further reduced vertical padding between tiles
TILE_WIDTH = 180
TILE_HEIGHT = 180

def launch_browser(command):
    """Launch the browser in settings.json with the selected profile"""
    try:
        logger.info(f"launch_browser called with command: {command}")
        # Run the command in a separate thread to avoid blocking the UI
        subprocess.Popen(command, shell=True)
    except Exception as e:
        logger.error(f"Error launching browser: {e}")
        print(f"Error launching browser: {e}")

def launch_editor(name):
    """Launch the editor with the workspace file or folder if it exists"""
    try:
        logger.info(f"launch_editor called for profile: '{name}' using editor: '{code_editor}'")

        # Use common util to resolve the target
        repo_path = "C:\\repo"
        target = utils.resolve_project_target(repo_path, name)
        
        # If target exists (either workspace file or project folder), launch it
        if target:
            utils.launch_code_editor(target, code_editor)
        else:
            logger.warn(f"No target found for profile: '{name}'")
    except Exception as e:
        logger.error(f"Error launching editor: {e}")
        print(f"Error launching editor: {e}")

def launch_sourcetree_for_profile(name):
    """Launch SourceTree for the matching project folder"""
    try:
        logger.info(f"launch_sourcetree_for_profile called for: '{name}'")
        repo_path = "C:\\repo"
        target = utils.resolve_project_target(repo_path, name)
        if target:
            logger.info(f"Resolved target for SourceTree: {target}")
            utils.launch_sourcetree(target)
        else:
            logger.warn(f"No target found to launch SourceTree for profile: '{name}'")
    except Exception as e:
        logger.error(f"Error launching SourceTree: {e}")
        print(f"Error launching SourceTree: {e}")

def select_profile(profile, ctrl_pressed=False, alt_pressed=False, shift_pressed=False):
    """Handle profile selection when a tile is clicked"""
    logger.info(f"select_profile called: name='{profile.get('name')}', shift={shift_pressed}, ctrl={ctrl_pressed}, alt={alt_pressed}")
    # If Shift is pressed, open the matching project in SourceTree and close app.
    # Must run synchronously: launch_sourcetree waits on SourceTree, and a daemon
    # thread would be killed as soon as the process exits after root.destroy().
    if shift_pressed:
        logger.info(f"Shift key active: Opening '{profile.get('name')}' in SourceTree and closing Dashboard")
        launch_sourcetree_for_profile(profile["name"])
        if root:
            root.destroy()
        return

    # If Alt is pressed, try to open the workspace and close app
    if alt_pressed:
        logger.info(f"Alt key active: Opening editor for '{profile.get('name')}' and closing Dashboard")
        launch_thread = threading.Thread(target=launch_editor, args=(profile["name"],))
        launch_thread.daemon = True
        launch_thread.start()
        # Close the window regardless of whether the editor was launched
        if root:
            root.destroy()
        return

    # Launch the browser selected in settings.json
    logger.info(f"Launching browser command for '{profile.get('name')}': {profile[PROFILE_COMMAND_KEY]}")
    launch_thread = threading.Thread(target=launch_browser, args=(profile[PROFILE_COMMAND_KEY],))
    launch_thread.daemon = True
    launch_thread.start()

    # If Ctrl is pressed, also launch the editor and SourceTree
    if ctrl_pressed:
        logger.info(f"Ctrl key active: also launching editor and SourceTree for '{profile.get('name')}'")
        editor_thread = threading.Thread(target=launch_editor, args=(profile["name"],))
        editor_thread.daemon = True
        editor_thread.start()
        # Synchronous for the same reason as the Shift branch above.
        launch_sourcetree_for_profile(profile["name"])

    # Close the window
    logger.info("Closing Dashboard window after profile selection")
    if root:
        root.destroy()

# Get the script directory
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_path = os.path.dirname(sys.executable)
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))

logger.info(f"Base path: {base_path}")
os.chdir(base_path)
logger.info(f"Base path and CWD: {base_path}")

profiles_file_path = os.path.join(base_path, "profiles.json")
logger.info(f"Loading profiles from: {profiles_file_path}")
EDGE_PROFILES = []
try:
    with open(profiles_file_path, "r", encoding="utf-8") as profiles_file:
        raw_profiles = profiles_file.read()
    try:
        EDGE_PROFILES = json.loads(raw_profiles)
    except json.JSONDecodeError as json_err:
        logger.warn(f"JSONDecodeError in profiles.json: {json_err}. Attempting recovery...")
        if hasattr(json_err, 'pos') and json_err.pos > 0:
            EDGE_PROFILES = json.loads(raw_profiles[:json_err.pos])
            logger.info(f"Successfully recovered {len(EDGE_PROFILES)} profiles.")
            try:
                with open(profiles_file_path, "w", encoding="utf-8") as f:
                    json.dump(EDGE_PROFILES, f, indent=4)
                    f.write("\n")
                logger.info("Self-healed profiles.json on disk.")
            except Exception as write_err:
                logger.warn(f"Could not rewrite profiles.json: {write_err}")
        else:
            raise
    logger.info(f"Successfully loaded {len(EDGE_PROFILES)} profiles from profiles.json")
except Exception as e:
    logger.error(f"Failed to load profiles.json: {e}")

app_settings = utils.load_settings(base_path)
browser_to_use = app_settings["browser_to_use"]
PROFILE_COMMAND_KEY = app_settings["profile_command_key"]
code_editor = app_settings["code_editor"]
logger.info(f"Using browserToUser='{browser_to_use}', PROFILE_COMMAND_KEY='{PROFILE_COMMAND_KEY}', codeEditor='{code_editor}'")

root = None

def create_dashboard():
    global root
    # Create the main window
    root = tk.Tk()
    utils.install_tk_exception_handler(root, logger)
    utils.attach_event_logger(root, logger)
    root.title(TITLE)
    # Let the window size adjust to its contents
    root.resizable(True, True)
    # Set the background color to #262626 (dark gray)
    root.configure(bg="#262626")

    # Set the window icon
    # Use Edge.png as the window favicon
    icon_path = os.path.join(base_path, "images", "Edge.png")
    # If Edge.png doesn't exist, fall back to CK.png
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_path, "images", "CK.png")

    if os.path.exists(icon_path):
        try:
            # Load the icon image
            icon = tk.PhotoImage(file=icon_path)
            # Set the window icon
            root.iconphoto(True, icon)
        except Exception as e:
            print(f"Error setting window icon: {e}")

    # Create main frame with padding
    main_frame = tk.Frame(root, padx=20, pady=20, bg="#262626")  # Standard padding
    main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=(0, 10))  # Add extra bottom padding in pack

    # Top bar / header frame with fixed height so title/search swap does not shift grid
    HEADER_HEIGHT = 48
    header_frame = tk.Frame(main_frame, bg="#262626", height=HEADER_HEIGHT)
    header_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 10))
    header_frame.pack_propagate(False)

    list_header = tk.Label(
        header_frame,
        text="Select Profile",
        font=("Segoe UI", 14, "bold"),
        fg="white",
        bg="#262626",
        cursor="hand2",
    )
    list_header.place(relx=0.5, rely=0.5, anchor="center")

    search_entry = tk.Entry(
        header_frame,
        font=("Segoe UI", 14, "bold"),
        fg="white",
        bg="#262626",
        insertbackground="white",
        relief=tk.FLAT,
        highlightthickness=0,
        bd=0,
        justify=tk.CENTER,
    )

    def on_editor_changed(new_editor):
        global code_editor
        code_editor = new_editor
        logger.info(f"Dashboard code_editor updated to: '{code_editor}'")

    editor_toggle = utils.create_editor_toggle(header_frame, base_path, code_editor, on_change=on_editor_changed)
    editor_toggle.place(relx=1.0, rely=0.5, anchor=tk.E)

    # Create a frame for the grid of tiles
    grid_frame = tk.Frame(main_frame, bg="#262626")
    grid_frame.pack(fill=tk.BOTH, expand=True)

    search_state = {"mode": False, "query": ""}
    matching_profiles = []
    image_cache = {}

    def get_profile_photo_image(profile_name):
        if profile_name in image_cache:
            return image_cache[profile_name]

        img = None
        try:
            image_path = os.path.join(base_path, "images", f"{profile_name}.png")
            if not os.path.exists(image_path):
                if profile_name == "AIMSProjectManagement":
                    image_path = os.path.join(base_path, "images", "AIMSInspection.png")
                else:
                    image_path = os.path.join(base_path, "images", "CK.png")
            if not os.path.exists(image_path):
                image_path = os.path.join(base_path, "images", "CK.png")

            if os.path.exists(image_path):
                pil_image = Image.open(image_path)
                max_width = TILE_WIDTH - 20
                max_height = TILE_HEIGHT - 20
                width_ratio = max_width / pil_image.width
                height_ratio = max_height / pil_image.height
                scale_factor = min(width_ratio, height_ratio)
                if scale_factor < 1:
                    new_width = int(pil_image.width * scale_factor)
                    new_height = int(pil_image.height * scale_factor)
                    pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img = ImageTk.PhotoImage(pil_image)
        except Exception as e:
            logger.error(f"Error loading image for '{profile_name}': {e}")
            img = None

        image_cache[profile_name] = img
        return img

    def populate_tiles():
        nonlocal matching_profiles
        for child in grid_frame.winfo_children():
            child.destroy()

        query = (search_state["query"] or "").strip().lower()
        matching = []
        for profile in EDGE_PROFILES:
            if query:
                raw_name = profile.get("name", "").lower()
                display_name = utils.split_camel_case(profile.get("name", "").replace("_", " ")).lower()
                clean_name = profile.get("name", "").replace("_", "").lower()
                if query not in raw_name and query not in display_name and query not in clean_name:
                    continue
            matching.append(profile)

        matching_profiles = matching
        total_profiles = len(matching)
        if total_profiles == 0:
            no_matches = tk.Label(
                grid_frame,
                text="No matching profiles",
                font=("Segoe UI", 11),
                fg="#888888",
                bg="#262626",
            )
            no_matches.grid(row=0, column=0, columnspan=COLUMNS, pady=40)
            return

        last_row_items = total_profiles % COLUMNS
        if last_row_items == 0:
            last_row_items = COLUMNS

        last_row_start_col = (COLUMNS - last_row_items) // 2 if last_row_items < COLUMNS else 0

        for i, profile in enumerate(matching):
            tile_frame = tk.Frame(
                grid_frame,
                width=TILE_WIDTH,
                height=TILE_HEIGHT,
                bd=0,
                relief=tk.FLAT,
                cursor="hand2",
                bg="#262626",
            )
            current_row = i // COLUMNS
            current_col = i % COLUMNS
            if current_row == total_profiles // COLUMNS and last_row_items < COLUMNS:
                current_col = last_row_start_col + (i % COLUMNS)

            tile_frame.grid(row=current_row, column=current_col, padx=PADDING_X, pady=PADDING_Y)
            tile_frame.pack_propagate(False)

            def handle_click(event, prof=profile):
                ctrl_pressed = bool(event.state & 0x4)
                alt_pressed = bool(event.state & 0x20000)
                shift_pressed = bool(event.state & 0x1)
                select_profile(prof, ctrl_pressed, alt_pressed, shift_pressed)

            img = get_profile_photo_image(profile["name"])
            if img:
                image_label = tk.Label(tile_frame, image=img, bg=tile_frame.cget("bg"))
                image_label.image = img
                image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
                image_label.bind("<Button-1>", handle_click)
            else:
                canvas = tk.Canvas(tile_frame, width=TILE_WIDTH - 20, height=TILE_HEIGHT - 20, bg="#7ec7d2")
                canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
                canvas.bind("<Button-1>", handle_click)

            tile_frame.bind("<Button-1>", handle_click)

    def _enter_search_mode():
        if search_state["mode"]:
            search_entry.focus_set()
            search_entry.selection_range(0, tk.END)
            return
        search_state["mode"] = True
        search_state["query"] = ""
        list_header.place_forget()
        search_entry.delete(0, tk.END)
        search_entry.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.52)
        search_entry.focus_set()

    def _exit_search_mode():
        if not search_state["mode"]:
            return
        search_state["mode"] = False
        search_state["query"] = ""
        search_entry.delete(0, tk.END)
        search_entry.place_forget()
        list_header.place(relx=0.5, rely=0.5, anchor="center")
        populate_tiles()
        root.focus_set()

    def _on_search_key_release(event=None):
        if not search_state["mode"]:
            return
        if event and event.keysym == "Escape":
            return
        query = search_entry.get()
        if query == search_state["query"]:
            return
        search_state["query"] = query
        populate_tiles()

    def _on_enter(event=None):
        if not matching_profiles:
            return "break"
        ctrl_pressed = bool(event.state & 0x4) if event else False
        alt_pressed = bool(event.state & 0x20000) if event else False
        shift_pressed = bool(event.state & 0x1) if event else False
        target_profile = matching_profiles[0]
        logger.info(f"Enter pressed: profile='{target_profile.get('name')}', ctrl={ctrl_pressed}, alt={alt_pressed}, shift={shift_pressed}")
        select_profile(target_profile, ctrl_pressed=ctrl_pressed, alt_pressed=alt_pressed, shift_pressed=shift_pressed)
        return "break"

    def _on_escape(event=None):
        if search_state["mode"]:
            _exit_search_mode()
            return "break"
        logger.info("Escape key pressed, closing Dashboard...")
        root.destroy()
        return "break"

    def _on_key_press(event):
        if event.keysym == "Escape":
            return _on_escape(event)

        # Return / KP_Enter (handles Enter, Ctrl+Enter, Shift+Enter, Alt+Enter)
        if event.keysym in ("Return", "KP_Enter"):
            return _on_enter(event)

        # Ctrl+F: enter search mode
        if (event.state & 0x4) and event.keysym.lower() == "f":
            _enter_search_mode()
            return "break"

        # If already typing inside search_entry, let Entry widget handle character insertion
        if event.widget == search_entry:
            return

        # BackSpace when focus is outside search_entry
        if search_state["mode"] and event.keysym == "BackSpace":
            search_entry.focus_set()
            cur = search_entry.get()
            if cur:
                search_entry.delete(len(cur) - 1, tk.END)
            _on_search_key_release()
            return "break"

        # Ignore modifier keys or navigation keys
        if event.keysym in (
            "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
            "Super_L", "Super_R", "Caps_Lock", "Num_Lock", "Scroll_Lock",
            "Tab", "Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next"
        ):
            return

        char_to_insert = utils.char_from_key_event(event)
        if char_to_insert:
            if not search_state["mode"]:
                _enter_search_mode()
            search_entry.focus_set()
            search_entry.insert(tk.END, char_to_insert)
            _on_search_key_release()
            return "break"

    list_header.bind("<Button-1>", lambda e: _enter_search_mode())
    search_entry.bind("<KeyRelease>", _on_search_key_release)
    search_entry.bind("<Escape>", _on_escape)
    search_entry.bind("<Control-f>", lambda e: "break")
    search_entry.bind("<Control-F>", lambda e: "break")

    for ret_key in (
        "<Return>", "<KP_Enter>",
        "<Control-Return>", "<Control-KP_Enter>",
        "<Shift-Return>", "<Shift-KP_Enter>",
        "<Alt-Return>", "<Alt-KP_Enter>",
    ):
        search_entry.bind(ret_key, _on_enter)
        root.bind_all(ret_key, _on_enter)

    root.bind_all("<KeyPress>", _on_key_press)
    root.bind_all("<Escape>", _on_escape)

    # Populate initial tiles
    populate_tiles()

    # Calculate the window size based on the grid
    grid_frame.update_idletasks()

    # Get the number of rows based on the number of profiles and columns
    num_rows = (len(EDGE_PROFILES) + COLUMNS - 1) // COLUMNS

    # Calculate the window width and height based on the grid
    window_width = (TILE_WIDTH + 2 * PADDING_X) * COLUMNS + 40  # Add padding for the main frame
    window_height = (TILE_HEIGHT + 2 * PADDING_Y) * num_rows + 50 + 40  # Adjusted for top bar + increased bottom padding

    # Set the window size
    logger.info(f"Calculated window size: {window_width}x{window_height}")
    root.geometry(f"{window_width}x{window_height}")

    # Positioning also raises the window and keeps it topmost briefly so coordinates stay put.
    logger.info("Positioning window on second monitor...")
    utils.center_window_on_second_monitor(root)

    # Start the main loop
    logger.info("Starting Tkinter mainloop (window is now visible)...")
    root.mainloop()
    logger.info("Dashboard closed cleanly.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        import argparse
        cli_parser = argparse.ArgumentParser(description="Edge Profile Dashboard")
        cli_parser.add_argument("profile", nargs="?", default=None, help="Name of profile to launch directly")
        cli_parser.add_argument("--editor", "-e", action="store_true", help="Launch editor for profile instead of browser")
        cli_parser.add_argument("--sourcetree", "-s", action="store_true", help="Launch SourceTree for profile")
        cli_args = cli_parser.parse_args()
        if cli_args.profile:
            matched_profile = next((p for p in EDGE_PROFILES if p.get("name", "").lower() == cli_args.profile.lower()), None)
            if matched_profile:
                logger.info(f"Direct profile launch via CLI: '{matched_profile.get('name')}', editor={cli_args.editor}, sourcetree={cli_args.sourcetree}")
                if cli_args.sourcetree:
                    launch_sourcetree_for_profile(matched_profile["name"])
                elif cli_args.editor:
                    launch_editor(matched_profile["name"])
                else:
                    launch_browser(matched_profile[PROFILE_COMMAND_KEY])
                sys.exit(0)
            else:
                logger.warning(f"Profile '{cli_args.profile}' not found in profiles.json. Opening GUI.")
    create_dashboard()
