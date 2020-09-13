# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject
from PyQt5.QtSql import QSqlDatabase
from enum import Enum


def _Singleton(cls):
    """单实例装饰器"""
    _instance = {}

    def _singleton(*args, **kargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kargs)
        return _instance[cls]

    return _singleton


class FieldType(Enum):
    '''FieldTyp类型及转换类'''
    Int = 1
    Float = 2
    String = 3
    Date = 4
    Boolean = 5
    DateTime = 6
    Time = 7
    Other = 0
    Unknown = -1


@_Singleton
class _MySqlFieldType(QObject):

    INT = 3  # PyQt5 typeName int
    TINYINT = 1  # PyQt5 typeName char
    SMALLINT = 2  # PyQt5 typeName short
    MEDIUMINT = 9  # PyQt5 typeName int
    BIGINT = 8  # PyQt5 typeName qlonglong
    BIT = 16  # PyQt5 typeName QString
    FLOAT = 4  # PyQt5 typeName double
    DOUBLE = 5  # PyQt5 typeName double
    DECIMAIL = 246  # PyQt5 typeName double
    CHAR = 254  # PyQt5 typeName QString
    VARCHAR = 253  # PyQt5 typeName QString
    TINYTEXT = 252  # PyQt5 typeName QString
    TEXT = 252  # PyQt5 typeName QString
    MEDIUMTEXT = 252  # PyQt5 typeName QString
    LONGTEXT = 252  # PyQt5 typeName QString
    BINARY = 254  # PyQt5 typeName QByteArray
    VARBINARY = 253  # PyQt5 typeName QByteArray
    TINYBLOB = 252  # PyQt5 typeName QByteArray
    BLOB = 252  # PyQt5 typeName QByteArray
    MEDIUMBLOB = 252  # PyQt5 typeName QByteArray
    LONGBLOB = 252  # PyQt5 typeName QByteArray
    DATE = 10  # PyQt5 typeName QDate
    TIME = 11  # PyQt5 typeName QString
    YEAR = 13  # PyQt5 typeName int
    DATATIME = 12  # PyQt5 typeName QDateTime
    TIMESTAMP = 7  # PyQt5 typeName QDateTime
    POINT = 255  # PyQt5 typeName QString
    LINESTRING = 255  # PyQt5 typeName QString
    POLYGON = 255  # PyQt5 typeName QString
    GEOMETRY = 255  # PyQt5 typeName QString
    MULTIPOINT = 255  # PyQt5 typeName QString
    MULTINESPOLYGON = 255  # PyQt5 typeName QString
    MULTIPOLYGON = 255  # PyQt5 typeName QString
    GEOMETRYCOLLECTION = 255  # PyQt5 typeName QString
    NUM = 254  # PyQt5 typeName QString
    SET = 254  # PyQt5 typeName QString

    def __init__(self):
        self._dic = {
            self.TINYINT: FieldType.Int,
            self.SMALLINT: FieldType.Int,
            self.INT: FieldType.Int,
            self.FLOAT: FieldType.Float,
            self.DOUBLE: FieldType.Float,
            self.TIMESTAMP: FieldType.DateTime,
            self.BIGINT: FieldType.Int,
            self.MEDIUMINT: FieldType.Int,
            self.DATE: FieldType.Date,
            self.TIME: FieldType.Time,
            self.DATATIME: FieldType.DateTime,
            self.YEAR: FieldType.Int,
            self.BIT: FieldType.Boolean,
            self.DECIMAIL: FieldType.Float,
            self.TEXT: FieldType.String,
            self.VARBINARY: FieldType.String,
            self.BINARY: FieldType.String,
            self.LINESTRING: FieldType.String,
        }

    def getFieldType(self, typeID: int) -> FieldType:
        try:
            return self._dic[typeID]
        except Exception:
            raise RuntimeError("MySql数据库中数据类型{}在类型转换器中没有定义！".format(typeID))


def getFieldType(db: QSqlDatabase, typeID: int) -> FieldType:
    '''根据当前数据库类型，返回一个数据库中字段的FieldType枚举值'''
    database_type = {'QMYSQL3': _MySqlFieldType}
    fun = database_type[db.driverName()]()
    tp = fun.getFieldType(typeID)
    return tp
