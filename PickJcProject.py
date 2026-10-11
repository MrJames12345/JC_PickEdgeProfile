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
root = None

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

def open_project(name, open_in_sourcetree=False, open_both=False):
    """Open the project in SourceTree or the selected editor (or both)"""
    try:
        logger.info(f"open_project called: name='{name}', open_in_sourcetree={open_in_sourcetree}, open_both={open_both}")

        if name == ALL_OPTION:
            # The All option opens in the configured editor only.
            target = ALL_OPTION_WORKSPACE if os.path.exists(ALL_OPTION_WORKSPACE) else REPO_DIR
            logger.info(f"Opening All option with target: {target}")
            if launch_code_editor(target):
                logger.info("Editor launched for All option, destroying window")
                if root:
                    root.destroy()
            return

        # Use common util to resolve the target (workspace or folder)
        target = utils.resolve_project_target(REPO_DIR, name)
        logger.info(f"Resolved target for '{name}': {target}")
        
        if target:
            success = False
            if open_both:
                logger.info(f"Launching Editor and SourceTree for: {target}")
                ed_success = launch_code_editor(target)
                st_success = utils.launch_sourcetree(target)
                success = ed_success or st_success
            elif open_in_sourcetree:
                logger.info(f"Launching SourceTree for: {target}")
                success = utils.launch_sourcetree(target)
            else:
                success = launch_code_editor(target)
                
            if success:
                # Close the dashboard after launching
                logger.info(f"Launch succeeded, closing window")
                if root:
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

    # Header bar with title centered and editor toggle at top right (fixed height so title/search swap does not shift grid)
    HEADER_HEIGHT = 48
    header_frame = tk.Frame(main_frame, bg="#262626", height=HEADER_HEIGHT)
    header_frame.pack(fill=tk.X, pady=(0, 10))
    header_frame.pack_propagate(False)

    list_header = tk.Label(
        header_frame,
        text="Select JC Project",
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
        logger.info(f"Pick JC Project code_editor updated to: '{code_editor}'")

    editor_toggle = utils.create_editor_toggle(header_frame, base_path, code_editor, on_change=on_editor_changed)
    editor_toggle.place(relx=1.0, rely=0.5, anchor=tk.E)

    # Grid frame
    grid_frame = tk.Frame(main_frame, bg="#262626")
    grid_frame.pack(fill=tk.BOTH, expand=True)

    all_projects = get_jc_projects()
    matching_projects = []
    search_state = {"mode": False, "query": ""}

    def populate_grid():
        nonlocal matching_projects
        for child in grid_frame.winfo_children():
            child.destroy()

        query = (search_state["query"] or "").strip().lower()
        matching = []
        for project in all_projects:
            if query:
                raw_name = project.lower()
                display_name = ("All" if project == ALL_OPTION else utils.split_camel_case(project.replace("JC_", "").replace("_", " "))).lower()
                clean_name = project.replace("JC_", "").replace("_", "").lower()
                if query not in raw_name and query not in display_name and query not in clean_name:
                    continue
            matching.append(project)

        matching_projects = matching
        if not matching:
            no_matches = tk.Label(
                grid_frame,
                text="No matching projects",
                font=("Segoe UI", 11),
                fg="#888888",
                bg="#262626",
            )
            no_matches.grid(row=0, column=0, columnspan=COLUMNS, pady=40)
            return

        for i, project in enumerate(matching):
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
                font=("Segoe UI", 10, "bold"),
            )
            btn.grid(row=row, column=col, padx=PADDING_X, pady=PADDING_Y)

            def on_click(e, p=project):
                shift_pressed = bool(e.state & 0x1)
                ctrl_pressed = bool(e.state & 0x4)
                alt_pressed = bool(e.state & 0x20000)
                logger.info(f"Tile click: project='{p}', shift={shift_pressed}, ctrl={ctrl_pressed}, alt={alt_pressed}")
                open_project(
                    p,
                    open_in_sourcetree=(shift_pressed and p != ALL_OPTION),
                    open_both=(ctrl_pressed and p != ALL_OPTION),
                )
                return "break"

            btn.bind("<Button-1>", on_click)

            # Add hover effect
            def on_enter(e, b=btn, bg=hover_bg):
                b.config(bg=bg)

            def on_leave(e, b=btn, bg=default_bg):
                b.config(bg=bg)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

    def _enter_search_mode():
        if search_state["mode"]:
            search_entry.focus_set()
            search_entry.selection_range(0, tk.END)
            return
        search_state["mode"] = True
        search_state["query"] = ""
        list_header.place_forget()
        search_entry.delete(0, tk.END)
        search_entry.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.55)
        search_entry.focus_set()

    def _exit_search_mode():
        if not search_state["mode"]:
            return
        search_state["mode"] = False
        search_state["query"] = ""
        search_entry.delete(0, tk.END)
        search_entry.place_forget()
        list_header.place(relx=0.5, rely=0.5, anchor="center")
        populate_grid()
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
        populate_grid()

    def _on_enter(event=None):
        if not matching_projects:
            return "break"
        project_name = matching_projects[0]
        shift_pressed = bool(event.state & 0x1) if event else False
        ctrl_pressed = bool(event.state & 0x4) if event else False
        alt_pressed = bool(event.state & 0x20000) if event else False
        logger.info(f"Enter pressed: project='{project_name}', shift={shift_pressed}, ctrl={ctrl_pressed}, alt={alt_pressed}")
        open_project(
            project_name,
            open_in_sourcetree=(shift_pressed and project_name != ALL_OPTION),
            open_both=(ctrl_pressed and project_name != ALL_OPTION),
        )
        return "break"

    def _on_escape(event=None):
        if search_state["mode"]:
            _exit_search_mode()
            return "break"
        logger.info("Escape pressed, closing Pick JC Project...")
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

    # Populate initial grid
    populate_grid()

    logger.info("Positioning window on second monitor...")
    utils.center_window_on_second_monitor(root)

    logger.info("Starting Tkinter mainloop (Pick JC Project window is now visible)...")
    root.mainloop()
    logger.info("Pick JC Project closed cleanly.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser(description="Pick JC Project Launcher")
        parser.add_argument("project", nargs="?", default=None, help="Project name or target to launch directly")
        parser.add_argument("--sourcetree", "-s", action="store_true", help="Launch in SourceTree instead of editor")
        args = parser.parse_args()
        if args.project:
            logger.info(f"Direct launch requested via CLI: project='{args.project}', sourcetree={args.sourcetree}")
            open_project(args.project, open_in_sourcetree=args.sourcetree)
            sys.exit(0)
    create_dashboard()
