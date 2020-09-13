from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import base64
from functools import partial
import re



class ReadOnlyDelegate(QtWidgets.QItemDelegate):
    '''内部类，生成一个只读代理，设置给需要只读的列'''
    def createEditor(self, *args, **kwargs):
        return


class StringDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        wdgt = QtWidgets.QLineEdit(parent)
        # 隐藏右键菜单
        wdgt.setContextMenuPolicy(Qt.NoContextMenu)
        return wdgt
    def updateEditorGeometry(
            self, editor: QtWidgets.QWidget,
            StyleOptionViewItem: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex):
        editor.setGeometry(StyleOptionViewItem.rect)


class IntgerDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self,
                 parent: QtCore.QObject = None,
                 prefix: str = None,
                 suffix: str = None):
        '''整数数代理\nprefix前缀字符串；suffix后缀字符串'''
        super().__init__(parent)
        self.prefix = prefix
        self.suffix = suffix

    def fixup(self, vstr):
        v = int(vstr)
        if v > self.top():
            return str(self.top())
        if v < self.bottom():
            return str(self.bottom())

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        wdgt = QtWidgets.QSpinBox(parent)
        # 是否打开中文输入
        # wdgt.setAttribute(Qt.WA_InputMethodEnabled, True)
        rng = index.model().getViewColumn(index).range()
        vMin, vMax = rng
        if any(rng):
            wdgt.setRange(int(vMin), int(vMax))
        else:
            wdgt.setRange(-2147483648, 2147483647)
        if self.prefix:
            wdgt.setPrefix(self.prefix)
        if self.suffix:
            wdgt.setSuffix(self.suffix)
        wdgt.setGeometry(option.rect)
        return wdgt

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex):
        editor.setGeometry(option.rect)

    # 这里应该加上禁止小数点的功能
    def editorEvent(self, event, model, vi, index):
        if (event.type() == QtCore.QEvent.KeyPress
                and event.key() == Qt.Key_Period):
            return
        else:
            return super().editorEvent(event, model, vi, index)


class FloatDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self,
                 parent: QtCore.QObject = None,
                 prefix: str = None,
                 suffix: str = None):
        '''浮点数代理\nprefix前缀字符串；suffix后缀字符串'''
        super().__init__(parent)
        self.prefix = prefix
        self.suffix = suffix

    def fixup(self, vstr):
        v = float(vstr)
        if v > self.top():
            return str(self.top())
        if v < self.bottom():
            return str(self.bottom())

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        wdgt = QtWidgets.QDoubleSpinBox(parent)
        # 是否打开中文输入
        # wdgt.setAttribute(Qt.WA_InputMethodEnabled, True)
        wdgt.setDecimals(index.model().getViewField(index).precision())
        rng = index.model().getViewColumn(index).range()
        vMin, vMax = rng
        if any(rng):
            wdgt.setRange(float(vMin), float(vMax))
        else:
            wdgt.setRange(float(-10**20), float(10**20))
        if self.prefix:
            wdgt.setPrefix(self.prefix)
        if self.suffix:
            wdgt.setSuffix(self.suffix)
        wdgt.setGeometry(option.rect)
        return wdgt

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex):
        editor.setGeometry(option.rect)


class DateDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent: QtCore.QObject = None):
        '''日期输入代理'''
        super().__init__(parent)
        self.defaultDate=None

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        wdgt = QtWidgets.QDateEdit(parent)
        wdgt.setDisplayFormat("yyyy-MM-dd")
        wdgt.setCalendarPopup(True)
        wdgt.setGeometry(option.rect)
        if self.defaultDate:
            wdgt.setDate(self.defaultDate)
        return wdgt

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex):
        editor.setGeometry(option.rect)


class IntSearchDelegate(QtWidgets.QStyledItemDelegate):
    class _Ui_Form(object):
        def setupUi(self, Form):
            Form.setObjectName("Form")
            Form.resize(563, 472)
            self.verticalLayout = QtWidgets.QVBoxLayout(Form)
            self.verticalLayout.setContentsMargins(2, 2, 2, 2)
            self.verticalLayout.setSpacing(2)
            self.verticalLayout.setObjectName("verticalLayout")
            self.horizontalLayout = QtWidgets.QHBoxLayout()
            self.horizontalLayout.setObjectName("horizontalLayout")
            self.label = QtWidgets.QLabel(Form)
            self.label.setMinimumSize(QtCore.QSize(0, 25))
            self.label.setObjectName("label")
            self.horizontalLayout.addWidget(self.label)
            self.lineEdit = QtWidgets.QLineEdit(Form)
            self.lineEdit.setMinimumSize(QtCore.QSize(0, 25))
            self.lineEdit.setObjectName("lineEdit")
            self.horizontalLayout.addWidget(self.lineEdit)
            self.verticalLayout.addLayout(self.horizontalLayout)
            self.treeWidget = QtWidgets.QTreeWidget(Form)
            self.treeWidget.setEditTriggers(
                QtWidgets.QAbstractItemView.NoEditTriggers)
            self.treeWidget.setSelectionMode(
                QtWidgets.QAbstractItemView.SingleSelection)
            self.treeWidget.setObjectName("treeWidget")
            self.treeWidget.headerItem().setText(0, "1")
            self.verticalLayout.addWidget(self.treeWidget)
            self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
            self.horizontalLayout_2.setSpacing(0)
            self.horizontalLayout_2.setObjectName("horizontalLayout_2")
            spacerItem = QtWidgets.QSpacerItem(40, 20,
                                               QtWidgets.QSizePolicy.Expanding,
                                               QtWidgets.QSizePolicy.Minimum)
            self.horizontalLayout_2.addItem(spacerItem)
            self.butOK = QtWidgets.QPushButton(Form)
            self.butOK.setObjectName("butOK")
            self.horizontalLayout_2.addWidget(self.butOK)
            spacerItem1 = QtWidgets.QSpacerItem(5, 20,
                                                QtWidgets.QSizePolicy.Minimum,
                                                QtWidgets.QSizePolicy.Minimum)
            self.horizontalLayout_2.addItem(spacerItem1)
            self.butCancel = QtWidgets.QPushButton(Form)
            self.butCancel.setObjectName("butCancel")
            self.horizontalLayout_2.addWidget(self.butCancel)
            spacerItem2 = QtWidgets.QSpacerItem(20, 20,
                                                QtWidgets.QSizePolicy.Minimum,
                                                QtWidgets.QSizePolicy.Minimum)
            self.horizontalLayout_2.addItem(spacerItem2)
            self.verticalLayout.addLayout(self.horizontalLayout_2)

            self.retranslateUi(Form)
            QtCore.QMetaObject.connectSlotsByName(Form)

        def retranslateUi(self, Form):
            _translate = QtCore.QCoreApplication.translate
            Form.setWindowTitle(_translate("Form", "选择项目"))
            self.label.setText(_translate("Form", "关键字："))
            self.lineEdit.setToolTip(_translate("Form", "输入关键字可快速度定位"))
            self.butOK.setText(_translate("Form", "确定"))
            self.butCancel.setText(_translate("Form", "取消"))

    def _loadTreeview(treeWidget, items, rootID, selected_item):
        class MyThreadReadTree(QtCore.QThread):
            """加载功能树的线程类"""
            def __init__(self, treeWidget, rootID, items):
                super().__init__()
                treeWidget.clear()
                tree_title = ["项目列表", "选择"]
                treeWidget.setHeaderLabels(tree_title)
                treeWidget.dirty = False
                root = QtWidgets.QTreeWidgetItem(treeWidget)
                root.setText(0, "高科集团")
                root.FullPath = "高科集团"
                root.key = "_root_root"
                root.dirty = False
                treeWidget._rootItem = root
                self.root = root
                self.items = items
                self.selected_item = selected_item
                self.rootID = rootID

            def parentChecked(self, parentItem: QtWidgets.QTreeWidgetItem):
                parentItem.setExpanded(1)
                if parentItem.key == self.root.key:
                    return
                else:
                    self.parentChecked(parentItem.parent())

            def addItems(self, parent, items):
                for r in items:
                    item = QtWidgets.QTreeWidgetItem(parent)
                    item.setText(0, r[1])
                    item.key = r[0]
                    item.jpData = r
                    item.dirty = False
                    item.FullPath = (parent.FullPath + '\\' + r[1])
                    self.addItems(item,
                                  [l for l in self.items if l[2] == r[0]])
                    # item.setExpanded(1)

            def run(self):  # 线程执行函数
                self.addItems(
                    self.root,
                    [l for l in self.items if not l[2] == self.rootID])
                self.root.setExpanded(True)

            def getRoot(self):
                return

        _readTree = MyThreadReadTree(treeWidget, rootID, items)
        _readTree.run()

    class _FormSelecter(_Ui_Form, QtCore.QObject):
        selectItemsChanged = QtCore.pyqtSignal(list)
        selectItemChanged = QtCore.pyqtSignal(int)

        def __init__(self, tree_data=[], rootID=None, selected_item=[]):
            super().__init__()
            self.tree_data = tree_data
            self.ListWidget = None
            self.Dialog = QtWidgets.QDialog()
            self.setupUi(self.Dialog)
            self.Dialog.setWindowModality(QtCore.Qt.ApplicationModal)
            self.treeWidget.setColumnWidth(0, 450)
            self.lineEdit.textChanged.connect(self.actionClick)
            IntSearchDelegate._loadTreeview(self.treeWidget, tree_data, rootID,
                                            selected_item)
            self.butOK.clicked.connect(self.okbutOKClicked)
            self.butCancel.clicked.connect(self.onCancelClick)

        def show(self):
            return self.Dialog.exec_()

        def onCancelClick(self):
            self.Dialog.close()

        def setListWidget(self, ListWidget):
            self.ListWidget = ListWidget

        def okbutOKClicked(self):
            key = self.treeWidget.currentItem().key
            if key:
                self.selectItemChanged.emit(key)
            # 遍历树控件节点
            cursor = QtWidgets.QTreeWidgetItemIterator(self.treeWidget)
            lst = []
            while cursor.value():
                item = cursor.value()
                if item.checkState(1) == QtCore.Qt.Checked:
                    lst.append(item.key)
                cursor = cursor.__iadd__(1)
            if lst:
                self.selectItemsChanged.emit(lst)
            self.Dialog.close()

        def ChangeParentExpanded(self, item):
            """递归修改上级为选中"""
            if item.parent() is self.treeWidget._rootItem:
                return
            else:
                p = item.parent()
                if p:
                    p.setExpanded(True)
                    self.ChangeParentExpanded(p)

        def actionClick(self, txt):
            if not txt:
                return
            p = ''.join((r'.*', txt, r'.*'))
            obj = re.compile(p)
            cursor = QtWidgets.QTreeWidgetItemIterator(self.treeWidget)
            while cursor.value():
                item = cursor.value()
                if item is not self.treeWidget._rootItem:
                    item.setExpanded(False)
                    item.setSelected(False)
                cursor = cursor.__iadd__(1)
            cursor = QtWidgets.QTreeWidgetItemIterator(self.treeWidget)
            while cursor.value():
                item = cursor.value()
                if item is self.treeWidget._rootItem:
                    cursor = cursor.__iadd__(1)
                    continue
                if item.parent() is self.treeWidget._rootItem:
                    cursor = cursor.__iadd__(1)
                    continue
                itemtext = item.text(0)
                if obj.match(itemtext):
                    self.ChangeParentExpanded(item)
                    item.setSelected(True)
                cursor = cursor.__iadd__(1)

    icodata = (b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAA7E'
               b'AAAOxAGVKw4bAAAIFklEQVRYhb1XW2xcVxVd9zEznvG8PDOemdjxY2zHSdM4'
               b'LWlaGhqlKDQVoagSCBW1IkkhKHxRpEpIPKp8IIEQiJJ+RgK1kIpSEARSoVaA'
               b'KElACW0ISZz4Vcdvz9gev8bjed579+Jjxp5HHfjrlY7uufeeq7322uvsvY9y'
               b'6rXbAAmSAFC6l0d5foCUPpIxkAEKb4AyRfJvFMltrKNI6R8RkAIIQQpYvkNk'
               b'cx3J8rNAB4mSaWwaBukm+S2QJ/0uPep1aHDaNdg0BamMgWzBwPxq1gJ5juQP'
               b'QRkuAZFNB7jpgNQ9l96VwBA6qwyXF3ya5Ks9za5oV8gFh64iZ1goGBZEiNYm'
               b'F3QVEIE2Nr/2fP/E4nMUvkTyx5Bq4xss1HvNCitkiYESCwTAkwTPPtLp06Je'
               b'B6aXcphcziKTL8ZVRVkgaZimuduuqY3bAy60h9yI+p32kdmVH40nVvpIHt8w'
               b'XM9IDbCqZx1l0yCejngcP+sNO1G0BNenUsgVrfMPdQffOLK3JU7ASQJC5N4b'
               b'nm+81D/zmeGZlVO7tvudD8RCoMixsfjKLMhvbxiuCUdZI9XaAAXKV39+EyBb'
               b'Qd76eKcvICBuTqdy92/3vfjsY7EpEr0E2kn4yo6lSEwJMfLuzSnr3f9MnO3a'
               b'5uvoDPtwdWAayZXMJ0m5eC/RVUTJighBnt4ZcQXCHjuuTaawt93/9WcOdKZJ'
               b'PEGgj8Q2IRrLDmWESAjRfqiv/apNU59/+18jvw64HZHObX4kl9NnQO4naX1I'
               b'dDXhKL1Ty4o/1hVyYXQhC8OS15850Jkg8SiBAyT6hIiRaCHRIkRMiD4SB4R8'
               b'9OH7Wl3RgPt7E3MraA15EG5qfJDCI/WiQ93W3AiHSvDxiNfuVBUFI3Np6/Ce'
               b'6C/KtO9hyVgTCScJu5SGk0STkDEprek9+dmHL8aT6buZXBHRoAegPF0vOlaN'
               b'CiMCFeTjQZcNazkDmoaBh7qCOQJtZW89JGwkFOGmuBUhbQJ4ymvahPA7bNqF'
               b'mYUUAl4nSB6oFV09C5VQqCBiTruGdN6ArioDBFwk/EK4tzAOISGAQsImhFsI'
               b'PwmXw6YPpDN5NDhsINleHed6FrCZCwiVpFNVAEsIADlWGduY1xnf4j0A0rBE'
               b'oAAARbuX6FAHSgWZLJoCu6bCMq2wEFkSqyTWhTA2GKszTiGM8ppVEtl80Wht'
               b'sOkoGiYoXL6X6OoTk0qyfy1bRFOjHUXTeqRgWGskpoWIC5EmYQjJLYynhYiT'
               b'mCaxms8XPxH0NyKdyQPkcK3othbkBgNXltYLsOsKQh5H6LW/Du0TYkSI2yTG'
               b'hVyRUmiKUho5EitCjLO0ZuTiv0fshmkeiQQ8WFhKo1QpqwtRbfqFSA0DV1bW'
               b'CwNzqzl0BBoxnVw7nVjOzJC4KuQVAfpLQBAvezwuRD+JKySuEhi9cnP0m/d1'
               b'hu1QgJHxOQuUc5UUXF8da+fag0dPguSkacpzO1q8KBhW08X+mY59PZHXNV1b'
               b'IbEsxKIQibLxARLXSLxPYODMuT9/MRJ0v7C7exvGZ5KYW0id7d696zeBcLOy'
               b'PL9QVXorXlezoT1w9CRAfrCeN/ZZluzc3daETL644533x/ev5wp/6G4NDpbp'
               b'HiqH5RaJgetDUyvnLvzzpXDQ/Y2etmbYbCo0TcPY9IJvZWHxy6vJpKun7/5r'
               b'wWiES4m5KuPVaVmgnHjlHxuofBS53Nvi69u5vQljiVWMJ1ZRKJoXXHb9HZ+7'
               b'YYgkVteyXZls7mDRsD63oz3o2xWLIlcowmG3QYRIredhmhZmE0uYnE6+5fF7'
               b'TwSjkdTw9RuyqQephEE5fuZyZZ8Km0H5fWfEe7C3tQkOm4b4YhqJxTTWSuqG'
               b'q8GGkM+FlrAXuqZh8G4cg6OJ2V1d0dZYRwR5Q1A0CVUBZmYWMDERv2lvsH8+'
               b'3NY2OXrjloXNilhOq8d/eqkuRqJReBqUF3tamtyRQCMCHic2+gYSWM/mMTu/'
               b'iunEMlJr2TdVBS9QOHb4UF9jzgByRQskYdcULCaXMTY6FVdU7QvRWMd7Ylky'
               b'2X+Hmwwce/liVTNZU7cDpJyC8ClSDoJEg11DNlsAKcMUniflVxD2d+/eqYwN'
               b'DL8a64icaGkJY71goWhYUJQSiPXUGkaGJrIET0Q6O/4oIubMnUGWAPzk76ju'
               b'UFiTvaQamEZKK4VT9R0whfD4vN5cZv18+/bI4ei2ZmQKJgpFEwDh0BUUc3kM'
               b'3h4VEeu7zZ0dL4tlGYnhEWp7nzxR6eGqupWaWJVAkMJUZS/X9nsdvT1Fm93+'
               b'28R0ogsK+zyNDQAAwyyxoesaItGAoqvqE/GJqVZV1//ijYRNbe+R4zVpsjZR'
               b'VKfOje9b9HsULM3NI9LWanqDgbemxyZUyzAPuZx2aLq6CQJQEAh4oCrKxxZm'
               b'EvtVXfud1lcGUG24Jmf/z7ouNZluKTEHf3NI3E1NlxNTs2ML80tHfV6X3tBg'
               b'h2EJDMOERSIU8kElepLx+WUVdbGvhOPDh4ytikn1IQMk7t66TRExo7GO1wke'
               b'HRkcW0yvpuB26LDZSgcK07TgD/pA8kn13nV7i15eqr/XN5qV/yb671BErOb2'
               b'tkuqph0a+2ByeCm5BL/bAbfLAYddRz5XAMk5bc+nvlSdiKpFV7UD6oDVhKO+'
               b'0JTAppKLWEsuMtTRtlwsFN5Yml/cr4jEdFXBWiqNoduja6qmfUV59vtv/98D'
               b'ZH0vX7sN60MmdcAE4e4uhaS2ODb+NYo8RnJZ1bRXQl2xuwpJfFTX8R/8SdmY'
               b'//I7TxEAPlIAW13/BZhNjLKjhFEEAAAAAElFTkSuQmCC')

    def __init__(self,
                 parent: QtCore.QObject = None,
                 RootID=None,
                 selected_Data=[]):
        '''dataListOrSqlo 设置用于tree的数据列表或查询语句，必须有三列：编号,文本，父编号\n
        RootID为根节点的父ID，查找时在第三列查找\n
        selected_Data
        '''   
        super().__init__(parent)
  
        self.selected_Data = selected_Data
        self.rootID = RootID
        self.selecterForm: IntSearchDelegate._FormSelecter = None

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        wdgt = QtWidgets.QLineEdit(parent)
        wdgt.keyPressEvent = self.editLinekeyPressEvent
        vc = index.model()._viewColumns[index.column()]
        self.dataList = vc.treeSource
        #self.dataList = index.model().treeSource(index.column())
        pm = QtGui.QPixmap()
        pm.loadFromData(base64.b64decode(IntSearchDelegate.icodata))
        icon = QtGui.QIcon(pm)
        action = wdgt.addAction(icon, QtWidgets.QLineEdit.TrailingPosition)
        action.triggered.connect(partial(self._actionClick, index))
        # 是否打开中文输入
        wdgt.setAttribute(QtCore.Qt.WA_InputMethodEnabled, False)
        self.wdgt_ = wdgt
        return wdgt

    def editLinekeyPressEvent(self, KeyEvent):
        # 屏蔽文本框的按键事件
        pass

    def _actionClick(self, index: QtCore.QModelIndex):
        self.selecterForm = IntSearchDelegate._FormSelecter(
            self.dataList, self.selected_Data)
        self.selecterForm.selectItemChanged.connect(
            partial(self._selectedItem, index))
        self.selecterForm.show()

    def _selectedItem(self, index: QtCore.QModelIndex, id):
        self.wdgt_.itemValue_ = id
        index.model().setData(index, id, QtCore.Qt.EditRole)

    def setEditorData(self, editor: QtWidgets.QWidget,
                      index: QtCore.QModelIndex):
        v = index.model().data(index, QtCore.Qt.EditRole)
        lst = [r for r in self.dataList if r[0] == v]
        editor.itemValue_ = None
        if lst:
            editor.setText(str(lst[0][1]))
            editor.itemValue_ = lst[0][0]

    def setModelData(self, editor: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        index.model().setData(index, editor.itemValue_, QtCore.Qt.EditRole)
    def updateEditorGeometry(
            self, editor: QtWidgets.QWidget,
            StyleOptionViewItem: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex):
        editor.setGeometry(StyleOptionViewItem.rect)


class IntSelectDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget:
        wdgt = QtWidgets.QComboBox(parent)
        vc = index.model()._viewColumns[index.column()]
        self.rowSource = vc.rowSource
        for r in self.rowSource:
            wdgt.addItem(r[0], r[1])
        v = index.model().data(index, QtCore.Qt.EditRole)
        for i, r in enumerate(self.rowSource):
            if r[1] == v:
                wdgt.setCurrentIndex(i)
                return wdgt
        return wdgt

    def setModelData(self, editor: QtWidgets.QWidget,
                     model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        index.model().setData(index, editor.currentData(), QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem,
                             index: QtCore.QModelIndex):
        editor.setGeometry(option.rect)
