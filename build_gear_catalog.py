"""Build a searchable level-75/ToAU equipment catalog for Gear Optimizer."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from missions import parse_gear_stats

ITEMS_SOURCE = "https://raw.githubusercontent.com/Windower/Resources/master/resources_data/items.lua"
DESCRIPTIONS_SOURCE = "https://raw.githubusercontent.com/Windower/Resources/master/resources_data/item_descriptions.lua"
LSB_BASE = "https://raw.githubusercontent.com/LandSandBoat/server/base/sql"
OUTPUT = Path("static/gear_catalog.json")

JOBS = {
    1: "WAR", 2: "MNK", 3: "WHM", 4: "BLM", 5: "RDM", 6: "THF",
    7: "PLD", 8: "DRK", 9: "BST", 10: "BRD", 11: "RNG", 12: "SAM",
    13: "NIN", 14: "DRG", 15: "SMN", 16: "BLU", 17: "COR", 18: "PUP",
}
RACES = {
    1: "Hume Male", 2: "Hume Female", 3: "Elvaan Male", 4: "Elvaan Female",
    5: "Tarutaru Male", 6: "Tarutaru Female", 7: "Mithra", 8: "Galka",
}
SLOTS = {
    0: "Main", 1: "Sub", 2: "Ranged", 3: "Ammo", 4: "Head", 5: "Body",
    6: "Hands", 7: "Legs", 8: "Feet", 9: "Neck", 10: "Waist",
    11: "Ear", 12: "Ear", 13: "Ring", 14: "Ring", 15: "Back",
}
ELEMENT_GLYPHS = {
    "\ue000": "Fire Resistance", "\ue001": "Ice Resistance",
    "\ue002": "Wind Resistance", "\ue003": "Earth Resistance",
    "\ue004": "Lightning Resistance", "\ue005": "Water Resistance",
    "\ue006": "Light Resistance", "\ue007": "Dark Resistance",
}
WEAPON_AH_CATEGORIES = {
    1: "hand-to-hand", 2: "daggers", 3: "swords", 4: "great-swords",
    5: "axes", 6: "great-axes", 7: "scythes", 8: "polearms",
    9: "katana", 10: "great-katana", 11: "clubs", 12: "staves",
    25: "ranged", 26: "ranged", 27: "ammo-misc",
    40: "instruments", 41: "instruments", 42: "instruments",
}
ARMOR_AH_CATEGORIES = {
    "Sub": "shields", "Ammo": "ammo-misc", "Head": "head", "Body": "body",
    "Hands": "hands", "Legs": "legs", "Feet": "feet", "Neck": "neck",
    "Waist": "waist", "Ear": "earrings", "Ring": "rings", "Back": "back",
}


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "HokutenGearCatalog/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def lua_string(record: str, field: str) -> str:
    match = re.search(rf'(?:^|,){re.escape(field)}="((?:\\.|[^"\\])*)"', record)
    if not match:
        return ""
    return match.group(1).replace(r'\"', '"').replace(r"\n", "\n").replace(r"\\", "\\")


def lua_int(record: str, field: str) -> int:
    match = re.search(rf"(?:^|,){re.escape(field)}=(-?\d+)", record)
    return int(match.group(1)) if match else 0


def bit_values(mask: int, values: dict[int, str]) -> list[str]:
    return list(dict.fromkeys(name for bit, name in values.items() if mask & (1 << bit)))


def classic_era_item(item_id: int) -> bool:
    # Original through ToAU equipment occupies the original armor/weapon DAT ranges.
    # Later expansions largely moved equipment into lower reclaimed and higher ranges.
    return 12416 <= item_id <= 19199


def auction_house_category(category: str, slots: list[str], skill: int) -> str:
    if category == "Weapon":
        if "Ammo" in slots:
            return "ammo-misc"
        if "Sub" in slots and skill == 0:
            return "grips"
        return WEAPON_AH_CATEGORIES.get(skill, "ranged" if "Ranged" in slots else "")
    return next((ARMOR_AH_CATEGORIES[slot] for slot in slots if slot in ARMOR_AH_CATEGORIES), "")


def lsb_keys(*sql_sources: str) -> dict[int, str]:
    keys = {}
    for sql in sql_sources:
        for match in re.finditer(r"^INSERT INTO `item_[a-z]+` VALUES \((\d+),'([^']+)'", sql, re.M):
            keys[int(match.group(1))] = match.group(2)
    return keys


def build(items_lua: str, descriptions_lua: str, keys: dict[int, str]) -> dict:
    descriptions = {
        int(match.group(1)): lua_string(match.group(2), "en")
        for match in re.finditer(r"^\s*\[(\d+)\] = \{(.*)\},$", descriptions_lua, re.M)
    }
    rows = []
    for match in re.finditer(r"^\s*\[(\d+)\] = \{(.*)\},$", items_lua, re.M):
        item_id, record = int(match.group(1)), match.group(2)
        if not classic_era_item(item_id):
            continue
        category = lua_string(record, "category")
        level = lua_int(record, "level")
        if category not in {"Armor", "Weapon"} or not 1 <= level <= 75:
            continue
        jobs = bit_values(lua_int(record, "jobs"), JOBS)
        races = bit_values(lua_int(record, "races"), RACES)
        slots = bit_values(lua_int(record, "slots"), SLOTS)
        if not jobs or not races or not slots:
            continue
        description = descriptions.get(item_id, "")
        flags = lua_int(record, "flags")
        for glyph, label in ELEMENT_GLYPHS.items():
            description = description.replace(glyph, label)
        rows.append({
            "item_id": item_id,
            "item_key": keys.get(item_id, ""),
            "name": lua_string(record, "en"),
            "level": level,
            "jobs": jobs,
            "races": races,
            "slots": slots,
            "ah_category": auction_house_category(category, slots, lua_int(record, "skill")),
            "description": description,
            "rare": bool(flags & 32768),
            "ex": bool(flags & 16384),
            "stats": parse_gear_stats(description),
        })
    rows.sort(key=lambda item: (item["level"], item["name"].casefold(), item["item_id"]))
    stats = sorted({stat for item in rows for stat in item["stats"]})
    return {
        "era": "Original through Treasures of Aht Urhgan; level cap 75",
        "items_source": ITEMS_SOURCE,
        "descriptions_source": DESCRIPTIONS_SOURCE,
        "stats": stats,
        "rows": rows,
    }


def main() -> None:
    payload = build(
        fetch_text(ITEMS_SOURCE),
        fetch_text(DESCRIPTIONS_SOURCE),
        lsb_keys(fetch_text(f"{LSB_BASE}/item_equipment.sql"), fetch_text(f"{LSB_BASE}/item_weapon.sql")),
    )
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(payload['rows'])} level-75/ToAU equipment records to {OUTPUT}")


if __name__ == "__main__":
    main()
