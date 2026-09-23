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
        root.destroy()
        return

    # If Alt is pressed, try to open the workspace and close app
    if alt_pressed:
        logger.info(f"Alt key active: Opening editor for '{profile.get('name')}' and closing Dashboard")
        launch_thread = threading.Thread(target=launch_editor, args=(profile["name"],))
        launch_thread.daemon = True
        launch_thread.start()
        # Close the window regardless of whether the editor was launched
        root.destroy()
        return

    # Launch the browser selected in settings.json
    logger.info(f"Launching browser command for '{profile.get('name')}': {profile[PROFILE_COMMAND_KEY]}")
    launch_thread = threading.Thread(target=launch_browser, args=(profile[PROFILE_COMMAND_KEY],))
    launch_thread.daemon = True
    launch_thread.start()

    # If Ctrl is pressed, also try to launch the editor
    if ctrl_pressed:
        logger.info(f"Ctrl key active: also launching editor for '{profile.get('name')}'")
        editor_thread = threading.Thread(target=launch_editor, args=(profile["name"],))
        editor_thread.daemon = True
        editor_thread.start()

    # Close the window
    logger.info("Closing Dashboard window after profile selection")
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

# Top bar containing editor toggle (Cursor on left, Antigravity on right)
top_bar = tk.Frame(main_frame, bg="#262626")
top_bar.pack(fill=tk.X, side=tk.TOP, pady=(0, 10))

def on_editor_changed(new_editor):
    global code_editor
    code_editor = new_editor
    logger.info(f"Dashboard code_editor updated to: '{code_editor}'")

editor_toggle = utils.create_editor_toggle(top_bar, base_path, code_editor, on_change=on_editor_changed)
editor_toggle.pack(side=tk.RIGHT)

# Create a frame for the grid of tiles
grid_frame = tk.Frame(main_frame, bg="#262626")
grid_frame.pack(fill=tk.BOTH, expand=True)

# Create tiles for each profile
row = 0
col = 0

# Calculate total number of profiles and items in the last row
total_profiles = len(EDGE_PROFILES)
last_row_items = total_profiles % COLUMNS
if last_row_items == 0:
    last_row_items = COLUMNS  # If last row is full

# Calculate the starting column for the last row to center it
last_row_start_col = (COLUMNS - last_row_items) // 2 if last_row_items < COLUMNS else 0

for i, profile in enumerate(EDGE_PROFILES):
    # Create a frame for each tile
    tile_frame = tk.Frame(
        grid_frame,
        width=TILE_WIDTH,
        height=TILE_HEIGHT,
        bd=0,  # No border
        relief=tk.FLAT,  # No relief
        cursor="hand2",
        bg="#262626"  # Match the main background color
    )

    # Check if this is the last row and adjust column for centering
    current_row = i // COLUMNS
    current_col = i % COLUMNS

    # If this is the last row and we need to center it
    if current_row == total_profiles // COLUMNS and last_row_items < COLUMNS:
        current_col = last_row_start_col + (i % COLUMNS)

    tile_frame.grid(row=current_row, column=current_col, padx=PADDING_X, pady=PADDING_Y)
    tile_frame.pack_propagate(False)  # Prevent the frame from shrinking

    # Try to load the image based on profile name
    try:
        # Get the profile name and use it to find the corresponding image
        profile_name = profile["name"]
        # Look for <name>.png in the images subdirectory
        image_path = os.path.join(base_path, "images", f"{profile_name}.png")

        # If the specific image doesn't exist, try AIMSInspection.png for AIMSProjectManagement
        if not os.path.exists(image_path):
            if profile_name == "AIMSProjectManagement":
                image_path = os.path.join(base_path, "images", "AIMSInspection.png")
            else:
                image_path = os.path.join(base_path, "images", "CK.png")

        # If the image still doesn't exist, fall back to CK.png
        if not os.path.exists(image_path):
            image_path = os.path.join(base_path, "images", "CK.png")

        if os.path.exists(image_path):
            # Load the image using PIL for high-quality resizing
            pil_image = Image.open(image_path)

            # Calculate the size to fit within the tile while maintaining aspect ratio
            # Use a slightly smaller size to ensure the image fits nicely within the tile
            max_width = TILE_WIDTH - 20  # Leave some padding
            max_height = TILE_HEIGHT - 20  # Leave some padding

            # Calculate the scaling factor to maintain aspect ratio
            width_ratio = max_width / pil_image.width
            height_ratio = max_height / pil_image.height
            scale_factor = min(width_ratio, height_ratio)

            # Only resize if the image is larger than the tile
            if scale_factor < 1:
                new_width = int(pil_image.width * scale_factor)
                new_height = int(pil_image.height * scale_factor)
                # Use LANCZOS for high-quality resizing
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert PIL image to tkinter PhotoImage
            img = ImageTk.PhotoImage(pil_image)
        else:
            # Create a placeholder if image doesn't exist
            img = None
    except Exception as e:
        print(f"Error loading image: {e}")
        img = None

    # Define click handler function that detects Ctrl, Alt, and Shift keys
    def handle_click(event, prof=profile):
        ctrl_pressed = bool(event.state & 0x4)  # Check if Ctrl key is pressed
        alt_pressed = bool(event.state & 0x20000)  # Check if Alt key is pressed (use only the reliable mask)
        shift_pressed = bool(event.state & 0x1)  # Check if Shift key is pressed
        select_profile(prof, ctrl_pressed, alt_pressed, shift_pressed)

    # Add image or placeholder
    if img:
        # Create a label with the image and center it in the tile
        # Use system background color to match the tile frame
        image_label = tk.Label(tile_frame, image=img, bg=tile_frame.cget('bg'))
        image_label.image = img  # Keep a reference to prevent garbage collection
        # Use place to center the image in the tile
        image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        # Bind click event to the image
        image_label.bind("<Button-1>", handle_click)
    else:
        # Create a colored rectangle as placeholder
        canvas = tk.Canvas(tile_frame, width=TILE_WIDTH-20, height=TILE_HEIGHT-20, bg="#7ec7d2")
        canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        # Bind click event to the canvas
        canvas.bind("<Button-1>", handle_click)

    # Bind click event to the entire tile
    tile_frame.bind("<Button-1>", handle_click)

# Calculate the window size based on the grid
# Update the grid layout to ensure all widgets are properly sized
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

def on_escape(event):
    logger.info("Escape key pressed, closing Dashboard...")
    root.destroy()

root.bind_all("<Escape>", on_escape)

# Start the main loop
logger.info("Starting Tkinter mainloop (window is now visible)...")
root.mainloop()
logger.info("Dashboard closed cleanly.")
