#!/usr/bin/env node

// Inline logging to <scriptname>_output.txt
import { writeFileSync as __logWFS, appendFileSync as __logAFS, mkdirSync as __logMKDIR } from "node:fs";
import { resolve as __logResolve, dirname as __logDirname, basename as __logBasename } from "node:path";
import { fileURLToPath as __logFTUP } from "node:url";
const __logDir = __logDirname(__logFTUP(import.meta.url));
const __logName = __logBasename(__logFTUP(import.meta.url), ".mjs");
const __logPath = __logResolve(__logDir, __logName + "_output.txt");
__logMKDIR(__logDir, { recursive: true });
__logWFS(__logPath, ["=".repeat(70)," LOG: " + __logName + ".mjs"," Time: " + new Date().toISOString()," CWD:  " + process.cwd()," Node: " + process.version," Args: " + (process.argv.slice(2).join(" ") || "(none)"),"=".repeat(70),"",""].join("\n"));
const __origLog=console.log,__origErr=console.error,__origWarn=console.warn;
function __wl(s){__logAFS(__logPath,s+"\n")}
console.log=(...a)=>{__wl(a.map(String).join(" "));__origLog(...a)};
console.error=(...a)=>{__wl("[ERR] "+a.map(String).join(" "));__origErr(...a)};
console.warn=(...a)=>{__wl("[WRN] "+a.map(String).join(" "));__origWarn(...a)};

/**
 * Add a new Edge profile with image, bookmarks, and dashboard registration.
 * Equivalent to: addProfile.bat
 *
 * Requires Python to be installed for the setup script.
 */

import { createInterface } from "node:readline";
import { existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { execSync } from "node:child_process";

function cmdExists(cmd) {
  try {
    execSync(`where ${cmd}`, { stdio: "ignore" });
    return true;
  } catch { return false; }
}

if (!cmdExists("python")) {
  console.error("Error: Python is not installed or not in PATH.");
  process.exit(1);
}

const rl = createInterface({ input: process.stdin, output: process.stdout });
function ask(question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

// 1. File Selection via PowerShell
console.log("Please select the PNG image for the new profile...");
let SOURCE_FILE = "";
try {
  SOURCE_FILE = execSync(
    'powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.OpenFileDialog; $f.Filter = \'PNG Files (*.png)|*.png\'; $f.InitialDirectory = [System.Environment]::GetFolderPath(\'Desktop\'); $res = $f.ShowDialog(); if($res -eq \'OK\'){ $f.FileName }"',
    { encoding: "utf8" }
  ).trim();
} catch {}

if (!SOURCE_FILE) {
  console.log("[ERROR] No file selected.");
  process.exit(1);
}

if (!existsSync(SOURCE_FILE)) {
  console.log(`[ERROR] Selected file does not exist: ${SOURCE_FILE}`);
  process.exit(1);
}

// Configuration
const PY_FILE = "C:\\repo\\JC_PickEdgeProfile\\Dashboard.py";
const IMAGES_DIR = "C:\\repo\\JC_PickEdgeProfile\\images";

// 2. Prompt for Profile Name
let PROFILE_NAME = "";
while (!PROFILE_NAME) {
  PROFILE_NAME = (await ask("Enter Profile Name (e.g. Sticker Boys): ")).trim();
  if (!PROFILE_NAME) continue;

  // Check if name exists in Dashboard.py
  try {
    const checkResult = execSync(
      `python -c "import sys; p=r'${PY_FILE}'; c=open(p, encoding='utf-8').read(); print('EXISTS' if f'\\\"name\\\": \\\"{PROFILE_NAME}\\\"' in c else 'OK')"`,
      { encoding: "utf8" }
    ).trim();
    if (checkResult === "EXISTS") {
      console.log(
        `[ERROR] Profile Name '${PROFILE_NAME}' already exists in Dashboard.py.`
      );
      PROFILE_NAME = "";
    }
  } catch {
    console.log("[ERROR] Failed to check Dashboard.py");
    process.exit(1);
  }
}
rl.close();

// 3. Verify PY_FILE exists
if (!existsSync(PY_FILE)) {
  console.log(`[ERROR] Could not find ${PY_FILE}`);
  process.exit(1);
}

// 4. Rename and move the image
console.log(`Renaming ${SOURCE_FILE} to ${PROFILE_NAME}.png...`);
const TARGET_FILE = resolve(IMAGES_DIR, `${PROFILE_NAME}.png`);

if (!existsSync(IMAGES_DIR)) {
  mkdirSync(IMAGES_DIR, { recursive: true });
}

try {
  execSync(`move "${SOURCE_FILE}" "${TARGET_FILE}"`);
} catch {
  console.log("[ERROR] Failed to move/rename file.");
  process.exit(1);
}

// 5. Run the Python setup script (ported inline from the bat)
// The bat generates a temp Python script, let me do the same
console.log("Creating Edge profile, injecting bookmarks, and updating Dashboard.py...");

const { writeFileSync, unlinkSync } = await import("node:fs");
const { tmpdir } = await import("node:os");
const { join } = await import("node:path");

const SETUP_SCRIPT = join(tmpdir(), "setup_edge_profile.py");
const STATUS_FILE = join(tmpdir(), "setup_status.txt");

const pythonSetup = `
import sys, re, os, json
name = sys.argv[1]
py_file = sys.argv[2]
user_data_dir = os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Edge', 'User Data')
local_state_path = os.path.join(user_data_dir, 'Local State')
max_num = 0
for entry in os.listdir(user_data_dir):
    m = re.match(r'^Profile (\\d+)$', entry)
    if m:
        n = int(m.group(1))
        if n > max_num: max_num = n
new_num = max_num + 1
profile_dir_name = 'Profile ' + str(new_num)
new_profile_path = os.path.join(user_data_dir, profile_dir_name)
os.makedirs(new_profile_path, exist_ok=True)
bm_child = {"date_added": "13250000000000000", "guid": "5d399380-6060-466d-9610-1c099309623e", "id": "5", "name": "Outlook", "type": "url", "url": "https://outlook.live.com/mail/0/"}
bm_bar = {"children": [bm_child], "date_added": "13250000000000000", "date_modified": "13250000000000000", "id": "1", "name": "Favorites bar", "type": "folder"}
bm_other = {"children": [], "id": "2", "name": "Other favorites", "type": "folder"}
bm_synced = {"children": [], "id": "3", "name": "Mobile favorites", "type": "folder"}
bookmarks = {"checksum": "", "roots": {"bookmark_bar": bm_bar, "other": bm_other, "synced": bm_synced}, "version": 1}
with open(os.path.join(new_profile_path, 'Bookmarks'), 'w', encoding='utf-8') as f: json.dump(bookmarks, f, indent=3)
with open(local_state_path, 'r', encoding='utf-8') as f: local_state = json.load(f)
info_entry = {"name": name, "shortcut_name": "", "user_name": "", "managed_user_id": "", "is_omitted_from_profile_list": False}
local_state.setdefault('profile', {}).setdefault('info_cache', {})[profile_dir_name] = info_entry
profiles_order = local_state['profile'].setdefault('profiles_order', [])
if profile_dir_name not in profiles_order: profiles_order.append(profile_dir_name)
with open(local_state_path, 'w', encoding='utf-8') as f: json.dump(local_state, f, indent=3)
with open(py_file, 'r', encoding='utf-8') as f: content = f.read()
pattern = re.compile(r'(EDGE_PROFILES = \\[.*?)\\s*(\\])', re.DOTALL)
match = pattern.search(content)
if match:
    middle = match.group(1).rstrip()
    if middle.endswith('}'): middle += ','
    cmd = '\\\\"C:\\\\\\\\Program Files (x86)\\\\\\\\Microsoft\\\\\\\\Edge\\\\\\\\Application\\\\\\\\msedge.exe\\\\" --profile-directory=\\\\"' + profile_dir_name + '\\\\"'
    entry = '\\n    {\\n        "name": "' + name + '",\\n        "command": "' + cmd + '"\\n    }'
    suffix = '\\n]'
    new_content = content[:match.start()] + middle + entry + suffix + content[match.end():]
    with open(py_file, 'w', encoding='utf-8') as f: f.write(new_content)
    print(profile_dir_name)
else:
    print("FAILED")
`;

writeFileSync(SETUP_SCRIPT, pythonSetup);

let PROFILE_DIR = "";
try {
  PROFILE_DIR = execSync(
    `python "${SETUP_SCRIPT}" "${PROFILE_NAME}" "${PY_FILE}"`,
    { encoding: "utf8" }
  ).trim();
} catch {}
try { unlinkSync(SETUP_SCRIPT); } catch {}

if (PROFILE_DIR === "FAILED" || !PROFILE_DIR) {
  console.log("[ERROR] Failed to create Edge profile or update Dashboard.py.");
  process.exit(1);
}

console.log();
console.log("==========================================================");
console.log(`SUCCESS!`);
console.log(`Profile '${PROFILE_NAME}' (${PROFILE_DIR}) was added.`);
console.log(`Image saved to: ${TARGET_FILE}`);
console.log("Dashboard.py updated.");
console.log("==========================================================");
console.log();

// 6. Launch Edge with the new profile
console.log(`Launching new profile '${PROFILE_NAME}'...`);
try {
  execSync(
    `start "" "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --profile-directory="${PROFILE_DIR}" --no-first-run`,
    { stdio: "ignore" }
  );
} catch {}

console.log();
console.log("Done!");
