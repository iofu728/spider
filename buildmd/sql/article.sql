-- using tbk;
CREATE TABLE if not exists `article` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'auto-increment primary keys',
  `article_id` varchar(50) NOT NULL DEFAULT '0' COMMENT 'yd article id',
  `title` varchar(500) NOT NULL DEFAULT '0' COMMENT 'article title',
  `q` varchar(500) NOT NULL DEFAULT '0' COMMENT 'article q',
  `established_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'article created time',
  `modified_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'article modified time',
  `is_deleted` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'is deleted',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='article table';
