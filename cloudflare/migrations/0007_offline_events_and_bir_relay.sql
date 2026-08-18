PRAGMA foreign_keys = ON;

-- B.I.R. v2.9 additive schema. No existing financial table is dropped or rewritten.
CREATE TABLE IF NOT EXISTS relay_identities (
    device_id TEXT PRIMARY KEY NOT NULL REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE CASCADE,
    node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    public_key_b64 TEXT NOT NULL,
    fingerprint_sha256 TEXT NOT NULL UNIQUE CHECK (length(fingerprint_sha256) = 64),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_relay_identities_node ON relay_identities(node_code, active);

CREATE TABLE IF NOT EXISTS offline_events (
    event_id TEXT PRIMARY KEY NOT NULL,
    source_device_id TEXT NOT NULL REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    source_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE RESTRICT,
    command_public_id TEXT,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    source_created_at INTEGER NOT NULL DEFAULT 0,
    received_via TEXT NOT NULL CHECK (received_via IN ('DIRECT','BIR_RELAY')),
    relay_fingerprint_sha256 TEXT,
    relay_hops INTEGER NOT NULL DEFAULT 0 CHECK (relay_hops BETWEEN 0 AND 3),
    received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_offline_events_node_time ON offline_events(source_node_code, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_offline_events_command ON offline_events(command_public_id, received_at DESC);

-- Idempotence is enforced by offline_events.event_id. Replayed Relay envelopes become duplicates,
-- never a second financial execution.
