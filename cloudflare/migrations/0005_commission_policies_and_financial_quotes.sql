ALTER TABLE nodes ADD COLUMN default_commission_bps INTEGER NOT NULL DEFAULT 0
    CHECK (default_commission_bps BETWEEN 0 AND 5000);

UPDATE nodes
SET default_commission_bps = CASE role
    WHEN 'DAE' THEN 1000
    WHEN 'DSM' THEN 800
    ELSE 0
END;

CREATE TABLE IF NOT EXISTS commission_overrides (
    parent_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    child_node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    rate_bps INTEGER NOT NULL CHECK (rate_bps BETWEEN 0 AND 5000),
    updated_by_node_code TEXT NOT NULL REFERENCES nodes(node_code),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY(parent_node_code, child_node_code)
);
CREATE INDEX IF NOT EXISTS idx_commission_overrides_parent
    ON commission_overrides(parent_node_code, child_node_code);

ALTER TABLE commands ADD COLUMN requested_base_amount INTEGER
    CHECK (requested_base_amount IS NULL OR requested_base_amount > 0);
ALTER TABLE commands ADD COLUMN commission_rate_bps INTEGER NOT NULL DEFAULT 0
    CHECK (commission_rate_bps BETWEEN 0 AND 5000);
ALTER TABLE commands ADD COLUMN commission_amount INTEGER NOT NULL DEFAULT 0
    CHECK (commission_amount >= 0);

ALTER TABLE purchase_preflights ADD COLUMN base_amount INTEGER
    CHECK (base_amount IS NULL OR base_amount > 0);
ALTER TABLE purchase_preflights ADD COLUMN commission_rate_bps INTEGER NOT NULL DEFAULT 0
    CHECK (commission_rate_bps BETWEEN 0 AND 5000);
ALTER TABLE purchase_preflights ADD COLUMN commission_amount INTEGER NOT NULL DEFAULT 0
    CHECK (commission_amount >= 0);

UPDATE purchase_preflights
SET base_amount = requested_amount
WHERE base_amount IS NULL;
