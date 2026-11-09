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
import math
import ctypes
from ctypes import wintypes

DEFAULT_BROWSER_WINDOW_GEOMETRIES = [
    {
        "x": 18,
        "y": 24,
        "width": 871,
        "height": 1639,
        "work_area_left": 0,
        "work_area_top": 0,
        "work_area_right": 3072,
        "work_area_bottom": 1680,
    },
    {
        "x": 3090,
        "y": 24,
        "width": 2155,
        "height": 1639,
        "work_area_left": 3072,
        "work_area_top": 0,
        "work_area_right": 6144,
        "work_area_bottom": 1680,
    },
]
DEFAULT_BROWSER_WINDOW_GEOMETRY = DEFAULT_BROWSER_WINDOW_GEOMETRIES[0]

class _POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]

class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

class _WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", _POINT),
        ("ptMaxPosition", _POINT),
        ("rcNormalPosition", _RECT),
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

def launch_jc_thegoodworkstation(target_path=None):
    """Launch JC_TheGoodWorkStation via Dashboard.vbs with optional workspace/project target"""
    try:
        vbs_path = r"C:\repo\JC_TheGoodWorkStation\Dashboard.vbs"
        log_info(f"Launching JC_TheGoodWorkStation: {vbs_path} (target: {target_path})")
        if not os.path.exists(vbs_path):
            log_error(f"JC_TheGoodWorkStation script not found at: {vbs_path}")
            return False
        if target_path:
            subprocess.Popen(f'wscript.exe "{vbs_path}" "{target_path}"', shell=True)
        else:
            subprocess.Popen(f'wscript.exe "{vbs_path}"', shell=True)
        return True
    except Exception as e:
        log_error(f"Error launching JC_TheGoodWorkStation: {e}")
        return False

def _normalize_window_geometries(raw_geom):
    """Normalize windowOpenGeometry from settings.json into a list of geometry dicts."""
    items = raw_geom if isinstance(raw_geom, list) else ([raw_geom] if isinstance(raw_geom, dict) else [])
    normalized = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        base = dict(
            DEFAULT_BROWSER_WINDOW_GEOMETRIES[idx]
            if idx < len(DEFAULT_BROWSER_WINDOW_GEOMETRIES)
            else DEFAULT_BROWSER_WINDOW_GEOMETRY
        )
        valid = True
        for key in ("x", "y", "width", "height"):
            val = item.get(key)
            if isinstance(val, int) and not isinstance(val, bool):
                base[key] = val
            else:
                valid = False
                break
        if not valid:
            continue
        if base["x"] >= 3072:
            base["work_area_left"] = 3072
            base["work_area_top"] = 0
            base["work_area_right"] = 6144
            base["work_area_bottom"] = 1680
        else:
            base["work_area_left"] = 0
            base["work_area_top"] = 0
            base["work_area_right"] = 3072
            base["work_area_bottom"] = 1680
        normalized.append(base)
    return normalized if normalized else [dict(g) for g in DEFAULT_BROWSER_WINDOW_GEOMETRIES]


def load_settings(base_path):
    """Load settings.json for Dashboard. // comments are ignored."""
    settings_file_path = os.path.join(base_path, "settings.json")
    log_info(f"Loading settings from: {settings_file_path}")
    with open(settings_file_path, "r", encoding="utf-8") as settings_file:
        settings_text = "\n".join(line.split("//", 1)[0] for line in settings_file)
    settings = json.loads(settings_text)

    browser_to_use = str(settings.get("browserToUser", "Edge")).strip().lower()
    if browser_to_use not in ("edge", "chrome"):
        log_warn(f"Unknown browserToUser '{browser_to_use}', falling back to Edge")
        browser_to_use = "edge"

    profile_command_key = "commandChrome" if browser_to_use == "chrome" else "commandEdge"
    geoms = _normalize_window_geometries(settings.get("windowOpenGeometry"))
    log_info(f"Settings loaded: browserToUser='{browser_to_use}', windowOpenGeometry={geoms}")
    return {
        "browser_to_use": browser_to_use,
        "profile_command_key": profile_command_key,
        "window_open_geometry": geoms,
    }


def _extract_profile_directory(command):
    """Extract the --profile-directory value from a browser launch command."""
    if not command:
        return "Default"
    match = re.search(r'--profile-directory=(?:"([^"]+)"|([^\s]+))', command)
    if not match:
        return "Default"
    return (match.group(1) or match.group(2) or "Default").strip()


def _browser_user_data_dir(command, browser_to_use="chrome"):
    cmd_lower = (command or "").lower()
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    if "msedge.exe" in cmd_lower or browser_to_use == "edge":
        return os.path.join(local_app_data, "Microsoft", "Edge", "User Data")
    return os.path.join(local_app_data, "Google", "Chrome", "User Data")


def apply_browser_profile_window_placement(command, geom=None, browser_to_use="chrome"):
    """Write browser.window_placement into the target profile's Preferences file before launch."""
    if isinstance(geom, list):
        g = geom[0] if geom else DEFAULT_BROWSER_WINDOW_GEOMETRY
    else:
        g = geom or DEFAULT_BROWSER_WINDOW_GEOMETRY
    x = int(g["x"])
    y = int(g["y"])
    width = int(g["width"])
    height = int(g["height"])
    placement = {
        "left": x,
        "top": y,
        "right": x + width,
        "bottom": y + height,
        "maximized": False,
        "work_area_left": int(g.get("work_area_left", 0)),
        "work_area_top": int(g.get("work_area_top", 0)),
        "work_area_right": int(g.get("work_area_right", 3072)),
        "work_area_bottom": int(g.get("work_area_bottom", 1680)),
    }
    try:
        profile_dir = _extract_profile_directory(command)
        user_data_dir = _browser_user_data_dir(command, browser_to_use=browser_to_use)
        pref_path = os.path.join(user_data_dir, profile_dir, "Preferences")
        if not os.path.exists(pref_path):
            os.makedirs(os.path.dirname(pref_path), exist_ok=True)
            data = {}
        else:
            with open(pref_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
        browser_sec = data.get("browser")
        if not isinstance(browser_sec, dict):
            browser_sec = {}
            data["browser"] = browser_sec
        browser_sec["window_placement"] = placement
        with open(pref_path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        log_info(f"Updated Preferences window_placement for '{profile_dir}': {placement}")
    except Exception as e:
        log_warn(f"Could not update browser Preferences window_placement: {e}")


def list_browser_window_hwnds():
    """Return visible top-level Chromium browser HWNDs (Chrome_WidgetWin_1 with caption/thickframe)."""
    hwnds = []
    if os.name != "nt":
        return hwnds
    try:
        user32 = ctypes.windll.user32
        GWL_STYLE = -16
        GWL_EXSTYLE = -20
        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL

        def enum_cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            if user32.GetWindowTextLengthW(hwnd) <= 0:
                return True
            cls_buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, cls_buf, 64)
            if cls_buf.value != "Chrome_WidgetWin_1":
                return True
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if (style & WS_CAPTION) and (style & WS_THICKFRAME) and not (exstyle & WS_EX_TOOLWINDOW):
                hwnds.append(int(hwnd))
            return True

        cb_ref = WNDENUMPROC(enum_cb)
        user32.EnumWindows(cb_ref, 0)
    except Exception as e:
        log_warn(f"list_browser_window_hwnds failed: {e}")
    return hwnds


def set_browser_window_geometry(hwnd, x, y, width, height):
    """Place a Chromium browser HWND at DIP coordinates (x, y, width, height), converting to physical pixels."""
    if os.name != "nt" or not hwnd:
        return False
    user32 = ctypes.windll.user32
    prev_ctx = 0
    try:
        user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
        user32.SetThreadDpiAwarenessContext.restype = ctypes.c_ssize_t
        prev_ctx = user32.SetThreadDpiAwarenessContext(-4)
    except Exception:
        prev_ctx = 0
    try:
        dpi = 96
        try:
            user32.GetDpiForWindow.argtypes = [wintypes.HWND]
            user32.GetDpiForWindow.restype = wintypes.UINT
            win_dpi = int(user32.GetDpiForWindow(hwnd) or 0)
            if win_dpi > 0:
                dpi = win_dpi
        except Exception:
            pass
        scale = (dpi / 96.0) if prev_ctx else 1.0
        px_x = int(math.floor(x * scale))
        px_y = int(math.floor(y * scale))
        px_w = int(math.ceil(width * scale))
        px_h = int(math.ceil(height * scale))

        SW_SHOWNORMAL = 1
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        if user32.IsZoomed(hwnd) or user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_SHOWNORMAL)

        user32.SetWindowPos(
            hwnd,
            0,
            px_x,
            px_y,
            px_w,
            px_h,
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
        return True
    except Exception as e:
        log_warn(f"set_browser_window_geometry failed for HWND={hwnd}: {e}")
        return False
    finally:
        if prev_ctx:
            try:
                user32.SetThreadDpiAwarenessContext(prev_ctx)
            except Exception:
                pass


def launch_browser_with_geometry(
    command,
    geom=None,
    browser_to_use="chrome",
    open_chrome1=True,
    chrome1_urls=None,
    open_chrome2=True,
    chrome2_urls=None,
):
    """Launch the browser profile and open a window for each enabled entry in ``geom`` (Monitor 1 and/or Monitor 2)."""
    geoms = _normalize_window_geometries(geom)
    chrome1_urls = [u.strip() for u in (chrome1_urls or []) if u and u.strip()]
    chrome2_urls = [u.strip() for u in (chrome2_urls or []) if u and u.strip()]

    windows_to_launch = []
    if open_chrome1 and len(geoms) > 0:
        windows_to_launch.append({
            "idx": 0,
            "name": "Monitor 1 (Small)",
            "geom": geoms[0],
            "urls": chrome1_urls,
        })
    if open_chrome2 and len(geoms) > 1:
        windows_to_launch.append({
            "idx": 1,
            "name": "Monitor 2 (Large)",
            "geom": geoms[1],
            "urls": chrome2_urls,
        })
    elif open_chrome2 and len(geoms) == 1:
        windows_to_launch.append({
            "idx": 1,
            "name": "Monitor 2 (Large)",
            "geom": geoms[0],
            "urls": chrome2_urls,
        })

    if not windows_to_launch:
        log_info("No browser windows enabled to launch (open_chrome1=False, open_chrome2=False).")
        return

    first_geom = windows_to_launch[0]["geom"]
    apply_browser_profile_window_placement(command, first_geom, browser_to_use=browser_to_use)

    known_hwnds = set(list_browser_window_hwnds())
    opened_windows = []

    for w_info in windows_to_launch:
        g = w_info["geom"]
        urls = w_info["urls"]
        idx = w_info["idx"]
        w_name = w_info["name"]

        x = int(g["x"])
        y = int(g["y"])
        width = int(g["width"])
        height = int(g["height"])

        # Check if an earlier launch in this loop already spawned an extra window (only if no specific URLs need launching)
        unclaimed = [h for h in list_browser_window_hwnds() if h not in known_hwnds]
        if unclaimed and not urls:
            target_hwnd = unclaimed[0]
            known_hwnds.add(target_hwnd)
            opened_windows.append((target_hwnd, g))
            set_browser_window_geometry(target_hwnd, x, y, width, height)
            log_info(f"Claimed extra browser HWND={target_hwnd} for {w_name} at DIP=({x}, {y}, {width}x{height})")
            continue

        full_command = command
        if "--new-window" not in full_command:
            full_command = f"{full_command} --new-window"
        if "--window-position=" not in full_command:
            full_command = f"{full_command} --window-position={x},{y}"
        if "--window-size=" not in full_command:
            full_command = f"{full_command} --window-size={width},{height}"

        if urls:
            url_args = " ".join(f'"{u}"' for u in urls)
            full_command = f"{full_command} {url_args}"

        log_info(f"Launching browser {w_name} with geometry ({x}, {y}, {width}x{height}): {full_command}")
        subprocess.Popen(full_command, shell=True)

        timeout_s = 4.0 if idx == 0 else 3.0
        deadline = time.monotonic() + timeout_s
        target_hwnd = None
        while time.monotonic() < deadline:
            current_hwnds = list_browser_window_hwnds()
            new_hwnds = [h for h in current_hwnds if h not in known_hwnds]
            if new_hwnds:
                target_hwnd = new_hwnds[0]
                known_hwnds.add(target_hwnd)
                break
            time.sleep(0.02)

        if target_hwnd is not None:
            opened_windows.append((target_hwnd, g))
            for _ in range(2):
                set_browser_window_geometry(target_hwnd, x, y, width, height)
                time.sleep(0.03)
            log_info(f"Positioned browser {w_name} HWND={target_hwnd} at DIP=({x}, {y}, {width}x{height})")
        else:
            log_warn(f"Browser {w_name} HWND was not detected within {timeout_s}s.")

    # Re-enforce geometry across all opened windows so neither drifts or cascades during tab restore
    if opened_windows:
        for _ in range(6):
            for hwnd, g in opened_windows:
                set_browser_window_geometry(hwnd, int(g["x"]), int(g["y"]), int(g["width"]), int(g["height"]))
            time.sleep(0.05)
        apply_browser_profile_window_placement(command, first_geom, browser_to_use=browser_to_use)

def resolve_project_target(repo_dir, name):
    """Resolve the best target (workspace or folder) for a project name"""
    candidates = [name]
    if not name.startswith("JC_"):
        candidates.append(f"JC_{name}")
    else:
        candidates.append(name[3:])

    for cand in candidates:
        project_path = os.path.join(repo_dir, cand)
        workspace_file = os.path.join(project_path, f"{cand}.code-workspace")
        hash_workspace_file = os.path.join(project_path, f"#{cand}.code-workspace")
        if os.path.exists(workspace_file):
            return workspace_file
        elif os.path.exists(hash_workspace_file):
            return hash_workspace_file
        if os.path.exists(project_path):
            return project_path

    return None

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

def char_from_key_event(event):
    """
    Return a printable character from a KeyPress event if not pressed with Ctrl or Alt.
    Handles Windows NumLock state (0x8) gracefully so NumLock doesn't register as Alt.
    """
    ctrl = bool(event.state & 0x4)
    if sys.platform == "win32":
        alt = bool(event.state & 0x20000)
    else:
        alt = bool(event.state & 0x8) or bool(event.state & 0x20000)
    if ctrl or alt:
        return ""
    if event.char and event.char.isprintable():
        return event.char
    keysym = event.keysym or ""
    if len(keysym) == 1 and keysym.isprintable():
        return keysym
    return ""


