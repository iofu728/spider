/*
* @Author: gunjianpan
* @Date:   2018-10-21 13:49:42
* @Last Modified by:   gunjianpan
* @Last Modified time: 2018-10-23 20:06:40
*/
CREATE TABLE if not exists `playlist_detail` (
  `id` int(15) unsigned NOT NULL AUTO_INCREMENT COMMENT 'auto-increment primary keys',
  `song_id` int(15) unsigned NOT NULL DEFAULT 0 COMMENT 'song id',
  `song_name` varchar(300) NOT NULL DEFAULT 'DEFAULT' COMMENT 'song name',
  `classify` varchar(50) NOT NULL DEFAULT 'DEFAULT' COMMENT 'classify name',
  `time` int(10) unsigned NOT NULL DEFAULT 0 COMMENT 'song in playlist time',
  `play_time` int(20) unsigned NOT NULL DEFAULT 0 COMMENT 'song play time',
  `is_deleted` int(2) unsigned NOT NULL DEFAULT 0 COMMENT 'flag for deleted',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='table for playlist detail';

CREATE TABLE if not exists `playlist_queue` (
  `id` int(15) unsigned NOT NULL AUTO_INCREMENT COMMENT 'auto-increment primary keys',
  `playlist_id` int(15) unsigned NOT NULL DEFAULT 0 COMMENT 'playlist id',
  `classify` varchar(50) NOT NULL DEFAULT 'DEFAULT' COMMENT 'classify name',
  `is_finished` int(2) unsigned NOT NULL DEFAULT 0 COMMENT 'flag for finished',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'create time',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 comment='table for playlist queue';

LOAD DATA INFILE '/Users/gunjianpan/Desktop/git/spider/song_detail' INTO TABLE playlist_detail
    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\n' (`song_id`, `song_name`, `classify`, `time`, `play_time`)
