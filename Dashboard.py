#!/usr/bin/env python
# Dashboard.py - Select Google Chrome profile using a grid of tiles

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

def launch_browser(command, open_chrome1=True, chrome1_urls=None, open_chrome2=True, chrome2_urls=None):
    """Launch the browser in settings.json with the selected profile and enforce window geometry."""
    try:
        logger.info(f"launch_browser called with command: {command}")
        utils.launch_browser_with_geometry(
            command,
            geom=WINDOW_OPEN_GEOMETRY,
            browser_to_use=browser_to_use,
            open_chrome1=open_chrome1,
            chrome1_urls=chrome1_urls or [],
            open_chrome2=open_chrome2,
            chrome2_urls=chrome2_urls or [],
        )
    except Exception as e:
        logger.error(f"Error launching browser: {e}")
        print(f"Error launching browser: {e}")

def launch_editor(name):
    """Launch JC_TheGoodWorkStation with the workspace file or folder if it exists"""
    try:
        logger.info(f"launch_editor called for profile: '{name}'")

        # Use common util to resolve the target
        repo_path = "C:\\repo"
        target = utils.resolve_project_target(repo_path, name)
        
        # If target exists (either workspace file or project folder), launch it
        if target:
            utils.launch_jc_thegoodworkstation(target)
        else:
            logger.warn(f"No specific target found for profile: '{name}', launching default JC_TheGoodWorkStation")
            utils.launch_jc_thegoodworkstation()
    except Exception as e:
        logger.error(f"Error launching editor: {e}")
        print(f"Error launching editor: {e}")

def select_profile(profile):
    """Handle profile selection when a tile is clicked or Enter is pressed.
    Respects profile preferences for Chrome 1, Chrome 2, and JC_TheGoodWorkStation."""
    logger.info(f"select_profile called: name='{profile.get('name')}'")

    open_chrome1 = profile.get("openChrome1", True)
    chrome1_urls = profile.get("chrome1Urls", [])
    open_chrome2 = profile.get("openChrome2", True)
    chrome2_urls = profile.get("chrome2Urls", [])
    open_workspace = profile.get("openJCTheGoodWorkspace", profile.get("openWorkspace", True))

    if open_chrome1 or open_chrome2:
        logger.info(
            f"Launching browser command for '{profile.get('name')}': {profile[PROFILE_COMMAND_KEY]} "
            f"(open_chrome1={open_chrome1}, chrome1_urls={chrome1_urls}, "
            f"open_chrome2={open_chrome2}, chrome2_urls={chrome2_urls})"
        )
        launch_thread = threading.Thread(
            target=launch_browser,
            args=(profile[PROFILE_COMMAND_KEY],),
            kwargs={
                "open_chrome1": open_chrome1,
                "chrome1_urls": chrome1_urls,
                "open_chrome2": open_chrome2,
                "chrome2_urls": chrome2_urls,
            }
        )
        launch_thread.daemon = False
        launch_thread.start()
    else:
        logger.info(f"Skipping browser launch for '{profile.get('name')}' (both Chrome 1 and 2 disabled)")

    if open_workspace:
        logger.info(f"Launching editor for '{profile.get('name')}'")
        editor_thread = threading.Thread(target=launch_editor, args=(profile["name"],))
        editor_thread.daemon = False
        editor_thread.start()
    else:
        logger.info(f"Skipping editor launch for '{profile.get('name')}' (openJCTheGoodWorkspace=False)")

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
WINDOW_OPEN_GEOMETRY = app_settings["window_open_geometry"]
logger.info(
    f"Using browserToUser='{browser_to_use}', PROFILE_COMMAND_KEY='{PROFILE_COMMAND_KEY}', "
    f"WINDOW_OPEN_GEOMETRY={WINDOW_OPEN_GEOMETRY}"
)

SCROLLBAR_BG = "#404040"
SCROLLBAR_ACTIVE = "#555555"
SCROLLBAR_TROUGH = "#1A1A1A"
SCROLLBAR_ARROW = "#FFFFFF"

def configure_custom_scrollbar(widget):
    """Style scrollbar to match the custom dark theme style in other JC GUIs."""
    style = ttk.Style(widget)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Preview.Vertical.TScrollbar",
        background=SCROLLBAR_BG,
        troughcolor=SCROLLBAR_TROUGH,
        bordercolor=SCROLLBAR_TROUGH,
        arrowcolor=SCROLLBAR_ARROW,
        darkcolor=SCROLLBAR_BG,
        lightcolor=SCROLLBAR_BG,
        width=10,
        arrowsize=10,
    )
    style.map(
        "Preview.Vertical.TScrollbar",
        background=[
            ("active", SCROLLBAR_ACTIVE),
            ("pressed", SCROLLBAR_ACTIVE),
        ],
    )

root = None
active_modal = None

def open_edit_modal(profile):
    """Open a modal dialog to edit profile settings:
    - Open Chrome 1 (Small) + URL tiles list with '+' button to add new
    - Open Chrome 2 (Large) + URL tiles list with '+' button to add new
    - Open JC_TheGoodWorkspace
    """
    global active_modal
    if active_modal and active_modal.winfo_exists():
        try:
            active_modal.lift()
            active_modal.focus_set()
        except Exception:
            pass
        return

    profile_name = profile.get("name", "Unknown")
    logger.info(f"Opening edit modal for profile '{profile_name}'")

    modal = tk.Toplevel(root)
    active_modal = modal
    modal.title(f"Edit Profile - {profile_name}")
    modal.configure(bg="#262626")
    modal.transient(root)
    modal.resizable(True, True)

    # Set icon
    icon_path = os.path.join(base_path, "images", f"{profile_name}.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_path, "images", "Edge.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_path, "images", "CK.png")
    if os.path.exists(icon_path):
        try:
            modal_icon = tk.PhotoImage(file=icon_path)
            modal.iconphoto(False, modal_icon)
        except Exception:
            pass

    # Values from profile with defaults
    open_chrome1_var = tk.BooleanVar(value=bool(profile.get("openChrome1", True)))
    chrome1_urls = list(profile.get("chrome1Urls") or [])
    open_chrome2_var = tk.BooleanVar(value=bool(profile.get("openChrome2", True)))
    chrome2_urls = list(profile.get("chrome2Urls") or [])
    open_workspace_var = tk.BooleanVar(
        value=bool(profile.get("openJCTheGoodWorkspace", profile.get("openWorkspace", True)))
    )

    # Position modal centered over root
    modal_w = 520
    modal_h = 600
    root.update_idletasks()
    rx = root.winfo_x()
    ry = root.winfo_y()
    rw = root.winfo_width()
    rh = root.winfo_height()
    mx = max(0, rx + (rw - modal_w) // 2)
    my = max(0, ry + (rh - modal_h) // 2)
    modal.geometry(f"{modal_w}x{modal_h}+{mx}+{my}")
    modal.minsize(440, 460)

    # Modal header
    header_frame = tk.Frame(modal, bg="#262626", padx=36, pady=14)
    header_frame.pack(side=tk.TOP, fill=tk.X)
    title_label = tk.Label(
        header_frame,
        text=f"Edit Profile: {profile_name}",
        font=("Segoe UI", 13, "bold"),
        fg="white",
        bg="#262626",
    )
    title_label.pack(side=tk.LEFT)

    sep_top = tk.Frame(modal, bg="#333333", height=1)
    sep_top.pack(side=tk.TOP, fill=tk.X)

    # Modal footer (fixed at bottom)
    footer_frame = tk.Frame(modal, bg="#1f1f1f", padx=36, pady=12)
    footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

    def close_modal():
        global active_modal
        active_modal = None
        try:
            modal.grab_release()
        except Exception:
            pass
        modal.destroy()
        root.focus_set()

    def save_and_close():
        profile["openChrome1"] = bool(open_chrome1_var.get())
        profile["chrome1Urls"] = [u.strip() for u in chrome1_urls if u.strip()]
        profile["openChrome2"] = bool(open_chrome2_var.get())
        profile["chrome2Urls"] = [u.strip() for u in chrome2_urls if u.strip()]
        profile["openJCTheGoodWorkspace"] = bool(open_workspace_var.get())
        profile["openWorkspace"] = bool(open_workspace_var.get())

        try:
            with open(profiles_file_path, "w", encoding="utf-8") as f:
                json.dump(EDGE_PROFILES, f, indent=4)
                f.write("\n")
            logger.info(
                f"Saved profile '{profile_name}': "
                f"openChrome1={profile['openChrome1']} ({len(profile['chrome1Urls'])} URLs), "
                f"openChrome2={profile['openChrome2']} ({len(profile['chrome2Urls'])} URLs), "
                f"openJCTheGoodWorkspace={profile['openJCTheGoodWorkspace']}"
            )
        except Exception as err:
            logger.error(f"Failed to write profiles.json: {err}")

        close_modal()

    save_btn = tk.Button(
        footer_frame,
        text="Save",
        font=("Segoe UI", 9, "bold"),
        fg="white",
        bg="#2e7d32",
        activebackground="#388e3c",
        activeforeground="white",
        relief=tk.FLAT,
        cursor="hand2",
        padx=18,
        pady=4,
        command=save_and_close,
    )
    save_btn.pack(side=tk.RIGHT)

    cancel_btn = tk.Button(
        footer_frame,
        text="Cancel",
        font=("Segoe UI", 9),
        fg="#cccccc",
        bg="#333333",
        activebackground="#444444",
        activeforeground="white",
        relief=tk.FLAT,
        cursor="hand2",
        padx=14,
        pady=4,
        command=close_modal,
    )
    cancel_btn.pack(side=tk.RIGHT, padx=(0, 8))

    sep_bottom = tk.Frame(modal, bg="#333333", height=1)
    sep_bottom.pack(side=tk.BOTTOM, fill=tk.X)

    configure_custom_scrollbar(modal)

    # Scrollable body area
    body_container = tk.Frame(modal, bg="#262626")
    body_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    body_canvas = tk.Canvas(body_container, bg="#262626", highlightthickness=0)
    body_scrollbar = ttk.Scrollbar(
        body_container,
        orient="vertical",
        command=body_canvas.yview,
        style="Preview.Vertical.TScrollbar",
    )

    def _autoscroll(first, last):
        first_val = float(first)
        last_val = float(last)
        if first_val <= 0.0 and last_val >= 1.0:
            if body_scrollbar.winfo_ismapped():
                body_scrollbar.pack_forget()
        else:
            if not body_scrollbar.winfo_ismapped():
                body_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=body_canvas)
        body_scrollbar.set(first, last)

    body_canvas.configure(yscrollcommand=_autoscroll)
    body_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    form_frame = tk.Frame(body_canvas, bg="#262626")
    canvas_window = body_canvas.create_window((0, 0), window=form_frame, anchor="nw")

    def _on_canvas_configure(event):
        body_canvas.itemconfig(canvas_window, width=event.width)

    body_canvas.bind("<Configure>", _on_canvas_configure)

    # Centered unit frame: all fields live in this single unit, centered in the main container
    unit_frame = tk.Frame(form_frame, bg="#262626")
    unit_frame.pack(anchor="center", padx=36, pady=(12, 16))

    unit_spacer = tk.Frame(unit_frame, width=380, height=0, bg="#262626")
    unit_spacer.pack()

    def _update_scroll():
        modal.update_idletasks()
        body_canvas.configure(scrollregion=body_canvas.bbox("all"))

    form_frame.bind("<Configure>", lambda e: _update_scroll())
    unit_frame.bind("<Configure>", lambda e: _update_scroll())

    def _on_mousewheel(event):
        if body_canvas.winfo_exists():
            body_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    body_canvas.bind("<MouseWheel>", _on_mousewheel)
    form_frame.bind("<MouseWheel>", _on_mousewheel)
    unit_frame.bind("<MouseWheel>", _on_mousewheel)

    # URL Section Builder with drag up/down reordering
    def create_url_section(parent_container, urls_list):
        tiles_frame = tk.Frame(parent_container, bg="#262626")
        tiles_frame.pack(fill=tk.X, expand=True)

        action_frame = tk.Frame(parent_container, bg="#262626")
        action_frame.pack(fill=tk.X, expand=True, pady=(4, 0))

        add_input_frame = tk.Frame(action_frame, bg="#262626")
        tile_records = []
        drag_state = {"src_idx": None}

        def delete_url_at(idx):
            if 0 <= idx < len(urls_list):
                urls_list.pop(idx)
                render_tiles()

        def render_tiles():
            for child in tiles_frame.winfo_children():
                child.destroy()
            tile_records.clear()
            drag_state["src_idx"] = None

            if not urls_list:
                empty_lbl = tk.Label(
                    tiles_frame,
                    text="(No URLs configured)",
                    font=("Segoe UI", 9, "italic"),
                    fg="#777777",
                    bg="#262626",
                    anchor="w",
                )
                empty_lbl.pack(fill=tk.X, pady=(1, 3))
            else:
                for idx, url in enumerate(urls_list):
                    tile = tk.Frame(tiles_frame, bg="#333333", padx=8, pady=5)
                    tile.pack(fill=tk.X, expand=True, pady=2)

                    handle = tk.Label(
                        tile,
                        text="::",
                        font=("Segoe UI", 9, "bold"),
                        fg="#777777",
                        bg="#333333",
                        cursor="sb_v_double_arrow",
                        padx=3,
                    )
                    handle.pack(side=tk.LEFT)

                    disp_url = url if len(url) <= 45 else url[:42] + "..."
                    lbl = tk.Label(
                        tile,
                        text=disp_url,
                        font=("Segoe UI", 9),
                        fg="#e0e0e0",
                        bg="#333333",
                        anchor="w",
                        cursor="sb_v_double_arrow",
                        padx=4,
                    )
                    lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

                    del_btn = tk.Label(
                        tile,
                        text="✕",
                        font=("Segoe UI", 9, "bold"),
                        fg="#ff6b6b",
                        bg="#333333",
                        cursor="hand2",
                        padx=6,
                    )
                    del_btn.pack(side=tk.RIGHT)

                    rec = {"frame": tile, "handle": handle, "lbl": lbl, "del_btn": del_btn}
                    tile_records.append(rec)

                    def _del_enter(e, b=del_btn):
                        b.config(fg="#ff3b3b")
                    def _del_leave(e, b=del_btn):
                        b.config(fg="#ff6b6b")
                    del_btn.bind("<Enter>", _del_enter)
                    del_btn.bind("<Leave>", _del_leave)

                    def make_del(e):
                        target_del = e.widget
                        for cur_i, r in enumerate(tile_records):
                            if r["del_btn"] == target_del:
                                delete_url_at(cur_i)
                                break
                    del_btn.bind("<Button-1>", make_del)

                    def _tile_enter(e, r=rec):
                        if drag_state["src_idx"] is None:
                            r["frame"].config(bg="#3a3a3a")
                            r["handle"].config(bg="#3a3a3a")
                            r["lbl"].config(bg="#3a3a3a")
                            r["del_btn"].config(bg="#3a3a3a")

                    def _tile_leave(e, r=rec):
                        if drag_state["src_idx"] is None:
                            r["frame"].config(bg="#333333")
                            r["handle"].config(bg="#333333")
                            r["lbl"].config(bg="#333333")
                            r["del_btn"].config(bg="#333333")

                    def _on_drag_press(e, r=rec):
                        try:
                            cur_idx = tile_records.index(r)
                            drag_state["src_idx"] = cur_idx
                            for w_elem in (r["frame"], r["handle"], r["lbl"], r["del_btn"]):
                                w_elem.config(bg="#1a4d6e")
                        except ValueError:
                            pass

                    def _on_drag_motion(e):
                        if drag_state["src_idx"] is None:
                            return
                        y_root = e.y_root
                        for j, other_rec in enumerate(tile_records):
                            ry = other_rec["frame"].winfo_rooty()
                            rh = other_rec["frame"].winfo_height()
                            if ry <= y_root <= ry + rh:
                                if j != drag_state["src_idx"]:
                                    src_i = drag_state["src_idx"]
                                    moving_rec = tile_records[src_i]
                                    if j < src_i:
                                        moving_rec["frame"].pack(before=other_rec["frame"], fill=tk.X, expand=True, pady=2)
                                    else:
                                        moving_rec["frame"].pack(after=other_rec["frame"], fill=tk.X, expand=True, pady=2)
                                    val = urls_list.pop(src_i)
                                    urls_list.insert(j, val)
                                    rec_popped = tile_records.pop(src_i)
                                    tile_records.insert(j, rec_popped)
                                    drag_state["src_idx"] = j
                                    _update_scroll()
                                    break

                    def _on_drag_release(e):
                        if drag_state["src_idx"] is not None:
                            src_i = drag_state["src_idx"]
                            if 0 <= src_i < len(tile_records):
                                r_active = tile_records[src_i]
                                for w_elem in (r_active["frame"], r_active["handle"], r_active["lbl"], r_active["del_btn"]):
                                    w_elem.config(bg="#333333")
                            drag_state["src_idx"] = None
                            _update_scroll()

                    for drag_target in (tile, handle, lbl):
                        drag_target.bind("<Enter>", _tile_enter)
                        drag_target.bind("<Leave>", _tile_leave)
                        drag_target.bind("<Button-1>", _on_drag_press)
                        drag_target.bind("<B1-Motion>", _on_drag_motion)
                        drag_target.bind("<ButtonRelease-1>", _on_drag_release)

            _update_scroll()

        def show_add_input():
            add_btn.pack_forget()
            add_input_frame.pack(fill=tk.X, expand=True, pady=(2, 4))
            url_entry.delete(0, tk.END)
            url_entry.focus_set()
            _update_scroll()

        def hide_add_input():
            add_input_frame.pack_forget()
            add_btn.pack(anchor="w", pady=(2, 4))
            _update_scroll()

        def commit_new_url(event=None):
            val = url_entry.get().strip()
            if val:
                urls_list.append(val)
                render_tiles()
            hide_add_input()

        add_btn = tk.Button(
            action_frame,
            text="+ Add URL",
            font=("Segoe UI", 9, "bold"),
            fg="#7ec7d2",
            bg="#333333",
            activebackground="#444444",
            activeforeground="#9fe8f4",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=3,
            command=show_add_input,
        )
        add_btn.pack(anchor="w", pady=(2, 4))

        # Input row
        url_entry = tk.Entry(
            add_input_frame,
            font=("Segoe UI", 9),
            fg="white",
            bg="#1c1c1c",
            insertbackground="white",
            relief=tk.SOLID,
            bd=1,
            highlightthickness=0,
        )
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=3)
        url_entry.bind("<Return>", commit_new_url)
        url_entry.bind("<Escape>", lambda e: hide_add_input())

        confirm_btn = tk.Button(
            add_input_frame,
            text="Add",
            font=("Segoe UI", 9, "bold"),
            fg="white",
            bg="#2e7d32",
            activebackground="#388e3c",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=2,
            command=commit_new_url,
        )
        confirm_btn.pack(side=tk.LEFT, padx=(0, 4))

        cancel_add_btn = tk.Button(
            add_input_frame,
            text="Cancel",
            font=("Segoe UI", 9),
            fg="#cccccc",
            bg="#333333",
            activebackground="#444444",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=2,
            command=hide_add_input,
        )
        cancel_add_btn.pack(side=tk.LEFT)

        render_tiles()
        return tiles_frame

    # --- Field 1: Open Chrome 1 (Small) ---
    cb_frame1 = tk.Frame(unit_frame, bg="#262626")
    cb_frame1.pack(fill=tk.X, pady=(4, 2))

    cb1 = tk.Checkbutton(
        cb_frame1,
        text="Open Chrome 1 (Small)",
        variable=open_chrome1_var,
        font=("Segoe UI", 10, "bold"),
        fg="white",
        bg="#262626",
        selectcolor="#1a1a1a",
        activebackground="#262626",
        activeforeground="white",
        cursor="hand2",
        padx=0,
        bd=0,
        highlightthickness=0,
    )
    cb1.pack(anchor="w")

    c1_urls_wrapper = tk.Frame(unit_frame, bg="#262626")
    create_url_section(c1_urls_wrapper, chrome1_urls)

    def on_toggle_c1():
        if open_chrome1_var.get():
            c1_urls_wrapper.pack(fill=tk.X, pady=(2, 8), after=cb_frame1)
        else:
            c1_urls_wrapper.pack_forget()
        _update_scroll()

    cb1.config(command=on_toggle_c1)
    if open_chrome1_var.get():
        c1_urls_wrapper.pack(fill=tk.X, pady=(2, 8), after=cb_frame1)

    # --- Field 2: Open Chrome 2 (Large) ---
    cb_frame2 = tk.Frame(unit_frame, bg="#262626")
    cb_frame2.pack(fill=tk.X, pady=(8, 2))

    cb2 = tk.Checkbutton(
        cb_frame2,
        text="Open Chrome 2 (Large)",
        variable=open_chrome2_var,
        font=("Segoe UI", 10, "bold"),
        fg="white",
        bg="#262626",
        selectcolor="#1a1a1a",
        activebackground="#262626",
        activeforeground="white",
        cursor="hand2",
        padx=0,
        bd=0,
        highlightthickness=0,
    )
    cb2.pack(anchor="w")

    c2_urls_wrapper = tk.Frame(unit_frame, bg="#262626")
    create_url_section(c2_urls_wrapper, chrome2_urls)

    def on_toggle_c2():
        if open_chrome2_var.get():
            c2_urls_wrapper.pack(fill=tk.X, pady=(2, 8), after=cb_frame2)
        else:
            c2_urls_wrapper.pack_forget()
        _update_scroll()

    cb2.config(command=on_toggle_c2)
    if open_chrome2_var.get():
        c2_urls_wrapper.pack(fill=tk.X, pady=(2, 8), after=cb_frame2)

    # --- Field 3: Open JC_TheGoodWorkspace ---
    cb_frame3 = tk.Frame(unit_frame, bg="#262626")
    cb_frame3.pack(fill=tk.X, pady=(10, 8))

    cb3 = tk.Checkbutton(
        cb_frame3,
        text="Open JC_TheGoodWorkspace",
        variable=open_workspace_var,
        font=("Segoe UI", 10, "bold"),
        fg="white",
        bg="#262626",
        selectcolor="#1a1a1a",
        activebackground="#262626",
        activeforeground="white",
        cursor="hand2",
        padx=0,
        bd=0,
        highlightthickness=0,
    )
    cb3.pack(anchor="w")

    modal.protocol("WM_DELETE_WINDOW", close_modal)
    modal.bind("<Escape>", lambda e: close_modal())

    modal.grab_set()
    modal.focus_set()
    _update_scroll()

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
                is_shift = bool(event and (event.state & 0x1))
                if is_shift:
                    logger.info(f"Shift+Click on tile: '{prof.get('name')}'")
                    open_edit_modal(prof)
                else:
                    select_profile(prof)

            def handle_shift_click(event, prof=profile):
                logger.info(f"<Shift-Button-1> on tile: '{prof.get('name')}'")
                open_edit_modal(prof)

            img = get_profile_photo_image(profile["name"])
            if img:
                image_label = tk.Label(tile_frame, image=img, bg=tile_frame.cget("bg"))
                image_label.image = img
                image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
                image_label.bind("<Button-1>", handle_click)
                image_label.bind("<Shift-Button-1>", handle_shift_click)
            else:
                canvas = tk.Canvas(tile_frame, width=TILE_WIDTH - 20, height=TILE_HEIGHT - 20, bg="#7ec7d2")
                canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
                canvas.bind("<Button-1>", handle_click)
                canvas.bind("<Shift-Button-1>", handle_shift_click)

            tile_frame.bind("<Button-1>", handle_click)
            tile_frame.bind("<Shift-Button-1>", handle_shift_click)

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
        if active_modal and active_modal.winfo_exists():
            return
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
        if active_modal and active_modal.winfo_exists():
            return "break"
        if not matching_profiles:
            return "break"
        target_profile = matching_profiles[0]
        is_shift = bool(event and (event.state & 0x1))
        if is_shift:
            logger.info(f"Shift+Enter pressed: opening modal for profile='{target_profile.get('name')}'")
            open_edit_modal(target_profile)
        else:
            logger.info(f"Enter pressed: profile='{target_profile.get('name')}'")
            select_profile(target_profile)
        return "break"

    def _on_escape(event=None):
        if active_modal and active_modal.winfo_exists():
            return "break"
        if search_state["mode"]:
            _exit_search_mode()
            return "break"
        logger.info("Escape key pressed, closing Dashboard...")
        root.destroy()
        return "break"

    def _on_key_press(event):
        if active_modal and active_modal.winfo_exists():
            return

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
        cli_parser = argparse.ArgumentParser(description="Chrome Profile Dashboard")
        cli_parser.add_argument("profile", nargs="?", default=None, help="Name of profile to launch directly")
        cli_parser.add_argument("--editor", "-e", action="store_true", help="Launch editor for profile instead of browser")
        cli_args = cli_parser.parse_args()
        if cli_args.profile:
            matched_profile = next((p for p in EDGE_PROFILES if p.get("name", "").lower() == cli_args.profile.lower()), None)
            if matched_profile:
                logger.info(f"Direct profile launch via CLI: '{matched_profile.get('name')}', editor={cli_args.editor}")
                if cli_args.editor:
                    launch_editor(matched_profile["name"])
                else:
                    launch_browser(
                        matched_profile[PROFILE_COMMAND_KEY],
                        open_chrome1=matched_profile.get("openChrome1", True),
                        chrome1_urls=matched_profile.get("chrome1Urls", []),
                        open_chrome2=matched_profile.get("openChrome2", True),
                        chrome2_urls=matched_profile.get("chrome2Urls", []),
                    )
                sys.exit(0)
            else:
                logger.warning(f"Profile '{cli_args.profile}' not found in profiles.json. Opening GUI.")
    create_dashboard()
