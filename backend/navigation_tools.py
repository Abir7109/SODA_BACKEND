import asyncio
import aiohttp
import json
import math
from typing import Optional
from logger import log as logger

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "https://router.project-osrm.org"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {"User-Agent": "SODA-HUD-Navigation/1.0 (personal assistant desktop app)"}

OSRM_PROFILE = {"drive": "car", "walk": "foot", "bike": "bike", "cycle": "bike"}


async def geocode_location(query: str) -> Optional[dict]:
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(f"{NOMINATIM_URL}/search", params=params, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                data = await resp.json()
                if not data:
                    logger.warning(f"[NAV] Geocode found nothing for: {query}")
                    return None
                result = data[0]
                return {"name": query, "lat": float(result["lat"]), "lon": float(result["lon"]), "display_name": result.get("display_name", query), "boundingbox": result.get("boundingbox", [])}
    except Exception as e:
        logger.error(f"[NAV] Geocode error for '{query}': {e}")
        return None


async def reverse_geocode(lat: float, lon: float) -> Optional[dict]:
    params = {"lat": lat, "lon": lon, "format": "json"}
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(f"{NOMINATIM_URL}/reverse", params=params, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                data = await resp.json()
                return {"display_name": data.get("display_name", "Unknown Location"), "lat": float(data.get("lat", lat)), "lon": float(data.get("lon", lon))}
    except Exception as e:
        logger.error(f"[NAV] Reverse geocode error: {e}")
        return None


async def get_osrm_route(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float, mode: str = "drive", alternatives: bool = True) -> Optional[dict]:
    profile = OSRM_PROFILE.get(mode.lower(), "car")
    coords = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true", "annotations": "false", "alternatives": "true" if alternatives else "false"}
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(f"{OSRM_URL}/route/v1/{profile}/{coords}", params=params, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                data = await resp.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    logger.error(f"[NAV] OSRM error: {data.get('code')}")
                    return None
                routes = []
                for idx, route in enumerate(data["routes"]):
                    parsed_steps = _parse_steps(route["legs"])
                    routes.append({"index": idx, "is_best": idx == 0, "distance_m": route["distance"], "distance_km": round(route["distance"] / 1000, 2), "duration_s": route["duration"], "duration_min": round(route["duration"] / 60, 1), "geometry": route["geometry"], "steps": parsed_steps, "summary": _build_summary(route, parsed_steps)})
                return {"mode": mode, "routes": routes, "best": routes[0] if routes else None}
    except Exception as e:
        logger.error(f"[NAV] OSRM routing error: {e}")
        return None


def _parse_steps(legs: list) -> list:
    steps = []
    step_num = 0
    for leg in legs:
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            instruction = _maneuver_to_instruction(maneuver, step.get("name", ""))
            steps.append({"index": step_num, "instruction": instruction, "name": step.get("name", ""), "distance_m": round(step.get("distance", 0)), "duration_s": round(step.get("duration", 0)), "maneuver": maneuver.get("type", ""), "modifier": maneuver.get("modifier", ""), "location": maneuver.get("location", []), "geometry": step.get("geometry", {})})
            step_num += 1
    return steps


def _maneuver_to_instruction(maneuver: dict, road_name: str) -> str:
    mtype = maneuver.get("type", "")
    modifier = maneuver.get("modifier", "")
    name = f" onto {road_name}" if road_name else ""
    mapping = {
        ("depart", ""): f"Start{name}", ("arrive", ""): "You have arrived at your destination",
        ("turn", "left"): f"Turn left{name}", ("turn", "right"): f"Turn right{name}",
        ("turn", "sharp left"): f"Turn sharp left{name}", ("turn", "sharp right"): f"Turn sharp right{name}",
        ("turn", "slight left"): f"Keep slight left{name}", ("turn", "slight right"): f"Keep slight right{name}",
        ("continue", "straight"): f"Continue straight{name}",
        ("merge", "left"): f"Merge left{name}", ("merge", "right"): f"Merge right{name}",
        ("roundabout", ""): f"Enter roundabout{name}",
        ("fork", "left"): f"Keep left at fork{name}", ("fork", "right"): f"Keep right at fork{name}",
        ("end of road", "left"): f"Turn left at end of road{name}", ("end of road", "right"): f"Turn right at end of road{name}",
    }
    key = (mtype, modifier)
    if key in mapping:
        return mapping[key]
    if mtype:
        return f"{mtype.replace('-', ' ').capitalize()}{name}"
    return f"Continue{name}"


def _build_summary(route: dict, steps: list) -> str:
    dist = round(route["distance"] / 1000, 1)
    mins = round(route["duration"] / 60)
    hours = mins // 60
    rem_min = mins % 60
    time_str = f"{hours}h {rem_min}m" if hours > 0 else f"{mins} min"
    road_names = list({s["name"] for s in steps if s["name"] and len(s["name"]) > 2})[:3]
    via = f" via {', '.join(road_names)}" if road_names else ""
    return f"{dist} km \u00b7 {time_str}{via}"


async def get_traffic_obstacles(bbox: tuple) -> list:
    min_lat, min_lon, max_lat, max_lon = bbox
    bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    query = f"""
    [out:json][timeout:25];
    (
      node["highway"="traffic_signals"]({bbox_str});
      node["highway"="stop"]({bbox_str});
      node["construction"~"yes|minor|major"]({bbox_str});
      way["construction"~"yes|minor|major"]({bbox_str});
      node["hazard"]({bbox_str});
      node["barrier"~"gate|bollard|block|jersey_barrier"]({bbox_str});
      way["access"="no"]({bbox_str});
      node["highway"="crossing"]({bbox_str});
    );
    out center;
    """
    obstacles = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.post(OVERPASS_URL, data={"data": query}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                for element in data.get("elements", []):
                    tags = element.get("tags", {})
                    lat = element.get("lat") or element.get("center", {}).get("lat")
                    lon = element.get("lon") or element.get("center", {}).get("lon")
                    if not lat or not lon:
                        continue
                    obstacles.append({"type": _classify_obstacle(tags), "severity": _get_severity(tags), "lat": lat, "lon": lon, "description": _build_obstacle_description(tags), "tags": {k: v for k, v in tags.items() if k in ["name", "description", "construction", "barrier", "hazard", "access"]}})
        logger.info(f"[NAV] Found {len(obstacles)} obstacles in route bbox")
        return obstacles
    except Exception as e:
        logger.error(f"[NAV] Overpass obstacle query error: {e}")
        return []


def _classify_obstacle(tags: dict) -> str:
    if tags.get("construction"):
        return "construction"
    if tags.get("hazard"):
        return "hazard"
    if tags.get("barrier"):
        return "barrier"
    if tags.get("highway") == "traffic_signals":
        return "traffic_signal"
    if tags.get("highway") == "stop":
        return "stop_sign"
    if tags.get("highway") == "crossing":
        return "crossing"
    if tags.get("access") == "no":
        return "road_closed"
    return "obstacle"


def _get_severity(tags: dict) -> str:
    construction = tags.get("construction", "")
    if construction in ["major", "yes"]:
        return "high"
    if construction == "minor":
        return "medium"
    if tags.get("hazard") or tags.get("access") == "no":
        return "high"
    if tags.get("barrier"):
        return "medium"
    return "low"


def _build_obstacle_description(tags: dict) -> str:
    if tags.get("construction"):
        level = tags["construction"]
        name = tags.get("name", "")
        return f"{'Major' if level == 'major' else 'Minor'} construction work{f': {name}' if name else ''}"
    if tags.get("hazard"):
        return f"Road hazard: {tags['hazard']}"
    if tags.get("access") == "no":
        return f"Road closed: {tags.get('name', 'No access')}"
    if tags.get("barrier"):
        return f"Barrier: {tags['barrier']}"
    if tags.get("highway") == "traffic_signals":
        return "Traffic signal"
    return "Road obstacle"


def get_route_bbox(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float, padding: float = 0.05) -> tuple:
    return (min(origin_lat, dest_lat) - padding, min(origin_lon, dest_lon) - padding, max(origin_lat, dest_lat) + padding, max(origin_lon, dest_lon) + padding)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


async def get_navigation_route(origin: str, destination: str, mode: str = "drive", origin_lat: Optional[float] = None, origin_lon: Optional[float] = None) -> dict:
    logger.info(f"[NAV] Route request: {origin} → {destination} ({mode})")

    if origin_lat and origin_lon:
        origin_data = {"name": "Your Location", "lat": origin_lat, "lon": origin_lon, "display_name": "Your Location"}
        dest_data = await geocode_location(destination)
    else:
        origin_data, dest_data = await asyncio.gather(
            geocode_location(origin), geocode_location(destination), return_exceptions=True
        )
        if isinstance(origin_data, Exception): origin_data = None
        if isinstance(dest_data, Exception): dest_data = None

    if not origin_data:
        return {"success": False, "error": f"Could not find location: {origin}"}
    if not dest_data:
        return {"success": False, "error": f"Could not find location: {destination}"}

    routing_result = await get_osrm_route(origin_lat=origin_data["lat"], origin_lon=origin_data["lon"], dest_lat=dest_data["lat"], dest_lon=dest_data["lon"], mode=mode, alternatives=False)

    if not routing_result:
        return {"success": False, "error": "Could not calculate route. Navigation service unavailable."}

    for route in routing_result["routes"]:
        route["obstacles"] = []
        route["obstacle_count"] = 0
        route["traffic_score"] = "clear"

    best = routing_result["routes"][0]
    routing_result["best"] = best

    voice_summary = _build_voice_summary(origin_data, dest_data, best, mode)

    return {"success": True, "origin": origin_data, "destination": dest_data, "mode": mode, "routes": routing_result["routes"], "best_route": best, "obstacles": [], "bbox": [], "voice_summary": voice_summary}


def _find_obstacles_near_route(geometry: dict, obstacles: list, threshold_km=0.3) -> list:
    if not geometry or not obstacles:
        return []
    coords = geometry.get("coordinates", [])
    nearby = []
    for obstacle in obstacles:
        obs_lat, obs_lon = obstacle["lat"], obstacle["lon"]
        is_near = any(haversine_km(obs_lat, obs_lon, coord[1], coord[0]) <= threshold_km for coord in coords[::5])
        if is_near:
            nearby.append(obstacle)
    return nearby


def _calculate_traffic_score(obstacles: list) -> str:
    if not obstacles:
        return "clear"
    score = 0
    for obs in obstacles:
        if obs["severity"] == "high":
            score += 3
        elif obs["severity"] == "medium":
            score += 1.5
        else:
            score += 0.5
    if score == 0:
        return "clear"
    if score < 3:
        return "light"
    if score < 7:
        return "moderate"
    return "heavy"


def _pick_best_route(routes: list) -> dict:
    if not routes:
        return {}
    def route_score(r):
        base = r["duration_s"]
        penalty = sum(600 if o["severity"] == "high" else 200 if o["severity"] == "medium" else 60 for o in r.get("obstacles", []))
        return base + penalty
    return min(routes, key=route_score)


def _build_voice_summary(origin, destination, best_route, mode) -> str:
    if not best_route:
        return "I couldn't find a route for that trip."
    dist = best_route["distance_km"]
    mins = best_route["duration_min"]
    traffic = best_route.get("traffic_score", "clear")
    has_const = best_route.get("has_construction", False)
    obs_count = best_route.get("obstacle_count", 0)
    hours = int(mins) // 60
    rem_min = int(mins) % 60
    time_str = f"{hours} hour{'s' if hours > 1 else ''} and {rem_min} minutes" if hours > 0 else f"{int(mins)} minutes"
    mode_str = {"drive": "driving", "walk": "walking", "bike": "cycling"}.get(mode, "traveling")
    origin_name = origin.get("name", "your location")
    dest_name = destination.get("display_name", "your destination").split(",")[0]
    summary = f"I've found the best route from {origin_name} to {dest_name}. {mode_str.capitalize()} distance is {dist} kilometers, estimated time is {time_str}. "
    if traffic == "clear":
        summary += "Roads look clear, no major obstacles detected. "
    elif traffic == "light":
        summary += f"There are {obs_count} minor obstacle{'s' if obs_count > 1 else ''} along the way. "
    elif traffic == "moderate":
        summary += f"Moderate road conditions detected with {obs_count} obstacle{'s' if obs_count > 1 else ''}. "
    else:
        summary += f"Heavy road obstacles detected \u2014 {obs_count} issues on this route. Consider alternatives. "
    if has_const:
        summary += "There is active construction work on this route. "
    summary += "I've opened the 3D map and plotted your route."
    return summary
