# -*- coding: utf-8 -*-
# flake8: noqa

################################################################################
## Form generated from reading UI file 'table_with_tool_bar.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHeaderView, QSizePolicy, QVBoxLayout,
    QWidget)

from xms.guipy.widgets.qx_table_view import QxTableView
from xms.guipy.widgets.tool_bar import ToolBar

class Ui_table_with_toolbar(object):
    def setupUi(self, table_with_toolbar):
        if not table_with_toolbar.objectName():
            table_with_toolbar.setObjectName(u"table_with_toolbar")
        table_with_toolbar.resize(400, 300)
        self.verticalLayout = QVBoxLayout(table_with_toolbar)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.table = QxTableView(table_with_toolbar)
        self.table.setObjectName(u"table")

        self.verticalLayout.addWidget(self.table)

        self.tool_bar = ToolBar(table_with_toolbar)
        self.tool_bar.setObjectName(u"tool_bar")

        self.verticalLayout.addWidget(self.tool_bar)


        self.retranslateUi(table_with_toolbar)

        QMetaObject.connectSlotsByName(table_with_toolbar)
    # setupUi

    def retranslateUi(self, table_with_toolbar):
        table_with_toolbar.setWindowTitle(QCoreApplication.translate("table_with_toolbar", u"Form", None))
    # retranslateUi

