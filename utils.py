import os
import shutil
import subprocess
import re
import time
import json
import datetime
import traceback
import sys
import threading
import ctypes
from ctypes import wintypes

class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32)
    ]

class _LogStream:
    def __init__(self, app_logger, level, original_stream=None):
        self.app_logger = app_logger
        self.level = level
        self.original_stream = original_stream
        self._buffer = ""
        self._in_write = False

    def write(self, s):
        if self._in_write or not s:
            return
        self._in_write = True
        try:
            if self.original_stream and not getattr(self.original_stream, 'closed', False):
                try:
                    self.original_stream.write(s)
                except Exception:
                    pass
            self._buffer += s
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                line = line.rstrip("\r")
                if line:
                    self.app_logger._write(self.level, f"[STREAM] {line}")
        finally:
            self._in_write = False

    def flush(self):
        if self._in_write:
            return
        self._in_write = True
        try:
            if self._buffer.strip():
                self.app_logger._write(self.level, f"[STREAM] {self._buffer.strip()}")
                self._buffer = ""
            if self.original_stream and not getattr(self.original_stream, 'closed', False):
                try:
                    self.original_stream.flush()
                except Exception:
                    pass
        finally:
            self._in_write = False

class AppLogger:
    def __init__(self, script_path):
        self.script_path = os.path.abspath(script_path)
        self.base_dir = os.path.dirname(self.script_path)
        script_name = os.path.splitext(os.path.basename(self.script_path))[0]
        self.log_file = os.path.join(self.base_dir, f"{script_name}_output.txt")
        self._orig_stdout = None
        self._orig_stderr = None
        self._init_log_file(script_name)
        self._install_hooks()

    def _init_log_file(self, script_name):
        header = [
            "=" * 70,
            f" LOG: {script_name}.py",
            f" Time: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
            f" CWD:  {os.getcwd()}",
            f" Python: {sys.version.split()[0]} ({sys.executable})",
            f" Args: {' '.join(sys.argv) if sys.argv else '(none)'}",
            "=" * 70,
            ""
        ]
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(header) + "\n")

    def _install_hooks(self):
        def excepthook(exc_type, exc_value, exc_traceback):
            tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.error(f"Uncaught exception:\n{tb_str}")
            if sys.__excepthook__:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)

        sys.excepthook = excepthook

        if hasattr(threading, 'excepthook'):
            def threading_excepthook(args):
                tb_str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
                self.error(f"Uncaught thread exception in thread '{args.thread.name}':\n{tb_str}")

            threading.excepthook = threading_excepthook

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = _LogStream(self, "INFO", self._orig_stdout)
        sys.stderr = _LogStream(self, "ERR", self._orig_stderr)

    def _write(self, level, msg):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{level}] {msg}"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception:
            pass
        if self._orig_stdout and not getattr(self._orig_stdout, 'closed', False):
            try:
                self._orig_stdout.write(line + "\n")
                self._orig_stdout.flush()
            except Exception:
                pass

    def info(self, msg):
        self._write("INFO", msg)

    def warn(self, msg):
        self._write("WRN", msg)

    def error(self, msg):
        self._write("ERR", msg)

    def debug(self, msg):
        self._write("DBG", msg)

logger = None

def setup_logger(script_path):
    global logger
    logger = AppLogger(script_path)
    return logger

def get_logger():
    global logger
    return logger

def log_info(msg):
    if logger:
        logger.info(msg)
    else:
        print(f"[INFO] {msg}")

def log_error(msg):
    if logger:
        logger.error(msg)
    else:
        print(f"[ERR] {msg}")

def log_warn(msg):
    if logger:
        logger.warn(msg)
    else:
        print(f"[WRN] {msg}")

def install_tk_exception_handler(window, app_logger=None):
    """Intercept and log any uncaught exceptions inside Tkinter callbacks"""
    l = app_logger or logger
    if not l:
        return

    def report_callback_exception(exc, val, tb):
        tb_str = "".join(traceback.format_exception(exc, val, tb))
        l.error(f"Uncaught Tkinter callback exception:\n{tb_str}")

    window.report_callback_exception = report_callback_exception

def attach_event_logger(window, app_logger=None):
    """Log Tkinter window lifecycle and state events"""
    l = app_logger or logger
    if not l:
        return

    def on_map(event):
        if event.widget == window:
            l.info(f"Event: Window <Map> (visible on screen). Geometry: {window.geometry()}, winfo_x: {window.winfo_x()}, winfo_y: {window.winfo_y()}")

    def on_unmap(event):
        if event.widget == window:
            l.info("Event: Window <Unmap> (hidden from screen)")

    def on_focus_in(event):
        if event.widget == window:
            l.info("Event: Window <FocusIn> (gained focus)")

    def on_focus_out(event):
        if event.widget == window:
            l.info("Event: Window <FocusOut> (lost focus)")

    def on_destroy(event):
        if event.widget == window:
            l.info("Event: Window <Destroy> (being destroyed)")

    window.bind("<Map>", on_map, add="+")
    window.bind("<Unmap>", on_unmap, add="+")
    window.bind("<FocusIn>", on_focus_in, add="+")
    window.bind("<FocusOut>", on_focus_out, add="+")
    window.bind("<Destroy>", on_destroy, add="+")

def get_display_monitors():
    """Enumerate all connected physical monitors using Windows API with DPI awareness"""
    monitors = []
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4) # Per-monitor v2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
        except Exception:
            pass

    user32 = ctypes.windll.user32

    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
            monitors.append({
                "hMonitor": hMonitor,
                "device": str(info.szDevice),
                "is_primary": bool(info.dwFlags & 1),
                "monitor_rect": (info.rcMonitor.left, info.rcMonitor.top, info.rcMonitor.right, info.rcMonitor.bottom),
                "work_rect": (info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)
            })
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(_RECT), wintypes.LPARAM)
    user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(monitor_enum_proc), 0)
    return monitors

def split_camel_case(text):
    """Split camelCase text by inserting spaces before uppercase letters"""
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', text)

def get_antigravity_path():
    """Find the absolute path to the Antigravity IDE executable"""
    path = shutil.which('antigravity-ide')
    if path:
        return path

    for potential_path in (
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Antigravity IDE\bin\antigravity-ide.cmd'),
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Antigravity IDE\Antigravity IDE.exe'),
    ):
        if os.path.exists(potential_path):
            return potential_path

    return 'antigravity-ide'

def launch_antigravity(target_path):
    """Launch Antigravity IDE with the specified path"""
    try:
        antigravity_exe = get_antigravity_path()
        log_info(f"Antigravity IDE executable: {antigravity_exe}")
        # Direct invocation with shell=True is reliable for Windows .cmd files
        subprocess.Popen(f'"{antigravity_exe}" "{target_path}"', shell=True)
        return True
    except Exception as e:
        print(f"Error launching Antigravity IDE: {e}")
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
    """Launch Cursor with the specified path in IDE (classic editor) view"""
    try:
        cursor_exe = get_cursor_path()
        # --classic opens the editor window instead of the Agents window
        subprocess.Popen(f'"{cursor_exe}" --classic "{target_path}"', shell=True)
        return True
    except Exception as e:
        print(f"Error launching Cursor: {e}")
        return False

def launch_editor(target_path):
    """Launch Cursor with the specified path"""
    return launch_cursor(target_path)

def load_settings(base_path):
    """Load settings.json for Dashboard and PickJcProject. // comments are ignored."""
    settings_file_path = os.path.join(base_path, "settings.json")
    log_info(f"Loading settings from: {settings_file_path}")
    with open(settings_file_path, "r", encoding="utf-8") as settings_file:
        settings_text = "\n".join(line.split("//", 1)[0] for line in settings_file)
    settings = json.loads(settings_text)

    browser_to_use = str(settings.get("browserToUser", "Edge")).strip().lower()
    if browser_to_use not in ("edge", "chrome"):
        log_warn(f"Unknown browserToUser '{browser_to_use}', falling back to Edge")
        browser_to_use = "edge"

    code_editor = str(settings.get("codeEditor", "Cursor")).strip().lower()
    if code_editor not in ("cursor", "antigravity"):
        log_warn(f"Unknown codeEditor '{code_editor}', falling back to Cursor")
        code_editor = "cursor"

    profile_command_key = "commandChrome" if browser_to_use == "chrome" else "commandEdge"
    log_info(f"Settings loaded: browserToUser='{browser_to_use}', codeEditor='{code_editor}'")
    return {
        "browser_to_use": browser_to_use,
        "profile_command_key": profile_command_key,
        "code_editor": code_editor,
    }

def launch_code_editor(target_path, code_editor):
    """Launch the editor selected by the codeEditor setting"""
    if str(code_editor).strip().lower() == "antigravity":
        log_info(f"Launching Antigravity with target: {target_path}")
        return launch_antigravity(target_path)
    log_info(f"Launching Cursor with target: {target_path}")
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

def find_workspace_file(target_path):
    """Find the .code-workspace file associated with target_path, if any."""
    if not target_path:
        return None

    if os.path.isfile(target_path) and target_path.endswith('.code-workspace'):
        return target_path

    if os.path.isdir(target_path):
        folder_name = os.path.basename(os.path.normpath(target_path))
        # Check standard naming patterns
        for candidate_name in (f"#{folder_name}.code-workspace", f"{folder_name}.code-workspace"):
            candidate_path = os.path.join(target_path, candidate_name)
            if os.path.isfile(candidate_path):
                return candidate_path

        # Check any .code-workspace in the directory
        try:
            for item in os.listdir(target_path):
                if item.endswith('.code-workspace'):
                    candidate_path = os.path.join(target_path, item)
                    if os.path.isfile(candidate_path):
                        return candidate_path
        except Exception:
            pass

    return None

def get_good_library_path_if_included(target_path):
    """If the target's workspace file includes the-good-library, return its absolute path; else None."""
    workspace_file = find_workspace_file(target_path)
    if not workspace_file or not os.path.isfile(workspace_file):
        return None

    try:
        with open(workspace_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading workspace file {workspace_file}: {e}")
        return None

    includes_good_lib = False
    good_lib_relative_path = None

    # Try parsing JSON (stripping JSONC comments if present)
    try:
        cleaned = re.sub(r'//.*', '', content)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        data = json.loads(cleaned)
        folders = data.get('folders', [])
        for folder in folders:
            path_val = folder.get('path', '')
            name_val = folder.get('name', '')
            if 'the-good-library' in path_val or 'the-good-library' in name_val:
                includes_good_lib = True
                if path_val:
                    good_lib_relative_path = path_val
                break
    except Exception:
        # Fallback if JSON parsing fails
        if 'the-good-library' in content:
            includes_good_lib = True
            match = re.search(r'"path"\s*:\s*"([^"]*the-good-library[^"]*)"', content)
            if match:
                good_lib_relative_path = match.group(1)

    if not includes_good_lib:
        return None

    workspace_dir = os.path.dirname(os.path.abspath(workspace_file))
    if good_lib_relative_path:
        candidate_path = os.path.normpath(os.path.join(workspace_dir, good_lib_relative_path))
        if os.path.exists(candidate_path):
            return candidate_path

    # Standard fallback locations
    for fallback in (
        os.path.normpath(os.path.join(workspace_dir, '..', 'the-good-library')),
        r'C:\repo\the-good-library',
    ):
        if os.path.exists(fallback):
            return fallback

    return None

def _open_sourcetree_repo(sourcetree_exe, repo_path):
    """Open or focus a single repo in SourceTree"""
    result = subprocess.run([sourcetree_exe, '-f', repo_path], shell=False)
    if result.returncode != 0:
        subprocess.Popen([sourcetree_exe, repo_path], shell=False)

def launch_sourcetree(target_path):
    """Launch SourceTree with the repo folder for the specified target.
    If the selected project workspace includes the-good-library, open that repo first, then the target.
    """
    log_info(f"launch_sourcetree called with target: {target_path}")
    try:
        sourcetree_exe = get_sourcetree_path()
        repo_path = os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
        repo_path = os.path.normpath(repo_path)
        log_info(f"Target repo folder: {repo_path}")

        # SourceTree must already be running before -f / path args are handled.
        if not is_sourcetree_running():
            log_info("SourceTree is not running. Launching SourceTree process...")
            subprocess.Popen([sourcetree_exe], shell=False)
            if not wait_for_sourcetree():
                print("SourceTree did not start in time")
                log_error("SourceTree did not start in time")
                return False
            log_info("SourceTree started successfully.")
        else:
            log_info("SourceTree is already running.")

        # Open the-good-library first when the workspace includes it, then the target repo.
        good_lib_path = get_good_library_path_if_included(target_path)
        if good_lib_path and os.path.normcase(os.path.normpath(good_lib_path)) != os.path.normcase(repo_path):
            log_info(f"get_good_library_path_if_included found '{good_lib_path}'. Opening it in SourceTree first...")
            _open_sourcetree_repo(sourcetree_exe, good_lib_path)
            time.sleep(0.5)
        else:
            log_info("Workspace does not include a separate the-good-library path.")

        log_info(f"Opening '{repo_path}' in SourceTree...")
        _open_sourcetree_repo(sourcetree_exe, repo_path)
        log_info("SourceTree launched successfully.")
        return True
    except Exception as e:
        print(f"Error launching SourceTree: {e}")
        log_error(f"Error launching SourceTree: {e}")
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
    """Position the tkinter window in the center of the second monitor, or the primary monitor if only one is connected, and show it."""
    window.update_idletasks()

    window_width = window.winfo_width() if window.winfo_width() > 1 else window.winfo_reqwidth()
    window_height = window.winfo_height() if window.winfo_height() > 1 else window.winfo_reqheight()
    if window_width <= 1:
        window_width = 670
    if window_height <= 1:
        window_height = 786

    log_info(f"Target window dimensions: {window_width}x{window_height}")

    monitors = []
    try:
        monitors = get_display_monitors()
    except Exception as e:
        log_warn(f"Failed to enumerate monitors via Win32: {e}")

    log_info(f"Detected {len(monitors)} monitor(s):")
    for idx, m in enumerate(monitors):
        log_info(f"  Monitor {idx + 1}: Device={m['device']}, Primary={m['is_primary']}, MonitorRect={m['monitor_rect']}, WorkRect={m['work_rect']}")

    target_monitor = None
    if len(monitors) > 1:
        # Prefer the rightmost non-primary monitor
        non_primaries = [m for m in monitors if not m["is_primary"]]
        if non_primaries:
            non_primaries.sort(key=lambda m: m["work_rect"][0])
            target_monitor = non_primaries[-1]
            log_info(f"Selected secondary monitor: Device={target_monitor['device']}, WorkRect={target_monitor['work_rect']}")
        else:
            target_monitor = monitors[0]
            log_info(f"No non-primary monitor found; using first monitor: Device={target_monitor['device']}")
    elif len(monitors) == 1:
        target_monitor = monitors[0]
        log_warn(f"Only 1 monitor detected. Falling back to primary monitor: Device={target_monitor['device']}, WorkRect={target_monitor['work_rect']}")
    else:
        log_warn("No monitors detected via Win32 API. Using Tkinter screen metrics fallback.")

    if target_monitor:
        wr = target_monitor["work_rect"]
        work_left, work_top, work_right, work_bottom = wr
        work_width = work_right - work_left
        work_height = work_bottom - work_top
        
        center_x = work_left + (work_width // 2)
        center_y = work_top + (work_height // 2)
        
        x = center_x - (window_width // 2)
        y = center_y - (window_height // 2)
    else:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        second_monitor_x = screen_width
        second_monitor_center_x = second_monitor_x + (screen_width // 2)
        second_monitor_center_y = screen_height // 2
        x = second_monitor_center_x - (window_width // 2)
        y = second_monitor_center_y - (window_height // 2)

    geom_str = f"{window_width}x{window_height}+{x}+{y}"
    window.geometry(geom_str)
    log_info(f"Set window geometry to: {geom_str}")

    # Realize window position with Windows OS before setting topmost
    window.deiconify()
    window.update()

    # Surface window cleanly above existing windows upon launch without resetting geometry
    try:
        window.lift()
        window.attributes('-topmost', True)
        def _clear_topmost():
            try:
                if window.winfo_exists():
                    window.attributes('-topmost', False)
            except Exception:
                pass
        # Keep topmost active for 500ms to guarantee window appears above full-screen apps, then release
        window.after(500, _clear_topmost)
    except Exception as e:
        log_warn(f"Could not set topmost attribute: {e}")

    try:
        window.focus_force()
    except Exception:
        pass

    # Post-placement verification
    try:
        actual_geom = window.geometry()
        actual_x = window.winfo_x()
        actual_y = window.winfo_y()
        log_info(f"Tkinter window mapped at: geometry='{actual_geom}', winfo_pos=({actual_x}, {actual_y})")

        # Win32 API verification
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
        rect = _RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            log_info(f"Win32 API verification: HWND={hwnd}, Rect=({rect.left}, {rect.top}, {rect.right}, {rect.bottom}), IsVisible={bool(user32.IsWindowVisible(hwnd))}")
    except Exception as e:
        log_warn(f"Post-placement verification error: {e}")


