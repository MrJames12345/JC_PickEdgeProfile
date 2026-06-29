import os
import shutil
import subprocess
import re
import time

def split_camel_case(text):
    """Split camelCase text by inserting spaces before uppercase letters"""
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', text)

def get_antigravity_path():
    """Find the absolute path to the antigravity executable"""
    path = shutil.which('antigravity')
    if not path:
        # Fallback to common location if not in PATH
        potential_path = os.path.expandvars(r'%LOCALAPPDATA%\Programs\Antigravity\bin\antigravity.cmd')
        if os.path.exists(potential_path):
            return potential_path
    return path or 'antigravity'

def launch_antigravity(target_path):
    """Launch Antigravity with the specified path"""
    try:
        antigravity_exe = get_antigravity_path()
        # Direct invocation with shell=True is reliable for Windows .cmd files
        subprocess.Popen(f'"{antigravity_exe}" "{target_path}"', shell=True)
        return True
    except Exception as e:
        print(f"Error launching Antigravity: {e}")
        return False

def get_cursor_path():
    """Find the absolute path to the Cursor executable"""
    path = shutil.which('cursor')
    if path:
        return path

    for potential_path in (
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\cursor\Cursor.exe'),
        r'C:\cursor\Cursor.exe',
    ):
        if os.path.exists(potential_path):
            return potential_path

    return 'cursor'

def launch_cursor(target_path):
    """Launch Cursor with the specified path"""
    try:
        cursor_exe = get_cursor_path()
        subprocess.Popen(f'"{cursor_exe}" "{target_path}"', shell=True)
        return True
    except Exception as e:
        print(f"Error launching Cursor: {e}")
        return False

def launch_editor(target_path):
    """Launch Cursor with the specified path"""
    return launch_cursor(target_path)

def get_sourcetree_path():
    """Find the absolute path to the SourceTree executable"""
    path = shutil.which('sourcetree')
    if path:
        return path

    potential_path = os.path.expandvars(r'%LOCALAPPDATA%\SourceTree\SourceTree.exe')
    if os.path.exists(potential_path):
        return potential_path

    return 'sourcetree'

def is_sourcetree_running():
    """Return True if SourceTree is already running"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq SourceTree.exe', '/NH'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return 'SourceTree.exe' in result.stdout
    except Exception:
        return False

def wait_for_sourcetree(timeout=10):
    """Wait until SourceTree process is running and briefly responsive"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_sourcetree_running():
            time.sleep(0.5)
            return True
        time.sleep(0.2)
    return False

def launch_sourcetree(target_path):
    """Launch SourceTree with the repo folder for the specified target"""
    try:
        sourcetree_exe = get_sourcetree_path()
        repo_path = os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
        repo_path = os.path.normpath(repo_path)

        # SourceTree must already be running before -f / path args are handled.
        if not is_sourcetree_running():
            subprocess.Popen([sourcetree_exe], shell=False)
            if not wait_for_sourcetree():
                print("SourceTree did not start in time")
                return False

        # Prefer SourceTree's explicit open/focus-repository argument.
        # Fallback to plain path invocation for installations that ignore -f.
        result = subprocess.run([sourcetree_exe, '-f', repo_path], shell=False)
        if result.returncode != 0:
            subprocess.Popen([sourcetree_exe, repo_path], shell=False)
        return True
    except Exception as e:
        print(f"Error launching SourceTree: {e}")
        return False

def resolve_project_target(repo_dir, name):
    """Resolve the best target (workspace or folder) for a project name"""
    project_path = os.path.join(repo_dir, name)
    # Check for <name>.code-workspace or #<name>.code-workspace
    workspace_file = os.path.join(project_path, f"{name}.code-workspace")
    hash_workspace_file = os.path.join(project_path, f"#{name}.code-workspace")
    
    if os.path.exists(workspace_file):
        return workspace_file
    elif os.path.exists(hash_workspace_file):
        return hash_workspace_file
    
    return project_path if os.path.exists(project_path) else None

def center_window_on_second_monitor(window):
    """Position the tkinter window in the center of the second monitor (to the right)"""
    window.update_idletasks()
    
    window_width = window.winfo_reqwidth()
    window_height = window.winfo_reqheight()

    # Get the screen width and height of primary monitor
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Assuming second monitor is to the right and has same resolution
    second_monitor_x = screen_width
    second_monitor_center_x = second_monitor_x + (screen_width // 2)
    second_monitor_center_y = screen_height // 2
    
    x = second_monitor_center_x - (window_width // 2)
    y = second_monitor_center_y - (window_height // 2)
    
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")
