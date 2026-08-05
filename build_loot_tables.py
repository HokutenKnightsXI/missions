"""Build the static Horizon-era loot index from LandSandBoat SQL exports."""

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen


BASE = "https://raw.githubusercontent.com/LandSandBoat/server/refs/heads/base/sql"
SOURCES = {"drops": f"{BASE}/mob_droplist.sql", "zones": f"{BASE}/zone_settings.sql"}
RATE_VARIABLES = {
    "@ALWAYS": 1000, "@VCOMMON": 240, "@COMMON": 150, "@UNCOMMON": 100,
    "@RARE": 50, "@VRARE": 10, "@SRARE": 5, "@URARE": 1,
}
TH_TABLE = (
    (24, 15, 10, 5, 1, .5, .1),
    (48, 30, 12, 6, 1.5, .75, .2),
    (56, 40, 15, 7, 2, 1, .3),
    (60, 42.5, 16.5, 7.5, 2.25, 1.2, .35),
    (64, 45, 18, 8, 2.5, 1.4, .4),
)
EXCLUDED_ZONES = {"Everbloom_Hollow", "Ruhotz_Silvermines", "Ghoyus_Reverie",
                  "Walk_of_Echoes", "Provenance"}


def fetch(url):
    request = Request(url, headers={"User-Agent": "HokutenLootIndex/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def rate_value(raw):
    return RATE_VARIABLES.get(raw.strip(), int(raw) if raw.strip().isdigit() else 0)


def th_rate(base_rate, th):
    """Convert a SQL per-1000 rate to the FFXI TH rarity-bracket percentage."""
    if base_rate >= 1000:
        return 100.0
    bracket = next((index for index, floor in enumerate((240, 150, 100, 50, 10, 5, 1))
                    if base_rate >= floor), 6)
    return TH_TABLE[th][bracket]


def allowed_zone(zone_id, name):
    if not name or zone_id > 255:
        return False
    return not (name.startswith("Abyssea-") or "_[S]" in name or name in EXCLUDED_ZONES)


def parse_zones(sql):
    zones = {}
    pattern = re.compile(
        r"INSERT INTO `zone_settings` VALUES \((\d+),\d+,'[^']*',\d+,'([^']+)',[^;]+;",
        re.I,
    )
    for zone_id, name in pattern.findall(sql):
        zones[int(zone_id)] = name
    return zones


def parse_drops(sql, zones):
    current_zone = current_mob = None
    rolls = defaultdict(list)
    block = re.compile(r"-- ZoneID:\s*(\d+)\s*-\s*(.+)$")
    insert = re.compile(
        r"VALUES \((\d+),(\d+),(\d+),([^,]+),(\d+),([^\)]+)\);\s*--\s*(.+?)(?:\s*\([^\)]*\))?$"
    )
    for line in sql.splitlines():
        heading = block.search(line)
        if heading:
            current_zone, current_mob = int(heading.group(1)), heading.group(2).strip()
            continue
        match = insert.search(line)
        if not match or current_zone is None or not allowed_zone(current_zone, zones.get(current_zone, "")):
            continue
        _drop_id, drop_type, _group_id, group_rate, _item_id, item_rate, item_name = match.groups()
        drop_type = int(drop_type)
        if drop_type not in (0, 1):
            continue
        group_rate, item_rate = rate_value(group_rate), rate_value(item_rate)
        rates = []
        for th in range(5):
            chance = th_rate(item_rate, th) if drop_type == 0 else th_rate(group_rate, th) * item_rate / 1000
            rates.append(min(100.0, chance))
        key = (zones[current_zone].replace("_", " "), current_mob.replace("_", " "), item_name.strip())
        rolls[key].append(rates)
    rows = []
    for (zone, mob, item), chances in rolls.items():
        combined = [100 * (1 - math.prod(1 - roll[th] / 100 for roll in chances)) for th in range(5)]
        rows.append([zone, mob, item, *[round(value, 3) for value in combined], len(chances)])
    return sorted(rows, key=lambda row: (row[0].casefold(), row[1].casefold(), row[2].casefold()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("static/loot_tables.json"))
    args = parser.parse_args()
    zones = parse_zones(fetch(SOURCES["zones"]))
    rows = parse_drops(fetch(SOURCES["drops"]), zones)
    payload = {"source": SOURCES["drops"], "th_max": 4, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(rows):,} filtered loot rows to {args.output}")


if __name__ == "__main__":
    main()
