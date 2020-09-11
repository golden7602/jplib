# -*- coding: utf-8 -*-

import time
from os import getcwd
from sys import path as jppath
jppath.append(getcwd())

import xlwt
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5 import QtSql, QtCore



class xls_alignment():
    VERT_TOP = 0x00  #上端对齐
    VERT_CENTER = 0x01  #居中对齐（垂直方向上）
    VERT_BOTTOM = 0x02  #低端对齐
    HORZ_LEFT = 0x01  #左端对齐
    HORZ_CENTER = 0x02  #居中对齐（水平方向上）
    HORZ_RIGHT = 0x03  #右端对齐


class JPExportToExcel(object):
    rowExported = QtCore.pyqtSignal(int, int)

    def __init__(self, parent):
        '''parent为母窗体，对话窗口显示在其中'''
        super().__init__()
        self.parent = parent
        self._initStyle()

    def __saveFile(self):
        fn, filetype = QFileDialog.getSaveFileName(
            self.parent,
            "Export To Excel File Name",
            getcwd(),  # 起始路径
            "Excel Files (*.xls)")
        if not fn:
            return
        try:
            self.workbook.save(fn)
        except Exception as e:
            errstr = '写入文件出错！\nWrite file error!\n{}'
            errstr = errstr.format(e)
        else:
            errStr = '导出数据完成！\nExport to excel complete!'
        finally:
            QMessageBox.information(self.parent, '提示', errStr)

    def _initStyle(self):
        # 新建一个excel
        self.workbook = xlwt.Workbook(encoding='utf-8')
        # 建立一个表线,用于加入到样式中
        borders = xlwt.Borders()
        borders.left = xlwt.Borders.THIN
        # DASHED虚线 NO_LINE没有 THIN实线
        # May be: NO_LINE, THIN, MEDIUM, DASHED,
        # DOTTED, THICK, DOUBLE, HAIR,
        # MEDIUM_DASHED, THIN_DASH_DOTTED,
        # MEDIUM_DASH_DOTTED, THIN_DASH_DOT_DOTTED,
        # MEDIUM_DASH_DOT_DOTTED,
        # SLANTED_MEDIUM_DASH_DOTTED, or 0x00 through 0x0D.
        borders.right = xlwt.Borders.THIN
        borders.top = xlwt.Borders.THIN
        borders.bottom = xlwt.Borders.THIN
        borders.left_colour = 0x40
        borders.right_colour = 0x40
        borders.top_colour = 0x40
        borders.bottom_colour = 0x40

        pattern = xlwt.Pattern()  # Create the Pattern
        # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
        pattern.pattern = xlwt.Pattern.SOLID_PATTERN
        # May be: 8 through 63. 0 = Black, 1 = White, 2 = Red, 3 = Green,
        # 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon,
        # 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow ,
        # almost brown), 20 = Dark Magenta, 21 = Teal,
        # 22 = Light Gray, 23 = Dark Gray, the list goes on...
        pattern.pattern_fore_colour = 22

        # 建立一个用于表头的样式
        self.style_header = xlwt.XFStyle()  # Create Style
        self.style_header.borders = borders  # Add Borders to Style
        self.style_header.pattern = pattern  # Add Pattern to Style

        # 建立一个用于用于表体的样式
        pattern_detail = xlwt.Pattern()
        pattern_detail.pattern = xlwt.Pattern.SOLID_PATTERN
        pattern_detail.pattern_fore_colour = 1
        self.style_detail = xlwt.XFStyle()
        self.style_detail.borders = borders
        self.style_detail.pattern = pattern_detail

    def __exportOneQuery(self,
                         viewColumns,
                         query: QtSql.QSqlQuery,
                         sheetName='newsheet'):
        vcs = viewColumns
        self.__curRow = 0
        # 添加一个sheet页
        sheet = self.workbook.add_sheet(sheetName)
        for col, vc in enumerate(vcs):
            sheet.write(self.__curRow, col, vc.header, self.style_header)
        self.__curRow += 1
        bz = query.first()
        aligns = self.__getAligns(vcs)
        chars = [0] * len(vcs)
        while bz:
            for col, vc in enumerate(vcs):
                rec = query.record()
                vStr = vc.displayString(rec.value(col))
                l = len(vStr) if vStr else 0
                if l > chars[col]:
                    chars[col] = l
                tempAlign = self.style_detail.alignment
                self.style_detail.alignment = aligns[col]
                sheet.write(self.__curRow, col, vStr, self.style_detail)
                self.style_detail.alignment = tempAlign
            self.__curRow += 1
            bz = query.next()
        for col, vc in enumerate(vcs):
            sheet.col(col).width=256* chars[col]
    def __getAligns(self, vcs) -> list:
        result = []
        A = xlwt.Formatting.Alignment
        for vc in vcs:
            align = A()
            try:
                if vc.align & QtCore.Qt.AlignHCenter:
                    align.horz = A.HORZ_CENTER
                if vc.align & QtCore.Qt.AlignLeft:
                    align.horz = A.HORZ_LEFT
                if vc.align & QtCore.Qt.AlignRight:
                    align.horz = A.HORZ_RIGHT
                if vc.align & QtCore.Qt.AlignVCenter:
                    align.vert = A.VERT_CENTER
                if vc.align & QtCore.Qt.AlignTop:
                    align.vert = A.VERT_TOP
                if vc.align & QtCore.Qt.AlignBottom:
                    align.vert = A.VERT_BOTTOM
            except Exception as e:
                align.horz = A.HORZ_CENTER
                align.vert = A.VERT_CENTER
            finally:
                result.append(align)
        return result

    def exportQuery(self,
                    viewColumns,
                    query: QtSql.QSqlQuery,
                    sheetName='newsheet'):
        '''导出一个查询对象'''
        if not isinstance(query, QtSql.QSqlQuery):
            raise Exception('query参数类型错！')
        self.__exportOneQuery(viewColumns, query, sheetName)
        self.__saveFile()

    def exportSQL(self,
                  viewColumns,
                  SQL: str,
                  db=QtSql.QSqlDatabase(),
                  sheetName='newsheet'):
        '''导出一个查询语句'''
        if not isinstance(SQL, str):
            raise Exception('SQL参数类型错！')
        query = QtSql(SQL, db)
        if not query.record():
            raise Exception('SQL执行结果有误，请检查SQL！')
        self.__exportOneQuery(viewColumns, query, sheetName)
        self.__saveFile()
