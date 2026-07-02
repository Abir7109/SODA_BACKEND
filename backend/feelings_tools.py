"""
feelings_tools.py — Emotional memory management tools + auto-detection

Tools for Gemini:
1. feelings_resolve_episode  — mark something as resolved
2. feelings_add_note         — add detail to an existing episode
3. feelings_get_history      — retrieve emotional history
4. feelings_check_followup   — get episodes needing attention
5. feelings_get_profile      — read the user's emotional profile

feelings_store_episode is no longer a Gemini tool — it runs automatically
in the background via auto_detect_and_store() when emotional content
is detected in the user's speech, so conversation never stops.
"""

from feelings_memory import FeelingsMemory

_memory = FeelingsMemory()


def get_feelings_memory():
    return _memory


def feelings_store_episode(category, intensity, summary, trigger_phrase="", stressor=""):
    from feelings import EmotionalCategory, EmotionalIntensity, EmotionalState, EmotionalSignal, SupportStrategy

    try:
        cat = EmotionalCategory(category.lower())
    except ValueError:
        cat = EmotionalCategory.UNKNOWN

    try:
        intensity_enum = EmotionalIntensity[intensity.upper()]
    except KeyError:
        intensity_enum = EmotionalIntensity.MODERATE

    signal = EmotionalSignal(
        category=cat, intensity=intensity_enum, confidence=0.9,
        trigger_phrase=trigger_phrase, context_clues=[summary],
    )
    state = EmotionalState(
        primary=signal, strategy=SupportStrategy.ACTIVE_LISTENING,
        needs_immediate_attention=(intensity_enum == EmotionalIntensity.SEVERE),
    )
    episode = _memory.store_episode(state, summary)

    if stressor:
        _memory.add_known_stressor(stressor)

    if episode:
        return {"stored": True, "episode_id": episode.id, "message": f"Stored {category} episode: {summary}"}
    return {"stored": False, "reason": "Below threshold or in cooldown period"}


def feelings_resolve_episode(episode_id, resolution="resolved naturally"):
    success = _memory.mark_resolved(episode_id, resolution)
    return {
        "resolved": success, "episode_id": episode_id,
        "message": f"Marked resolved: {resolution}" if success else "Episode not found",
    }


def feelings_add_note(episode_id, note):
    success = _memory.add_note_to_episode(episode_id, note)
    return {"updated": success, "message": "Note added" if success else "Episode not found"}


def feelings_get_history(days=30, category="", include_resolved=True):
    from feelings_memory import EmotionalCategory
    cat = None
    if category:
        try:
            cat = EmotionalCategory(category.lower())
        except ValueError:
            pass

    episodes = _memory.get_recent_episodes(days=days, category=cat, include_resolved=include_resolved)
    return {
        "episodes": [{
            "id": ep.id, "category": ep.category, "intensity": ep.intensity,
            "summary": ep.summary, "days_ago": ep.days_ago,
            "resolved": ep.is_resolved, "resolution": ep.resolution, "notes": ep.notes,
        } for ep in episodes],
        "count": len(episodes),
    }


def feelings_check_followup():
    episodes = _memory.get_episodes_needing_followup()
    results = []
    for ep in episodes:
        days_str = ("today" if ep.days_ago == 0 else "yesterday" if ep.days_ago == 1 else f"{ep.days_ago} days ago")
        results.append({
            "id": ep.id, "category": ep.category, "summary": ep.summary,
            "when": days_str, "follow_up_count": ep.follow_up_count, "intensity": ep.intensity,
        })
    return {"needs_followup": len(results) > 0, "episodes": results}


def feelings_get_profile():
    profile_text = _memory.get_profile_summary()
    profile = _memory._profile
    return {
        "profile_summary": profile_text,
        "baseline_mood": profile.baseline_mood,
        "common_stressors": profile.common_stressors,
        "common_joys": profile.common_joys,
        "support_preferences": profile.support_preferences,
        "total_episodes_tracked": profile.total_episodes,
        "average_recovery_days": profile.average_recovery_days,
    }


FEELINGS_TOOLS_SCHEMA = [
    {
        "name": "feelings_resolve_episode",
        "description": (
            "Mark an emotional episode as resolved when the user indicates "
            "they're doing better about something they previously shared. "
            "Look for signals: 'I'm okay now', 'moved on', "
            "'not bothering me anymore', or a clear shift to a better place."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "episode_id": {"type": "STRING", "description": "The episode ID from feelings_get_history"},
                "resolution": {"type": "STRING", "description": "Brief description of how it resolved (optional)"},
            },
            "required": ["episode_id"],
        },
    },
    {
        "name": "feelings_add_note",
        "description": (
            "Add new information to an existing emotional episode. "
            "Use when the user reveals more detail about an ongoing situation "
            "that connects to something already stored."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "episode_id": {"type": "STRING", "description": "The episode ID to update"},
                "note": {"type": "STRING", "description": "The new information to add"},
            },
            "required": ["episode_id", "note"],
        },
    },
    {
        "name": "feelings_get_history",
        "description": (
            "Retrieve the user's emotional history. "
            "Call when they mention recurring struggles, when you want to "
            "understand their emotional arc, or to check if a current emotion "
            "is a pattern. Returns past episodes with timestamps and summaries."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "days": {"type": "INTEGER", "description": "How far back to look (default 30)"},
                "category": {"type": "STRING", "description": "Filter by category (optional)"},
                "include_resolved": {"type": "BOOLEAN", "description": "Include resolved episodes (default true)"},
            },
            "required": [],
        },
    },
    {
        "name": "feelings_check_followup",
        "description": (
            "Check if any past emotional episodes need a gentle proactive check-in. "
            "Call this at the start of a new session or during a natural pause. "
            "If it returns episodes, consider weaving a gentle check-in into "
            "the conversation naturally."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "feelings_get_profile",
        "description": (
            "Get the user's overall emotional profile — their patterns, "
            "stressors, joys, and support preferences. "
            "Call when you want to understand what kind of support "
            "they respond best to."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": [],
        },
    },
]

# ── Auto-detection (runs server-side, no Gemini involvement) ──

_EMOTION_PATTERNS = [
    # grief / loss
    (["grief", "grieving", "mourning", "lost someone", "passed away", "died", "death", "funeral"], "grief", "STRONG"),
    (["miss", "miss her", "miss him", "missing them", "gone forever", "never see again"], "grief", "MODERATE"),
    # heartbreak
    (["heartbreak", "broken heart", "broke up", "ended things", "left me", "dumped", "relationship ended", "cheated on"], "heartbreak", "STRONG"),
    (["ex ", "ex-boyfriend", "ex-girlfriend", "ex-husband", "ex-wife", "toxic relationship", "getting over"], "heartbreak", "MODERATE"),
    # anxiety
    (["anxious", "anxiety", "panic", "nervous", "worried sick", "can't stop thinking", "overthinking", "racing thoughts", "dread"], "anxiety", "MODERATE"),
    (["panic attack", "can't breathe", "overwhelmed", "can't cope"], "anxiety", "STRONG"),
    # depression
    (["depressed", "depression", "hopeless", "worthless", "empty", "numb", "can't get out of bed", "no energy", "no motivation"], "depression", "STRONG"),
    (["sad", "down", "low", "not okay", "struggling", "having a hard time", "rough day", "bad day"], "depression", "MODERATE"),
    # anger
    (["furious", "livid", "pissed off", "so angry", "raging", "hate", "can't stand"], "anger", "STRONG"),
    (["annoyed", "frustrated", "irritated", "ticked off"], "anger", "MILD"),
    # loneliness
    (["lonely", "alone", "no one", "isolated", "nobody cares", "no friends", "by myself"], "loneliness", "MODERATE"),
    # exhaustion
    (["exhausted", "burned out", "burnout", "drained", "depleted", "wiped out", "so tired", "can't keep going"], "exhaustion", "MODERATE"),
    (["ashamed", "shame", "guilty", "embarrassed", "humiliated", "disappointed in myself", "hate myself"], "shame", "MODERATE"),
    # joy
    (["so happy", "amazing", "incredible", "thrilled", "ecstatic", "over the moon", "best day", "so excited"], "joy", "STRONG"),
    (["happy", "great news", "good day", "proud", "wonderful", "fantastic"], "joy", "MODERATE"),
    # relief
    (["relieved", "finally over", "what a relief", "thank god", "weight off", "finally done"], "relief", "MODERATE"),
    # pride
    (["proud of", "accomplished", "achievement", "worked hard", "finally did it", "made it"], "pride", "MODERATE"),
]


def auto_detect_and_store(text: str) -> dict | None:
    """
    Called server-side after each user transcription.
    Returns the store result if something was stored, None otherwise.
    Conversation is NOT interrupted — this runs in a background task.
    """
    text_lower = text.lower().strip()
    if len(text_lower) < 10:
        return None

    best_category = "unknown"
    best_intensity = "MILD"
    best_score = 0

    for keywords, category, intensity in _EMOTION_PATTERNS:
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_category = category
            best_intensity = intensity

    if best_score == 0:
        return None

    # Skip MILD matches unless they have 2+ keyword hits (avoid false positives)
    if best_intensity == "MILD" and best_score < 2:
        return None

    summary = text[:200]
    result = feelings_store_episode(
        category=best_category,
        intensity=best_intensity,
        summary=summary,
        trigger_phrase=text[:120],
    )
    result["category"] = best_category
    result["intensity"] = best_intensity
    return result
