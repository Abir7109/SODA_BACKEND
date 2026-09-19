"""
IELTS Tool Schema for Gemini Live API — Consolidated
Single tool with action enum replaces 18 individual tools.
"""

IELTS_TOOLS = [
    {
        "name": "ielts",
        "description": (
            "IELTS preparation assistant. Use action to select the operation:\n"
            "  dashboard — Show band scores, target, exam date, streak, progress\n"
            "  set_goal — Set target band score and/or exam date\n"
            "  speaking_start — Start speaking practice (Part 1/2/3). Result contains EXACT text to speak aloud word for word.\n"
            "  speaking_evaluate — Evaluate spoken response. Result contains EXACT feedback to speak aloud word for word.\n"
            "  speaking_tips — Get tips for improving speaking band score\n"
            "  writing_prompt — Get a writing task prompt for practice\n"
            "  writing_evaluate — Evaluate a writing submission with detailed band scores\n"
            "  writing_template — Get essay structure/template for a specific type\n"
            "  grammar_check — Check text for grammar errors with IELTS context\n"
            "  reading_start — Start reading practice session with passage and questions\n"
            "  reading_check — Check reading answers and get score with explanations\n"
            "  reading_strategy — Get strategies for a specific question type\n"
            "  vocab_add — Add word to personal vocabulary bank\n"
            "  vocab_topic — Get topic-specific vocabulary with collocations\n"
            "  vocab_flashcards — Start flashcard review session from saved words\n"
            "  vocab_upgrade — Scan text and suggest Band 7+ vocabulary upgrades\n"
            "  study_plan — Generate personalized study plan\n"
            "  mock_test — Start timed mock test for a specific module"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "IELTS operation to perform",
                    "enum": [
                        "dashboard", "set_goal",
                        "speaking_start", "speaking_evaluate", "speaking_tips",
                        "writing_prompt", "writing_evaluate", "writing_template", "grammar_check",
                        "reading_start", "reading_check", "reading_strategy",
                        "vocab_add", "vocab_topic", "vocab_flashcards", "vocab_upgrade",
                        "study_plan", "mock_test"
                    ]
                },
                # ── set_goal ──
                "target_band": {"type": "number", "description": "Target overall band score (e.g., 7.0)"},
                "exam_date": {"type": "string", "description": "Exam date YYYY-MM-DD"},
                # ── speaking_start / speaking_evaluate ──
                "part": {"type": "integer", "description": "Speaking part: 1, 2, or 3"},
                "topic": {"type": "string", "description": "Topic (e.g., 'technology', 'education')"},
                "transcript": {"type": "string", "description": "User's spoken response (transcribed)"},
                "question": {"type": "string", "description": "Question or cue card topic"},
                # ── speaking_tips ──
                "criteria": {"type": "string", "description": "fluency/vocabulary/grammar/pronunciation"},
                "current_band": {"type": "number", "description": "Current band in this criterion"},
                # ── writing_prompt / writing_evaluate ──
                "task": {"type": "integer", "description": "Task 1 (graph/letter) or Task 2 (essay)"},
                "type": {"type": "string", "description": "opinion/discussion/problem_solution/advantages_disadvantages/task1_academic"},
                "essay": {"type": "string", "description": "User's essay or Task 1 response"},
                "task_prompt": {"type": "string", "description": "Original task prompt"},
                "essay_type": {"type": "string", "description": "opinion/discussion/problem_solution/advantages_disadvantages/task1"},
                # ── grammar_check ──
                "text": {"type": "string", "description": "Text to check"},
                # ── reading_check ──
                "passage_title": {"type": "string", "description": "Title of the reading passage"},
                "answers": {"type": "object", "description": "Dict of question_number: answer (e.g. {'1': 'TRUE', '2': 'B'})"},
                # ── reading_strategy ──
                "question_type": {"type": "string", "description": "true_false_not_given/matching_headings/sentence_completion/multiple_choice"},
                # ── vocab_add ──
                "word": {"type": "string", "description": "Word to add"},
                "definition": {"type": "string", "description": "Definition"},
                "example": {"type": "string", "description": "Example sentence"},
                # ── vocab_flashcards ──
                "count": {"type": "integer", "description": "Number of flashcards (default 10)"},
                # ── study_plan ──
                "hours_per_day": {"type": "number", "description": "Hours available per day"},
                # ── mock_test ──
                "module": {"type": "string", "description": "speaking/writing/reading/listening or full"}
            },
            "required": ["action"]
        }
    }
]
