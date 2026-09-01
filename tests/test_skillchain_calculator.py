import json
from pathlib import Path

from build_skillchain_catalog import build, parse_blood_pacts, parse_skill_caps, parse_weapon_skills, supplement_blue_magic
from missions import create_app


def test_catalog_reads_job_weapon_and_skillchain_properties():
    sql = "INSERT INTO `weapon_skills` VALUES (150,'tachi_yukikaze',0x00000000000000000000000200000000000000000000,10,200,0,0,0,3,1,0,7,6,0,0,0);"
    payload = build(sql, [{"id": "blu:foot kick", "name": "Foot Kick", "kind": "Blue Magic (Chain Affinity)", "weapon": "Blue Magic", "jobs": ["BLU"], "skill_level": 1, "properties": ["Detonation"]}])
    tachi = payload["actions"][1]
    assert tachi["weapon"] == "Great Katana"
    assert tachi["jobs"] == ["SAM"]
    assert tachi["properties"] == ["Induration", "Detonation"]
    assert payload["actions"][0]["weapon"] == "Blue Magic"


def test_skill_caps_are_exposed_for_level_filtering():
    caps = parse_skill_caps("INSERT INTO `skill_caps` VALUES (75,0,276,269,256,250,240,230,225,220,210,200,189,171,210);")
    payload = build("", [], caps)
    assert payload["skill_caps"]["75"]["1"] == 276
    assert payload["skill_caps"]["75"]["12"] == 171


def test_blood_pact_rage_actions_include_skillchain_properties():
    pet_skills = "INSERT INTO `pet_skills` VALUES (550,0,38,'flaming_crush',0,0,3,2000,1000,4,317,@SKILLFLAG_BLOODPACT_RAGE,0,13,0,@SC_FUSION,@SC_REVERBERATION,0);"
    abilities = "INSERT INTO `abilities` VALUES (550,'flaming_crush',15,70,4,60,173,0,0,94,2000,0,6,3,0,0,1,60,0,0,NULL);"
    actions = parse_blood_pacts(pet_skills, abilities)
    assert actions == []


def test_horizon_blood_pact_actions_include_required_avatar():
    pet_skills = "INSERT INTO `pet_skills` VALUES (544,0,32,'punch',0,0,3,2000,1000,4,317,@SKILLFLAG_BLOODPACT_RAGE,0,13,0,@SC_LIQUEFACTION,0,0);"
    abilities = "INSERT INTO `abilities` VALUES (544,'punch',15,1,4,60,173,0,0,94,2000,0,6,3,0,0,1,60,0,0,NULL);"
    assert parse_blood_pacts(pet_skills, abilities)[0]["avatar"] == "Ifrit"


def test_skillchain_calculator_requires_sign_in_and_renders(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "skillchains.db"), "SECRET_KEY": "test", "AUTH_DISABLED": False})
    client = app.test_client()
    assert client.get("/skillchain-calculator").status_code == 302
    with client.session_transaction() as session:
        session["is_editor"] = True
        session["member_id"] = 1
    page = client.get("/skillchain-calculator")
    assert page.status_code == 200
    assert b"Skillchain Calculator" in page.data
    assert b"Chain Affinity" in page.data
    assert b"Require weapon skill first" in page.data
    assert b'id="skillchain-type-filter"' in page.data
    script = Path("static/skillchain_calculator.js").read_text(encoding="utf-8")
    assert 'input type="number"' in script
    assert "requireWeaponSkillFirst.checked" in script
    assert "requiresBlueMagicOpener" in script
    assert "Chain Affinity assumed active" in script
    assert "typeFilter.value" in script
    assert "bluSlot" in script
    assert "localeCompare" in script
    catalog = json.loads(Path("static/skillchain_catalog.json").read_text(encoding="utf-8"))
    assert any(action["name"] == "Foot Kick" and action["weapon"] == "Blue Magic" for action in catalog["actions"])


def test_blue_magic_catalog_includes_horizon_chain_affinity_properties():
    spells = {spell["name"]: spell for spell in supplement_blue_magic([], [
        {"spell": "Screwdriver", "spell_level": 26, "spell_type": "Physical"},
        {"spell": "Ram Charge", "spell_level": 73, "spell_type": "Physical"},
        {"spell": "Quadratic Continuum", "spell_level": 54, "spell_type": "Physical"},
    ])}
    assert spells["Screwdriver"]["properties"] == ["Transfixion", "Scission"]
    assert spells["Ram Charge"]["properties"] == ["Fragmentation"]
    assert spells["Quadratic Continuum"]["properties"] == ["Scission", "Distortion"]


def test_horizon_seraph_blade_retains_its_transfixion_property():
    sql = "INSERT INTO `weapon_skills` VALUES (37,'seraph_blade',0x00000000000000000000000200000000000000000000,3,125,0,0,0,3,1,0,4,0,0,0,0);"
    seraph_blade = parse_weapon_skills(sql)[0]
    assert seraph_blade["properties"] == ["Scission", "Transfixion"]
