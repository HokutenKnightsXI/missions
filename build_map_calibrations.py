"""Build per-floor spawn-map transforms from public FFXIDB map metadata."""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DATA = Path("static/loot_tables.json")
OUTPUT = Path("static/map_calibrations.json")
MAP_DIR = Path("static/calibrated_maps")
MAP_HEADER = re.compile(
    r"id:\s*(\d+),\s*mult:\s*(-?[\d.]+),\s*xoff:\s*(-?[\d.]+),"
    r"\s*yoff:\s*(-?[\d.]+),\s*boxes:\s*\[", re.S)
BOX = re.compile(
    r"x1:\s*(-?[\d.]+),\s*y1:\s*(-?[\d.]+),\s*z1:\s*(-?[\d.]+),"
    r"\s*x2:\s*(-?[\d.]+),\s*y2:\s*(-?[\d.]+),\s*z2:\s*(-?[\d.]+)")


def get(url, binary=False):
    request = Request(url, headers={"User-Agent": "HokutenMapCalibration/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read() if binary else response.read().decode("utf-8", "replace")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def parse_maps(html):
    start = html.find("var maps =")
    end = html.find("// Helper function", start)
    if start < 0 or end < 0:
        return []
    source = html[start:end]
    headers = list(MAP_HEADER.finditer(source))
    maps = []
    for index, match in enumerate(headers):
        tail = source[match.end():headers[index + 1].start() if index + 1 < len(headers) else len(source)]
        boxes = [[float(value) for value in values] for values in BOX.findall(tail)]
        maps.append({"id": int(match.group(1)), "mult": float(match.group(2)),
                     "xoff": float(match.group(3)), "yoff": float(match.group(4)),
                     "boxes": boxes})
    return maps


def load_zone(zone_id, zone_name, mobs):
    for mob in mobs:
        try:
            html = get(f"https://www.ffxidb.com/zones/{zone_id}/{quote(slug(mob))}")
        except (HTTPError, URLError, TimeoutError):
            continue
        maps = parse_maps(html)
        if maps:
            for map_data in maps:
                destination = MAP_DIR / str(zone_id) / f"map_{map_data['id']:02d}.png"
                if not destination.exists():
                    try:
                        content = get(
                            f"https://www.ffxidb.com/public/img/maps/map_{zone_id:03d}_{map_data['id']:02d}.png",
                            binary=True)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(content)
                    except (HTTPError, URLError, TimeoutError):
                        pass
                map_data["image"] = destination.exists()
            return zone_name, maps
    return zone_name, []


def main():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    mobs_by_zone = {}
    for zone, mob, *_rest in payload["rows"]:
        mobs_by_zone.setdefault(zone, [])
        if mob not in mobs_by_zone[zone]:
            mobs_by_zone[zone].append(mob)
    results = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(load_zone, zone_id, zone, mobs_by_zone.get(zone, [])[:20])
                   for zone, zone_id in payload["zone_ids"].items() if zone in mobs_by_zone]
        for future in as_completed(futures):
            zone, maps = future.result()
            if maps:
                results[zone] = maps
    OUTPUT.write_text(json.dumps(results, separators=(",", ":")), encoding="utf-8")
    print(f"Calibrated {len(results)} zones with {sum(len(v) for v in results.values())} map floors")


if __name__ == "__main__":
    main()
