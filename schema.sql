CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    discord_name TEXT NOT NULL DEFAULT '',
    discord_user_id TEXT NOT NULL DEFAULT '',
    discord_admin INTEGER NOT NULL DEFAULT 0,
    timezone TEXT NOT NULL DEFAULT '',
    availability TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS member_jobs (
    member_id INTEGER,
    custom_name TEXT NOT NULL DEFAULT '',
    job TEXT NOT NULL,
    level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 75),
    PRIMARY KEY (member_id, job),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS progress (
    member_id INTEGER NOT NULL,
    campaign TEXT NOT NULL,
    chapter TEXT NOT NULL DEFAULT '',
    mission TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Not started'
        CHECK(status IN ('Not started', 'In progress', 'Ready for help', 'Complete')),
    details TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (member_id, campaign),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS help_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    zone TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    level_cap INTEGER CHECK(level_cap IS NULL OR level_cap BETWEEN 1 AND 75),
    helpers_needed INTEGER NOT NULL DEFAULT 1 CHECK(helpers_needed BETWEEN 1 AND 17),
    availability_mode TEXT NOT NULL CHECK(availability_mode IN ('now', 'after', 'fixed', 'range')),
    start_at TEXT,
    available_after TEXT,
    end_at TEXT,
    expires_at TEXT,
    requirements TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK(status IN ('Open', 'Forming', 'Full', 'Completed', 'Cancelled', 'Expired')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (requester_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS help_request_jobs (
    request_id INTEGER NOT NULL,
    job TEXT NOT NULL,
    PRIMARY KEY (request_id, job),
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS help_request_roles (
    request_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'job' CHECK(kind IN ('job', 'role')),
    quantity INTEGER CHECK(quantity IS NULL OR quantity BETWEEN 1 AND 5),
    PRIMARY KEY (request_id, role),
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS help_volunteers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    selected INTEGER NOT NULL DEFAULT 0 CHECK(selected IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (request_id, member_id),
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS help_volunteer_jobs (
    volunteer_id INTEGER NOT NULL,
    job TEXT NOT NULL,
    PRIMARY KEY (volunteer_id, job),
    FOREIGN KEY (volunteer_id) REFERENCES help_volunteers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_help_requests_status ON help_requests(status);
CREATE INDEX IF NOT EXISTS idx_help_requests_dates ON help_requests(start_at, end_at, expires_at);
CREATE INDEX IF NOT EXISTS idx_help_requests_requester ON help_requests(requester_id);
CREATE INDEX IF NOT EXISTS idx_help_volunteers_request ON help_volunteers(request_id, selected);

CREATE TABLE IF NOT EXISTS loot_ownership (
    member_id INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (member_id, item_key),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alliance_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_member_id INTEGER,
    name TEXT NOT NULL,
    event_at TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alliance_slots (
    event_id INTEGER NOT NULL,
    party_number INTEGER NOT NULL CHECK(party_number BETWEEN 1 AND 3),
    slot_number INTEGER NOT NULL CHECK(slot_number BETWEEN 1 AND 6),
    member_id INTEGER NOT NULL,
    job TEXT NOT NULL,
    PRIMARY KEY (event_id, party_number, slot_number),
    UNIQUE (event_id, member_id),
    FOREIGN KEY (event_id) REFERENCES alliance_events(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alliance_events_date ON alliance_events(event_at, updated_at);

CREATE TABLE IF NOT EXISTS blue_spell_ownership (
    member_id INTEGER NOT NULL,
    spell TEXT NOT NULL,
    learned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (member_id, spell),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS blue_spell_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_member_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    blue_level INTEGER NOT NULL CHECK(blue_level BETWEEN 1 AND 75),
    spells_json TEXT NOT NULL DEFAULT '[]',
    is_shared INTEGER NOT NULL DEFAULT 0 CHECK(is_shared IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_blue_spell_templates_owner
ON blue_spell_templates(owner_member_id, updated_at);

CREATE TABLE IF NOT EXISTS gear_ownership (
    member_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    name TEXT NOT NULL,
    slot TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    jobs TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 1,
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (member_id, item_id),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gear_ownership_member_slot
ON gear_ownership(member_id, slot);
