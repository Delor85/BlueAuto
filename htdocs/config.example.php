<?php
// Copier ce fichier sous le nom config.php puis remplacer toutes les valeurs CHANGE_ME.
// Ne jamais envoyer config.php sur GitHub.
return [
    'database' => [
        'host' => 'sqlXXX.infinityfree.com',
        'port' => 3306,
        'name' => 'if0_XXXXXXXX_blue_magic',
        'user' => 'if0_XXXXXXXX',
        'password' => 'CHANGE_ME_DATABASE_PASSWORD',
    ],
    'app' => [
        'pairing_secret' => 'CHANGE_ME_LONG_RANDOM_SECRET_AT_LEAST_24_CHARS',
        'allowed_origin' => 'https://magicservice-blue.gt.tc',
        'setup_enabled' => true,
    ],
];
