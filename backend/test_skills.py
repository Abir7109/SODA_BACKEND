"""Self-check for the skills layer: load → register → render → run.

Run: py -3.11 backend/test_skills.py
Exits 0 on pass, 1 on failure.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

VALID = """\
[skill]
name = "test_echo"
description = "Chains two steps"
user_invocable = true

[skill.params]
msg = { type = "string", description = "Message", default = "hi" }

[[skill.steps]]
tool_name = "get_system_status"
arguments_template = '{}'
output_key = "sys"

[[skill.steps]]
tool_name = "remember_fact"
arguments_template = '{"key": "skills_selfcheck", "value": "{sys}"}'
output_key = "saved"
"""

MALFORMED = "this is not toml at all [["


def main() -> int:
    import skills
    from tools import tools_list

    tmp = Path(tempfile.mkdtemp(prefix="soda_skills_"))
    (tmp / "test_echo.toml").write_text(VALID, encoding="utf-8")
    (tmp / "broken.toml").write_text(MALFORMED, encoding="utf-8")
    skills.SKILLS_DIR = tmp  # redirect before load

    decls = tools_list[0]["function_declarations"]
    before = len(decls)
    n = skills.load_skills(tools_list)
    assert n == 1, f"expected 1 skill registered (malformed skipped), got {n}"
    assert len(decls) == before + 1

    decl = next(d for d in decls if d["name"] == "test_echo")
    assert decl["parameters"]["properties"]["msg"]["type"] == "string"
    assert "required" not in decl["parameters"], "defaulted param must not be required"

    # Renderer: substitution, escaping, missing-key visibility
    assert skills._render('{"a": "{x}"}', {"x": 'he"llo'}) == '{"a": "he\\"llo"}'
    assert skills._render('{"a": "{missing}"}', {}) == '{"a": "{missing}"}'
    assert skills._render('{"n": 5}', {}) == '{"n": 5}'

    # Non-invocable skill loads but is NOT registered
    (tmp / "hidden.toml").write_text(
        '[skill]\nname = "hidden"\ndescription = "x"\nuser_invocable = false\n'
        '[[skill.steps]]\ntool_name = "get_system_status"\n', encoding="utf-8")
    assert skills.load_skills(tools_list) == 0

    # End-to-end: run registered skill through dispatch entry point.
    # Step 2 embeds step 1's output via {sys} — proves real chaining.
    r = asyncio.run(skills.call_registered("test_echo", {}))
    assert r and r.get("success") is True, r
    assert "sys" in r["outputs"] and "saved" in r["outputs"], r
    assert "os" in r["outputs"]["sys"], "step-1 output should be system status"

    # Prove step 2 actually received step-1 output (memory round-trip)
    from tool_dispatch import dispatch_local_tool
    recalled = asyncio.run(dispatch_local_tool("recall_facts", {"query": "skills_selfcheck"}))
    facts = json.dumps(recalled, default=str)
    assert "skills_selfcheck" in facts, f"chained value not stored: {recalled}"
    asyncio.run(dispatch_local_tool("forget_fact", {"key": "skills_selfcheck"}))

    # Unknown name passes through as None
    assert asyncio.run(skills.call_registered("nope", {})) is None

    # Cycle guard: skill invoking itself
    skills._registry["cyc"] = {"name": "cyc", "steps": [{"tool_name": "cyc"}]}
    r2 = asyncio.run(skills.call_registered("cyc", {}))
    assert r2 and "cycle" in r2["error"], r2

    skills._registry.clear()
    skills._running.clear()
    print("Skills self-check PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"Skills self-check FAILED: {e}")
        sys.exit(1)
