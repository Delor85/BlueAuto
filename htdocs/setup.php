<?php
declare(strict_types=1);

$message = '';
$success = false;
$configFile = __DIR__ . '/config.php';
if (!is_file($configFile)) {
    $message = 'Créez d’abord config.php à partir de config.example.php.';
} else {
    $config = require $configFile;
    if (empty($config['app']['setup_enabled'])) {
        $message = 'Installation désactivée dans config.php.';
    } elseif (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
        $provided = (string)($_POST['pairing_secret'] ?? '');
        $expected = (string)($config['app']['pairing_secret'] ?? '');
        if (strlen($expected) < 24 || !hash_equals($expected, $provided)) {
            $message = 'Secret d’appairage incorrect.';
        } else {
            try {
                $db = $config['database'];
                $pdo = new PDO(
                    "mysql:host={$db['host']};port=" . ($db['port'] ?? 3306) . ";dbname={$db['name']};charset=utf8mb4",
                    $db['user'],
                    $db['password'],
                    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_EMULATE_PREPARES => false]
                );
                $sql = file_get_contents(__DIR__ . '/schema.sql');
                if ($sql === false) throw new RuntimeException('schema.sql introuvable.');
                $statements = preg_split('/;\\s*(?:\\r?\\n|$)/', $sql);
                foreach ($statements as $statement) {
                    if (trim($statement) !== '') $pdo->exec($statement);
                }
                $success = true;
                $message = 'Base initialisée. Passez maintenant setup_enabled à false dans config.php.';
            } catch (Throwable $error) {
                $message = 'Échec MySQL : ' . htmlspecialchars($error->getMessage(), ENT_QUOTES, 'UTF-8');
            }
        }
    }
}
?><!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Installation Blue Magic</title>
    <style>
        body{font:16px system-ui;background:#0b0c10;color:#fff;max-width:650px;margin:40px auto;padding:20px}
        main{background:#1f2833;padding:24px;border-radius:16px;border:1px solid #c5a059}
        input,button{width:100%;box-sizing:border-box;padding:14px;margin-top:12px;border-radius:8px}
        button{background:#c5a059;border:0;font-weight:800}.ok{color:#66fcf1}.bad{color:#ff8a80}
    </style>
</head>
<body><main>
    <h1>Blue Magic — installation MySQL</h1>
    <p class="<?= $success ? 'ok' : 'bad' ?>"><?= htmlspecialchars($message, ENT_QUOTES, 'UTF-8') ?></p>
    <?php if (!$success): ?>
    <form method="post">
        <label>Secret d’appairage défini dans config.php</label>
        <input type="password" name="pairing_secret" required autocomplete="off">
        <button type="submit">Initialiser les tables</button>
    </form>
    <?php endif; ?>
</main></body></html>
