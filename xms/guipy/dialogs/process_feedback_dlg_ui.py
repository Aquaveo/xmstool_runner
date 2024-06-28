# -*- coding: utf-8 -*-
# flake8: noqa

################################################################################
## Form generated from reading UI file 'process_feedback_dlg.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QGroupBox, QHBoxLayout, QLabel,
    QSizePolicy, QTextEdit, QVBoxLayout, QWidget)

class Ui_ProcessFeedbackDlg(object):
    def setupUi(self, ProcessFeedbackDlg):
        if not ProcessFeedbackDlg.objectName():
            ProcessFeedbackDlg.setObjectName(u"ProcessFeedbackDlg")
        ProcessFeedbackDlg.setWindowModality(Qt.NonModal)
        ProcessFeedbackDlg.resize(707, 541)
        ProcessFeedbackDlg.setModal(False)
        self.verticalLayout_3 = QVBoxLayout(ProcessFeedbackDlg)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.grp_status = QGroupBox(ProcessFeedbackDlg)
        self.grp_status.setObjectName(u"grp_status")
        self.verticalLayout = QVBoxLayout(self.grp_status)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.lbl_status = QLabel(self.grp_status)
        self.lbl_status.setObjectName(u"lbl_status")
        font = QFont()
        font.setBold(True)
        self.lbl_status.setFont(font)
        self.lbl_status.setScaledContents(False)
        self.lbl_status.setWordWrap(False)

        self.horizontalLayout_2.addWidget(self.lbl_status)

        self.lbl_load_indicator = QLabel(self.grp_status)
        self.lbl_load_indicator.setObjectName(u"lbl_load_indicator")

        self.horizontalLayout_2.addWidget(self.lbl_load_indicator)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.lbl_note = QLabel(self.grp_status)
        self.lbl_note.setObjectName(u"lbl_note")
        font1 = QFont()
        font1.setBold(False)
        self.lbl_note.setFont(font1)
        self.lbl_note.setWordWrap(True)

        self.verticalLayout.addWidget(self.lbl_note)


        self.verticalLayout_3.addWidget(self.grp_status)

        self.grp_log = QGroupBox(ProcessFeedbackDlg)
        self.grp_log.setObjectName(u"grp_log")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.grp_log.sizePolicy().hasHeightForWidth())
        self.grp_log.setSizePolicy(sizePolicy)
        self.verticalLayout_2 = QVBoxLayout(self.grp_log)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.txt_log = QTextEdit(self.grp_log)
        self.txt_log.setObjectName(u"txt_log")
        self.txt_log.setLineWrapMode(QTextEdit.NoWrap)
        self.txt_log.setReadOnly(True)
        self.txt_log.setTextInteractionFlags(Qt.TextSelectableByKeyboard|Qt.TextSelectableByMouse)

        self.verticalLayout_2.addWidget(self.txt_log)


        self.verticalLayout_3.addWidget(self.grp_log)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.tog_auto_close = QCheckBox(ProcessFeedbackDlg)
        self.tog_auto_close.setObjectName(u"tog_auto_close")
        self.tog_auto_close.setChecked(True)

        self.horizontalLayout.addWidget(self.tog_auto_close)

        self.btn_box = QDialogButtonBox(ProcessFeedbackDlg)
        self.btn_box.setObjectName(u"btn_box")
        self.btn_box.setOrientation(Qt.Horizontal)
        self.btn_box.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.horizontalLayout.addWidget(self.btn_box)


        self.verticalLayout_3.addLayout(self.horizontalLayout)


        self.retranslateUi(ProcessFeedbackDlg)
        self.btn_box.accepted.connect(ProcessFeedbackDlg.accept)
        self.btn_box.rejected.connect(ProcessFeedbackDlg.reject)

        QMetaObject.connectSlotsByName(ProcessFeedbackDlg)
    # setupUi

    def retranslateUi(self, ProcessFeedbackDlg):
        ProcessFeedbackDlg.setWindowTitle(QCoreApplication.translate("ProcessFeedbackDlg", u"Dialog", None))
        self.grp_status.setTitle("")
        self.lbl_status.setText("")
        self.lbl_load_indicator.setText("")
        self.lbl_note.setText("")
        self.grp_log.setTitle(QCoreApplication.translate("ProcessFeedbackDlg", u"Log", None))
        self.tog_auto_close.setText("")
    # retranslateUi

