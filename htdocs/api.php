<?php
declare(strict_types=1);

const API_VERSION = '2.0.0';

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store, max-age=0');
header('Referrer-Policy: no-referrer');

$configFile = __DIR__ . '/config.php';
if (!is_file($configFile)) {
    fail('SERVER_NOT_CONFIGURED', 'Le fichier config.php est absent.', 503);
}
$config = require $configFile;

$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$allowedOrigin = (string)($config['app']['allowed_origin'] ?? '');
if ($origin !== '' && $allowedOrigin !== '' && hash_equals($allowedOrigin, $origin)) {
    header('Access-Control-Allow-Origin: ' . $allowedOrigin);
    header('Vary: Origin');
    header('Access-Control-Allow-Headers: Content-Type, X-Device-Token, X-BlueMagic-Client');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
}
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

try {
    $db = database($config);
    $action = trim((string)($_GET['action'] ?? 'health'));
    $input = readJsonBody();

    if ($action === 'health') {
        $db->query('SELECT 1');
        ok(['service' => 'blue-magic-api', 'version' => API_VERSION, 'database' => 'online']);
    }
    if ($action === 'pair_device') {
        pairDevice($db, $config, $input);
    }

    $auth = authenticate($db);
    switch ($action) {
        case 'heartbeat':
            heartbeat($db, $auth, $input);
            break;
        case 'create_command':
            createCommand($db, $auth, $input);
            break;
        case 'lease_command':
            leaseCommand($db, $auth);
            break;
        case 'command_event':
            commandEvent($db, $auth, $input);
            break;
        case 'command_status':
            commandStatus($db, $auth, $input);
            break;
        default:
            fail('UNKNOWN_ACTION', 'Action API inconnue.', 404);
    }
} catch (ApiError $error) {
    fail($error->apiCode, $error->getMessage(), $error->httpStatus);
} catch (Throwable $error) {
    error_log('BlueMagic API: ' . $error->getMessage());
    fail('INTERNAL_ERROR', 'Erreur interne. Consultez le journal du serveur.', 500);
}

function database(array $config): PDO
{
    $db = $config['database'] ?? [];
    $host = (string)($db['host'] ?? '');
    $port = (int)($db['port'] ?? 3306);
    $name = (string)($db['name'] ?? '');
    $user = (string)($db['user'] ?? '');
    $password = (string)($db['password'] ?? '');
    if ($host === '' || $name === '' || $user === '') {
        throw new ApiError('DATABASE_NOT_CONFIGURED', 'Paramètres MySQL incomplets.', 503);
    }
    return new PDO(
        "mysql:host={$host};port={$port};dbname={$name};charset=utf8mb4",
        $user,
        $password,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
            PDO::ATTR_PERSISTENT => false,
        ]
    );
}

function pairDevice(PDO $db, array $config, array $input): never
{
    $provided = (string)($input['pairing_secret'] ?? '');
    $expected = (string)($config['app']['pairing_secret'] ?? '');
    if (strlen($expected) < 24 || !hash_equals($expected, $provided)) {
        throw new ApiError('PAIRING_DENIED', 'Secret d’appairage incorrect.', 403);
    }

    $node = nodeCode($input['node_code'] ?? '');
    $parent = trim(strtoupper((string)($input['parent_node_code'] ?? '')));
    $role = strtoupper(trim((string)($input['role'] ?? '')));
    $mode = strtoupper(trim((string)($input['mode'] ?? '')));
    $phone = phone($input['phone_number'] ?? '');
    $deviceName = mb_substr(trim((string)($input['device_name'] ?? 'Android')), 0, 160);
    if (!in_array($role, ['DAE', 'DSM', 'POS'], true)) throw new ApiError('INVALID_ROLE', 'Rôle invalide.', 422);
    if (!in_array($mode, ['REMOTE', 'ROBOT', 'HYBRID'], true)) throw new ApiError('INVALID_MODE', 'Mode invalide.', 422);
    if ($role === 'DAE') $parent = '';
    if ($role !== 'DAE' && $parent === '') throw new ApiError('PARENT_REQUIRED', 'Le supérieur est obligatoire.', 422);

    $db->beginTransaction();
    try {
        if ($parent !== '') {
            $parentStmt = $db->prepare('SELECT node_code FROM nodes WHERE node_code = ? AND active = 1');
            $parentStmt->execute([$parent]);
            if (!$parentStmt->fetch()) throw new ApiError('PARENT_NOT_FOUND', 'Nœud supérieur introuvable.', 422);
        }
        $stmt = $db->prepare('SELECT * FROM nodes WHERE node_code = ? FOR UPDATE');
        $stmt->execute([$node]);
        $existing = $stmt->fetch();
        if ($existing) {
            $same = $existing['role'] === $role
                && $existing['phone_number'] === $phone
                && (string)($existing['parent_node_code'] ?? '') === $parent;
            if (!$same) throw new ApiError('NODE_IDENTITY_CONFLICT', 'Ce nœud existe avec une autre identité.', 409);
        } else {
            $insertNode = $db->prepare(
                'INSERT INTO nodes(node_code, role, phone_number, parent_node_code) VALUES(?, ?, ?, ?)'
            );
            $insertNode->execute([$node, $role, $phone, $parent === '' ? null : $parent]);
        }

        $deviceId = uuid4();
        $token = bin2hex(random_bytes(32));
        $insertDevice = $db->prepare(
            'INSERT INTO devices(device_id, node_code, mode, device_name, token_hash, last_seen_at) '
            . 'VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)'
        );
        $insertDevice->execute([$deviceId, $node, $mode, $deviceName, hash('sha256', $token)]);
        $db->commit();
        ok([
            'device_id' => $deviceId,
            'device_token' => $token,
            'node_code' => $node,
            'role' => $role,
            'mode' => $mode,
        ], 201);
    } catch (Throwable $error) {
        if ($db->inTransaction()) $db->rollBack();
        throw $error;
    }
}

function authenticate(PDO $db): array
{
    $token = trim((string)($_SERVER['HTTP_X_DEVICE_TOKEN'] ?? ''));
    if ($token === '') throw new ApiError('AUTH_REQUIRED', 'Jeton appareil requis.', 401);
    $stmt = $db->prepare(
        'SELECT d.device_id, d.node_code, d.mode, d.active AS device_active, '
        . 'n.role, n.phone_number, n.parent_node_code, n.active AS node_active '
        . 'FROM devices d JOIN nodes n ON n.node_code = d.node_code WHERE d.token_hash = ? LIMIT 1'
    );
    $stmt->execute([hash('sha256', $token)]);
    $auth = $stmt->fetch();
    if (!$auth || !(int)$auth['device_active'] || !(int)$auth['node_active']) {
        throw new ApiError('AUTH_INVALID', 'Appareil inconnu ou désactivé.', 401);
    }
    return $auth;
}

function heartbeat(PDO $db, array $auth, array $input): never
{
    $stmt = $db->prepare(
        'UPDATE devices SET last_seen_at = CURRENT_TIMESTAMP, robot_enabled = ?, '
        . 'app_version = ?, android_version = ? WHERE device_id = ?'
    );
    $stmt->execute([
        !empty($input['robot_enabled']) ? 1 : 0,
        mb_substr((string)($input['app_version'] ?? ''), 0, 40),
        mb_substr((string)($input['android_version'] ?? ''), 0, 40),
        $auth['device_id'],
    ]);
    ok(['server_time' => gmdate('c'), 'node_code' => $auth['node_code']]);
}

function createCommand(PDO $db, array $auth, array $input): never
{
    $requestType = strtoupper(trim((string)($input['request_type'] ?? '')));
    $clientId = trim((string)($input['client_request_id'] ?? ''));
    if (!preg_match('/^[A-Za-z0-9_-]{16,80}$/', $clientId)) {
        throw new ApiError('INVALID_REQUEST_ID', 'Clé anti-doublon invalide.', 422);
    }

    $existingStmt = $db->prepare(
        'SELECT public_id, state, created_at FROM commands WHERE requester_node_code = ? AND client_request_id = ?'
    );
    $existingStmt->execute([$auth['node_code'], $clientId]);
    $existing = $existingStmt->fetch();
    if ($existing) ok(['command' => $existing, 'duplicate' => true]);

    $requester = $auth['node_code'];
    $executor = '';
    $targetNode = null;
    $targetPhone = null;
    $amount = null;
    $operation = '';
    $ussd = '';
    $requiresPin = 1;

    if ($requestType === 'REQUEST_SUPPLY') {
        if (!in_array($auth['role'], ['DSM', 'POS'], true) || empty($auth['parent_node_code'])) {
            throw new ApiError('REQUEST_NOT_ALLOWED', 'Ce compte ne peut pas demander une recharge supérieure.', 403);
        }
        $executor = (string)$auth['parent_node_code'];
        $targetNode = $requester;
        $targetPhone = (string)$auth['phone_number'];
        $amount = amount($input['amount'] ?? '');
        $operation = 'DISTRIBUTION_TRANSFER';
        $ussd = "*550*2*{$targetPhone}*{$amount}#";
    } elseif ($requestType === 'SUPPLY_CHILD') {
        if (!in_array($auth['role'], ['DAE', 'DSM'], true)) {
            throw new ApiError('REQUEST_NOT_ALLOWED', 'Seul un DAE ou DSM peut approvisionner un enfant.', 403);
        }
        $targetNode = nodeCode($input['target_node_code'] ?? '');
        $childStmt = $db->prepare(
            'SELECT node_code, phone_number FROM nodes WHERE node_code = ? AND parent_node_code = ? AND active = 1'
        );
        $childStmt->execute([$targetNode, $requester]);
        $child = $childStmt->fetch();
        if (!$child) throw new ApiError('CHILD_NOT_FOUND', 'Ce compte n’est pas un enfant direct actif.', 422);
        $executor = $requester;
        $targetPhone = $child['phone_number'];
        $amount = amount($input['amount'] ?? '');
        $operation = 'DISTRIBUTION_TRANSFER';
        $ussd = "*550*2*{$targetPhone}*{$amount}#";
    } elseif ($requestType === 'RETAIL_SALE') {
        if ($auth['role'] !== 'POS') throw new ApiError('REQUEST_NOT_ALLOWED', 'Vente détail réservée aux PoS.', 403);
        $executor = $requester;
        $targetPhone = phone($input['target_phone'] ?? '');
        $amount = amount($input['amount'] ?? '');
        $operation = 'RETAIL_TRANSFER';
        $ussd = "*550*1*{$targetPhone}*{$amount}#";
    } elseif ($requestType === 'TEST_NUMBER') {
        $executor = $requester;
        $operation = 'TEST_NUMBER';
        $ussd = '*825*3*3#';
        $requiresPin = 0;
    } else {
        throw new ApiError('INVALID_REQUEST_TYPE', 'Type de commande inconnu.', 422);
    }

    $publicId = uuid4();
    $stmt = $db->prepare(
        'INSERT INTO commands(public_id, client_request_id, requester_node_code, executor_node_code, '
        . 'target_node_code, operation, target_phone, amount, ussd_code, requires_pin) '
        . 'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    );
    $stmt->execute([
        $publicId, $clientId, $requester, $executor, $targetNode, $operation,
        $targetPhone, $amount, $ussd, $requiresPin,
    ]);
    $commandId = (int)$db->lastInsertId();
    insertEvent($db, $commandId, $auth['device_id'], 'PENDING', 'Commande créée et contrôlée par le serveur.');
    ok([
        'command' => ['public_id' => $publicId, 'state' => 'PENDING', 'executor_node_code' => $executor],
        'duplicate' => false,
    ], 201);
}

function leaseCommand(PDO $db, array $auth): never
{
    if (!in_array($auth['mode'], ['ROBOT', 'HYBRID'], true)) {
        throw new ApiError('NOT_A_ROBOT', 'Cet appareil n’est pas autorisé à louer des commandes.', 403);
    }

    $db->beginTransaction();
    try {
        $expire = $db->prepare(
            "UPDATE commands SET state = IF(attempt < max_attempts, 'PENDING', 'FAILED'), "
            . "result_message = IF(attempt < max_attempts, 'Lease expiré avant composition.', 'Robot indisponible après plusieurs leases.'), "
            . "lease_token_hash = NULL, leased_until = NULL "
            . "WHERE executor_node_code = ? AND state = 'LEASED' AND leased_until < CURRENT_TIMESTAMP"
        );
        $expire->execute([$auth['node_code']]);

        $stmt = $db->prepare(
            "SELECT * FROM commands WHERE executor_node_code = ? AND state = 'PENDING' "
            . 'ORDER BY id ASC LIMIT 1 FOR UPDATE'
        );
        $stmt->execute([$auth['node_code']]);
        $command = $stmt->fetch();
        if (!$command) {
            $db->commit();
            ok(['available' => false]);
        }

        $leaseToken = bin2hex(random_bytes(24));
        $update = $db->prepare(
            "UPDATE commands SET state = 'LEASED', attempt = attempt + 1, lease_token_hash = ?, "
            . 'leased_until = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 120 SECOND) WHERE id = ?'
        );
        $update->execute([hash('sha256', $leaseToken), $command['id']]);
        insertEvent($db, (int)$command['id'], $auth['device_id'], 'LEASED', 'Commande réservée au Robot.');
        $db->commit();

        ok([
            'available' => true,
            'command' => [
                'public_id' => $command['public_id'],
                'lease_token' => $leaseToken,
                'operation' => $command['operation'],
                'target_phone' => $command['target_phone'],
                'amount' => $command['amount'],
                'ussd_code' => $command['ussd_code'],
                'requires_pin' => (bool)$command['requires_pin'],
            ],
        ]);
    } catch (Throwable $error) {
        if ($db->inTransaction()) $db->rollBack();
        throw $error;
    }
}

function commandEvent(PDO $db, array $auth, array $input): never
{
    if (!in_array($auth['mode'], ['ROBOT', 'HYBRID'], true)) {
        throw new ApiError('NOT_A_ROBOT', 'Événement réservé au Robot exécuteur.', 403);
    }
    $publicId = trim((string)($input['command_id'] ?? ''));
    $leaseToken = trim((string)($input['lease_token'] ?? ''));
    $nextState = strtoupper(trim((string)($input['state'] ?? '')));
    $allowed = ['DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT', 'SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'];
    if (!in_array($nextState, $allowed, true)) throw new ApiError('INVALID_STATE', 'État de commande invalide.', 422);

    $db->beginTransaction();
    try {
        $stmt = $db->prepare('SELECT * FROM commands WHERE public_id = ? FOR UPDATE');
        $stmt->execute([$publicId]);
        $command = $stmt->fetch();
        if (!$command || $command['executor_node_code'] !== $auth['node_code']) {
            throw new ApiError('COMMAND_NOT_FOUND', 'Commande introuvable pour ce Robot.', 404);
        }
        if (!hash_equals((string)$command['lease_token_hash'], hash('sha256', $leaseToken))) {
            throw new ApiError('LEASE_INVALID', 'Lease invalide ou expiré.', 409);
        }
        if (in_array($command['state'], ['SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'], true)) {
            $db->commit();
            ok(['command' => commandView($command), 'already_terminal' => true]);
        }

        $validTransitions = [
            'LEASED' => ['DIALING', 'FAILED'],
            'DIALING' => ['AWAITING_PIN', 'AWAITING_RESULT', 'SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'],
            'AWAITING_PIN' => ['PIN_SUBMITTED', 'FAILED', 'UNKNOWN', 'BLOCKED'],
            'PIN_SUBMITTED' => ['AWAITING_RESULT', 'SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'],
            'AWAITING_RESULT' => ['SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'],
        ];
        if (!in_array($nextState, $validTransitions[$command['state']] ?? [], true)) {
            throw new ApiError('INVALID_TRANSITION', "Transition {$command['state']} vers {$nextState} refusée.", 409);
        }

        $message = mb_substr(trim((string)($input['message'] ?? '')), 0, 2000);
        $operatorId = trim((string)($input['operator_transaction_id'] ?? ''));
        if ($operatorId !== '' && !preg_match('/^[A-Za-z0-9_-]{6,64}$/', $operatorId)) $operatorId = '';
        $terminal = in_array($nextState, ['SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'], true);

        $update = $db->prepare(
            'UPDATE commands SET state = ?, result_message = ?, operator_transaction_id = NULLIF(?, \'\'), '
            . 'started_at = IF(? = \'DIALING\' AND started_at IS NULL, CURRENT_TIMESTAMP, started_at), '
            . 'completed_at = IF(? = 1, CURRENT_TIMESTAMP, completed_at), '
            . 'leased_until = IF(? = 1, NULL, leased_until) WHERE id = ?'
        );
        $update->execute([$nextState, $message, $operatorId, $nextState, $terminal ? 1 : 0, $terminal ? 1 : 0, $command['id']]);
        insertEvent($db, (int)$command['id'], $auth['device_id'], $nextState, $message);
        $db->commit();
        ok(['command' => ['public_id' => $publicId, 'state' => $nextState], 'already_terminal' => false]);
    } catch (Throwable $error) {
        if ($db->inTransaction()) $db->rollBack();
        throw $error;
    }
}

function commandStatus(PDO $db, array $auth, array $input): never
{
    $publicId = trim((string)($input['command_id'] ?? ''));
    $stmt = $db->prepare(
        'SELECT public_id, requester_node_code, executor_node_code, target_node_code, operation, target_phone, '
        . 'amount, state, result_message, operator_transaction_id, created_at, started_at, completed_at, updated_at '
        . 'FROM commands WHERE public_id = ? AND (requester_node_code = ? OR executor_node_code = ?)'
    );
    $stmt->execute([$publicId, $auth['node_code'], $auth['node_code']]);
    $command = $stmt->fetch();
    if (!$command) throw new ApiError('COMMAND_NOT_FOUND', 'Commande introuvable.', 404);
    ok(['command' => commandView($command)]);
}

function commandView(array $command): array
{
    $allowed = ['public_id', 'requester_node_code', 'executor_node_code', 'target_node_code', 'operation',
        'target_phone', 'amount', 'state', 'result_message', 'operator_transaction_id', 'created_at',
        'started_at', 'completed_at', 'updated_at'];
    return array_intersect_key($command, array_flip($allowed));
}

function insertEvent(PDO $db, int $commandId, ?string $deviceId, string $state, string $message): void
{
    $stmt = $db->prepare('INSERT INTO command_events(command_id, device_id, state, message) VALUES(?, ?, ?, ?)');
    $stmt->execute([$commandId, $deviceId, $state, mb_substr($message, 0, 2000)]);
}

function readJsonBody(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === false || trim($raw) === '') return [];
    $data = json_decode($raw, true);
    if (!is_array($data)) throw new ApiError('INVALID_JSON', 'Corps JSON invalide.', 400);
    return $data;
}

function nodeCode(mixed $value): string
{
    $node = strtoupper(trim((string)$value));
    if (!preg_match('/^[A-Z0-9\\/_-]{3,64}$/', $node)) throw new ApiError('INVALID_NODE', 'Code nœud invalide.', 422);
    return $node;
}

function phone(mixed $value): string
{
    $phone = preg_replace('/\\D+/', '', (string)$value);
    if (!preg_match('/^\\d{9}$/', $phone)) throw new ApiError('INVALID_PHONE', 'Le numéro doit contenir 9 chiffres.', 422);
    return $phone;
}

function amount(mixed $value): int
{
    $text = trim((string)$value);
    if (!preg_match('/^[1-9]\\d{0,8}$/', $text)) throw new ApiError('INVALID_AMOUNT', 'Montant entier invalide.', 422);
    $amount = (int)$text;
    if ($amount < 1 || $amount > 50000000) throw new ApiError('INVALID_AMOUNT', 'Montant hors limites.', 422);
    return $amount;
}

function uuid4(): string
{
    $bytes = random_bytes(16);
    $bytes[6] = chr((ord($bytes[6]) & 0x0f) | 0x40);
    $bytes[8] = chr((ord($bytes[8]) & 0x3f) | 0x80);
    $hex = bin2hex($bytes);
    return substr($hex, 0, 8) . '-' . substr($hex, 8, 4) . '-' . substr($hex, 12, 4)
        . '-' . substr($hex, 16, 4) . '-' . substr($hex, 20, 12);
}

function ok(array $data, int $status = 200): never
{
    http_response_code($status);
    echo json_encode(['ok' => true, 'data' => $data], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function fail(string $code, string $message, int $status): never
{
    http_response_code($status);
    echo json_encode(['ok' => false, 'error' => ['code' => $code, 'message' => $message]],
        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

final class ApiError extends RuntimeException
{
    public string $apiCode;
    public int $httpStatus;

    public function __construct(string $apiCode, string $message, int $httpStatus)
    {
        parent::__construct($message);
        $this->apiCode = $apiCode;
        $this->httpStatus = $httpStatus;
    }
}
