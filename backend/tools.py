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
},

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
},

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
},

execute_command_tool = {
    "name": "execute_command",
    "description": "Executes a system command or opens an application. Use this when the user asks to run programs, open applications, execute system commands, or perform any system operations.",
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
        "Run a terminal/shell command on the user's system and return the output. "
        "Use this to run scripts, check git status, install packages, list files, etc. "
        "Output is shown to the user in the HUD terminal. "
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
    get_news_tool,
    news_control_tool,
    define_word_tool,
    wikipedia_tool,
    web_search_live_tool,
    browse_webpage_tool,
    open_browser_tool,
    show_search_results_tool,
    list_files_tool,
    open_file_tool,
    close_panel_tool,
    show_tools_tool,
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
        "DO NOT call this for news, current events, or world happenings — use get_news instead. "
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

play_music_tool = {
    "name": "play_music",
    "description": (
        "Search and play music on Spotify. "
        "Opens Spotify, searches for the requested song/artist/genre/mood, "
        "and plays the top result. Automatically sets volume to 80% and "
        "minimizes SODA to the background widget so you can use your desktop. "
        "Use when the user says 'play some music', 'play [genre/mood/song]', "
        "'play chill music', 'I want to listen to [something]', "
        "'play lofi beats', 'play rock', 'play my liked songs', or similar. "
        "Examples: play_music(query='chill lofi'), play_music(query='rock classics'), "
        "play_music(query='focus study music')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "What to search for — genre, mood, artist, song, or playlist name. Examples: 'chill lofi', 'rock classics', 'focus study music', 'my liked songs'"
            }
        },
        "required": ["query"]
    }
}

control_music_tool = {
    "name": "control_music",
    "description": (
        "Control Spotify music playback globally. "
        "Works even when Spotify is minimized or in the background — "
        "no window focus needed. "
        "Actions: 'play_pause' (toggle play/pause), "
        "'next' (skip to next track), 'previous' (go to previous track). "
        "Use when the user says 'pause', 'resume', 'play', 'next song', "
        "'next track', 'skip', 'previous song', 'go back', 'change track'. "
        "Examples: control_music(action='play_pause'), control_music(action='next'), "
        "control_music(action='previous')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "'play_pause' to toggle, 'next' to skip forward, 'previous' to skip back"
            }
        },
        "required": ["action"]
    }
}

control_system_tool = {
    "name": "control_system",
    "description": (
        "Control system volume, brightness, and applications. "
        "Actions: volume_up, volume_down, volume_set (requires value 0-100), "
        "mute, brightness_up, brightness_down, brightness_set (requires value), "
        "open_app (requires app name), close_app, minimize, maximize, "
        "full_screen, show_desktop, switch_window, task_manager, "
        "screenshot, lock_screen, file_explorer, open_settings, "
        "restart, shutdown, type_text (requires text), "
        "press_key (requires key), scroll_up, scroll_down. "
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
        "Use ONLY when the user asks to call someone via WhatsApp. "
        "Before calling, use recall_person or recall_by_relationship to find the person "
        "in memory. If multiple matches, ask the user which one. "
        "Then pass the exact contact name to this tool. "
        "Only works with WhatsApp Desktop — no browser fallback. "
        "Example: whatsapp_find_and_call(contact_name='Rubab')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "contact_name": {"type": "STRING", "description": "Exact name to search in WhatsApp contacts"}
        },
        "required": ["contact_name"]
    }
}

whatsapp_find_and_message_tool = {
    "name": "whatsapp_find_and_message",
    "description": (
        "Find a contact in WhatsApp Desktop and send them a text message. "
        "Use ONLY when the user asks to message someone via WhatsApp. "
        "Before messaging, use recall_person or recall_by_relationship to find the person "
        "in memory. If multiple matches, ask the user which one. "
        "Then pass the exact contact name and message to this tool. "
        "Example: whatsapp_find_and_message(contact_name='Rubab', message='Hey, how are you?')"
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "contact_name": {"type": "STRING", "description": "Exact name to search in WhatsApp contacts"},
            "message": {"type": "STRING", "description": "The message text to send"}
        },
        "required": ["contact_name", "message"]
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

open_app_tool = {
    "name": "open_app",
    "description": "Search and open an application via Windows Start Menu. "
                   "Provide the app name as the user says it. "
                   "For example: 'open whatsapp', 'launch calculator', 'start chrome'. "
                   "The system will search the Start Menu and open the matching app. "
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

start_workflow_tool = {
    "name": "start_workflow",
    "description": (
        "Launch a full-screen HUD animation. Only call this when the user EXPLICITLY asks "
        "for one of these scenarios by name or clear description. Do NOT infer from context. "
        "Scenarios: 'outside' → user says 'going outside' or 'leaving workflow'; "
        "'project-review' → user says 'project review' or 'check project'; "
        "'break-time' → user says 'break time' or 'take a break'; "
        "'workbase-showcase' → user says 'show workbase' or 'workbase showcase'. "
        "Do NOT call this unless the user uses clear command phrases."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "workflow": {
                "type": "STRING",
                "description": "Name of the workflow to launch: outside, project-review, break-time, workbase-showcase"
            }
        },
        "required": ["workflow"]
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

tools_list = [{"function_declarations": [
    write_file_tool,
    read_file_tool,
    edit_file_tool,
    execute_command_tool,
    terminal_execute_tool,
    weather_tool,
    ip_info_tool,
    exchange_tool,
    get_news_tool,
    news_control_tool,
    define_word_tool,
    wikipedia_tool,
    web_search_live_tool,
    browse_webpage_tool,
    open_browser_tool,
    show_search_results_tool,
    list_files_tool,
    open_file_tool,
    close_panel_tool,
    show_tools_tool,
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
    start_workflow_tool,
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
    create_scheduled_task_tool,
    list_scheduled_tasks_tool,
    delete_scheduled_task_tool,
    open_app_tool,
    webview_action_tool,
    take_photo_tool,
    welcome_home_tool,
    play_music_tool,
    control_music_tool,
    control_system_tool,
    *FEELINGS_TOOLS_SCHEMA,
    *IELTS_TOOLS,
    pentest_target_tool,
    pentest_browser_target_tool,
    open_pastebox_tool,
]}]

