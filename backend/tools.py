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
    go_to_sleep_tool,
    wake_up_tool,
    send_telegram_message_tool,
    send_telegram_file_tool,
    search_and_send_telegram_tool,
    create_folder_tool,
    show_agents_tool,
    shutdown_soda_tool,
    delete_items_tool,
    get_pagespeed_insights_tool,
    rename_item_tool,
    copy_item_tool,
    move_item_tool,
    list_drives_tool,
    scroll_file_list_tool,
    scrape_site_tool,
    export_data_tool,
    get_pagespeed_insights_tool,
)
from soda_agents import get_agent_tool_defs
from workbase import (
    workbase_list_tool,
    workbase_get_tool,
    workbase_save_progress_tool,
    workbase_import_tool,
    workbase_save_context_tool,
    workbase_compare_tool,
)
from ielts_tools import IELTS_TOOLS
from feelings_tools import FEELINGS_TOOLS_SCHEMA

clipboard_read_tool = {
    "name": "clipboard_read",
    "description": "Read text content from the system clipboard. Use when the user says 'what's on my clipboard', 'paste the latest', 'show clipboard', 'I copied something, read it'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

clipboard_write_tool = {
    "name": "clipboard_write",
    "description": "Write text to the system clipboard. Use when the user says 'copy this to clipboard', 'put this on my clipboard', 'clipboard this', 'I need to paste this later'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to put on the clipboard"}
        },
        "required": ["text"]
    }
}

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

set_reminder_tool = {
    "name": "set_reminder",
    "description": "Schedule a one-shot or recurring reminder. Use when the user says 'remind me in 10 minutes to...', 'remind me at 3pm to call John', 'every hour remind me to stretch', 'alert me when...'. Times are ISO 8601 (e.g. '2026-06-03T15:30:00').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "message": {"type": "STRING", "description": "What to remind the user about"},
            "in_seconds": {"type": "INTEGER", "description": "How many seconds from now to fire (one-shot)"},
            "fire_at": {"type": "STRING", "description": "ISO 8601 timestamp for one-shot reminders"},
            "recurring_seconds": {"type": "INTEGER", "description": "Interval in seconds for a recurring reminder (e.g. 3600 for hourly)"}
        },
        "required": ["message"]
    }
}

list_reminders_tool = {
    "name": "list_reminders",
    "description": "List all active reminders with their IDs and fire times.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

cancel_reminder_tool = {
    "name": "cancel_reminder",
    "description": "Cancel a reminder by its ID. Use when the user says 'cancel reminder', 'stop reminder', 'don't remind me'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING", "description": "The reminder ID to cancel"}
        },
        "required": ["id"]
    }
}

set_schedule_tool = {
    "name": "set_schedule",
    "description": "Save a schedule/event with date and time. Opens a beautiful floating window with an animated analog clock and calendar. Also registers in Windows Task Scheduler as fallback so the notification fires even if SODA is offline. Use when the user says 'schedule', 'save a schedule', 'set an event', 'plan a meeting', 'add to calendar'. Examples: 'schedule meeting tomorrow at 8', 'save dentist appointment on June 10 at 2pm', 'set event for day after tomorrow at 5:30pm'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Title of the schedule/event"},
            "date": {"type": "STRING", "description": "Date: 'tomorrow', 'today', 'day after tomorrow', or 'YYYY-MM-DD' format"},
            "time": {"type": "STRING", "description": "Time in HH:MM format (e.g. '08:00', '14:30'). Optional."},
            "details": {"type": "STRING", "description": "Additional details about the schedule. Optional."}
        },
        "required": ["title", "date"]
    }
}

list_schedules_tool = {
    "name": "list_schedules",
    "description": "List all saved schedules sorted by date/time. Returns each schedule with id, title, date, time, and details.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

delete_schedule_tool = {
    "name": "delete_schedule",
    "description": "Delete a schedule by its ID. Also removes the Windows Task Scheduler fallback task. Use when the user says 'delete schedule', 'remove event', 'cancel schedule'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING", "description": "The schedule ID to delete"}
        },
        "required": ["id"]
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

window_focus_tool = {
    "name": "window_focus",
    "description": "Bring a window to the front and give it focus by searching its title. Use to switch between apps before interacting with them. Examples: 'Chrome', 'Notepad', 'Visual Studio Code', 'Spotify'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Window title to focus (partial match works)"}
        },
        "required": ["title"]
    }
}

window_list_tool = {
    "name": "window_list",
    "description": "List all visible open windows with their titles. Use to discover what apps and windows are currently open on the desktop.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

go_background_tool = {
    "name": "go_background",
    "description": "Put SODA into background mode. Minimizes the window so the user can see their desktop and work on other things, but SODA stays fully active — can still hear voice commands, respond, use tools, and control the screen. Use when the user says 'go to background', 'minimize', 'go away but stay listening', 'work in background', 'go to the back'. Does NOT pause audio or camera unlike sleep.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

come_back_tool = {
    "name": "come_back",
    "description": "Bring SODA back to the foreground. Restores the minimized window. Use when the user says 'come back', 'come to foreground', 'restore window', 'show yourself', 'come to front', 'come forward'. Works from both background and sleep modes.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

welcome_home_tool = {
    "name": "welcome_home",
    "description": "Play a spoken welcome message via ElevenLabs TTS. Use when the user says 'welcome home', 'I'm back', 'jarvis', 'I returned', or after double-clap detection.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
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

window_move_tool = {
    "name": "window_move",
    "description": "Move or resize a window by title. Use to arrange windows on the desktop. If width and height are omitted, only moves the window.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Window title to move/resize"},
            "x": {"type": "INTEGER", "description": "New X screen position"},
            "y": {"type": "INTEGER", "description": "New Y screen position"},
            "width": {"type": "INTEGER", "description": "New width in pixels (optional)"},
            "height": {"type": "INTEGER", "description": "New height in pixels (optional)"}
        },
        "required": ["title", "x", "y"]
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

github_list_repos_tool = {
    "name": "github_list_repos",
    "description": "List GitHub repositories, optionally filtered by owner. Uses the 'gh' CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "owner": {"type": "STRING", "description": "GitHub username or org to list repos for (optional)"}
        },
        "required": []
    }
}

github_create_repo_tool = {
    "name": "github_create_repo",
    "description": "Create a new GitHub repository. Uses the 'gh' CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "Repository name"},
            "description": {"type": "STRING", "description": "Repository description"},
            "private": {"type": "BOOLEAN", "description": "Whether the repo should be private"},
            "auto_init": {"type": "BOOLEAN", "description": "Initialize with a README"}
        },
        "required": ["name"]
    }
}

github_get_repo_tool = {
    "name": "github_get_repo",
    "description": "Get details about a specific GitHub repository. Uses the 'gh' CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "repo": {"type": "STRING", "description": "Repository in format 'owner/name'"}
        },
        "required": ["repo"]
    }
}

github_create_pr_tool = {
    "name": "github_create_pr",
    "description": "Create a pull request on a GitHub repository. Uses the 'gh' CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "repo": {"type": "STRING", "description": "Repository in format 'owner/name'"},
            "title": {"type": "STRING", "description": "Pull request title"},
            "body": {"type": "STRING", "description": "Pull request body/description"},
            "head": {"type": "STRING", "description": "Source branch name"},
            "base": {"type": "STRING", "description": "Target branch name (default: main)"}
        },
        "required": ["repo", "title", "head"]
    }
}

github_list_issues_tool = {
    "name": "github_list_issues",
    "description": "List issues for a GitHub repository. Uses the 'gh' CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "repo": {"type": "STRING", "description": "Repository in format 'owner/name'"},
            "state": {"type": "STRING", "description": "Filter by state: 'open', 'closed', 'all'"}
        },
        "required": ["repo"]
    }
}

github_create_issue_tool = {
    "name": "github_create_issue",
    "description": "Create a new issue on a GitHub repository. Uses the 'gh' CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "repo": {"type": "STRING", "description": "Repository in format 'owner/name'"},
            "title": {"type": "STRING", "description": "Issue title"},
            "body": {"type": "STRING", "description": "Issue body/description"}
        },
        "required": ["repo", "title"]
    }
}

# ── Vercel ──

vercel_list_projects_tool = {
    "name": "vercel_list_projects",
    "description": "List Vercel projects. Uses the Vercel CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

vercel_deploy_tool = {
    "name": "vercel_deploy",
    "description": "Deploy a project to Vercel from a local path. Uses the Vercel CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "Path to the project directory"},
            "name": {"type": "STRING", "description": "Project name (optional)"},
            "prod": {"type": "BOOLEAN", "description": "Deploy to production"}
        },
        "required": []
    }
}

vercel_list_deployments_tool = {
    "name": "vercel_list_deployments",
    "description": "List recent Vercel deployments for a project. Uses the Vercel CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "project": {"type": "STRING", "description": "Vercel project name"},
            "limit": {"type": "INTEGER", "description": "Max number of deployments to return"}
        },
        "required": []
    }
}

vercel_get_deployment_tool = {
    "name": "vercel_get_deployment",
    "description": "Get details about a specific Vercel deployment by URL or ID. Uses the Vercel CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url_or_id": {"type": "STRING", "description": "Deployment URL or ID"}
        },
        "required": ["url_or_id"]
    }
}

# ── Netlify ──

netlify_list_sites_tool = {
    "name": "netlify_list_sites",
    "description": "List Netlify sites. Uses the Netlify CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

netlify_get_site_tool = {
    "name": "netlify_get_site",
    "description": "Get details about a specific Netlify site. Uses the Netlify CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "site_id": {"type": "STRING", "description": "Netlify site ID"}
        },
        "required": ["site_id"]
    }
}

netlify_deploy_tool = {
    "name": "netlify_deploy",
    "description": "Deploy a local directory to Netlify. Uses the Netlify CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "Path to the build directory"},
            "prod": {"type": "BOOLEAN", "description": "Deploy to production branch"},
            "message": {"type": "STRING", "description": "Deploy message"}
        },
        "required": []
    }
}

netlify_create_site_tool = {
    "name": "netlify_create_site",
    "description": "Create a new empty Netlify site. Uses the Netlify CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "Site name (optional)"}
        },
        "required": []
    }
}

netlify_list_deploys_tool = {
    "name": "netlify_list_deploys",
    "description": "List recent deploys for a Netlify site. Uses the Netlify CLI.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "site_id": {"type": "STRING", "description": "Netlify site ID"}
        },
        "required": ["site_id"]
    }
}

# ── Notepad ──

notepad_open_tool = {
    "name": "notepad_open",
    "description": "Open the notepad with optional pre-populated tabs. Each tab is an object with 'name' and 'content'.",
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
    "description": "Write content to a notepad tab. If the tab doesn't exist, it will be created.",
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
    "description": "Read the content of a notepad tab.",
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

# ── Sleep / Wake ──

go_to_sleep_tool = {
    "name": "go_to_sleep",
    "description": "Put SODA to sleep mode. Minimizes the window and stops proactive monitoring. Use when the user says 'go to sleep', 'sleep', 'goodnight'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

wake_up_tool = {
    "name": "wake_up",
    "description": "Wake SODA from sleep mode. Restores the window and resumes monitoring. Use when the user says 'wake up', 'come back'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

# ── Telegram ──

send_telegram_message_tool = {
    "name": "send_telegram_message",
    "description": "Send a text message via Telegram bot.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Message text to send"}
        },
        "required": ["text"]
    }
}

send_telegram_file_tool = {
    "name": "send_telegram_file",
    "description": "Send a file via Telegram bot.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "Path to the file to send"}
        },
        "required": ["path"]
    }
}

search_and_send_telegram_tool = {
    "name": "search_and_send_telegram",
    "description": "Search the web and send results via Telegram.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Search query"},
            "num_results": {"type": "INTEGER", "description": "Number of results to send"}
        },
        "required": ["query"]
    }
}

create_folder_tool = {
    "name": "create_folder",
    "description": "Create a folder at the specified path. Also creates parent directories if needed.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {"type": "STRING", "description": "Folder path to create"}
        },
        "required": ["path"]
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
    "description": "List all available SODA capabilities and tools.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

shutdown_soda_tool = {
    "name": "shutdown_soda",
    "description": "Gracefully shut down the SODA assistant only (not the computer). Use when the user says 'turn off', 'exit', 'quit', 'stop'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

shutdown_system_tool = {
    "name": "shutdown_system",
    "description": "SHUT DOWN THE ENTIRE COMPUTER. Use ONLY when the user explicitly says 'shutdown', 'shut down', 'power off', or 'turn off the laptop/computer/pc'. This will force-close everything and power off the machine.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

# ── Task Planner ──

plan_tasks_tool = {
    "name": "plan_tasks",
    "description": (
        "Create a structured plan with multiple TODO items. Call this IMMEDIATELY when the user gives 2+ commands "
        "or a multi-step request (e.g. 'do X, then Y, then Z'). Breaks the request into numbered steps. "
        "A panel slides from the left showing the plan with checkboxes. "
        "Each task is tracked as pending/running/done/failed."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Plan title"},
            "tasks": {
                "type": "ARRAY",
                "description": "List of task objects, each with 'title' and optional 'description'",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING", "description": "Task title"},
                        "description": {"type": "STRING", "description": "Task description"}
                    }
                }
            }
        },
        "required": ["title", "tasks"]
    }
}

update_task_tool = {
    "name": "update_task",
    "description": (
        "Update the status of a task in the active plan. Call after completing each step. "
        "Status: 'running' when you start working on a task, 'done' when completed, "
        "'failed' if it couldn't be done."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task_id": {"type": "STRING", "description": "The task ID to update"},
            "status": {"type": "STRING", "description": "New status: 'running', 'done', or 'failed'"},
            "result": {"type": "STRING", "description": "Optional result description"}
        },
        "required": ["task_id", "status"]
    }
}

cancel_plan_tool = {
    "name": "cancel_plan",
    "description": (
        "Cancel/dismiss the current task plan. Call when the user says 'cancel', 'dismiss tasks', "
        "'forget the tasks', or when ALL tasks are done and the panel should close."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

get_plan_tool = {
    "name": "get_plan",
    "description": (
        "Get the current active plan with all tasks and their statuses. "
        "Call when resuming work after a reset to recover the task list "
        "and continue from the first task that isn't 'done'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
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

app_search_tool = {
    "name": "app_search",
    "description": (
        "Search inside ANY desktop app (YouTube, Spotify, browser, etc.) using keyboard automation. "
        "Opens or focuses the app, types a keyboard shortcut to activate the search bar, "
        "types the query, presses Enter, then takes a screenshot and uses AI Vision "
        "to read and describe the search results. "
        "Use when the user says 'search [query] on YouTube', 'find [query] in Spotify', "
        "'look up [query] in [app]'. "
        "For YouTube specifically, the search key is '/' (presses slash to focus search bar). "
        "For most other apps, the search key is 'Ctrl+F'. "
        "If no search_key is provided, defaults to '/'. "
        "The result includes an 'analysis' field with what AI Vision saw on screen. "
        "After returning, the user may ask to scroll or open a specific result. "
        "Examples: app_search(app_name='YouTube', query='python tutorial'), "
        "app_search(app_name='Spotify', search_key='Ctrl+F', query='lofi beats')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {"type": "STRING", "description": "Name of the app to search in (e.g. 'YouTube', 'Spotify')"},
            "query": {"type": "STRING", "description": "The search query text"},
            "search_key": {"type": "STRING", "description": "Keyboard shortcut to activate search bar. Default '/' for YouTube. Can be 'Ctrl+F' for other apps."}
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

credential_save_tool = {
    "name": "credential_save",
    "description": (
        "Save a username/password for a service (like a website login). "
        "Credentials are encrypted at rest using Fernet (cryptography). "
        "Use when the user says 'save my password for [service]', "
        "'remember my login for [service]', 'store credentials for [service]'. "
        "service is the website/app name (e.g. 'facebook', 'gmail', 'amazon'). "
        "username is the email or username. password is the password. "
        "All three are required. "
        "Returns success confirmation. "
        "Example: credential_save(service='facebook', username='user@email.com', password='mypassword123')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "service": {"type": "STRING", "description": "Service/app name (e.g. 'facebook', 'gmail', 'amazon')"},
            "username": {"type": "STRING", "description": "Username or email for the service"},
            "password": {"type": "STRING", "description": "Password for the service"}
        },
        "required": ["service", "username", "password"]
    }
}

credential_get_tool = {
    "name": "credential_get",
    "description": (
        "Retrieve saved credentials for a specific service. "
        "Returns username and password that were previously saved. "
        "Use when the user says 'what's my password for [service]', "
        "'get my [service] login', 'show me my saved password'. "
        "Example: credential_get(service='facebook')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "service": {"type": "STRING", "description": "Service name to retrieve credentials for"}
        },
        "required": ["service"]
    }
}

credential_list_tool = {
    "name": "credential_list",
    "description": (
        "List all services that have saved credentials. "
        "Returns an array of service names with their usernames. "
        "Does NOT leak passwords. "
        "Use when the user says 'list my saved passwords', 'what services do I have saved', "
        "'show me all saved credentials'. "
        "No parameters required."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

credential_delete_tool = {
    "name": "credential_delete",
    "description": (
        "Delete saved credentials for a specific service. "
        "Use when the user says 'delete my [service] password', "
        "'remove [service] credentials', 'forget [service] login'. "
        "Example: credential_delete(service='facebook')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "service": {"type": "STRING", "description": "Service name to delete credentials for"}
        },
        "required": ["service"]
    }
}

# ── Browser Automation ──

browser_automate_tool = {
    "name": "browser_automate",
    "description": (
        "Full browser automation: navigate to a URL, then execute a list of steps. "
        "SUPPORTED ACTIONS:\n"
        "- navigate(url): Navigate to a URL in Chrome (Chrome profile 'rahikulmakhtum' auto-detected).\n"
        "- click(description): Find and click an element. Uses AI Vision to locate it on screen. "
        "description must describe what to click clearly (e.g. 'the login button', 'the search box'). "
        "3 retries with escalating vision prompts on failure.\n"
        "- type(text, target): Type text into an input field. 'target' describes where to click first. "
        "Automatically clicks the target before typing. Set press_enter=true to press Enter after typing.\n"
        "- read(prompt): Read text from the current page. prompt explains what to look for. "
        "Uses AI Vision to analyze the screenshot.\n"
        "- wait(seconds): Wait a specified number of seconds.\n\n"
        "COMMON WORKFLOWS:\n"
        "1. LOGIN: navigate(url) → click('username/email field') → type(username, 'the email input') → "
        "click('password field') → type(password, 'the password input') → click('login/sign in button').\n"
        "2. SEARCH: navigate(url) → click('search box') → type(query, 'search box', press_enter=true) → "
        "read('What are the search results on this page? List them.').\n\n"
        "Use for ANY task that needs clicking, typing, and reading in a web browser. "
        "Especially useful for sites without APIs (messaging platforms, social media, internal tools). "
        "ALWAYS auto-inject saved credentials from credential_get when doing login workflows. "
        "CRITICAL: When the user asks to log into a service, FIRST call credential_get(service=...) "
        "to retrieve saved credentials, then inject them at the right step. "
        "DO NOT use this tool for reading or checking emails. Use read_emails tool instead — "
        "browser automation does NOT work for Gmail (Google blocks automated login)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "The URL to navigate to"},
            "steps": {
                "type": "ARRAY",
                "description": "List of step objects to execute. Each step has 'action' and 'params' fields.",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {
                            "type": "STRING",
                            "description": "Action: 'navigate', 'click', 'type', 'read', 'wait'"
                        },
                        "params": {
                            "type": "OBJECT",
                            "description": "Parameters for the action. See description for details per action type.",
                            "properties": {
                                "url": {"type": "STRING", "description": "For navigate: the URL to go to"},
                                "description": {"type": "STRING", "description": "For click: description of the element to find and click"},
                                "target": {"type": "STRING", "description": "For type: description of the input field to click first"},
                                "text": {"type": "STRING", "description": "For type: the text to type"},
                                "press_enter": {"type": "BOOLEAN", "description": "For type: press Enter after typing (default false)"},
                                "prompt": {"type": "STRING", "description": "For read: what to look for on the page"},
                                "seconds": {"type": "NUMBER", "description": "For wait: seconds to wait"}
                            }
                        }
                    },
                    "required": ["action", "params"]
                }
            },
            "profile": {"type": "STRING", "description": "Chrome profile name (default: 'rahikulmakhtum')"}
        },
        "required": ["url", "steps"]
    }
}

# ── Scheduled Tasks ──

create_scheduled_task_tool = {
    "name": "create_scheduled_task",
    "description": (
        "Schedule a task to run at a specific time or interval. "
        "Use when the user says 'schedule [action] at [time]', "
        "'every [interval] do [action]', 'remind me to [action] at [time]', "
        "or similar scheduling requests. "
        "The action_text is WHAT to do — write it exactly as the user described it "
        "so it can be re-injected into conversation later. "
        "The schedule is a human-readable time expression. Supported formats:\n"
        "- 'every day at 9am' or 'daily at 09:00'\n"
        "- 'every monday at 14:30'\n"
        "- 'every 30 minutes' or 'every 2 hours'\n"
        "- 'tomorrow at 8am'\n"
        "- 'in 10 minutes'\n"
        "- 'at 3pm' (today or next occurrence)\n"
        "When the time comes, SODA will act as if the user said the action_text."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action_text": {"type": "STRING", "description": "What to do — the natural language description of the action"},
            "schedule": {"type": "STRING", "description": "Human-readable schedule like 'every day at 9am' or 'every 30 minutes'"},
            "label": {"type": "STRING", "description": "Short label for the task (optional, defaults to action_text)"}
        },
        "required": ["action_text", "schedule"]
    }
}

list_scheduled_tasks_tool = {
    "name": "list_scheduled_tasks",
    "description": "List all currently scheduled tasks with their IDs, labels, and next fire times.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
}

delete_scheduled_task_tool = {
    "name": "delete_scheduled_task",
    "description": "Delete a scheduled task by its ID. Use when the user says 'cancel schedule', 'remove task', 'delete schedule'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task_id": {"type": "STRING", "description": "The task ID to delete"}
        },
        "required": ["task_id"]
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
    "description": "Open a live camera viewfinder window on the user's screen. "
                   "Call this when the user says 'open the camera', 'show me the camera', "
                   "'turn on the camera', or wants to take a photo or see themselves. "
                   "The window is small, draggable, and mobile-friendly. "
                   "After opening, use camera_control to capture, analyze, save, switch, or close.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

camera_control_tool = {
    "name": "camera_control",
    "description": "Control the live camera window after it is open. "
                   "snapshot = capture current frame silently for you to see. "
                   "analyze = capture current frame and describe what you see to the user. "
                   "save = capture current frame and store it in the database with a description. "
                   "switch = toggle between front and back camera. "
                   "close = close the camera window. "
                   "Use analyze when the user asks 'what do you see', 'what's in front of me', "
                   "or anything requiring visual description. "
                   "Use snapshot for silent capture without commentary. "
                   "Use save when the user says 'save this photo' or 'remember this image'. "
                   "Use switch when the user says 'switch camera', 'back camera', 'selfie'. "
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

open_pastebox_tool = {
    "name": "open_pastebox",
    "description": "Show a floating text box where the user can paste or type content for SODA to read, analyze, or process. Returns the pasted content as text. Use when user says 'open paste box', 'show paste box', 'I need to paste something', 'open a text box', 'I want to paste text'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": []
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

read_emails_tool = {
    "name": "read_emails",
    "description": (
        "CRITICAL: This is the ONLY tool for reading emails. NEVER use open_browser or browser_automate "
        "for email — those tools do NOT work for Gmail (login blocks automation). "
        "Read emails from the user's Gmail inbox via IMAP. Returns subject, sender, date, and body preview. "
        "Use when the user asks to 'check my email', 'read my inbox', 'show unread emails', "
        "'any new emails', 'read my messages', or 'check gmail'. "
        "If email is not configured, guide the user through setting up an App Password. "
        "MANDATORY: Call this tool for ANY email-related request. Do NOT open Gmail in the browser."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "IMAP search query: 'UNSEEN' (default), 'ALL', 'FROM someone@example.com', 'SUBJECT meeting', 'SINCE 01-Jan-2025'"
            },
            "max_results": {
                "type": "INTEGER",
                "description": "Maximum emails to return (default 10, max 50)"
            }
        },
        "required": []
    }
}

send_email_tool = {
    "name": "send_email",
    "description": (
        "Send an email via Gmail SMTP. Use ONLY after asking the user to confirm the reply content "
        "and getting explicit confirmation. Always show the user what will be sent before sending. "
        "Parameters: recipient address, subject line, and body text."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "to": {"type": "STRING", "description": "Recipient email address"},
            "subject": {"type": "STRING", "description": "Email subject line"},
            "body": {"type": "STRING", "description": "Email body text (plain text)"}
        },
        "required": ["to", "subject", "body"]
    }
}

email_config_tool = {
    "name": "email_config",
    "description": (
        "Configure Gmail IMAP/SMTP credentials. Call this when the user provides their "
        "email address and app password. Store them for the session. "
        "Guide them to https://myaccount.google.com/apppasswords if they don't have an app password."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "address": {"type": "STRING", "description": "Full Gmail address (e.g., user@gmail.com)"},
            "password": {"type": "STRING", "description": "16-character Gmail App Password"}
        },
        "required": ["address", "password"]
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
    clipboard_read_tool,
    clipboard_write_tool,
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
    set_reminder_tool,
    set_schedule_tool,
    list_schedules_tool,
    delete_schedule_tool,
    show_calendar_tool,
    list_reminders_tool,
    cancel_reminder_tool,
    recognize_face_tool,
    remember_face_tool,
    plan_tasks_tool,
    update_task_tool,
    cancel_plan_tool,
    get_plan_tool,
    github_list_repos_tool,
    github_create_repo_tool,
    github_get_repo_tool,
    github_create_pr_tool,
    github_list_issues_tool,
    github_create_issue_tool,
    vercel_list_projects_tool,
    vercel_deploy_tool,
    vercel_list_deployments_tool,
    vercel_get_deployment_tool,
    netlify_list_sites_tool,
    netlify_get_site_tool,
    netlify_deploy_tool,
    netlify_create_site_tool,
    netlify_list_deploys_tool,
    notepad_open_tool,
    notepad_write_tool,
    notepad_read_tool,
    view_file_tool,
    go_to_sleep_tool,
    wake_up_tool,
    go_background_tool,
    come_back_tool,
    mouse_click_tool,
    mouse_move_tool,
    mouse_scroll_tool,
    mouse_drag_tool,
    keyboard_type_tool,
    keyboard_press_tool,
    click_element_tool,
    type_into_tool,
    find_element_tool,
    window_focus_tool,
    window_list_tool,
    window_move_tool,
    send_telegram_message_tool,
    send_telegram_file_tool,
    search_and_send_telegram_tool,
    create_folder_tool,
    delete_items_tool,
    rename_item_tool,
    copy_item_tool,
    move_item_tool,
    list_drives_tool,
    scroll_file_list_tool,
    scrape_site_tool,
    export_data_tool,
    get_pagespeed_insights_tool,
    show_agents_tool,
    shutdown_soda_tool,
    shutdown_system_tool,
    start_website_project_tool,
    web_builder_answer_tool,
    workbase_list_tool,
    workbase_get_tool,
    workbase_save_progress_tool,
    workbase_import_tool,
    workbase_save_context_tool,
    workbase_compare_tool,
    whatsapp_find_and_call_tool,
    whatsapp_find_and_message_tool,
    check_whatsapp_tool,
    reply_whatsapp_tool,
    read_whatsapp_chat_tool,
    create_scheduled_task_tool,
    list_scheduled_tasks_tool,
    delete_scheduled_task_tool,
    open_app_tool,
    list_installed_apps_tool,
    webview_action_tool,
    take_photo_tool,
    open_camera_tool,
    camera_control_tool,
    welcome_home_tool,
    control_system_tool,
    *FEELINGS_TOOLS_SCHEMA,
    *IELTS_TOOLS,
    pentest_target_tool,
    pentest_browser_target_tool,
    open_pastebox_tool,
    browser_command_tool,
    app_search_tool,
    app_scroll_tool,
    credential_save_tool,
    credential_get_tool,
    credential_list_tool,
    credential_delete_tool,
    browser_automate_tool,
    read_emails_tool,
    send_email_tool,
    email_config_tool,

    # ── Custom Memory Schemas ──
    create_memory_schema_tool,
    list_custom_schemas_tool,
    store_custom_memory_tool,
    query_custom_memory_tool,

    
]}]

