"""Skills — TOML-defined multi-step tool pipelines.

Drop a ``*.toml`` into ``projects/skills/`` and it becomes a first-class
Gemini tool; one call runs the whole step pipeline server-side through
``dispatch_local_tool`` (same path force_tool uses).

Adapted from open-jarvis/OpenJarvis skills system (Apache License 2.0),
simplified: TOML only (stdlib tomllib), no signatures/scanning/dependency
graphs — ceiling: no skill→skill steps (cycle guard rejects re-entry).

Format::

    [skill]
    name = "daily_briefing"
    description = "Weather + system status in one call"
    user_invocable = true

    [skill.params]
    location = { type = "string", description = "City for weather", default = "Dhaka" }

    [[skill.steps]]
    tool_name = "get_weather"
    arguments_template = '{"location": "{location}"}'
    output_key = "weather"

Placeholders ``{name}`` are substituted from params (call args override
defaults) and prior steps' ``output_key`` values. Strings are JSON-escaped
for in-quote use; a missing key leaves the placeholder visible.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import tomllib

from logger import log

SKILLS_DIR = Path("projects/skills")

# registered Gemini name -> manifest dict
_registry: dict = {}
# skills currently executing (cycle guard for hand-wired skill→skill steps)
_running: set = set()

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_MAX_NAME = 60


def _sanitize(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]", "_", raw)
    return s or "skill"


def _esc(value) -> str:
    """Render a value for substitution inside a JSON string/atom."""
    if isinstance(value, str):
        return json.dumps(value)[1:-1]  # escaped, outer quotes stripped
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _render(template: str, ctx: dict) -> str:
    """Substitute {placeholders}; unknown keys stay visible."""
    return _PLACEHOLDER.sub(
        lambda m: _esc(ctx[m.group(1)]) if m.group(1) in ctx else m.group(0),
        template,
    )


def _extract(result) -> str:
    """Step output stored under output_key — readable string for chaining."""
    if isinstance(result, dict):
        for key in ("result", "output", "text"):
            v = result.get(key)
            if isinstance(v, str):
                return v
        return json.dumps(result, ensure_ascii=False, default=str)
    return str(result)


def _decl_for(name: str, manifest: dict) -> dict:
    props = {}
    required = []
    for pname, pdef in (manifest.get("params") or {}).items():
        pdef = pdef if isinstance(pdef, dict) else {"type": "string"}
        props[pname] = {
            "type": pdef.get("type", "string"),
            "description": str(pdef.get("description", pname)),
        }
        if "default" not in pdef:
            required.append(pname)
    decl = {
        "name": name,
        "description": manifest.get("description") or f"Skill: {manifest['name']}",
        "parameters": {"type": "object", "properties": props},
    }
    if required:
        decl["parameters"]["required"] = required
    return decl


def _load_file(path: Path) -> Optional[dict]:
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except Exception as e:
        log.warning(f"[SKILLS] Skipping malformed {path.name}: {e}")
        return None
    skill = data.get("skill")
    if not isinstance(skill, dict) or not skill.get("name"):
        log.warning(f"[SKILLS] Skipping {path.name}: missing [skill] name")
        return None
    steps = [s for s in skill.get("steps", []) if isinstance(s, dict) and s.get("tool_name")]
    if not steps:
        log.warning(f"[SKILLS] Skipping {skill['name']}: no steps")
        return None
    return {
        "name": str(skill["name"]),
        "description": str(skill.get("description", "")),
        "user_invocable": bool(skill.get("user_invocable", True)),
        "params": skill.get("params") or {},
        "steps": steps,
        "source": str(path),
    }


def load_skills(tools_list) -> int:
    """Scan projects/skills/*.toml, register invocable skills as Gemini tools.

    Never raises — a bad file must not kill startup. Returns count registered.
    """
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    decls = tools_list[0]["function_declarations"]
    taken = {d.get("name") for d in decls} | set(_registry)

    registered = 0
    known = {m["name"] for m in _registry.values()}
    for path in sorted(SKILLS_DIR.glob("*.toml")):
        manifest = _load_file(path)
        if manifest is None:
            continue
        if manifest["name"] in known:
            continue  # already registered (reload safety)
        if not manifest["user_invocable"]:
            log.info(f"[SKILLS] Loaded '{manifest['name']}' (not model-invocable)")
            continue
        base = _sanitize(manifest["name"])[:_MAX_NAME]
        name = base
        i = 2
        while name in taken:
            suffix = f"_{i}"
            name = base[: _MAX_NAME - len(suffix)] + suffix
            i += 1
        taken.add(name)
        _registry[name] = manifest
        decls.append(_decl_for(name, manifest))
        registered += 1
        log.info(f"[SKILLS] Registered '{name}' "
                 f"({len(manifest['steps'])} steps, from {path.name})")

    if registered:
        log.info(f"[SKILLS] {registered} skill(s) available "
                 f"({len(list(SKILLS_DIR.glob('*.toml')))} file(s) in {SKILLS_DIR})")
    return registered


async def call_registered(name: str, args: dict, sio=None, audio_loop=None) -> Optional[dict]:
    """Run a skill pipeline. Returns None if *name* isn't a registered skill."""
    manifest = _registry.get(name)
    if manifest is None:
        return None
    if name in _running:
        return {"success": False,
                "error": f"Skill '{name}' tried to invoke itself (cycle). "
                         f"Restructure the skill steps."}

    # Params: defaults first, call args override
    ctx = {}
    for pname, pdef in (manifest.get("params") or {}).items():
        if isinstance(pdef, dict) and "default" in pdef:
            ctx[pname] = pdef["default"]
    ctx.update(args or {})

    from tool_dispatch import dispatch_local_tool

    _running.add(name)
    outputs = {}
    try:
        for i, step in enumerate(manifest["steps"], 1):
            tool = step["tool_name"]
            template = str(step.get("arguments_template", "{}"))
            rendered = _render(template, ctx)
            try:
                step_args = json.loads(rendered)
                if not isinstance(step_args, dict):
                    raise ValueError("arguments must be a JSON object")
            except (json.JSONDecodeError, ValueError) as e:
                return {"success": False,
                        "error": f"Skill '{name}' step {i} ({tool}): "
                                 f"bad arguments after rendering — {e}. "
                                 f"Rendered: {rendered[:200]}"}
            try:
                r = await dispatch_local_tool(tool, step_args, sio=sio, audio_loop=audio_loop)
            except Exception as e:
                return {"success": False,
                        "error": f"Skill '{name}' step {i} ({tool}) crashed: {e}"}
            if isinstance(r, dict) and r.get("success") is False:
                err = r.get("error", "failed")
                return {"success": False,
                        "error": f"Skill '{name}' step {i} ({tool}) failed: {err}",
                        "outputs": outputs}
            if step.get("output_key"):
                ctx[step["output_key"]] = _extract(r)
                outputs[step["output_key"]] = ctx[step["output_key"]]
    finally:
        _running.discard(name)

    return {"success": True, "skill": manifest["name"],
            "outputs": outputs,
            "result": _extract(outputs[list(outputs)[-1]]) if outputs else "done"}


def status() -> dict:
    return {"skills": len(_registry), "names": sorted(_registry)}
