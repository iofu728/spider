CREATE TABLE ip2asn_tmp (
    `ip_from` INT(11) UNSIGNED NOT NULL,
    `ip_to` INT(11) UNSIGNED NOT NULL,
    `cidr` VARCHAR(20) NOT NULL,
    `asn` VARCHAR(6) NOT NULL,
    `as` VARCHAR(256) NOT NULL,
    INDEX `idx_ip_to` (`ip_to`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='asn';