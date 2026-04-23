#!/usr/bin/env python
# PickJcProject.py - Dashboard to select and open JC projects

import os
import sys
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import utils

# Toggle for launching Antigravity vs VSCode
useAntigravity = False

# Constants
TITLE = "Pick JC Project"
REPO_DIR = "C:\\repo"
COLUMNS = 4
PADDING_X = 10
PADDING_Y = 10
BTN_WIDTH = 25
BTN_HEIGHT = 2

def get_jc_projects():
    """Get list of folders in C:\\repo starting with JC_"""
    projects = []
    try:
        if os.path.exists(REPO_DIR):
            for d in os.listdir(REPO_DIR):
                if d.startswith("JC_") and os.path.isdir(os.path.join(REPO_DIR, d)):
                    projects.append(d)
    except Exception as e:
        print(f"Error listing projects: {e}")
    return sorted(projects)

def open_project(name):
    """Open the project in the selected editor"""
    try:
        # Use common util to resolve the target (workspace or folder)
        target = utils.resolve_project_target(REPO_DIR, name)
        
        if target:
            # Launch using common util
            success = False
            if useAntigravity:
                success = utils.launch_antigravity(target)
            else:
                success = utils.launch_vscode(target)
                
            if success:
                # Close the dashboard after launching
                root.destroy()
    except Exception as e:
        print(f"Error opening project: {e}")

def create_dashboard():
    global root
    root = tk.Tk()
    root.title(TITLE)
    root.configure(bg="#262626")
    root.resizable(True, True)

    # Main frame
    main_frame = tk.Frame(root, padx=20, pady=20, bg="#262626")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Label for title
    header = tk.Label(main_frame, text="Select JC Project", font=("Segoe UI", 14, "bold"), fg="white", bg="#262626", pady=10)
    header.pack()

    # Grid frame
    grid_frame = tk.Frame(main_frame, bg="#262626")
    grid_frame.pack(fill=tk.BOTH, expand=True)

    projects = get_jc_projects()
    
    for i, project in enumerate(projects):
        row = i // COLUMNS
        col = i % COLUMNS
        
        btn = tk.Button(
            grid_frame,
            text=utils.split_camel_case(project.replace("JC_", "").replace("_", " ")),
            width=BTN_WIDTH,
            height=BTN_HEIGHT,
            bg="#333333",
            fg="white",
            activebackground="#444444",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda p=project: open_project(p),
            font=("Segoe UI", 10, "bold")
        )
        btn.grid(row=row, column=col, padx=PADDING_X, pady=PADDING_Y)
        
        # Add hover effect
        def on_enter(e, b=btn):
            b.config(bg="#444444")
        def on_leave(e, b=btn):
            b.config(bg="#333333")
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    # Center the window using common util
    utils.center_window_on_second_monitor(root)

    # Escape to close
    root.bind("<Escape>", lambda e: root.destroy())

    root.mainloop()

if __name__ == "__main__":
    create_dashboard()
