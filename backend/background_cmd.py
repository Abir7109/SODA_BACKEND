"""
Background Command Execution Module
====================================
Hides console windows, retries with Gemini-generated alternatives,
and emits status events for frontend animation feedback.
"""

import os
import sys
import subprocess
import json
import asyncio
import time
from typing import Callable, Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ── Singleton Gemini client (lazy init from soda.py's AudioLoop) ──
_gemini_client = None

def set_gemini_client(client):
    global _gemini_client
    _gemini_client = client


def run_hidden_command(command: str, shell: bool = True, timeout: int = 30) -> dict:
    """
    Run a shell command with the console window completely hidden.
    Uses Windows STARTUPINFO with SW_HIDE.
    Returns {success, returncode, output, error}
    """
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    try:
        result = subprocess.run(
            command if shell else command.split(),
            shell=shell,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            timeout=timeout,
        )
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "output": output.strip(),
            "error": result.stderr.strip() if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "output": "", "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "returncode": -1, "output": "", "error": str(e)}


async def generate_alternatives(
    original_command: str,
    error_output: str,
    context: str = "",
    max_alternatives: int = 4,
) -> list:
    """
    Call Gemini to generate alternative commands that achieve the same intent.
    Returns a list of command strings, or empty list on failure.
    """
    if _gemini_client is None:
        return _static_alternatives(original_command)

    shell_hint = "PowerShell" if "powershell" in original_command.lower() or any(
        pw in original_command.lower() for pw in ["get-", "set-", "write-", "remove-"]
    ) else "CMD"

    prompt = (
        f"The following command was executed on Windows ({shell_hint}):\n"
        f"  {original_command}\n\n"
        f"It failed with this error:\n"
        f"  {error_output[:500]}\n\n"
        f"Context: {context[:300] if context else '(none)'}\n\n"
        f"Generate {max_alternatives} alternative commands that achieve the SAME INTENT "
        f"as the original command. The alternatives should use different approaches "
        f"(different flags, different tools, PowerShell vs CMD equivalents).\n\n"
        f"Return ONLY a JSON array of strings, each string being one command. "
        f"Example: ['dir C:\\\\', 'Get-ChildItem C:\\\\']\n"
        f"Do NOT include any explanation or markdown formatting."
    )

    try:
        response = _gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
        alternatives = json.loads(text)
        if isinstance(alternatives, list) and len(alternatives) > 0:
            return [str(cmd) for cmd in alternatives[:max_alternatives]]
    except Exception as e:
        print(f"[BackgroundCmd] Gemini alternative generation failed: {e}")

    return _static_alternatives(original_command)


def _static_alternatives(command: str) -> list:
    """Fallback: static mapping of common command equivalents."""
    cmd = command.strip().lower()
    alternatives = []

    # File listing
    if cmd in ("dir", "dir /w", "dir /b"):
        alternatives = ["Get-ChildItem", "cmd /c dir", "ls", "powershell Get-ChildItem"]
    elif "Get-ChildItem" in cmd or "gci" in cmd:
        alternatives = ["dir", "cmd /c dir", "ls"]
    elif cmd.startswith("ls"):
        alternatives = ["dir", "Get-ChildItem", "cmd /c dir"]

    # Network
    elif cmd in ("ipconfig", "ipconfig /all"):
        alternatives = ["Get-NetIPAddress", "netsh interface ip show config", "cmd /c ipconfig"]
    elif "Get-NetIPAddress" in cmd:
        alternatives = ["ipconfig", "cmd /c ipconfig", "netsh interface ip show config"]
    elif "ping" in cmd:
        base = cmd.replace("ping", "").strip()
        alternatives = [
            f"Test-Connection {base} -Count 4",
            f"cmd /c ping {base}",
            f"powershell Test-Connection {base} -Count 4",
        ]

    # Disk / storage
    elif "wmic" in cmd and "disk" in cmd:
        alternatives = [
            "powershell Get-PSDrive -PSProvider FileSystem",
            "fsutil volume diskfree C:",
            "cmd /c wmic logicaldisk get size,freespace,caption",
        ]
    elif "Get-PSDrive" in cmd:
        alternatives = [
            "wmic logicaldisk get size,freespace,caption",
            "cmd /c wmic logicaldisk get size,freespace,caption",
            "fsutil volume diskfree C:",
        ]
    elif "chkdsk" in cmd:
        alternatives = ["fsutil dirty query C:", "cmd /c chkdsk", "powershell Repair-Volume -DriveLetter C"]

    # System info
    elif cmd in ("systeminfo", "systeminfo | more"):
        alternatives = ["Get-ComputerInfo", "cmd /c systeminfo", "powershell Get-ComputerInfo"]
    elif "Get-ComputerInfo" in cmd:
        alternatives = ["systeminfo", "cmd /c systeminfo"]
    elif "tasklist" in cmd:
        alternatives = ["Get-Process | Format-Table", "cmd /c tasklist", "powershell Get-Process"]
    elif "Get-Process" in cmd:
        alternatives = ["tasklist", "cmd /c tasklist"]

    # Process kill
    elif "taskkill" in cmd or "kill" in cmd:
        alternatives = [
            cmd.replace("taskkill", "Stop-Process").replace("kill", "Stop-Process"),
            f"powershell {cmd.replace('taskkill', 'Stop-Process').replace('/F', '-Force')}",
        ]

    # Date / time
    elif cmd in ("time", "date", "time /t", "date /t"):
        alternatives = ["Get-Date", "cmd /c time /t", "powershell Get-Date"]
    elif "Get-Date" in cmd:
        alternatives = ["time /t", "cmd /c time /t"]

    # General fallback: try the same command in the other shell
    if not alternatives:
        if "powershell" in cmd:
            pw_clean = cmd.replace("powershell ", "").replace("powershell.exe ", "")
            alternatives = [f"cmd /c {pw_clean}"]
        else:
            alternatives = [f"powershell {cmd}", f"cmd /c {cmd}"]

    return alternatives


async def execute_with_retry(
    command: str,
    context: str = "",
    max_attempts: int = 5,
    timeout: int = 30,
    use_powershell: bool = False,
    emit_status: Optional[Callable] = None,
) -> dict:
    """
    Execute a command with hidden window and intelligent retries.
    
    1. Tries the original command first (hidden, no popup).
    2. If it fails, generates alternative commands via Gemini (or static fallback).
    3. Tries each alternative until one succeeds or max_attempts exhausted.
    4. Calls emit_status callback after each attempt for frontend animation.
    
    Args:
        command: The command to execute
        context: Description of what the command is trying to do
        max_attempts: Maximum attempts (original + alternatives)
        timeout: Per-command timeout in seconds
        use_powershell: Whether to prefer PowerShell
        emit_status: Async callback(status_dict) for frontend updates
    
    Returns:
        dict with {success, output, returncode, attempts, error}
    """
    if emit_status is None:
        async def _noop(_d):
            pass
        emit_status = _noop

    attempts = []
    shell = use_powershell

    # Determine shell hint
    shell_name = "PowerShell" if use_powershell else "CMD"
    cmd_lower = command.lower()

    # Phase: THINKING
    await emit_status({
        "phase": "thinking",
        "attempt": 0,
        "total": 1,
        "command": command,
        "output": "",
        "error": "",
    })
    await asyncio.sleep(0.5)

    # Collect commands to try (start with original)
    commands_to_try = [command]
    errors_so_far = ""

    for attempt_num in range(1, max_attempts + 1):
        if attempt_num > len(commands_to_try):
            # Generate alternatives if we haven't yet
            if attempt_num == 2:
                await emit_status({
                    "phase": "thinking",
                    "attempt": attempt_num,
                    "total": max_attempts,
                    "command": f"Analyzing failure, generating alternatives...",
                    "output": errors_so_far[:200],
                    "error": "",
                })
                alternatives = await generate_alternatives(
                    command, errors_so_far, context, max_alternatives=max_attempts - 1
                )
                # Filter out already-tried commands
                tried_set = set(c.strip().lower() for c in commands_to_try)
                for alt in alternatives:
                    if alt.strip().lower() not in tried_set:
                        commands_to_try.append(alt)
                        tried_set.add(alt.strip().lower())

                if len(commands_to_try) <= 1:
                    commands_to_try.append(command)  # fallback: retry original

            if attempt_num > len(commands_to_try):
                # No more alternatives — stop
                break

        current_cmd = commands_to_try[attempt_num - 1]

        # Phase: RETRYING or RUNNING
        await emit_status({
            "phase": "retrying" if attempt_num > 1 else "running",
            "attempt": attempt_num,
            "total": max_attempts,
            "command": current_cmd,
            "output": "",
            "error": errors_so_far[:200] if errors_so_far else "",
        })

        # Determine shell for this specific command
        cmd_shell = shell
        if current_cmd.lower().startswith("powershell") or "powershell" in current_cmd.lower():
            cmd_shell = True

        try:
            result = run_hidden_command(current_cmd, timeout=timeout)
        except Exception as e:
            result = {"success": False, "returncode": -1, "output": "", "error": str(e)}

        attempt_info = {
            "command": current_cmd,
            "success": result["success"],
            "returncode": result["returncode"],
            "output": result["output"][:1000],
            "error": result["error"][:500],
        }
        attempts.append(attempt_info)

        if result["success"]:
            # Phase: DONE
            await emit_status({
                "phase": "done",
                "attempt": attempt_num,
                "total": len(commands_to_try),
                "command": current_cmd,
                "output": result["output"][:1000],
                "error": "",
                "success": True,
            })
            return {
                "success": True,
                "output": result["output"],
                "returncode": result["returncode"],
                "attempts": attempts,
                "total_attempts": attempt_num,
                "error": "",
            }

        errors_so_far = result["error"] or result["output"][:300]

    # All attempts failed
    last_output = attempts[-1]["output"] if attempts else ""
    last_error = attempts[-1]["error"] if attempts else "Command failed"
    await emit_status({
        "phase": "failed",
        "attempt": len(attempts),
        "total": len(commands_to_try),
        "command": commands_to_try[-1] if commands_to_try else command,
        "output": last_output,
        "error": last_error,
        "success": False,
    })

    return {
        "success": False,
        "output": last_output,
        "returncode": -1,
        "attempts": attempts,
        "total_attempts": len(attempts),
        "error": f"All {len(attempts)} attempts failed. Last error: {last_error[:300]}",
    }
