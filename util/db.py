# -*- coding: utf-8 -*-
# @Author: gunjianpan
# @Date:   2018-10-24 13:32:39
# @Last Modified by:   gunjianpan
# @Last Modified time: 2021-06-29 22:53:05

import os
import sys
import threading

import pymysql
import redis
import time
from elasticsearch import Elasticsearch

sys.path.append(os.getcwd())
from util.util import echo, read_file, load_cfg

configure_path = "util/util.ini"


class Db(object):
    DB_TYPE = {ii: ii for ii in ["redis", "es"]}

    def __init__(
        self, database: str, return_type: str = "list", local_infile: bool = False
    ):
        db_type = self.DB_TYPE.get(database, "mysql")
        self.load_configure(db_type)
        if db_type == "mysql":
            self.database = database
            self.return_type = return_type
            self.local_infile = local_infile
            self.lock = threading.Lock()
            self.reconnect()
        else:
            self.connect(db_type)

    def load_configure(self, db_type: str = "mysql"):
        cfg = load_cfg(configure_path)
        if db_type == "mysql":
            self.mysql_host = cfg.get("mysql", "hostname")
            self.mysql_user = cfg.get("mysql", "username")
            self.mysql_pw = cfg.get("mysql", "passwd")
            self.mysql_char = cfg.get("mysql", "charset")
        elif db_type == "redis":
            self.redis_host = cfg.get("Redis", "host")
            self.redis_port = cfg.get("Redis", "port")
            self.redis_db = cfg.get("Redis", "db")
            self.redis_pw = cfg.get("Redis", "password")
        elif db_type == "es":
            self.es_host = cfg.get("ElasticSearch", "host")
            self.es_port = cfg.get("ElasticSearch", "port")
            self.es_user = cfg.get("ElasticSearch", "username")
            self.es_pw = cfg.get("ElasticSearch", "password")

    def connect(self, db_type: str):
        if db_type == "redis":
            self.r = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_pw,
            )
        elif db_type == "es":
            self.es = Elasticsearch(
                hosts=f"{self.es_host}:{self.es_port}",
                http_auth=(self.es_user, self.es_pw),
            )

    def connect_db(self, database: str, return_type: str, local_infile: bool = False):
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
                local_infile=local_infile,
            )
        except pymysql.OperationalError:
            echo(0, "Please change mysql info in util/db.ini!!!")
            self.db = False
        except pymysql.InternalError:
            echo(2, "Try to create database in mysql.........")
            if self.create_db(database):
                self.connect_db(database, return_type, local_infile)
            else:
                self.db = False
        except:
            echo(0, "Other db error!!!")
            self.db = False

    def reconnect(self):
        self.connect_db(self.database, self.return_type, self.local_infile)

    def ping_db(self, num: int = 20, stime: int = 3):
        _num, status = 0, True
        while status and _num <= num:
            try:
                self.db.ping()
                status = False
            except:
                self.reconnect()
                if self.db != False:
                    status = False
                    break
                _num += 1
                time.sleep(stime)

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
        create_table_sql = "".join(read_file(sql_path))
        try:
            with self.db.cursor() as cursor:
                cursor.execute(create_table_sql)
                echo(2, "Create Table from {} Success!!!".format(sql_path))
                return True
        except Exception as e:
            echo(0, "Create Table from {} error".format(sql_path), e)
            return False

    def execute(self, sql: str, use_lock: bool = False):
        if use_lock:
            self.lock.acquire()
        try:
            self.ping_db()
            with self.db.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                self.db.commit()
                if use_lock:
                    self.lock.release()
                return result
        except Exception as e:
            if use_lock:
                self.lock.release()
            echo(0, "execute sql {} error".format(sql), e)
            self.db.rollback()
            return False

    def select_db(self, sql: str):
        return self.execute(sql)

    def insert_db(self, sql: str):
        return self.execute(sql, True) is not False

    def update_db(self, sql: str):
        return self.execute(sql, True) is not False
