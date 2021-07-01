CREATE TABLE ip2location_tmp (
    `ip_from` INT(10) UNSIGNED ZEROFILL NOT NULL,
    `ip_to` INT(10) UNSIGNED ZEROFILL NOT NULL,
    `country_code` CHAR(2) NOT NULL,
    `country_name` VARCHAR(64) NOT NULL,
    `region_name` VARCHAR(128) NOT NULL,
    `city_name` VARCHAR(128) NOT NULL,
    `latitude` DOUBLE NULL DEFAULT NULL,
    `longitude` DOUBLE NULL DEFAULT NULL,
    `zip_code` VARCHAR(30) NULL DEFAULT NULL,
    `time_zone` VARCHAR(8) NULL DEFAULT NULL,
    INDEX `idx_ip_to` (`ip_to`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='location';