@echo off
setlocal enabledelayedexpansion

:: -----------------------------------------------------------------------------
:: Dashboard - New Profile Script
:: -----------------------------------------------------------------------------

:: 1. File Selection - Prompt via PowerShell File Picker
echo Please select the PNG image for the new profile...
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.OpenFileDialog; $f.Filter = 'PNG Files (*.png)|*.png'; $f.InitialDirectory = [System.Environment]::GetFolderPath('Desktop'); $res = $f.ShowDialog(); if($res -eq 'OK'){ $f.FileName }"`) do set "SOURCE_FILE=%%I"

if "%SOURCE_FILE%"=="" (
    echo [ERROR] No file selected.
    echo Please select a PNG file to process.
    pause
    exit /b 1
)

if not exist "%SOURCE_FILE%" (
    echo [ERROR] Selected file does not exist: %SOURCE_FILE%
    pause
    exit /b 1
)


:: Configuration
set "PY_FILE=C:\repo\JC_PickEdgeProfile\Dashboard.py"
set "IMAGES_DIR=C:\repo\JC_PickEdgeProfile\images"

:: 2. Prompt for Profile Name
:PROMPT_NAME
set "PROFILE_NAME="
set /p PROFILE_NAME="Enter Profile Name (e.g. Sticker Boys): "
if "%PROFILE_NAME%"=="" goto PROMPT_NAME

:: Check if name exists in Dashboard.py
python -c "import sys; p=r'%PY_FILE%'; c=open(p).read(); print('EXISTS' if f'\"name\": \"{sys.argv[1]}\"' in c else 'OK')" "%PROFILE_NAME%" > "%temp%\check_name.txt"
set /p NAME_STATUS=<"%temp%\check_name.txt"
if "!NAME_STATUS!"=="EXISTS" (
    echo [ERROR] Profile Name '%PROFILE_NAME%' already exists in Dashboard.py.
    goto PROMPT_NAME
)

:: 3. Final Verification
if not exist "%PY_FILE%" (
    echo [ERROR] Could not find %PY_FILE%
    pause
    exit /b 1
)

:: 5. Renaming and Moving
echo Renaming %SOURCE_FILE% to %PROFILE_NAME%.png...
set "TARGET_FILE=%IMAGES_DIR%\%PROFILE_NAME%.png"

if not exist "%IMAGES_DIR%" (
    mkdir "%IMAGES_DIR%"
)

move "%SOURCE_FILE%" "%TARGET_FILE%" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to move/rename file.
    pause
    exit /b 1
)

:: 5b. Create Edge profile, inject Bookmarks, register in Local State, update Dashboard.py
set "SETUP_SCRIPT=%temp%\setup_edge_profile.py"

echo import sys, re, os, json > "%SETUP_SCRIPT%"
echo name = sys.argv[1] >> "%SETUP_SCRIPT%"
echo py_file = sys.argv[2] >> "%SETUP_SCRIPT%"
echo user_data_dir = os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Edge', 'User Data') >> "%SETUP_SCRIPT%"
echo local_state_path = os.path.join(user_data_dir, 'Local State') >> "%SETUP_SCRIPT%"
echo max_num = 0 >> "%SETUP_SCRIPT%"
echo for entry in os.listdir(user_data_dir): >> "%SETUP_SCRIPT%"
echo     m = re.match(r'^^Profile (\d+)$', entry) >> "%SETUP_SCRIPT%"
echo     if m: >> "%SETUP_SCRIPT%"
echo         n = int(m.group(1)) >> "%SETUP_SCRIPT%"
echo         if n ^> max_num: max_num = n >> "%SETUP_SCRIPT%"
echo new_num = max_num + 1 >> "%SETUP_SCRIPT%"
echo profile_dir_name = 'Profile ' + str(new_num) >> "%SETUP_SCRIPT%"
echo new_profile_path = os.path.join(user_data_dir, profile_dir_name) >> "%SETUP_SCRIPT%"
echo os.makedirs(new_profile_path, exist_ok=True) >> "%SETUP_SCRIPT%"
echo bm_child = {"date_added": "13250000000000000", "guid": "5d399380-6060-466d-9610-1c099309623e", "id": "5", "name": "Outlook", "type": "url", "url": "https://outlook.live.com/mail/0/"} >> "%SETUP_SCRIPT%"
echo bm_bar = {"children": [bm_child], "date_added": "13250000000000000", "date_modified": "13250000000000000", "id": "1", "name": "Favorites bar", "type": "folder"} >> "%SETUP_SCRIPT%"
echo bm_other = {"children": [], "id": "2", "name": "Other favorites", "type": "folder"} >> "%SETUP_SCRIPT%"
echo bm_synced = {"children": [], "id": "3", "name": "Mobile favorites", "type": "folder"} >> "%SETUP_SCRIPT%"
echo bookmarks = {"checksum": "", "roots": {"bookmark_bar": bm_bar, "other": bm_other, "synced": bm_synced}, "version": 1} >> "%SETUP_SCRIPT%"
echo with open(os.path.join(new_profile_path, 'Bookmarks'), 'w', encoding='utf-8') as f: json.dump(bookmarks, f, indent=3) >> "%SETUP_SCRIPT%"
echo with open(local_state_path, 'r', encoding='utf-8') as f: local_state = json.load(f) >> "%SETUP_SCRIPT%"
echo info_entry = {"name": name, "shortcut_name": "", "user_name": "", "managed_user_id": "", "is_omitted_from_profile_list": False} >> "%SETUP_SCRIPT%"
echo local_state.setdefault('profile', {}).setdefault('info_cache', {})[profile_dir_name] = info_entry >> "%SETUP_SCRIPT%"
echo profiles_order = local_state['profile'].setdefault('profiles_order', []) >> "%SETUP_SCRIPT%"
echo if profile_dir_name not in profiles_order: profiles_order.append(profile_dir_name) >> "%SETUP_SCRIPT%"
echo with open(local_state_path, 'w', encoding='utf-8') as f: json.dump(local_state, f, indent=3) >> "%SETUP_SCRIPT%"
echo with open(py_file, 'r', encoding='utf-8') as f: content = f.read() >> "%SETUP_SCRIPT%"
echo pattern = re.compile(r'(EDGE_PROFILES = \[.*?)\s*(\])', re.DOTALL) >> "%SETUP_SCRIPT%"
echo match = pattern.search(content) >> "%SETUP_SCRIPT%"
echo if match: >> "%SETUP_SCRIPT%"
echo     middle = match.group(1).rstrip() >> "%SETUP_SCRIPT%"
echo     if middle.endswith('}'): middle += ',' >> "%SETUP_SCRIPT%"
echo     cmd = '\\"C:\\\\Program Files (x86)\\\\Microsoft\\\\Edge\\\\Application\\\\msedge.exe\\" --profile-directory=\\"' + profile_dir_name + '\\"' >> "%SETUP_SCRIPT%"
echo     entry = '\n    {\n        "name": "' + name + '",\n        "command": "' + cmd + '"\n    }' >> "%SETUP_SCRIPT%"
echo     suffix = '\n]' >> "%SETUP_SCRIPT%"
echo     new_content = content[:match.start()] + middle + entry + suffix + content[match.end():] >> "%SETUP_SCRIPT%"
echo     with open(py_file, 'w', encoding='utf-8') as f: f.write(new_content) >> "%SETUP_SCRIPT%"
echo     print(profile_dir_name) >> "%SETUP_SCRIPT%"
echo else: >> "%SETUP_SCRIPT%"
echo     print("FAILED") >> "%SETUP_SCRIPT%"

python "%SETUP_SCRIPT%" "%PROFILE_NAME%" "%PY_FILE%" > "%temp%\setup_status.txt"
set /p PROFILE_DIR=<"%temp%\setup_status.txt"
del "%SETUP_SCRIPT%"

if "!PROFILE_DIR!"=="FAILED" (
    echo [ERROR] Failed to create Edge profile or update Dashboard.py.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo SUCCESS! 
echo Profile '%PROFILE_NAME%' (!PROFILE_DIR!) was added.
echo Image saved to: %TARGET_FILE%
echo Dashboard.py updated.
echo ==========================================================
echo.

:: 6. Launch Edge with the new profile
echo Launching new profile '%PROFILE_NAME%'...
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --profile-directory="!PROFILE_DIR!" --no-first-run

echo.
echo Finishing... closing in 3 seconds.
timeout /t 3 /nobreak > nul
exit