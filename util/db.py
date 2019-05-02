'''
@Author: gunjianpan
@Date:   2018-10-24 13:32:39
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-24 01:13:29
'''

import os
import pymysql
import shutil

from configparser import ConfigParser
from util.util import echo

configure_path = 'util/db.ini'


class Db(object):
    ''' db operation, without sql injection '''

    def __init__(self, database: str, return_type: str = 'list'):
        self.load_configure()
        self.connect_db(database, return_type)
        # try:
        #     self.db = pymysql.connect("localhost", "root", "", database)
        # except:
        #     print('db connect error!!! Please check util/db.py')
        #     self.db = False

    def load_configure(self):
        ''' load configure '''
        if not os.path.exists(configure_path):
            shutil.copy(configure_path + '.tmp', configure_path)
        cfg = ConfigParser()
        cfg.read(configure_path, 'utf-8')
        self.mysql_host = cfg.get('mysql', 'hostname')
        self.mysql_user = cfg.get('mysql', 'username')
        self.mysql_pw = cfg.get('mysql', 'passwd')
        self.mysql_char = cfg.get('mysql', 'charset')

    def connect_db(self, database: str, return_type: str):
        ''' connect database '''

        cursorclass = pymysql.cursors.DictCursor if return_type == 'dict' else pymysql.cursors.Cursor
        try:
            self.db = pymysql.connect(host=self.mysql_host,
                                      user=self.mysql_user,
                                      password=self.mysql_pw,
                                      db=database,
                                      charset=self.mysql_char,
                                      cursorclass=cursorclass)
        except pymysql.OperationalError:
            echo(0, 'Please change mysql info in util/db.ini!!!')
            self.db = False
        except pymysql.InternalError:
            echo(2, 'Try to create database in mysql.........')
            if self.create_db(database):
                self.connect_db(database, return_type)
            else:
                self.db = False
        except:
            echo(0, 'Other db error!!!')
            self.db = False

    def create_db(self, database: str):
        ''' crete database '''
        db = pymysql.connect(host=self.mysql_host,
                             user=self.mysql_user,
                             password=self.mysql_pw,
                             charset=self.mysql_char)
        database_sql = 'CREATE DATABASE if not exists {}'.format(database)
        try:
            cursor = db.cursor()
            cursor.execute(database_sql)
            return True
        except:
            echo(0, 'Create Database {} error'.format(database))
            return False

    def select_db(self, sql: str):
        '''  select sql @return False: Expection; list: Success '''

        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            return cursor.fetchall()
        except:
            return False

    def select_one(self, sql: str):
        ''' select one @return False: Expection; list: Success '''

        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            return cursor.fetchone()
        except:
            return False

    def insert_db(self, sql: str):
        ''' insert sql @return False: Expection; True: Success '''
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False

    def update_db(self, sql: str):
        '''  update sql @return False: Expection; True: Success '''

        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False
