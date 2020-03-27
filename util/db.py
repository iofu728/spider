# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-24 13:32:39
# @Last Modified by:   gunjianpan
# @Last Modified time: 2020-03-27 18:37:27

import os
import shutil
import sys
from configparser import ConfigParser

import pymysql
sys.path.append(os.getcwd())
from util.util import echo, read_file

configure_path = "util/db.ini"


class Db(object):
    """ db operation, without sql injection """

    def __init__(self, database: str, return_type: str = "list"):
        self.load_configure()
        self.connect_db(database, return_type)
        self.database = database
        self.return_type = return_type

    def load_configure(self):
        """ load configure """
        if not os.path.exists(configure_path):
            shutil.copy(configure_path + ".tmp", configure_path)
        cfg = ConfigParser()
        cfg.read(configure_path, "utf-8")
        self.mysql_host = cfg.get("mysql", "hostname")
        self.mysql_user = cfg.get("mysql", "username")
        self.mysql_pw = cfg.get("mysql", "passwd")
        self.mysql_char = cfg.get("mysql", "charset")

    def connect_db(self, database: str, return_type: str):
        """ connect database """
        cursorclass = (
            pymysql.cursors.DictCursor
            if return_type == "dict"
            else pymysql.cursors.Cursor
        )
        try:
            self.db = pymysql.connect(
                host=self.mysql_host,
                user=self.mysql_user,
                password=self.mysql_pw,
                db=database,
                charset=self.mysql_char,
                cursorclass=cursorclass,
            )
        except pymysql.OperationalError:
            echo(0, "Please change mysql info in util/db.ini!!!")
            self.db = False
        except pymysql.InternalError:
            echo(2, "Try to create database in mysql.........")
            if self.create_db(database):
                self.connect_db(database, return_type)
            else:
                self.db = False
        except:
            echo(0, "Other db error!!!")
            self.db = False

    def create_db(self, database: str):
        """ crete database """
        db = pymysql.connect(
            host=self.mysql_host,
            user=self.mysql_user,
            password=self.mysql_pw,
            charset=self.mysql_char,
        )
        database_sql = "CREATE DATABASE if not exists {}".format(database)
        try:
            cursor = db.cursor()
            cursor.execute(database_sql)
            echo(2, "Create Database {} Success!!!".format(database))
            return True
        except:
            echo(0, "Create Database {} error".format(database))
            return False

    def create_table(self, sql_path: str):
        if not os.path.exists(sql_path):
            echo(0, "Create Table {} error, file not found".format(sql_path))
            return False
        create_table_sql = "\n".join(read_file(sql_path))
        try:
            cursor = self.db.cursor()
            cursor.execute(create_table_sql)
            echo(2, "Create Table from {} Success!!!".format(sql_path))
            return True
        except Exception as e:
            echo(0, "Create Table from {} error".format(sql_path), e)
            return False

    def select_db(self, sql: str):
        """  select sql @return False: Expection; list: Success """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception as e:
            self.connect_db(self.database, self.return_type)
            echo(0, "execute sql {} error".format(sql), e)
            return False

    def select_one(self, sql: str):
        """ select one @return False: Expection; list: Success """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            return cursor.fetchone()
        except Exception as e:
            self.connect_db(self.database, self.return_type)
            echo(0, "execute sql {} error".format(sql), e)
            return False

    def insert_db(self, sql: str):
        """ insert sql @return False: Expection; True: Success """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            return True
        except Exception as e:
            self.connect_db(self.database, self.return_type)
            echo(0, "execute sql {} error".format(sql), e)
            self.db.rollback()
            return False

    def update_db(self, sql: str):
        """  update sql @return False: Expection; True: Success """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            return True
        except Exception as e:
            self.connect_db(self.database, self.return_type)
            echo(0, "execute sql {} error".format(sql), e)
            self.db.rollback()
            return False
