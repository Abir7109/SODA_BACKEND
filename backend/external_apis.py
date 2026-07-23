import httpx
import asyncio
import os
import platform
import shutil
import subprocess
from datetime import datetime

# ============ EXTERNAL API TOOLS FOR SODA ============

# 0. System Status (psutil-free fallback)
async def get_system_status():
    """Get current CPU, RAM, disk and battery info using stdlib only."""
    def collect():
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "hostname": platform.node(),
        }

        try:
            import os
            cpu_count = os.cpu_count()
            info["cpu_count"] = cpu_count

            loadavg = None
            if hasattr(os, "getloadavg"):
                try:
                    loadavg = os.getloadavg()
                except OSError:
                    pass
            if loadavg is not None:
                info["cpu_load_1m"] = round(loadavg[0], 2)
                info["cpu_load_5m"] = round(loadavg[1], 2)
                info["cpu_load_15m"] = round(loadavg[2], 2)
        except Exception as e:
            info["cpu_error"] = str(e)

        try:
            import psutil  # type: ignore
            vm = psutil.virtual_memory()
            info["ram_total_gb"] = round(vm.total / (1024 ** 3), 2)
            info["ram_used_gb"] = round(vm.used / (1024 ** 3), 2)
            info["ram_percent"] = vm.percent
            disk = psutil.disk_usage("/")
            info["disk_total_gb"] = round(disk.total / (1024 ** 3), 2)
            info["disk_used_gb"] = round(disk.used / (1024 ** 3), 2)
            info["disk_percent"] = disk.percent
            info["cpu_percent"] = psutil.cpu_percent(interval=None)
            battery = psutil.sensors_battery()
            if battery is not None:
                info["battery_percent"] = battery.percent
                info["battery_charging"] = battery.power_plugged
        except ImportError:
            # ponytail: fallback CPU% from loadavg (Linux-only)
            if info.get("cpu_load_1m") is not None and info.get("cpu_count"):
                info["cpu_percent"] = round((info["cpu_load_1m"] / info["cpu_count"]) * 100, 1)
            info["ram_percent"] = 0
        except Exception as e:
            info["metrics_error"] = str(e)

        return info

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, collect)

# 1. Weather API - Open-Meteo (FREE, no API key)
# Docs: https://open-meteo.com/en/docs
async def get_weather(location: str, units: str = "celsius"):
    """
    Get current weather for a location using Open-Meteo API.
    Location format: 'latitude,longitude' or city name lookup.
    """
    # First, geocode the location
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&format=json&language=en"
    
    try:
        async with httpx.AsyncClient() as client:
            # Geocode
            geo_resp = await client.get(geo_url, timeout=10.0)
            geo_data = geo_resp.json()
            
            if not geo_data.get('results'):
                return {"error": f"Location not found: {location}"}
            
            lat = geo_data['results'][0]['latitude']
            lon = geo_data['results'][0]['longitude']
            name = geo_data['results'][0]['name']
            
            # Get weather
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,snowfall,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m&timezone=auto"
            
            weather_resp = await client.get(weather_url, timeout=10.0)
            weather_data = weather_resp.json()
            
            current = weather_data.get('current', {})
            
            return {
                "location": name,
                "temperature": current.get('temperature_2m'),
                "feels_like": current.get('apparent_temperature'),
                "humidity": current.get('relative_humidity_2m'),
                "wind_speed": current.get('wind_speed_10m'),
                "wind_direction": current.get('wind_direction_10m'),
                "weather_code": current.get('weather_code'),
                "is_day": current.get('is_day', 1) == 1,
                "precipitation": current.get('precipitation'),
                "cloud_cover": current.get('cloud_cover')
            }
    except Exception as e:
        return {"error": str(e)}

# 2. IP Geolocation - IPStack (needs API key, but free tier)
async def get_ip_info(ip: str = ""):
    """
    Get IP geolocation info. If no IP provided, returns info for current IP.
    Get free API key: https://ipstack.com/
    """
    # IPStack free tier - use their fallback or just use ipapi
    url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,query,isp,org,as"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            data = resp.json()
            
            if data.get('status') == 'fail':
                return {"error": "IP not found"}
            
            return {
                "ip": data.get('query'),
                "country": data.get('country'),
                "region": data.get('regionName'),
                "city": data.get('city'),
                "latitude": data.get('lat'),
                "longitude": data.get('lon'),
                "isp": data.get('isp'),
                "org": data.get('org')
            }
    except Exception as e:
        return {"error": str(e)}

# 3. Exchange Rates - ExchangeRate.Host (FREE)
async def get_exchange_rate(from_curr: str, to_curr: str):
    """
    Get exchange rate between two currencies.
    Codes: USD, EUR, GBP, JPY, BDT, INR, etc.
    """
    url = f"https://api.exchangerate.host/latest?base={from_curr.upper()}&symbols={to_curr.upper()}"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            data = resp.json()
            
            if not data.get('success'):
                return {"error": data.get('error', 'Failed to get rates')}
            
            rate = data['rates'].get(to_curr.upper())
            return {
                "from": from_curr.upper(),
                "to": to_curr.upper(),
                "rate": rate,
                "date": data.get('date')
            }
    except Exception as e:
        return {"error": str(e)}




# 4b. Bangladeshi News - BBC Bengali (via news-api-fs)
BANGLADESHI_NEWS_BASE = "https://news-api-fs.vercel.app/api"

async def get_bangladeshi_news(category: str = "main"):
    """
    Fetch latest Bangladeshi news from BBC Bengali via news-api-fs.
    Categories: main, politics, world, economics, health, sports, technology, bangladesh, india
    """
    try:
        url = f"{BANGLADESHI_NEWS_BASE}/categories/{category}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=15.0)
            if resp.status_code != 200:
                return {"error": f"API returned {resp.status_code}", "articles": []}
            data = resp.json()
            if not data.get("success"):
                return {"error": "API returned unsuccessful response", "articles": []}
            return {
                "category": data.get("categoryName", category),
                "articles": [
                    {
                        "id": a.get("id", ""),
                        "title": a.get("title", ""),
                        "link": a.get("link", ""),
                        "description": a.get("description", ""),
                        "time": a.get("time", ""),
                    }
                    for a in data.get("articles", [])
                ]
            }
    except Exception as e:
        return {"error": str(e), "articles": []}

get_bangladeshi_news_tool = {
    "name": "get_bangladeshi_news",
    "description": (
        "Fetch latest Bangladeshi news from BBC Bengali. "
        "Call this when the user asks about news from Bangladesh, "
        "Bengali news, or any Bangladesh-specific topic. "
        "Returns articles in Bengali language with titles, links, and timestamps.\n\n"
        "Available categories: main (মূলপাতা), politics (রাজনীতি), world (বিশ্ব), "
        "economics (অর্থনীতি), health (স্বাস্থ্য), sports (খেলা), technology (প্রযুক্তি), "
        "bangladesh (বাংলাদেশ), india (ভারত).\n\n"
        "Use 'main' or 'bangladesh' for general Bangladeshi news. "
        "Use specific categories for focused topics."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "category": {
                "type": "STRING",
                "description": "Category ID: main, politics, world, economics, health, sports, technology, bangladesh, india. Default: main"
            }
        },
        "required": []
    }
}

# 5. Dictionary - Free Dictionary API
async def define_word(word: str):
    """
    Get dictionary definition of a word.
    """
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            
            if resp.status_code == 404:
                return {"error": f"Word not found: {word}"}
            
            data = resp.json()
            if not data:
                return {"error": f"No definition found"}
            
            entry = data[0]
            meanings = []
            
            for meaning in entry.get('meanings', [])[:2]:
                for defn in meaning.get('definitions', [])[:2]:
                    meanings.append({
                        "part_of_speech": meaning.get('partOfSpeech'),
                        "definition": defn.get('definition'),
                        "example": defn.get('example')
                    })
            
            return {
                "word": entry.get('word'),
                "phonetic": entry.get('phonetic', ''),
                "meanings": meanings
            }
    except Exception as e:
        return {"error": str(e)}






# ============ TOOL DEFINITIONS FOR SODA ============

weather_tool = {
    "name": "get_weather",
    "description": "Get current weather for any location. Use when user asks about weather, temperature, or climate.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "location": {"type": "STRING", "description": "City name or location"},
            "units": {"type": "STRING", "description": "celsius or fahrenheit (default: celsius)"}
        },
        "required": ["location"]
    }
}

ip_info_tool = {
    "name": "get_ip_info",
    "description": "Get IP geolocation and location info. Use when user asks about IP or location.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "ip": {"type": "STRING", "description": "IP address (optional)"}
        },
        "required": []
    }
}

exchange_tool = {
    "name": "get_exchange_rate",
    "description": "Get currency exchange rate. Use when user asks about currency conversion or exchange rates.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "from_curr": {"type": "STRING", "description": "From currency code (e.g., USD)"},
            "to_curr": {"type": "STRING", "description": "To currency code (e.g., EUR)"}
        },
        "required": ["from_curr", "to_curr"]
    }
}

define_word_tool = {
    "name": "define_word",
    "description": "Get dictionary definition of a word. Use when user asks about word meaning or definition.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "word": {"type": "STRING", "description": "Word to define"}
        },
        "required": ["word"]
    }
}

open_browser_tool = {
    "name": "open_browser",
    "description": (
        "Open a URL in the internal floating webview window (within SODA's own UI). "
        "By default opens internally. Use this when the user asks to 'open', 'show', "
        "'visit', 'go to', or 'view' a link or website. "
        "Pass the full URL. Does NOT open in the system browser unless external=true. "
        "Set external=true ONLY if the user explicitly says 'open in Chrome', "
        "'open externally', or names a specific browser. "
        "When external=true, SODA also goes to background mode automatically. "
        "For text-only content extraction, use browse_webpage instead. "
        "DO NOT use this tool for checking or reading emails. Use read_emails tool instead."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "The full URL to open"},
            "external": {"type": "BOOLEAN", "description": "Set to true to open in system browser instead of internal webview (default: false)"},
            "browser": {"type": "STRING", "description": "Optional browser override (only used if external=true)"}
        },
        "required": ["url"]
    }
}

list_files_tool = {
    "name": "list_files",
    "description": (
        "List files and folders in ANY directory on ANY drive with structured results shown in the HUD. "
        "Has FULL access to all drives and folders (C:\\, D:\\, E:\\, etc.) — no restrictions. "
        "Use when the user wants to navigate to a folder, see what's in a drive, "
        "or browse files. Results are numbered so the user can pick one. "
        "The 'search' parameter lets you find files by partial name match — use when the user says "
        "'find the config file', 'search for python scripts', 'look for readme', or gives a vague filename. "
        "Examples: 'navigate to D drive', 'find python files' -> list_files(path='D:\\', search='.py'), "
        "'search for config in Documents' -> list_files(path='C:\\Users\\Abir\\Documents', search='config'), "
        "'show me my desktop' -> list_files(path='C:\\Users\\Abir\\Desktop')."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "The directory path to list (e.g., 'D:\\', 'C:\\Users\\Abir\\Documents'). Can be ANY drive or folder. If empty or 'drives', shows all available drives."},
            "search": {"type": "STRING", "description": "Optional: filter files by name (case-insensitive partial match). Use when user gives a vague filename. Example: 'config' finds all files with 'config' in the name."}
        },
        "required": []
    }
}

open_file_tool = {
    "name": "open_file",
    "description": (
        "Open a file with its default application. Use after listing files "
        "and the user picks one by number or name. The file opens in its default app."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "The full path of the file to open"}
        },
        "required": ["path"]
    }
}

notepad_open_tool = {
    "name": "notepad_open",
    "description": "Open a multi-tab notepad window where you can write notes, links, numbers, and important information. Use this for workflow planning, tracking progress, storing URLs during tasks. The notepad supports multiple named tabs and can save content as .txt files.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "tabs": {
                "type": "ARRAY",
                "description": "Optional initial tabs. Each tab: {title, content}. If omitted, opens with one empty tab.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING", "description": "Tab name e.g. 'github-links', 'deploy-notes'"},
                        "content": {"type": "STRING", "description": "Initial text content"}
                    }
                }
            }
        }
    }
}

notepad_write_tool = {
    "name": "notepad_write",
    "description": "Write content to a notepad tab. Creates the tab if it doesn't exist, appends or replaces content. Use this to store progress, links, and notes during multi-step workflows.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "tab": {
                "type": "STRING",
                "description": "Tab name to write to. If it doesn't exist, a new tab is created."
            },
            "content": {
                "type": "STRING",
                "description": "Text content to write. Use \\n for newlines."
            },
            "mode": {
                "type": "STRING",
                "description": "'append' (add to existing content) or 'replace' (overwrite). Default 'append'."
            }
        },
        "required": ["tab", "content"]
    }
}

notepad_read_tool = {
    "name": "notepad_read",
    "description": "Read content from a notepad tab. Returns the text content of the specified tab, or lists all tabs if no tab specified.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "tab": {
                "type": "STRING",
                "description": "Tab name to read. If omitted, returns list of all tab names."
            }
        }
    }
}

view_file_tool = {
    "name": "view_file",
    "description": "Open a file inside a floating draggable window in SODA. Supports text files (code, logs, config), images (PNG, JPG, GIF, SVG), and videos (MP4, WebM). The file appears in a resizable window you can move around. Use this INSTEAD of open_file when the user wants to see the file content inside SODA rather than opening it in an external app. Examples: 'show me that image' -> view_file(path='D:\\photo.png'), 'open this log file' -> view_file(path='D:\\error.log'), 'let me see the config' -> view_file(path='D:\\config.json').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "Full path to the file to view."}
        },
        "required": ["path"]
    }
}

send_telegram_message_tool = {
    "name": "send_telegram_message",
    "description": "Send a text message to the user's Telegram. Use when the user asks you to message them on Telegram, send a notification, or provide a status update on their phone. Examples: 'notify me on Telegram' -> send_telegram_message(text='Task complete!'), 'send this to my phone' -> send_telegram_message(text='Here is the info you requested.').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "The message text to send to Telegram."}
        },
        "required": ["text"]
    }
}

send_telegram_file_tool = {
    "name": "send_telegram_file",
    "description": "Send a file to the user's Telegram. Automatically zips folders. Max file size 50MB. Use when the user says 'send me this file on Telegram', 'transfer this file to my phone', or wants a file delivered to their Telegram. The user will see a visual animation in the HUD showing the file being sent. Examples: 'send me that photo on Telegram' -> send_telegram_file(path='D:\\photo.jpg'), 'transfer the report to my phone' -> send_telegram_file(path='D:\\report.pdf'), 'send my project folder' -> send_telegram_file(path='D:\\myproject').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "Full path to the file or folder to send."}
        },
        "required": ["path"]
    }
}

go_to_sleep_tool = {
    "name": "go_to_sleep",
    "description": "Put SODA to sleep. Minimizes the window and stops responding to all voice and text commands. Only the wake command 'wake up' will be recognized. Use when the user says 'sleep', 'go to sleep', 'take a nap', 'goodnight', or wants SODA to stop listening and minimize its window.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

wake_up_tool = {
    "name": "wake_up",
    "description": "Wake SODA up from sleep mode. Restores the window and resumes normal operation. Use when the user says 'wake up', 'come back', 'resume', 'good morning', or wants SODA to start listening again.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

close_panel_tool = {
    "name": "close_panel",
    "description": (
        "Close/clear/dismiss everything on the screen — panels, windows, etc. "
        "Use when the user says ANY of: 'close it', 'close this', 'close everything', 'close all', 'clear the screen', "
        "'dismiss', 'get rid of this', 'make it go away', "
        "'wipe everything', 'leave', 'leave it', 'stop', 'exit', 'cancel', 'quit', 'forget it', 'never mind'. "
        "Also works for specific panels: 'close the search', 'close the file list', 'close the terminal', "
        "'close the news'. "
        "Panel 'all' wipes EVERYTHING — panels and floating windows."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "panel": {
                "type": "STRING",
                "description": "Panel to close. 'all' — closes everything, clears the screen. Specific: 'terminal', 'search', 'files', 'webpage', 'file', 'info', 'tool', 'tools', 'github', 'deploy', 'webview'. Stacks: 'github_stack', 'deploy_stack', 'search_stack'. Special: 'file_scroll'."
            }
        },
        "required": []
    }
}

# ============ SYSTEM CONTROL TOOLS ============

system_status_tool = {
    "name": "get_system_status",
    "description": "Get current system performance - CPU, RAM, GPU usage. Use when user asks about system status, computer health, device performance, how's the computer doing, check system.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

close_window_tool = {
    "name": "close_window",
    "description": "Close a specific window or application by name. Use when user asks to close WhatsApp, close Chrome, or close specific app. Provide the window name like 'whatsapp', 'chrome', 'youtube', etc.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "window_name": {
                "type": "STRING", 
                "description": "The name of the window to close (e.g., 'whatsapp', 'chrome', 'notepad'). Partial match works."
            }
        },
        "required": ["window_name"]
    }
}

async def close_window(window_name: str):
    """Close a window by name using async taskkill."""
    try:
        import asyncio
        window_name_lower = window_name.lower()
        app_mappings = {
            'whatsapp': 'WhatsApp',
            'chrome': 'chrome',
            'firefox': 'firefox',
            'edge': 'msedge',
            'brave': 'brave',
            'opera': 'opera',
            'spotify': 'spotify',
            'discord': 'discord',
            'slack': 'slack',
            'notepad': 'notepad',
            'code': 'code',
            'vscode': 'code',
        }
        process_name = None
        for key, name in app_mappings.items():
            if key in window_name_lower:
                process_name = name
                break
        if not process_name:
            process_name = window_name
        proc = await asyncio.create_subprocess_exec(
            'taskkill', '/F', '/IM', f'{process_name}.exe',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return f"Closed {window_name}"
        elif b"not found" in stderr.lower():
            return f"Process not found: {window_name}"
        else:
            return f"Could not close {window_name}: {stderr.decode(errors='replace')}"
    except Exception as e:
        return f"Error closing window: {str(e)}"


# 8. File Browser Tools (interactive file navigation)

async def list_files(path: str = "", search: str = "") -> dict:
    """List directory contents with structured metadata (name, type, size)."""
    import asyncio
    import string
    import json
    try:
        path = path.strip().strip('"').strip("'") if path else ""
        # Drive enumeration
        if not path or path.lower() in (".", "drives", "this pc", "computer", "my computer"):
            try:
                ps_drive = "Get-PSDrive -PSProvider FileSystem | Select-Object @{N='Name';E={$_.Root}}, @{N='Type';E={'folder'}} | ConvertTo-Json -Compress"
                proc = await asyncio.create_subprocess_exec('powershell', '-Command', ps_drive, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                out, _ = await proc.communicate()
                drives = json.loads(out.decode('utf-8', errors='replace').strip())
                if isinstance(drives, dict): drives = [drives]
                items = []
                for d in drives:
                    root = d.get('Name', '')
                    if root:
                        items.append({"number": len(items) + 1, "name": root, "type": "folder", "size": 0, "modified": "", "ext": "", "path": root})
                return {"success": True, "path": "Available Drives", "items": items}
            except Exception:
                return {"success": False, "path": "drives", "items": [], "error": "Could not enumerate drives"}

        # Normalize path
        if len(path) == 2 and path[1] == ':':
            path += '\\'

        ps_script = (
            "Get-ChildItem -Path '" + path + "' -Force -ErrorAction SilentlyContinue | "
            "Select-Object Name, @{N='Type';E={if($_.PSIsContainer){'folder'}else{'file'}}}, Length, LastWriteTime | "
            "ConvertTo-Json -Compress"
        )
        proc = await asyncio.create_subprocess_exec(
            'powershell', '-Command', ps_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode('utf-8', errors='replace').strip()
        if not output:
            err_msg = stderr.decode('utf-8', errors='replace').strip()
            if "access denied" in err_msg.lower() or "permission denied" in err_msg.lower():
                return {"success": False, "path": path, "items": [], "error": f"Access denied: {path}"}
            if "not found" in err_msg.lower():
                return {"success": False, "path": path, "items": [], "error": f"Path not found: {path}"}
            return {"success": True, "path": path, "items": [], "error": "Directory is empty"}
        items = json.loads(output)
        if isinstance(items, dict):
            items = [items]
        result = []
        for item in items:
            name = item.get('Name', '')
            item_type = item.get('Type', 'file')
            size = item.get('Length', 0)
            modified = item.get('LastWriteTime', '')
            ext = os.path.splitext(name)[1].lower() if item_type == 'file' else ''
            result.append({
                "number": len(result) + 1,
                "name": name,
                "type": item_type,
                "size": size,
                "modified": modified,
                "ext": ext,
                "path": os.path.join(path, name)
            })
        # Apply search filter
        if search:
            search_lower = search.lower()
            result = [i for i in result if search_lower in i['name'].lower()]
        return {"success": True, "path": path, "items": result}
    except Exception as e:
        print(f"[list_files] Failed: {e}")
        return {"success": False, "path": path, "items": [], "error": str(e)}


async def open_file(file_path: str) -> dict:
    """Open a file with its default application."""
    import asyncio
    try:
        file_path = file_path.strip().strip('"').strip("'")
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        proc = await asyncio.create_subprocess_exec(
            'cmd', '/c', 'start', '""', file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode == 0:
            return {"success": True, "result": f"Opened {os.path.basename(file_path)}"}
        else:
            return {"success": False, "error": f"Failed to open {file_path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_folder(path: str) -> dict:
    """Create a new folder at the specified path."""
    try:
        os.makedirs(path, exist_ok=True)
        return {"success": True, "result": f"Created folder: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_items(paths: list) -> dict:
    """Move files/folders to the Windows Recycle Bin."""
    import asyncio
    try:
        if isinstance(paths, str):
            paths = [paths]
        results = []
        for p in paths:
            p = p.strip().strip('"').strip("'")
            if not os.path.exists(p):
                results.append({"path": p, "success": False, "error": "Not found"})
                continue
            ps_script = (
                f"[Microsoft.VisualBasic.FileIO]::DeleteFile('{p}','OnlyErrorDialogs','SendToRecycleBin')"
                if os.path.isfile(p) else
                f"[Microsoft.VisualBasic.FileIO]::DeleteDirectory('{p}','OnlyErrorDialogs','SendToRecycleBin')"
            )
            proc = await asyncio.create_subprocess_exec(
                'powershell', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            results.append({"path": p, "success": proc.returncode == 0})
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def rename_item(old_path: str, new_path: str) -> dict:
    """Rename a file or folder."""
    try:
        old_path = old_path.strip().strip('"').strip("'")
        new_path = new_path.strip().strip('"').strip("'")
        if not os.path.exists(old_path):
            return {"success": False, "error": f"Not found: {old_path}"}
        os.rename(old_path, new_path)
        return {"success": True, "result": f"Renamed to {os.path.basename(new_path)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def copy_item(source: str, destination: str) -> dict:
    """Copy a file or folder to a new location."""
    try:
        source = source.strip().strip('"').strip("'")
        destination = destination.strip().strip('"').strip("'")
        if not os.path.exists(source):
            return {"success": False, "error": f"Not found: {source}"}
        if os.path.isfile(source):
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
        else:
            os.makedirs(destination, exist_ok=True)
            shutil.copytree(source, destination, dirs_exist_ok=True)
        return {"success": True, "result": f"Copied to {destination}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def move_item(source: str, destination: str) -> dict:
    """Move a file or folder to a new location."""
    try:
        source = source.strip().strip('"').strip("'")
        destination = destination.strip().strip('"').strip("'")
        if not os.path.exists(source):
            return {"success": False, "error": f"Not found: {source}"}
        os.makedirs(os.path.dirname(destination), exist_ok=True) if os.path.isfile(source) else os.makedirs(destination, exist_ok=True)
        shutil.move(source, destination)
        return {"success": True, "result": f"Moved to {destination}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_drives() -> dict:
    """List all available drives on the system."""
    return await list_files("drives")


async def scrape_site(url: str, prompt: str) -> dict:
    """Extract structured data from a URL using AI. Uses dedicated SCRAPER_GEMINI_KEY or falls back."""
    from scraper_ai import extract
    return await extract(url, prompt)


create_folder_tool = {
    "name": "create_folder",
    "description": (
        "Create a new folder on the filesystem. "
        "After creating the folder, you will automatically be taken into it "
        "so you can see its contents. "
        "Example: create_folder(path='D:\\downloads\\sorted')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "Full path for the new folder to create."
            }
        },
        "required": ["path"]
    }
}

search_and_send_telegram_tool = {
    "name": "search_and_send_telegram",
    "description": (
        "Search the web for a query, then save the results as a markdown file with "
        "a summary and all useful links, and send the file to the user's Telegram. "
        "Perfect for research: 'search for X and send me the results', "
        "'find info about Y and send to my Telegram', "
        "'search the web for Z and send links and summary'. "
        "Example: search_and_send_telegram(query='latest AI news 2026', num_results=8)"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "The search query"},
            "num_results": {"type": "INTEGER", "description": "Number of results (1-15). Default 8."}
        },
        "required": ["query"]
    }
}


async def search_and_send_telegram(query: str, num_results: int = 8) -> dict:
    """Search the web, save results as markdown, send via Telegram."""
    from telegram_bot import telegram_bot
    from agents.web_search_agent import WebSearchAgent
    import os, time

    # Search
    agent = WebSearchAgent()
    search_result = await agent.execute(query=query, num_results=num_results)
    results = search_result.get("results", [])
    if not results:
        return {"success": False, "result": "No search results found for that query."}

    # Format as markdown
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Web Search Results",
        f"",
        f"**Query:** {query}",
        f"**Searched at:** {timestamp}",
        f"**Results found:** {len(results)}",
        f"",
        f"---",
        f"",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"## {i}. {r['title']}")
        lines.append(f"")
        lines.append(f"**URL:** {r['url']}")
        lines.append(f"")
        lines.append(f"{r.get('snippet', 'No description available.')}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    summary = f"Found {len(results)} results for \"{query}\". "
    links = "\n".join(f"- {r['title']}: {r['url']}" for r in results)
    lines.extend([
        f"## Quick Links",
        f"",
        links,
        f"",
        f"---",
        f"*Generated by SODA Websmith*"
    ])

    content = "\n".join(lines)

    # Save to temp file
    safe_name = "".join(c if c.isalnum() or c in ' _-' else '_' for c in query)[:40]
    temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"search_{safe_name}_{int(time.time())}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Send via telegram
    send_result = await telegram_bot.send_file(file_path)
    sent = send_result.get("success", False)

    # Clean up
    try:
        os.unlink(file_path)
    except:
        pass

    return {
        "success": sent,
        "result": send_result.get("result", "Sent to Telegram"),
        "query": query,
        "results_count": len(results),
        "summary": summary,
        "links": links
    }


async def get_pagespeed_insights(url: str, strategy: str = "desktop"):
    """Fetches Lighthouse SEO/performance audit from Google PageSpeed Insights API (free)."""
    base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": strategy}
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if api_key:
        params["key"] = api_key

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(base_url, params=params)
            if resp.status_code != 200:
                return {"error": f"Google API Error: {resp.status_code} — {resp.text[:200]}"}
            data = resp.json()
            lh = data.get("lighthouseResult", {})
            cat = lh.get("categories", {})
            audits = lh.get("audits", {})

            scores = {
                "seo": int((cat.get("seo", {}).get("score") or 0) * 100),
                "performance": int((cat.get("performance", {}).get("score") or 0) * 100),
                "accessibility": int((cat.get("accessibility", {}).get("score") or 0) * 100),
                "best_practices": int((cat.get("best-practices", {}).get("score") or 0) * 100),
            }

            vitals = {
                "lcp": audits.get("largest-contentful-paint", {}).get("displayValue", "N/A"),
                "cls": audits.get("cumulative-layout-shift", {}).get("displayValue", "N/A"),
                "tbt": audits.get("total-blocking-time", {}).get("displayValue", "N/A"),
                "fcp": audits.get("first-contentful-paint", {}).get("displayValue", "N/A"),
                "si": audits.get("speed-index", {}).get("displayValue", "N/A"),
            }

            opportunities = []
            for aid, a in audits.items():
                s = a.get("score")
                if s is not None and s < 0.90:
                    desc = a.get("description", "")
                    opportunities.append({
                        "title": a.get("title", aid),
                        "issue": desc.split("[")[0].strip(),
                        "score_impact": int((1 - s) * 100),
                        "category": aid,
                    })
            opportunities.sort(key=lambda x: x["score_impact"], reverse=True)

            passed = [a.get("title", aid) for aid, a in audits.items()
                      if a.get("score") is not None and a.get("score") >= 0.90][:15]

            return {
                "url": url,
                "strategy": strategy,
                "scores": scores,
                "vitals": vitals,
                "opportunities": opportunities[:25],
                "passed_audits": passed,
                "total_audits": len(audits),
            }
        except httpx.TimeoutException:
            return {"error": "Google API timed out (60s). Try a smaller page or add a paid API key."}
        except Exception as e:
            return {"error": f"PageSpeed audit failed: {str(e)}"}


get_pagespeed_insights_tool = {
    "name": "get_pagespeed_insights",
    "description": (
        "Run a free Google Lighthouse SEO & performance audit on any public URL. "
        "Returns Core Web Vitals (LCP, CLS, TBT, FCP), category scores (SEO, performance, "
        "accessibility, best practices), and ranked optimization opportunities with score impact. "
        "Example: get_pagespeed_insights(url='https://example.com', strategy='desktop')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {
                "type": "STRING",
                "description": "Full URL of the page to audit (e.g. 'https://example.com')"
            },
            "strategy": {
                "type": "STRING",
                "description": "Device strategy: 'desktop' or 'mobile' (default 'desktop')"
            }
        },
        "required": ["url"]
    }
}


shutdown_soda_tool = {
    "name": "shutdown_soda",
    "description": (
        "Completely shut down SODA — stops the server and closes everything. "
        "Use ONLY when the user explicitly says 'soda turn off', 'shut down soda', "
        "'stop soda', 'power off', 'exit soda', or wants to fully terminate SODA. "
        "This is NOT sleep mode — the server process will exit and must be manually restarted. "
        "Example: shutdown_soda() — terminates the entire SODA server."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}


show_agents_tool = {
    "name": "show_agents",
    "description": (
        "Show all available SODA sub-agents with their names, roles, status, and capabilities. "
        "Use when the user asks 'what agents do you have', 'show me your agents', "
        "'who are your helpers', 'list all agents', or wants to know about available sub-agents. "
        "Returns a list of agent identity cards."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

delete_items_tool = {
    "name": "delete_items",
    "description": (
        "Move files or folders to the Windows Recycle Bin (not permanently deleted). "
        "Use when the user says 'delete file 3', 'remove this folder', 'trash this', "
        "'get rid of file 2', 'delete the config file'. You can delete multiple items at once. "
        "After deletion, the file browser refreshes automatically. "
        "Example: delete_items(paths=['D:\\temp\\old.txt'])"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "paths": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "List of full paths to delete. Can be files or folders."
            }
        },
        "required": ["paths"]
    }
}

rename_item_tool = {
    "name": "rename_item",
    "description": (
        "Rename a file or folder. Use when the user says 'rename file 2 to newname', "
        "'rename the config file to config.old', 'rename the Photos folder to Old Photos'. "
        "After renaming, the file browser refreshes automatically. "
        "Example: rename_item(old_path='D:\\notes.txt', new_path='D:\\notes_old.txt')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "old_path": {"type": "STRING", "description": "Current full path"},
            "new_path": {"type": "STRING", "description": "New full path (new name)"}
        },
        "required": ["old_path", "new_path"]
    }
}

copy_item_tool = {
    "name": "copy_item",
    "description": (
        "Copy a file or folder to a new location. Use when the user says "
        "'copy file 3 to D drive', 'copy this folder to Desktop', 'duplicate report.docx'. "
        "After copying, the file browser navigates to the destination automatically. "
        "Example: copy_item(source='D:\\docs\\report.docx', destination='D:\\Backup\\report.docx')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "source": {"type": "STRING", "description": "Source full path"},
            "destination": {"type": "STRING", "description": "Destination full path"}
        },
        "required": ["source", "destination"]
    }
}

move_item_tool = {
    "name": "move_item",
    "description": (
        "Move a file or folder to a new location. Use when the user says "
        "'move file 2 to D drive', 'move this folder to Desktop', 'move the downloads'. "
        "After moving, the file browser navigates to the destination automatically. "
        "Example: move_item(source='D:\\docs\\file.txt', destination='E:\\archive\\file.txt')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "source": {"type": "STRING", "description": "Source full path"},
            "destination": {"type": "STRING", "description": "Destination full path"}
        },
        "required": ["source", "destination"]
    }
}

list_drives_tool = {
    "name": "list_drives",
    "description": (
        "List all available drives on the system (C:\\, D:\\, E:\\, etc.). "
        "Use when the user says 'show my drives', 'list drives', 'what drives do I have', "
        "'show me my disks', or when you need to know what drives exist. "
        "Results show in the file browser just like a folder listing. "
        "Example: list_drives()"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

scroll_file_list_tool = {
    "name": "scroll_file_list",
    "description": (
        "Scroll the file browser panel in the specified direction. "
        "Use when user says 'scroll down', 'scroll up', 'scroll down a bit', "
        "'scroll to bottom', 'go to the bottom', 'stop scrolling'. "
        "The file list must be visible first (call list_files or list_drives)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Scroll action: 'up' (scroll up a bit), "
                               "'down' (scroll down a bit), 'bottom' (jump to last item), "
                               "'stop' (stop any ongoing scroll animation)"
            }
        },
        "required": ["action"]
    }
}

export_data_tool = {
    "name": "export_data",
    "description": (
        "Export scraped or structured data to a formatted file. "
        "Call this when the user says 'save this', 'export', "
        "'make a doc', 'make a csv', 'save as markdown', 'save as word', "
        "'create a report', 'download', or similar. The exported file is automatically opened "
        "in the SODA viewer so the user can see it immediately. "
        "Supported formats: json, html, markdown (table), csv (spreadsheet), docx (Word with HUD styling). "
        "Examples: 'export as markdown', 'save as csv', 'download as html to desktop', "
        "'save as json to downloads folder'. "
        "The title becomes the filename. If the user specifies a save location, "
        "fill the path parameter (e.g. '~/Downloads/report.json', 'C:/Users/Abir/Desktop/report.md')."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "data": {
                "type": "STRING",
                "description": "The data to export — can be a JSON string (dict or list of dicts), or plain text. Usually pass the raw scrape result or PageSpeed data."
            },
            "format": {
                "type": "STRING",
                "description": "Export format: 'json', 'html', 'markdown', 'csv', or 'docx'"
            },
            "title": {
                "type": "STRING",
                "description": "Filename title (without extension). e.g. 'Laptop Prices 2026'"
            },
            "path": {
                "type": "STRING",
                "description": "(Optional) Full save path including filename and extension. "
                               "Examples: 'C:/Users/Abir/Desktop/report.md', '~/Downloads/scores.json'. "
                               "Use ~ for home directory. If omitted, saves to Desktop/soda_exports/."
            }
        },
        "required": ["data", "format", "title"]
    }
}

scrape_site_tool = {
    "name": "scrape_site",
    "description": (
        "Extract structured data from any URL using AI. "
        "You give a prompt describing what data you want, and it extracts that information "
        "from the webpage — handles JavaScript-rendered content, dynamic pages, and complex layouts. "
        "Use when the user says 'scrape this page', 'extract data from this site', "
        "'get the prices from this page', 'find all links on this site', "
        "'get me the product details from this URL', or when you need to collect structured "
        "information from a website. The prompt should be specific about what to extract. "
        "Examples: 'extract all product names and prices', "
        "'get the company description, founders, and funding amount', "
        "'list all article titles and publication dates', "
        "'find all navigation links and their labels'. "
        "Uses a dedicated Gemini API key for scraping (separate from main SODA key)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "The full URL of the page to scrape"},
            "prompt": {"type": "STRING", "description": "Natural language description of what data to extract from the page"}
        },
        "required": ["url", "prompt"]
    }
}
