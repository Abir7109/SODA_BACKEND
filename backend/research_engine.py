import asyncio
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger("soda.research_engine")

# ponytail: inline agent imports rather than top-level to avoid circular deps


async def _web_search(query: str, num: int = 10) -> list[dict]:
    from agents.web_search_agent import WebSearchAgent
    agent = WebSearchAgent()
    r = await agent.execute(query=query, num_results=num)
    return r.get("results", [])


async def _fetch_page(url: str) -> dict:
    from agents.webpage_agent import WebpageAgent
    agent = WebpageAgent()
    r = await agent.execute(url=url)
    return r


async def _gemini_synthesize(topic: str, sources: list[dict], pages: list[dict]) -> str:
    import google.genai as genai
    key = os.getenv("SUB_AGENT_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    if not key:
        return "Synthesis unavailable: no API key"
    client = genai.Client(api_key=key)
    sources_text = "\n".join(f"- {s['title']}: {s['snippet'][:500]}" for s in sources[:10])
    pages_text = "\n\n".join(f"[{p.get('url','')}]\n{p.get('content','')[:2000]}" for p in pages[:5])
    prompt = f"""Research topic: {topic}

Search results:
{sources_text}

Scraped pages:
{pages_text}

Return a structured JSON with these keys:
- summary: 3-5 sentence overview
- key_findings: list of {{finding, source_url}} objects
- statistics: list of {{label, value, source_url}} for any numbers found
- chart_data: list of {{type: "bar"|"pie"|"line", title, labels: [str], values: [number], source_url}} when numeric comparisons exist
- sentiment: overall positive/negative/neutral
- quotes: list of notable {{quote, source_url}}

Return ONLY valid JSON, no markdown."""
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return {"summary": f"Research completed for {topic}. Synthesis failed.", "key_findings": [], "statistics": [], "chart_data": []}


_NUMERIC_PAT = re.compile(r'\$?[\d,]+\.?\d*\s*(million|billion|thousand|%|percent)?', re.IGNORECASE)


def _has_numeric_data(pages: list[dict]) -> bool:
    for p in pages[:3]:
        content = p.get("content", "")
        if _NUMERIC_PAT.search(content):
            return True
    return False


async def deep_research(topic: str, depth: str = "normal") -> dict:
    logger.info(f"[research] topic={topic}, depth={depth}")
    search_results = await _web_search(topic, num=12 if depth == "deep" else 8)
    if not search_results:
        return {"success": False, "error": "No search results found"}

    result = {
        "success": True,
        "topic": topic,
        "depth": depth,
        "sources_count": len(search_results),
        "search_results": search_results,
        "pages": [],
        "pages_read": 0,
        "synthesis": None,
        "has_charts": False,
        "chart_data": [],
    }

    if depth == "quick":
        return result

    urls = [s["url"] for s in search_results if s.get("url")][:5]
    pages = await asyncio.gather(*[_fetch_page(u) for u in urls], return_exceptions=True)
    valid = []
    for p in pages:
        if isinstance(p, dict) and p.get("content"):
            valid.append({"url": p.get("url", ""), "title": p.get("title", ""), "content": p.get("content", "")[:3000]})
    result["pages"] = valid
    result["pages_read"] = len(valid)

    if depth == "deep" and valid:
        synthesis = await _gemini_synthesize(topic, search_results, valid)
        result["synthesis"] = synthesis
        chart_data = synthesis.get("chart_data", [])
        if chart_data:
            result["has_charts"] = True
            result["chart_data"] = chart_data
        if not result.get("has_charts") and _has_numeric_data(valid):
            result["chart_data"] = _auto_extract_charts(valid, topic)

    return result


def _auto_extract_charts(pages: list[dict], topic: str) -> list[dict]:
    charts = []
    text = " ".join(p.get("content", "")[:1000] for p in pages[:3])
    nums = re.findall(r'(\d[\d,]*\.?\d*)', text)
    nums = [float(n.replace(",", "")) for n in nums if n.replace(",", "").replace(".", "").isdigit()]
    nums = [n for n in nums if 0 < n < 1e12]
    if len(nums) >= 3:
        labels = [f"Entry {i+1}" for i in range(min(len(nums), 10))]
        charts.append({
            "type": "bar",
            "title": f"Key figures from {topic}",
            "labels": labels,
            "values": nums[:10],
            "source_url": pages[0].get("url", ""),
        })
    return charts


async def export_research(data: dict, fmt: str = "json") -> dict:
    if fmt == "json":
        return {"success": True, "format": "json", "content": json.dumps(data, indent=2, default=str)}
    if fmt == "markdown":
        lines = [f"# Research: {data.get('topic', '')}", ""]
        if data.get("synthesis"):
            s = data["synthesis"]
            if isinstance(s, dict):
                lines.append(f"**Summary:** {s.get('summary', '')}")
                if s.get("key_findings"):
                    lines.extend(["", "## Key Findings", ""])
                    for f in s["key_findings"]:
                        lines.append(f"- {f.get('finding', '')} ({f.get('source_url', '')})")
                if s.get("statistics"):
                    lines.extend(["", "## Statistics", ""])
                    for st in s["statistics"]:
                        lines.append(f"- {st.get('label', '')}: {st.get('value', '')} ({st.get('source_url', '')})")
        lines.extend(["", "## Sources", ""])
        for s in data.get("search_results", []):
            lines.append(f"- [{s.get('title', '')}]({s.get('url', '')})")
        return {"success": True, "format": "markdown", "content": "\n".join(lines)}
    return {"success": False, "error": f"Unsupported format: {fmt}"}
