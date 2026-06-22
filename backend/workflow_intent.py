import re
import time

CONTEXT_TIMEOUT = 60
MAX_CONTEXT_CHARS = 5000
CONTEXT_DECAY = 0.5
SCORE_THRESHOLD = 6
MIN_UTTERANCE_LENGTH = 8

class WorkflowIntentMatcher:
    def __init__(self):
        self.workflows = {
            "outside": {
                "phrases": [
                    "heading out", "going outside", "leaving now", "on my way",
                    "going out", "about to go", "stepping out", "getting ready to leave",
                    "time to go", "need to go out", "leave the house", "head out",
                    "going somewhere", "on the move", "heading over",
                    "leaving for", "on my way to", "im off",
                    "ready to go", "time to leave", "got to go",
                    "weather outside", "weather today", "what's the weather",
                    "whats the weather", "how is the weather", "how's the weather",
                    "is it raining", "check the weather", "temperature outside",
                    "আমি বের হচ্ছি", "বাইরে যাব", "রওনা দিচ্ছি", "আবহাওয়া কেমন",
                ],
                "keywords": [
                    "outside", "leaving", "heading out", "commute",
                    "step out", "going", "leave", "headed", "leaving for",
                    "weather", "raining", "temperature", "forecast","বাইরে","বের হব","রওনা","যাব","আবহাওয়া","বের হচ্ছি",
                ],
                "catch": r"\b(head(ing\s)?out|going\s(outside|out)|leaving|on (my|the) (way|move)|step(ping)?\s?out|leaving for|ready to go|im off|time to (go|leave)|weather|raining|temperature|forecast|বাইরে|রওনা|বের হচ্ছি|বাইরে যাব|আবহাওয়া)\b",
            },
            "project-review": {
                "phrases": [
                    "project status", "project review", "project overview",
                    "how's the project", "check my project", "project health",
                    "project progress", "show project", "project update",
                    "project report", "review my project", "project check",
                    "how are the projects", "show me my projects",
                    "প্রজেক্টের অবস্থা", "প্রজেক্ট রিভিউ", "প্রজেক্ট চেক",
                ],
                "keywords": [
                    "project", "review project", "project status","প্রজেক্ট","প্রকল্প","প্রজেক্ট রিভিউ","প্রজেক্টের","রিভিউ",
                ],
                "catch": r"\bproject\s+(status|review|overview|health|progress|update|report|check)\b|প্রজেক্ট|প্রকল্প",
            },

            "break-time": {
                "phrases": [
                    "take a break", "need a break", "break time", "coffee break",
                    "lunch time", "taking a break", "rest time", "stretch break",
                    "quick break", "break now", "time for a break", "step away",
                    "pause", "refresh", "take a rest", "need to rest",
                    "time to eat", "grab a coffee", "taking a rest",
                    "i need to rest", "break reminder", "let me rest",
                    "বিরতি দরকার", "ব্রেক নেব", "লাঞ্চ টাইম",
                    "বিশ্রাম নেব", "একটু বিরতি", "কফি খাব",
                ],
                "keywords": [
                    "break", "lunch", "rest", "coffee", "pause", "stretch","বিরতি","ব্রেক","লাঞ্চ","কফি","বিশ্রাম","breck","brek","bira","lunch","khawa","braek",
                ],
                "catch": r"\b((take|need|time for) a (break|rest)|break time|lunch|coffee break|rest|pause|stretch|grab a coffee|time to eat|বিরতি|ব্রেক|বিশ্রাম|লাঞ্চ)\b",
            },
            "pentest-scan": {
                "phrases": [
                    "penetration test", "pentest", "run pentest",
                    "vulnerability scan", "hack this",
                    "check vulnerabilities",
                    "scan for vulnerabilities", "run a security scan",
                    "penetration testing", "hack that",
                    "pentest this",
                ],
                "keywords": [
                    "pentest", "penetration", "vulnerability",
                    "hack", "exploit",
                ],
                "catch": r"\b(?:pentest|penetration\s?test|vulnerability\s?scan|hack\s+(?:this|that))\b",
            },
        }

        self.context_window = []
        self._last_wf_cooldown = {}  # per-workflow cooldown tracking
        self.learned_keywords = {}   # {wf_name: {keyword: frequency}} from memory

    def inject_learned(self, workflow_name, keywords, weight=2):
        if keywords:
            self.learned_keywords[workflow_name] = {"keywords": keywords, "weight": weight}

    def can_fire(self, wf_name, cooldown=60):
        now = time.time()
        last = self._last_wf_cooldown.get(wf_name, 0)
        if now - last >= cooldown:
            self._last_wf_cooldown[wf_name] = now
            return True
        return False

    def feed(self, text):
        now = time.time()
        self.context_window.append((now, text.strip().lower()))
        cutoff = now - CONTEXT_TIMEOUT
        self.context_window = [(t, txt) for t, txt in self.context_window if t > cutoff]
        total = sum(len(t) for _, t in self.context_window)
        if total > MAX_CONTEXT_CHARS:
            self.context_window = self.context_window[-(MAX_CONTEXT_CHARS // 40):]

    def _score_text(self, text):
        scores = {name: 0 for name in self.workflows}
        for wf_name, wf_data in self.workflows.items():
            score = 0
            for phrase in wf_data["phrases"]:
                if phrase.lower() in text:
                    score += 5
                    break
            for keyword in wf_data["keywords"]:
                if keyword.lower() in text:
                    score += 3
                    break
            try:
                matches = re.findall(wf_data["catch"], text, re.IGNORECASE)
                score += len(matches) * 3
            except re.error:
                pass
            # Learned keywords (from memory) — lower weight
            if wf_name in self.learned_keywords:
                lk = self.learned_keywords[wf_name]
                for kw in lk["keywords"]:
                    if kw in text:
                        score += lk["weight"]
                        break
            scores[wf_name] = score
        return scores

    def match_with_context(self, text):
        if not text or not text.strip():
            return None
        text = text.strip()
        if len(text) < MIN_UTTERANCE_LENGTH:
            return None
        self.feed(text)

        current_scores = self._score_text(text.strip().lower())

        best_current = max(current_scores, key=current_scores.get)
        if current_scores[best_current] >= SCORE_THRESHOLD and self.can_fire(best_current):
            return best_current

        ctx_scores = {name: 0 for name in self.workflows}
        now = time.time()
        for ts, txt in self.context_window[:-1]:
            age = now - ts
            decay = CONTEXT_DECAY ** max(0.1, age)
            chunk_scores = self._score_text(txt)
            for name in ctx_scores:
                ctx_scores[name] += chunk_scores[name] * decay

        blended = {}
        for name in current_scores:
            blended[name] = current_scores[name] + ctx_scores[name] * 0.5

        best_name = max(blended, key=blended.get)
        if blended[best_name] >= SCORE_THRESHOLD and self.can_fire(best_name):
            return best_name
        return None


intent_matcher = WorkflowIntentMatcher()