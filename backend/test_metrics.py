"""Runnable self-check for metrics.py — run: py -3.11 backend/test_metrics.py"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import metrics

d = pathlib.Path(tempfile.mkdtemp())
metrics.DB_PATH = d / "metrics.db"

metrics.record_tool_run("t1", 12.5, True)
metrics.record_tool_run("t2", 40.0, False)
metrics.record_tool_run("t1", 7.5, True)
metrics.record_turn(850.0)
metrics.record_usage(100, 50)

s = metrics.get_summary()
assert s["tools"]["count"] == 3, s
assert s["tools"]["success_rate"] == round(2 / 3, 3), s
assert s["tools"]["avg_duration_ms"] == round((12.5 + 40.0 + 7.5) / 3, 1), s
assert s["tools"]["top"][0]["name"] == "t1" and s["tools"]["top"][0]["count"] == 2, s["tools"]["top"]
assert s["turns"]["count"] == 1 and s["turns"]["avg_first_audio_ms"] == 850, s["turns"]
assert s["usage"] == {"tokens_in": 100, "tokens_out": 50}, s["usage"]

# bad/edge hours input must not raise or crash
assert metrics.get_summary(hours=0)["tools"]["count"] == 3  # clamped to 1h, rows still inside window
assert metrics.get_summary(hours="bogus")["tools"]["count"] == 3

# broken DB path: record + summary must not raise
blocker = d / "blocker"
blocker.write_text("not a dir")
metrics.DB_PATH = blocker / "metrics.db"
metrics.record_tool_run("x", 1.0, True)
s2 = metrics.get_summary()
assert "tools" in s2 and s2["tools"]["count"] == 0, s2

# bad hours input must not raise
assert "tools" in metrics.get_summary(hours="bogus")

print("metrics tests PASSED")
