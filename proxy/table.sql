/*
* @Author: gunjianpan
* @Date:   2018-10-19 15:01:18
* @Last Modified by:   gunjianpan
* @Last Modified time: 2019-01-27 23:39:47
*/
use proxy;
CREATE TABLE if not exists `ip_proxy` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'auto-increment primary keys',
  `address` varchar(50) NOT NULL DEFAULT '0' COMMENT 'proxy address',
  `http_type` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'http type, 1: https, 0: http',
  `is_failured` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'failure time',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='table for ip proxy';
