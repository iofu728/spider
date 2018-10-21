# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-21 12:49:22
# @Last Modified by:   gunjianpan
# @Last Modified time: 2018-10-21 13:34:02
import pymysql


class Db(object):
    """
    db operation, without sql injection
    """

    def __init__(self):
        self.db = pymysql.connect("localhost", "root", "", "netease")

    def select_db(self, sql):
        """
        select sql
        @return False: Expection; []: Success
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception as e:
            return False

    def insert_db(self, sql):
        """
        insert sql
        @return False: Expection; True: Success
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            return False

    def update_db(self, sql):
        """
        update sql
        @return False: Expection; True: Success
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            return False
