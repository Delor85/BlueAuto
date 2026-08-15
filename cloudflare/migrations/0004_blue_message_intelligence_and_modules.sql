CREATE TABLE IF NOT EXISTS operator_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    message_kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '',
    transaction_id TEXT,
    receipt_number TEXT,
    source_phone TEXT NOT NULL DEFAULT '',
    source_node_code TEXT NOT NULL DEFAULT '',
    target_phone TEXT NOT NULL DEFAULT '',
    target_node_code TEXT NOT NULL DEFAULT '',
    amount INTEGER CHECK (amount IS NULL OR amount >= 0),
    current_balance INTEGER CHECK (current_balance IS NULL OR current_balance >= 0),
    account_no TEXT NOT NULL DEFAULT '',
    transaction_date TEXT NOT NULL DEFAULT '',
    transaction_time TEXT NOT NULL DEFAULT '',
    debit_credit TEXT NOT NULL DEFAULT '',
    charge_amount INTEGER,
    commission_amount INTEGER,
    tax_amount INTEGER,
    raw_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_operator_messages_tx_unique
    ON operator_messages(node_code, transaction_id, message_kind)
    WHERE transaction_id IS NOT NULL AND length(transaction_id) > 0;
CREATE INDEX IF NOT EXISTS idx_operator_messages_node_time
    ON operator_messages(node_code, created_at DESC);

CREATE TABLE IF NOT EXISTS node_activity_state (
    node_code TEXT PRIMARY KEY NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    last_activity_at TEXT,
    last_financial_activity_at TEXT,
    last_unbalanced_activity_at TEXT,
    last_operator_message_at TEXT,
    last_transaction_id TEXT,
    transaction_counter INTEGER NOT NULL DEFAULT 0 CHECK (transaction_counter >= 0),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS shadow_accounts (
    node_code TEXT PRIMARY KEY NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    created_by_node_code TEXT NOT NULL REFERENCES nodes(node_code),
    terminal_type TEXT NOT NULL DEFAULT 'TCHORONKO_SHADOW'
        CHECK (terminal_type IN ('TCHORONKO_SHADOW','ANDROID_PENDING','ANDROID_ACTIVE')),
    display_name TEXT NOT NULL DEFAULT '',
    zone TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    debtor_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    amount_advanced INTEGER NOT NULL CHECK (amount_advanced >= 0),
    amount_repaid INTEGER NOT NULL DEFAULT 0 CHECK (amount_repaid >= 0),
    due_date TEXT,
    note TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'OPEN' CHECK (state IN ('OPEN','PAID','CANCELLED')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_debts_owner_state ON debts(owner_node_code, state);

CREATE TABLE IF NOT EXISTS kyc_profiles (
    node_code TEXT PRIMARY KEY NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    legal_name TEXT NOT NULL DEFAULT '',
    id_document_number TEXT NOT NULL DEFAULT '',
    document_reference TEXT NOT NULL DEFAULT '',
    latitude REAL,
    longitude REAL,
    zone TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS mercenary_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_dae_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    dedicated_pos_node_code TEXT REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE SET NULL,
    virtual_balance INTEGER NOT NULL DEFAULT 0 CHECK (virtual_balance >= 0),
    commission_balance INTEGER NOT NULL DEFAULT 0 CHECK (commission_balance >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(owner_dae_node_code, phone_number)
);

CREATE TABLE IF NOT EXISTS mercenary_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mercenary_id INTEGER NOT NULL REFERENCES mercenary_accounts(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('DEPOSIT','SALE_DEBIT','COMMISSION','REFUND','COMMISSION_TO_BALANCE')),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS mercenary_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mercenary_id INTEGER NOT NULL REFERENCES mercenary_accounts(id) ON DELETE CASCADE,
    command_public_id TEXT UNIQUE REFERENCES commands(public_id) ON DELETE SET NULL,
    client_phone TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount > 0),
    debit_amount INTEGER NOT NULL CHECK (debit_amount >= 0),
    commission_amount INTEGER NOT NULL CHECK (commission_amount >= 0),
    state TEXT NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','SUCCEEDED','FAILED','VERIFY','REFUNDED')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
