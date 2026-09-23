#!/usr/bin/env python
# PickJcProject.py - Dashboard to select and open JC projects

import os
import sys
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import utils

logger = utils.setup_logger(__file__)
logger.info("Starting Pick JC Project...")

# Constants
TITLE = "Pick JC Project"
REPO_DIR = "C:\\repo"
ALL_OPTION = "All"
ALL_OPTION_WORKSPACE = os.path.join(REPO_DIR, "#AllApps.code-workspace")
COLUMNS = 4
PADDING_X = 10
PADDING_Y = 10
BTN_WIDTH = 25
BTN_HEIGHT = 2

# Get the script directory
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(base_path)
logger.info(f"Base path and CWD: {base_path}")

app_settings = utils.load_settings(base_path)
code_editor = app_settings["code_editor"]
logger.info(f"Using codeEditor='{code_editor}'")

def get_jc_projects():
    """Get list of folders in C:\\repo starting with JC_"""
    projects = []
    try:
        logger.info(f"Scanning '{REPO_DIR}' for JC_ projects...")
        if os.path.exists(REPO_DIR):
            for d in os.listdir(REPO_DIR):
                if d.startswith("JC_") and os.path.isdir(os.path.join(REPO_DIR, d)):
                    projects.append(d)
        logger.info(f"Discovered {len(projects)} JC_ project folders in '{REPO_DIR}'")
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        print(f"Error listing projects: {e}")
    return [ALL_OPTION] + sorted(projects)

def open_project(name, open_in_sourcetree=False):
    """Open the project in SourceTree or the selected editor"""
    try:
        logger.info(f"open_project called: name='{name}', open_in_sourcetree={open_in_sourcetree}")
        if name == ALL_OPTION:
            # The All option opens in the configured editor only.
            target = ALL_OPTION_WORKSPACE if os.path.exists(ALL_OPTION_WORKSPACE) else REPO_DIR
            logger.info(f"Opening All option with target: {target}")
            if launch_code_editor(target):
                logger.info("Editor launched for All option, destroying window")
                root.destroy()
            return

        # Use common util to resolve the target (workspace or folder)
        target = utils.resolve_project_target(REPO_DIR, name)
        logger.info(f"Resolved target for '{name}': {target}")
        
        if target:
            success = False
            if open_in_sourcetree:
                logger.info(f"Launching SourceTree for: {target}")
                success = utils.launch_sourcetree(target)
            else:
                success = launch_code_editor(target)
                
            if success:
                # Close the dashboard after launching
                logger.info(f"Launch succeeded, closing window")
                root.destroy()
        else:
            logger.warn(f"No target found for project: '{name}'")
    except Exception as e:
        logger.error(f"Error opening project: {e}")
        print(f"Error opening project: {e}")

def launch_code_editor(target):
    """Launch the editor selected by the codeEditor setting"""
    return utils.launch_code_editor(target, code_editor)

def create_dashboard():
    global root
    logger.info("Creating Pick JC Project Tkinter window...")
    root = tk.Tk()
    utils.install_tk_exception_handler(root, logger)
    utils.attach_event_logger(root, logger)
    root.title(TITLE)
    root.configure(bg="#262626")
    root.resizable(True, True)

    # Main frame
    main_frame = tk.Frame(root, padx=20, pady=20, bg="#262626")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Header bar with title centered and editor toggle at top right
    header_frame = tk.Frame(main_frame, bg="#262626")
    header_frame.pack(fill=tk.X, pady=(0, 10))

    header = tk.Label(header_frame, text="Select JC Project", font=("Segoe UI", 14, "bold"), fg="white", bg="#262626", pady=10)
    header.pack(expand=True)

    def on_editor_changed(new_editor):
        global code_editor
        code_editor = new_editor
        logger.info(f"Pick JC Project code_editor updated to: '{code_editor}'")

    editor_toggle = utils.create_editor_toggle(header_frame, base_path, code_editor, on_change=on_editor_changed)
    editor_toggle.place(relx=1.0, rely=0.5, anchor=tk.E)

    # Grid frame
    grid_frame = tk.Frame(main_frame, bg="#262626")
    grid_frame.pack(fill=tk.BOTH, expand=True)

    projects = get_jc_projects()
    
    for i, project in enumerate(projects):
        row = i // COLUMNS
        col = i % COLUMNS

        is_all = project == ALL_OPTION
        default_bg = "#2e7d32" if is_all else "#333333"
        hover_bg = "#388e3c" if is_all else "#444444"
        
        btn = tk.Button(
            grid_frame,
            text=project if project == ALL_OPTION else utils.split_camel_case(project.replace("JC_", "").replace("_", " ")),
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            bg=default_bg,
            fg="white",
            activebackground=hover_bg,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            font=("Segoe UI", 10, "bold")
        )
        btn.grid(row=row, column=col, padx=PADDING_X, pady=PADDING_Y)

        def on_click(e, p=project):
            shift_pressed = bool(e.state & 0x1)
            alt_pressed = bool(e.state & 0x20000)
            logger.info(f"Tile click: project='{p}', shift={shift_pressed}, alt={alt_pressed}")
            open_project(p, open_in_sourcetree=(shift_pressed and p != ALL_OPTION))
            return "break"

        btn.bind("<Button-1>", on_click)
        
        # Add hover effect
        def on_enter(e, b=btn, bg=hover_bg):
            b.config(bg=bg)
        def on_leave(e, b=btn, bg=default_bg):
            b.config(bg=bg)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    logger.info("Positioning window on second monitor...")
    utils.center_window_on_second_monitor(root)

    def on_escape(e):
        logger.info("Escape pressed, closing Pick JC Project...")
        root.destroy()

    root.bind_all("<Escape>", on_escape)

    # Build letter-to-project mapping: first project whose display name starts with each letter
    letter_map = {}
    for project in projects:
        display = "All" if project == ALL_OPTION else utils.split_camel_case(project.replace("JC_", "").replace("_", " "))
        first_letter = display[0].lower() if display else ""
        if first_letter and first_letter not in letter_map:
            letter_map[first_letter] = project

    def on_key_press(e):
        key = e.char.lower() if e.char else ""
        if key in letter_map:
            shift_pressed = bool(e.state & 0x1)
            project_name = letter_map[key]
            logger.info(f"Key pressed: '{key}' -> project '{project_name}', shift={shift_pressed}")
            open_project(project_name, open_in_sourcetree=(shift_pressed and project_name != ALL_OPTION))

    root.bind_all("<KeyPress>", on_key_press)

    logger.info("Starting Tkinter mainloop (Pick JC Project window is now visible)...")
    root.mainloop()
    logger.info("Pick JC Project closed cleanly.")

if __name__ == "__main__":
    create_dashboard()
