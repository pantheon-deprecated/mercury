#!/usr/bin/php -q
<?php
  if (file_exists('/etc/mercury/incep')) {
    // only run once
    exit(0);
  }
  else {
    ob_start(); // get it all set
    // Update pressflow
    echo `cd /var/www/pressflow; bzr merge --force`;
    
    // move mysql start state to /mnt
    // TODO: this should be EBS'ed
    echo `mkdir /mnt/tmp`;
    echo `chown mysql:mysql /mnt/tmp/`;
    echo `chmod 777 /mnt/tmp`;
    echo `rsync -a /var/lib/mysql /mnt`;
    echo `/etc/init.d/mysql restart`;
    // TODO: clean up vestigal /var/lib/mysql
    
    // set up varnish area in /mnt
    echo `rsync -a /var/lib/varnish /mnt`;
    echo `/etc/init.d/varnish restart`;
    // TODO: clean up vistigal /var/lib/varnish

    echo `apt-get update`;    
    echo `echo Y|apt-get upgrade`;
    
    
    // Set up postfix
    // get hostname
    $hostname = trim(str_replace('public-hostname: ', '', `/usr/local/bin/ec2-metadata -p`));
    echo `postconf -e 'myhostname = $hostname'`;
    echo `postconf -e 'mydomain = $hostname'`;
    echo `postconf -e 'mydestination = $hostname, localhost'`;
    
    // Phone home
    $ami = trim(str_replace('ami-id: ', '', `/usr/local/bin/ec2-metadata -a`));
    $instance = trim(str_replace('instance-id: ', '', `/usr/local/bin/ec2-metadata -i`));
    $url = 'http://getpantheon.com/pantheon.php?ami='. $ami .'&instance='. $instance;
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_HEADER, 0);
    curl_exec($ch);
    curl_close($ch);

    $output = ob_get_flush();
    $log = fopen('/etc/mercury/bootlog', 'w');
    fwrite($log, $output);
    fclose($log);

    // mark incep date
    $stamp = date('Y-m-d H:i');
    echo `echo $stamp >> /etc/mercury/incep`\n;
  }
?>
