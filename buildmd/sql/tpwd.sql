using tbk;
CREATE TABLE if not exists `article_tpwd` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'auto-increment primary keys',
  `article_id` varchar(50) NOT NULL DEFAULT '0' COMMENT 'article id',
  `tpwd_id` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'tpwd item id',
  `item_id` varchar(30) NOT NULL DEFAULT '0' COMMENT 'goods item id',
  `tpwd` varchar(30) NOT NULL DEFAULT '0' COMMENT 'tpwd content',
  `domain` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'tpwd type @0->s.click, @1->item, @5->uland, @10->taoquan',
  `content` varchar(300) NOT NULL DEFAULT '_' COMMENT 'tpwd content', 
  `url` varchar(1000) NOT NULL DEFAULT '_' COMMENT 'tpwd corresponding url',
  `commission_rate` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'commission rate',
  `commission_type` varchar(30) NOT NULL DEFAULT '' COMMENT 'commission type',
  `expire_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'expire time',
  `is_deleted` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'is deleted',
  `other1` varchar(300) NOT NULL DEFAULT '' COMMENT 'other1',
  `other2` varchar(300) NOT NULL DEFAULT '' COMMENT 'other2',
  `other3` varchar(300) NOT NULL DEFAULT '' COMMENT 'other3',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='table for article info in tbk';
