"""Build the tracked-loot tooltip index from Windower's FFXI resources."""

import difflib
import json
import re
from urllib.request import Request, urlopen

from missions import AF1_SLOTS, LIMBUS_AF1, LIMBUS_LOOT, dynamis_catalog


RESOURCE_ROOT = "https://raw.githubusercontent.com/Windower/Resources/master/resources_data"


def download(name):
    request = Request(f"{RESOURCE_ROOT}/{name}", headers={"User-Agent": "HokutenLootTracker/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def lua_text(value):
    return value.replace(r"\n", "\n").replace(r'\"', '"').replace(r"\\", "\\")


def normalized(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def main():
    item_rows = {}
    for match in re.finditer(
        r'\[(\d+)\] = \{id=\d+,en="((?:\\.|[^"\\])*)".*?category="([^"]+)".*?level=(\d+).*?slots=(\d+)',
        download("items.lua"),
    ):
        item_id, name, category, level, slots = match.groups()
        item_rows[int(item_id)] = {"name": lua_text(name), "category": category,
                                   "level": int(level), "slots": int(slots)}
    descriptions = {
        int(item_id): lua_text(description)
        for item_id, description in re.findall(
            r'\[(\d+)\] = \{id=\d+,en="((?:\\.|[^"\\])*)"',
            download("item_descriptions.lua"),
        )
    }
    candidates = list(item_rows.items())

    def find(name):
        wanted = normalized(name)
        pool = candidates
        if name.endswith(" +1"):
            pool = [(item_id, row) for item_id, row in candidates if row["name"].endswith(" +1")]
        exact = next(((item_id, row) for item_id, row in pool
                      if normalized(row["name"]) == wanted), None)
        if exact:
            return exact
        item_id, row = max(pool, key=lambda pair: difflib.SequenceMatcher(
            None, wanted, normalized(pair[1]["name"])).ratio())
        return item_id, row

    output = {}
    seen = set()
    for piece in dynamis_catalog():
        if piece["key"] in seen:
            continue
        seen.add(piece["key"])
        if piece["kind"] == "Relic armor -1":
            upgrade_name = f"{piece['item'][:-3]} +1"
            item_id, row = find(upgrade_name)
            output[piece["key"]] = {"name": piece["item"], "job": piece["job"],
                                    "slot": piece["slot"], "level": row["level"],
                                    "stats": (f"UPGRADE PREVIEW — {upgrade_name}\n"
                                              f"{descriptions.get(item_id, 'Equipment description unavailable.')}"),
                                    "note": "The -1 item is an upgrade material; these are the resulting +1 armor stats."}
            continue
        item_id, row = find(piece["item"])
        output[piece["key"]] = {"name": piece["item"], "job": piece["job"],
                                "slot": piece["slot"], "level": row["level"],
                                "stats": descriptions.get(item_id, "Equipment description unavailable.")}
    limbus_jobs = {
        "Proto-Omega": "BLU · DRG · DRK · PLD · THF",
        "Proto-Ultima": "BLU · BLM · BRD · RDM · SMN · WHM",
    }
    for boss, pieces in LIMBUS_LOOT.items():
        for _component, item, slot in pieces:
            key = f"limbus:{boss.lower()}:{slot.lower()}"
            item_id, row = find(item)
            output[key] = {"name": item, "job": limbus_jobs[boss], "slot": slot,
                           "level": row["level"],
                           "stats": descriptions.get(item_id, "Equipment description unavailable.")}
    for job, group in LIMBUS_AF1.items():
        for zone in ("apollyon", "temenos"):
            item, floors = group[zone]
            output[f"limbus:af1:{job}:{zone}"] = {
                "name": item, "job": job, "slot": f"{zone.title()} upgrade material",
                "level": None, "stats": f"Known original Limbus sources: {floors}",
                "note": "Required with the matching job material from the other Limbus zone for every AF+1 piece.",
            }
        for slot, item in zip(AF1_SLOTS, group["pieces"]):
            item_id, row = find(item)
            output[f"limbus:af1:{job}:{slot.lower()}"] = {
                "name": item, "job": job, "slot": slot, "level": row["level"],
                "stats": descriptions.get(item_id, "Equipment description unavailable."),
            }
    with open("static/item_tooltips.json", "w", encoding="utf-8") as output_file:
        json.dump(output, output_file, ensure_ascii=False, indent=2, sort_keys=True)
        output_file.write("\n")
    print(f"Wrote {len(output)} tracked item tooltips.")


if __name__ == "__main__":
    main()
