
from PyQt5 import QtCore,QtSql
from PyQt5.QtCore import Qt
from jplib.database.FieldType import FieldType,getFieldType
from jplib.model.constants import StatisticsMode,_statisticsColumn


class ViewColumn(object):
    def __init__(self,
                 model: QtCore.QAbstractTableModel = None,
                 header: str = '',
                 fieldName: str = '',
                 align: Qt.AlignmentFlag = Qt.AlignLeft
                 | Qt.AlignVCenter,
                 formatString: str = None,
                 valueRange=[0, 0]):
        '''在tableview中要显示的一个列的信息的封装
        header：列标题; fieldName:字段名，如果是计算列，
        则应设置一个数据库表中不存在的字段名
        参数 formatString '{:,.2f}' 分节符两位小数;\n
        rowSource和treeSource可以为一个SQL或一个列表:\n
        rowSource必须有两列(编号,文本),
        treeSource设置用于tree的数据列表或查询语句，
        必须有三列(编号,文本，父编号);
        '''
        super().__init__()
        self.header = header
        self.fieldName = fieldName
        self.align = align
        self.formatString = formatString
        self.jpFieldType: FieldType = FieldType.Unknown
        self._valueRange = valueRange
        self._rowSource = []
        self.rootID = None
        self._treeSource = []
        self.prefix = None
        self.suffix = None
        self.modelColumn = None
        self.displayColumn = None
        self.parentColumn = None
        self.parent = None
        self.width = 100
        self._statisticses = []

    def addStatistics(self,
                      statisticsMode: StatisticsMode,
                      precision: int = 0):
        '''添加一个统计，只能统计子表中的可见列'''
        obj = _statisticsColumn(statisticsMode, precision)
        self._statisticses.append(obj)
        mod = statisticsMode
        if mod == StatisticsMode.Sum:
            obj.func = lambda lst: sum(lst) if lst else None
        if mod == StatisticsMode.Average:
            obj.func = lambda lst: sum(lst) / len(lst) if lst else None
        if mod == StatisticsMode.Min:
            obj.func = lambda lst: min(lst) if lst else None
        if mod == StatisticsMode.Max:
            obj.func = lambda lst: max(lst) if lst else None

    def setRange(self, minValue, maxValue):
        self._valueRange = (minValue, maxValue)

    def range(self):
        if self._valueRange:
            return self._valueRange[0], self._valueRange[1]

    def _getList(self, SqlorList):

        if isinstance(SqlorList, list):
            return SqlorList
        q = QtSql.QSqlQuery(SqlorList)
        lst = []
        while q.next():
            temp = []
            for i in range(q.record().count()):
                temp.append(q.value(i))
            lst.append(temp)
        return lst

    @property
    def fieldIndex(self) -> int:
        # 防止QSqlQueryModel对象没有fieldIndex方法
        model = self.parent.model
        if model is None:
            raise RuntimeError("ViewColumn对象的_model属性不能为None！")
        if isinstance(model, QtSql.QSqlQueryModel):
            return model.record().indexOf(self.fieldName)
        if isinstance(model, QtSql.QSqlTableModel):
            return model.fieldIndex(self.fieldName)
        return -1

    @property
    def rowSource(self):
        return self._rowSource

    @rowSource.setter
    def rowSource(self, SqlorList):
        if SqlorList:
            self._rowSource = self._getList(SqlorList)
            self.modelColumn = 1
            self.displayColumn = 0
            self.formatString = '{}'

    @property
    def treeSource(self):
        return self._treeSource

    @treeSource.setter
    def treeSource(self, SqlorList):
        if SqlorList:
            self._treeSource = self._getList(SqlorList)
            self.modelColumn = 1
            self.displayColumn = 0
            self.parentColumn = 2
            self.formatString = '{}'

    def displayString(self, value):
        f = self.formatString
        if self.jpFieldType == FieldType.Date:
            return value.toString(f) if value else None
        if self.rowSource:
            r = [
                r[self.displayColumn] for r in self.rowSource
                if r[self.modelColumn] == value
            ]
            return r[0] if r else None
        if self.treeSource:
            r = [
                r[self.displayColumn] for r in self.treeSource
                if r[self.modelColumn] == value
            ]
            return r[0] if r else None
        return f.format(value) if value else None


class ViewColumns(object):
    def __init__(self, db=QtSql.QSqlDatabase()):
        '''保存所有tableview中的列信息'''
        self._list = []
        self.db = db

    def __len__(self) -> int:
        return len(self._list)

    def _setViewColumnAlighAndFormatString(self, viewColumn: ViewColumn):
        '''根据已有的列信息，设置默认格式'''
        vc = viewColumn
        rec = self.model.record()
        if vc.fieldIndex == -1:
            vc.formatString = '{:,.2f}'
            vc.align = Qt.AlignVCenter | Qt.AlignRight
        else:
            field = rec.field(vc.fieldName)
            vc.jpFieldType = getFieldType(self.db, field.typeID())
            if vc.jpFieldType == FieldType.Int:
                vc.formatString = '{:,.0f}'
                vc.align = Qt.AlignVCenter | Qt.AlignRight
            elif vc.jpFieldType == FieldType.Float:
                vc.formatString = '{:,.' + str(field.precision()) + 'f}'
                vc.align = Qt.AlignVCenter | Qt.AlignRight
            elif vc.jpFieldType == FieldType.Date:
                vc.formatString = 'yyyy-MM-dd'
                vc.align = Qt.AlignCenter
            elif vc.jpFieldType == FieldType.String:
                vc.formatString = '{}'
                vc.align = Qt.AlignVCenter | Qt.AlignLeft

    def _setDefaultColumn(self, model, db, record: QtSql.QSqlRecord):
        '''根据一个record对象设置默认ViewColumns'''
        self.__model = model
        for i in range(record.count()):
            fld = record.field(i)
            fn = fld.name()
            vc = ViewColumn(model, fn, fn)
            vc.parent = self
            self._list.append(vc)
            self._setViewColumnAlighAndFormatString(vc)

    def _getPropertyList(self, propertyName: str) -> list:
        pn = propertyName
        _pn = '_disp_' + propertyName
        if _pn not in self.__dict__:
            self.__dict__[_pn] = []
            for vc in self._list:
                self.__dict__[_pn].append(vc.__dict__[pn])
        return self.__dict__[_pn]

    @property
    def _alignmentList(self) -> list:
        return self._getPropertyList('align')

    @property
    def _fieldNameList(self) -> list:
        return self._getPropertyList('fieldName')

    @property
    def _headerList(self) -> list:
        return self._getPropertyList('header')

    @property
    def _widthList(self) -> list:
        return self._getPropertyList('width')

    @property
    def _fieldIndexList(self) -> list:
        pn = 'fieldIndex'
        _pn = '_disp_' + pn
        if _pn not in self.__dict__:
            self.__dict__[_pn] = []
            for vc in self._list:
                self.__dict__[_pn].append(vc.fieldIndex)
        return self.__dict__[_pn]

    @property
    def model(self) -> QtSql.QSqlQueryModel:
        return self.__model

    def setModel(self, model: QtSql.QSqlQueryModel):
        if len(self._list) == 0:
            raise Exception("显示列集合为空，请先使用append()方法添加列信息！")
        if not isinstance(model, QtSql.QSqlQueryModel):
            raise Exception("model参数必须为QSqlQueryModel或其子类的实例！")
        self.__model = model
        record = model.record()
        for vc in self._list:
            at = vc.fieldIndex
            if at != -1:
                field = record.field(at)
                vc.jpFieldType = getFieldType(self.db, field.typeID())
            if vc.formatString is None:
                self._setViewColumnAlighAndFormatString(vc)

    def append(self, obj: ViewColumn):
        if not obj.fieldName:
            raise RuntimeError('增加的显示列未设置字段名!')
        fn = obj.fieldName
        if not obj.header:
            raise RuntimeError('增加的显示列[{}]未设置标题!'.format(fn))
        if obj.fieldName in [obj.fieldName for obj in self._list]:
            raise RuntimeError('增加的显示列[{}]字段名重复!'.format(fn))
        obj.parent = self
        self._list.append(obj)

    def __getitem__(self, key) -> ViewColumn:
        if isinstance(key, int):
            try:
                r = self._list[key]
            except IndexError as e:
                r = None
                raise RuntimeError("'{}'在对象'ViewColumns'中没有找到!".format(key))
            return r
        if isinstance(key, str):
            for vc in self._list:
                if vc.fieldName == key:
                    return vc
            raise RuntimeError("'字段名为[{}]'在对象'ViewColumns'中没有找到!".format(key))

    def __iter__(self):
        return iter(self._list)

    def count(self):
        return self.__len__()

