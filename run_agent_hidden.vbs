' SODA Local Agent - Hidden launcher (no console window) with auto-restart watchdog
' Uses the VBS script's own location to find local_agent.py
' Restarts the agent if it dies (killed, crashed, or PC wakes from sleep)

Dim fso, scriptDir, scriptPath
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetFile(WScript.ScriptFullName).ParentFolder.Path
scriptPath = scriptDir & "\backend\local_agent.py"

Do While True
    ' No BACKEND_URL pin: agent uses its default (Render) so it meets the Netlify HUD on the same server
    CreateObject("WScript.Shell").Run "cmd /c py -3.11 """ & scriptPath & """, 0, True"
    WScript.Sleep 5000
Loop
