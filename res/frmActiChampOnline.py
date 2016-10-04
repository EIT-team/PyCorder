# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'frmActiChampOnline.ui'
#
# Created: Wed Jun 05 12:00:50 2013
#      by: PyQt4 UI code generator 4.5.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_frmActiChampOnline(object):
    def setupUi(self, frmActiChampOnline):
        frmActiChampOnline.setObjectName("frmActiChampOnline")
        frmActiChampOnline.resize(427, 233)
        frmActiChampOnline.setFrameShape(QtGui.QFrame.Panel)
        frmActiChampOnline.setFrameShadow(QtGui.QFrame.Raised)
        self.gridLayout_3 = QtGui.QGridLayout(frmActiChampOnline)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.groupBoxMode = QtGui.QGroupBox(frmActiChampOnline)
        self.groupBoxMode.setFlat(False)
        self.groupBoxMode.setCheckable(False)
        self.groupBoxMode.setObjectName("groupBoxMode")
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBoxMode)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButtonStartDefault = QtGui.QPushButton(self.groupBoxMode)
        self.pushButtonStartDefault.setMinimumSize(QtCore.QSize(100, 40))
        self.pushButtonStartDefault.setStyleSheet("text-align: left; padding-left: 10px;")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/play.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon.addPixmap(QtGui.QPixmap(":/icons/play_green.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.pushButtonStartDefault.setIcon(icon)
        self.pushButtonStartDefault.setIconSize(QtCore.QSize(32, 32))
        self.pushButtonStartDefault.setCheckable(True)
        self.pushButtonStartDefault.setAutoExclusive(True)
        self.pushButtonStartDefault.setAutoDefault(False)
        self.pushButtonStartDefault.setObjectName("pushButtonStartDefault")
        self.horizontalLayout.addWidget(self.pushButtonStartDefault)
        self.pushButtonStartShielding = QtGui.QPushButton(self.groupBoxMode)
        self.pushButtonStartShielding.setMinimumSize(QtCore.QSize(100, 40))
        self.pushButtonStartShielding.setStyleSheet("text-align: left; padding-left: 10px;")
        self.pushButtonStartShielding.setIcon(icon)
        self.pushButtonStartShielding.setIconSize(QtCore.QSize(32, 32))
        self.pushButtonStartShielding.setCheckable(True)
        self.pushButtonStartShielding.setAutoExclusive(True)
        self.pushButtonStartShielding.setObjectName("pushButtonStartShielding")
        self.horizontalLayout.addWidget(self.pushButtonStartShielding)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.pushButtonStop = QtGui.QPushButton(self.groupBoxMode)
        self.pushButtonStop.setMinimumSize(QtCore.QSize(100, 40))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/stop.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon1.addPixmap(QtGui.QPixmap(":/icons/stop_green.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.pushButtonStop.setIcon(icon1)
        self.pushButtonStop.setIconSize(QtCore.QSize(32, 32))
        self.pushButtonStop.setCheckable(True)
        self.pushButtonStop.setAutoExclusive(True)
        self.pushButtonStop.setObjectName("pushButtonStop")
        self.gridLayout.addWidget(self.pushButtonStop, 2, 0, 1, 1)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushButtonStartImpedance = QtGui.QPushButton(self.groupBoxMode)
        self.pushButtonStartImpedance.setMinimumSize(QtCore.QSize(100, 40))
        self.pushButtonStartImpedance.setIcon(icon)
        self.pushButtonStartImpedance.setIconSize(QtCore.QSize(32, 32))
        self.pushButtonStartImpedance.setCheckable(True)
        self.pushButtonStartImpedance.setAutoExclusive(True)
        self.pushButtonStartImpedance.setAutoDefault(False)
        self.pushButtonStartImpedance.setObjectName("pushButtonStartImpedance")
        self.horizontalLayout_2.addWidget(self.pushButtonStartImpedance)
        self.pushButtonStartTest = QtGui.QPushButton(self.groupBoxMode)
        self.pushButtonStartTest.setMinimumSize(QtCore.QSize(100, 40))
        self.pushButtonStartTest.setIcon(icon)
        self.pushButtonStartTest.setIconSize(QtCore.QSize(32, 32))
        self.pushButtonStartTest.setCheckable(True)
        self.pushButtonStartTest.setChecked(False)
        self.pushButtonStartTest.setAutoExclusive(True)
        self.pushButtonStartTest.setObjectName("pushButtonStartTest")
        self.horizontalLayout_2.addWidget(self.pushButtonStartTest)
        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)
        self.gridLayout_3.addWidget(self.groupBoxMode, 0, 0, 1, 1)

        self.retranslateUi(frmActiChampOnline)
        QtCore.QMetaObject.connectSlotsByName(frmActiChampOnline)

    def retranslateUi(self, frmActiChampOnline):
        frmActiChampOnline.setWindowTitle(QtGui.QApplication.translate("frmActiChampOnline", "Frame", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBoxMode.setTitle(QtGui.QApplication.translate("frmActiChampOnline", "Amplifier", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonStartDefault.setText(QtGui.QApplication.translate("frmActiChampOnline", "Default\n"
"Mode", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonStartShielding.setText(QtGui.QApplication.translate("frmActiChampOnline", "Shielding\n"
"Mode", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonStop.setText(QtGui.QApplication.translate("frmActiChampOnline", "Stop", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonStartImpedance.setStyleSheet(QtGui.QApplication.translate("frmActiChampOnline", "text-align: left; padding-left: 10px;", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonStartImpedance.setText(QtGui.QApplication.translate("frmActiChampOnline", "Impedance\n"
"Mode", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonStartTest.setStyleSheet(QtGui.QApplication.translate("frmActiChampOnline", "text-align: left; padding-left: 10px;", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonStartTest.setText(QtGui.QApplication.translate("frmActiChampOnline", "Test\n"
"Mode", None, QtGui.QApplication.UnicodeUTF8))

import resources_rc
