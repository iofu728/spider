CREATE TABLE ip2proxy_tmp (
    `ip_from` INT(11) UNSIGNED NOT NULL,
    `ip_to` INT(11) UNSIGNED NOT NULL,
    `proxy_type` VARCHAR(3) NOT NULL,
    `country_code` CHAR(2) NOT NULL,
    `country_name` VARCHAR(64) NOT NULL,
    `region_name` VARCHAR(128) NOT NULL,
    `city_name` VARCHAR(128) NOT NULL,
    `isp` VARCHAR(255) NOT NULL,
    `domain` VARCHAR(128) NOT NULL,
    `usage_type` VARCHAR(11) NOT NULL,
    `asn` VARCHAR(6) NOT NULL,
    `as` VARCHAR(256) NOT NULL,
    `last_seen` INT(10) NOT NULL,
    `threat` VARCHAR(128),
    INDEX `idx_ip_to` (`ip_to`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='proxy';