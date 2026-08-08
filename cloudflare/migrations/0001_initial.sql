PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS nodes (
    node_code TEXT PRIMARY KEY NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('DAE', 'DSM', 'POS')),
    phone_number TEXT NOT NULL UNIQUE CHECK (length(phone_number) = 9),
    parent_node_code TEXT REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE RESTRICT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_node_code);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY NOT NULL,
    node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('REMOTE', 'ROBOT', 'HYBRID')),
    device_name TEXT NOT NULL DEFAULT '',
    token_hash TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    robot_enabled INTEGER NOT NULL DEFAULT 0 CHECK (robot_enabled IN (0, 1)),
    app_version TEXT NOT NULL DEFAULT '',
    android_version TEXT NOT NULL DEFAULT '',
    device_model TEXT NOT NULL DEFAULT '',
    last_seen_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_devices_node_mode ON devices(node_code, mode, active);

CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_id TEXT NOT NULL UNIQUE,
    client_request_id TEXT NOT NULL,
    requester_node_code TEXT NOT NULL REFERENCES nodes(node_code),
    executor_node_code TEXT NOT NULL REFERENCES nodes(node_code),
    target_node_code TEXT REFERENCES nodes(node_code),
    operation TEXT NOT NULL CHECK (operation IN ('DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER', 'TEST_NUMBER')),
    target_phone TEXT,
    amount INTEGER,
    ussd_code TEXT NOT NULL,
    requires_pin INTEGER NOT NULL DEFAULT 1 CHECK (requires_pin IN (0, 1)),
    state TEXT NOT NULL DEFAULT 'PENDING',
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 2,
    lease_token_hash TEXT,
    leased_until TEXT,
    result_message TEXT,
    operator_transaction_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(requester_node_code, client_request_id)
);

CREATE INDEX IF NOT EXISTS idx_commands_executor_queue
    ON commands(executor_node_code, state, id);

CREATE TABLE IF NOT EXISTS command_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id INTEGER NOT NULL REFERENCES commands(id) ON DELETE CASCADE,
    device_id TEXT REFERENCES devices(device_id) ON DELETE SET NULL,
    state TEXT NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_events_command ON command_events(command_id, id);
