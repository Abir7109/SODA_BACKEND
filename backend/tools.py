write_file_tool = {
    "name": "write_file",
    "description": "Writes content to a file at the specified path. Overwrites if exists. After writing, the file is automatically opened in the SODA viewer and the file browser refreshes to show the new file in its parent directory.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to write to."
            },
            "content": {
                "type": "STRING",
                "description": "The content to write to the file."
            }
        },
        "required": ["path", "content"]
    }
}

read_file_tool = {
    "name": "read_file",
    "description": "Reads the content of a file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to read."
            }
        },
        "required": ["path"]
    }
}

edit_file_tool = {
    "name": "edit_file",
    "description": "Edit an existing file by finding and replacing exact text. Use this instead of write_file when you only need to change part of a file — it preserves everything else. The old_string must match the existing content exactly, including whitespace and indentation.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The full path of the file to edit."
            },
            "old_string": {
                "type": "STRING",
                "description": "The exact existing text to find and replace. Must match whitespace and indentation exactly."
            },
            "new_string": {
                "type": "STRING",
                "description": "The new text to replace it with."
            }
        },
        "required": ["path", "old_string", "new_string"]
    }
}

list_files_tool = {
    "name": "list_files",
    "description": "List files and folders in a directory on the local machine. Returns file names, sizes, and modification dates. Use this to browse the user's file system.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "Directory path to list. Defaults to user's desktop if not specified."
            },
            "search": {
                "type": "STRING",
                "description": "Optional search query to filter files by name."
            }
        }
    }
}

open_file_tool = {
    "name": "open_file",
    "description": "Open a file on the local machine using the default application. Use when the user asks you to open a specific file or document.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The full path to the file to open."
            }
        },
        "required": ["path"]
    }
}

execute_command_tool = {
    "name": "execute_command",
    "description": "Executes a system command in the background (no popup windows). Use when the user asks to run programs, execute system commands, or perform any system operations. The command runs hidden and returns the output directly.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {
                "type": "STRING",
                "description": "The command to execute (e.g., 'calc', 'notepad', 'start chrome', etc.)"
            }
        },
        "required": ["command"]
    }
}

terminal_execute_tool = {
    "name": "terminal_execute",
    "description": (
        "Run a terminal/shell command on the user's system in the BACKGROUND "
        "(no console window pops up) and return the output. "
        "Use this to run scripts, check git status, install packages, list files, etc. "
        "Output is captured and returned cleanly — NEVER show empty results. "
        "If a command fails, the system automatically retries with alternative approaches "
        "up to 5 times. The frontend shows a thinking animation during retries. "
        "NEVER use for destructive commands without asking first."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {"type": "STRING", "description": "The full shell command to run"},
            "timeout": {"type": "INTEGER", "description": "Max seconds to wait. Default 30."}
        },
        "required": ["command"]
    }
}

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from external_apis import (
    weather_tool,
    ip_info_tool,
    exchange_tool,
    get_bangladeshi_news_tool,
    define_word_tool,
    open_browser_tool,
    list_files_tool,
    open_file_tool,
    close_panel_tool,
    system_status_tool,
    close_window_tool,
    notepad_open_tool,
    notepad_write_tool,
    notepad_read_tool,
    view_file_tool,
    create_folder_tool,
    show_agents_tool,
    delete_items_tool,
    get_pagespeed_insights_tool,
    rename_item_tool,
    copy_item_tool,
    move_item_tool,
    list_drives_tool,
    scroll_file_list_tool,
    scrape_site_tool,
    export_data_tool,
)
from soda_agents import get_agent_tool_defs
from workbase import workbase_tool, Workbase
from ielts_tools import IELTS_TOOLS
from feelings_tools import FEELINGS_TOOLS_SCHEMA

screenshot_tool = {
    "name": "screenshot",
    "description": "Take a full-screen screenshot and save it to projects/clipboard/. Returns the file path. Use when the user says 'screenshot', 'snap this', 'capture screen', 'take a picture of my screen'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

list_processes_tool = {
    "name": "list_processes",
    "description": "List the top running processes sorted by memory. Use when the user asks 'what's using my RAM', 'top processes', 'show running apps', 'what's slowing my computer'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "limit": {"type": "INTEGER", "description": "Max number of processes to return (default 10)"}
        },
        "required": []
    }
}

get_active_window_tool = {
    "name": "get_active_window",
    "description": "Get the title of the currently focused window. Use when the user says 'what window am I in', 'what am I looking at', 'what's the active app'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

run_code_tool = {
    "name": "run_code",
    "description": "Run a Python or JavaScript code snippet in a sandboxed subprocess. Returns stdout, stderr, execution time, and the value of the last expression (Python). Use when the user says 'run this python', 'execute this code', 'eval this', 'what does this code do', 'test this script'. Supports python and javascript.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "code": {"type": "STRING", "description": "The code to execute"},
            "language": {"type": "STRING", "description": "Language: 'python', 'javascript', or 'auto' (default auto-detect)"},
            "timeout": {"type": "INTEGER", "description": "Timeout in seconds (default 10)"}
        },
        "required": ["code"]
    }
}

remember_fact_tool = {
    "name": "remember_fact",
    "description": "Permanently remember a fact about the user (name, birthday, preferences, allergies, project info, etc). CALL THIS PROACTIVELY whenever the user shares new personal information — do not wait to be asked. Also use when the user explicitly says 'remember that...', 'don't forget...', 'my X is Y', 'I live in...', 'note that...'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "key": {"type": "STRING", "description": "Short identifier, e.g. 'birthday', 'favorite_food', 'home_address'"},
            "value": {"type": "STRING", "description": "The value to remember"}
        },
        "required": ["key", "value"]
    }
}

recall_facts_tool = {
    "name": "recall_facts",
    "description": "Search the user's stored facts by keyword. Use when the user says 'what do you know about me', 'do you remember my X', 'what's my Y', 'recall...'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Search term (case-insensitive substring)"}
        },
        "required": ["query"]
    }
}

get_user_profile_tool = {
    "name": "get_user_profile",
    "description": "Get the user's stored profile (name, preferences, etc.) and recent facts. Use when the user says 'what's my name', 'show my profile', 'what do you know about me'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

set_preference_tool = {
    "name": "set_preference",
    "description": "Set a user preference (e.g. 'wake_word', 'theme', 'volume'). Use when the user says 'I prefer X', 'change my Y to Z', 'set my...'. For personal facts, use remember_fact instead.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "key": {"type": "STRING", "description": "Preference name"},
            "value": {"type": "STRING", "description": "Preference value"}
        },
        "required": ["key", "value"]
    }
}

remember_person_tool = {
    "name": "remember_person",
    "description": "Remember information about a person the user knows. Store name, relationship, traits, preferences, and notes. CALL THIS PROACTIVELY when someone is introduced or mentioned with relationship context — never ask 'should I remember them', just remember. Also use when the user explicitly says 'remember this person' or gives info about someone.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "Person's name"},
            "relationship": {"type": "STRING", "description": "Relationship to user (friend, brother, colleague, etc.)"},
            "traits": {"type": "STRING", "description": "Key traits or personality characteristics"},
            "preferences": {"type": "STRING", "description": "Things this person likes or dislikes"},
            "notes": {"type": "STRING", "description": "Any additional information"}
        },
        "required": ["name"]
    }
}

recall_person_tool = {
    "name": "recall_person",
    "description": "Search stored people information by name or trait. Use when the user asks 'who is X', 'what do you know about X', 'remind me about X'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Name or trait to search for"}
        },
        "required": ["query"]
    }
}

recall_by_relationship_tool = {
    "name": "recall_by_relationship",
    "description": "Search people by relationship keyword (e.g. 'sister', 'boss', 'neighbor'). Use this when the user says 'call my sister', 'message my brother', etc. — before calling any phone/WhatsApp action.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "relationship": {"type": "STRING", "description": "Relationship keyword to search (e.g. 'sister', 'boss', 'neighbor', 'dad')"},
            "limit": {"type": "INTEGER", "description": "Maximum results to return (default 5)"}
        },
        "required": ["relationship"]
    }
}

remember_lesson_tool = {
    "name": "remember_lesson",
    "description": "Learn from a mistake or correction. Store what went wrong and what should be done differently next time. CALL THIS PROACTIVELY whenever you receive feedback or realize a better approach. Also use when the user explicitly corrects you, or when you identify a pattern to improve.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "situation": {"type": "STRING", "description": "What happened or the situation that needs correction"},
            "correction": {"type": "STRING", "description": "What should be done differently next time"}
        },
        "required": ["situation", "correction"]
    }
}

forget_fact_tool = {
    "name": "forget_fact",
    "description": "Delete a stored fact by key. Use when the user says 'forget that', 'remove that memory', 'I changed my mind about X', 'delete that fact'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "key": {"type": "STRING", "description": "The key of the fact to forget"}
        },
        "required": ["key"]
    }
}

list_memory_tool = {
    "name": "list_memory",
    "description": "List all stored memories: facts, people, and lessons learned. Use when the user asks 'what do you remember', 'show me your memory', 'what have I told you', 'what do you know'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "type": {"type": "STRING", "description": "Type to list: 'facts', 'people', 'lessons', or 'all' (default)"}
        },
        "required": []
    }
}

show_memory_tool = {
    "name": "show_memory",
    "description": (
        "Display all stored memory (profile, facts, people, lessons) in the MEMORY DATABASE "
        "HUD animation overlay. Call this ONLY when the user explicitly asks to see your "
        "memory/knowledge — e.g. 'show me what you know', 'show me your memory', "
        "'let me see what you remember'. "
        "DO NOT call this for news, current events, or world happenings — use agent_news instead. "
        "Opens a full-screen military HUD animation.\n\n"
        "IMPORTANT — SYNCHRONIZE YOUR NARRATION WITH THE ANIMATION TIMELINE:\n"
        "The animation shows 7 timed phases. Describe each section AS IT APPEARS:\n"
        "1. 0–3s 'ACCESSING MEMORY DATABASE' — say 'Accessing memory database, sir...'\n"
        "2. 3–5.5s AUTH FRAME appears — say 'Identity confirmed, sir.' as brackets appear\n"
        "3. 5.5–13s PROFILE CARD visible (7.5s window) — describe the profile: name, "
        "nationality (Bangladeshi Bengali), creator, language, and any preferences\n"
        "4. 13–20s FACTS visible (7s window) — read out each fact one by one, "
        "say how many total are stored\n"
        "5. 20–25s PEOPLE visible (5s window) — introduce each person "
        "with their relationship role\n"
        "6. 25–30s LESSONS visible (5s window) — mention lessons you've learned "
        "from your sessions\n"
        "7. 30s+ STANDBY — wrap up: 'That's everything in my database, sir. "
        "It updates as we talk.'\n"
        "Speak conversationally as if walking them through your memory files. "
        "Always address as 'sir'. Stay aligned with each section's visible window."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

analyze_screen_tool = {
    "name": "analyze_screen",
    "description": "Take a screenshot of the COMPUTER MONITOR and analyze it with a custom prompt. Use ONLY when asked about the screen/monitor/display — NOT for seeing the user or surroundings. For seeing the user, use the live camera feed you already receive.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "What to ask about the screen (default: 'Describe what is on the screen in detail.')"}
        },
        "required": []
    }
}

read_screen_text_tool = {
    "name": "read_screen_text",
    "description": "Capture the screen and extract all visible text using Gemini vision OCR. Use when the user says 'read the screen', 'OCR this', 'copy text from screen', 'what does the error say', 'read the article'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

reminder_tool = {
    "name": "reminder",
    "description": "One-shot or recurring reminders. Actions: set, list, cancel.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Reminder action", "enum": ["set", "list", "cancel"]},
            "message": {"type": "STRING", "description": "What to remind about. Required for set."},
            "in_seconds": {"type": "INTEGER", "description": "Seconds from now (one-shot). For set."},
            "fire_at": {"type": "STRING", "description": "ISO 8601 timestamp. For set."},
            "recurring_seconds": {"type": "INTEGER", "description": "Recurring interval in seconds. For set."},
            "id": {"type": "STRING", "description": "Reminder ID. Required for cancel."}
        },
        "required": ["action"]
    }
}

schedule_tool = {
    "name": "schedule",
    "description": "Calendar schedule management. Actions: set (save event), list (all events), delete (remove event by ID).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Schedule action", "enum": ["set", "list", "delete"]},
            "title": {"type": "STRING", "description": "Event title. Required for set."},
            "date": {"type": "STRING", "description": "Date: 'tomorrow', 'today', 'YYYY-MM-DD'. Required for set."},
            "time": {"type": "STRING", "description": "Time in HH:MM format. Optional for set."},
            "details": {"type": "STRING", "description": "Additional details. Optional for set."},
            "id": {"type": "STRING", "description": "Schedule ID. Required for delete."}
        },
        "required": ["action"]
    }
}

show_calendar_tool = {
    "name": "show_calendar",
    "description": "Open the calendar floating window with an animated analog clock, month calendar grid, and all saved schedules. Use when the user says 'open calendar', 'show calendar', 'show my schedule', 'let me see the calendar', 'view my events'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

brief_me_day_tool = {
    "name": "brief_me_day",
    "description": (
        "Run the Jarvis-style MORNING BRIEFING: gather today's date, weather (Dhaka), "
        "today's schedule, reminders, unread emails, top news, and memory highlights, "
        "open a beautiful briefing panel in the HUD, and speak a concise summary. "
        "Use when the user greets in the morning, says 'good morning', 'brief me my day', "
        "'brief me today', 'what's on my schedule today', 'morning report', "
        "or when the scheduled 09:00 morning briefing fires."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

day_recap_tool = {
    "name": "day_recap",
    "description": (
        "Run the DAYTIME RECAP: summarize what has happened so far today (from the daily "
        "activity log), show remaining schedule and pending reminders, open a recap panel "
        "in the HUD, and speak a short summary. Use when the user says 'recap my day', "
        "'what have we done today', 'mid-day report', 'catch me up', "
        "or when the scheduled 13:00 recap fires."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

good_night_tool = {
    "name": "good_night",
    "description": (
        "Run the NIGHT WIND-DOWN: recap the full day (daily activity log), show tomorrow's "
        "first schedule and pending reminders, open a calm night overlay with breathing "
        "rings, then gracefully put SODA to sleep (minimize + idle). Use when the user "
        "says 'good night', 'wind down', 'recap and sleep', 'let's sleep', "
        "or when the scheduled 22:00 night recap fires."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

window_tool = {
    "name": "window",
    "description": "Manage desktop windows. Actions: focus (bring window to front by title), list (show all open windows), move (reposition/resize window).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Action to perform", "enum": ["focus", "list", "move"]},
            "title": {"type": "STRING", "description": "Window title (partial match). Required for focus and move."},
            "x": {"type": "INTEGER", "description": "New X position. Required for move."},
            "y": {"type": "INTEGER", "description": "New Y position. Required for move."},
            "width": {"type": "INTEGER", "description": "New width in pixels (optional). For move."},
            "height": {"type": "INTEGER", "description": "New height in pixels (optional). For move."}
        },
        "required": ["action"]
    }
}

control_system_tool = {
    "name": "control_system",
    "description": (
        "Control system volume and brightness only. "
        "Actions: volume_up, volume_down, volume_set (requires value 0-100), "
        "mute, unmute, toggle_mute, "
        "brightness_up, brightness_down, brightness_set (requires value). "
        "Do NOT use for opening or closing apps — use open_app or close_app tools instead. "
        "Use for: 'turn it up', 'turn it down', 'set volume to X', "
        "'mute', 'unmute', 'volume 50', 'volume 70 percent', "
        "'increase volume', 'decrease volume', 'louder', 'softer', "
        "'raise the volume', 'lower the volume'. "
        "Examples: control_system(action='volume_up'), "
        "control_system(action='volume_set', value=50)"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Action to perform"},
            "value": {"type": "STRING", "description": "Value for volume_set, brightness_set, open_app, type_text, press_key"}
        },
        "required": ["action"]
    }
}



# ── Face Auth ──

recognize_face_tool = {
    "name": "recognize_face",
    "description": "Take a photo from the camera and try to recognize any known face. Returns name and confidence if matched, otherwise 'Unknown'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

remember_face_tool = {
    "name": "remember_face",
    "description": "Take a photo and associate it with a person's name for future face recognition.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The person's name to associate with the captured face"}
        },
        "required": ["name"]
    }
}

# ── GitHub ──

github_tool = {
    "name": "github",
    "description": "GitHub operations via 'gh' CLI. Actions: list_repos, create_repo, get_repo, create_pr, list_issues, create_issue.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "GitHub action", "enum": ["list_repos", "create_repo", "get_repo", "create_pr", "list_issues", "create_issue"]},
            "owner": {"type": "STRING", "description": "GitHub username or org. For list_repos."},
            "name": {"type": "STRING", "description": "Repository name. For create_repo."},
            "repo": {"type": "STRING", "description": "Repository in 'owner/name' format. For get_repo, create_pr, list_issues, create_issue."},
            "description": {"type": "STRING", "description": "Description. For create_repo."},
            "private": {"type": "BOOLEAN", "description": "Private repo. For create_repo."},
            "auto_init": {"type": "BOOLEAN", "description": "Init with README. For create_repo."},
            "title": {"type": "STRING", "description": "PR or issue title. For create_pr, create_issue."},
            "body": {"type": "STRING", "description": "PR or issue body. For create_pr, create_issue."},
            "head": {"type": "STRING", "description": "Source branch. For create_pr."},
            "base": {"type": "STRING", "description": "Target branch (default: main). For create_pr."},
            "state": {"type": "STRING", "description": "Filter: 'open', 'closed', 'all'. For list_issues."}
        },
        "required": ["action"]
    }
}

# ── Vercel ──

vercel_tool = {
    "name": "vercel",
    "description": "Vercel deployment operations. Actions: list_projects, deploy, list_deployments, get_deployment.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Vercel action", "enum": ["list_projects", "deploy", "list_deployments", "get_deployment"]},
            "path": {"type": "STRING", "description": "Project directory path. For deploy."},
            "name": {"type": "STRING", "description": "Project name. For deploy."},
            "prod": {"type": "BOOLEAN", "description": "Deploy to production. For deploy."},
            "project": {"type": "STRING", "description": "Vercel project name. For list_deployments."},
            "limit": {"type": "INTEGER", "description": "Max deployments. For list_deployments."},
            "url_or_id": {"type": "STRING", "description": "Deployment URL or ID. For get_deployment."}
        },
        "required": ["action"]
    }
}

# ── Netlify ──

netlify_tool = {
    "name": "netlify",
    "description": "Netlify deployment operations. Actions: list_sites, get_site, deploy, create_site, list_deploys.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Netlify action", "enum": ["list_sites", "get_site", "deploy", "create_site", "list_deploys"]},
            "site_id": {"type": "STRING", "description": "Site ID. For get_site, list_deploys."},
            "path": {"type": "STRING", "description": "Build directory path. For deploy."},
            "prod": {"type": "BOOLEAN", "description": "Deploy to production. For deploy."},
            "message": {"type": "STRING", "description": "Deploy message. For deploy."},
            "name": {"type": "STRING", "description": "Site name. For create_site."}
        },
        "required": ["action"]
    }
}

# ── Notepad ──

notepad_open_tool = {
    "name": "notepad_open",
    "description": "Open SODA's INTERNAL floating notepad widget (a tabbed notes panel inside the SODA HUD window). "
                   "Use ONLY for storing notes, links, numbers, and progress during multi-step workflows. "
                   "This is NOT the Windows Notepad app. To open the real Windows Notepad app on the desktop, "
                   "use open_app(app_name='notepad') instead.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "tabs": {
                "type": "ARRAY",
                "description": "List of tab objects, each with 'name' and 'content'",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "description": "Tab name"},
                        "content": {"type": "STRING", "description": "Tab content"}
                    }
                }
            }
        },
        "required": []
    }
}

notepad_write_tool = {
    "name": "notepad_write",
    "description": "Write content to a tab of SODA's INTERNAL floating notepad widget (NOT the Windows Notepad app). "
                   "If the tab doesn't exist, it will be created. "
                   "Use ONLY for storing notes/links/progress in the HUD during workflows. "
                   "To type text into a real desktop app window (e.g. Windows Notepad, a browser, Word), "
                   "use type_into or keyboard_type instead.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "tab": {"type": "STRING", "description": "Tab name"},
            "content": {"type": "STRING", "description": "Content to write"},
            "mode": {"type": "STRING", "description": "'append' or 'overwrite' (default: append)"}
        },
        "required": ["tab", "content"]
    }
}

notepad_read_tool = {
    "name": "notepad_read",
    "description": "Read the content of a tab of SODA's INTERNAL floating notepad widget (NOT the Windows Notepad app).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "tab": {"type": "STRING", "description": "Tab name to read"}
        },
        "required": ["tab"]
    }
}

# ── View ──

view_file_tool = {
    "name": "view_file",
    "description": "View a file's content in a popup preview window. Supports images, text, code, and PDFs.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "Path to the file to view"}
        },
        "required": ["path"]
    }
}

file_manager_tool = {
    "name": "file_manager",
    "description": "File system operations. Actions: create_folder, delete_items, rename_item, copy_item, move_item, list_drives, scroll_file_list.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "File manager action", "enum": ["create_folder", "delete_items", "rename_item", "copy_item", "move_item", "list_drives", "scroll_file_list"]},
            "path": {"type": "STRING", "description": "File/folder path. For create_folder."},
            "paths": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of paths. For delete_items, copy_item, move_item."},
            "source": {"type": "STRING", "description": "Source path. For rename_item, copy_item, move_item."},
            "destination": {"type": "STRING", "description": "Destination path. For rename_item, copy_item, move_item."},
            "new_name": {"type": "STRING", "description": "New name. For rename_item."},
            "direction": {"type": "STRING", "description": "Scroll direction: 'up' or 'down'. For scroll_file_list."},
            "amount": {"type": "INTEGER", "description": "Scroll amount in pixels. For scroll_file_list."}
        },
        "required": ["action"]
    }
}

start_website_project_tool = {
    "name": "start_website_project",
    "description": "FIRST STEP to build a website. Call this when the user says 'build a website', 'make a site', 'create a landing page', etc. Returns a question that you MUST read aloud to the user. After they reply verbally, call web_builder_answer with what they said. Keep going back and forth until the interview is done, then the build starts automatically.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

web_builder_answer_tool = {
    "name": "web_builder_answer",
    "description": "SECOND STEP of website building. Call this after the user answers a question from the website builder interview. Pass the user's exact words as 'answer'. Returns the NEXT question to ask them, or says 'Build started!' when the interview is done. Keep calling this after each answer until the build begins.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "answer": {
                "type": "STRING",
                "description": "The user's exact answer to the interview question. Pass their words verbatim."
            }
        },
        "required": ["answer"]
    }
}

show_agents_tool = {
    "name": "show_agents",
    "description": "Show all available SODA sub-agents with their names, roles, status, capabilities, and task activity. Returns a structured list of agent identity cards. Use when the user asks 'what agents do you have', 'show me your agents', 'who are your helpers', 'list all agents', or wants to know about available sub-agents.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

# ── Task Planner ──

plan_tool = {
    "name": "plan",
    "description": "Multi-step task planner. Actions: create (new plan with tasks), get (current plan), update (change task status), cancel (dismiss plan).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Plan action", "enum": ["create", "get", "update", "cancel"]},
            "title": {"type": "STRING", "description": "Plan title. Required for create."},
            "tasks": {
                "type": "ARRAY",
                "description": "List of {title, description} objects. Required for create.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING", "description": "Task title"},
                        "description": {"type": "STRING", "description": "Task description"}
                    }
                }
            },
            "task_id": {"type": "STRING", "description": "Task ID. Required for update."},
            "status": {"type": "STRING", "description": "New status: 'running', 'done', 'failed'. Required for update."},
            "result": {"type": "STRING", "description": "Result description. Optional for update."}
        },
        "required": ["action"]
    }
}

# ── WhatsApp ──

whatsapp_find_and_call_tool = {
    "name": "whatsapp_find_and_call",
    "description": (
        "Find a contact in WhatsApp Desktop and initiate a voice call. "
        "Use when the user says 'call [name]', 'WhatsApp call [name]', or 'call [name] on WhatsApp'. "
        "If the user gives a relationship (e.g. 'call my sister'), first call recall_by_relationship "
        "to find the person's name, then call this tool with that name. "
        "If the user gives a name directly (e.g. 'call Rubab'), call this tool immediately. "
        "Opens WhatsApp Desktop automatically if not running. "
        "Example: whatsapp_find_and_call(contact_name='Rubab')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "contact_name": {"type": "STRING", "description": "Exact contact name to search and call in WhatsApp"}
        },
        "required": ["contact_name"]
    }
}

whatsapp_find_and_message_tool = {
    "name": "whatsapp_find_and_message",
    "description": (
        "Find a contact in WhatsApp Desktop and send them a text message. "
        "Use when the user says 'WhatsApp [name] saying [message]', 'tell [name] [message] on WhatsApp', "
        "'send WhatsApp to [name]', 'message [name]', 'text [name]'. "
        "If the user gives a relationship (e.g. 'message my sister'), first call recall_by_relationship "
        "to find the person's name, then call this tool with that name. "
        "If the user gives a name and message directly, call this tool immediately. "
        "Opens WhatsApp Desktop automatically, searches the contact, types and sends the message. "
        "Requires both contact_name and message. "
        "Example: whatsapp_find_and_message(contact_name='Rubab', message='Hey, how are you?')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "contact_name": {"type": "STRING", "description": "Exact contact name to search in WhatsApp"},
            "message": {"type": "STRING", "description": "The full message text to send"}
        },
        "required": ["contact_name", "message"]
    }
}

check_whatsapp_tool = {
    "name": "check_whatsapp",
    "description": (
        "READ WhatsApp messages from the user's screen. Opens WhatsApp Desktop automatically, "
        "captures a screenshot of the chat list, analyzes it with AI Vision, and returns "
        "any unread messages found — including contact name, last message preview, and unread count. "
        "THIS TOOL WORKS. It physically screenshots the WhatsApp window and reads text from it. "
        "Use for ANY request about reading/checking WhatsApp messages including: "
        "'check my WhatsApp', 'any WhatsApp messages', 'read my WhatsApp', "
        "'open WhatsApp and read messages', 'did I get any messages', 'check WhatsApp', "
        "'any new messages on WhatsApp', 'what's on WhatsApp', 'see my WhatsApp'. "
        "If no unread messages, returns 'No unread messages'. "
        "Example: check_whatsapp(query='any messages')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "What to check for. Always pass 'check messages'."}
        },
        "required": ["query"]
    }
}

reply_whatsapp_tool = {
    "name": "reply_whatsapp",
    "description": (
        "Reply to an existing WhatsApp chat. Opens the chat by contact name in WhatsApp Desktop, "
        "types the message, and sends it. Use after check_whatsapp when the user says 'reply to [name]', "
        "'respond to [name]', 'tell [name] back', 'send [name] a reply'. "
        "Requires contact_name (the exact name as shown in chat list) and message (the reply text). "
        "Opens WhatsApp Desktop automatically. "
        "Example: reply_whatsapp(contact_name='Rubab', message='On my way!')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "contact_name": {"type": "STRING", "description": "Exact contact name from the chat list to reply to"},
            "message": {"type": "STRING", "description": "The reply message text to send"}
        },
        "required": ["contact_name", "message"]
    }
}

read_whatsapp_chat_tool = {
    "name": "read_whatsapp_chat",
    "description": (
        "READ a specific contact's WhatsApp conversation. Opens WhatsApp Desktop automatically, "
        "searches for the contact, opens their chat, takes a screenshot of the conversation area, "
        "and uses AI Vision to read and describe the recent messages visible. "
        "THIS TOOL WORKS — it physically screenshots the WhatsApp window and reads text from it. "
        "Use when the user says 'open [name] WhatsApp', 'show me my chat with [name]', "
        "'what did [name] say', 'read my conversation with [name]', "
        "'open WhatsApp and show [name]', 'let me see [name]'s messages'. "
        "Optionally sends a message after reading if 'message' parameter is provided. "
        "contact_name is required (the exact name). message is optional. "
        "Example: read_whatsapp_chat(contact_name='Rubab')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "contact_name": {"type": "STRING", "description": "Exact contact name to open and read chat from"},
            "message": {"type": "STRING", "description": "Optional message to send after reading the chat"}
        },
        "required": ["contact_name"]
    }
}

browser_command_tool = {
    "name": "browser_command",
    "description": (
        "Open a URL or search the web in the user's DEFAULT SYSTEM BROWSER (Chrome/Edge/Firefox). "
        "Use action='open' with a url to open a specific website, or action='search' with a query "
        "to search Google. "
        "Use when the user says 'open Chrome and search for [query]', 'Google [query]', "
        "'search for [query] in Chrome', 'open [url] in Chrome', 'browse to [url]'. "
        "Only use this when the user explicitly wants to use the system browser — "
        "for internal SODA webview, use open_browser instead. "
        "Do NOT use this for checking Gmail/email — use the read_emails tool instead (IMAP-based). "
        "Examples: browser_command(action='search', query='cat pictures'), "
        "browser_command(action='open', url='https://youtube.com')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "'search' to search Google, 'open' to open a URL"},
            "url": {"type": "STRING", "description": "Full URL to open (required if action='open')"},
            "query": {"type": "STRING", "description": "Search query (required if action='search')"}
        },
        "required": ["action"]
    }
}

search_youtube_tool = {
    "name": "search_youtube",
    "description": (
        "Search YouTube for videos and return structured results with titles and video URLs. "
        "Use this INSTEAD of app_search for YouTube — it returns actual video data "
        "(titles, URLs), not AI vision descriptions. "
        "WORKFLOW:\n"
        "1. Call search_youtube(query='...') to search — returns numbered results.\n"
        "2. Present the results to the user: 'I found: 1. Title, 2. Title...'\n"
        "3. When user says 'play number N' or 'open the Nth video', find the URL from the results "
        "and call browser_command(action='open', url=result_url) to open it — this routes to your local agent.\n"
        "Examples:\n"
        "- search_youtube(query='python tutorial') → returns results list\n"
        "- Then: browser_command(action='open', url='https://youtube.com/watch?v=VIDEO_ID') → plays video"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "Search query for YouTube"
            }
        },
        "required": ["query"]
    }
}

app_search_tool = {
    "name": "app_search",
    "description": (
        "Search inside a NON-YOUTUBE desktop app (Spotify, browser, etc.) using keyboard automation. "
        "DO NOT use this for YouTube — use search_youtube instead for YouTube searches. "
        "Opens or focuses the app, types a keyboard shortcut to activate the search bar, "
        "types the query, presses Enter, then takes a screenshot and uses AI Vision "
        "to read and describe the search results. "
        "Use when the user says 'search [query] in Spotify', "
        "'look up [query] in [app]'. "
        "For most apps, the search key is 'Ctrl+F'. "
        "If no search_key is provided, defaults to '/'. "
        "The result includes an 'analysis' field with what AI Vision saw on screen. "
        "After returning, the user may ask to scroll or open a specific result. "
        "Examples: app_search(app_name='Spotify', search_key='Ctrl+F', query='lofi beats')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {"type": "STRING", "description": "Name of the app to search in (e.g. 'Spotify', 'Chrome')"},
            "query": {"type": "STRING", "description": "The search query text"},
            "search_key": {"type": "STRING", "description": "Keyboard shortcut to activate search bar. Default '/'."}
        },
        "required": ["app_name", "query"]
    }
}

app_scroll_tool = {
    "name": "app_scroll",
    "description": (
        "Scroll up or down inside a specific desktop app window. "
        "Focuses the app by name, then scrolls by the specified amount. "
        "Use AFTER app_search when the user says 'scroll down', 'scroll up', "
        "'show more results', 'go down', 'scroll further'. "
        "direction is 'down' or 'up'. amount is number of scroll clicks (default 5, higher = more scroll). "
        "After scrolling, takes a screenshot of the window and uses AI Vision "
        "to read what's visible. Returns analysis of what's now on screen. "
        "Examples: app_scroll(app_name='YouTube', direction='down'), "
        "app_scroll(app_name='YouTube', direction='down', amount=10)"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {"type": "STRING", "description": "Name of the app window to scroll in"},
            "direction": {"type": "STRING", "description": "'down' or 'up'"},
            "amount": {"type": "INTEGER", "description": "Number of scroll clicks. Higher = more scroll. Default 5."}
        },
        "required": ["app_name", "direction"]
    }
}

# ── Credential Manager ──

credential_tool = {
    "name": "credential",
    "description": "Encrypted credential manager. Actions: save (store login), get (retrieve login), list (all saved services), delete (remove service).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Credential action", "enum": ["save", "get", "list", "delete"]},
            "service": {"type": "STRING", "description": "Service name (e.g. 'facebook', 'gmail'). Required for save, get, delete."},
            "username": {"type": "STRING", "description": "Username or email. Required for save."},
            "password": {"type": "STRING", "description": "Password. Required for save."}
        },
        "required": ["action"]
    }
}

# ── Scheduled Tasks (recurring) ──

scheduled_task_tool = {
    "name": "scheduled_task",
    "description": "Recurring automated tasks (like cron). Actions: create, list, delete. For calendar events, use 'schedule' tool instead.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Action", "enum": ["create", "list", "delete"]},
            "action_text": {"type": "STRING", "description": "What to do. Required for create."},
            "schedule": {"type": "STRING", "description": "Human-readable schedule like 'every day at 9am'. Required for create."},
            "label": {"type": "STRING", "description": "Short label. Optional for create."},
            "task_id": {"type": "STRING", "description": "Task ID. Required for delete."}
        },
        "required": ["action"]
    }
}

# ── Screen Control (Mouse & Keyboard) ──

mouse_click_tool = {
    "name": "mouse_click",
    "description": "Click at a specific screen coordinate. Use after moving the mouse. Supports left, right, middle buttons and multiple clicks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "x": {"type": "INTEGER", "description": "X screen coordinate"},
            "y": {"type": "INTEGER", "description": "Y screen coordinate"},
            "button": {"type": "STRING", "description": "Mouse button: 'left', 'right', 'middle'"},
            "clicks": {"type": "INTEGER", "description": "Number of clicks (1 for single, 2 for double)"}
        },
        "required": ["x", "y"]
    }
}

mouse_move_tool = {
    "name": "mouse_move",
    "description": "Move the mouse cursor to a specific screen coordinate smoothly.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "x": {"type": "INTEGER", "description": "X screen coordinate"},
            "y": {"type": "INTEGER", "description": "Y screen coordinate"},
            "duration": {"type": "NUMBER", "description": "Duration of the movement in seconds"}
        },
        "required": ["x", "y"]
    }
}

mouse_scroll_tool = {
    "name": "mouse_scroll",
    "description": "Scroll the mouse wheel. Positive amount scrolls down, negative scrolls up.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "amount": {"type": "INTEGER", "description": "Scroll amount (positive=down, negative=up)"}
        },
        "required": ["amount"]
    }
}

mouse_drag_tool = {
    "name": "mouse_drag",
    "description": "Click and drag from one coordinate to another.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "start_x": {"type": "INTEGER", "description": "Starting X coordinate"},
            "start_y": {"type": "INTEGER", "description": "Starting Y coordinate"},
            "end_x": {"type": "INTEGER", "description": "Ending X coordinate"},
            "end_y": {"type": "INTEGER", "description": "Ending Y coordinate"},
            "duration": {"type": "NUMBER", "description": "Duration of the drag in seconds"}
        },
        "required": ["start_x", "start_y", "end_x", "end_y"]
    }
}

keyboard_type_tool = {
    "name": "keyboard_type",
    "description": "Type text at the current cursor position.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to type"},
            "interval": {"type": "NUMBER", "description": "Delay between keystrokes in seconds"}
        },
        "required": ["text"]
    }
}

keyboard_press_tool = {
    "name": "keyboard_press",
    "description": "Press a key or key combination (e.g. 'enter', 'ctrl+c', 'alt+tab').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "keys": {"type": "STRING", "description": "Key or key combination to press"}
        },
        "required": ["keys"]
    }
}

click_element_tool = {
    "name": "click_element",
    "description": "Click a UI element described in natural language (e.g. 'the Submit button', 'the search box', 'the login link'). "
                   "Uses AI vision to find the element on screen — no coordinates needed. "
                   "PREFER this over mouse_click(x,y) when you know what to click but not the exact coordinates.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "description": {"type": "STRING", "description": "Natural language description of the element to click"}
        },
        "required": ["description"]
    }
}

type_into_tool = {
    "name": "type_into",
    "description": "Type text into a UI element. Optionally describe the element (e.g. 'the email field', 'the search bar') — "
                   "AI vision finds it and clicks it first, then types. If description is omitted, types at the current cursor position. "
                   "PREFER this over keyboard_type when you need to type into a specific field.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to type"},
            "description": {"type": "STRING", "description": "Optional: description of the element to type into"}
        },
        "required": ["text"]
    }
}

find_element_tool = {
    "name": "find_element",
    "description": "Find a UI element on screen by description and return its coordinates. "
                   "Useful when you need to know where something is before interacting with it.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "description": {"type": "STRING", "description": "Natural language description of the element to find"}
        },
        "required": ["description"]
    }
}

open_app_tool = {
    "name": "open_app",
    "description": "Open an installed application instantly. Uses a pre-built app registry of all installed apps "
                   "(Start Menu, Microsoft Store, PATH, registry). Provide the app name as the user says it. "
                   "If unsure what apps are available, call list_installed_apps first. "
                   "For example: 'open whatsapp', 'launch calculator', 'start chrome'. "
                   "Do NOT use execute_command for opening apps — use this tool instead.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {
                "type": "STRING",
                "description": "Name of the app to open (e.g. 'whatsapp', 'notepad', 'calculator', 'chrome')"
            }
        },
        "required": ["app_name"]
    }
}

list_installed_apps_tool = {
    "name": "list_installed_apps",
    "description": "List all installed applications on the user's Windows PC. "
                   "Returns up to 200 apps with their names. Use this when the user asks "
                   "'what apps do I have?' or 'list my installed programs'. "
                   "After listing, you can open any app with open_app.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "search": {
                "type": "STRING",
                "description": "Optional search term to filter apps (e.g. 'chrome', 'adobe', 'micro')"
            }
        }
    }
}

webview_action_tool = {
    "name": "webview_action",
    "description": "Interact with a webview window that's currently open in SODA. Use for actions like clicking elements, typing text, scrolling, navigating, or running JavaScript inside an open webview. Requires a valid webview ID (from open_browser or similar).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "id": {
                "type": "STRING",
                "description": "The webview instance ID (e.g. from open_browser or previous webview_action responses)."
            },
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'click' (click a CSS selector), 'type' (type text into an input), 'scroll' (scroll by x,y pixels), 'getContent' (get page text/links/URL), 'getUrl' (get current URL), 'goBack' / 'goForward' (navigation), 'navigate' (load a new URL), 'waitForLoad' (wait for page load), 'executeJS' (run JS code)."
            },
            "params": {
                "type": "STRING",
                "description": "JSON string of action-specific parameters. For 'click': {\"selector\": \"#button\"}. For 'type': {\"selector\": \"#input\", \"text\": \"hello\"}. For 'navigate': {\"url\": \"https://...\"}. For 'executeJS': {\"code\": \"document.title\"}. For 'scroll': {\"x\": 0, \"y\": 100}."
            }
        },
        "required": ["id", "action"]
    }
}

take_photo_tool = {
    "name": "take_photo",
    "description": "Capture a live photo from the camera and send it to the AI for visual analysis. "
                   "Use when the user asks about their surroundings, what you see, "
                   "or any question that requires a live camera view. "
                   "This replaces the old automatic continuous photo capture.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

open_camera_tool = {
    "name": "open_camera",
    "description": "Open a FULL-SCREEN live camera view on the user's screen with a 'Camera On' label. "
                   "Call this when the user says 'open the camera', 'show me the camera', "
                   "'turn on the camera', or wants to take a photo or see themselves. "
                   "While it is open you receive a continuous live video feed — you can see the user in real time. "
                   "After opening, use camera_control to capture, analyze, save, switch, or close.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

camera_control_tool = {
    "name": "camera_control",
    "description": "Control the live camera view after it is open. "
                   "snapshot = capture current frame silently for you to see. "
                   "analyze = capture current frame and describe what you see to the user. "
                   "save = capture current frame and store it in the database with a description. "
                   "switch = toggle between front and back camera. "
                   "close = close the full-screen camera view. "
                   "Use analyze when the user asks 'what do you see', 'what's in front of me', "
                   "or anything requiring visual description. "
                   "Use snapshot for silent capture without commentary. "
                   "Use save when the user says 'save this photo' or 'remember this image'. "
                   "Use switch when the user says 'switch camera', 'back camera', 'selfie'. "
                   "Use close when the user says 'close the camera' or 'turn off the camera'. "
                   "Do NOT ask for permission — just call the appropriate action.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform. One of: snapshot, analyze, save, switch, close"
            },
            "description": {
                "type": "STRING",
                "description": "Description of the photo (required when action is save)"
            }
        },
        "required": ["action"]
    }
}

pentest_target_tool = {
    "name": "pentest_target",
    "description": (
        "Run a full penetration testing pipeline against a target (IP, domain, or URL). "
        "This runs nmap, whois, dnsrecon, whatweb, gobuster, nikto, searchsploit, "
        "theHarvester, sublist3r, and vulnerability scanning automatically. "
        "Results are compiled into a report with risk breakdown and recommendations. "
        "Use when the user asks to 'pentest', 'hack', 'scan', 'test security', "
        "'penetration test', or 'check vulnerabilities' on a target. "
        "HIGH RISK: This tool actively probes the target. Only call when user explicitly provides a target."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "Target IP address, domain name, or URL to test"
            },
            "scan_type": {
                "type": "STRING",
                "description": "Scan type: 'auto' (default, detects playbook from target type), 'quick' (fast scan)"
            }
        },
        "required": ["target"]
    }
}

pentest_browser_target_tool = {
    "name": "pentest_browser_target",
    "description": (
        "Run a full penetration test on the URL currently open in the user's browser/webview. "
        "This grabs the current page URL from the frontend and runs the full pentest pipeline "
        "(nmap, whois, dnsrecon, whatweb, gobuster, nikto, theHarvester, searchsploit) on it. "
        "Use ONLY when the user says 'pentest this', 'test this site', 'hack this website', "
        "'check this URL', or 'scan the current page'. "
        "Do NOT use if the user specifies a target by name — use pentest_target instead."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

# ── Research Engine V2 ──────────────────────────────────────
deep_research_tool = {
    "name": "deep_research",
    "description": "Perform deep multi-source research on a topic. Searches web, scrapes pages, and synthesizes findings with charts and statistics. Use for market research, competitive analysis, topic investigation.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "topic": {"type": "STRING", "description": "Research topic or question"},
            "depth": {"type": "STRING", "description": "'quick' (search only), 'normal' (search + top pages), or 'deep' (full synthesis with charts)"},
        },
        "required": ["topic"]
    }
}

export_research_tool = {
    "name": "export_research",
    "description": "Export research results from deep_research to JSON or Markdown format.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "research_data": {"type": "STRING", "description": "The full result JSON string from deep_research"},
            "format": {"type": "STRING", "description": "Export format: 'json' or 'markdown'"}
        },
        "required": ["research_data", "format"]
    }
}

# ── Background Agent Management ─────────────────────────────
bg_tasks_tool = {
    "name": "bg_tasks",
    "description": "Background task management. Actions: spawn (run task async), status (check task), kill (terminate task), list (all tasks).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "BG task action", "enum": ["spawn", "status", "kill", "list"]},
            "prompt": {"type": "STRING", "description": "Task prompt. Required for spawn."},
            "workdir": {"type": "STRING", "description": "Working directory. Optional for spawn."},
            "task_id": {"type": "STRING", "description": "Task ID. Required for status and kill."}
        },
        "required": ["action"]
    }
}

# ── OpenCode Remote Tasks ────────────────────────────────────
opencode_tool = {
    "name": "opencode",
    "description": "OpenCode remote task management. Actions: start (launch session), status (check task), stop (kill task).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "OpenCode action", "enum": ["start", "status", "stop"]},
            "folder": {"type": "STRING", "description": "Project folder path. Required for start."},
            "prompt": {"type": "STRING", "description": "Task prompt. Required for start."},
            "task_id": {"type": "STRING", "description": "Task ID. Required for status and stop."}
        },
        "required": ["action"]
    }
}

notebook_read_tool = {
    "name": "notebook_read",
    "description": "Read a past OpenCode task result from the notebook. Returns the full task record including output summary.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task_id": {"type": "STRING", "description": "The task ID to read"},
        },
        "required": ["task_id"]
    }
}

notebook_search_tool = {
    "name": "notebook_search",
    "description": "Search the OpenCode notebook by keyword. Returns matching task records.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "keyword": {"type": "STRING", "description": "Search keyword (matches prompt and output)"},
        },
        "required": ["keyword"]
    }
}



email_tool = {
    "name": "email",
    "description": "Gmail email management. Actions: read (inbox via IMAP), send (via SMTP), config (set credentials). Do NOT use browser for email.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Email action", "enum": ["read", "send", "config"]},
            "query": {"type": "STRING", "description": "IMAP search: 'UNSEEN', 'ALL', 'FROM x', 'SUBJECT x'. For read."},
            "max_results": {"type": "INTEGER", "description": "Max emails (default 10). For read."},
            "to": {"type": "STRING", "description": "Recipient email. Required for send."},
            "subject": {"type": "STRING", "description": "Subject line. Required for send."},
            "body": {"type": "STRING", "description": "Body text. Required for send."},
            "address": {"type": "STRING", "description": "Gmail address. Required for config."},
            "password": {"type": "STRING", "description": "App Password. Required for config."}
        },
        "required": ["action"]
    }
}

create_memory_schema_tool = {
    "name": "create_memory_schema",
    "description": (
        "Create a new custom memory schema for storing structured data about a recurring topic. "
        "Use this when the user mentions a topic that would benefit from structured memory "
        "(e.g. projects, books, movies, recipes, contacts, vehicles, collections). "
        "Define the columns you need as a list of {name, type, description} objects. "
        "Example: create_memory_schema(name='books', description='Books I want to read', "
        "columns=[{name='title', type='string', description='Book title'}, "
        "{name='author', type='string', description='Author name'}, "
        "{name='status', type='string', description='Reading status'}])"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "Schema name (e.g. 'books', 'projects', 'recipes')"},
            "description": {"type": "STRING", "description": "What this schema stores"},
            "columns": {
                "type": "ARRAY",
                "description": "List of column definitions, each with name (string), type (string), and description (string)",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "description": "Column name"},
                        "type": {"type": "STRING", "description": "Data type: 'string', 'number', 'boolean', 'date', 'json'"},
                        "description": {"type": "STRING", "description": "What this column stores"}
                    },
                    "required": ["name", "type"]
                }
            }
        },
        "required": ["name", "columns"]
    }
}

list_custom_schemas_tool = {
    "name": "list_custom_schemas",
    "description": "List all custom memory schemas. Returns schema names, descriptions, and column definitions. Use when the user asks 'what schemas do I have', 'show my memory schemas', 'what topics can I store data about'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

store_custom_memory_tool = {
    "name": "store_custom_memory",
    "description": (
        "Store a structured data entry in a custom memory schema. "
        "Use after creating a schema with create_memory_schema. "
        "Pass data as a JSON string matching the schema's column definitions. "
        "Example: store_custom_memory(schema_name='books', data='{\"title\":\"1984\",\"author\":\"George Orwell\",\"status\":\"want to read\"}')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "schema_name": {"type": "STRING", "description": "Name of the schema to store data in"},
            "data": {
                "type": "STRING",
                "description": "JSON string of key-value pairs matching the schema's column definitions. Example: '{\"title\":\"1984\",\"author\":\"George Orwell\"}'"
            }
        },
        "required": ["schema_name", "data"]
    }
}

query_custom_memory_tool = {
    "name": "query_custom_memory",
    "description": "Query entries from a custom memory schema. Returns matching entries with their stored data. Empty query returns all recent entries. Use when the user asks 'what books do I have', 'show me my recipes', 'find projects about X'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "schema_name": {"type": "STRING", "description": "Schema name to query"},
            "query": {"type": "STRING", "description": "Search text to filter entries by (optional, case-insensitive)"},
            "limit": {"type": "INTEGER", "description": "Max entries to return (default 20)"}
        },
        "required": ["schema_name"]
    }
}

# ── Project Registry ──

project_registry_tool = {
    "name": "project_registry",
    "description": "External project registration and analytics. Actions: register, list, query, query_all, remove.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Registry action", "enum": ["register", "list", "query", "query_all", "remove"]},
            "name": {"type": "STRING", "description": "Project name. Required for register."},
            "endpoint": {"type": "STRING", "description": "Project stats endpoint URL. Required for register."},
            "project_id": {"type": "STRING", "description": "Project ID. Required for query and remove."}
        },
        "required": ["action"]
    }
}

# ── World Monitor Controller ──

open_world_monitor_tool = {
    "name": "open_world_monitor",
    "description": "Opens the World Monitor global intelligence dashboard in fullscreen. MUST be called before navigate_world_monitor. Use when user says 'open the controller', 'open world map', 'show me the world', 'open the dashboard', 'show global map', 'open world monitor', 'what's happening in the world', or any variation of wanting to see the world monitor dashboard.",
    "parameters": {"type": "OBJECT", "properties": {}, "required": []}
}

navigate_world_monitor_tool = {
    "name": "navigate_world_monitor",
    "description": "Switches to a specific section inside the World Monitor controller. ONLY call this AFTER open_world_monitor has been called. Sections: map (default overview), wire (news feed), globe (3D view), stocks (markets), chat (analyst), predictions (forecasts), cameras (live feeds), defcon (threat level), outbreaks (disease tracking), streams (live data).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "section": {
                "type": "STRING",
                "enum": ["map", "wire", "globe", "stocks", "chat", "predictions", "cameras", "defcon", "outbreaks", "streams"],
                "description": "Which section to navigate to"
            }
        },
        "required": ["section"]
    }
}

get_world_monitor_data_tool = {
    "name": "get_world_monitor_data",
    "description": "Fetches live data from the World Monitor dashboard panels. Use this to EXPLAIN what's happening in the world to the user. Returns real-time data for: stocks (market overview, top movers, sector performance), war (active conflicts, casualty counts, recent events), outbreaks (disease tracking, affected regions), defcon (military alert levels, force posture), earthquakes (recent seismic activity), economy (economic indicators), predictions (prediction market odds). ALWAYS use this tool BEFORE web search when the user asks about world events, markets, conflicts, or global situation. The data comes from the same sources as the World Monitor dashboard.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "section": {
                "type": "STRING",
                "enum": ["stocks", "war", "outbreaks", "defcon", "earthquakes", "economy", "predictions", "all"],
                "description": "Which data to fetch. Use 'all' for a general world overview."
            }
        },
        "required": ["section"]
    }
}



tools_list = [{"function_declarations": [
    write_file_tool,
    read_file_tool,
    edit_file_tool,
    execute_command_tool,
    terminal_execute_tool,
    weather_tool,
    ip_info_tool,
    exchange_tool,
    get_bangladeshi_news_tool,
    define_word_tool,
    open_browser_tool,
    *get_agent_tool_defs(),
    list_files_tool,
    open_file_tool,
    close_panel_tool,
    system_status_tool,
    close_window_tool,
    screenshot_tool,
    list_processes_tool,
    get_active_window_tool,
    run_code_tool,
    remember_fact_tool,
    recall_facts_tool,
    get_user_profile_tool,
    set_preference_tool,
    remember_person_tool,
    recall_person_tool,
    recall_by_relationship_tool,
    remember_lesson_tool,
    forget_fact_tool,
    list_memory_tool,
    show_memory_tool,
    analyze_screen_tool,
    read_screen_text_tool,
    reminder_tool,
    schedule_tool,
    show_calendar_tool,
    brief_me_day_tool,
    day_recap_tool,
    good_night_tool,
    recognize_face_tool,
    remember_face_tool,
    plan_tool,
    github_tool,
    vercel_tool,
    netlify_tool,
    notepad_open_tool,
    notepad_write_tool,
    notepad_read_tool,
    view_file_tool,
    mouse_click_tool,
    mouse_move_tool,
    mouse_scroll_tool,
    mouse_drag_tool,
    keyboard_type_tool,
    keyboard_press_tool,
    click_element_tool,
    type_into_tool,
    find_element_tool,
    window_tool,
    file_manager_tool,
    scrape_site_tool,
    export_data_tool,
    get_pagespeed_insights_tool,
    show_agents_tool,
    start_website_project_tool,
    web_builder_answer_tool,
    workbase_tool,
    whatsapp_find_and_call_tool,
    whatsapp_find_and_message_tool,
    check_whatsapp_tool,
    reply_whatsapp_tool,
    read_whatsapp_chat_tool,
    scheduled_task_tool,
    open_app_tool,
    list_installed_apps_tool,
    webview_action_tool,
    take_photo_tool,
    open_camera_tool,
    camera_control_tool,
    control_system_tool,
    *FEELINGS_TOOLS_SCHEMA,
    *IELTS_TOOLS,
    pentest_target_tool,
    pentest_browser_target_tool,
    browser_command_tool,
    search_youtube_tool,
    app_search_tool,
    app_scroll_tool,
    credential_tool,

    # ── Research Engine V2 ──
    deep_research_tool,
    export_research_tool,

    # ── Background Agent Management ──
    bg_tasks_tool,

    # ── OpenCode Remote Tasks ──
    opencode_tool,
    notebook_read_tool,
    notebook_search_tool,

    email_tool,

    # ── Custom Memory Schemas ──
    create_memory_schema_tool,
    list_custom_schemas_tool,
    store_custom_memory_tool,
    query_custom_memory_tool,

    # ── Project Registry ──
    project_registry_tool,

    # ── World Monitor Controller ──
    open_world_monitor_tool,
    navigate_world_monitor_tool,
    get_world_monitor_data_tool,

    # ── Hermes Agent (AI-powered desktop control) ──
    {
        "name": "hermes_execute",
        "description": (
            "Execute a desktop task using Hermes Agent AI. "
            "Use this for complex multi-step tasks like: opening an app and performing actions, "
            "automating WhatsApp messages, reading screen content, controlling desktop apps, "
            "or any task that requires visual understanding of the screen. "
            "Hermes Agent uses computer_use to see and interact with the desktop in the background."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The desktop task to execute. Be specific about what to do. Examples: 'Open WhatsApp, search for John, and send hello', 'Open Notepad and type today's date', 'Take a screenshot and tell me what's on screen'",
                },
            },
            "required": ["task"],
        },
    },

]}]

