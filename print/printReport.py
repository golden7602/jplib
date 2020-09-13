# -*- coding: utf-8 -*-
# 2020年8月最后一次修改
# 本类使用QtSql对象及Qt中数据类型来处理报表
# 删除字段计算功能，该功能应该在提供数据源时由SQL语句计算
# 分组功能全部重写
import abc
#import datetime
import itertools
#from decimal import Decimal
from enum import Enum
import logging
from typing import List
from PyQt5.QtCore import QDate, QDateTime, QMargins, QRect, Qt
from PyQt5.QtGui import (
    QFont,
    QFontMetrics,
    QPainter,
    QPixmap,
)
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5 import QtSql
from jplib.database.FieldType import FieldType, getFieldType
from jplib.dataStruction.linkList import BilateralLinkList
import typing

def _lstPaperSize():
    return [
        [5, 'A0', '841 x 1189 mm'],
        [6, 'A1', '594 x 841 mm'],
        [7, 'A2', '420 x 594 mm'],
        [8, 'A3', '297 x 420 mm'],
        [0, 'A4', '210 x 297 mm, 8.26 x 11.69 英寸'],
        [9, 'A5', '148 x 210 mm'],
        [10, 'A6', '105 x 148 mm'],
        [11, 'A7', '74 x 105 mm'],
        [12, 'A8', '52 x 74 mm'],
        [13, 'A9', '37 x 52 mm'],
        [14, 'B0', '1000 x 1414 mm'],
        [15, 'B1', '707 x 1000 mm'],
        [16, 'B10', '31 x 44 mm'],
        [17, 'B2', '500 x 707 mm'],
        [18, 'B3', '353 x 500 mm'],
        [19, 'B4', '250 x 353 mm'],
        [1, 'B5', '176 x 250 mm, 6.93 x 9.84 英寸'],
        [20, 'B6', '125 x 176 mm'],
        [21, 'B7', '88 x 125 mm'],
        [22, 'B8', '62 x 88 mm'],
        [23, 'B9', '33 x 62 mm'],
        [24, 'C5E', '163 x 229 mm'],
        [25, 'Comm10E', '105 x 241 mm, U.S. Common 10 Envelope'],
        [30, 'Custom', 'Unknown, or a user defined size.'],
        [26, 'DLE', '110 x 220 mm'],
        [4, 'Executive', '7.5 x 10 英寸, 190.5 x 254 mm'],
        [27, 'Folio', '210 x 330 mm'],
        [44, 'JisB6', ''],
        [28, 'Ledger', '431.8 x 279.4 mm'],
        [3, 'Legal', '8.5 x 14 英寸, 215.9 x 355.6 mm'],
        [2, 'Letter', '8.5 x 11 英寸, 215.9 x 279.4 mm'],
        [29, 'Tabloid', '279.4 x 431.8 mm'],
    ]


class PrintItemType(Enum):
    Label = 1
    Field = 2
    Picture = 3
    # 页码信息
    Page = 4
    # 用于Detail（主体）节计算行号用
    RowCount = 5
    # 打印时间
    PrintDateTime = 6
    # 一个联次的标题
    CopyTitle = 7


class PrintSectionType(Enum):
    """本类为节类型的枚举"""
    ReportHeader = 1
    PageHeader = 2
    Detail = 0
    PageFooter = 3
    ReportFooter = 4
    GroupHeader = 5
    GroupFooter = 6
    Unknown = -1


class CalcFieldType(Enum):
    '''计算字段类型枚举'''
    Sum = 0
    Count = 1
    Average = 2
    Max = 3
    Min = 4
    First = 5
    Last = 6


class PrintError(Exception):
    def __init__(self, msg: str):
        self.Msg = msg


class _jpPrintItem(metaclass=abc.ABCMeta):
    def __init__(self, rect: QRect, PrintObject, **kwargs):
        self.AutoLineBreak = kwargs.get("AutoLineBreak", False)
        self.Rect: QRect = rect
        self.PrintObject = PrintObject
        self.Bolder = kwargs.get("Bolder", True)
        self.Font = kwargs.get("Font", QFont("Microsoft YaHei", 11))
        self.AlignmentFlag: Qt.AlignmentFlag = kwargs.get(
            "AlignmentFlag", Qt.AlignHCenter)
        # 是否文本右转90度（纵向打印）
        self.Transform = kwargs.get("Transform", False)
        self.FormatString = kwargs.get("FormatString", '{}')
        self.FillColor = kwargs.get("FillColor", None)
        self.Visible = True
        # 是否在文本长度超出指定宽度时，自动截断加上省略号
        self.AutoEllipsis = kwargs.get("AutoEllipsis", False)
        # 是否在文本长度超出指定宽度时，自动缩小字号
        self.AutoShrinkFont = kwargs.get("AutoShrinkFont", False)
        self.Tag = kwargs.get("Tag", None)

    @abc.abstractmethod
    def getPrintText(self) -> str:
        pass

    def SetAlignment(self, AlignmentFlag: Qt.AlignmentFlag):
        """指定对齐方式"""
        self.AlignmentFlag = AlignmentFlag

    def _NewRect(self, m, o):
        r = self.Rect
        return QRect(r.x() + m.left(),
                     r.y() + o + m.top(), r.width(), r.height())

    def Print(self, p: QPainter, m: QMargins, o: int = 0):
        if self.Report.TotalPagesCalculated is False or self.Visible is False:
            return

        r1, r2 = self.Report.onBeforePrint(
            self.Report._CurrentCopys, self.Section,
            self.Section._GetCurrentPrintRecord(), self)
        if r1:
            return
        txt = r2 if not (r2 is None) else self.getPrintText()
        rect = self._NewRect(m, o)
        # 填充颜色
        if self.FillColor:
            p.fillRect(rect, self.FillColor)
        # 绘制边框及文本
        if self.Bolder or self.FillColor:
            p.drawRect(rect)
            rect = rect - QMargins(1, 1, 1, 1)
        p.setFont(self.Font)

        if self.Transform:
            # 文本旋转的情况
            FontHeight = QFontMetrics(self.Font).height()
            p.save()
            p.translate(self.Rect.x() + m.left() + FontHeight,
                        self.Rect.y() + m.top() + o)
            # 第一个参数为距离
            p.rotate(90)
            p.drawText(QRect(0, 0, self.Rect.width(), self.Rect.height()),
                       self.AlignmentFlag, txt)
            # 第一个参数Left为调整后距离页面顶端的距离
            p.restore()
        else:
            # 文字不旋转的情况
            fm = p.fontMetrics()
            # 处理长文本省略
            if self.AutoEllipsis:
                elidedText = fm.elidedText(txt, Qt.ElideRight, rect.width())
            # 处理长文本自动缩小字体
            if self.AutoShrinkFont:
                self.__AutoShrinkFont(p, rect, txt)
            if self.AutoEllipsis:
                p.drawText(rect, self.AlignmentFlag, elidedText)
            else:
                p.drawText(rect, self.AlignmentFlag, txt)

    def __AutoShrinkFont(self, p: QPainter, rect: QRect, txt: str):
        # 循环减小字体适应宽度
        c_Font = p.font()
        c_Size = c_Font.pointSize()
        fm = p.fontMetrics()
        w = fm.width(txt)
        r_w = rect.width()
        while w > r_w:
            c_Size -= 1
            c_Font.setPointSize(c_Size)
            p.setFont(c_Font)
            fm = p.fontMetrics()
            w = fm.width(txt)

    @property
    def Section(self):
        if '_Section' not in self.__dict__.keys():
            errStr = '没有指定打印条目{}的Section属性！'
            errStr = errStr.format(str(self.PrintObject))
            raise Exception(errStr)
        else:
            return self._Section

    @Section.setter
    def Section(self, sec):
        self._Section = sec

    @property
    def Report(self):
        return self._Section.Report


class _jpPrintLable(_jpPrintItem):
    def getPrintText(self) -> str:
        return self.FormatString.format(
            self.PrintObject) if self.PrintObject else ''


class _jpPrintPageField(_jpPrintItem):
    def getPrintText(self):
        try:
            s = self.FormatString
            rpt = self.Report
            return s.format(Page=rpt._CurrentPage, Pages=rpt.PageCount)
        except Exception:
            return 'ForamtString Error'


class _jpPrintDateTime(_jpPrintItem):
    def getPrintText(self):
        try:
            dt = QDateTime.currentDateTime()
            return dt.toString(self.FormatString)
        except Exception:
            return 'ForamtString Error'


class _itemFormatMixin(object):
    '''混入类，只能多重继承用'''
    def getPrintString(self, value: typing.Any, jptype: FieldType) -> str:
        result = ''
        field = self.Report.DataSourceRecord.field(self.PrintObject)
        s = self.FormatString
        T = FieldType
        try:
            if jptype == T.Int or jptype == T.Float:
                s = s if s else '{:,.' + str(field.precision()) + 'f}'
                result = s.format(value)
            elif jptype == T.String:
                result = value
            elif jptype == T.Date:
                result = value.toString(s if s else 'yyyy-MM-dd')
            elif jptype == T.Boolean:
                result = self.Report.BoolString[0 if value == '\x01' else 1]
            elif jptype == T.DateTime:
                ds='yyyy-MM-dd hh:mm:ss.zzz'
                result = value.toString(s if s else ds)
            elif jptype == T.Time:
                result = value.toString(s if s else 'hh:mm:ss.zzz')
            elif jptype == T.Other:
                result = str(value)
        except Exception as e:
            errMsg = '[{}]字段值[{}]格式化错误,[{}]!错误信息\n{}'
            result = errMsg.format(field.name(), field.value, str(s), str(e))
            logging.getLogger().warning(result)
        finally:
            return result


class _jpPrintField(_jpPrintItem, _itemFormatMixin):
    def getPrintText(self):
        retult = ''
        fieldName = self.PrintObject
        rowData = self.Section._GetCurrentPrintRecord()
        if fieldName not in rowData.keys():
            errMsg = "数据源中没有找到字段'[{}]',请检查相关指定数据源的语句！"
            errMsg = errMsg.format(fieldName)
            logging.getLogger().warning(errMsg)
        else:
            jptype = self.Report.__dict__['_Report__FieldTypes'][fieldName]
            value = rowData[fieldName]
            if value:
                retult = self.getPrintString(value, jptype)
        return retult


class _jpPrintRowCount(_jpPrintItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__currentRow = 0

    def Print(self, painter, Margins, SectionPrintBeginY, currentRow):
        self.__currentRow = currentRow
        super().Print(painter, Margins, SectionPrintBeginY)

    def getPrintText(self):
        return str(self.__currentRow)


class _jpPrintCopyTitle(_jpPrintItem):
    def __init__(self, rect: QRect, PrintObject, **kwargs):
        if isinstance(PrintObject, (list, tuple)):
            if len(PrintObject) == 0:
                errMsg = '联次信息不能为空'
                raise Exception(errMsg.format(str(type(PrintObject))))
        else:
            errMsg = '联次信息必须为一个由字符串构成的列表或元组，但给定值类型为{}'
            raise Exception(errMsg.format(str(type(PrintObject))))
        super().__init__(rect, PrintObject, **kwargs)
        self._CopysInfomation = PrintObject

    def getPrintText(self):
        return self._CopysInfomation[self.Report._CurrentCopys - 1]


class _jpPrintPixmap(_jpPrintItem):
    def __init__(self, rect, obj, **kwargs):
        img = QPixmap(obj)
        super().__init__(rect, img, **kwargs)

    def Print(self, painter, *args):
        if self.Report.TotalPagesCalculated is False:
            return
        if self.Visible is False:
            return
        r1, r2 = self.Report.onBeforePrint(
            self.Report._CurrentCopys, self.Section,
            self.Section._GetCurrentPrintRecord(), self)
        if r1:
            return
        obj = r2 if isinstance(r2, QPixmap) else self.PrintObject
        if self.Report.TotalPagesCalculated:
            painter.drawPixmap(self._NewRect(args[0], args[1]), obj)

    def getPrintText(self) -> typing.Any:
        return


class _jpPrintSection(object):
    """本类描述一个打印的节,抽象类，请不要实例化"""

    # Report = None  # 类属性，节所属的报表对象

    def __init__(self, report):
        self.Report = report
        self.Items: list = []
        self._Height = 0

    def __len__(self):
        """节中打印条目的个数"""
        return len(self.Items)

    @property
    def SectionType(self) -> PrintSectionType:
        if '__SectionType' not in self.__dict__.keys():
            return PrintSectionType.Unknown
        else:
            return self.__SectionType

    @SectionType.setter
    def SectionType(self, secType: PrintSectionType):
        self.__SectionType = secType

    @abc.abstractmethod
    def Print(self, painter):
        pass

    @property
    def SectionHeight(self):
        return self._Height

    def _setSectionHeight(self, pitem: _jpPrintItem):
        if pitem.Transform:
            # 旋转文字方向时，高度计算方法为左加宽，也就是算最右
            maxH = pitem.Rect.width() + pitem.Rect.top()
        else:
            maxH = pitem.Rect.height() + pitem.Rect.top()
        if (maxH) > self._Height:
            self._Height = maxH

    def addPrintItemRect(self, itemType: PrintItemType, rect: QRect, obj,
                         **kwargs) -> typing.Any:
        """
        添加一个单独的打印条目\n
        obj 为内容，对应itemType值如下。
            1：标签文本的字符串对象 ; 2：图片路径或QPixmap对象； 3：字段名称；4：页码；5：日期时间 
        其他命名参数：\n
        Font=QFont 对象 
        FormatString='' 格式字符串。应用于字符串format方法 
            日期时间或页码页码格式字符串。应用于字符串format方法 如：'第{Page}/{Pages}\n
            时间日期格式字符串。如： "PrintTime: %Y-%m-%d %H:%M:%S"
        AlignmentFlag=Qt.Align 如 (Qt.AlignLeft | Qt.TextWordWrap)为左对齐且自动折行
        Bolder=bool 是否打印边框
        Transform=bool 是否纵向文本,itemType为2时无效
        Transform值为True时：
        w 指的是打印条目的纵向高度（相对于纸张）
        h 指的是打印条目的横向宽度（相对于纸张）
        """
        JT = PrintItemType
        classDic = {
            JT.Label: _jpPrintLable,
            JT.Field: _jpPrintField,
            JT.Picture: _jpPrintPixmap,
            JT.Page: _jpPrintPageField,
            JT.RowCount: _jpPrintRowCount,
            JT.PrintDateTime: _jpPrintDateTime,
            JT.CopyTitle: _jpPrintCopyTitle
        }
        currectCls = classDic[itemType]
        pitem = currectCls(rect, obj, **kwargs)
        pitem.Section = self
        #pitem.Report = self.Report
        self._setSectionHeight(pitem)
        self.Items.append(pitem)
        return pitem

    def __getItemObjectName(self, nameString: str, objClass) -> str:
        # 生成一个打印项目名
        item = list([p for p in self.Items if isinstance(p, objClass)])
        fn = '{}_{}'.format(nameString, len(item) + 1)
        return fn

    def addPrintItem(self, itemType: PrintItemType, x, y, w, h, obj,
                     **kwargs) -> _jpPrintItem:
        """addPrintItemRect的重载函数\n
        x, y, w, h 分别为 左，上，宽，高。注意对于文本，y值指 BaseLine的y坐标"""
        return self.addPrintItemRect(itemType, QRect(x, y, w, h), obj,
                                     **kwargs)

    def addPrintLabel(self, rect: QRect, text: str, **kwargs) -> _jpPrintLable:
        """addPrintItemRect的重载函数,添加一个打印字符串"""
        kwargs['AlignmentFlag'] = kwargs.get('AlignmentFlag',
                                             Qt.AlignVCenter | Qt.AlignLeft)
        return self.addPrintItemRect(PrintItemType.Label, rect, text,
                                     **kwargs)

    def addPrintCopysInfomation(self, rect: QRect, CopysTitleList: list,
                                **kwargs) -> _jpPrintLable:
        """addPrintItemRect的重载函数,添加一个联次信息"""
        return self.addPrintItemRect(PrintItemType.CopyTitle, rect,
                                     CopysTitleList, **kwargs)

    def addPrintField(self, rect: QRect, fieldName: str,
                      **kwargs) -> _jpPrintField:
        """addPrintItemRect的重载函数,添加一个打印字段"""
        if 'FormatString' not in kwargs.keys():
            kwargs['FormatString'] = ''
        return self.addPrintItemRect(PrintItemType.Field, rect, fieldName,
                                     **kwargs)

    def addPrintPixmap(self, rect: QRect, filePathOrPixmap,
                       **kwargs) -> _jpPrintPixmap:
        """addPrintItemRect的重载函数,添加一个打印图片，可用路径或path"""
        return self.addPrintItemRect(PrintItemType.Picture, rect,
                                     filePathOrPixmap, **kwargs)

    def addPrintPageField(self, rect: QRect, **kwargs) -> _jpPrintPageField:
        """addPrintItemRect的重载函数,添加一个打印页码\n 
        FormatString='' 格式字符串。
        应用于字符串format方法 '第{Page}/{Pages}页\n
        """
        fn = self.__getItemObjectName('PrintRowCount', _jpPrintRowCount)
        item = self.addPrintItemRect(PrintItemType.Page, rect, fn, **kwargs)
        item.FormatString = kwargs.get("FormatString", '第{Page}/{Pages}页')
        item.Bolder = kwargs.get("Bolder", False)
        return item

    def addPrintRowCount(self, rect: QRect, **kwargs) -> _jpPrintRowCount:
        """addPrintItemRect的重载函数,添加一个打印行号，
        一般用于detail节"""
        fn = self.__getItemObjectName('PrintRowCount', _jpPrintRowCount)
        return self.addPrintItemRect(PrintItemType.RowCount, rect, fn,
                                     **kwargs)

    def addPrintDateTime(self, rect: QRect, **kwargs) -> _jpPrintDateTime:
        """addPrintItemRect的重载函数,添加一个打印日期或时间
        （打印报表时的系统日期时间）\n 
        时间日期格式字符串(不能有花括号)。
        如： "PrintTime: yyyy-MM-dd hh:mm:ss.zzzz"
        """
        fn = self.__getItemObjectName('PrintDateTime', _jpPrintDateTime)
        item = self.addPrintItemRect(PrintItemType.PrintDateTime, rect, fn,
                                     **kwargs)
        item.FormatString = kwargs.get("FormatString",
                                       'yyyy-MM-dd hh:mm:ss.zzz')
        item.Bolder = kwargs.get("Bolder", False)
        return item

    def __addMultipleItems(self,
                           itemType: PrintItemType,
                           left,
                           top,
                           height,
                           Texts: list = [],
                           Widths: list = [],
                           Aligns: list = [],
                           **kwargs):
        '''一次性添加多个项目'''
        n_texts = len(Texts)
        n_widths = len(Widths)
        n_aligns = len(Aligns)
        msg = '标签数与宽度、对齐数不相等:\n'
        msg = msg + f'标签数为{n_texts};宽度数为{n_widths};对齐数为{n_aligns}'
        msg = msg + '\n' + str(Texts)
        if not (n_texts > 0 and n_texts == n_widths and n_texts == n_aligns):
            raise PrintError(msg)
        leftSum = 0
        for i in range(n_texts):
            AD = self.addPrintItemRect
            AD(itemType,
               QRect(left + leftSum, top, Widths[i], height),
               Texts[i],
               AlignmentFlag=Aligns[i],
               **kwargs)
            leftSum += Widths[i]

    def addPrintLables(self,
                       left,
                       top,
                       height,
                       Texts: list = [],
                       Widths: list = [],
                       Aligns: list = [],
                       **kwargs):
        '''为一个方便一次性添加多个打印文本的方法，一般用于打印表格式报表的表头'''
        if not Aligns:
            Aligns = [Qt.AlignVCenter | Qt.AlignLeft] * len(Texts)
        self.__addMultipleItems(PrintItemType.Label, left, top, height,
                                Texts, Widths, Aligns, **kwargs)

    def addPrintFields(self,
                       left,
                       top,
                       height,
                       fieldsName: list = [],
                       Widths: list = [],
                       Aligns: list = [],
                       **kwargs):
        '''为一个方便一次性添加多个字段的方法，一般用于打印表格式报表的表体'''
        self.__addMultipleItems(PrintItemType.Field, left, top, height,
                                fieldsName, Widths, Aligns, **kwargs)

    def _GetCurrentPrintRecord(self) -> typing.Any:
        # 当前节为Detail时返回当前正在打印的数据行，否则返回报表数据源第一行
        if self.SectionType is PrintSectionType.Detail:
            return self.__dict__['_CurrentPrintRowData']
        if self.Report.DataSource:
            return self.Report.DataSource[0]
        else:
            return None

    def _RaisePrintError(self):
        estr = "节【{}】的超出页面可打印范围".format(self.__dict__["SectionType"])
        raise PrintError(estr)


class _SectionAutoPaging(_jpPrintSection):
    """定义一个自动分页的节，实现，请不要实例化"""
    def __init__(self, *args, **kwargs):
        #  当前页面条目打印时的向下偏移量
        self._CurPageOffset = 0
        #  止上页本节所有已打印项目的总高度
        self._SectionOffset = 0
        super().__init__(*args, **kwargs)

    def Print(self, painter):
        rpt = self.Report
        self._SectionOffset = 0
        self._CurPageOffset = rpt._SectionPrintBeginY
        if rpt.onFormat(self.SectionType, rpt._CurrentPage) or len(self) == 0:
            return
        last_item = None
        for item in self.Items:
            if item.Visible is False:
                continue
            item_bottom = item.Rect.top() + item.Rect.height()
            # 计算当面页面扣除页脚高度后，还能否容纳当前条目，如不能则进行分页
            if (self._CurPageOffset + item_bottom - self._SectionOffset) > (
                    rpt.PageValidHeight - rpt.PageFooter.SectionHeight):
                self._SectionOffset = item.Rect.top()
                rpt._Report__insertNewPage(painter)
                self._CurPageOffset = rpt._SectionPrintBeginY
            item.Print(painter, rpt.Margins,
                       -1 * self._SectionOffset + self._CurPageOffset)
             # 纵向打印的不参与计算SectionPrintBeginY
            if item.Transform is False:
                last_item = item
        # 打印完所有条目后，为下一节保存开始位置，存放于报表对象中
        rpt._SectionPrintBeginY += (last_item.Rect.top() +
                                    last_item.Rect.height() -
                                    self._SectionOffset)


class _jpSectionReportHeader(_SectionAutoPaging):
    """报表、组页头类"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SectionType = PrintSectionType.ReportHeader

    def Print(self, painter):
        super().Print(painter)


class _jpSectionReportFooter(_SectionAutoPaging):
    """报表、组页脚类"""
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.SectionType = PrintSectionType.ReportFooter

    def Print(self, painter):
        rpt = self.Report
        curSecH = self.SectionHeight
        if rpt.onFormat(self.SectionType, rpt._CurrentPage) or len(self) == 0:
            return

        # 判断页面剩余空间能否容纳页脚节高度及页脚高度，不能则分页
        if rpt.PageValidHeight < (rpt._SectionPrintBeginY + curSecH +
                                  rpt.PageFooter.SectionHeight):
            rpt._Report__insertNewPage(painter)
            rpt._SectionPrintBeginY = rpt.PageHeader.SectionHeight
        for item in self.Items:
            item.Print(painter, rpt.Margins, rpt._SectionPrintBeginY)
        rpt._SectionPrintBeginY += curSecH


class _jpSectionDetail(_jpPrintSection):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.SectionType = PrintSectionType.Detail

    def Print(self, painter, dataRows):
        rpt = self.Report
        curSecH = self.SectionHeight
        if rpt.onFormat(self.SectionType, rpt._CurrentPage) or len(self) == 0:
            return
        # 判断一下能否同时容纳主体节、页面页眉、页面页脚，不能容纳则抛出错误

        if rpt.PageValidHeight < (curSecH + rpt.PageHeader.SectionHeight +
                                  rpt.PageFooter.SectionHeight):
            self._RaisePrintError()
        rows = dataRows
        for i, row in enumerate(rows):
            self._CurrentPrintRowData = row
            if rpt.onFormat(self.SectionType, rpt._CurrentPage, row):
                continue
            # 判断页面剩余空间能否容纳一个节高度及页脚高度，不能则分页
            if rpt.PageValidHeight < (rpt._SectionPrintBeginY + curSecH +
                                      rpt.PageFooter.SectionHeight):
                rpt._Report__insertNewPage(painter)
                rpt._SectionPrintBeginY = rpt.PageHeader.SectionHeight
            # 打印主体节每一个条目
            for item in self.Items:
                if isinstance(item, _jpPrintRowCount):
                    item.Print(painter, rpt.Margins, rpt._SectionPrintBeginY,
                               i + 1)
                else:
                    item.Print(painter, rpt.Margins, rpt._SectionPrintBeginY)
            rpt._SectionPrintBeginY += curSecH


class _jpSectionPageHeader(_jpPrintSection):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.SectionType = PrintSectionType.PageHeader

    def Print(self, painter):
        rpt = self.Report
        if rpt.onFormat(self.SectionType, rpt._CurrentPage) or len(self) == 0:
            return
        # 判断当前页面剩余空间能否容纳本节，如不能则引发错误
        if rpt.PageValidHeight < (rpt._SectionPrintBeginY +
                                  self.SectionHeight):
            self._RaisePrintError()
        for item in self.Items:
            if item.Visible is False:
                continue
            item.Print(painter, rpt.Margins, rpt._SectionPrintBeginY)
        rpt._SectionPrintBeginY = self.SectionHeight


class _jpSectionPageFooter(_jpPrintSection):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.SectionType = PrintSectionType.PageFooter

    def Print(self, painter):
        rpt = self.Report
        if rpt.onFormat(self.SectionType, rpt._CurrentPage) or len(self) == 0:
            return
        # 判断当前页面剩余空间能否容纳本节，如不能则引发错误
        if rpt.PageValidHeight < (rpt._SectionPrintBeginY +
                                  self.SectionHeight):
            self._RaisePrintError()
        # 处理打印页脚打印时的开始点
        ph = rpt._Report__PageHeight
        sh = self.SectionHeight
        mb = rpt.Margins.bottom()
        mt = rpt.Margins.top()
        by = rpt._SectionPrintBeginY
        by = (ph - sh - mb - mt)
        for item in self.Items:
            if item.Visible is False:
                continue
            item.Print(painter, rpt.Margins, by)
        # 打印完页脚后恢复节的当前打印高度
        rpt._SectionPrintBeginY = 0


class _jpGroupCalcField(_jpPrintItem, _itemFormatMixin):
    def curentValues(self):
        errStr = '当前行数据中[{}]字段的值类型错误，分组的计算字段只能是'
        errStr = errStr = 'int或float类型!当前行数据为{}'
        fn = self.PrintObject
        for r in self.Section.CurrentDataRows:
            v = r[fn]
            if v:
                if not isinstance(v, (int, float)):
                    raise Exception(errStr.format(fn, r))
                yield v
            else:
                yield 0

    def getPrintString(self, value, jptype=None):
        fn = self.PrintObject
        key = '_Report__FieldTypes'
        if jptype is None:
            jptype = self.Report.__dict__[key][fn]
        return super().getPrintString(value, jptype)

    def _getFirstOtLast(self, location: int) -> str:
        # 取第一行或最后一行的字段值
        fn = self.PrintObject
        rows = self.Section.CurrentDataRows
        v = rows[location][fn] if rows else ''
        return self.getPrintString(v)


class _jpGroupCalcField_Sum(_jpGroupCalcField):
    def getPrintText(self):
        return self.getPrintString(sum(self.curentValues()))


class _jpGroupCalcField_Count(_jpGroupCalcField):
    def getPrintText(self):
        tp = FieldType.Int
        v = len(list(self.curentValues()))
        return self.getPrintString(v, tp)


class _jpGroupCalcField_Average(_jpGroupCalcField):
    def getPrintText(self):
        data = self.curentValues()
        n = len(list(data))
        tp = FieldType.Float
        v = sum(data) // n if n else None
        return self.getPrintString(v, tp)


class _jpGroupCalcField_Max(_jpGroupCalcField):
    def getPrintText(self):
        v = max(self.curentValues())
        return self.getPrintString(v)


class _jpGroupCalcField_Min(_jpGroupCalcField):
    def getPrintText(self):
        v = min(self.curentValues())
        return self.getPrintString(v)


class _jpGroupCalcField_First(_jpGroupCalcField):
    def getPrintText(self):
        return self._getFirstOtLast(0)


class _jpGroupCalcField_Last(_jpGroupCalcField):
    def getPrintText(self):
        return self._getFirstOtLast(-1)


class _jpGroupSection(_SectionAutoPaging):
    def __init__(self, report, group):
        super().__init__(report)
        self.Group = group

    def AddCaluField(self, CalcMode: CalcFieldType, rect: QRect,
                     CalcFieldName, **kwargs):
        '''
        添加一个组内计算字段。CalcMode为计算类型，
        CalcFieldName为计算的字段名。\n
        '''
        tp = CalcFieldType
        tempclses = {
            tp.Sum: _jpGroupCalcField_Sum,
            tp.Count: _jpGroupCalcField_Count,
            tp.Average: _jpGroupCalcField_Average,
            tp.Max: _jpGroupCalcField_Max,
            tp.Min: _jpGroupCalcField_Min,
            tp.First: _jpGroupCalcField_First,
            tp.Last: _jpGroupCalcField_Last
        }
        pitem = tempclses[CalcMode](rect, CalcFieldName, **kwargs)
        #pitem.Report = self.Report
        pitem.Section = self
        self.Items.append(pitem)

    def Print(self, painter, dataRows):
        self.CurrentDataRows = dataRows
        super().Print(painter)


class _GroupLinkList(BilateralLinkList):
    def __init__(self, report):
        super().__init__()
        self.Report = report

    def __getValueTuple(self, row, keyTup: tuple) -> tuple:
        '''根据给定行数据及一个分组字段名元组，生成一个值元组'''
        result = ()
        for key in keyTup:
            v = row[key]
            result = result + (v if str(v) else '', )
        return result

    def init_GroupKeys(self):
        # 执行任何打印操作前必须先计算一次此函数
        # 此函数给各级分组的键值表赋值
        if self.is_empty():
            return
        # 从第一个分组开始，执行每一个分组值的打印，先打印
        # 分组页眉，如果当前分组为末级分组，调用打印明细数据
        # 再打印分组页脚
        for row in self.Report.DataSource:
            for node in self.itemsReverse():
                keyTup = node.GroupFieldNames
                valueTup = self.__getValueTuple(row, keyTup)
                grp_k_d = node.GroupKeysData
                if valueTup in grp_k_d.keys():
                    grp_k_d[valueTup].append(row)
                else:
                    grp_k_d[valueTup] = [row]


class _Group(object):
    def __init__(self, report, GroupByFieldName: str):
        '''定义一个组，GroupByFieldName为分组字段'''
        self.__gfn = GroupByFieldName
        self.Report = report
        self.GroupHeader = _jpGroupSection(report, self)
        self.GroupHeader.SectionType = PrintSectionType.GroupHeader
        self.GroupFooter = _jpGroupSection(report, self)
        self.GroupFooter.SectionType = PrintSectionType.GroupFooter
        self.GroupKeysData = {}

    @property
    def GroupFieldNames(self) -> tuple:
        '''用递归的方式取得当前组的分组字段元组,row为一行数据的字典'''
        if 'my__GroupFieldNames__' not in self.__dict__.keys():
            curTuple = (self.__gfn, )
            node = self.Report._GroupLinkList.findNode(self)
            if node.prev is None:
                self.my__GroupFieldNames__ = curTuple
            else:
                self.my__GroupFieldNames__ = node.prev.item.GroupFieldNames + curTuple
        return self.my__GroupFieldNames__

    def Print(self, painter, parentCurrentKeys: tuple = ()):
        l = len(parentCurrentKeys)
        rgl = self.Report._GroupLinkList
        for key in self.GroupKeysData.keys():
            if key[0:l] == parentCurrentKeys:
                curDataRows = self.GroupKeysData[key]
                self.GroupHeader.Print(painter, curDataRows)
                nextNode = rgl.findNode(self).next
                if nextNode:
                    nextNode.item.Print(painter, key)
                else:
                    self.Report.Detail.Print(painter, curDataRows)
                self.GroupFooter.Print(painter, curDataRows)


class _PrintPreviewDialog(QPrintPreviewDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # def open(self):
    #     print("afadsfasdf")

    # def done(self,int1):
    #     print(int1)


class Report(object):
    """报表类"""
    def __init__(self,
                 PaperSize=QPrinter.A4,
                 Orientation=QPrinter.Orientation(0),
                 db=QtSql.QSqlDatabase()):
        self.TotalPagesCalculated = False
        self.PaperSize = PaperSize
        self.Orientation = Orientation
        self.BoolString = ['是', '否']
        self.Margins: QMargins = QMargins(0, 0, 0, 0)
        self.ReportHeader = _jpSectionReportHeader(self)
        self.ReportFooter = _jpSectionReportFooter(self)
        self.PageHeader = _jpSectionPageHeader(self)
        self.PageFooter = _jpSectionPageFooter(self)
        self.Detail = _jpSectionDetail(self)
        self._Copys = 1
        self._CurrentPage = 0
        self._CurrentCopys = 0
        self.__PageCount = 0
        self.__DataSource = []
        self.__Errors = []
        self.__Printer: typing.Any = None
        self.__PageHeight = 0
        self.__Calculated = False
        self.__Reseted = False
        self.__SectionPrintBeginY = 0
        self.__ExecNewPageTimes = 0
        self.__db: QtSql.QSqlDatabase = db
        self.__FieldTypes = {}
        self._GroupLinkList = _GroupLinkList(self)
        self.DataSourceRecord: QSql.QSqlRecord = None

    def __getFieldType(self, fieldName: str):
        if fieldName not in self.__FieldTypes.keys():
            errMsg = '没有找到名为[{}]字段的类型信息！'.format(fieldName)
            raise Exception(errMsg)
        else:
            return self.__FieldTypes[fieldName]

    def onFormat(self,
                 SectionType: PrintSectionType,
                 CurrentPage: int,
                 RowDate=None):
        """
        请在子类中覆盖本方法
        本方法为报表类各节的格式化事件，返回值为False或None时，
        当前节或Detail节的本行数据不打印，其他值均正常打印。
        """
        msg = '[{}节的format事件没有重写!]'.format(SectionType)
        print(msg)
        return True

    def onBeforePrint(self, Copys, Sec, CurrentPrintRecord: QtSql.QSqlRecord,
                      obj):
        """一个条目的打印前事件,可以重写此方法
        传递参数：
        1、当前Copy数；2、当前打印的节；3、当前打印的行数据(对于Detail节)
        4、当前打印对象 
        要求的返回值：
        第一个值为True时，将取消打印事件
        第二个值有返回值时，将用此返回值做为最终打印的文本,
        """
        return False, None

    @property
    def _SectionPrintBeginY(self):
        return self.__SectionPrintBeginY

    @_SectionPrintBeginY.setter
    def _SectionPrintBeginY(self, top: int):
        self.__SectionPrintBeginY = top

    @property
    def PageCount(self):
        return self.__PageCount

    @PageCount.setter
    def PageCount(self, num):
        if self.TotalPagesCalculated is False:
            self.__PageCount = num

    def AddGroup(self, GroupFieldName: str) -> _Group:
        """添加一个组，参数是组名,可加入多个分组，
        后加入的分组将成为先加入分组的子分组"""
        grp = _Group(self, GroupFieldName)
        self._GroupLinkList.append(grp)
        return grp

    @property
    def PageValidHeight(self) -> int:
        ph = int(self.__PageHeight)
        mt = self.Margins.top()
        mb = self.Margins.bottom()
        return ph - mt - mb

    @property
    def DataSource(self) -> list:
        """返回报表数据源"""
        return self.__DataSource

    @DataSource.setter
    def DataSource(self, data):
        """报表数据源属性\n
        data取值可有两种，一是一个SQL语句，或一个QtSql.QSqlQuery对象
        """
        if isinstance(data, str):
            self.__DataSource = self.__getDataSourceFromSQL(data)
        elif isinstance(data, QtSql.QSqlQuery):
            self.__DataSource = self.__getDataSourceFromQuery(data)

    def __getDataSourceFromSQL(self, sql: str) -> list:
        query = QtSql.QSqlQuery(sql, self.__db)
        return self.__getDataSourceFromQuery(query)

    def __getDataSourceFromQuery(self, query: QtSql.QSqlQuery) -> list:
        if not query.exec():
            errMsg = '报表执行查询失败！语句为\n{}'
            raise Exception(errMsg.format(query.executedQuery()))
        result = []
        self.DataSourceRecord = query.record()
        bz = query.first()
        while bz:
            recs = query.record()
            if not self.__FieldTypes:
                self.__FieldTypes = {
                    recs.field(i).name():
                    getFieldType(self.__db,
                                   recs.field(i).typeID())
                    for i in range(recs.count())
                }
            for i in range(recs.count()):
                row = {
                    recs.field(i).name(): recs.field(i).value()
                    for i in range(recs.count())
                }
            result.append(row)
            bz = query.next()
        return result

    @property
    def Errors(self):
        return self.__Errors

    def SetMargins(self, top=0, left=0, right=0, bottom=0):
        """设置纸边距"""
        self.Margins = QMargins(top, left, right, bottom)

    @property
    def Printer(self) -> QPrinter:
        return self.__Printer

    @Printer.setter
    def Printer(self, Printer):
        # 重置相关内部属性，恢复页码，设置纸型
        self.CurrentPage = 0
        self._CurrentCopys = 0
        if self.__Reseted is False:
            self.PageCount = 0
        self._SectionPrintBeginY = 0
        self.__Printer = Printer
        if self.__Reseted is False:
            self.__Printer.setPaperSize(self.PaperSize)
            self.__Printer.setOrientation(self.Orientation)
            self.__Reseted = True
        pageRect = self.__Printer.pageRect()
        self.__PageHeight = pageRect.height()

    def __insertNewPage(self, painter):
        """创建一个新页，设置下页打印开始位置为页面起始位置"""
        if self.TotalPagesCalculated and self.__ExecNewPageTimes > 0:
            self.__Printer.newPage()
        self._SectionPrintBeginY = 0
        self._CurrentPage += 1
        self.PageCount += 1
        self.PageFooter.Print(painter)
        self.PageHeader.Print(painter)
        self.__ExecNewPageTimes += 1

    def __printOrCalcOneCopy(self, painter):
        """打印或计算一次报表"""
        # 重新打印或计算页码时，总页码清零
        self.PageCount = 0
        self.__insertNewPage(painter)
        #self.PageFooter.Print(painter) 好像重复打印了
        self.ReportHeader.Print(painter)
        if self._GroupLinkList.is_empty():
            # 没有分组时，直接打明细
            self.Detail.Print(painter, self.__DataSource)
        else:
            grp = self._GroupLinkList.first().item
            grp.Print(painter)
        self.ReportFooter.Print(painter)

    def __setMaxCopys(self):
        '''取得最大联次数,防止用户加入多个联次字段'''
        secs = [
            self.ReportHeader, self.ReportFooter, self.PageHeader,
            self.PageFooter, self.Detail
        ]
        for sec in secs:
            for item in sec.Items:
                if isinstance(item, _jpPrintCopyTitle):
                    ic = item.Report._Copys
                    l = len(item._CopysInfomation)
                    item.Report._Copys = max(l, ic)

    def printPreview(self, printer: QPrinter):
        """PrintPreview方法会自动接收一个参数 ，参数为QPrinter对象"""
        self.Printer = printer
        painter = QPainter(printer)
        #painter.restore()
        self.TotalPagesCalculated = False
        # 第一遍打印用于计算总页数，其后打印进行实际绘制
        self.__printOrCalcOneCopy(painter)
        self.__ExecNewPageTimes = 0
        self.TotalPagesCalculated = True
        for i in range(self._Copys):
            self._CurrentPage = 0
            self._CurrentCopys += 1
            self.__printOrCalcOneCopy(painter)

    def beginPrint(self):
        if len(self.__Errors):
            return
        # 打印之前先进行分组字段的计算，并修改计算完成标志
        # 放到此处是为了防止用户在修改纸型等打印参数时引发重算
        self.__setMaxCopys()
        # 分组计算
        self._GroupLinkList.init_GroupKeys()
        self.__Calculated = True

        # 后台用用户定义的纸型及边距计算一次页码，注意过程中不用真正绘制
        dialog = _PrintPreviewDialog(self.Printer)
        dialog.paintRequested.connect(self.printPreview)

        dialog.exec_()
