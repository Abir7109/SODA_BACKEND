"""
Spotify workflow — search + play specific result via direct API.
No UI automation, no OCR, no AI Vision.
"""

from logger import log
from play_history import record_play
from spotify_bridge import search, play_track, play_uri, get_status


def search_music(query):
    """Search Spotify and return formatted results for the frontend.

    Returns:
        {"success": True, "query": "...", "results": [
            {"index": 1, "title": "...", "type": "track", "uri": "spotify:track:..."},
            ...
        ]}
    """
    try:
        data = search(query, limit=10)
        if not data:
            log.warning("[Workflow] search_music: no results for '%s'", query)
            return {"success": True, "query": query, "results": []}

        results = []
        index = 0

        # Tracks
        tracks = (data.get("tracks") or {}).get("items") or []
        for t in tracks:
            index += 1
            artists = ", ".join(a["name"] for a in (t.get("artists") or []))
            title = f'{t["name"]} — {artists}' if artists else t["name"]
            results.append({
                "index": index,
                "title": title,
                "type": "track",
                "uri": t.get("uri", ""),
                "id": t.get("id", ""),
            })

        # Albums
        albums = (data.get("albums") or {}).get("items") or []
        for a in albums:
            index += 1
            title = f'{a["name"]} — {a["artists"][0]["name"]}' if a.get("artists") else a["name"]
            results.append({
                "index": index,
                "title": title,
                "type": "album",
                "uri": a.get("uri", ""),
                "id": a.get("id", ""),
            })

        # Artists
        artists = (data.get("artists") or {}).get("items") or []
        for a in artists:
            index += 1
            results.append({
                "index": index,
                "title": a.get("name", "Unknown Artist"),
                "type": "artist",
                "uri": a.get("uri", ""),
                "id": a.get("id", ""),
            })

        # Playlists
        playlists = (data.get("playlists") or {}).get("items") or []
        for p in playlists:
            index += 1
            results.append({
                "index": index,
                "title": p.get("name", "Unknown Playlist"),
                "type": "playlist",
                "uri": p.get("uri", ""),
                "id": p.get("id", ""),
            })

        log.info("[Workflow] search_music('%s'): %d results", query, len(results))
        return {"success": True, "query": query, "results": results}

    except Exception as e:
        log.error("[Workflow] search_music failed: %s", e)
        return {"success": False, "error": str(e)}


def play_music_result(query, index):
    """Play the Nth search result.

    Uses the Spotify API directly — no UI automation.
    If the result is a track, plays it directly.
    If it's an album/artist/playlist, starts playback of that context.

    Returns:
        {"success": True, "now_playing": {...}}
    """
    try:
        data = search(query, limit=max(index + 2, 10))
        if not data:
            return {"success": False, "error": "Search returned no results"}

        # Flatten all items into a single ordered list
        items = []
        for t in ((data.get("tracks") or {}).get("items") or []):
            items.append(("track", t))
        for a in ((data.get("albums") or {}).get("items") or []):
            items.append(("album", a))
        for a in ((data.get("artists") or {}).get("items") or []):
            items.append(("artist", a))
        for p in ((data.get("playlists") or {}).get("items") or []):
            items.append(("playlist", p))

        if index < 1 or index > len(items):
            log.warning("[Workflow] play_music_result: index %d out of range (1-%d)", index, len(items))
            return {"success": False, "error": f"Index {index} out of range (1-{len(items)})"}

        item_type, item = items[index - 1]
        uri = item.get("uri", "")
        item_id = item.get("id", "")

        if item_type == "track":
            title = item.get("name", "")
            artists = ", ".join(a["name"] for a in (item.get("artists") or []))
            log.info("[Workflow] Playing track %d: '%s' by %s (uri=%s)", index, title, artists, uri)
            play_track(item_id)
        else:
            name = item.get("name", "")
            log.info("[Workflow] Playing %s %d: '%s' (uri=%s)", item_type, index, name, uri)
            play_uri(uri)

        # Wait briefly for playback to start, then get now-playing info
        import time
        time.sleep(2.0)

        now_playing = _build_now_playing(item, item_type)
        record_play(query, now_playing.get("title", ""))
        log.info("[Workflow] Playback started: %s", now_playing.get("title"))

        return {
            "success": True,
            "now_playing": now_playing,
            "clicked": True,
        }

    except Exception as e:
        log.error("[Workflow] play_music_result failed: %s", e)
        return {"success": False, "error": str(e)}


def _build_now_playing(item, item_type):
    """Build now_playing dict from a search result item."""
    if item_type == "track":
        return {
            "title": item.get("name", ""),
            "artist": ", ".join(a["name"] for a in (item.get("artists") or [])),
            "album": item.get("album", {}).get("name", "") if isinstance(item.get("album"), dict) else "",
            "id": item.get("id", ""),
            "uri": item.get("uri", ""),
            "image": _get_image(item),
            "type": "track",
        }
    else:
        return {
            "title": item.get("name", ""),
            "artist": "",
            "album": "",
            "id": item.get("id", ""),
            "uri": item.get("uri", ""),
            "image": _get_image(item),
            "type": item_type,
        }


def _get_image(item):
    images = item.get("images") or []
    if not images:
        album = item.get("album")
        if isinstance(album, dict):
            images = album.get("images") or []
    if images:
        return images[0].get("url", "")
    return ""
