using tbk;
CREATE TABLE if not exists `items` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'auto-increment primary keys.',
  `item_id` varchar(30) NOT NULL DEFAULT '' COMMENT 'item id',
  `title` varchar(500) NOT NULL DEFAULT '' COMMENT 'item title',
  `shop_id` varchar(30) NOT NULL DEFAULT '' COMMENT 'subordinate shop id',
  `category_id` varchar(10) NOT NULL DEFAULT '' COMMENT 'category id',
  `sku_num` varchar(10) NOT NULL DEFAULT '0' COMMENT 'sku number',
  `quest_num` varchar(10) NOT NULL DEFAULT '0' COMMENT 'question number',
  `favcount` varchar(10) NOT NULL DEFAULT '0' COMMENT 'like count',
  `comment_count` varchar(10) NOT NULL DEFAULT '0' COMMENT 'comment count',
  `rate_keywords` varchar(1000) NOT NULL DEFAULT '' COMMENT 'rate keywords',
  `ask_text` varchar(500) NOT NULL DEFAULT '' COMMENT 'ask text',
  `props` varchar(2000) NOT NULL DEFAULT '' COMMENT 'props',
  `is_deleted` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'is deleted',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='table for items info in tbk';
