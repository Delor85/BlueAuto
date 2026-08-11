ALTER TABLE devices ADD COLUMN sim_verified INTEGER NOT NULL DEFAULT 0
    CHECK (sim_verified IN (0, 1));

ALTER TABLE devices ADD COLUMN sim_fingerprint TEXT NOT NULL DEFAULT '';

ALTER TABLE devices ADD COLUMN sim_slot INTEGER;

CREATE INDEX IF NOT EXISTS idx_devices_robot_eligibility
    ON devices(node_code, mode, active, robot_enabled, sim_verified);
