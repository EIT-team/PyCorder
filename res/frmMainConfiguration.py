# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'frmMainConfiguration.ui'
#
# Created: Wed Jun 05 12:00:50 2013
#      by: PyQt4 UI code generator 4.5.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_frmConfiguration(object):
    def setupUi(self, frmConfiguration):
        frmConfiguration.setObjectName("frmConfiguration")
        frmConfiguration.setWindowModality(QtCore.Qt.ApplicationModal)
        frmConfiguration.resize(861, 743)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/process.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        frmConfiguration.setWindowIcon(icon)
        self.gridLayout = QtGui.QGridLayout(frmConfiguration)
        self.gridLayout.setObjectName("gridLayout")
        self.tabWidget = QtGui.QTabWidget(frmConfiguration)
        self.tabWidget.setObjectName("tabWidget")
        self.tab1 = QtGui.QWidget()
        self.tab1.setObjectName("tab1")
        self.gridLayout1 = QtGui.QGridLayout(self.tab1)
        self.gridLayout1.setObjectName("gridLayout1")
        self.tabWidget.addTab(self.tab1, "")
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(frmConfiguration)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(frmConfiguration)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), frmConfiguration.accept)
        QtCore.QMetaObject.connectSlotsByName(frmConfiguration)

    def retranslateUi(self, frmConfiguration):
        frmConfiguration.setWindowTitle(QtGui.QApplication.translate("frmConfiguration", "Configuration", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab1), QtGui.QApplication.translate("frmConfiguration", "Tab 1", None, QtGui.QApplication.UnicodeUTF8))

import resources_rc
