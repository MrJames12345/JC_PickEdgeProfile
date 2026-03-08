Option Explicit

' PickJcProject.vbs - Launches PickJcProject.py with hidden command window
' This script runs the Python script without showing a command prompt window

' Get the script directory
Dim fso, scriptDir, pythonScript
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonScript = scriptDir & "\PickJcProject.py"

' Check if the Python script exists
If Not fso.FileExists(pythonScript) Then
    WScript.Echo "Error: Could not find " & pythonScript
    WScript.Quit(1)
End If

' Create a shell object
Dim shell
Set shell = CreateObject("WScript.Shell")

' Run the Python script with hidden window
' 0 = Hide the window and activate another window
shell.Run "pythonw """ & pythonScript & """", 0, False

' Clean up
Set shell = Nothing
Set fso = Nothing
