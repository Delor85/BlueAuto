PRAGMA defer_foreign_keys = on;

-- B.I.R. v2.9.5 — keep historical relational keys stable while exposing the official
-- Camtel business identity XXY -> DSMZ_XXY -> POSA_DSMZ_XXY.
ALTER TABLE nodes ADD COLUMN official_node_code TEXT NOT NULL DEFAULT '';
ALTER TABLE nodes ADD COLUMN identity_state TEXT NOT NULL DEFAULT 'DERIVED'
    CHECK (identity_state IN ('VERIFIED','DERIVED','REVIEW_REQUIRED'));

CREATE UNIQUE INDEX IF NOT EXISTS idx_nodes_official_identity
    ON nodes(official_node_code) WHERE length(official_node_code) > 0;

CREATE TABLE IF NOT EXISTS node_identity_aliases (
    alias_code TEXT NOT NULL,
    scope_parent_node_code TEXT NOT NULL DEFAULT '',
    node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    alias_kind TEXT NOT NULL DEFAULT 'LEGACY'
        CHECK (alias_kind IN ('LEGACY','LOCAL','OFFICIAL')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY(alias_code, scope_parent_node_code)
);
CREATE INDEX IF NOT EXISTS idx_node_identity_alias_target
    ON node_identity_aliases(node_code, alias_kind);

INSERT OR IGNORE INTO node_identity_aliases(alias_code,scope_parent_node_code,node_code,alias_kind)
SELECT node_code,'',node_code,'LEGACY' FROM nodes;

-- Field correction explicitly confirmed on 20 August 2026. The relational primary key is
-- intentionally not renamed: old commands and device tokens remain valid without a risky
-- multi-table rewrite. Every public surface uses the official identity below.
UPDATE nodes
SET official_node_code='POS1_DSM1_SU1', identity_state='VERIFIED'
WHERE node_code='POS1_DSM1' AND phone_number='621081275' AND role='POS';
INSERT OR IGNORE INTO node_identity_aliases(alias_code,scope_parent_node_code,node_code,alias_kind)
SELECT 'POS1_DSM1_SU1','',node_code,'OFFICIAL' FROM nodes
WHERE node_code='POS1_DSM1' AND phone_number='621081275' AND role='POS';
INSERT OR IGNORE INTO node_identity_aliases(alias_code,scope_parent_node_code,node_code,alias_kind)
SELECT 'POS1',COALESCE(parent_node_code,''),node_code,'LOCAL' FROM nodes
WHERE node_code='POS1_DSM1' AND phone_number='621081275' AND role='POS';

-- A distribution has two legitimate operator messages: the sender/executor message and the
-- recipient/child message. They must never overwrite or impersonate each other.
ALTER TABLE commands ADD COLUMN recipient_result_message TEXT NOT NULL DEFAULT '';
ALTER TABLE commands ADD COLUMN recipient_result_at TEXT;
ALTER TABLE commands ADD COLUMN recipient_balance_after INTEGER
    CHECK (recipient_balance_after IS NULL OR recipient_balance_after >= 0);

-- Only Remote and Robot remain public/effective modes. Historical Hybrid rows become Robot
-- without deleting their devices, tokens, SIM proof, queue or telemetry.
UPDATE devices SET mode='ROBOT' WHERE mode='HYBRID';

PRAGMA defer_foreign_keys = off;
