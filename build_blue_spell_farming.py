"""Build the local level-75 Blue Magic farming catalog.

Source rows are factual spell/mob/zone data published by ffxibluemage.com.
The generated catalog removes post-ToAU zones and derives the minimum learning
skill from the HorizonXI rule that the caster may be at most 29 skill below cap.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.request import urlopen

SOURCE = "https://ffxibluemage.com/blue_magic_data.json"
OUTPUT = Path("static/blue_spell_farming.json")

DENIED_ZONE_PARTS = (
    "abyssea", "escha", "reisenjima", "ceizak", "yahse", "foret de hennetiel",
    "morimar", "marjami", "kamihr", "yorcia", "ra'kaznar", "dho gates",
    "moh gates", "sih gates", "woh gates", "crawler's nest [s]", " (s)",
    "everbloom hollow", "maze voucher", "walk of echoes",
)

ZONE_FIXES = {
    "Boyahda Tree": "The Boyahda Tree",
    "Crawlers' Nest": "Crawler's Nest",
    "Eldieme Necropolis": "The Eldieme Necropolis",
    "Lower Delkfutt Tower": "Lower Delkfutt's Tower",
    "Lower Delkfutts Tower": "Lower Delkfutt's Tower",
    "Middle Delkfutt Tower": "Middle Delkfutt's Tower",
    "Riverne - Site A01": "Riverne - Site #A01",
    "Riverne Site #B01": "Riverne - Site #B01",
    "Sanctuary of Zi'Tah": "The Sanctuary of Zi'Tah",
}


def blue_magic_cap(level: int) -> int:
    """Return the classic A+ Blue Magic skill cap at a job level."""
    if level <= 50:
        return level * 3 + 3
    if level <= 60:
        return 153 + (level - 50) * 5
    if level <= 70:
        return 203 + int((level - 60) * 4.5)
    return 248 + round((level - 70) * 5.6)


def clean_level(value: object) -> int | None:
    match = re.match(r"\d+", str(value or ""))
    return int(match.group()) if match else None


def clean_zone(value: object) -> str | None:
    zone = " ".join(str(value or "").split()).strip()
    if not zone or len(zone) > 70 or zone.startswith("**"):
        return None
    lower = zone.lower()
    if any(part in lower for part in DENIED_ZONE_PARTS):
        return None
    return ZONE_FIXES.get(zone, zone)


def build(rows: list[dict]) -> dict:
    catalog = []
    seen = set()
    for row in rows:
        spell_level = clean_level(row.get("spell_level"))
        zone = clean_zone(row.get("zone"))
        spell = " ".join(str(row.get("name") or "").split())
        monster = " ".join(str(row.get("monster_name") or "").split())
        if not spell_level or spell_level > 75 or not zone or not spell or not monster:
            continue
        minimum = clean_level(row.get("min_level"))
        maximum = clean_level(row.get("max_level"))
        key = (spell.lower(), monster.lower(), zone.lower(), minimum, maximum)
        if key in seen:
            continue
        seen.add(key)
        cap = blue_magic_cap(spell_level)
        catalog.append({
            "spell": spell,
            "spell_level": spell_level,
            "skill_cap": cap,
            "minimum_skill": max(0, cap - 29),
            "monster": monster,
            "zone": zone,
            "monster_min": minimum,
            "monster_max": maximum,
            "source": row.get("link") or "",
        })
    catalog.sort(key=lambda item: (item["spell_level"], item["spell"], item["zone"], item["monster"]))
    return {
        "source": SOURCE,
        "horizon_rule_source": "https://horizonffxi.wiki/Category:Blue_Magic",
        "era": "Original through Treasures of Aht Urhgan; level cap 75",
        "rows": catalog,
    }


def main() -> None:
    with urlopen(SOURCE, timeout=30) as response:
        rows = json.load(response)
    payload = build(rows)
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    spells = {row["spell"] for row in payload["rows"]}
    print(f"Wrote {len(payload['rows'])} farming targets for {len(spells)} spells to {OUTPUT}")


if __name__ == "__main__":
    main()
