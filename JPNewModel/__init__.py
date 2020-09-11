
import logging

from functools import partial

from PyQt5 import QtCore, QtSql, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from JPPrint.JPPrintReportNew import JPReport
from JPDatabase.FieldType import JPFieldType, getJPFieldType

from ._delegate import (DateDelegate, FloatDelegate, IntgerDelegate,
                        IntSearchDelegate, IntSelectDelegate, StringDelegate)
from ._icos import _ICO_DICT, _loadIcon
from ._viewColumn import ViewColumn, ViewColumns
from .constants import (JPEditDataMode, JPEditFormModelRole, JPStatisticsMode,
                        SaveDataSqlType,JPButtonEnum)
from ._exportToExcel import JPExportToExcel
from ._search import SearchTableModel


    # # 使用本类，最好在数据库中做如下设定
    # # 主表最好使用InnoDB存储引擎
    # # 数据库中存在systabelautokeyroles的规则表
    # # ##########################################
    # # CREATE TABLE `systabelautokeyroles` (
    # #     `fRoleID` TINYINT(4) NOT NULL AUTO_INCREMENT COMMENT '编号',
    # #     `fRoleName` VARCHAR(50) NOT NULL COMMENT '名称',
    # #     `fTabelName` VARCHAR(50) NOT NULL COMMENT '表名',
    # #     `fFieldName` VARCHAR(50) NOT NULL COMMENT '字段名',
    # #     `fHasDateTime` BIT(1) NOT NULL DEFAULT b'0' COMMENT '有时间',
    # #     `fPreFix` VARCHAR(50) NOT NULL COMMENT '前缀',
    # #     `fCurrentValue` INT(10) UNSIGNED NOT NULL,
    # #     `fLenght` TINYINT(4) NOT NULL DEFAULT '6' COMMENT '长度',
    # #     `fLastKey` VARCHAR(255) NULL DEFAULT NULL COMMENT '最后生成键值',
    # #     `fDateFormat` VARCHAR(50) NULL DEFAULT NULL COMMENT '日期格式',
    # #     `TS` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    # #     PRIMARY KEY (`fRoleID`),
    # #     UNIQUE INDEX `PreFix` (`fPreFix`),
    # #     INDEX `LastKey` (`fLastKey`)
    # # )
    # # COLLATE='utf8_general_ci'
    # # ENGINE=InnoDB
    # # AUTO_INCREMENT=8
    # # ;

    # # ####设定时最好使用管理员用户##############################
    # # MySql自定义函数getNewID(IN roleID INT)
    # # SET GLOBAL log_bin_trust_function_creators = 1;
    # # DELIMITER $$
    # # CREATE FUNCTION getNewID(roleID int)
    # # RETURNS VARCHAR(100)
    # # BEGIN
    # #     UPDATE systabelautokeyroles
    # #     SET    fCurrentValue = fCurrentValue + 1
    # #     WHERE  fRoleID = roleID;

    # #     RETURN
    # #     (SELECT Concat(fPreFix, CASE fHasDateTime
    # #                                 WHEN 1 THEN Date_format(Now(), Replace(Replace(Replace(fDateFormat, 'yyyy', '%Y'), 'mm', '%m'), 'dd', '%d'))
    # #                                 ELSE ''
    # #                             END, Lpad(fCurrentValue, fLenght, 0))
    # #     FROM   systabelautokeyroles
    # #     WHERE  fRoleID = roleID);
    # # END
    # # END $$
    # # DELIMITER ;
    # # SET GLOBAL log_bin_trust_function_creators = 0;
    # # ###########################################
    # # 各主表的 before_Insert触发器
    # # BEGIN
    # #     set NEW.fOrderID=getNewID(1);
    # # END


def _createFilter(fieldName, value) -> str:
    if value is None:
        return '1=0'
    if isinstance(value, str):
        return "{}='{}'".format(fieldName, value)
    elif isinstance(value, int):
        return "{}={}".format(fieldName, value)
    else:
        return ''

class _JPRelationalDelegate(QtSql.QSqlRelationalDelegate):
    def __init__(self, parent: QtWidgets.QWidget,
                 mapper: QtWidgets.QDataWidgetMapper):
        '''自定义有外键的单表编辑代理\n
        调用方法：\n
        Mapper.setItemDelegate(parent:窗体,mapper:QDataWidgetMapper)\n
        参数：\n
        parent为编辑窗体,mapper中存放窗体的数据model，所以必须传递
        '''
        self.mapper = mapper
        super().__init__(parent=parent)

    def setEditorData(self, editor: QtWidgets.QWidget,
                      index: QtCore.QModelIndex):
        '''当编辑窗口的基础model的当前行变化时，设置控件值'''
        if isinstance(editor, QtWidgets.QComboBox):
            if not index.data():
                return editor.setCurrentIndex(-1)
            else:
                model = editor.model()
                for i in range(model.rowCount()):
                    if index.data() == model.data(model.createIndex(i, 0),
                                                  Qt.EditRole):
                        return editor.setCurrentIndex(i)
        elif isinstance(editor, QtWidgets.QLineEdit):
            value = index.data()
            vc = index.model()._widgetsInformation[editor.objectName()]
            editor.setText(vc.displayString(value))
        else:
            return super().setEditorData(editor, index)

    def setModelData(self, editor: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        '''保存前更新基础model的数据'''
        mapperModel = self.mapper.model()
        mapperIndex = mapperModel.createIndex(self.mapper.currentIndex(),
                                              index.column())

        if isinstance(editor, QtWidgets.QComboBox):
            lst = editor.model().viewColumn.rowSource
            if not lst:
                return logging.getLogger().warning("[{}]对象没有设置行数据来源！".format(
                    editor.objectName()))
            modelColumn = editor.model().viewColumn.modelColumn
            data = lst[editor.currentIndex()][modelColumn]
            mapperModel.setData(mapperIndex, data)
        elif isinstance(editor, QtWidgets.QLineEdit):
            fieldtype = editor.viewColumn.jpFieldType
            if fieldtype == JPFieldType.Int:
                data = None
                txt = editor.text()
                if txt:
                    data = int(txt.replace(",", ''))
                mapperModel.setData(mapperIndex, data)
            elif fieldtype == JPFieldType.Float:
                data = None
                txt = editor.text()
                if txt:
                    data = float(txt.replace(",", ''))
                mapperModel.setData(mapperIndex, data)
            else:
                mapperModel.setData(mapperIndex, editor.text())
        else:
            super().setModelData(editor, model, index)
        #mapperModel.dataChanged.emit(mapperIndex, mapperIndex)


class _JPComboBoxModel(QtCore.QAbstractTableModel):
    def __init__(self, parent, viewColumn: ViewColumn):
        '''返回一个用于主表编辑关系数据QComboBox对象的数据模型。\n
        注意由于model从数据库中读取数据时会将Null自动转换成0值，
        所以此功能要求modelColumn列的有效值中不包含0，如果有0值，
        会自动将combobox设置成未选中任何行的状态'''
        # 具体实现请参见_JPRelationalDelegate类setEditorData()方法
        self.viewColumn = viewColumn
        super().__init__(parent=parent)

    def rowCount(self,
                 parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self.viewColumn.rowSource)

    def columnCount(self,
                    parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 2

    def data(self, QModelIndex, role=Qt.DisplayRole):
        r = QModelIndex.row()
        vc = self.viewColumn
        if role == Qt.DisplayRole:
            return vc.rowSource[r][vc.displayColumn]
        elif role == Qt.EditRole:
            return vc.rowSource[r][vc.modelColumn]
        else:
            return QtCore.QVariant()





class JPMainTableModel(QtSql.QSqlRelationalTableModel):
    # _tp中存放需要添加到数据映射器中的控件类型
    # 要添加的控件，必须用字段名命名(大小写敏感)
    _tp = (QtWidgets.QLineEdit, QtWidgets.QDateEdit, QtWidgets.QTextEdit,
           QtWidgets.QCheckBox, QtWidgets.QSpinBox, QtWidgets.QComboBox)

    # 数据变化信号，用字段名发出
    dataChangedByName = QtCore.pyqtSignal(str, QtCore.QVariant)
    # 记录添加或修改信号
    recordInserted = QtCore.pyqtSignal(str, str)
    recordChanged = QtCore.pyqtSignal(str, str)
    statisticsValueChange = QtCore.pyqtSignal(str, JPStatisticsMode,
                                              QtCore.QVariant)
    editFormButtonClicked = QtCore.pyqtSignal(str)
    mainRecordSaved = QtCore.pyqtSignal(JPEditDataMode, QtCore.QVariant)

    def __init__(self,
                 editUi: object,
                 windowsFlags: Qt.WindowFlags = Qt.WindowFlags(),
                 db=QtSql.QSqlDatabase()):
        '''用于窗体模式进行数据编辑时的主窗体数据模型。\n
        会自动增加数据映射器，但是外键字段要使用addComboBoxData方法增加列表文字。
        最后要调用tofirst()方法定位编辑的记录。\n
        注：数据映射器不能增删记录，只能编辑
        '''
        dialog = QtWidgets.QDialog(flags=windowsFlags)
        super().__init__(parent=dialog, db=db)

        # 初始化UI
        self.Dialog = dialog
        self._ui = editUi()
        self._ui.setupUi(self.Dialog)

        self._mainTableName: str = ''
        self._mainLinkField: str = ''
        self._mainPkFieldName: str = ''

        self._editDataMode = None

        self._db = db
        self._widgetsInformation = ViewColumns(db)
        # 保存新记录或当前记录连接子表字段的值
        self._LAST_ID = None
        self._RequiredControl = []

        # 决定一些动作参数
        self.autoCloseDialog = True
        self.popMessageBox = True

    def setMainTable(self,
                     tableName: str,
                     pkFieldName: str,
                     linkFieldName: str = None):
        self._mainTableName = tableName
        self._mainPkFieldName = pkFieldName
        self._mainLinkField = linkFieldName if linkFieldName else pkFieldName

    def _createMapper(self):
        # 建立映射模式
        # 一定要提前设定表名，要不后面添加映射会出错
        self.mapper = QtWidgets.QDataWidgetMapper(self.Dialog)
        # 此行主要是解决下拉列表框的问题
        self.mapper.setItemDelegate(
            _JPRelationalDelegate(self.Dialog, self.mapper))
        # 提交策略
        # QDataWidgetMapper.AutoSubmit只是自动提交到model并不向数据库提交
        # QDataWidgetMapper.ManualSubmit则是在手动执行submit()时同时向模型再向数据库提交
        self.mapper.setSubmitPolicy(QtWidgets.QDataWidgetMapper.AutoSubmit)

    def _addMapper(self):
        self._hasComboBox = False
        if self.tableName() is None:
            raise RuntimeError('addMapper之前必须设置表名！')
        rec = self.record()
        for i in range(rec.count()):
            fieldName = rec.fieldName(i)
            widget = self.Dialog.findChild(self._tp, fieldName)
            if widget is not None:
                #self._connectChangeSingal(widget)
                self.mapper.addMapping(widget, i)
                if isinstance(widget, QtWidgets.QComboBox):
                    vc = self._widgetsInformation[widget.objectName()]
                    model = _JPComboBoxModel(self.Dialog, vc)
                    widget.setModel(model)
                    self._hasComboBox = True
                else:
                    widget.viewColumn = self._widgetsInformation[
                        widget.objectName()]
        self._widgetsInformation.setModel(self)

    def getDefaultButtonObjectName(self, buttonEnum: JPButtonEnum) -> str:
        '''设置窗体中按钮的名称'''
        return ''

    def getReportEvent(self):
        '''返回用户定义的一个报表类'''
        return JPReport

    def _addbuttonCilcked(self):
        # 添加按钮信号
        def clickEmit(name: str):
            self.editFormButtonClicked.emit(name)

        def addOneButtom(buttonEnum: JPButtonEnum, dic: dict):
            name = self.getDefaultButtonObjectName(buttonEnum)
            if name:
                obj = self.Dialog.findChild(QtWidgets.QPushButton, name)
                if obj:
                    dic[buttonEnum] = obj

        E = JPButtonEnum
        butDic = {}
        for e in [E.Save, E.Cancel, E.Delete, E.PDF, E.Print]:
            addOneButtom(e, butDic)
        # 设置用户指定的保存按钮的动作
        if E.Save in butDic:
            butDic[E.Save].clicked.connect(self.saveData)
        # 设置用户指定的取消按钮的动作
        if E.Cancel in butDic:
            butDic[E.Cancel].clicked.connect(self._cancelClick)
        # 设置用户指定的按钮的动作
        if E.Print in butDic:
            butDic[E.Print].clicked.connect(self.PrintReport)
        exp = QtCore.QRegExp(r'.*')
        # 窗体中所有按钮对象的集合
        buts = self.Dialog.findChildren(QtWidgets.QPushButton, exp)
        # 所有内置按钮名字的集合
        objNames = [v.objectName() for v in butDic.values()]
        for but in buts:
            if self._editDataMode == JPEditDataMode.readOnlyMode:
                # 只读状态禁止按钮，打印按钮始终显示
                if but.objectName()!=butDic[E.Print].objectName():
                    but.setDisabled(True)
            else:
                tn = but.objectName()
                if tn not in objNames:
                    but.clicked.connect(partial(clickEmit, tn))


    def getFieldsInfomationEvent(self, weidgetInfos: ViewColumns,
                                 EditFormModelRole: JPEditFormModelRole):
        if self._hasComboBox:
            raise RuntimeError('窗体中存在ComboBox部件，必须重写before方法')

    def init(self, editmode: JPEditDataMode, filterValue: str = ""):
        # 下面各行顺序不能修改，否则映射可能无效
        self._filterValue = filterValue
        tn = self._mainTableName
        pn = self._mainPkFieldName
        ln = self._mainLinkField
        filter = _createFilter(self._mainLinkField, self._filterValue)
        self.setTable(tn)
        fieldNotExistStr = "字段[{}]在表[{}]中不存在！"
        errstr = ''
        # 检查字段是否存在
        if self.record().indexOf(pn) == -1:
            errstr = fieldNotExistStr.format(pn, tn)
        elif self.record().indexOf(ln) == -1:
            errstr = fieldNotExistStr.format(ln, tn)
        # 查找表的自动增加主键信息，没有则报错
        elif not self.record().field(pn).isAutoValue():
            errstr = "字段[{}]必须是一个自动增加字段,"
            errstr = errstr + "可以另有一个字段用于和子表连接"
            errstr = errstr.format(pn)
        if errstr:
            raise Exception(errstr)
        # 取得列信息（用户修改)
        self._widgetsInformation._setDefaultColumn(self, self._db,
                                                   self.record())
        self.getFieldsInfomationEvent(self._widgetsInformation,
                                      JPEditFormModelRole.mainModel)
        self.setFilter(filter)
        self.select()
        self._createMapper()
        self.mapper.setModel(self)
        self._addMapper()
        self._editDataMode = editmode
        self._addbuttonCilcked()
        if self._editDataMode == JPEditDataMode.newMode:
            self.insertRow(0)
        self._setWidgetsState()
        self.mapper.toFirst()

    def setData(self, index: QtCore.QModelIndex, Any, role=Qt.EditRole):
        # 当修改数据时，发出数据修改信号
        result = super().setData(index, Any, role=role)
        if role == Qt.EditRole and result:
            rec = self.record(0)
            col = index.column()
            nm = rec.fieldName(col)
            self.dataChanged.emit(index, index, [role])
            self.dataChangedByName.emit(nm, rec)
            self.calculateMainRecord(rec, nm)
        return result

    def calculateMainRecord(self, record: QtSql.QSqlRecord, fieldName: str):
        '''用于计算主表的计算字段'''

        lst = [r for r in self._widgetsInformation if r.fieldIndex == -1]
        s = ('存在计算列，但没有实现calculateSubViewCell函数。' '该函数给定当前行数据及列名，应该返回计算列的值')
        if lst:
            raise UserWarning(s)
        return

    def setWidgetState(self, widgetName: str, widget: QtWidgets.QWidget,
                       editMode: JPEditDataMode):
        '''用户可重写此方法设置每一个控件的状态'''
        return

    def _setWidgetsState(self):
        # 检查字段的必输状态
        exp = QtCore.QRegExp(r'.*')
        labs = self.Dialog.findChildren(QtWidgets.QLabel, exp)
        objs = [(r, r.buddy()) for r in labs if not r.buddy() is None]
        rec = self.record()
        requiredFromat = '<font color=red>*{}</font>'
        for lab, obj in objs:
            field = rec.field(obj.objectName())
            if field.requiredStatus() == QtSql.QSqlField.Required:
                obj._oldText = lab.text()
                self._RequiredControl.append(obj)
                lab.setText(requiredFromat.format(lab.text()))
        Widgets = []
        # 查找所有控件
        tp = [t for t in self._tp] + [QtWidgets.QComboBox]
        for cls in tp:
            objs = self.Dialog.findChildren(cls, exp)
            Widgets += objs
        # 设置主键字段控件的状态
        for obj in Widgets:
            nm = obj.objectName()
            if self._editDataMode == JPEditDataMode.readOnlyMode:
                obj.setEnabled(False)
            if nm == self._mainPkFieldName or nm == self._mainLinkField:
                obj.setEnabled(False)

        # 开放由用户设置字段控件的状态
        for obj in Widgets:
            self.setWidgetState(obj.objectName(), obj, self._editDataMode)

    def _checkRequiredValue(self) -> bool:
        # 检查字段的必输值
        for obj in self._RequiredControl:
            fn = obj.objectName()
            if self.record(0).field(fn).isNull():
                result = False
                errMsg = "字段'{}'必须输入有效值！".format(obj._oldText)
                QtWidgets.QMessageBox.warning(self.Dialog, '提醒', errMsg)
                return False
        return True

    def getLinkFieldValue(self) -> str:
        '''返回连接子表字段的值'''
        if self._LAST_ID:
            return self._LAST_ID
        raise RuntimeError('查找PK值失败!')

    def submitAll(self):
        result = self.mapper.submit()
        if result:
            self._LAST_ID = None
            fn = self._mainLinkField if self._mainLinkField else self._mainPkFieldName
            fn_i = self.fieldIndex(fn)
            if self._editDataMode == JPEditDataMode.editMode:
                index = self.createIndex(0, fn_i)
                self._LAST_ID = self.data(index, Qt.EditRole)
            if self._editDataMode == JPEditDataMode.newMode:
                sql = 'select {linkField} from {tableName} where {pkField}=LAST_INSERT_ID()'
                sql = sql.format(linkField=fn,
                                 tableName=self.tableName(),
                                 pkField=self._mainPkFieldName)
                q = QtSql.QSqlQuery(self._db)
                q.exec(sql)
                if not q.size() == 1:
                    raise RuntimeError('取得生成新ID错误！')
                if q.first():
                    self._LAST_ID = q.value(fn)
        return result

    def saveDateSQL(self, type: SaveDataSqlType) -> list:
        return []

    def _cancelClick(self):
        self.Dialog.close()

    def PrintReport(self):
        if self._filterValue:
            P = self.getReportEvent()(self._db)
            p.DataSource = "select * from {} where {}".format(
                self._mainTableName,
                _createFilter(self._mainLinkField, self._filterValue))
            P.BeginPrint()

    def saveData(self):
        if self._checkRequiredValue() is False:
            return
        if self._editDataMode == JPEditDataMode.readOnlyMode:
            return
        rollback = False
        errStr = ''
        try:
            self._db.transaction()
        except Exception as e:
            rollback = True
            errStr = "开始事务失败！"
        else:
            try:
                for sql in self.saveDateSQL(
                        SaveDataSqlType.beforeSaveMainFormData):
                    self._db.exec(sql)
                if not self.submitAll():
                    rollback = True
                    raise RuntimeError("主表提交数据失败！")
                for sql in self.saveDateSQL(
                        SaveDataSqlType.afterSaveMainFormData):
                    self._db.exec(sql)
            except Exception as e:
                rollback = True
                errStr = str(e) + ";" + self._db.lastError().text()
        finally:
            if rollback:
                txt = ''
                if not self._db.rollback():
                    txt = '数据保存失败，回滚数据失败！数据库错误信息：\n{}'
                else:
                    txt = '数据保存失败，数据库错误信息：\n{}\n数据已经成功回滚！'
                if self.popMessageBox:
                    txt = txt.format(errStr)
                    QtWidgets.QMessageBox.warning(self.Dialog, '消息', txt)
                return
            else:
                self._db.commit()
                if self.popMessageBox:
                    QtWidgets.QMessageBox.information(self.Dialog, '消息',
                                                      "数据保存成功！")
                if self.autoCloseDialog:
                    self.Dialog.done(1)
                m = self._editDataMode
                if m == JPEditDataMode.editMode:
                    self.mainRecordSaved.emit(m, self._filterValue)
                elif m == JPEditDataMode.newMode:
                    self.mainRecordSaved.emit(m, self._LAST_ID)
                return True


class JPSubTableModel(QtCore.QAbstractTableModel):
    # 统计信息信号，只有添加了统计列才会发送此信号
    # 信号的三个参数分别为：统计字段名、统计类型、统计值
    #statisticsValueChange = QtCore.pyqtSignal(str, int, float)

    def __init__(self,
                 dialog: QtWidgets.QWidget,
                 tableName: str,
                 tableView: QtWidgets.QTableView,
                 linkFieldName: str = '',
                 db=QtSql.QSqlDatabase()):
        '''用于使用tableView显示一个表中的数据，也可以作为主子表情况下子表数据模型。\n
        可以设置统计列数据（statisticsValueChange信号会传递相关结果）;
        也可能加一些计算列（addViewColumn方法增加列时，省略fieldIndex参数会被认为只计算列）
        '''
        super().__init__(parent=dialog)
        self.db = db
        self._tableView = tableView
        self._tableView.setEditTriggers(
            QtWidgets.QAbstractItemView.AllEditTriggers)
        self._tableView.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        self._tableName = tableName

        # 存放tableView中要显示的列的信息
        self._viewColumns = ViewColumns(db)
        self.mainModel: JPMainTableModel = None
        # 存放用户增加的统计列的信息
        self._linkFieldName = linkFieldName
        self._model = QtSql.QSqlTableModel(parent=dialog, db=db)
        self._model.setEditStrategy(QtSql.QSqlTableModel.OnManualSubmit)
        # self._setPrimaryKeyInfomation()
        # 是否已经设置过只读列
        self._readOnlyDelegateSeted = False
        # 记录当前有效行和已经移除和行
        self.buttonEnabled = False
        self._mainfilter: str = ''

        #self._ico_deleted = _loadIcon(_ICO_DICT['ico_deleted'])
        self._ico_act_del = _loadIcon(_ICO_DICT['ico_act_del'])
        self._ico_act_new = _loadIcon(_ICO_DICT['ico_act_new'])

    def init(self,
             editmode: JPEditDataMode = JPEditDataMode.readOnlyMode,
             filterValue: str = '',
             sorter: str = ''):

        self.editDataMode = editmode
        pn = self._linkFieldName
        self._model.setTable(self._tableName)

        # 检查字段是否存在
        if self._model.record().indexOf(pn) == -1:
            raise Exception("字段[{}]在表[{}]中不存在！".format(pn, tn))
        # 设置过滤条件
        filter = _createFilter(pn, filterValue)
        self._model.setFilter(filter)
        sorti=self._model.fieldIndex(sorter)
        if sorter:
            self._model.setSort(sorti, Qt.AscendingOrder)
        self._model.select()
        # 防止只加载256行数据
        while self._model.canFetchMore():
            self._model.fetchMore()
        # self._effectiveRows = [i for i in range(self._model.rowCount())]
        # self._deletedRows = []

        # 滚动到最后
        self._tableView.scrollToBottom()

        # 设置列的编辑代理
        rec = self._model.record()
        self._viewColumns.setModel(self._model)
        # 更新统计信息,发送统计信号
        self._calculateAllstatisticsColumn()
        for i, c in enumerate(self._viewColumns):
            de = self._getDelegate(i, rec.field(c.fieldIndex))
            if de:
                self._tableView.setItemDelegateForColumn(i, de)

        # 拦截窗体的关闭事件，检查一下有没有未保存数据
        self._tableView.parent().closeEvent = self._beforeParentWidgetClose

    def columnCount(self, parent=QtCore.QModelIndex()):
        r = len(self._viewColumns)
        if self.buttonEnabled is False:
            return r
        if self._editDataMode == JPEditDataMode.readOnlyMode:
            return r
        else:
            return r + 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        return self._model.rowCount()

    def flags(self, index: QtCore.QModelIndex):
        row = index.row()
        col = index.column()
        # 重新生成一个index
        viewIndex = self._model.createIndex(row, col)
        if self._editDataMode == JPEditDataMode.readOnlyMode:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if self._viewColumns[index.column()].fieldIndex == -1:
            return Qt.ItemIsEnabled
        else:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled

    def _dataEditRole(self, index):
        r = index.row()
        c = index.column()
        # 防止读取大于设定列的数据
        colinfo = self._viewColumns[c]
        y = colinfo.fieldIndex
        if y != -1:
            return self._model.data(self.createIndex(r, y), role=Qt.EditRole)
        else:
            v = None
            try:
                v = self.mainModel.calculateSubViewCell(
                    self._model.record(r), colinfo.fieldName)
            except Exception:
                s = "第{}行[{}]计算错误".format(r, colinfo.header)
                logging.getLogger().warning(s)
                v = None
            return v

    def data(self, index: QtCore.QModelIndex, role=Qt.DisplayRole):
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole:
            return self._dataDisplayRole(index)
        elif role == Qt.EditRole:
            return self._dataEditRole(index)
        elif role == Qt.TextAlignmentRole:
            return self._viewColumns[col].align
        else:
            return self._model.data(index, role=role)

    def setData(self, index: QtCore.QModelIndex, Any, role=Qt.EditRole):
        row = index.row()
        col = index.column()
        # 重新生成一个index
        cols = len(self._viewColumns)
        if role == Qt.EditRole:
            colinfo = self._viewColumns[col]
            y = colinfo.fieldIndex
            # 如果是一个计算列，直接返回
            if y == -1:
                return False
            modelIndex = self._model.createIndex(index.row(), y)
            self._model.setData(modelIndex, Any, role=role)
            # 统计并发射统计信号
            self._StatisticsAndEmit(colinfo)
            # 如果有计算列，还要发送计算列的统计信号
            for vc in self._viewColumns:
                if vc._statisticses:
                    self._StatisticsAndEmit(vc)
            self.dataChanged.emit(index, index)
            return True
        return False

    def getViewColumn(self, index: QtCore.QModelIndex) -> ViewColumn:
        '''返回视图中指定列信息对象'''
        return self._viewColumns[index.column()]

    def getViewField(self, index: QtCore.QModelIndex) -> QtSql.QSqlField:
        '''返回视图中指定列对应底层QSqlField信息对象'''
        y = self._viewColumns[index.column()].fieldIndex
        if y != -1:
            return self._model.record().field(y)

    @property
    def editDataMode(self):
        '''设置模型的数据状态，可选:\n
        JPEditDataMode.readOnlyMode\n
        JPEditDataMode.editMode\n
        JPEditDataMode.newMode\n
        '''
        return self._editDataMode

    @editDataMode.setter
    def editDataMode(self, mode: JPEditDataMode):
        self._editDataMode = mode
        tv = self._tableView
        #  只读状态时，设置view的选择状态
        if self._editDataMode == JPEditDataMode.readOnlyMode:
            en = QtWidgets.QAbstractItemView
            tv.setEditTriggers(en.NoEditTriggers)
            tv.setSelectionBehavior(en.SelectRows)
            tv.setSelectionMode(en.SingleSelection)
            tv.setContextMenuPolicy(Qt.NoContextMenu)
        else:
            # 设置右键菜单
            tv.setContextMenuPolicy(Qt.CustomContextMenu)  # 允许右键产生子菜单
            tv.customContextMenuRequested.connect(
                self._setTableViewMenu)  # 右键菜单

    def _setTableViewMenu(self, pos):
        # if self.editDataMode == JPEditDataMode.readOnlyMode:
        #     return
        # 弹出的位置要减去标题行的高度
        tv = self._tableView
        newPos = tv.mapToGlobal(pos)
        hh = tv.verticalHeader().defaultSectionSize()
        newPos.setY(newPos.y() + hh)
        # 取得鼠标点所在行号
        currentRow = tv.rowAt(pos.y())

        menu = QtWidgets.QMenu()
        item1 = menu.addAction(self._ico_act_new, u"增加行")
        # 如果当前坐标为一个有效行，添加删除菜单
        menu.addSeparator()
        item2 = menu.addAction(self._ico_act_del, u"删除行")
        item2.setEnabled((currentRow > -1)
                         and currentRow not in self._deletedRows)

        # 显示菜单
        action = menu.exec_(newPos)
        if action == item1:
            if self.appendRow():
                self._tableView.setCurrentIndex(
                    self.createIndex(self.rowCount() - 1, 0))
        elif action == item2:
            self.removeRow(currentRow)

            self._tableView.setCurrentIndex(
                self.createIndex(self._findToRow(currentRow), 0))

    def _findToRow(self, row: int):
        # 删除后定位到的行号
        for i in range(row, -1, -1):
            if i not in self._deletedRows:
                return i
        for i in range(row, self.rowCount()):
            if i not in self._deletedRows:
                return i

    def _beforeParentWidgetClose(self, event):
        t_str = "窗体中存在未保存的数据，确认是否继续关闭窗口"
        if self._model.isDirty():
            if QtWidgets.QMessageBox.question(
                    self._tableView.parent(), "确认",
                    t_str) == QtWidgets.QMessageBox.No:
                event.ignore()
            else:
                event.accept()
        else:
            event.accept()

    def _getDelegate(self, columnIndex: int,
                     field: QtSql.QSqlField):
        '''返回每一列的代理，可重写'''
        obj = self._viewColumns[columnIndex]
        tv = self._tableView
        JT = JPFieldType
        if obj.fieldIndex == -1:
            # 调用时判断返回值，如果是计算列，歹能返回任何值
            return 
        if obj.treeSource:
            return IntSearchDelegate(tv, 0)
        if obj.rowSource:
            return IntSelectDelegate(tv)
        jpFieldType = getJPFieldType(self.db, field.typeID())
        if jpFieldType == JT.Int:
            return IntgerDelegate(tv, obj.prefix, obj.suffix)
        elif jpFieldType == JT.Float:
            return FloatDelegate(tv, obj.prefix, obj.suffix)
        elif jpFieldType == JT.Date:
            return DateDelegate(tv)
        else:
            return StringDelegate(tv)

    def submit(self):
        return self._model.submit()

    def submitAll(self):
        return self._model.submitAll()

    def _dataDisplayRole(self, index: QtCore.QModelIndex):
        vcs = self._viewColumns
        r, c = index.row(), index.column()
        fieldIndex = vcs._fieldIndexList[c]
        value = None
        if fieldIndex == -1:
            try:
                fieldName = vcs._fieldNameList[c]
                rec = self._model.record(index.row())
                value = self.mainModel.calculateSubViewCell(rec, fieldName)
            except Exception as e:
                header = vcs._headerList[c]
                s = "第{}行[{}]计算错误:{}".format(r, header, str(e))
                logging.getLogger().warning(s)
        else:
            newIndex = self.createIndex(r, fieldIndex)
            value = self._model.data(newIndex, Qt.EditRole)
        return self._viewColumns[c].displayString(value)

    def connectNotify(self, signal):
        # 当统计信号被绑定到一个函数时，如果模型中存在数据
        # 则计算一次统计信息并发送一次统计信号(初始化用户界面中引用的统计值)
        if (QtCore.QMetaMethod(signal).name() == b'statisticsValueChange'
                and self.rowCount() > 0):
            self._calculateAllstatisticsColumn()
        return self._model.connectNotify(signal)

    def _calculateAllstatisticsColumn(self):
        # 计算全部统计信息并发送信号
        vcs = [vc for vc in self._viewColumns if vc._statisticses]
        for vc in vcs:
            self._StatisticsAndEmit(vc)
        # for r in self._StatisticsColumns:
        #     self._StatisticsAndEmit(r.fieldIndex)

    def _StatisticsAndEmit(self, viewColumn: ViewColumn):
        # 任何时候程序调用了setData/removeRow方法后，内部计算统计信息并发射统计信号
        vc = viewColumn
        data = []
        rows = self._model.rowCount()
        funRec = self._model.record
        #取得一个用于计算统计值的数据列表
        if vc.fieldIndex == -1:
            cacu = self.mainModel.calculateSubViewCell
            data = [cacu(funRec(i), vc.fieldName) for i in range(rows)]
        else:
            data = [funRec(i).value(vc.fieldIndex) for i in range(rows)]
        # 防止None值影响计算
        data = [0.0 if r is None else r for r in data]
        # 计算每一个统计值并发送信号
        for tj in vc._statisticses:
            try:
                result = tj.func(data)
            except Exception as e:
                errMsg = '计算列[{}]的[{}]统计值时出现错误,错误信息为：\n{}'
                errMsg = errMsg.format(vc.header, tj.statisticsMode, str(e))
                QtWidgets.QMessageBox.critical(self.mainModel.Dialog, '出错',
                                               errMsg)
                return
            else:
                v = result if result else None
                self.mainModel.statisticsValueChange.emit(
                    vc.fieldName, tj.statisticsMode, v)

    def headerData(self, col: int, QtOrientation, role=Qt.DisplayRole):
        # 横标题和纵标题的设置
        if QtOrientation == Qt.Horizontal:
            fn = self._viewColumns[col].fieldName
            field = self._model.record().field(fn)
            required = (field.requiredStatus() == QtSql.QSqlField.Required)
            if col == len(self._viewColumns):
                return QtCore.QVariant()
            if role == Qt.DisplayRole:
                t = "*" if required else ''
                return t + self._viewColumns[col].header
            if role == Qt.TextColorRole:
                if required:
                    return QColor('red')
                else:
                    return QColor('black')
        if QtOrientation == Qt.Vertical:
            # 设置新增行纵标题为*时加上行号
            p_header = self._model.headerData(col, QtOrientation, role=role)
            if p_header == '*':
                return str(col + 1) + '*'
            return p_header

    def appendRow(self):
        '''在末尾增加一行，增加前调用checkDataBeforeInsertRowToSubTable函数检查尾行合法性'''
        # 检查尾行合法性
        checkOK = False
        if self._model.rowCount() == 0:
            checkOK = True
        else:
            row = self.rowCount() - 1
            if self.mainModel.checkDataBeforeInsertRowToSubTable(
                    self._model.record(row)):
                checkOK = True
        if not checkOK:
            QtWidgets.QMessageBox.warning(self.mainModel.Dialog, '警告',
                                          '尾行检查不合规，增加行失败！')
            return False
        # 增加行
        pos = self._model.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), pos, pos)
        result = self._model.insertRow(pos)
        self.endInsertRows()
        self._calculateAllstatisticsColumn()
        return result

    def removeRow(self,
                  position: int,
                  parent: QtCore.QModelIndex = QtCore.QModelIndex()):
        # 有beginRemoveRows和endRemoveRows会在view中删除一行
        self.beginResetModel()
        self._model.beginRemoveRows(parent, position, position)
        self._model.removeRow(position)
        self._calculateAllstatisticsColumn()
        self._model.endRemoveRows()
        self.endResetModel()

        return True

    def _beforeInsertToBaseSubTable(self, record: QtSql.QSqlRecord):
        '''增加一行之前给子表的主表键值列赋值'''
        # 此方法会在底层给数据库中表增加行之前被自动调用
        if self.editDataMode == JPEditDataMode.editMode:
            kn, kv = self._model.filter().split("=")
            kv = kv.replace("'", '')
            # 判断主表主键的类型,并给新增加的行赋值
            tp = getJPFieldType(self.db, record.field(kn).typeID())
            newKV = None
            if tp == JPFieldType.Int:
                kv = int(kv)
            record.setValue(kn, kv)
            record.setGenerated(kn, True)


    def _checkRequiredValue(self) -> bool:
        # 检查字段的必输值
        viewFieldsIndexes = [
            r.fieldIndex for r in self._viewColumns if r.fieldIndex != -1
        ]
        for i in range(self._model.rowCount()):
            rec = self._model.record(i)
            for c in range(rec.count()):
                if c in viewFieldsIndexes:
                    tempViewColumn = [
                        r.header for r in self._viewColumns
                        if r.fieldIndex == c
                    ]
                    field = rec.field(c)
                    if field.requiredStatus(
                    ) == QtSql.QSqlField.Required and field.isNull():
                        errMsg = "第[{}]行[{}]'列的值不能为空"
                        errMsg = errMsg.format(i + 1, tempViewColumn[0])
                        QtWidgets.QMessageBox.warning(self.mainModel.Dialog,
                                                      '警告', errMsg)
                        return False
        return True


class JPMainSubTableModel(JPMainTableModel):
    def __init__(self,
                 editUi: object,
                 tableViewName: str = 'tableView',
                 windowsFlags: Qt.WindowFlags = Qt.WindowFlags(),
                 db=QtSql.QSqlDatabase()):
        '''主子表编辑模型'''
        super().__init__(editUi, windowsFlags, db)
        self._subTableName: str = ''
        self._subLinkField: str = ''
        self._subSorter: str = ''
        self._db = db
        self._subModel: JPSubTableModel = None
        self._tableView = self._findTableView(tableViewName)

    def _findTableView(self, tableViewName) -> QtWidgets.QTableView:
        '''查找 tableView 对象'''
        obj = self.Dialog.findChild(QtWidgets.QTableView, tableViewName)
        if obj:
            return obj
        raise RuntimeError("{}中必须有名为{}的QtableView对象！".format(self._ui, n))

    def setSubTable(self, tableName: str, linkFieldName: str = None,
                    sorter=''):
        if not self._mainTableName:
            raise RuntimeError("必须先执行setMainTable()方法设定主表信息！")
        self._subTableName = tableName
        self._subLinkField = linkFieldName if linkFieldName else self._mainLinkField
        self._subSorter = sorter

    @property
    def subModel(self) -> JPSubTableModel:
        if self._subModel:
            return self._subModel
        raise RuntimeError("subModel()方法获取子表模型前必须先执行init()方法")

    def onGetSubModel(self):
        '''重写该方法指定一个重写的用于编辑窗体的子表模型，
        返回值必须是JPSubTableModel类的子类\n
        子类中可以重写相关的方法以改变类的功能,重写部分。   
        '''
        return JPSubTableModel

    def getFieldsInfomationEvent(self, columnsInfInSubFormat: ViewColumns,
                                 EditFormModelRole: JPEditFormModelRole):
        '''必须重写此函数，添加列信息等'''
        raise RuntimeError('必须重写此函数，添加列信息等!')

    def init(self,
             editmode: JPEditDataMode = JPEditDataMode.newMode,
             filterValue: str = ""):
        # 初始化主表模型
        super().init(editmode, filterValue)

        self._editDataMode: JPEditDataMode = editmode
        self._filterValue = filterValue
        self._subModel = self.onGetSubModel()(self.Dialog,
                                              self._subTableName,
                                              self._tableView,
                                              linkFieldName=self._subLinkField,
                                              db=self._db)

        # 转移_subModel方法到此类
        self._subModel.mainModel = self
        self._subModel._model.beforeInsert.connect(
            self._beforeInsertToBaseSubTable)
        # self._subModel.calculateSubViewCell = self.calculateSubViewCell
        # self._subModel.checkDataBeforeInsertRowToSubTable = self.checkDataBeforeInsertRowToSubTable

        # 由用户增加列信息等
        self._subModel._viewColumns = ViewColumns(self._db)

        self.getFieldsInfomationEvent(self._subModel._viewColumns,
                                      JPEditFormModelRole.subModel)
        self._subModel.init(self._editDataMode, self._filterValue,
                            self._subSorter)

        if self._editDataMode == JPEditDataMode.newMode:
            self._subModel.appendRow()
        self._tableView.setModel(self._subModel)
        for i, vc in enumerate(self._subModel._viewColumns):
            self._tableView.setColumnWidth(i, vc.width)
        # 当主表当前行变化时，引发子表设置过滤条件
        self.mapper.currentIndexChanged.connect(
            self._mainMapperCurrentIndexChanged)

    def calculateSubViewCell(self, record: QtSql.QSqlRecord, fieldName: str):
        '''如果有计算列，此函数要被覆盖，此函数应返回计算列的值\n
        参数：index要计算的值位于tableView中的位置用于判断\n
        record代表当前行所有列的数据，可使用record.field(fieldName).value()取任意字段值进行计算
        返回值时注意小数位复合业务要求
        '''
        lst = [r for r in self._subModel._viewColumns if r.fieldIndex == -1]
        s = ('子View存在计算列，但没有实现calculateSubViewCell函数。'
             '该函数给定当前行数据及列名，应该返回计算列的值')
        if lst:
            raise UserWarning(s)

    def PrintReport(self):
        if self._filterValue:
            P = self.getReportEvent()(db=self._db)
            filter = _createFilter(self._mainLinkField, self._filterValue)
            sql = "select a.*,b.* from {mn} as a left join {sn} as b on a.{ml}=b.{sl}  where a.{mf}"
            P.DataSource = sql.format(mn=self._mainTableName,
                                      sn=self._subTableName,
                                      ml=self._mainLinkField,
                                      sl=self._subLinkField,
                                      mf=filter)

            P.beginPrint()

    def checkDataBeforeInsertRowToSubTable(self, lastRecord: QtSql.QSqlRecord):
        if self._editDataMode == JPEditDataMode.readOnlyMode:
            return False
        '''子表增加新行前检查最后一行数据的有效性'''
        s = ('没有重写增加新行前的检查函数,lastRecord参数为最后一行的数据用于判断本函数,返回值为True时增加行')
        raise UserWarning(s)

    def _beforeInsertToBaseSubTable(self, record: QtSql.QSqlRecord):
        # 给数据库增加记录前，修改子表连接字段的值
        msg = ("程序尝试给自增字'{}'段赋值，请检查setSubTable()方法是不是没有设置子表连接字段!")
        kn = self._subLinkField
        kv = self.getLinkFieldValue()
        if record.field(kn).isAutoValue():
            raise RuntimeError(msg.format(kn))
        record.setValue(kn, kv)
        record.setGenerated(kn, True)

    def _mainMapperCurrentIndexChanged(self, row: int):
        # 当主表当前行变化时，引发子表设置过滤条件
        pkn = self._mainPkFieldName
        v = self.record(row).value(pkn)
        self._subModel.init(self.editDataMode, v)

    def saveData(self):
        if self._editDataMode == JPEditDataMode.readOnlyMode:
            return
        if self._checkRequiredValue() is False:
            return
        if self._subModel._checkRequiredValue() is False:
            return
        rollback = False
        errStr = ''
        try:
            self._db.transaction()
        except Exception as e:
            rollback = True
            errStr = "开始事务失败！"
        else:
            try:
                for sql in self.saveDateSQL(
                        SaveDataSqlType.beforeSaveMainFormData):
                    self._db.exec(sql)
                if not self.submitAll():
                    rollback = True
                    raise Exception("主表提交数据失败！")
                for sql in self.saveDateSQL(
                        SaveDataSqlType.afterSaveMainFormData):
                    self._db.exec(sql)
                for sql in self.saveDateSQL(
                        SaveDataSqlType.beforeSaveSubFormData):
                    self._db.exec(sql)
                if not self._subModel.submitAll():
                    rollback = True
                    raise Exception("主表提交数据失败！")
                for sql in self.saveDateSQL(
                        SaveDataSqlType.afterSaveSubFormData):
                    self._db.exec(sql)
            except Exception as e:
                rollback = True
                errStr = str(e) + ";" + self._db.lastError().text()
        finally:
            if rollback:
                txt = ''
                if not self._db.rollback():
                    txt = '数据保存失败，回滚数据失败！数据库错误信息：\n{}'
                else:
                    txt = '数据保存失败，数据库错误信息：\n{}\n数据已经成功回滚！'
                if self.popMessageBox:
                    txt = txt.format(errStr)
                    QtWidgets.QMessageBox.warning(self.Dialog, '消息', txt)
            else:
                self._db.commit()
                self._subModel._tableView.selectRow(self._subModel.rowCount())
                if self.popMessageBox:
                    QtWidgets.QMessageBox.information(self.Dialog, '消息',
                                                      "数据保存成功！")
                if self.autoCloseDialog:
                    self.Dialog.done(1)
                m = self._editDataMode
                if m == JPEditDataMode.editMode:
                    self.mainRecordSaved.emit(m, self._filterValue)
                elif m == JPEditDataMode.newMode:
                    self.mainRecordSaved.emit(m, self._LAST_ID)
                return True


class JPListModel(QtSql.QSqlQueryModel):
    def __init__(self,
                 tableView: QtWidgets.QTableView,
                 sql: str,
                 defaultFilter=None,
                 pkFieldName: str = '',
                 db=QtSql.QSqlDatabase(),
                 editUI: object = None):
        super().__init__(parent=None)
        self.editUI = editUI
        if not sql:
            raise Exception('必须指定sql参数！')
        self._sql = sql
        self._defaultFilter = defaultFilter
        self._tableView = self._setTableView(tableView)
        self.setEnabledMenu(False)
        self._db = db
        self._setQuery(self._defaultFilter)

        # 设置可右键菜单
        self._enabledMenu = False
        self._tableView.setContextMenuPolicy(Qt.CustomContextMenu)  # 允许右键产生子菜单
        self._tableView.customContextMenuRequested.connect(
            self._setTableViewMenu)

        # 设置列信息字典
        self._viewColumns = ViewColumns(db)
        self._viewColumns._setDefaultColumn(self, db, self.record())

        # 表名
        self._mainTableName = None
        self._subTableName = None
        self._modelObject = None

        self._tableViewName: str = ''

        # 图标信息
        self._ico_act_edit = _loadIcon(_ICO_DICT['ico_act_edit'])
        self._ico_act_del = _loadIcon(_ICO_DICT['ico_act_del'])
        self._ico_act_new = _loadIcon(_ICO_DICT['ico_act_new'])
        self._ico_act_search = _loadIcon(_ICO_DICT['ico_act_search'])
        self._ico_act_browse = _loadIcon(_ICO_DICT['ico_act_browse'])
        self._ico_act_exportExcel = _loadIcon(_ICO_DICT['ico_act_exportExcel'])

    def setEnabledMenu(self, mode: bool = True):
        '''设定菜单的是否显示'''
        self._enabledMenu = mode

    def _setQuery(self, filter: str):
        sql = 'select * from ({}) as mySQL____ where {}'
        sql = sql.format(self._sql, filter) if filter else self._sql
        self.setQuery(sql, self._db)
        # 防止只加载256行数据
        while self.canFetchMore():
            self.fetchMore()

    def _setTableView(self,
                      widget: QtWidgets.QTableView) -> QtWidgets.QTableView:
        # 设置tableView
        if widget:
            en = QtWidgets.QAbstractItemView
            widget.setEditTriggers(en.NoEditTriggers)
            widget.setSelectionBehavior(en.SelectRows)
            widget.setSelectionMode(en.SingleSelection)
        return widget

    def _setTableViewMenu(self, pos):
        if not self._enabledMenu:
            return
        tv = self._tableView
        menu = QtWidgets.QMenu()
        actNew = menu.addAction(self._ico_act_new, u"添加")
        actDel = menu.addAction(self._ico_act_del, u"删除")
        actEdit = menu.addAction(self._ico_act_edit, u"编辑")
        actBrowse = menu.addAction(self._ico_act_browse, u"浏览")
        menu.addSeparator()
        actSearch = menu.addAction(self._ico_act_search, u"查询")
        actExp = menu.addAction(self._ico_act_exportExcel, u"导出")
        # 弹出的位置要减去标题行的高度
        newPos = tv.mapToGlobal(pos)
        hh = tv.verticalHeader().defaultSectionSize()
        newPos.setY(newPos.y() + hh)
        action = menu.exec_(newPos)
        # 取得鼠标点所在行号
        currentRow = tv.rowAt(pos.y())

        dic = {
            actNew: self.actionNew,
            actDel: self.actionDelete,
            actEdit: self.actionEdit,
            actSearch: self.actionSearch,
            actExp: self.actionExortToExcel,
            actBrowse: self.actionBrowse
        }
        if action:
            dic[action]()

    def headerData(self, index: int, QtOrientation, role=Qt.DisplayRole):
        # 横标题设置
        if QtOrientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._viewColumns._headerList[index]
        return super().headerData(index, QtOrientation, role=role)

    def data(self, index: QtCore.QModelIndex, role=Qt.DisplayRole):
        c = index.column()
        if role == Qt.DisplayRole:
            value = super().data(index, role=Qt.EditRole)
            return self._viewColumns[c].displayString(value)
        elif role == Qt.TextAlignmentRole:
            return self._viewColumns._alignmentList[c]
        else:
            return super().data(index, role)

    def init(self):
        self._tableView.setModel(self)
        for i, vc in enumerate(self._viewColumns):
            self._tableView.setColumnWidth(i, vc.width)

    def _initEditModel(self,
                       editmode: JPEditDataMode = JPEditDataMode.newMode,
                       filterValue=None):

        if not self._mainTableName:
            t = "必须先执行setMainTable方法设定主表信息！"
            raise RuntimeError(t)

        if not self.editUI:
            raise RuntimeError('必须在实例化JPListModel类时设置编辑窗体ui')

        # 生成编辑模型类(mainSub)
        _class = self.onGetMainModelOrMainSubModel()
        if not self._subTableName:
            # 建立编辑模型
            self._modelObject = _class(self.editUI,
                                       windowsFlags=Qt.WindowFlags(),
                                       db=self._db)
            self._modelObject.setMainTable(self._mainTableName,
                                           self._mainPkFieldName,
                                           self._mainLinkField)
            self._modelObject.init(editmode, filterValue)
        else:
            # 建立编辑模型
            self._modelObject = _class(self.editUI,
                                       windowsFlags=Qt.WindowFlags(),
                                       tableViewName=self._tableViewName,
                                       db=self._db)
            self._modelObject.setMainTable(self._mainTableName,
                                           self._mainPkFieldName,
                                           self._mainLinkField)
            self._modelObject.setSubTable(self._subTableName,
                                          self._subLinkField, self._subSorter)
            self._modelObject.init(editmode, filterValue)

        self._modelObject.mainRecordSaved.connect(self._gotoRow)

    def _gotoRow(self, editmode: JPEditDataMode, pkValue: QtCore.QVariant):
        if not pkValue:
            return
        self._setQuery(self._defaultFilter)
        col = self.viewColumn(self._mainLinkField).fieldIndex
        for i in range(self.rowCount()):
            rec = self.record(i)
            if rec.value(col) == pkValue:
                self._tableView.setCurrentIndex(self.createIndex(i, 0))

    def viewColumn(self, fieldName) -> ViewColumn:
        '''不要删除此函数，其他类对此函数有依赖性，主要是代理'''
        for v in self._viewColumns:
            if v.fieldName == fieldName:
                return v
        msg = '列[{}]未包含在查询中,请检查查询语句\n{}'.format(fieldName, self._sql)
        raise Exception(msg)

    def setMainTable(self,
                     tableName: str,
                     pkFieldName: str,
                     linkFieldName: str = None):
        '''设定主表信息，编辑窗体根据这些信息生成查询'''
        self._mainTableName = tableName
        self._mainPkFieldName = pkFieldName
        self._mainLinkField = linkFieldName if linkFieldName else pkFieldName

    def setSubTable(self,
                    tableName: str,
                    linkFieldName: str = None,
                    sorter='',
                    tableViewName: str = 'tableView'):
        '''设定子表信息，编辑窗体根据这些信息生成查询（无子表时不作设置）'''
        if not self._mainTableName:
            t = "必须先执行setMainTable方法设定主表信息！"
            raise RuntimeError(t)
        self._subTableName = tableName
        self._subLinkField = linkFieldName if linkFieldName else self._mainLinkField
        self._subSorter = sorter
        self._tableViewName = tableViewName

    def _getCurrentSelectPKValue(self):
        # 返回当选选中行的主键值
        index = self._tableView.selectionModel().currentIndex()
        col = self.viewColumn(self._mainLinkField).fieldIndex
        if index.isValid():
            newIndex = self.createIndex(index.row(), col)
            return self.data(newIndex, Qt.EditRole)

    def onEditFormModelcreated(self, model, mode: JPEditFormModelRole):
        '''编辑窗体模型建立完成后调用此事件函数，可在此函数中增加子表列等'''
        return

    def onBefoerShowEditForm(self, pkValue):
        '''显示编辑窗体之前执行此函数，用户可以覆盖'''
        return

    def actionEdit(self):
        pk = self._getCurrentSelectPKValue()
        if pk is None:
            return
        self._initEditModel(JPEditDataMode.editMode, pk)
        self.onBefoerShowEditForm(pk)
        self._modelObject.Dialog.exec_()

    def actionNew(self):
        self._initEditModel(JPEditDataMode.newMode)
        self.onBefoerShowEditForm(None)
        self._modelObject.Dialog.exec_()

    def actionDelete(self):
        p = self._tableView.parent()
        mn = self._mainTableName
        ml = self._mainLinkField
        sn = self._subTableName
        sl = self._subLinkField
        pk = self._getCurrentSelectPKValue()
        header = self._viewColumns[ml].header
        txt = ('您确认要删除[<font color="blue">{}={}</font>]的记录吗？'
               '删除后将不可恢复！点击[cancel]可取消删除!')
        txt = txt.format(header, pk)
        if QtWidgets.QMessageBox.question(
                p,
                '确认',
                txt,
                defaultButton=QtWidgets.QMessageBox.Cancel
        ) == QtWidgets.QMessageBox.Cancel:
            return
        if pk is None:
            return
        sql = "delete from {} where {};"
        # 事务处理
        rollback = False
        errStr = ''
        try:
            self._db.transaction()
        except Exception as e:
            rollback = True
            errStr = "开始事务失败！"
        else:
            try:
                query = QtSql.QSqlQuery(self._db)
                query.exec(sql.format(mn, _createFilter(ml, pk)))
                if sn:
                    query.exec(sql.format(sn, _createFilter(sl, pk)))
            except Exception as e:
                rollback = True
                errStr = str(e) + ";" + self._db.lastError().text()
        finally:
            rowNum = self._tableView.currentIndex().row()
            if rollback:
                txt = ''
                if not self._db.rollback():
                    txt = '数据删除失败，回滚数据失败！数据库错误信息：\n{}'
                else:
                    txt = '数据删除失败，数据库错误信息：\n{}\n数据已经成功回滚！'
                if self.popMessageBox:
                    txt = txt.format(errStr)
                    QtWidgets.QMessageBox.warning(p, '消息', txt)
            else:
                self._db.commit()
                # 定位到新行
                self._setQuery(self._defaultFilter)
                if rowNum >= (self.rowCount() - 1):
                    newNum = self.rowCount() - 1
                else:
                    newNum = rowNum
                newIndex = self.createIndex(newNum, 0)
                self._tableView.setCurrentIndex(newIndex)
                QtWidgets.QMessageBox.information(p, '消息', "数据删除成功！")
                return True

    def actionBrowse(self):
        pk = self._getCurrentSelectPKValue()
        if pk is None:
            return
        self._initEditModel(JPEditDataMode.readOnlyMode, pk)
        self.onBefoerShowEditForm(pk)
        self._modelObject.Dialog.exec_()

    def actionSearch(self):
        def mySetFilter(filter:str):
            self._setQuery(filter)
        sear = SearchTableModel(self)
        sear.CondictionsCreated.connect(mySetFilter)
        sear.DlgSearch.exec()


    def actionExortToExcel(self):
        xls = JPExportToExcel(self._tableView.parent())
        xls.exportQuery(self._viewColumns, self.query())

    def onGetMainModelOrMainSubModel(self):
        '''接口方法，用户可覆盖，返回一个模型类，一般用于
        用户根据MainModel或MainSubModel设计一个子类返回，
        可改变子类的行为'''
        if self._subTableName:
            return JPMainSubTableModel
        return JPMainTableModel
