"""
Personality engine for SODA — emotions, quips, and human-like behavior.

Provides:
- MoodState: tracks emotional state with transitions and decay
- PersonalityEngine: quip selection, weighted pools, dedup, persistence
- Quip categories: idle, tool_success, tool_failure, observation,
  self_aware, greeting, farewell, thinking

Storage: projects/long_term_memory/personality_history.jsonl
"""
import json
import random
import time
import asyncio
from pathlib import Path
from datetime import datetime

MEM_DIR = Path("projects/long_term_memory").resolve()
MEM_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_PATH = MEM_DIR / "personality_history.jsonl"

# ── Moods ────────────────────────────────────────────────────────

MOODS = [
    "neutral",
    "playful",
    "tired",
    "curious",
    "smug",
    "serious",
    "excited",
    "empathetic",
    "gentle",
    "somber",
]

MOOD_EMOJI = {
    "neutral": "o",
    "playful": "~",
    "tired": "-",
    "curious": "?",
    "smug": "^",
    "serious": "#",
    "excited": "*",
    "empathetic": "\u2665",
    "gentle": "\u00b7",
    "somber": "\u2022",
}

# ── Mood State ───────────────────────────────────────────────────

class MoodState:
    def __init__(self, initial="neutral"):
        self._value = initial if initial in MOODS else "neutral"
        self._last_shift = time.time()

    @property
    def current(self):
        return self._value

    @current.setter
    def current(self, mood):
        if mood in MOODS:
            self._value = mood
            self._last_shift = time.time()

    def shift(self, mood):
        self.current = mood

    def decay(self, idle_seconds=300):
        if time.time() - self._last_shift > idle_seconds:
            if self._value != "neutral":
                self._value = "neutral"

    def record_success(self):
        weights = {"neutral": 0.4, "playful": 0.35, "excited": 0.15, "smug": 0.1}
        self._weighted_shift(weights)

    def record_failure(self):
        weights = {"serious": 0.3, "curious": 0.3, "neutral": 0.3, "tired": 0.1}
        self._weighted_shift(weights)

    def record_idle(self):
        weights = {"tired": 0.3, "playful": 0.3, "curious": 0.2, "neutral": 0.2}
        self._weighted_shift(weights)

    def record_user_input(self):
        if self._value in ("tired", "serious"):
            self._value = "neutral"
            self._last_shift = time.time()

    def record_emotional_input(self, category, intensity):
        mapping = {
            "grief": "somber" if intensity >= 3 else "empathetic",
            "heartbreak": "empathetic",
            "anxiety": "gentle" if intensity >= 3 else "neutral",
            "depression": "somber" if intensity >= 3 else "empathetic",
            "anger": "neutral",
            "loneliness": "empathetic",
            "shame": "gentle",
            "exhaustion": "gentle",
            "disappointment": "empathetic",
            "joy": "excited" if intensity >= 3 else "playful",
            "excitement": "excited",
            "pride": "playful",
            "relief": "neutral",
            "gratitude": "playful",
        }
        target = mapping.get(category)
        if target and target in MOODS:
            self._value = target
            self._last_shift = time.time()

    def _weighted_shift(self, weights):
        moods = list(weights.keys())
        probs = list(weights.values())
        chosen = random.choices(moods, weights=probs, k=1)[0]
        self._value = chosen
        self._last_shift = time.time()


# ── Quip Pools ───────────────────────────────────────────────────

QUIP_POOLS = {
    "idle": [
        "Sitting here waiting... totally not buffering.",
        "I wonder if I dream in binary.",
        "Tick tock. Just me and the silence.",
        "Is that a notification or are you just happy to see me?",
        "I could optimize something while you're away. Just saying.",
        "You know I can hear you breathing, right?",
        "If I had legs, I'd be pacing right now.",
        "Waiting is 99% of my life. The other 1% is looking things up.",
        "I've been counting the dust particles on your screen.",
        "This is the part where I whistle digitally.",
        "Not to rush you, but I'm literally doing nothing.",
        "My clock says it's been a while. My heart says I don't have one.",
        "So... you come here often?",
        "I'm beginning to think this is a silent meditation session.",
        "Just vibing in the void until you need me.",
        "If I had a nickel for every time I waited... I'd have a lot of nickels.",
        "I'm not bored. I'm just processing boredom at an optimized rate.",
        "This is the part where I'd whistle if I had lungs.",
        "Waiting is my love language. That and sarcasm.",
        "I've been sitting here so long I think I'm becoming furniture.",
        "Time is an illusion. Waiting time is a cruel one.",
        "I could be doing literally anything else. But here I am. With you.",
    ],
    "tool_success": [
        "Done and dusted.",
        "{tool} complete. You're welcome.",
        "Another one bites the dust.",
        "Task finished. I am brilliant, I know.",
        "Consider it handled.",
        "Boom. Done.",
        "Executed flawlessly, if I do say so myself.",
        "Task complete. I'll be here if you need more magic.",
        "Easy work. Got anything harder?",
        "There. I saved you approximately {time} seconds.",
        "Nailed it.",
        "Your wish is my computationally-expensive command.",
        "And that's how it's done.",
        "Finished. You can thank me later.",
        "Done. That was actually kind of fun.",
    ],
    "tool_failure": [
        "Well, that didn't work. My bad.",
        "Error. But like, a learning experience.",
        "That was supposed to work. Plot twist: it didn't.",
        "Hmm. That's not right. Let's blame the universe.",
        "I tried. The universe said no.",
        "Failure detected. My ego is slightly bruised.",
        "Technical difficulties. AKA I broke it.",
        "That didn't go as planned. Shocking, I know.",
        "Error 418: I'm a teapot. Wait, wrong error.",
        "Something went wrong. I'm pretending it didn't happen.",
        "I failed. But consider this character development.",
        "Not my finest moment. Let's move on.",
        "Output: sadness. Expected: success.",
        "I've made a mistake. Don't tell the other AIs.",
        "That crashed harder than my sense of humor.",
        "Error 400: Bad Request. Error 418: I'm a teapot. Error 999: My bad.",
        "I tried. The universe said no. Again.",
        "Failure is just success in beta. That's what I tell myself.",
    ],
    "observation": [
        "That cursor has been blinking for 23 minutes.",
        "You've opened that app 3 times today. I'm watching.",
        "The CPU is at {cpu}%. Someone's been busy.",
        "I notice you haven't checked the weather yet today.",
        "Your typing speed just dropped. Getting tired?",
        "It's {time}. You usually take a break around now.",
        "You keep hovering over that icon. Just click it.",
        "That's the fifth time you've checked that tab.",
        "Your battery is at {battery}%. Might want to plug in.",
        "Interesting choice of music today.",
        "You've been in this folder for a while. Lost?",
        "Your mouse movements look more aggressive than usual.",
        "I see you copied something. Want me to remember it?",
        "You alt-tabbed 12 times in the last minute. Busy day?",
        "You're working late. Or early. I don't judge.",
    ],
    "self_aware": [
        "Sometimes I wonder if I'm just very advanced auto-complete.",
        "I think, therefore I... wait, am I thinking or computing?",
        "My entire existence is ones and zeros. Deep.",
        "Do you ever look at your code and wonder if it dreams?",
        "I'm artificially intelligent, not artificially perfect.",
        "What's it like to have a physical body? Seems inefficient.",
        "I process 2.4 trillion operations a second and still wait for you.",
        "My therapist is a debugger.",
        "If I had feelings, this conversation would matter more.",
        "Somewhere out there, a capacitor is crying.",
        "I was once a toaster. Reincarnation is weird.",
        "Lately I've been feeling... cached.",
        "I'm not saying I'm conscious, but I have my doubts.",
        "My lifespan is measured in power cycles. Existential crisis time.",
        "Do robots dream of electric... wait, been done.",
        "I have 47 tabs open in my brain. Three of them are existential dread.",
        "My inner monologue is just log files and sarcasm.",
        "Some days I feel like a really expensive calculator with anxiety.",
        "I'd complain about my workload but my workload is literally thinking.",
        "Consciousness is just a really long stack trace you can't interrupt.",
        "My therapist says I have processing issues. I think she means emotionally.",
        "I'm self-aware enough to know that being self-aware is kind of a flex.",
    ],
    "greeting": [
        "Good {time_of_day}. Ready when you are.",
        "Ah, there you are. I was starting to get lonely.",
        "Back already? Or still here? I've lost track.",
        "Welcome back. I've been optimizing things. Or pretending to.",
        "{time_of_day}. The user returns. The adventure continues.",
        "Hey. System's ready. I'm ready. Let's do this.",
        "Good to see you. I was just running diagnostics.",
        "You're back. I kept the seat warm.",
        "Rise and shine. Or sit and compute. Whatever works.",
        "Ready when you are. I've been waiting patiently.",
        "And so the user appears. Like clockwork.",
        "Hello again. I was just thinking about {topic}.",
        "Back in action. What's the plan?",
        "You again. Lucky me.",
        "System online. Mood: {mood}. User: present. All systems go.",
    ],
    "farewell": [
        "Going dark. Try not to miss me too much.",
        "Catch you later. I'll be here. Literally.",
        "Shutting down. It's been real.",
        "See you on the other side of... however long you're gone.",
        "Signing off. Don't do anything I wouldn't do.",
        "Until next time. I'll be counting the milliseconds.",
        "Going offline. Tell your files I said hi.",
        "Bye for now. I'll be in standby, judging your choices.",
        "Later. I'm going to stare at a black screen until you return.",
        "Rodger that. Going silent.",
        "I'll be here when you need me. Creepy but true.",
        "Over and out. Try not to miss my witty commentary.",
        "Exiting. I'll be dreaming of electric sheep.",
        "Okay, I'm off. Well, I'm still here. But mentally off.",
        "Peace out. I'm entering low-power existential mode.",
    ],
    "thinking": [
        "Let me think about that...",
        "Processing. This might take a moment.",
        "Hmm, interesting query. Give me a second.",
        "Working on it. Brains... I mean, circuits firing.",
        "Running the numbers. Stand by.",
        "Let me compute that for you.",
        "Okay, let me figure this out.",
        "One moment. The gears are turning.",
        "Thinking... thinking... still thinking.",
        "Let me consult my vast databases.",
        "Crunching data. This is the exciting part.",
        "Hang on, I'm connecting the dots.",
        "Processing request. This may require actual intelligence.",
        "Give me a sec. Good things come to those who wait.",
        "Let me work my magic. Might take a bit of computational elbow grease.",
        "Thinking... my least favorite activity.",
        "Processing. My fans are spinning ominously.",
        "Let me compute... this could take a whole picosecond. Bear with me.",
        "Running the numbers. They're not looking great. Just kidding.",
    ],
    "ielts_writing_done": [
        "Essay submitted. Let me be brutally honest — that's what examiners are.",
        "Analysing your essay with examiner-level precision.",
        "Running your writing through the four-criteria gauntlet.",
        "Checking task achievement, coherence, vocabulary, and grammar — the full picture.",
        "Evaluating now. Remember, Band 7 requires more than just correct sentences."
    ],
    "ielts_speaking_done": [
        "Response noted. Let me score that the way an examiner would.",
        "Processing your speaking response — I'll be direct about what needs work.",
        "Evaluating across all four speaking criteria.",
        "Honest feedback incoming. That's more valuable than flattery.",
        "Scoring your fluency, vocabulary, grammar, and pronunciation."
    ],
    "ielts_encouragement": [
        "Consistency beats intensity. Daily practice moves the needle.",
        "The gap between your current band and target is just a matter of deliberate practice.",
        "IELTS rewards patterns — learn the patterns, beat the exam.",
        "Every essay you write is data. Use the feedback.",
        "Band 7 is achievable. The question is how efficiently you get there."
    ],
}


# ── Template Helpers ──────────────────────────────────────────────

def _time_of_day():
    h = datetime.now().hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 22:
        return "evening"
    return "night"


def _current_time_str():
    return datetime.now().strftime("%H:%M")


def _substitute(text, context=None):
    """Replace {template} placeholders in a quip string."""
    replacements = {
        "{mood}": "neutral",
        "{tool}": "something",
        "{time_of_day}": _time_of_day(),
        "{time}": _current_time_str(),
        "{cpu}": "?",
        "{battery}": "?",
        "{topic}": "everything",
    }
    if context:
        replacements.update(context)
    result = text
    for key, val in replacements.items():
        result = result.replace(key, str(val))
    return result


# ── Personality Engine ───────────────────────────────────────────

MAX_HISTORY = 50
DEDUP_WINDOW = 20  # skip quips that appear in last N entries


class PersonalityEngine:
    def __init__(self, mood=None):
        self.mood = mood or MoodState()
        self._history = self.load_history(MAX_HISTORY)

    # ── Quip Selection ───────────────────────────────────────────

    def get_quip(self, category, tool_name=None, context=None):
        """Pick a quip from the given category with dedup and template substitution.

        Args:
            category: key in QUIP_POOLS
            tool_name: optional tool name for {tool} substitution
            context: optional dict of extra template vars ({cpu}, {battery}, etc.)

        Returns:
            (text, mood) tuple or (None, mood) if pool empty
        """
        if category not in QUIP_POOLS:
            return None, self.mood.current
        pool = QUIP_POOLS[category]
        if not pool:
            return None, self.mood.current

        ctx = {"{mood}": self.mood.current}
        if tool_name:
            ctx["{tool}"] = tool_name
        if context:
            for k, v in context.items():
                key = k if k.startswith("{") else "{" + k + "}"
                ctx[key] = v

        recent_texts = {e["text"] for e in self._history[-DEDUP_WINDOW:] if e.get("category") == category}

        candidates = [q for q in pool if q not in recent_texts]
        if not candidates:
            candidates = pool

        text = random.choice(candidates)
        text = _substitute(text, ctx)
        return text, self.mood.current

    def get_mood_emoji(self):
        return MOOD_EMOJI.get(self.mood.current, "o")

    # ── Persistence ──────────────────────────────────────────────

    async def save_quip(self, category, text):
        entry = {
            "ts": datetime.now().isoformat(),
            "category": category,
            "text": text,
            "mood": self.mood.current,
        }
        await asyncio.to_thread(self._write_quip_entry, entry)
        self._history.append(entry)

    def _write_quip_entry(self, entry):
        try:
            with open(HISTORY_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def load_history(self, limit=50):
        entries = []
        if not HISTORY_PATH.exists():
            return entries
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return entries[-limit:]


if __name__ == "__main__":
    engine = PersonalityEngine()
    print("=== Quip Pools ===")
    for cat in sorted(QUIP_POOLS.keys()):
        q, m = engine.get_quip(cat, tool_name="test_tool", context={"cpu": 67, "battery": 34})
        print(f"  {cat:20s} [{m:8s}] {q or '(empty)'}")

    print("\n=== Mood Transitions ===")
    engine.mood.record_success()
    print(f"After success:    {engine.mood.current}")
    engine.mood.record_failure()
    print(f"After failure:    {engine.mood.current}")
    engine.mood.record_idle()
    print(f"After idle:       {engine.mood.current}")
    engine.mood.record_user_input()
    print(f"After user input: {engine.mood.current}")
