AGENT_MIGRATION = {
    "version": 2,
    "name": "create_multi_agent_tables",
    "sql": """
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    parent_id TEXT,
    model TEXT NOT NULL DEFAULT '',
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    summary TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    phase TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    files_json TEXT NOT NULL,
    status TEXT NOT NULL,
    report_json TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS build_contracts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    feature TEXT NOT NULL,
    contract_json TEXT NOT NULL,
    markdown TEXT NOT NULL,
    frozen INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_ownership (
    session_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    path TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    PRIMARY KEY (session_id, contract_id, path)
);

CREATE TABLE IF NOT EXISTS validation_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    contract_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    findings_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS validation_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    validation_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    owner INTEGER NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    file TEXT NOT NULL DEFAULT '',
    line INTEGER NOT NULL DEFAULT 0,
    expected TEXT NOT NULL DEFAULT '',
    actual TEXT NOT NULL DEFAULT '',
    command TEXT NOT NULL DEFAULT '',
    fix TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_strikes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    agent_id INTEGER NOT NULL,
    phase TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_session ON agent_runs(session_id, phase);
CREATE INDEX IF NOT EXISTS idx_agent_messages_session ON agent_messages(session_id, phase);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_session ON agent_tasks(session_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_build_contracts_session ON build_contracts(session_id, version);
CREATE INDEX IF NOT EXISTS idx_validation_runs_session ON validation_runs(session_id, round_number);
CREATE INDEX IF NOT EXISTS idx_validation_findings_session ON validation_findings(session_id, owner, status);
CREATE INDEX IF NOT EXISTS idx_agent_strikes_session ON agent_strikes(session_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_session ON agent_events(session_id, id);
""",
}
