CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    discord_name TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL DEFAULT '',
    availability TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS member_jobs (
    member_id INTEGER NOT NULL,
    job TEXT NOT NULL,
    level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 75),
    PRIMARY KEY (member_id, job),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS progress (
    member_id INTEGER NOT NULL,
    campaign TEXT NOT NULL CHECK(campaign IN ('COP', 'ZILART')),
    chapter TEXT NOT NULL DEFAULT '',
    mission TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Not started'
        CHECK(status IN ('Not started', 'In progress', 'Ready for help', 'Complete')),
    details TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (member_id, campaign),
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

