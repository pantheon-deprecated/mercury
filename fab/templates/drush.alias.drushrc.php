<?php

// Get settings.php variables from vhost file.
$vhost = explode(PHP_EOL, file_get_contents('${vhost_path}'));
$vars = array();
foreach ($vhost as $line) {
    $line = trim($line);
    if (strpos($line, 'SetEnv') !== FALSE) {
        $var = explode(' ', $line);
        $_SERVER[$var[1]] = $var[2];
    }
}

$options['uri'] = 'default';
$options['root'] = '${root}';

