"""
IELTS Tool Schemas for Gemini Live API
All 18 IELTS tools defined here, imported by tools.py
"""

IELTS_TOOLS = [
    {
        "name": "ielts_dashboard",
        "description": (
            "Show the user's IELTS preparation dashboard: current band scores, "
            "target band, exam date, streak, and progress history. Use when the "
            "user asks about their IELTS progress or overall status."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "ielts_set_goal",
        "description": (
            "Set the user's target IELTS band score and/or exam date. "
            "Use when the user tells you their target score or test date."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_band": {
                    "type": "number",
                    "description": "Target overall band score (e.g., 7.0, 7.5)"
                },
                "exam_date": {
                    "type": "string",
                    "description": "Exam date in ISO format YYYY-MM-DD"
                }
            },
            "required": []
        }
    },
    {
        "name": "ielts_speaking_start",
        "description": (
            "Start IELTS Speaking Part {part}. The result field contains "
            "the EXACT text you must speak aloud to the user in a natural "
            "interviewer voice. Read it word for word — do NOT change, "
            "summarize, or rephrase. After speaking, wait for the user's "
            "response. Call ielts_speaking_evaluate with their transcript."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "part": {
                    "type": "integer",
                    "description": "Speaking part: 1 (interview), 2 (cue card), or 3 (discussion)"
                },
                "topic": {
                    "type": "string",
                    "description": "Optional topic (e.g., 'technology', 'education')"
                }
            },
            "required": ["part"]
        }
    },
    {
        "name": "ielts_speaking_evaluate",
        "description": (
            "Evaluate the user's spoken response. The result field "
            "contains the EXACT feedback text you must speak aloud to "
            "the user. Read it word for word — do NOT change, summarize, "
            "or rephrase. Then continue the interview."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "The user's spoken response (transcribed)"
                },
                "question": {
                    "type": "string",
                    "description": "The question or cue card topic they were responding to"
                },
                "part": {
                    "type": "integer",
                    "description": "Which speaking part (1, 2, or 3)"
                }
            },
            "required": ["transcript", "question", "part"]
        }
    },
    {
        "name": "ielts_speaking_tips",
        "description": (
            "Get specific tips for improving IELTS Speaking band score. "
            "Can target specific criteria or general improvement."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "criteria": {
                    "type": "string",
                    "description": "Specific criterion: fluency, vocabulary, grammar, or pronunciation"
                },
                "current_band": {
                    "type": "number",
                    "description": "Current band in this criterion"
                }
            },
            "required": []
        }
    },
    {
        "name": "ielts_writing_prompt",
        "description": (
            "Get an IELTS Writing task prompt for practice. "
            "Specify task 1 or 2, and optionally a topic type."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "integer",
                    "description": "Task 1 (graph/letter) or Task 2 (essay)"
                },
                "type": {
                    "type": "string",
                    "description": "For Task 2: opinion/discussion/problem_solution/advantages_disadvantages"
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "ielts_writing_evaluate",
        "description": (
            "Evaluate a writing submission. Provide the essay text and the prompt. "
            "Returns detailed band scores across all 4 criteria with specific corrections."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "essay": {
                    "type": "string",
                    "description": "The user's essay or Task 1 response"
                },
                "task_prompt": {
                    "type": "string",
                    "description": "The original task prompt they were responding to"
                },
                "task_type": {
                    "type": "string",
                    "description": "opinion/discussion/problem_solution/advantages_disadvantages/task1_academic"
                }
            },
            "required": ["essay", "task_prompt", "task_type"]
        }
    },
    {
        "name": "ielts_writing_template",
        "description": (
            "Get a template or structure guide for a specific IELTS essay type. "
            "Includes paragraph structure, linking phrases, and band 7+ examples."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "essay_type": {
                    "type": "string",
                    "description": "opinion/discussion/problem_solution/advantages_disadvantages/task1"
                }
            },
            "required": ["essay_type"]
        }
    },
    {
        "name": "ielts_grammar_check",
        "description": (
            "Check a sentence or paragraph for grammar errors with IELTS context. "
            "Identifies error types and provides corrections."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to grammar-check"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "ielts_reading_start",
        "description": (
            "Start an IELTS Reading practice session. "
            "Returns a passage and questions for the user to answer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional topic preference (e.g., 'science', 'environment')"
                }
            },
            "required": []
        }
    },
    {
        "name": "ielts_reading_check",
        "description": (
            "Check the user's reading answers and provide score with explanations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "passage_title": {
                    "type": "string",
                    "description": "Title of the passage (from ielts_reading_start)"
                },
                "answers": {
                    "type": "object",
                    "description": "Dictionary of question_number: answer (e.g. {'1': 'TRUE', '2': 'B'})"
                }
            },
            "required": ["passage_title", "answers"]
        }
    },
    {
        "name": "ielts_reading_strategy",
        "description": (
            "Get strategies for a specific reading question type."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question_type": {
                    "type": "string",
                    "description": "true_false_not_given/matching_headings/sentence_completion/multiple_choice"
                }
            },
            "required": ["question_type"]
        }
    },
    {
        "name": "ielts_vocab_add",
        "description": (
            "Add a word to the user's personal IELTS vocabulary bank. "
            "Use when learning a new word during any session."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "word": {"type": "string", "description": "The word to add"},
                "definition": {"type": "string", "description": "Definition"},
                "example": {"type": "string", "description": "Example sentence"},
                "topic": {"type": "string", "description": "Topic category"}
            },
            "required": ["word", "definition", "example"]
        }
    },
    {
        "name": "ielts_vocab_topic",
        "description": (
            "Get topic-specific vocabulary for IELTS. "
            "Returns curated words, collocations, and upgrade suggestions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic: education/technology/environment/health/society"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "ielts_vocab_flashcards",
        "description": (
            "Start a vocabulary flashcard review session using the user's saved words."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of flashcards (default 10)"
                }
            },
            "required": []
        }
    },
    {
        "name": "ielts_vocab_upgrade",
        "description": (
            "Scan a text and suggest vocabulary upgrades to reach Band 7+."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to analyze for vocabulary improvements"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "ielts_study_plan",
        "description": (
            "Generate a personalized IELTS study plan based on the user's "
            "current bands, target band, and days until exam."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "hours_per_day": {
                    "type": "number",
                    "description": "Hours available per day for study"
                }
            },
            "required": []
        }
    },
    {
        "name": "ielts_mock_test",
        "description": (
            "Start a timed mock test for a specific IELTS module."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "module": {
                    "type": "string",
                    "description": "speaking/writing/reading/listening or full"
                }
            },
            "required": ["module"]
        }
    }
]
