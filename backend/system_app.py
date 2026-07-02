import os
import sys
import subprocess
import shutil
import time
import platform
import json
import re
import asyncio
from pathlib import Path
from urllib.parse import quote_plus

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.06
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

_SYSTEM = platform.system()

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"

# ============ TERMINAL EXECUTE (Phase 2 T-01) ============

DESTRUCTIVE_PATTERNS = ["rm -rf", "del /f", "format ", "shutdown", "mkfs", "dd if"]


async def _run_terminal_command_unchecked(command: str, timeout: int = 30) -> dict:
    """Run a shell command without destructive-pattern check. Use after user confirmation.
    Uses hidden window on Windows to prevent popups."""
    kwargs = {
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.STDOUT,
        "shell": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        # Hide console window on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startupinfo
    proc = None
    try:
        proc = await asyncio.create_subprocess_shell(command, **kwargs)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace")
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "output": output[:4000],
        }
    except asyncio.TimeoutError:
        if proc is not None and proc.returncode is None:
            await _kill_process_tree(proc)
        return {"success": False, "returncode": -1, "output": f"Command timed out after {timeout}s"}
    except Exception as e:
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
            except Exception:
                pass
        return {"success": False, "returncode": -1, "output": str(e)}


async def _kill_process_tree(proc: asyncio.subprocess.Process) -> None:
    """Kill a process and all its children. On Windows, uses taskkill /T /F."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True, timeout=5
            )
        except Exception:
            pass
    else:
        try:
            proc.kill()
        except Exception:
            pass


async def run_terminal_command(command: str, timeout: int = 30) -> dict:
    """
    Run a shell command, capture stdout+stderr, return as dict.
    Raises ValueError if command contains a destructive pattern (caller handles confirmation).
    """
    cmd_lower = (command or "").lower()
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in cmd_lower:
            raise ValueError(f"Destructive command detected: {pattern}")
    return await _run_terminal_command_unchecked(command, timeout)

_YT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_APP_ALIASES = {
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "google chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "firefox": {"Windows": "firefox", "Darwin": "Firefox", "Linux": "firefox"},
    "edge": {"Windows": "msedge", "Darwin": "Microsoft Edge", "Linux": "microsoft-edge"},
    "brave": {"Windows": "brave", "Darwin": "Brave Browser", "Linux": "brave-browser"},
    "safari": {"Windows": "msedge", "Darwin": "Safari", "Linux": "firefox"},
    "opera": {"Windows": "opera", "Darwin": "Opera", "Linux": "opera"},
    "whatsapp": {"Windows": "WhatsApp", "Darwin": "WhatsApp", "Linux": "whatsapp"},
    "telegram": {"Windows": "Telegram", "Darwin": "Telegram", "Linux": "telegram"},
    "discord": {"Windows": "Discord", "Darwin": "Discord", "Linux": "discord"},
    "slack": {"Windows": "Slack", "Darwin": "Slack", "Linux": "slack"},
    "zoom": {"Windows": "Zoom", "Darwin": "zoom.us", "Linux": "zoom"},
    "teams": {"Windows": "msteams", "Darwin": "Microsoft Teams", "Linux": "teams"},
    "skype": {"Windows": "skype", "Darwin": "Skype", "Linux": "skype"},
    "signal": {"Windows": "signal", "Darwin": "Signal", "Linux": "signal"},
    "vlc": {"Windows": "vlc", "Darwin": "VLC", "Linux": "vlc"},
    "netflix": {"Windows": "Netflix", "Darwin": "Netflix", "Linux": "firefox"},
    "vscode": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "visual studio code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "terminal": {"Windows": "wt", "Darwin": "Terminal", "Linux": "gnome-terminal"},
    "cmd": {"Windows": "cmd.exe", "Darwin": "Terminal", "Linux": "bash"},
    "powershell": {"Windows": "powershell.exe", "Darwin": "Terminal", "Linux": "bash"},
    "postman": {"Windows": "Postman", "Darwin": "Postman", "Linux": "postman"},
    "git": {"Windows": "git-bash", "Darwin": "Terminal", "Linux": "bash"},
    "figma": {"Windows": "Figma", "Darwin": "Figma", "Linux": "figma"},
    "blender": {"Windows": "blender", "Darwin": "Blender", "Linux": "blender"},
    "word": {"Windows": "winword", "Darwin": "Microsoft Word", "Linux": "libreoffice --writer"},
    "excel": {"Windows": "excel", "Darwin": "Microsoft Excel", "Linux": "libreoffice --calc"},
    "powerpoint": {"Windows": "powerpnt", "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "libreoffice": {"Windows": "soffice", "Darwin": "LibreOffice", "Linux": "libreoffice"},
    "notepad": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
    "textedit": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
    "explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "file explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "finder": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "task manager": {"Windows": "taskmgr.exe", "Darwin": "Activity Monitor", "Linux": "gnome-system-monitor"},
    "settings": {"Windows": "ms-settings:", "Darwin": "System Preferences", "Linux": "gnome-control-center"},
    "calculator": {"Windows": "calc.exe", "Darwin": "Calculator", "Linux": "gnome-calculator"},
    "paint": {"Windows": "mspaint.exe", "Darwin": "Preview", "Linux": "gimp"},
    "instagram": {"Windows": "Instagram", "Darwin": "Instagram", "Linux": "firefox"},
    "tiktok": {"Windows": "TikTok", "Darwin": "TikTok", "Linux": "firefox"},
    "notion": {"Windows": "Notion", "Darwin": "Notion", "Linux": "notion"},
    "obsidian": {"Windows": "Obsidian", "Darwin": "Obsidian", "Linux": "obsidian"},
    "capcut": {"Windows": "CapCut", "Darwin": "CapCut", "Linux": "capcut"},
    "steam": {"Windows": "steam", "Darwin": "Steam", "Linux": "steam"},
    "epic": {"Windows": "EpicGamesLauncher", "Darwin": "Epic Games Launcher", "Linux": "legendary"},
    "epic games": {"Windows": "EpicGamesLauncher", "Darwin": "Epic Games Launcher", "Linux": "legendary"},
}

_APP_URIS = {
    "whatsapp": "whatsapp://",
    "telegram": "tg://",
    "discord": "discord://",
    "zoom": "zoommtg://",
    "teams": "msteams://",
    "skype": "skype://",
    "signal": "signal://",
}

_APP_PATHS = {
    "WhatsApp": [("LOCALAPPDATA", "WhatsApp\\WhatsApp.exe")],
    "Telegram": [("LOCALAPPDATA", "Telegram Desktop\\Telegram.exe")],
    "Discord": [("LOCALAPPDATA", "Discord\\Update.exe")],
    "Zoom": [("APPDATA", "Zoom\\bin\\Zoom.exe")],
    "Slack": [("LOCALAPPDATA", "slack\\slack.exe")],
    "Signal": [("LOCALAPPDATA", "Signal\\signal.exe")],
    "Postman": [("LOCALAPPDATA", "Postman\\Postman.exe")],
    "Notion": [("LOCALAPPDATA", "Notion\\Notion.exe")],
    "Obsidian": [("LOCALAPPDATA", "Obsidian\\Obsidian.exe")],
    "Figma": [("LOCALAPPDATA", "Figma\\Figma.exe")],
    "Blender": [("LOCALAPPDATA", "Blender Foundation\\Blender\\blender.exe")],
    "CapCut": [("LOCALAPPDATA", "CapCut\\CapCut.exe")],
    "Steam": [("PROGRAMFILES(X86)", "Steam\\steam.exe")],
    "EpicGamesLauncher": [("PROGRAMFILES(X86)", "Epic Games\\Launcher\\Portal\\Binaries\\Win64\\EpicGamesLauncher.exe")],
}

def _get_default_browser():
    if _SYSTEM == "Windows":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice")
            prog_id = winreg.QueryValueEx(k, "ProgId")[0].lower()
            winreg.CloseKey(k)
            for b in ("edge", "chrome", "firefox", "opera", "brave"):
                if b in prog_id:
                    return b
        except:
            pass
    return "chrome"

def open_app(app_name):
    if not app_name:
        return "No application name provided."
    
    app_key = app_name.lower().strip()
    normalized = _APP_ALIASES.get(app_key, {}).get(_SYSTEM, app_name)
    
    print(f"[OpenApp] Launching: {app_name} -> {normalized} ({_SYSTEM})")
    
    if _SYSTEM == "Windows":
        return _open_windows(normalized, app_name)
    elif _SYSTEM == "Darwin":
        return _open_macos(normalized, app_name)
    else:
        return _open_linux(normalized, app_name)

def _open_windows(app_name, original_name):
    if shutil.which(app_name) or shutil.which(app_name.split(".")[0]):
        try:
            subprocess.Popen(app_name, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opened {original_name}."
        except Exception as e:
            print(f"[OpenApp] subprocess failed: {e}")

    if ":" in app_name:
        try:
            subprocess.Popen(f"start {app_name}", shell=True)
            return f"Opened {original_name}."
        except:
            pass
    
    if app_name.lower() in ("chrome", "firefox", "edge", "brave", "opera"):
        browser_path = shutil.which(app_name)
        if browser_path:
            try:
                subprocess.Popen(f'"{browser_path}"', shell=True)
                return f"Opened {original_name}."
            except:
                pass

    if _PYAUTOGUI:
        try:
            pyautogui.PAUSE = 0.1
            pyautogui.press("win")
            time.sleep(0.7)
            pyautogui.write(app_name, interval=0.05)
            time.sleep(0.9)
            pyautogui.press("enter")
            return f"Opened {original_name} via Start Menu."
        except Exception as e:
            print(f"[OpenApp] Start Menu failed: {e}")

    return f"Could not open {original_name}. It may not be installed."

def _open_macos(app_name, original_name):
    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return f"Opened {original_name}."
    except:
        pass
    
    try:
        result = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return f"Opened {original_name}."
    except:
        pass
    
    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return f"Opened {original_name}."
        except:
            pass
    
    return f"Could not open {original_name}. It may not be installed."

def _open_linux(app_name, original_name):
    binary = shutil.which(app_name) or shutil.which(app_name.lower()) or shutil.which(app_name.lower().replace(" ", "-"))
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return f"Opened {original_name}."
        except:
            pass
    
    try:
        subprocess.run(["xdg-open", app_name], capture_output=True, timeout=5)
        return f"Opened {original_name}."
    except:
        pass
    
    return f"Could not open {original_name}."

def open_url(url, browser=None):
    if not url:
        return "No URL provided."
    
    if not url.startswith("http"):
        url = "https://" + url
    
    target_browser = browser.lower() if browser else _get_default_browser()
    
    print(f"[OpenURL] Opening {url} in {target_browser}")
    
    if _SYSTEM == "Windows":
        browser_exe = shutil.which(target_browser) or shutil.which(f"{target_browser}.exe")
        if not browser_exe:
            for b in ("chrome", "msedge", "firefox", "brave", "opera"):
                browser_exe = shutil.which(b)
                if browser_exe:
                    break
        
        if browser_exe:
            try:
                subprocess.Popen(f'"{browser_exe}" {url}', shell=True, 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Opened {url} in {target_browser}."
            except Exception as e:
                print(f"[OpenURL] Error: {e}")
        
        try:
            subprocess.Popen(f"start {url}", shell=True)
            return f"Opened {url} in default browser."
        except:
            pass
    
    elif _SYSTEM == "Darwin":
        try:
            subprocess.Popen(["open", "-a", target_browser, url])
            return f"Opened {url} in {target_browser}."
        except:
            pass
    
    try:
        subprocess.Popen(["xdg-open", url])
        return f"Opened {url}."
    except:
        pass
    
    return f"Could not open {url}."

KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "youtube music": "https://music.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "instagram": "https://www.instagram.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://en.wikipedia.org",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "discord": "https://discord.com",
    "slack": "https://slack.com",
    "twitch": "https://www.twitch.tv",
    "maps": "https://www.google.com/maps",
    "drive": "https://drive.google.com",
    "docs": "https://docs.google.com",
    "sheets": "https://docs.google.com/spreadsheets",
    "cloudsim": "https://cloudsim.io",
}

SITE_SEARCH_URLS = {
    "youtube": "https://www.youtube.com/results?search_query=",
    "google": "https://www.google.com/search?q=",
    "bing": "https://www.bing.com/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "reddit": "https://www.reddit.com/search/?q=",
    "github": "https://github.com/search?q=",
    "stackoverflow": "https://stackoverflow.com/search?q=",
    "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search=",
    "amazon": "https://www.amazon.com/s?k=",
    "twitter": "https://twitter.com/search?q=",
    "x": "https://x.com/search?q=",
}

SITE_KEYWORDS = {
    "youtube": ["youtube", "yt"],
    "google": ["google", "goog"],
    "facebook": ["facebook", "fb"],
    "twitter": ["twitter", "x.com"],
    "instagram": ["instagram", "insta"],
    "reddit": ["reddit", "redd"],
    "linkedin": ["linkedin"],
    "github": ["github", "gh"],
    "stackoverflow": ["stackoverflow", "stack overflow", "so"],
    "wikipedia": ["wikipedia", "wiki"],
    "amazon": ["amazon", "amzn"],
    "netflix": ["netflix", "nflx"],
    "whatsapp": ["whatsapp", "wa"],
    "telegram": ["telegram", "tg"],
    "discord": ["discord", "dc"],
    "twitch": ["twitch"],
}

def extract_site_and_search(query):
    query_lower = query.lower().strip()
    
    for site_name, search_url_base in SITE_SEARCH_URLS.items():
        keywords = SITE_KEYWORDS.get(site_name, [site_name])
        
        for kw in keywords:
            if query_lower.startswith(kw + " ") or query_lower.startswith(kw + " in ") or query_lower.startswith(kw + " on "):
                search_term = query
                for prefix in [kw + " ", kw + " in ", kw + " on "]:
                    if query_lower.startswith(prefix):
                        search_term = query[len(prefix):].strip()
                        break
                if search_term:
                    return search_url_base + search_term.replace(" ", "+"), True
    
    for site_name, url in KNOWN_SITES.items():
        keywords = SITE_KEYWORDS.get(site_name, [site_name])
        for kw in keywords:
            if query_lower == kw or query_lower.startswith(kw + " "):
                return url, True
    
    return None, False

def search_web(query, engine="google", browser=None):
    if not query:
        return "No search query provided."
    
    query_lower = query.lower().strip()
    
    if query_lower.startswith("http://") or query_lower.startswith("https://"):
        return open_url(query, browser)
    
    url, found_site = extract_site_and_search(query)
    if found_site:
        return open_url(url, browser)
    
    engines = {
        "google": "https://www.google.com/search?q=",
        "bing": "https://www.bing.com/search?q=",
        "duckduckgo": "https://duckduckgo.com/?q=",
        "yandex": "https://yandex.com/search/?text=",
    }
    
    base_url = engines.get(engine.lower(), engines["google"])
    url = base_url + query.replace(" ", "+")
    
    return open_url(url, browser)

def _scrape_youtube_video(query):
    if not _REQUESTS_OK:
        return None
    
    search_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    
    try:
        r = requests.get(search_url, headers=_YT_HEADERS, timeout=10)
        html = r.text
        
        video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
        
        seen = set()
        for vid in video_ids:
            if vid in seen:
                continue
            seen.add(vid)
            
            if f'/shorts/{vid}' in html:
                continue
            return f"https://www.youtube.com/watch?v={vid}"
    
    except Exception as e:
        print(f"[YouTube] scrape failed: {e}")
    
    return None

def search_youtube(query, browser=None):
    if not query:
        return "No search query provided."
    
    query_lower = query.lower().strip()
    
    if "youtube" in query_lower:
        search_term = query_lower.replace("youtube", "").strip()
        if search_term:
            query = search_term
    
    video_url = _scrape_youtube_video(query)
    
    if video_url:
        print(f"[YouTube] Playing: {video_url}")
        return open_url(video_url, browser)
    
    fallback_url = (
        f"https://www.youtube.com/results"
        f"?search_query={quote_plus(query)}"
        f"&sp={_YT_VIDEO_FILTER}"
    )
    print(f"[YouTube] Fallback to search page")
    return open_url(fallback_url, browser)

def _paste_text(text):
    if not _PYAUTOGUI:
        return False
    try:
        if _PYPERCLIP:
            pyperclip.copy(text)
            time.sleep(0.15)
            paste_hotkey = ("command", "v") if _SYSTEM == "Darwin" else ("ctrl", "v")
            pyautogui.hotkey(*paste_hotkey)
        else:
            pyautogui.write(text, interval=0.03)
        time.sleep(0.1)
        return True
    except Exception as e:
        print(f"[_paste_text] Failed: {e}")
        return False

def _search_in_app(query):
    if not _PYAUTOGUI:
        return
    try:
        search_hotkey = ("command", "f") if _SYSTEM == "Darwin" else ("ctrl", "f")
        pyautogui.hotkey(*search_hotkey)
        time.sleep(0.5)
        _paste_text(query)
        time.sleep(1.0)
    except Exception as e:
        print(f"[_search_in_app] Failed: {e}")

def _open_app_desktop(app_name):
    if not _PYAUTOGUI:
        return False
    try:
        if _SYSTEM == "Windows":
            pyautogui.press("win")
            time.sleep(0.5)
            _paste_text(app_name)
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(2.5)
            return True
        elif _SYSTEM == "Darwin":
            result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=10)
            if result.returncode != 0:
                result = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=10)
            time.sleep(2.5)
            return result.returncode == 0
        else:
            for launcher in [["gtk-launch", app_name.lower()], [app_name.lower()]]:
                try:
                    subprocess.Popen(launcher, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(2.5)
                    return True
                except FileNotFoundError:
                    continue
            return False
    except Exception as e:
        print(f"[_open_app_desktop] Failed to open {app_name}: {e}")
        return False

def send_whatsapp(contact, message, browser=None):
    if not message:
        return "No message provided."
    
    if not _PYAUTOGUI:
        return "PyAutoGUI not installed. Cannot control desktop apps."
    
    contact_clean = contact.strip() if contact else ""
    message_clean = message.strip()
    
    print(f"[send_whatsapp] Opening WhatsApp to send to: {contact_clean}, message: {message_clean[:30]}...")
    
    if not _open_app_desktop("WhatsApp"):
        phone = ""
        if contact_clean:
            phone = ''.join(c for c in contact_clean if c.isdigit() or c == '+')
            if phone.startswith('+'):
                phone = phone[1:]
        
        encoded_msg = message.replace(" ", "%20").replace("\n", "%0A")
        
        if phone:
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
        else:
            url = "https://web.whatsapp.com"
        
        return open_url(url, browser)
    
    time.sleep(1.0)
    _search_in_app(contact_clean)
    pyautogui.press("enter")
    time.sleep(0.8)
    
    _paste_text(message_clean)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)
    
    return f"Message sent to {contact_clean} via WhatsApp."

def send_telegram(contact, message, browser=None):
    if not message:
        return "No message provided."
    
    if not _PYAUTOGUI:
        return "PyAutoGUI not installed. Cannot control desktop apps."
    
    contact_clean = contact.strip() if contact else ""
    message_clean = message.strip()
    
    print(f"[send_telegram] Opening Telegram to send to: {contact_clean}, message: {message_clean[:30]}...")
    
    if not _open_app_desktop("Telegram"):
        return "Could not open Telegram desktop app."
    
    time.sleep(1.0)
    _search_in_app(contact_clean)
    pyautogui.press("enter")
    time.sleep(0.8)
    
    _paste_text(message_clean)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)
    
    return f"Message sent to {contact_clean} via Telegram."

def send_discord(contact, message, browser=None):
    if not message:
        return "No message provided."
    
    if not _PYAUTOGUI:
        return "PyAutoGUI not installed. Cannot control desktop apps."
    
    contact_clean = contact.strip() if contact else ""
    message_clean = message.strip()
    
    print(f"[send_discord] Opening Discord to send to: {contact_clean}, message: {message_clean[:30]}...")
    
    if not _open_app_desktop("Discord"):
        return "Could not open Discord desktop app."
    
    time.sleep(1.0)
    _search_in_app(contact_clean)
    pyautogui.press("enter")
    time.sleep(0.8)
    
    _paste_text(message_clean)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)
    
    return f"Message sent to {contact_clean} via Discord."