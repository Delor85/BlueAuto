ALTER TABLE commands ADD COLUMN command_kind TEXT NOT NULL DEFAULT ''
    CHECK (command_kind IN ('', 'BALANCE_OWN', 'TRANSACTION_DETAIL', 'HISTORY_LAST5',
        'FREEZE_SELF', 'INIT_CHILD_PIN_RESET', 'SUSPEND_CHILD', 'REACTIVATE_CHILD',
        'BALANCE_CHILD', 'FREEZE_CHILD', 'REACTIVATE_FROZEN_CHILD'));

ALTER TABLE commands ADD COLUMN capacity_check_id TEXT;

ALTER TABLE commands ADD COLUMN command_argument TEXT NOT NULL DEFAULT '';

CREATE UNIQUE INDEX IF NOT EXISTS idx_commands_capacity_check
    ON commands(capacity_check_id) WHERE capacity_check_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS account_balances (
    node_code TEXT PRIMARY KEY NOT NULL REFERENCES nodes(node_code)
        ON UPDATE CASCADE ON DELETE CASCADE,
    balance INTEGER NOT NULL CHECK (balance >= 0),
    source TEXT NOT NULL CHECK (source IN ('USSD', 'ESTIMATED_TRANSFER')),
    evidence_kind TEXT NOT NULL CHECK (evidence_kind IN (
        'BALANCE_QUERY', 'CHILD_BALANCE_QUERY', 'HISTORY_RESULT',
        'TRANSACTION_DETAIL_RESULT', 'FINANCIAL_RESULT', 'ESTIMATED_TRANSFER'
    )),
    confidence TEXT NOT NULL CHECK (confidence IN (
        'OPERATOR_EXPLICIT', 'DERIVED_FROM_EXPLICIT'
    )),
    source_command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    evidence_command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    observed_at TEXT NOT NULL,
    valid_until TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS purchase_preflights (
    public_id TEXT PRIMARY KEY NOT NULL,
    client_request_id TEXT NOT NULL,
    requester_node_code TEXT NOT NULL REFERENCES nodes(node_code),
    supplier_node_code TEXT NOT NULL REFERENCES nodes(node_code),
    requested_amount INTEGER NOT NULL CHECK (requested_amount > 0),
    available_balance INTEGER CHECK (available_balance >= 0),
    balance_command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    balance_reused INTEGER NOT NULL DEFAULT 0 CHECK (balance_reused IN (0, 1)),
    balance_observed_at TEXT,
    purchase_command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    state TEXT NOT NULL CHECK (state IN (
        'WAITING', 'AVAILABLE', 'INSUFFICIENT', 'FAILED', 'CONSUMED', 'EXPIRED'
    )),
    result_message TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(requester_node_code, client_request_id)
);

CREATE INDEX IF NOT EXISTS idx_purchase_preflights_balance_command
    ON purchase_preflights(balance_command_public_id, state);

CREATE INDEX IF NOT EXISTS idx_balances_observed ON account_balances(observed_at);
