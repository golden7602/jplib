#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
from os import getcwd, environ, path as ospath
from sys import argv
from sys import exit as sys_exit
from sys import path as jppath

# 下面行解决造生成exe后闪退，请不要注释或删除
# 命令行下运行出现如下提示
# ImportError: unable to find Qt5Core.dll on PATHImportError: unable to find Qt5Core.dll on PATH
# 的问题
import fix_qt_import_error

from PyQt5 import sip
from PyQt5.QtCore import QMetaObject, Qt, QThread
from PyQt5.QtGui import QIcon, QPixmap, QGuiApplication
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
                             QProgressBar, QPushButton, QTreeWidgetItem,
                             QWidget, QMessageBox)

from lib.JPDatabase.Database import JPDb, JPDbType
from lib.JPFunction import readQss, setWidgetIconByName, seWindowsIcon
from lib.JPPublc import JPPub, JPUser


from lib.JPForms.JPFormBackup import Form_Backup
from lib.JPForms.JPFormConfig import Form_Config
from lib.JPForms.JPFormEnumManger import Form_EnumManger
from lib.JPForms.JPFormUser import Form_User

from Ui.Ui_FormMain import Ui_MainWindow
from Ui.Ui_FormBackGround import Ui_Form as Ui_Form_back
from lib.JPConfigInfo import ConfigInfo


class Form_Background(Ui_Form_back):
    def __init__(self, mainform):
        super().__init__()
        self.Widget = QWidget()
        self.setupUi(self.Widget)
        # self.label.setPixmap(mainform.backPixmap)
        self.label.setText("")
        mainform.addForm(self.Widget)


def loadTreeview(treeWidget, items, MF):
    class MyThreadReadTree(QThread):  # 加载功能树的线程类
        def __init__(self, treeWidget, items, MF):
            super().__init__()
            treeWidget.clear()
            root = QTreeWidgetItem(treeWidget)
            root.setText(0, "功能列表")
            root.FullPath = "Function"
            self.root = root
            self.items = items
            #self.icoPath = MF.icoPath

        def addItems(self, parent, items):
            pub = JPPub()
            for r in items:
                item = QTreeWidgetItem(parent)
                item.setText(0, r["fMenuText"])
                item.setIcon(0, QIcon(pub.getIcoPath(r["fIcon"])))
                item.jpData = r
                item.FullPath = (parent.FullPath + '\\' + r["fMenuText"])
                lst = [l for l in self.items if l["fParentId"] == r["fNMID"]]
                self.addItems(item, lst)
                item.setExpanded(1)

        def run(self):  # 线程执行函数
            lst = [l for l in self.items if l["fParentId"] == 1]
            self.addItems(self.root, lst)
            self.root.setExpanded(True)

        def getRoot(self):
            return

    _readTree = MyThreadReadTree(treeWidget, items, MF)
    _readTree.run()


class JPMainWindow(QMainWindow):
    def __init__(self, dataBaseType: JPDbType = JPDbType.MySQL, *args, **kwargs):
        super(JPMainWindow, self).__init__(*args, **kwargs)
        try:
            db = JPDb()
            db.setDatabaseType(dataBaseType)
            JPPub().MainForm = self
        except Exception as e:
            QMessageBox.warning(self, "提示", str(e))

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.label_Title.setText("")
        self.commandDict = {}
        self.logoPixmap = None

        self.addOneButtonIcon(self.ui.ChangeUser, "changeuser.png")
        self.addOneButtonIcon(self.ui.ChangePassword, "changepassword.png")
        # self.addLogoToLabel(self.ui.label_logo)

        # 用户及密码修改功能
        objUser = JPUser()
        objUser.INIT()  # 程序开始时只初始化一次
        objUser.userChange.connect(self.onUserChanged)
        objUser.currentUserID()
        self.ui.ChangeUser.clicked.connect(objUser.changeUser)
        self.ui.ChangePassword.clicked.connect(objUser.changePassword)

        # 堆叠布局
        self.ui.stackedWidget.removeWidget(self.ui.page)
        self.ui.stackedWidget.removeWidget(self.ui.page_2)

        # 隐藏树标题
        self.ui.label_FunPath.setText('')
        self.ui.treeWidget.setHeaderHidden(True)

        # 设置状态条中的进度条及标签
        self.Label = QLabel(" ")
        self.ProgressBar = QProgressBar()
        self.statusBar = self.statusBar()
        self.statusBar.addPermanentWidget(self.Label)
        self.statusBar.addPermanentWidget(self.ProgressBar)
        self.ProgressBar.setGeometry(0,  0, 100, 5)
        self.ProgressBar.hide()
        self.statusBar.hide()

        self.ui.splitter.setStretchFactor(0, 2)
        self.ui.splitter.setStretchFactor(1, 11)

        # 连接点击了功能树中的节点到函数
        self.ui.treeWidget.itemClicked[QTreeWidgetItem, int].connect(
            self.treeViewItemClicked)

    def closeEvent(self, event):
        q = QMessageBox
        result = q.question(self,
                            "请确认",
                            "退出前是否要备份数据 ?",
                            q.Yes | q.No, q.No)
        if result == QMessageBox.Yes:
            mypath = JPPub().getConfigData()["archives_path"]
            to = ospath.join(mypath, "backup.sql")
            Form_Backup(to)
        event.accept()

    def showInfo(self, range):
        self.ProgressBar.show()
        self.ProgressBar.setRange(0, range)
        self.statusBar.clearMessage()
        self.statusBar.show()
        QGuiApplication.processEvents()

    def dispInfo(self, text, value=0):
        self.statusBar.showMessage(text)
        if value:
            self.ProgressBar.setValue(value)
        QGuiApplication.processEvents()

    def hideInfo(self):
        self.ProgressBar.hide()
        self.ProgressBar.setRange(0, 0)
        self.statusBar.clearMessage()
        self.statusBar.hide()
        QGuiApplication.processEvents()

    def treeViewItemClicked(self, item, i):
        # 当点击了功能树中的节点时
        try:
            self.ui.label_FunPath.setText(item.FullPath)
            self.__getStackedWidget(item.jpData)
        except AttributeError as e:
            print(str(e))

    def onUserChanged(self, args):
        self.ui.label_UserName.setText(args[1])
        loadTreeview(self.ui.treeWidget, JPUser().currentUserRight(), self)
        Form_Background(self)

    def addForm(self, form):
        st = self.ui.stackedWidget
        if st.count() > 0:
            temp = st.widget(0)
            st.removeWidget(temp)
            try:
                JPPub().UserSaveData.disconnect(temp.UserSaveData)
            except Exception:
                pass
            del temp
        st.addWidget(form)

    def getIcon(self, icoName) -> QIcon:
        return QIcon(JPPub().getIcoPath(icoName))

    def getPixmap(self, icoName) -> QPixmap:
        return QPixmap(JPPub().getIcoPath(icoName))

    def addOneButtonIcon(self, btn, icoName):
        icon = QIcon(JPPub().getIcoPath(icoName))
        btn.setIcon(icon)

    def addLogoToLabel(self, label):
        if self.logoPixmap:
            label.setPixmap(self.logoPixmap)

    def addButtons(self, frm: QWidget, btns, styleName='Layout_Button'):
        """给窗体中Layout_Button的布局添加按钮"""
        layout = frm.findChild((QHBoxLayout, QWidget), styleName)
        if not (layout is None):
            layout.setSpacing(2)
            for m in btns:
                btn = QPushButton(m['fMenuText'])
                btn.NMID = m['fNMID']
                btn.setObjectName(m['fObjectName'])
                self.addOneButtonIcon(btn, m['fIcon'])
                btn.setEnabled(m['fHasRight'])
                layout.addWidget(btn)
            else:
                errStr = "窗体【{}】中没有找到名为'【Layout_Button】'的布局".format(
                    frm.objectName())
                errStr = errStr+",无法添加按钮。"
                logging.getLogger().warning(errStr)
            # 设置按名称执行槽函数
            QMetaObject.connectSlotsByName(frm)

    def __getStackedWidget(self, sysnavigationmenus_data):
        '''窗体切换'''
        frm = None
        btns = sysnavigationmenus_data['btns']
        self.menu_id = sysnavigationmenus_data['fNMID']
        sys_formCreater = {
            10: Form_EnumManger,
            13: Form_User,
            14: Form_Config
        }
        form_createor = {**sys_formCreater, **self.commandDict}
        if self.menu_id == 12:
            self.close()
        elif self.menu_id in form_createor:
            frm = form_createor[self.menu_id](self)
        else:
            frm = Form_Background(self)
        # 尝试给窗体添加按钮,要求窗体中有一个名为 “Layout_Button”的布局
        self.addButtons(frm, btns)
        return


class JPMianApp():
    def __init__(self, defultConfigDict: dict):
        """用户应用程序"""
        super().__init__()
        # 高清屏设置
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setStyle('Fusion')
        self.__app = QApplication(argv)
        cfg = ConfigInfo(defultConfigDict)
        self.__mainForm = JPMainWindow()

        # 根据配置文件设置文件及日志级别日志级别
        level = int(cfg.debug.level)
        fn = cfg.debug.logfile
        logger = logging.getLogger()
        logger.setLevel(level)
        f_handler = logging.FileHandler(fn, encoding="utf-8", mode="a")
        f_handler.setLevel(level)
        f_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s line[:%(lineno)d] - %(message)s"))
        conHandler = logging.StreamHandler()
        conHandler.setLevel(level)
        conHandler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s line[:%(lineno)d] - %(message)s"))
        logger.addHandler(f_handler)
        logger.addHandler(conHandler)

    def show(self):
        """启动应用程序"""
        # 启动数据改变事件的监听
        JPPub().receiveMessage(self.__app)
        self.__mainForm.showMaximized()
        sys_exit(self.__app.exec_())

    def setCommand(self, dict: dict):
        """保存用户窗体ID及对应对象的一个"""
        self.__mainForm.commandDict = dict

    def setMainFormLogo(self, logoName: str):
        '''设置主窗体Logo图标,参数为图标文件名'''
        pixmap = QPixmap(JPPub().getLogoPath(logoName))
        self.__mainForm.ui.label_logo.setPixmap(pixmap)
        self.__mainForm.logoPixmap = pixmap

    def setAppIcon(self, logoName: str):
        '''设置主应用程序图标,参数为图标文件名'''
        icon = QIcon()
        icon.addPixmap(
            QPixmap(JPPub().getIcoPath(logoName)))
        self.__mainForm.setWindowIcon(icon)

    def setMainFormTitle(self, title: str):
        '''设置主应用标题及主窗口顶部文字'''
        self.__mainForm.ui.label_Title.setText(title)
        self.__mainForm.setWindowTitle(title)


if __name__ == "__main__":
    app = JPMianApp()
    dic = {}
    app.setCommand(dic)
    app.show()
