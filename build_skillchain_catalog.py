"""Build the Horizon-era skillchain catalog used by the party calculator."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

WEAPON_SKILLS_SOURCE = "https://raw.githubusercontent.com/LandSandBoat/server/base/sql/weapon_skills.sql"
SKILL_CAPS_SOURCE = "https://raw.githubusercontent.com/LandSandBoat/server/base/sql/skill_caps.sql"
SKILL_RANKS_SOURCE = "https://raw.githubusercontent.com/LandSandBoat/server/base/sql/skill_ranks.sql"
PET_SKILLS_SOURCE = "https://raw.githubusercontent.com/LandSandBoat/server/base/sql/pet_skills.sql"
ABILITIES_SOURCE = "https://raw.githubusercontent.com/LandSandBoat/server/base/sql/abilities.sql"
BLUE_SPELLS_API = "https://api.github.com/repos/LandSandBoat/server/contents/scripts/actions/spells/blue?ref=base"
OUTPUT = Path("static/skillchain_catalog.json")
JOBS = ("WAR", "MNK", "WHM", "BLM", "RDM", "THF", "PLD", "DRK", "BST", "BRD", "RNG", "SAM", "NIN", "DRG", "SMN", "BLU", "COR", "PUP", "DNC", "SCH", "GEO", "RUN")
WEAPONS = {1: "Hand-to-Hand", 2: "Dagger", 3: "Sword", 4: "Great Sword", 5: "Axe", 6: "Great Axe", 7: "Scythe", 8: "Polearm", 9: "Katana", 10: "Great Katana", 11: "Club", 12: "Staff", 25: "Archery", 26: "Marksmanship"}
SKILL_NAMES = {1: "hand2hand", 2: "dagger", 3: "sword", 4: "great sword", 5: "axe", 6: "great axe", 7: "scythe", 8: "polearm", 9: "katana", 10: "great katana", 11: "club", 12: "staff", 25: "archery", 26: "marksmanship"}
SC_PROPERTIES = {1: "Transfixion", 2: "Compression", 3: "Liquefaction", 4: "Scission", 5: "Reverberation", 6: "Detonation", 7: "Induration", 8: "Impaction", 9: "Gravitation", 10: "Distortion", 11: "Fusion", 12: "Fragmentation", 13: "Light", 14: "Darkness"}
SC_VARIABLES = {f"@SC_{name.upper()}": name for value, name in SC_PROPERTIES.items()}
AVATAR_BLOOD_PACTS = ((512, 527, "Carbuncle"), (528, 539, "Fenrir"), (544, 555, "Ifrit"), (560, 571, "Titan"), (576, 587, "Leviathan"), (592, 603, "Garuda"), (608, 619, "Shiva"), (624, 635, "Ramuh"), (656, 667, "Diabolos"))
ERA_RANK_OVERRIDES = {("dagger", "THF"): 2, ("axe", "BST"): 2, ("katana", "NIN"): 2, ("sword", "BLU"): 2, ("hand2hand", "PUP"): 3, ("dagger", "DNC"): 3}

# LandSandBoat's current Blue Magic action-script directory has only a small
# subset of the era spells.  HorizonXI's level-75 list supplies the remaining
# physical spells and their Chain Affinity properties.
HORIZON_BLUE_SKILLCHAIN_PROPERTIES = {
    "Foot Kick": ("Detonation",),
    "Power Attack": ("Reverberation",),
    "Sprout Smack": ("Reverberation",),
    "Wild Oats": ("Transfixion",),
    "Queasyshroom": ("Compression",),
    "Battle Dance": ("Impaction",),
    "Feather Storm": ("Transfixion",),
    "Head Butt": ("Impaction",),
    "Helldive": ("Transfixion",),
    "Bludgeon": ("Liquefaction",),
    "Claw Cyclone": ("Scission",),
    "Screwdriver": ("Transfixion", "Scission"),
    "Vanity Dive": ("Scission",),
    "Grand Slam": ("Induration",),
    "Empty Thrash": ("Compression", "Scission"),
    "Smite of Rage": ("Detonation",),
    "Pinecone Bomb": ("Liquefaction",),
    "Jet Stream": ("Impaction",),
    "Uppercut": ("Liquefaction", "Impaction"),
    "Terror Touch": ("Compression", "Reverberation"),
    "Sickle Slash": ("Compression",),
    "Mandibular Bite": ("Induration",),
    "Death Scissors": ("Compression", "Reverberation"),
    "Dimensional Death": ("Transfixion", "Impaction"),
    "Body Slam": ("Impaction",),
    "Frenetic Rip": ("Induration",),
    "Frypan": ("Impaction",),
    "Hydro Shot": ("Reverberation",),
    "Spinal Cleave": ("Scission", "Detonation"),
    "Hysteric Barrage": ("Detonation",),
    "Tail Slap": ("Reverberation",),
    "Cannonball": ("Fusion",),
    "Disseverment": ("Distortion",),
    "Ram Charge": ("Fragmentation",),
    "Vertical Cleave": ("Gravitation",),
    # Verified in-game on HorizonXI: Seraph Blade closes into Quad. Continuum
    # as Reverberation.  Horizon's live behavior therefore differs from the
    # inherited retail/Chains data, which lists Distortion / Scission.
    "Quadratic Continuum": ("Reverberation", "Scission"),
}
# Vanity Dive is an Horizon-era physical spell in the skillchain reference but
# is absent from the imported spell-farming metadata.  Keep its level here so
# the party calculator still offers it.
HORIZON_BLUE_SPELL_LEVEL_OVERRIDES = {"Vanity Dive": 28}

# The upstream weapon-skill dataset omits a secondary property that is present
# on HorizonXI.  Keep this small override alongside the Horizon Blue Magic
# list so regenerated catalogs preserve Horizon-era behavior.
HORIZON_WEAPON_SKILL_PROPERTY_OVERRIDES = {
    "Seraph Blade": ("Scission", "Transfixion"),
}


def display_name(value: str) -> str:
    value = value.replace("blade_", "Blade: ").replace("tachi_", "Tachi: ")
    return " ".join(part.capitalize() if not part.isupper() else part for part in value.replace("_", " ").split())


def parse_skill_caps(sql: str) -> dict[str, dict[str, int]]:
    caps = {}
    for row in re.findall(r"^INSERT INTO `?skill_caps`? VALUES \(([^;]+)\);", sql, re.M):
        values = [int(value.strip()) for value in row.split(",")]
        if 1 <= values[0] <= 75:
            caps[str(values[0])] = {str(rank): cap for rank, cap in enumerate(values[1:]) if rank and cap}
    return caps


def parse_skill_ranks(sql: str) -> dict[str, dict[str, int]]:
    ranks = {}
    for _, skill_name, values in re.findall(r"^INSERT INTO `?skill_ranks`? VALUES \((\d+),'([^']+)',([^;]+)\);", sql, re.M):
        if skill_name in SKILL_NAMES.values():
            ranks[skill_name] = {job: rank for job, rank in zip(JOBS, (int(value.strip()) for value in values.split(","))) if rank}
    for (skill_name, job), rank in ERA_RANK_OVERRIDES.items():
        ranks.setdefault(skill_name, {})[job] = rank
    return ranks


def parse_weapon_skills(sql: str, skill_ranks: dict[str, dict[str, int]] | None = None) -> list[dict]:
    skill_ranks = skill_ranks or {}
    rows = re.findall(r"^INSERT INTO `weapon_skills` VALUES \((\d+),'([^']+)',0x([0-9A-F]+),([^;]+)\);", sql, re.M)
    catalog = []
    for ident, name, jobs_hex, values in rows:
        fields = [int(value.rstrip(")")) for value in values.split(",")]
        weapon_type, skill_level = fields[0], fields[1]
        properties = [SC_PROPERTIES.get(value) for value in fields[8:11] if value]
        name = display_name(name)
        properties = list(HORIZON_WEAPON_SKILL_PROPERTY_OVERRIDES.get(name, properties))
        if weapon_type not in WEAPONS or not properties or not 0 < skill_level <= 276:
            continue
        job_flags = bytes.fromhex(jobs_hex)
        jobs = [job for job, flag in zip(JOBS, job_flags) if flag]
        catalog.append({
            "id": f"ws:{ident}", "name": name, "kind": "Weapon Skill",
            "weapon": WEAPONS[weapon_type], "jobs": jobs, "skill_level": skill_level,
            "skill_ranks": {job: skill_ranks.get(SKILL_NAMES[weapon_type], {}).get(job, 1) for job in jobs},
            "level_requirement": 0, "properties": properties,
        })
    return catalog


def parse_blue_spell(script: str) -> dict | None:
    name = re.search(r"--\s*Spell:\s*([^\r\n]+)", script)
    level = re.search(r"--\s*Level:\s*(\d+)", script)
    prop = re.search(r"--\s*Skillchain Property:\s*([^\r\n]+)", script, re.I)
    if not name or not level or not prop or not re.search(r"--\s*Spell Type:\s*Physical", script, re.I):
        return None
    properties = [value.strip().title() for value in prop.group(1).split("/")]
    return {"id": f"blu:{name.group(1).strip().casefold()}", "name": name.group(1).strip(),
            "kind": "Blue Magic (Chain Affinity)", "weapon": "Blue Magic", "jobs": ["BLU"],
            "skill_level": int(level.group(1)), "level_requirement": int(level.group(1)), "properties": properties}


def parse_blood_pacts(pet_skills_sql: str, abilities_sql: str) -> list[dict]:
    levels = {}
    for ident, level in re.findall(r"^INSERT INTO `?abilities`? VALUES \((\d+),'[^']+',15,(\d+),", abilities_sql, re.M):
        levels[int(ident)] = int(level)
    actions = []
    for row in re.findall(r"^INSERT INTO `?pet_skills`? VALUES \(([^;]+)\);", pet_skills_sql, re.M):
        if "@SKILLFLAG_BLOODPACT_RAGE" not in row:
            continue
        fields = row.split(",")
        ident, name = int(fields[0]), fields[3].strip("'")
        level = levels.get(ident)
        properties = [SC_VARIABLES[value.strip()] for value in fields[-3:] if value.strip() in SC_VARIABLES]
        avatar = next((avatar for start, end, avatar in AVATAR_BLOOD_PACTS if start <= ident <= end), None)
        # HorizonXI specifically removes skillchain properties from its level-70 Blood Pacts.
        if avatar and level and level < 70 and properties:
            actions.append({"id": f"bp:{ident}", "name": display_name(name), "kind": "Summoner Blood Pact: Rage",
                            "weapon": "Blood Pact", "jobs": ["SMN"], "skill_level": level,
                            "level_requirement": level, "avatar": avatar, "properties": properties})
    return actions


def supplement_blue_magic(parsed_spells: list[dict], farm_rows: list[dict]) -> list[dict]:
    """Apply Horizon's complete era property list to parsed Blue Magic data."""
    farming_spells = {row["spell"]: row for row in farm_rows}
    parsed = {spell["name"]: spell for spell in parsed_spells}
    for name, properties in HORIZON_BLUE_SKILLCHAIN_PROPERTIES.items():
        farm_spell = farming_spells.get(name)
        level = farm_spell.get("spell_level") if farm_spell else HORIZON_BLUE_SPELL_LEVEL_OVERRIDES.get(name)
        if level and (not farm_spell or farm_spell.get("spell_type") == "Physical"):
            parsed[name] = {
                "id": f"blu:{name.casefold()}", "name": name,
                "kind": "Blue Magic (Chain Affinity)", "weapon": "Blue Magic",
                "jobs": ["BLU"], "skill_level": level,
                "level_requirement": level,
                "properties": list(properties),
            }
    return list(parsed.values())


def fetch_blue_magic() -> list[dict]:
    with Path("static/blue_spell_farming.json").open(encoding="utf-8") as handle:
        farm_rows = json.load(handle)["rows"]
    horizon_spells = {row["spell"].casefold() for row in farm_rows}
    with urlopen(BLUE_SPELLS_API, timeout=30) as response:
        files = [row for row in json.load(response) if row.get("name", "").endswith(".lua")]
    def load(row):
        with urlopen(row["download_url"], timeout=30) as response:
            return response.read().decode("utf-8")
    with ThreadPoolExecutor(max_workers=12) as executor:
        spells = [parse_blue_spell(script) for script in executor.map(load, files)]
    parsed = [spell for spell in spells if spell and spell["name"].casefold() in horizon_spells]
    return supplement_blue_magic(parsed, farm_rows)


def build(sql: str, blue_spells: list[dict], skill_caps: dict[str, dict[str, int]] | None = None, skill_ranks: dict[str, dict[str, int]] | None = None, blood_pacts: list[dict] | None = None) -> dict:
    actions = parse_weapon_skills(sql, skill_ranks) + blue_spells + (blood_pacts or [])
    actions.sort(key=lambda action: (action["weapon"], action["skill_level"], action["name"]))
    return {"era": "HorizonXI level-75 era", "source": WEAPON_SKILLS_SOURCE,
            "blue_magic_source": BLUE_SPELLS_API, "jobs": JOBS, "skill_caps": skill_caps or {}, "actions": actions}


def main() -> None:
    with ThreadPoolExecutor(max_workers=5) as executor:
        def fetch(source):
            with urlopen(source, timeout=30) as response:
                return response.read().decode("utf-8")
        weapon_sql, caps_sql, ranks_sql, pet_skills_sql, abilities_sql = executor.map(fetch, (WEAPON_SKILLS_SOURCE, SKILL_CAPS_SOURCE, SKILL_RANKS_SOURCE, PET_SKILLS_SOURCE, ABILITIES_SOURCE))
    payload = build(weapon_sql, fetch_blue_magic(), parse_skill_caps(caps_sql), parse_skill_ranks(ranks_sql), parse_blood_pacts(pet_skills_sql, abilities_sql))
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(payload['actions'])} skillchain actions to {OUTPUT}")


if __name__ == "__main__":
    main()
