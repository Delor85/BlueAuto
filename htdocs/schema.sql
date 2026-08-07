CREATE TABLE IF NOT EXISTS nodes (
    node_code VARCHAR(64) NOT NULL,
    role ENUM('DAE', 'DSM', 'POS') NOT NULL,
    phone_number CHAR(9) NOT NULL,
    parent_node_code VARCHAR(64) NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (node_code),
    UNIQUE KEY uq_nodes_phone (phone_number),
    KEY idx_nodes_parent (parent_node_code),
    CONSTRAINT fk_nodes_parent FOREIGN KEY (parent_node_code) REFERENCES nodes(node_code)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS devices (
    device_id CHAR(36) NOT NULL,
    node_code VARCHAR(64) NOT NULL,
    mode ENUM('REMOTE', 'ROBOT', 'HYBRID') NOT NULL,
    device_name VARCHAR(160) NOT NULL DEFAULT '',
    token_hash CHAR(64) NOT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    robot_enabled TINYINT(1) NOT NULL DEFAULT 0,
    app_version VARCHAR(40) NOT NULL DEFAULT '',
    android_version VARCHAR(40) NOT NULL DEFAULT '',
    last_seen_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (device_id),
    UNIQUE KEY uq_devices_token (token_hash),
    KEY idx_devices_node_mode (node_code, mode, active),
    CONSTRAINT fk_devices_node FOREIGN KEY (node_code) REFERENCES nodes(node_code)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS commands (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    public_id CHAR(36) NOT NULL,
    client_request_id VARCHAR(80) NOT NULL,
    requester_node_code VARCHAR(64) NOT NULL,
    executor_node_code VARCHAR(64) NOT NULL,
    target_node_code VARCHAR(64) NULL,
    operation ENUM('DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER', 'TEST_NUMBER') NOT NULL,
    target_phone CHAR(9) NULL,
    amount BIGINT UNSIGNED NULL,
    ussd_code VARCHAR(96) NOT NULL,
    requires_pin TINYINT(1) NOT NULL DEFAULT 1,
    state VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    attempt SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    max_attempts SMALLINT UNSIGNED NOT NULL DEFAULT 2,
    lease_token_hash CHAR(64) NULL,
    leased_until TIMESTAMP NULL DEFAULT NULL,
    result_message VARCHAR(2000) NULL,
    operator_transaction_id VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL DEFAULT NULL,
    completed_at TIMESTAMP NULL DEFAULT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_commands_public (public_id),
    UNIQUE KEY uq_commands_idempotency (requester_node_code, client_request_id),
    KEY idx_commands_executor_queue (executor_node_code, state, id),
    CONSTRAINT fk_commands_requester FOREIGN KEY (requester_node_code) REFERENCES nodes(node_code),
    CONSTRAINT fk_commands_executor FOREIGN KEY (executor_node_code) REFERENCES nodes(node_code),
    CONSTRAINT fk_commands_target FOREIGN KEY (target_node_code) REFERENCES nodes(node_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS command_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    command_id BIGINT UNSIGNED NOT NULL,
    device_id CHAR(36) NULL,
    state VARCHAR(32) NOT NULL,
    message VARCHAR(2000) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_events_command (command_id, id),
    CONSTRAINT fk_events_command FOREIGN KEY (command_id) REFERENCES commands(id) ON DELETE CASCADE,
    CONSTRAINT fk_events_device FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
