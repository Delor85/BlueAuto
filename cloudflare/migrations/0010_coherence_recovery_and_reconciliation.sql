PRAGMA foreign_keys = ON;

-- B.I.R. v2.9.3 — additive coherence recovery.
-- Never stores a PIN, USSD secret or lease token in plaintext.
ALTER TABLE commands ADD COLUMN leased_by_device_id TEXT REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE SET NULL;
ALTER TABLE commands ADD COLUMN last_recovery_at TEXT;
CREATE INDEX IF NOT EXISTS idx_commands_executor_recovery
    ON commands(executor_node_code, state, leased_by_device_id, id);

-- Separate what the account receives from the commercial policy it applies to its children.
-- Existing default_commission_bps remains the child-pricing policy and is never overwritten here.
ALTER TABLE nodes ADD COLUMN inbound_commission_bps INTEGER NOT NULL DEFAULT 0
    CHECK (inbound_commission_bps >= 0 AND inbound_commission_bps <= 5000);
UPDATE nodes SET inbound_commission_bps = CASE role
    WHEN 'DAE' THEN 1000
    WHEN 'DSM' THEN 900
    WHEN 'POS' THEN 800
    ELSE 0 END
WHERE inbound_commission_bps = 0;

-- Duplicate attempts are telemetry, not new financial commands.
CREATE TABLE IF NOT EXISTS duplicate_request_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    existing_command_public_id TEXT NOT NULL REFERENCES commands(public_id) ON DELETE CASCADE,
    client_request_id TEXT NOT NULL,
    existing_state TEXT NOT NULL,
    observed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_duplicate_request_node_time
    ON duplicate_request_audit(requester_node_code, observed_at, id);

-- Optional J+1/J+2 operator file reconciliation. B.I.R. remains fully operational without it.
CREATE TABLE IF NOT EXISTS reconciliation_batches (
    batch_id TEXT PRIMARY KEY NOT NULL,
    source_kind TEXT NOT NULL DEFAULT 'CAMTEL_FILE'
        CHECK (source_kind IN ('CAMTEL_FILE','BIR_IMPORT','MANUAL_AUDIT')),
    period_start TEXT,
    period_end TEXT,
    row_count INTEGER NOT NULL DEFAULT 0 CHECK (row_count >= 0),
    file_sha256 TEXT NOT NULL DEFAULT '',
    imported_by_node_code TEXT REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE SET NULL,
    imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS reconciliation_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL REFERENCES reconciliation_batches(batch_id) ON DELETE CASCADE,
    transaction_id TEXT NOT NULL DEFAULT '',
    receipt_number TEXT NOT NULL DEFAULT '',
    source_phone TEXT NOT NULL DEFAULT '',
    target_phone TEXT NOT NULL DEFAULT '',
    source_node_code TEXT NOT NULL DEFAULT '',
    target_node_code TEXT NOT NULL DEFAULT '',
    operation_kind TEXT NOT NULL DEFAULT '',
    amount INTEGER CHECK (amount IS NULL OR amount >= 0),
    transaction_at TEXT,
    final_status TEXT NOT NULL DEFAULT '',
    balance_after INTEGER CHECK (balance_after IS NULL OR balance_after >= 0),
    row_sha256 TEXT NOT NULL,
    matched_command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    match_state TEXT NOT NULL DEFAULT 'UNMATCHED'
        CHECK (match_state IN ('MATCHED','MISMATCH','BLUE_ONLY','BIR_ONLY','UNMATCHED','REVIEW')),
    match_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(batch_id, row_sha256)
);
CREATE INDEX IF NOT EXISTS idx_reconciliation_tx ON reconciliation_rows(transaction_id, receipt_number);
CREATE INDEX IF NOT EXISTS idx_reconciliation_nodes_time ON reconciliation_rows(source_node_code, target_node_code, transaction_at);
CREATE INDEX IF NOT EXISTS idx_reconciliation_match ON reconciliation_rows(match_state, id);
