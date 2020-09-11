
from enum import Enum
from dataclasses import dataclass

class JPEditDataMode(Enum):
    '''指定编辑数据模式：只读、编辑、新增'''
    readOnlyMode = 0
    editMode = 1
    newMode = 2

class JPButtonEnum(Enum):
    '''窗体中按钮的类型'''
    Save = 0
    Cancel = 1
    Print = 2
    Delete = 3
    PDF = 4
    Search = 5
    ExportExcel = 6


class JPEditFormModelRole(Enum):
    '''指定编辑模型的类型：单个表或母子表'''
    mainModel = 0
    mainSubModel = 1
    subModel = 2

class JPStatisticsMode(Enum):
    '''统计数据的类型'''
    Sum = 1
    Max = 2
    Min = 4
    Average = 8

class SaveDataSqlType(Enum):
    '''额外保存数据的sql类型'''
    beforeSaveMainFormData = 0
    afterSaveMainFormData = 1
    beforeSaveSubFormData = 2
    afterSaveSubFormData = 3

@dataclass
class _statisticsColumn:
    statisticsMode: JPStatisticsMode = JPStatisticsMode.Sum
    precision: int = 0
    func = lambda x: sum(x)
