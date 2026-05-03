import os
import shutil
import subprocess
import re

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

def launch_vscode(target_path):
    """Launch VS Code with the specified path"""
    try:
        # 'code' is the standard command for VS Code if it's in PATH
        subprocess.Popen(f'code "{target_path}"', shell=True)
        return True
    except Exception as e:
        print(f"Error launching VS Code: {e}")
        return False

def get_sourcetree_path():
    """Find the absolute path to the SourceTree executable"""
    path = shutil.which('sourcetree')
    if path:
        return path

    potential_path = os.path.expandvars(r'%LOCALAPPDATA%\SourceTree\SourceTree.exe')
    if os.path.exists(potential_path):
        return potential_path

    return 'sourcetree'

def launch_sourcetree(target_path):
    """Launch SourceTree with the repo folder for the specified target"""
    try:
        sourcetree_exe = get_sourcetree_path()
        repo_path = os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
        repo_path = os.path.normpath(repo_path)

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
