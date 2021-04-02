-- using tbk;
CREATE TABLE if not exists `shops` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'auto-increment primary keys.',
  `shop_id` varchar(30) NOT NULL DEFAULT '' COMMENT 'shop id',
  `shop_name` varchar(500) NOT NULL DEFAULT '' COMMENT 'shop name',
  `user_id` varchar(30) NOT NULL DEFAULT '' COMMENT 'subordinate user id',
  `seller_nick` varchar(500) NOT NULL DEFAULT '' COMMENT 'seller nick',
  `item_count` varchar(10) NOT NULL DEFAULT '0' COMMENT 'item count',
  `fans_count` varchar(10) NOT NULL DEFAULT '0' COMMENT 'fans count',
  `credit_level` varchar(10) NOT NULL DEFAULT '0' COMMENT 'credit level',
  `good_rate_perc` varchar(10) NOT NULL DEFAULT '0' COMMENT 'good Rate Percentage',
  `item_desc_rate` varchar(10) NOT NULL DEFAULT '0' COMMENT 'item describe rate',
  `seller_serv_rate` varchar(10) NOT NULL DEFAULT '0' COMMENT 'seller service rate',
  `logistics_serv_rate` varchar(10) NOT NULL DEFAULT '0' COMMENT 'logistics service rate',
  `start_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'start time',
  `is_deleted` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'is deleted',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='table for shops info in tbk';
