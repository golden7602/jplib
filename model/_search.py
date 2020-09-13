import logging
import typing
from functools import partial

from click.types import DateTime
from PyQt5 import QtCore, QtSql, QtWidgets
from PyQt5.QtCore import QModelIndex, Qt

from jplib.database.FieldType import FieldType
from jplib.model import ViewColumns
from jplib.model._delegate import (DateDelegate, FloatDelegate, IntgerDelegate,
                             IntSelectDelegate,
                             ReadOnlyDelegate, StringDelegate)
from jplib.model._icos import _ICO_DICT, _loadIcon
#from model._viewColumn import ViewColumns

TITLE = '删除按钮,关系,(,字段名,运算,起始值,结束值,)'.split(',')
COLUMN_BUTTON = 0
COLUMN_OPERATOR = 1

COLUMN_BRACKETLEFT = 2
COLUMN_FIELD = 3
COLUMN_EXP = 4
COLUMN_VALUE1 = 5
COLUMN_VALUE2 = 6
COLUMN_BRACKETRIGHT = 7
COLUMN_VALUEENABLED = -1
COLUMN_TITLECHINESE = -2
COLUMN_TITLEENGLISH = -3


class Ui_DlgSearch(object):
    def setupUi(self, DlgSearch):
        DlgSearch.setObjectName("DlgSearch")
        DlgSearch.resize(702, 349)
        DlgSearch.setMinimumSize(QtCore.QSize(0, 0))
        DlgSearch.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setFamily("Arial")
        DlgSearch.setFont(font)
        self.verticalLayout = QtWidgets.QVBoxLayout(DlgSearch)
        self.verticalLayout.setContentsMargins(3, 3, 3, 10)
        self.verticalLayout.setSpacing(15)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tableView = QtWidgets.QTableView(DlgSearch)
        self.tableView.setEditTriggers(
            QtWidgets.QAbstractItemView.AllEditTriggers)
        self.tableView.setObjectName("tableView")
        self.verticalLayout.addWidget(self.tableView)
        self.buttonBox = QtWidgets.QDialogButtonBox(DlgSearch)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel
                                          | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(DlgSearch)
        # self.buttonBox.accepted.connect(DlgSearch.accept)
        # self.buttonBox.rejected.connect(DlgSearch.reject)
        QtCore.QMetaObject.connectSlotsByName(DlgSearch)

    def retranslateUi(self, DlgSearch):
        _translate = QtCore.QCoreApplication.translate
        DlgSearch.setWindowTitle(_translate("DlgSearch", "Search"))


ExpressionData = {
    FieldType.String:
    [("`{fn}` like '%{v1}%'", 1, 0, "包含", "Include"),
     ("`{fn}`='{v1}'", 1, 0, "等于", "Equal"),
     ("`{fn}`>'{v1}'", 1, 0, "大于", "GreaterThan"),
     ("`{fn}`>='{v1}'", 1, 0, "大于或等于", "GreaterOrEqual"),
     ("`{fn}`<'{v1}'", 1, 0, "小于", "LessThan"),
     ("`{fn}`<='{v1}'", 1, 0, "小于或等于", "LessOrEqual"),
     ("`{fn}`<>'{v1}'", 1, 0, "不等于", "NotEqual"),
     ("`{fn}` like '{v1}%'", 1, 0, "开头是", "Beginlike "),
     ("Not `{fn}` like '{v1}%'", 1, 0, "开头不是", "NotBeginlike "),
     ("`{fn}` like '%{v1}'", 1, 0, "结束是", "Endlike "),
     ("Not` {fn}` like '%{v1}'", 1, 0, "结束不是", "NotEndlike "),
     ("IsNull(`{fn}`)", 0, 0, "为空", "IsNull"),
     ("Not IsNull(`{fn}`)", 0, 0, "不为空", "NotNull"),
     ("LENGTH(`{fn}`)={v1}", 1, 0, "长度为", "LengthIs"),
     ("LENGTH(`{fn}`)>={v1}", 1, 0, "长度大于等于", "LengthGreaterOrEqual"),
     ("LENGTH(`{fn}`)<={v1}", 1, 0, "长度小于等于", "LengthLessOrEqual"),
     ("LENGTH(`{fn}`)>{v1}", 1, 0, "长度大于", "LengthGreaterThan"),
     ("LENGTH(`{fn}`)<{v1}", 1, 0, "长度小于", "LengthLessThan"),
     ("`{fn}`=''", 0, 0, "为空字符", "IsEmptyString")],
    FieldType.Boolean: [("`{fn}`=1", 0, 0, "值为是", "IsTrue"),
                          ("`{fn}`=0", 0, 0, "值为否", "ISFalse"),
                          ("IsNull(`{fn}`)", 0, 0, "为空", "IsNull"),
                          ("Not IsNull(`{fn}`)", 0, 0, "不为空", "NotNull")],
    FieldType.Date:
    [("`{fn}`='{v1}'", 1, 0, "等于", "Equal"),
     ("`{fn}`<'{v1}'", 1, 0, "早于", "EarluThan"),
     ("`{fn}`<='{v1}'", 1, 0, "早于等于", "EarlyOrEqual"),
     ("`{fn}`>'{v1}'", 1, 0, "晚于", "LaterThan"),
     ("`{fn}`>='{v1}'", 1, 0, "晚于等于", "LaterOrEqual"),
     ("`{fn}`<>'{v1}'", 1, 0, "不等于", "NotEqual"),
     ("`{fn}` Between '{v1}' AND '{v1}'", 1, 1, "在区间内", "Between"),
     ("Not (`{fn}` Between '{v1}' AND '{v1}')", 1, 1, "不在区间内", "NotBetween"),
     ("IsNull(`{fn}`)", 0, 0, "为空", "IsNull"),
     ("Not IsNull(`{fn}`)", 0, 0, "不为空", "NotNull")],
    FieldType.Int:
    [("`{fn}`={v1}", 1, 0, "等于", "Equal"),
     ("`{fn}`>{v1}", 1, 0, "大于", "GreaterThan"),
     ("`{fn}`>={v1}", 1, 0, "大于或等于", "GreaterOrEqual"),
     ("`{fn}`<{v1}", 1, 0, "小于", "LessThan"),
     ("`{fn}`<={v1}", 1, 0, "小于或等于", "LessOrEqual"),
     ("`{fn}`<>{v1}", 1, 0, "不等于", "NotEqual"),
     ("`{fn}` Between {v1} AND {v1}", 1, 1, "在区间内", "Between"),
     ("Not (`{fn}` Between {v1} AND {v1})", 1, 1, "不在区间内", "NotBetween"),
     ("IsNull(`{fn}`)", 0, 0, "为空", "IsNull"),
     ("Not IsNull(`{fn}`)", 0, 0, "不为空", "NotNull")]
}
ExpressionData[FieldType.Float] = ExpressionData[FieldType.Int]


class _ExpressionTemplate():
    def __init__(self) -> None:
        self.template = ''
        self.valueEnabled = (0, 0)
        self.titleEnglish = ''
        self.titleChinese = ''


class _Expressions():
    def __init__(self, tp: FieldType) -> None:
        '''某个类型字段的可选择表达式'''
        super().__init__()
        self._list = []
        for tup in ExpressionData[tp]:
            e = _ExpressionTemplate()
            e.template = tup[0]
            e.valueEnabled = tup[1:3]
            e.titleEnglish = tup[4]
            e.titleChinese = tup[3]
            self._list.append(e)

    def __getitem__(self, key):
        return self._list[key]

    def item(self):
        for e in self._list:
            yield e


class _Condiction():
    def __init__(self, parent) -> None:
        '''窗体中一行条件，parent指Condictions集合类'''
        self.template: typing.Any = ''
        self.valueEnabled = (0, 0)
        self.value = (None, None)
        self.bracketsLeft = None
        self.bracketsRight = None
        self.Operator = None
        self.titleEnglish = None
        self.titleChinese = None
        self._viewColumn = None
        self.parent = parent

    @property
    def fieldName(self) -> str:
        if self._viewColumn:
            return self._viewColumn.fieldName
        else:
            return ''

    def __str__(self) -> str:
        result = []
        s = '{}={}\n'
        result.append(s.format('template', self.template))
        result.append(s.format('valueEnabled', self.valueEnabled))
        result.append(s.format('fieldName', self.fieldName))
        result.append(s.format('value', self.value))
        result.append(s.format('bracketsLeft', self.bracketsLeft))
        result.append(s.format('bracketsRight', self.bracketsRight))
        result.append(s.format('Operator', self.Operator))
        result.append(s.format('titleEnglish', self.titleEnglish))
        result.append('-------------------------------------------')
        return ''.join(result)

    def check(self) -> bool:
        # 返回当前条件是否完整

        if not self.fieldName:
            return False
        if not self.template:
            return False
        e = self.valueEnabled
        if e == (0, 0):
            return True
        v = self.value
        result=True
        if e[0]:
            result=  (True if v[0] else False) and result
        if e[1]:
            result=  (True if v[1] else False) and result
        return result

    def setViewColumn(self, viewColumn):
        self._viewColumn = viewColumn

    @property
    def jpFieldType(self):
        return self._viewColumn.jpFieldType

    def getCondition(self) -> str:
        '''处理一行条件为字符串'''
        v1 = self.getConditionString(COLUMN_VALUE1)
        v2 = self.getConditionString(COLUMN_VALUE2)
        v = self.template.format(fn=self.fieldName, v1=v1, v2=v2)
        # 处理逻辑运算符及括号
        v = self.bracketsLeft + v if self.bracketsLeft else v
        v = self.Operator + " " + v if self.Operator else v
        v = v + self.bracketsRight if self.bracketsRight else v
        return v

    def getDiaplayValueString(self, column: int):
        value = self.value[column - COLUMN_VALUE1]
        if not value:
            return None
        tp = self._viewColumn.jpFieldType
        if tp in (FieldType.String, FieldType.Float, FieldType.Int):
            return self._viewColumn.formatString.format(value)
        elif tp in (FieldType.Date, FieldType.DateTime):
            return value.toString('yyyy-MM-dd')
        else:
            raise Exception('不应该执行到此')

    def getConditionString(self, column: int):
        value = self.value[column - COLUMN_VALUE1]
        if not value:
            return None
        tp = self._viewColumn.jpFieldType
        if tp in (FieldType.String, FieldType.Float, FieldType.Int):
            return str(value)
        elif tp in (FieldType.Date, FieldType.DateTime):
            return value.toString('yyyy-MM-dd')
        else:
            raise Exception('不应该执行到此')

    def getDisplayString(self, col: int):
        if col == COLUMN_FIELD:
            for vc in self.parent.parent.viewColumns:
                if vc.fieldName == self.fieldName:
                    return vc.header
        elif col == COLUMN_OPERATOR:
            return self.Operator
        elif col == COLUMN_BRACKETLEFT:
            return self.bracketsLeft
        elif col == COLUMN_BRACKETRIGHT:
            return self.bracketsRight
        elif col == COLUMN_EXP:
            return self.titleChinese
        elif col in (COLUMN_VALUE1, COLUMN_VALUE2):
            return self.getDiaplayValueString(col)
        else:
            return None

    def setData(self, index: QtCore.QModelIndex, Any, role=Qt.EditRole):
        col = index.column()
        if col == COLUMN_FIELD:
            self._viewColumn = self.parent.parent.viewColumns[Any]
            #self.fieldName = Any
        elif col == COLUMN_OPERATOR:
            self.Operator = Any
        elif col == COLUMN_BRACKETLEFT:
            self.bracketsLeft = Any
        elif col == COLUMN_BRACKETRIGHT:
            self.bracketsRight = Any
        elif col == COLUMN_EXP:
            self.template = Any
        elif col == COLUMN_VALUE1:
            self.value = (Any, self.value[1])
        elif col == COLUMN_VALUE2:
            self.value = (self.value[0], Any)
        elif col == COLUMN_VALUEENABLED:
            self.valueEnabled = Any
        elif col == COLUMN_TITLECHINESE:
            self.titleChinese = Any
        elif col == COLUMN_TITLEENGLISH:
            self.titleEnglish = Any
        return True

    def getEditRole(self, col: int):
        if col == COLUMN_FIELD:
            return self.fieldName
        elif col == COLUMN_OPERATOR:
            return self.Operator
        elif col == COLUMN_BRACKETLEFT:
            return self.bracketsLeft
        elif col == COLUMN_BRACKETRIGHT:
            return self.bracketsRight
        elif col == COLUMN_EXP:
            return self.template
        elif col == COLUMN_VALUE1:
            return self.value[0]
        elif col == COLUMN_VALUE2:
            return self.value[1]
        else:
            return None

    def delegate(self, col: int):
        par = self.parent.parent
        if col not in (COLUMN_VALUE1, COLUMN_VALUE2):
            raise Exception('参数有误')
        tp = self._viewColumn.jpFieldType
        if tp == FieldType.String:
            result = StringDelegate(par)
        elif tp == FieldType.Int:
            result = IntgerDelegate(par)
        elif tp == FieldType.Float:
            result = FloatDelegate(par)
        elif tp == FieldType.Boolean:
            result = IntSelectDelegate(par)
        elif tp in (FieldType.Date, FieldType.DateTime):
            de = DateDelegate(par)
            de.defaultDate = QtCore.QDate.currentDate()
            result = de
        else:
            result = ReadOnlyDelegate(par)
        if self.valueEnabled[col - COLUMN_VALUE1]:
            return result
        else:
            return ReadOnlyDelegate(par)

    def getAlign(self, column: int):
        if column in (COLUMN_OPERATOR, COLUMN_BRACKETLEFT,
                      COLUMN_BRACKETRIGHT):
            return Qt.AlignCenter
        elif column in (COLUMN_FIELD, COLUMN_EXP, COLUMN_BUTTON):
            return Qt.AlignLeft | Qt.AlignVCenter
        elif column in (COLUMN_VALUE1, COLUMN_VALUE2):
            vc = self._viewColumn
            if vc.jpFieldType == FieldType.String:
                return Qt.AlignLeft | Qt.AlignVCenter
            elif vc.jpFieldType in (FieldType.Int, FieldType.Float):
                return Qt.AlignLeft | Qt.AlignVCenter
            elif vc.jpFieldType in (FieldType.Date, FieldType.DateTime,
                                    FieldType.Boolean, FieldType.Unknown):
                return Qt.AlignCenter
        else:
            return Qt.AlignCenter


class _Condictions():
    def __init__(self, parent) -> None:
        '''parent 指searchMolde'''
        self.parent = parent
        self.list = []

    def count(self):
        return len(self.list)

    def __getitem__(self, key):
        return self.list[key]

    def append(self):
        con = _Condiction(self)
        con.setViewColumn(self.parent.viewColumns[0])
        if len(self.list) > 0:
            con.Operator = "AND"
        con.titleChinese = None
        self.list.append(con)
        return con

    def checkLast(self) -> bool:
        if len(self.list) == 0:
            return True
        return self.list[len(self.list) - 1].check()

    def checkRow(self, row):
        self.list[row].check()

    def checkBrackets(self):
        left = [1 for vc in self.list if vc.bracketsLeft]
        right = [1 for vc in self.list if vc.bracketsRight]
        return (len(left) == len(right), len(left), len(right))

    def __iter__(self):
        return iter(self.list)




class _commonComboBox(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        self.parent = parent
        super().__init__(parent)

    def setRowSource(self, data: list):
        self.list = data

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QModelIndex) -> QtWidgets.QWidget:

        wdgt = QtWidgets.QComboBox(parent)
        for row in self.list:
            wdgt.addItem(row)
        return wdgt

    def setEditorData(self, editor: QtWidgets.QWidget, index: QModelIndex):
        data = index.data(Qt.EditRole)
        if data is None:
            editor.setCurrentIndex(-1)
        else:
            editor.setCurrentText(data)

    def setModelData(self, editor: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel, index: QModelIndex):
        data = editor.currentText()
        index.model().setData(index, data, Qt.EditRole)


class _OperatorComboBox(_commonComboBox):
    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QModelIndex) -> QtWidgets.QWidget:
        if index.row() == 0:
            return
        else:
            return super().createEditor(parent, option, index)


class _fieldComboBox(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        self.parent = parent
        self.oldRowSelectedIndex = {}
        super().__init__(parent)

    def currentIndexChanged(self, editor: typing.Any, index: QModelIndex,
                            curIndex: int):
        # 在combo中当前选择行发生变化时，要清除一些数据，并且修改调整
        if not self.oldRowSelectedIndex[index.row()] == editor.currentIndex():
            cur_Row = index.row()
            model = index.model()
            c_index = index.model().createIndex
            con = model.Condictions[cur_Row]
            con.setViewColumn(
                model.viewColumns[editor.currentData().fieldName])
            con.template = None
            con.valueEnabled = (0, 0)
            con.value = (None, None)
            con.titleEnglish = None
            con.titleChinese = None
            newIndex0 = c_index(cur_Row, COLUMN_EXP)
            newIndex2 = c_index(cur_Row, COLUMN_VALUE2)
            model.dataChanged.emit(newIndex0, newIndex2, [Qt.DisplayRole])
            self.oldRowSelectedIndex[index.row()] = editor.currentIndex()

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QModelIndex) -> QtWidgets.QWidget:

        wdgt = QtWidgets.QComboBox(parent)
        vcs = self.parent.viewColumns
        for i, vc in enumerate(vcs):
            wdgt.addItem(vc.header, vc)
        return wdgt

    def setEditorData(self, editor: QtWidgets.QWidget, index: QModelIndex):
        data = index.data(Qt.EditRole)
        if data is None:
            editor.setCurrentIndex(-1)
        else:
            vcs = self.parent.viewColumns
            for i, vc in enumerate(vcs):
                if data == vc.fieldName:
                    editor.setCurrentIndex(i)
                    self.oldRowSelectedIndex[index.row()] = i
        editor.currentIndexChanged.connect(
            partial(self.currentIndexChanged, editor, index))

    def setModelData(self, editor: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel, index: QModelIndex):
        data = editor.currentData().fieldName
        index.model().setData(index, data, Qt.EditRole)

    def updateEditorGeometry(
            self, editor: QtWidgets.QWidget,
            StyleOptionViewItem: QtWidgets.QStyleOptionViewItem,
            index: QModelIndex):
        editor.setGeometry(StyleOptionViewItem.rect)


class _expComboBox(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        self.parent = parent
        super().__init__(parent)

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QModelIndex) -> QtWidgets.QWidget:

        wdgt = QtWidgets.QComboBox(parent)

        tp = self.parent.getFieldType(index.row())
        self.expressionData = _Expressions(tp)
        for e in self.expressionData.item():
            wdgt.addItem(e.titleChinese, e)
        return wdgt

    def currentIndexChanged(self, editor: typing.Any, index: QModelIndex,
                            curIndex: int):
        cur_Row = index.row()
        model = index.model()
        c_index = index.model().createIndex
        con = model.Condictions[cur_Row]
        if editor.currentData():
            exp = self.expressionData[editor.currentIndex()]
            con.template = editor.currentData().template
            con.valueEnabled = editor.currentData().valueEnabled
            v0 = con.value[0] if con.valueEnabled[0] else None
            v1 = con.value[1] if con.valueEnabled[1] else None
            self.value = (v0, v1)
            con.titleEnglish = exp.titleEnglish
            con.titleChinese = exp.titleChinese
            # 如果条件是一个不用输入数据参数的条件，并且当前行是最后一行直接插入一个空行
            if cur_Row == model.Condictions.count() - 1 and con.template == (
                    0, 0):
                model.insertRow(model.Condictions.count())
        else:
            con.value = (None, None)
            con.template = None
            con.valueEnabled = (0, 0)
            con.titleEnglish = None
            con.titleChinese = None
        # 发射信号更新界面相关数据
        model.valueChanged()
        model.dataChanged.emit(c_index(cur_Row, COLUMN_VALUE1),
                               c_index(cur_Row, COLUMN_VALUE2),
                               [Qt.DisplayRole])
        model.refreshValueDelegate(cur_Row)

    def setEditorData(self, editor: QtWidgets.QWidget, index: QModelIndex):
        editor.currentIndexChanged.connect(
            partial(self.currentIndexChanged, editor, index))
        data = index.model().Condictions[index.row()].template
        if data is None:
            editor.setCurrentIndex(0)
        else:
            for row in range(editor.count()):
                if editor.itemData(row).template == data:
                    editor.setCurrentIndex(row)

    def setModelData(self, editor: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel, index: QModelIndex):
        # 表达式变化后，更新VALUEENABLED属性
        # 需要注意的是，清除数据时不能随意清除，要先检查一下允许输入的状态
        #　如果允许输入，就保留数据
        #print("下面会_expComboBox清除第{}行的数据".format(index.row()))
        self.currentIndexChanged(editor, index, editor.currentIndex())

    def updateEditorGeometry(
            self, editor: QtWidgets.QWidget,
            StyleOptionViewItem: QtWidgets.QStyleOptionViewItem,
            index: QModelIndex):
        editor.setGeometry(StyleOptionViewItem.rect)


class SearchTableModel(QtCore.QAbstractTableModel):
    CondictionsCreated = QtCore.pyqtSignal(str)
    def __init__(self, listModel):
        super().__init__()

        self.DlgSearch = QtWidgets.QDialog()
        ui = Ui_DlgSearch()
        ui.setupUi(self.DlgSearch)
        ui.buttonBox.accepted.connect(self.accept)
        self.listModel = listModel
        self.viewColumns = listModel._viewColumns
        self.Condictions = _Condictions(self)

        # 设置taleView
        self.tableView = self.__findTableView(self.DlgSearch)
        self.tableView.setModel(self)
        for i, w in enumerate([30, 50, 30, 150, 150, 100, 100, 30]):
            self.tableView.setColumnWidth(i, w)

        # 设置字段选择代理
        combo_field = _fieldComboBox(self)
        self.tableView.setItemDelegateForColumn(COLUMN_FIELD, combo_field)
        self.tableView.setItemDelegateForColumn(COLUMN_EXP, _expComboBox(self))

        combo_kh_l = _commonComboBox(self)
        combo_kh_l.setRowSource(['', '('])
        self.tableView.setItemDelegateForColumn(COLUMN_BRACKETLEFT, combo_kh_l)

        combo_kh_r = _commonComboBox(self)
        combo_kh_r.setRowSource(['', ')'])
        self.tableView.setItemDelegateForColumn(COLUMN_BRACKETRIGHT,
                                                combo_kh_r)
        combo_op = _OperatorComboBox(self)
        combo_op.setRowSource(['AND', 'OR', 'NOT'])
        self.tableView.setItemDelegateForColumn(COLUMN_OPERATOR, combo_op)

        self.insertRow(0)
        self.tableView.selectionModel().currentRowChanged.connect(
            self.currentRowChanged)
        self.tableView.selectionModel().currentColumnChanged.connect(
            self.currentColumnChanged)
        self.tableView.setContextMenuPolicy(Qt.CustomContextMenu)  # 允许右键产生子菜单
        self.tableView.customContextMenuRequested.connect(
            self.__setTableViewMenu)  # 右键菜单

    def __setTableViewMenu(self, pos):
        # 弹出的位置要减去标题行的高度
        tv = self.tableView
        newPos = tv.mapToGlobal(pos)
        hh = tv.verticalHeader().defaultSectionSize()
        newPos.setY(newPos.y() + hh)
        # 取得鼠标点所在行号
        currentRow = tv.rowAt(pos.y())
        ico_act_del = _loadIcon(_ICO_DICT['ico_act_del'])
        ico_act_new = _loadIcon(_ICO_DICT['ico_act_new'])
        menu = QtWidgets.QMenu()
        item1 = menu.addAction(ico_act_new,u"增加行")
        item1.setEnabled(self.Condictions.checkLast())
        # 如果当前坐标为一个有效行，添加删除菜单
        menu.addSeparator()
        item2 = menu.addAction(ico_act_del,u"删除行")
        item2.setEnabled(self.rowCount(QModelIndex())>1)
        print(currentRow)
        # 显示菜单
        action = menu.exec_(newPos) if currentRow!=-1 else None

        item2.setEnabled(False)

        if action == item1:
            if self.insertRow(self.rowCount(QModelIndex())):
                self._tableView.setCurrentIndex(
                    self.createIndex(self.rowCount(QModelIndex()) - 1, 0))
        elif action == item2:
            self.beginRemoveRows(QModelIndex(), currentRow, currentRow)
            del self.Condictions.list[currentRow]
            self.Condictions[0].Operator=None
            self.endRemoveRows()
            self.removeRow(currentRow)
            self.tableView.setCurrentIndex(
                self.createIndex(currentRow, COLUMN_FIELD))

    def currentColumnChanged(self, cur_index: QModelIndex,
                             old_index: QModelIndex):
        return

    def currentRowChanged(self, cur_index: QModelIndex,
                          old_index: QModelIndex):
        # 当行数只剩下一行时，要清除操作符
        if self.Condictions.count() == 1:
            self.Condictions[0].Operator = None
            index = self.createIndex(0, COLUMN_OPERATOR)
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
        self.refreshValueDelegate(cur_index.row())

    def getFieldType(self, row: int) -> FieldType:
        return self.Condictions[row].jpFieldType

    def __findTableView(self, parent) -> QtWidgets.QTableView:
        '''查找 tableView 对象'''
        obj = parent.findChild(QtWidgets.QTableView, 'tableView')
        if obj:
            return obj
        raise RuntimeError("{}中必须有名为{}的QtableView对象！".format(self._ui, 'tableView'))

    def getViewField(self, index) -> QtSql.QSqlField:
        # 返回listModel中的一个字段，注意index为
        # Condictions中的索引，要转换成
        fn = self.Condictions[index.row()].fieldName
        fld = self.listModel.record().field(fn)
        return fld

    def getViewColumn(self, index: QtCore.QModelIndex):
        '''返回视图中指定列信息对象'''
        fn = self.Condictions[index.row()].fieldName
        return self.viewColumns[fn]

    def rowCount(self, parent: QModelIndex) -> int:
        return self.Condictions.count()

    def columnCount(self, parent: QModelIndex) -> int:
        return len(TITLE)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        #print('开始flag{},{}'.format(index.row(),index.column()))
        col = index.column()
        row = index.row()
        con = self.Condictions[row]
        bz = Qt.ItemIsEnabled | Qt.ItemIsEditable
        if col in (COLUMN_VALUE1, COLUMN_VALUE2):
            return bz if con.valueEnabled[col -
                                          COLUMN_VALUE1] else Qt.NoItemFlags
        if col == COLUMN_BUTTON:
            return Qt.ItemIsEnabled
        return bz

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int) -> typing.Any:
        if orientation == Qt.Horizontal:
            col = section
            if role == Qt.DisplayRole:
                return '' if col == 0 else TITLE[section]

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> typing.Any:
        col = index.column()
        row = index.row()
        con = self.Condictions[row]
        if role == Qt.DisplayRole:
            return con.getDisplayString(col)
        elif role == Qt.EditRole:
            return con.getEditRole(col)
        elif role == Qt.TextAlignmentRole:
            return con.getAlign(col)
        elif role == Qt.BackgroundRole:
            b = QtGui.QBrush(QtGui.QColor(245, 245, 245))
            if col == COLUMN_VALUE1:
                if not self.Condictions[row].valueEnabled[0]:
                    return b
            if col == COLUMN_VALUE2:
                if not self.Condictions[row].valueEnabled[1]:
                    return b
        return None

    def refreshValueDelegate(self, currentRow: int):
        deleValue1 = self.Condictions[currentRow].delegate(COLUMN_VALUE1)
        self.tableView.setItemDelegateForColumn(COLUMN_VALUE1, deleValue1)
        deleValue2 = self.Condictions[currentRow].delegate(COLUMN_VALUE2)
        self.tableView.setItemDelegateForColumn(COLUMN_VALUE2, deleValue2)

    def valueChanged(self):
        if self.Condictions.checkLast():
            rows = self.Condictions.count()
            self.insertRow(rows)

    def insertRow(self, row):
        self.beginInsertRows(QModelIndex(), row, row)
        con = self.Condictions.append()
        con.setViewColumn(self.viewColumns[0])
        self.endInsertRows()
        index1 = self.createIndex(row, COLUMN_FIELD)
        flag = QtCore.QItemSelectionModel.Select
        self.tableView.selectionModel().setCurrentIndex(index1, flag)
        self.dataChanged.emit(index1, index1, [Qt.DisplayRole])
        return True

    def setData(self, index: QtCore.QModelIndex, Any, role=Qt.EditRole):
        con = self.Condictions[index.row()]
        result = con.setData(index, Any, role)
        col = index.column()
        # 内容变化时，看看要不要增加行
        if result and col in (COLUMN_EXP, COLUMN_VALUE1, COLUMN_VALUE2):
            self.valueChanged()
        return result

    def accept(self):
        index1 = self.createIndex(self.Condictions.count()-1, COLUMN_FIELD)
        flag = QtCore.QItemSelectionModel.Select
        self.tableView.selectionModel().setCurrentIndex(index1, flag)
        row = self.Condictions.count() - 1
        if not self.Condictions.checkLast():
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.Condictions.list[row]
            self.endRemoveRows()
        r = self.Condictions.checkBrackets()
        if not r[0]:
            errMsg = "括号不全！左括号{}个，而右括号为{}个！".format(r[1], r[2])
            QtWidgets.QMessageBox.warning(self.DlgSearch, '提醒', errMsg)
        result = []
        for vc in self.Condictions:
            result.append(vc.getCondition())
        self.CondictionsCreated.emit(' '.join(result))
        self.DlgSearch.close()






# def getModel():

#     db = QtSql.QSqlDatabase.addDatabase("QMYSQL3")
#     db.setHostName('192.168.1.20')
#     db.setPort(3306)
#     db.setDatabaseName('myorder')
#     db.setUserName('jhglb')
#     db.setPassword('1234')
#     db.open()
#     header = ['单据编号', '单价', '客户名称', '金额', '日期']
#     sql = 'select fOrderID,fPrice,c.fCustomerName,o.fAmount,fRequiredDeliveryDate,fSubmited from t_order as o left join t_customer as c on o.fCustomerID=c.fCustomerID'
#     mod = ListModel(QtWidgets.QTableView(),
#                       sql,
#                       pkFieldName='fOrderID',
#                       db=db,
#                       editUI=None)
#     col = mod.viewColumn('fOrderID')
#     col.header = '单据编号'
#     col.width = 150

#     col = mod.viewColumn('fPrice')
#     col.header = '单价'
#     col.formatString = '{:,.2f}'
#     col.align = Qt.AlignVCenter | Qt.AlignRight

#     col = mod.viewColumn('fCustomerName')
#     col.header = '客户名称'
#     col.width = 250

#     col = mod.viewColumn('fAmount')
#     col.header = '金额'
#     col.formatString = '{:,.2f}'
#     col.align = Qt.AlignVCenter | Qt.AlignRight

#     col = mod.viewColumn('fRequiredDeliveryDate')
#     col.header = '日期'
#     col.formatString = 'yyyy-MM-dd'
#     col.align = Qt.AlignCenter

#     col = mod.viewColumn('fSubmited')
#     col.header = '已提交'
#     col.align = Qt.AlignCenter

#     mod.setMainTable('t_order', 'fPK', 'fOrderID')
#     mod.setSubTable('t_order_detail')
#     mod.init()
#     mod.setEnabledMenu(True)
#     return mod


# if __name__ == "__main__":
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     model = _SearchTableModel(getModel())
#     model.DlgSearch.show()

#     sys.exit(app.exec_())
