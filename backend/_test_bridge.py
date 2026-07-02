import sys, time, json
sys.path.insert(0, "backend")
from spotify_bridge import search, get_status, play_track, play_pause, set_volume

# 1. Search via extension
print("=== SEARCH ===")
t0 = time.time()
try:
    data = search("adele hello", limit=2)
    print(f"Time: {time.time()-t0:.1f}s")
    tracks = (data.get("tracks") or {}).get("items") or []
    print(f"Tracks: {len(tracks)}")
    for t in tracks:
        artist = t["artists"][0]["name"] if t.get("artists") else "?"
        print(f'  {t["name"]} - {artist}')
except Exception as e:
    print(f"Search error: {e}")
    print(f"Data: {data}")

# 2. Status
print("\n=== STATUS ===")
try:
    s = get_status()
    print(f"Playing: {s.get('playing')}, Volume: {s.get('volume'):.2f}")
    tr = s.get("track", {})
    if tr:
        print(f'Track: {tr.get("title")} - {tr.get("artist")}')
except Exception as e:
    print(f"Status error: {e}")

# 3. Play
print("\n=== PLAY ===")
if tracks:
    t = tracks[0]
    try:
        play_track(t["id"])
        print(f'Playing: {t["name"]}')
    except Exception as e:
        print(f"Play error: {e}")

# 4. Status after play
time.sleep(2)
try:
    s = get_status()
    print(f'Now playing: {s.get("track", {}).get("title")}')
except Exception as e:
    print(f"Status error: {e}")

print("\n=== DONE ===")
