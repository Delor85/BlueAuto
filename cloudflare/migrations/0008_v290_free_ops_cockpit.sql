-- B.I.R. v2.9 free operations cockpit: additive telemetry and escalations only.
ALTER TABLE devices ADD COLUMN offline_pending_events INTEGER NOT NULL DEFAULT 0;
ALTER TABLE devices ADD COLUMN accessibility_enabled INTEGER NOT NULL DEFAULT 0;
ALTER TABLE devices ADD COLUMN accessibility_connected INTEGER NOT NULL DEFAULT 0;
ALTER TABLE devices ADD COLUMN battery_percent INTEGER;
ALTER TABLE devices ADD COLUMN last_telemetry_at TEXT;

CREATE TABLE IF NOT EXISTS ops_escalations (
  public_id TEXT PRIMARY KEY,
  raised_by_node_code TEXT NOT NULL REFERENCES nodes(node_code),
  target_node_code TEXT NOT NULL REFERENCES nodes(node_code),
  assigned_to TEXT NOT NULL,
  severity TEXT NOT NULL CHECK(severity IN ('INFO','WARN','HOT','CRITICAL')),
  kind TEXT NOT NULL,
  message TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL DEFAULT 'OPEN' CHECK(state IN ('OPEN','RESOLVED')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ops_escalations_assigned ON ops_escalations(assigned_to,state,created_at);
CREATE INDEX IF NOT EXISTS idx_ops_escalations_target ON ops_escalations(target_node_code,state,created_at);
