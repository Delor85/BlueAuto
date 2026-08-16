PRAGMA foreign_keys = ON;

-- SOURCE-ONLY MIGRATION FOR B.I.R. v2.8.0.
-- DO NOT APPLY TO PRODUCTION WITHOUT A SEPARATE EXPLICIT AUTHORIZATION.

CREATE TABLE IF NOT EXISTS owner_entitlements (
    entitlement_id TEXT PRIMARY KEY NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('MOCK_OWNER', 'OWNER_ADMIN')),
    bound_device_id TEXT NOT NULL REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_seen_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_owner_entitlements_kind_device
    ON owner_entitlements(kind, bound_device_id);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entitlement_id TEXT REFERENCES owner_entitlements(entitlement_id) ON UPDATE CASCADE ON DELETE SET NULL,
    action TEXT NOT NULL,
    target_node_code TEXT,
    target_device_id TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    outcome TEXT NOT NULL DEFAULT 'ACCEPTED',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_target ON admin_audit_log(target_node_code, created_at DESC);

CREATE TABLE IF NOT EXISTS device_control_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_device_id TEXT NOT NULL REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE CASCADE,
    target_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('START_ROBOT','STOP_ROBOT','SET_REMOTE','SET_ROBOT','SYNC_NOW','CANCEL_PENDING')),
    payload_json TEXT NOT NULL DEFAULT '{}',
    state TEXT NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','ACKNOWLEDGED','FAILED','CANCELLED')),
    requested_by_entitlement_id TEXT NOT NULL REFERENCES owner_entitlements(entitlement_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    acknowledged_at TEXT,
    result_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_device_control_pending
    ON device_control_actions(target_device_id, state, id);

CREATE TABLE IF NOT EXISTS admin_assist_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    request_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    state TEXT NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','PRESENTED','CONFIRMED','REJECTED','EXPIRED','CANCELLED')),
    requires_user_confirmation INTEGER NOT NULL DEFAULT 1 CHECK (requires_user_confirmation IN (0,1)),
    requested_by_entitlement_id TEXT NOT NULL REFERENCES owner_entitlements(entitlement_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_admin_assist_target
    ON admin_assist_requests(target_node_code, state, created_at DESC);
