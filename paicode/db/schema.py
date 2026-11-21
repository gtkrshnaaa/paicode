MIGRATIONS = [
    {
        "version": 1,
        "name": "create_core_tables",
        "sql": """
CREATE TABLE IF NOT EXISTS provider_presets (
    name TEXT PRIMARY KEY,
    base_url TEXT NOT NULL,
    default_model TEXT NOT NULL DEFAULT '',
    models_url TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS providers (
    name TEXT PRIMARY KEY,
    base_url TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    models_url TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS provider_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL REFERENCES providers(name) ON DELETE CASCADE,
    api_key TEXT NOT NULL,
    UNIQUE(provider, api_key)
);

CREATE TABLE IF NOT EXISTS provider_models (
    provider TEXT NOT NULL REFERENCES providers(name) ON DELETE CASCADE,
    model TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(provider, model)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    workspace TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_opened_at TEXT NOT NULL,
    title TEXT NOT NULL,
    stats_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS session_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    role TEXT NOT NULL,
    content_json TEXT,
    tool_calls_json TEXT,
    tool_call_id TEXT
);

CREATE TABLE IF NOT EXISTS session_transcript (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT,
    name TEXT,
    status TEXT,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS session_diffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    path TEXT NOT NULL,
    diff TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_provider_keys_provider ON provider_keys(provider);
CREATE INDEX IF NOT EXISTS idx_provider_models_provider ON provider_models(provider);
CREATE INDEX IF NOT EXISTS idx_sessions_last_opened ON sessions(last_opened_at);
CREATE INDEX IF NOT EXISTS idx_session_messages_session ON session_messages(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_session_transcript_session ON session_transcript(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_session_diffs_session ON session_diffs(session_id, seq);
""",
    },
]
