PRAGMA foreign_keys = ON;

-- B.I.R. v2.9.1 — additive, non-financial Remote -> Robot synchronization wake.
-- No command, USSD, PIN, secret or financial payload is stored here.
CREATE TABLE IF NOT EXISTS sync_wake_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    requested_by_device_id TEXT NOT NULL REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE CASCADE,
    consumed_by_device_id TEXT REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE SET NULL,
    reason TEXT NOT NULL DEFAULT 'REMOTE_SYNC_STALE',
    state TEXT NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','CONSUMED','EXPIRED')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    consumed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_wake_pending
    ON sync_wake_requests(node_code, state, id);
CREATE INDEX IF NOT EXISTS idx_sync_wake_requester
    ON sync_wake_requests(requested_by_device_id, created_at DESC);
