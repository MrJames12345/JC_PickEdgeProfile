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

:: 2. Prompt for Profile Number
:PROMPT_NUMBER
set "PROFILE_NUMBER="
set /p PROFILE_NUMBER="Enter Profile Number (e.g. 7): "
if "%PROFILE_NUMBER%"=="" goto PROMPT_NUMBER

:: Check if number exists in Dashboard.py
python -c "import sys; p=r'%PY_FILE%'; c=open(p).read(); print('EXISTS' if f'Profile {sys.argv[1]}' in c else 'OK')" "%PROFILE_NUMBER%" > "%temp%\check_num.txt"
set /p NUM_STATUS=<"%temp%\check_num.txt"
if "!NUM_STATUS!"=="EXISTS" (
    echo [ERROR] Profile Number '%PROFILE_NUMBER%' already exists in Dashboard.py.
    goto PROMPT_NUMBER
)

:: 3. Prompt for Profile Name
:PROMPT_NAME
set "PROFILE_NAME="
set /p PROFILE_NAME="Enter Profile Name (e.g. StickerBoys): "
if "%PROFILE_NAME%"=="" goto PROMPT_NAME

:: Check if name exists in Dashboard.py
python -c "import sys; p=r'%PY_FILE%'; c=open(p).read(); print('EXISTS' if f'\"name\": \"{sys.argv[1]}\"' in c else 'OK')" "%PROFILE_NAME%" > "%temp%\check_name.txt"
set /p NAME_STATUS=<"%temp%\check_name.txt"
if "!NAME_STATUS!"=="EXISTS" (
    echo [ERROR] Profile Name '%PROFILE_NAME%' already exists in Dashboard.py.
    goto PROMPT_NAME
)

:: 4. Final Verification
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

:: 6. Update Dashboard.py
echo Updating Dashboard.py...

set "UPDATE_SCRIPT=%temp%\update_pep_script.py"

:: Write the python script line by line WITHOUT the ( ) block to avoid escaping hell
echo import sys, re > "%UPDATE_SCRIPT%"
echo p = r'%PY_FILE%' >> "%UPDATE_SCRIPT%"
echo name = sys.argv[1] >> "%UPDATE_SCRIPT%"
echo num = sys.argv[2] >> "%UPDATE_SCRIPT%"
echo with open(p, 'r', encoding='utf-8') as f: content = f.read() >> "%UPDATE_SCRIPT%"
echo pattern = re.compile(r'(EDGE_PROFILES = \[.*?)\s*(\])', re.DOTALL) >> "%UPDATE_SCRIPT%"
echo match = pattern.search(content) >> "%UPDATE_SCRIPT%"
echo if match: >> "%UPDATE_SCRIPT%"
echo     middle = match.group(1).rstrip() >> "%UPDATE_SCRIPT%"
echo     if middle.endswith('}'): middle += ',' >> "%UPDATE_SCRIPT%"
echo     entry = '\n    {\n        "name": "' + name + '",\n        "command": "\\"C:\\\\Program Files (x86)\\\\Microsoft\\\\Edge\\\\Application\\\\msedge.exe\\" --profile-directory=\\"Profile ' + num + '\\""\n    }' >> "%UPDATE_SCRIPT%"
echo     suffix = '\n]' >> "%UPDATE_SCRIPT%"
echo     new_content = content[:match.start()] + middle + entry + suffix + content[match.end():] >> "%UPDATE_SCRIPT%"
echo     with open(p, 'w', encoding='utf-8') as f: f.write(new_content) >> "%UPDATE_SCRIPT%"
echo     print("SUCCESS") >> "%UPDATE_SCRIPT%"
echo else: >> "%UPDATE_SCRIPT%"
echo     print("FAILED") >> "%UPDATE_SCRIPT%"

python "%UPDATE_SCRIPT%" "%PROFILE_NAME%" "%PROFILE_NUMBER%" > "%temp%\update_status.txt"
set /p UPDATE_STATUS=<"%temp%\update_status.txt"
del "%UPDATE_SCRIPT%"

if "!UPDATE_STATUS!"=="FAILED" (
    echo [ERROR] Failed to update EDGE_PROFILES in Dashboard.py. 
    echo Please check the file format.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo SUCCESS! 
echo Profile '%PROFILE_NAME%' (Number %PROFILE_NUMBER%) was added.
echo Image saved to: %TARGET_FILE%
echo Dashboard.py updated and formatted.
echo ==========================================================
echo.

echo.
echo Finishing... closing in 3 seconds.
timeout /t 3 /nobreak > nul
exit